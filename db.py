# -*- coding: utf-8 -*-

import asyncpg
import json

from constants import ChatStates

pool = None


async def conn_init(conn):
    await conn.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')


async def init(url):
    global pool
    pool = await asyncpg.create_pool(dsn=url, init=conn_init, min_size=5, max_size=5)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute('''CREATE TABLE IF NOT EXISTS chats (
id INTEGER PRIMARY KEY, state SMALLINT, level_set SMALLINT, bet BIGINT, ts INTEGER, round SMALLINT, players JSONB, answer TEXT
)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS settings (
id INTEGER PRIMARY KEY, last_tr_id INTEGER
)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY, balance BIGINT, level SMALLINT, exp INTEGER, stat_solved INTEGER
)''')

            await conn.execute("INSERT INTO settings VALUES(1, -1) ON CONFLICT (ID) DO NOTHING")


# Пользователи

async def add_user(user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users VALUES($1, 0, 1, 0, 0)",
            user_id
        )


async def get_user(user_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT balance, level, exp, stat_solved FROM users WHERE id = $1",
            user_id
        )


async def add_balance(user_id, amount):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance = balance + $2 WHERE id = $1",
            user_id, amount
        )


async def set_level_data(user_id, level, exp, solved_amount):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET level = $2, exp = $3, stat_solved = stat_solved + $4 WHERE id = $1",
            user_id, level, exp, solved_amount
        )


async def get_top(user_id):
    async with pool.acquire() as conn:
        top = await conn.fetch(
            "SELECT id, level, exp FROM users ORDER BY exp DESC LIMIT 20",
        )

        position = await conn.fetchval(
            "SELECT position FROM(SELECT id, ROW_NUMBER() OVER(ORDER BY exp DESC) AS position FROM users) RESULT WHERE id = $1",
            user_id
        )

        return top, position


# Беседы

async def add_chat(chat_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chats VALUES($1, 0, null, null, null, null, null, null)",
            chat_id
        )


async def get_chat(chat_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT state, level_set, bet, ts, round, players, answer FROM chats WHERE id = $1",
            chat_id
        )


async def set_chat_state(chat_id, new_state):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET state = $2 WHERE id = $1",
            chat_id, new_state
        )


async def set_chat_level_set(chat_id, level_set):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET level_set = $2 WHERE id = $1",
            chat_id, level_set
        )


async def chat_create_game(chat_id, user_id, bet, ts):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET bet = $2, ts = $3, round = 0, players = json_build_object($4::int, 0) WHERE id = $1",
            chat_id, bet, ts, user_id
        )


async def chat_join_game(chat_id, user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET players = players::jsonb || jsonb_build_object($2::int, 0) WHERE id = $1",
            chat_id, user_id
        )


async def chat_answer(chat_id, user_id, new_score):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET players = jsonb_set(players, ARRAY[$2], $3) WHERE id = $1",
            chat_id, str(user_id), new_score
        )


# Игры


async def get_pending_games(ts):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT id, bet, players FROM chats WHERE state = $1 AND ts < $2 - 60",
            ChatStates.WAITING, ts
        )


async def get_games_to_resume(ts):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT id, level_set, bet, round, players FROM chats WHERE state = $1 AND ts < $2 - 3",
            ChatStates.BREAK, ts
        )


async def get_games_to_skip_round(ts):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT id, answer FROM chats WHERE state = $1 AND ts < $2 - 30",
            ChatStates.PLAYING, ts
        )


async def start_game(peer_id, ts):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET state = $2, ts = $3 WHERE id = $1",
            peer_id, ChatStates.BREAK, ts
        )


async def cancel_game(peer_id):
    async with pool.acquire() as conn:
        bet, players = await conn.fetchrow(
            "SELECT bet, players FROM chats WHERE id = $1",
            peer_id
        )

        await conn.execute(
            "UPDATE users SET balance = balance + $2 WHERE id = any($1::int[])",
            [int(i) for i in players], bet
        )

        await conn.execute(
            "UPDATE chats SET state = $2, bet = null, ts = null, players = null WHERE id = $1",
            peer_id, ChatStates.MENU
        )


async def finish_game(peer_id, winner_id):
    async with pool.acquire() as conn:
        bet, players = await conn.fetchrow(
            "SELECT bet, players FROM chats WHERE id = $1",
            peer_id
        )

        await conn.execute(
            "UPDATE users SET balance = balance + $2 WHERE id = $1",
            winner_id, bet * len(players)
        )

        await conn.execute(
            "UPDATE chats SET state = $2, level_set = null, bet = null, ts = null, round = null, players = null, answer = null WHERE id = $1",
            peer_id, ChatStates.MENU
        )


async def game_end_round(peer_id, ts):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET state = $2, ts = $3, answer = null WHERE id = $1",
            peer_id, ChatStates.BREAK, ts
        )


async def game_start_new_round(peer_id, ts, answer):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE chats SET state = $2, ts = $3, round = round + 1, answer = $4 WHERE id = $1",
            peer_id, ChatStates.PLAYING, ts, str(answer)
        )


# Глобальные переменные

async def get_setting(key):
    async with pool.acquire() as conn:
        return await conn.fetchval(
            f"SELECT {key} FROM settings WHERE id = 1",
        )


async def set_setting(key, value):
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE settings SET {key} = $1 WHERE id = 1",
            value
        )
