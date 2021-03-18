# -*- coding: utf-8 -*-

import asyncio
import random
import time
from vk_api.keyboard import VkKeyboard

import cfg
import db
from constants import WORDS_POINT
from utils import num_split, get_num_ending, get_example_desc, get_examples_amount


async def start_new_round(game, ts):
    if game['level_set'] == 4:
        level = random.randint(1, 12)
    else:
        level = random.randint(game['level_set'] * 4 - 3, game['level_set'] * 4)

    example = random.choice(cfg.examples[level])

    await db.game_start_new_round(game['id'], ts, example['answer'])

    cfg.vk.send(
        game['id'],
        get_example_desc(level),
        attach=f"photo-{cfg.config['group_id']}_{example['photo_id']}"
    )


async def game_handler():
    while True:
        ts = int(time.time())

        for game in await db.get_pending_games(ts):
            if len(game['players']) >= 2:
                await db.start_game(game['id'], ts)

                cfg.vk.send(
                    game['id'],
                    f"Игра начинается...\n\nБанк: {num_split(game['bet'] * len(game['players']))} VK Coin\n"
                    f"Кол-во примеров: {get_examples_amount(len(game['players']))}",
                    VkKeyboard.get_empty_keyboard()
                )

            else:
                await db.cancel_game(game['id'])

                cfg.vk.send(
                    game['id'],
                    'Никто не присоединился к игре, игра отменяется...',
                    VkKeyboard.get_empty_keyboard()
                )

        for game in await db.get_games_to_resume(ts):
            examples_amount = get_examples_amount(len(game['players']))
            if game['round'] >= examples_amount:
                top = [{'id': int(k), 'points': v} for k, v in
                       sorted(game['players'].items(), key=lambda i: i[1], reverse=True)
                       ]

                if top[0]['points'] != top[1]['points'] or game['round'] == examples_amount + 3:
                    await db.finish_game(game['id'], top[0]['id'])

                    bank = game['bet'] * len(game['players'])
                    top_str = []
                    user_links = cfg.vk.get_user_links([i['id'] for i in top])

                    for index, i in enumerate(top):
                        top_str.append(
                            f"\n{index + 1}. {user_links[i['id']]} — {num_split(i['points'])} {get_num_ending(i['points'], WORDS_POINT)}"
                            f"{(', +' + num_split(i['points']) + ' опыта') if i['points'] > 0 else ''}"
                        )

                    cfg.vk.send(
                        game['id'],
                        f"Результаты:{''.join(top_str)}\n\n"
                        f"Побеждает {user_links[top[0]['id']]} и забирает приз в размере {num_split(bank)} VK Coin!"
                    )

                else:
                    await start_new_round(game, ts)

                    cfg.vk.send(game['id'], 'Дополнительный раунд!')

            else:
                await start_new_round(game, ts)

        for game in await db.get_games_to_skip_round(ts):
            await db.game_end_round(game['id'], ts)

            cfg.vk.send(
                game['id'],
                f"Никто не ответил верно, правильный ответ: {game['answer']}"
            )

        await asyncio.sleep(0.25)
