# -*- coding: utf-8 -*-

import asyncio
import collections
import functools
import json
import time
from typing import List, Optional
from threading import Thread
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from vk_api.execute import VkFunction
from vk_api.upload import VkUpload
from vk_api.utils import get_random_id

API_VERSION = '5.130'


vk_execute = VkFunction(
    args=('methods',),
    clean_args=('methods',),
    code='''
    %(methods)s;
    return 1;
''')


def threaded(fn):
    def wrapper(*args, **kwargs):
        Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()

    return wrapper


class VKMessage:
    __slots__ = ('id', 'peer_id', 'user_id', 'text', 'payload', 'reply')

    def __init__(self, raw: dict, vk: 'VK') -> None:
        self.id = raw['id']
        self.peer_id = raw['peer_id']
        self.user_id = raw['from_id']
        self.text = raw['text']
        self.payload = json.loads(raw['payload']) if 'payload' in raw else None

        self.reply = functools.partial(vk.send, self.peer_id)


class VK:
    __slots__ = ('vk', 'logger', 'event_queue', 'msg_queue', 'user_cache', 'group_id')

    def __init__(self, token: str, logger) -> None:
        self.vk = VkApi(token=token, api_version=API_VERSION)
        self.logger = logger

        self.event_queue = collections.deque()
        self.msg_queue = []
        self.user_cache = {}

        self.group_id = self.method('groups.getById')[0]['id']

        self.init_group_settings()

    def method(self, method: str, args: dict = None) -> dict:
        return self.vk.method(method, args)

    def send(self, peer_id: int, message: str, keyboard=None, attach=None, sticker=None, disable_mentions=True) -> None:
        if 4000 < len(message) < 100000 and (not attach) and (not sticker):
            for message_part in [message[j:j + 4000] for j in range(0, len(message), 4000)]:
                self.msg_queue.append({'peer_id': peer_id, 'message': message_part, 'random_id': get_random_id(), 'disable_mentions': disable_mentions,
                                       'keyboard': keyboard})

        else:
            self.msg_queue.append({'peer_id': peer_id, 'message': message, 'random_id': get_random_id(), 'disable_mentions': disable_mentions,
                                   'keyboard': keyboard, 'attachment': attach, 'sticker_id': sticker})

    def send_multiple(self, peer_ids: List[int], message: str, keyboard=None, disable_mentions=True) -> None:
        self.msg_queue.append({'peer_ids': peer_ids, 'message': message, 'random_id': get_random_id(), 'disable_mentions': disable_mentions,
                               'keyboard': keyboard})

    def get_user_link(self, target_id: int, name_case: str = 'nom') -> str:
        if target_id not in self.user_cache and target_id != 0:
            if target_id < 0:
                self.user_cache[target_id] = self.method('groups.getById', {'group_id': -target_id})[0]

            else:
                self.user_cache[target_id] = self.method('users.get', {'user_ids': target_id, 'name_case': name_case})[0]

        if target_id < 0:
            return ''.join(['[id', str(target_id), '|', self.user_cache[target_id]['first_name'], ']'])

        elif target_id == 0:
            return '@id0'

        else:
            self.user_cache[target_id] = self.method('users.get', {'user_ids': target_id, 'name_case': name_case})[0]
            return f"[id{target_id}|{self.user_cache[target_id]['first_name']}]"

    def get_user_links(self, target_ids: List[int]) -> dict:
        cached = True
        for i in target_ids:
            if i not in self.user_cache:
                cached = False
                break

        if not cached:
            for i in self.method('users.get', {'user_ids': ','.join(list(map(str, target_ids)))}):
                self.user_cache[i['id']] = i

        return {i: f"[id{i}|{self.user_cache[i]['first_name']}]" for i in target_ids}

    def get_target_id(self, s: str) -> Optional[int]:
        r = s.replace('https://', '').replace('vk.com/', '').replace('@id', '').replace('@', '').replace('[', '').replace(']', '')

        if '|' in r:
            r = r.split('|')[0]

        if not r.isdecimal():
            r = self.method('utils.resolveScreenName', {'screen_name': r.replace('-', 'club')})
            if not r:
                return

            if r['type'] == 'user':
                r = r['object_id']
            elif r['type'] == 'group':
                r = -r['object_id']

        return int(r)

    def is_chat_member(self, peer_id: int, user_id: int) -> bool:
        members = self.method('messages.getConversationMembers', {'peer_id': peer_id})['items']
        for i in members:
            if i['member_id'] == user_id:
                return True

    def is_chat_admin(self, peer_id: int, user_id: int, check_if_owner: bool = False) -> bool:
        members = self.method('messages.getConversationMembers', {'peer_id': peer_id})['items']
        for i in members:
            if i['member_id'] == user_id and 'is_admin' in i and i['is_admin'] and ((not check_if_owner) or ('is_owner' in i and i['is_owner'])):
                return True

    def get_chat_owner(self, peer_id: int) -> Optional[int]:
        members = self.method('messages.getConversationMembers', {'peer_id': peer_id})['items']
        for i in members:
            if 'is_owner' in i and i['is_owner']:
                return i['member_id']

    def get_upload(self) -> VkUpload:
        return VkUpload(self.vk)

    def init_group_settings(self) -> None:
        self.method('groups.setSettings', {
            'group_id': self.group_id,
            'messages': 1,
            'bots_capabilities': 1,
            'bots_start_button': 1,
            'bots_add_to_chat': 1,
        })

        self.method('groups.setLongPollSettings', {
            'group_id': self.group_id,
            'enabled': 1,
            'api_version': API_VERSION,
            'message_new': 1,
        })

    async def messages_sender(self) -> None:
        while True:
            queue = self.msg_queue[:25]

            if queue:
                self.msg_queue = self.msg_queue[25:]

                try:
                    vk_execute(self.vk, ''.join(('API.messages.send(' + json.dumps(i, ensure_ascii=False, separators=(',', ':')) + ');') for i in queue))
                except Exception as ex:
                    self.logger.warning('Произошла ошибка при отправке сообщений', exc_info=ex)

            await asyncio.sleep(0.05)

    @threaded
    def event_handler(self) -> None:
        convs = self.method('messages.getConversations', {'count': 200, 'filter': 'unanswered'})['items']
        for i in convs:
            self.event_queue.append(VKMessage(i['last_message'], self))

        lp = VkBotLongPoll(self.vk, self.group_id)

        while True:
            try:
                for event in lp.check():
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        self.event_queue.append(VKMessage(event.raw['object']['message'], self))

                    else:
                        self.event_queue.append(event)

            except Exception as ex:
                self.logger.warning('Произошла ошибка в LongPoll', exc_info=ex)
                time.sleep(3)
