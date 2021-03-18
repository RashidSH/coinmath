# -*- coding: utf-8 -*-

import asyncio

import cfg
import db
from logger import logger
from utils import num_split


async def withdraw(user_id: int, amount: float) -> bool:
    try:
        cfg.merchant.send_payment(user_id, amount * 1000, mark_as_merchant=True)
    except Exception as ex:
        logger.warning('Произошла ошибка при переводе VK Coin', exc_info=ex)
    else:
        logger.info(f'Вывод: id{user_id} - {num_split(amount)} VK Coin')
        return True


async def payment_received(user_id: int, amount: float, payload: int) -> None:
    logger.info(f'Пополнение: id{user_id} - {num_split(amount)} VK Coin')

    await db.add_balance(user_id, amount)

    cfg.vk.send(user_id, f'Ваш баланс пополнен на {num_split(amount)} VK Coin!')


async def vkc_handler(merchant):
    while True:
        try:
            await asyncio.sleep(0.5)

            history = merchant.get_transactions(tx=[1])
            last_tr_id = await db.get_setting('last_tr_id')

            for txn in reversed(history):
                if txn['id'] > last_tr_id:
                    await db.set_setting('last_tr_id', txn['id'])
                    await payment_received(txn['from_id'], int(txn['amount']) // 1000, txn['payload'])

        except Exception as ex:
            logger.warning('Произошла ошибка в обработчике переводов VK Coin', exc_info=ex)
            await asyncio.sleep(3)
