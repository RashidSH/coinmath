# -*- coding: utf-8 -*-

import asyncio
import random
import re
import time
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

import cfg
import db
from constants import STR_RULES, STR_HELP_DEPOSIT, STR_HELP_PVP, WORDS_EXP, ChatStates
from logger import logger
from utils import clear_msg, num_split, get_num_ending, get_levels_keyboard, get_example_desc
from vk import VKMessage
from vk_coin import withdraw


async def add_exp(user_id, level, exp, amount):
    new_level = level
    new_exp = exp + amount

    while new_level < len(cfg.config['levels']) and new_exp >= cfg.config['levels'][new_level]['exp']:
        new_level += 1

    await db.set_level_data(user_id, new_level, new_exp, 1)

    if new_level > level:
        return new_level


async def process_events():
    while True:
        while cfg.vk.event_queue:
            event = cfg.vk.event_queue.popleft()

            try:
                if isinstance(event, VKMessage):
                    await handle_msg(event)

            except Exception as ex:
                logger.error('Произошла ошибка при обработке события', exc_info=ex)

        await asyncio.sleep(0.01)


async def handle_msg(msg):
    if msg.user_id < 0 or not msg.text:
        return

    action = None
    if msg.payload is not None and isinstance(msg.payload, dict):
        if 'action' in msg.payload:
            action = msg.payload['action']

    user = await db.get_user(msg.user_id)
    if user is None:
        await db.add_user(msg.user_id)
        user = await db.get_user(msg.user_id)

        if msg.peer_id <= 2e9:
            action = 'menu'

    if msg.peer_id > 2e9:
        await handle_chat_msg(msg, user)
        return

    state = cfg.state.get(msg.user_id)

    if action == 'menu' or re.match(r'(?i)(начать|меню|назад)$', msg.text):
        cfg.state.set(msg.user_id, 'menu')

        keyboard = VkKeyboard()

        if user['level'] == 1:
            keyboard.add_button(
                f"Уровень {user['level']}",
                VkKeyboardColor.PRIMARY,
                payload={'action': 'level', 'level': 1}
            )

            msg.reply(
                f"Привет,{cfg.vk.method('users.get', {'user_ids': msg.user_id})[0]['first_name']}!\n\n{STR_RULES}",
                keyboard.get_keyboard()
            )

        else:
            keyboard.add_button('&#128160; Играть', VkKeyboardColor.PRIMARY, payload={'action': 'play'})
            keyboard.add_button('&#9876; PvP с друзьями', VkKeyboardColor.PRIMARY, payload={'action': 'pvp'})
            keyboard.add_line()
            keyboard.add_button('&#128190; Профиль', payload={'action': 'profile'})
            keyboard.add_button('&#127942; Рейтинг', payload={'action': 'top'})
            keyboard.add_line()
            keyboard.add_button('&#128229; Пополнить', payload={'action': 'deposit'})
            keyboard.add_button('&#128228; Вывести', payload={'action': 'withdraw'})

            msg.reply('Меню:', keyboard.get_keyboard())

    elif action == 'play':
        msg.reply('Выберите уровень:', get_levels_keyboard(user['level']).get_keyboard())

    elif action == 'pvp':
        msg.reply(STR_HELP_PVP.format(cfg.config['group_domain']))

    elif action == 'profile':
        s = f"&#128179; Баланс: {num_split(user['balance'])} VK Coin\n\n&#128302; Уровень: {user['level']}\n&#128202; Очки опыта: {num_split(user['exp'])}"

        if user['level'] < len(cfg.config['levels']):
            s += f" / {num_split(cfg.config['levels'][user['level']]['exp'])}"

        s += f"\n\n&#128221; Решено примеров: {num_split(user['stat_solved'])}"

        msg.reply(s)

    elif action == 'top':
        top, position = await db.get_top(msg.user_id)

        user_links = cfg.vk.get_user_links([i['id'] for i in top])

        s = '&#127942; Топ игроков:\n'

        for index, i in enumerate(top):
            s += f"\n{index + 1}. [{i['level']}] {user_links[i['id']]} — {num_split(i['exp'])} {get_num_ending(i['exp'], WORDS_EXP)}"

        s += f'\n\nВы находитесь на {num_split(position)}-м месте.'

        msg.reply(s)

    elif action == 'deposit':
        msg.reply(STR_HELP_DEPOSIT.format(
            cfg.merchant.get_payment_url(amount=1000 * 1000, free_amount=True)
        ))

    elif action == 'withdraw':
        if user['balance'] <= 0:
            msg.reply('На вашем балансе пусто.')

        if await withdraw(msg.user_id, user['balance']):
            msg.reply(f"&#9989; {num_split(user['balance'])} VK Coin успешно переведены на вашу страницу.")

            await db.add_balance(msg.user_id, -user['balance'])

        else:
            msg.reply('Произошла ошибка... Пожалуйста, повторите попытку через несколько минут.')

    elif action == 'level':
        if ('level' not in msg.payload)\
                or (not isinstance(msg.payload['level'], int))\
                or not (0 < msg.payload['level'] <= len(cfg.config['levels'])):
            return

        level = msg.payload['level']
        if level > user['level']:
            msg.reply('Вам недоступен этот уровень.')
            return

        example = random.choice(cfg.examples[level])

        cfg.state.set_example(msg.user_id, level, example['example'], example['answer'])

        keyboard = VkKeyboard()

        keyboard.add_button('Вернуться назад', VkKeyboardColor.PRIMARY, payload={'action': 'menu'})
        keyboard.add_button('Показать ответ', payload={'action': 'show_answer'})

        msg.reply(
            get_example_desc(level),
            VkKeyboard().get_empty_keyboard() if user['level'] == 1 else keyboard.get_keyboard(),
            attach=f"photo-{cfg.config['group_id']}_{example['photo_id']}"
        )

    elif state == 'example':
        example = cfg.state.get_example(msg.user_id)

        if action == 'show_answer':
            cfg.state.set(msg.user_id, 'menu')

            msg.reply(
                f"Ответ: {example['example'][:-2]} = {example['answer']}",
                get_levels_keyboard(user['level']).get_keyboard()
            )

        else:
            if example['level'] not in (11, 12) and not re.match(r'-?\d+$', msg.text):
                msg.reply('Введите целое число, или нажмите на одну из кнопок, чтобы вернуться назад или узнать ответ.')
                return

            if msg.text.replace('\\', '/') == str(example['answer']):
                reward = cfg.config['levels'][example['level'] - 1]['reward']

                await db.add_balance(msg.user_id, reward)
                new_level = await add_exp(msg.user_id, user['level'], user['exp'], example['level'])

                cfg.state.set(msg.user_id, 'menu')

                msg.reply(
                    f"Ответ верный! Вы получили {reward} VK Coin и {example['level']} {get_num_ending(example['level'], WORDS_EXP)}!",
                    get_levels_keyboard(new_level or user['level']).get_keyboard()
                )

                if new_level:
                    msg.reply(f'&#10035; Вы достигли уровня {new_level}!')

            else:
                msg.reply('Ответ неверный, попробуйте ещё раз...')

    else:
        msg.reply('Команда не найдена.')


