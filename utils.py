# -*- coding: utf-8 -*-

import re
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def clear_msg(s):
    return re.sub(r'^(\[club\d*\|.*] )?', '', s)


def num_split(x):
    return '{0:,}'.format(int(x) if x == int(x) else round(x, 3)).replace(',', ' ')


def get_num_ending(n, words):
    n = n % 100
    if 11 <= n <= 19:
        r = words[2]
    else:
        i = n % 10
        if i == 1:
            r = words[0]
        elif 0 < i < 5:
            r = words[1]
        else:
            r = words[2]

    return r


def get_levels_keyboard(level):
    keyboard = VkKeyboard()

    for i in range(0, level, 1):
        if i % 4 == 0 and i > 0:
            keyboard.add_line()

        keyboard.add_button(f'Ур. {i + 1}', payload={'action': 'level', 'level': i + 1})

    keyboard.add_line()
    keyboard.add_button('Вернуться назад', VkKeyboardColor.PRIMARY, payload={'action': 'menu'})

    return keyboard


def get_example_desc(level):
    if level in (8, 9):
        return 'Решите уравнение:'
    elif level in (11, 12):
        return 'Решите пример и запишите ответ, разделяя косой чертой числитель и знаменатель (например, 2/19):'
    else:
        return 'Решите пример:'


def get_examples_amount(players_amount):
    return min(3 + players_amount * 2, 20)
