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
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from django.conf import settings

from leads.models import Business, Lead

logging.basicConfig(level=logging.INFO)


session = AiohttpSession(proxy='socks5://127.0.0.1:12334')
bot = Bot(token=settings.BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

class LeadForm(StatesGroup):
    """Состояния опроса. Используем одно динамическое состояние."""
    answering = State()

async def get_business() -> Business | None:
    """Пока берём первый активный бизнес. Позже сделаем по ссылке."""
    return await Business.objects.filter(is_active=True).afirst()

@dp.message(Command('admin'))
async def cmd_admin(message: Message):
    """Привязывает владельца к бизнесу. Работает только для ADMIN_TELEGRAM_ID."""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        await message.answer('У вас нет доступа к этой команде.')
        return

    business = await get_business()
    if not business:
        await message.answer('Нет активного бизнеса.')
        return

    business.telegram_id = message.from_user.id
    await business.asave()

    await message.answer(
        f'Готово. Теперь уведомления о новых заявках будут приходить сюда.\n'
        f'Бизнес: {business.name}\n'
        f'Ваш Telegram ID: {message.from_user.id}'
    )

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    business = await get_business()
    if not business:
        await message.answer('Извините, бот временно не настроен.')
        return

    # Получаем вопросы полученные по порядку
    questions = []
    async for q in business.questions.all():
        questions.append({'id': q.id, 'text': q.text, 'field_name': q.field_name})

    if not questions:
        await message.answer('Бот не настроен: нет вопросов.')
        return

    # Сохраняем в состояние список вопросов и индекс текущего
    await state.set_state(LeadForm.answering)
    await state.update_data(
        business_id=business.id,
        questions=questions,
        index=0,
        answers={},
    )

    # Отправляем первое приветствие и первый вопрос
    await message.answer(business.greeting)
    await message.answer(questions[0]['text'])

@dp.message(LeadForm.answering, F.text)
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data['questions']
    index = data['index']
    answers = data['answers']

    # Сохраняем ответ на текущий вопрос
    current = questions[index]
    answers[current['field_name']] = message.text

    index += 1

    business = await Business.objects.aget(id=data['business_id'])

    #Если вопросы закончились - сохраняем заявку
    if index >= len(questions):
        
        await Lead.objects.acreate(
            business=business,
            client_telegram_id=message.from_user.id,
            client_username=message.from_user.username or '',
            name=answers.get('name', ''),
            phone=answers.get('phone', ''),
            service=answers.get('service', ''),
            message=answers.get('message', ''),
            budget=answers.get('budget', '')
        )

        if business.telegram_id:
            await bot.send_message(
                business.telegram_id,
                f'🔔 Новая заявка!\n\n'
                f'Имя: {answers.get("name", "—")}\n'
                f'Телефон: {answers.get("phone", "—")}\n'
                f'Услуга: {answers.get("service", "—")}\n'
                f'Комментарий: {answers.get("message", "—")}\n\n'
                f'Клиент: @{message.from_user.username or "без_username"}'
            )

        await message.answer(
            'Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.'
        )
        await state.clear()
        return

    # Иначе - сохраняем прогресс и задаём следующий вопрос
    await state.update_data(index=index, answers=answers)
    await message.answer(questions[index]['text'])

async def main():
    print('Бот запущен. Ctrl+C для остановки.')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())