async def handle_chat_msg(msg, user):
    chat = await db.get_chat(msg.peer_id)
    if chat is None:
        await db.add_chat(msg.peer_id)
        chat = await db.get_chat(msg.peer_id)

        msg.reply(f"Привет! Чтобы начать игру, напишите \"@{cfg.config['group_domain']} игра\"")

    msg.text = clear_msg(msg.text)

    if chat['state'] == ChatStates.LEVEL_SELECT\
            and msg.payload\
            and 'level_set' in msg.payload\
            and isinstance(msg.payload['level_set'], int)\
            and 0 < msg.payload['level_set'] <= 4:

        await db.set_chat_level_set(msg.peer_id, msg.payload['level_set'])
        await db.set_chat_state(msg.peer_id, ChatStates.BET_SELECT)

        msg.reply('Введите сумму ставки:', VkKeyboard().get_empty_keyboard())

    elif chat['state'] == ChatStates.BET_SELECT and msg.text.isdecimal():
        bet = int(msg.text)
        if bet < 100:
            msg.reply('Минимальная ставка - 100 VK Coin')
            return

        if user['balance'] < bet:
            msg.reply(
                f"У вас недостаточно VK Coin...\n"
                f"Быстрое пополнение: {cfg.merchant.get_payment_url(amount=bet * 1000, free_amount=True)}"
            )
            return

        await db.add_balance(msg.user_id, -bet)
        await db.chat_create_game(msg.peer_id, msg.user_id, bet, int(time.time()))
        await db.set_chat_state(msg.peer_id, ChatStates.WAITING)

        keyboard = VkKeyboard()
        keyboard.add_button(f'Присоединиться ({bet} VK Coin)', payload={'action': 'join_game'})

        msg.reply(
            f'Игра начнётся через 1 минуту! Ставка: {num_split(bet)} VK Coin\n\n\
             Чтобы присоединиться к игре, нажмите на кнопку или напишите "игра"',
            keyboard.get_keyboard()
        )

    elif chat['state'] == ChatStates.PLAYING\
            and str(msg.user_id) in chat['players']\
            and msg.text.replace('\\', '/') == chat['answer']:
        await db.chat_answer(msg.peer_id, msg.user_id, chat['players'][str(msg.user_id)] + 1)
        await db.set_chat_state(msg.peer_id, ChatStates.BREAK)

        new_level = await add_exp(msg.user_id, user['level'], user['exp'], 1)

        msg.reply(f'{cfg.vk.get_user_link(msg.user_id)} ответил(а) верно!')

        if new_level:
            cfg.vk.send(msg.user_id, f'&#10035; Вы достигли уровня {new_level}!')

    elif re.match('(?i)[!/]?(игра|присоединиться)', msg.text):
        if chat['state'] in (ChatStates.MENU, ChatStates.LEVEL_SELECT, ChatStates.BET_SELECT):
            await db.set_chat_state(msg.peer_id, ChatStates.LEVEL_SELECT)

            keyboard = VkKeyboard()
            keyboard.add_button('1-4', payload={'action': 'level_set', 'level_set': 1})
            keyboard.add_button('5-8', payload={'action': 'level_set', 'level_set': 2})
            keyboard.add_button('9-12', payload={'action': 'level_set', 'level_set': 3})
            keyboard.add_line()
            keyboard.add_button('1-12', VkKeyboardColor.PRIMARY, payload={'action': 'level_set', 'level_set': 4})

            msg.reply('Выберите набор уровней:', keyboard.get_keyboard())

        elif chat['state'] == ChatStates.WAITING:
            if str(msg.user_id) not in chat['players']:
                if user['balance'] > chat['bet']:
                    await db.add_balance(msg.user_id, -chat['bet'])
                    await db.chat_join_game(msg.peer_id, msg.user_id)

                    msg.reply(f"Вы присоединились к игре и внесли ставку {chat['bet']} VK Coin!")

                else:
                    msg.reply(
                        f"У вас недостаточно VK Coin...\n"
                        f"Быстрое пополнение: {cfg.merchant.get_payment_url(amount=chat['bet'] * 1000, free_amount=True)}"
                    )

            else:
                msg.reply('Вы уже присоединились к игре.')

        else:
            msg.reply('В беседе уже идёт игра.')
