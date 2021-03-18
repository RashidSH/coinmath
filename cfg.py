# -*- coding: utf-8 -*-

from state import State

config = {
    'group_domain': 'abc123',
    'group_id': 123,
    'token': 'abc123',
    'vkc_id': 123,
    'vkc_key': 'abc123',
    'db_url': 'postgres://user:password@hostname:port/database-name',
    'levels': [
        {'exp': 0, 'reward': 20},
        {'exp': 1, 'reward': 24},
        {'exp': 10, 'reward': 28},
        {'exp': 40, 'reward': 32},
        {'exp': 140, 'reward': 35},
        {'exp': 270, 'reward': 40},
        {'exp': 450, 'reward': 45},
        {'exp': 630, 'reward': 50},
        {'exp': 820, 'reward': 55},
        {'exp': 1050, 'reward': 60},
        {'exp': 1440, 'reward': 65},
        {'exp': 1960, 'reward': 70},
    ],
}

examples = {}
merchant = None
state = State('menu')
vk = None
