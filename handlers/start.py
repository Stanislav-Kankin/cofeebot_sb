from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from utils.keyboards import get_main_menu_keyboard
from config import Config

router = Router()
db = Database()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Добавляем пользователя в базу
    db.add_user(user_id, username)
    
    # Проверяем админские права
    if user_id in Config.ADMIN_IDS:
        from .admin import get_admin_keyboard
        await message.answer(
            "👋 Добро пожаловать в панель администратора!",
            reply_markup=get_admin_keyboard()
        )
        return
    
    # Проверяем, заполнен ли профиль
    user = db.get_user(user_id)
    
    if not user or not user.get('profile_completed'):
        await message.answer(
            "👋 Привет! Я бот для Random Coffee - помогу найти интересных собеседников!\n\n"
            "Давай заполним твой профиль, это займет всего 2 минуты.\n\n"
            "Как тебя зовут?"
        )
        from .registration import RegistrationStates
        await state.set_state(RegistrationStates.waiting_name)
    else:
        await message.answer(
            "С возвращением! Что хочешь сделать?",
            reply_markup=get_main_menu_keyboard()
        )

@router.message(F.text == "🔙 В главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )