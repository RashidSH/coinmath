# -*- coding: utf-8 -*-

import asyncio
import argparse
import json
import os
import progressbar
import vk_api.exceptions
from vkcoin import VKCoin

import cfg
import db
from events import process_events
from game import game_handler
from generate_examples import generate_example
from logger import logger
from vk import VK
from vk_coin import vkc_handler


async def main():
    try:
        with open('config.json', encoding='utf-8') as f:
            cfg.config = json.load(f)

    except FileNotFoundError:
        with open('config.json', 'w') as f:
            json.dump(cfg.config, f, indent=2, ensure_ascii=False)

        os.makedirs('./examples', exist_ok=True)

        print('Файл конфигурации (config.json) создан. Нажмите Enter для выхода...')
        input()
        return

    cfg.vk = VK(cfg.config['token'], logger)

    parser = argparse.ArgumentParser()
    parser.add_argument('--generate', metavar='N', type=int)

    args = parser.parse_args()
    if args.generate:
        amount = args.generate
        level_amount = len(cfg.config['levels'])
        upload = cfg.vk.get_upload()

        print(f'Генерация по {amount} примеров для {level_amount} уровней...')

        with progressbar.ProgressBar(max_value=amount * level_amount) as bar:
            for level in range(1, level_amount + 1, 1):
                examples = []

                for i in range(amount):
                    answer, example, image = generate_example(level)
                    try:
                        photo = upload.photo_messages(image)[0]

                    except vk_api.exceptions.ApiError as ex:
                        logger.error('Ошибка при загрузке картинки на сервер', exc_info=ex)
                        continue

                    else:
                        examples.append({
                            'answer': answer,
                            'example': example,
                            'photo_id': photo['id'],
                        })

                    bar.update((level - 1) * amount + i)

                with open(f'examples/{level}.json', 'w') as f:
                    json.dump(examples, f, separators=(',', ':'))

        print('Примеры успешно сгенерированы и загружены на сервер. Нажмите Enter для выхода...')
        input()
        return

    for level in range(1, len(cfg.config['levels']) + 1, 1):
        try:
            with open(f'examples/{level}.json', encoding='utf-8') as f:
                cfg.examples[level] = json.load(f)

        except FileNotFoundError:
            print('Необходимо сгенерировать примеры (main.py --generate 100). Нажмите Enter для выхода...')
            input()
            return

    await db.init(cfg.config['db_url'])

    cfg.merchant = VKCoin(user_id=cfg.config['vkc_id'], key=cfg.config['vkc_key'])
    cfg.vk.event_handler()

    logger.info('Бот запущен')

    await asyncio.gather(
        cfg.vk.messages_sender(),
        process_events(),
        vkc_handler(cfg.merchant),
        game_handler(),
    )


if __name__ == "__main__":
    asyncio.run(main())
