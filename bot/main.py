import asyncio
import logging
import os
import sys
from pathlib import Path

# Инициализация Django до импорта моделей:
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from django.conf import settings

logging.basicConfig(level=logging.INFO)

from aiogram.client.session.aiohttp import AiohttpSession

session = AiohttpSession(proxy='socks5://127.0.0.1:12334')
bot = Bot(token=settings.BOT_TOKEN, session=session)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f'Привет, {message.from_user.full_name}!\n'
        f'Это тестовый бот проекта leadbot.'
    )

@dp.message(F.text)
async def echo(message: Message):
    await message.answer(f'Ты написал: {message.text}')

async def main():
    print('Бот запущен. Ctrl+C для остановки.')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())