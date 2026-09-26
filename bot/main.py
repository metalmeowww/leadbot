import asyncio
import logging
import os
import re
import sys
from pathlib import Path

# Инициализация Django до импорта моделей:
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from django.conf import settings

from leads.models import Business, Lead

logging.basicConfig(level=logging.INFO)

API_SERVER = TelegramAPIServer.from_base('https://tg-proxy.flafy3290.workers.dev')
session = AiohttpSession(api=API_SERVER)
bot = Bot(token=settings.BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

class LeadForm(StatesGroup):
    """Состояния опроса. Используем одно динамическое состояние."""
    answering = State()

# Клавиатуры

def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню внизу экрана."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📝 Записаться')],
            [KeyboardButton(text='ℹ️ О нас'), KeyboardButton(text='📞 Контакты')],
        ],
        resize_keyboard=True,
    )

def question_keyboard(question: dict) -> ReplyKeyboardMarkup | None:
    """Если у вопроса есть варианты - показать их кнопками."""
    options = question.get('options') or []
    if not options:
        return None
    buttons = [[KeyboardButton(text=opt)] for opt in options]
    buttons.append([KeyboardButton(text='❌ Отмена')])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Валидация

SKIP_WORDS = {'-', 'нет', 'пропустить', 'skip', 'no', 'нет комментариев'}

def validate_phone(text: str) -> bool:
    """Проверяет, что телефон содержит только цифры и допустимые символы, и минимум 10 цифр"""
    cleaned = re.sub(r'[\s\-\(\)\+]', '', text)
    if not cleaned.isdigit():
        return False
    return len(cleaned) >= 10

def validate_answer(field_name: str, text: str, is_required: bool) -> tuple[bool, str]:
    """Возвращает (валидно, сообщение_об_ошибке)."""
    if not is_required and text.strip().lower() in SKIP_WORDS:
        return True, ''
    if field_name == 'phone':
        if not validate_phone(text):
            return False, 'Похоже, это не телефон. Введите номер в формате +7 900 123-45-67.'
    if field_name == 'name':
        if len(text) > 100:
            return False, 'Слишком длинное имя. Максимум 100 символов.'
        if text.strip().isdigit():
            return False, 'Имя не может состоять только из цифр.'
    return True, ''

# Хелперы
async def get_business() -> Business | None:
    """Пока берём первый активный бизнес. Позже сделаем по ссылке."""
    return await Business.objects.filter(is_active=True).afirst()

async def ask_question(message: Message, question: dict):
    """Отправляет вопрос. Если есть варианты - с кнопками."""
    kb = question_keyboard(question)
    if kb:
        await message.answer(question['text'], reply_markup=kb)
    else:
        await message.answer(question['text'])

async def start_survey(message: Message, state: FSMContext):
    """Запускает опрос: собирает вопросы и задаёт первый."""
    business = await get_business()
    if not business:
        await message.answer('Извините, бот временно не настроен.')
        return

    questions = []
    async for q in business.questions.all():
        questions.append({
            'id': q.id,
            'text': q.text,
            'field_name': q.field_name,
            'is_required': q.is_required,
            'options': q.options or [],
        })

    if not questions:
        await message.answer('Бот не настроен: нет вопросов.')
        return

    await state.set_state(LeadForm.answering)
    await state.update_data(
        business_id=business.id,
        questions=questions,
        index=0,
        answers={},
    )

    await message.answer(business.greeting)
    await ask_question(message, questions[0])

# Команды и кнопки

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие + главное меню."""
    await state.clear()
    await message.answer(
        f'Здравствуйте, {message.from_user.first_name}!\n'
        f'Нажмите кнопку ниже, чтобы записаться.',
        reply_markup=main_menu(),
    )

@dp.message(F.text == '📝 Записаться')
async def btn_signup(message: Message, state: FSMContext):
    await start_survey(message, state)

@dp.message(F.text == 'ℹ️ О нас')
async def btn_about(message: Message):
    business = await get_business()
    if not business:
        await message.answer('Информация временно недоступна.')
        return
    await message.answer(business.about_text)

@dp.message(F.text == '📞 Контакты')
async def btn_contacts(message: Message):
    business = await get_business()
    if not business:
        await message.answer('Контакты временно недоступны.')
        return
    await message.answer(business.contacts_text)

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

@dp.message(Command('cancel'))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Опрос отменён.', reply_markup=main_menu())

@dp.message(F.text == '❌ Отмена')
async def btn_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Опрос отменён.', reply_markup=main_menu())

# Опрос

@dp.message(LeadForm.answering, F.text)
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data['questions']
    index = data['index']
    answers = data['answers']

    # Сохраняем ответ на текущий вопрос
    current = questions[index]
    is_valid, error_message = validate_answer(
        current['field_name'], message.text, current['is_required']
    )

    if not is_valid:
        await message.answer(error_message)
        return

    if not current['is_required'] and message.text.strip().lower() in SKIP_WORDS:
        answers[current['field_name']] = ''
    else:
        answers[current['field_name']] = message.text

    index += 1

    business = await Business.objects.aget(id=data['business_id'])

    if index >= len(questions):
        await Lead.objects.acreate(
            business=business,
            client_telegram_id=message.from_user.id,
            client_username=message.from_user.username or '',
            name=answers.get('name', ''),
            phone=answers.get('phone', ''),
            service=answers.get('service', ''),
            message=answers.get('message', ''),
            budget=answers.get('budget', ''),
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

        await state.clear()
        await message.answer(
            business.thank_you_text,
            reply_markup=main_menu(),
        )
        return

    await state.update_data(index=index, answers=answers)
    await ask_question(message, questions[index])

async def main():
    print('Бот запущен. Ctrl+C для остановки.')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())