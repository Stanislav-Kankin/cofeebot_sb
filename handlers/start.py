from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from utils.states import RegistrationStates
from utils.keyboards import get_main_menu_inline, get_admin_main_inline
from config import Config
import logging

logger = logging.getLogger(__name__)

router = Router()
db = Database()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Очищаем состояние
    await state.clear()
    
    # Добавляем/обновляем пользователя в базе
    db.add_user(user_id, username)
    
    # Получаем данные пользователя
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Ошибка при загрузке профиля. Попробуй позже.")
        return
    
    # Проверяем, заполнен ли профиль
    if not user.get('profile_completed'):
        await message.answer(
            "👋 Привет! Я бот для Random Coffee - помогу найти интересных собеседников!\n\n"
            "Давай заполним твой профиль, это займет всего 2 минуты.\n\n"
            "Как тебя зовут?"
        )
        await state.set_state(RegistrationStates.waiting_name)
    else:
        # Обновляем last_active
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (message.date.isoformat(), user_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating last_active: {e}")
        
        # ПОСЛЕ заполнения профиля показываем обычное меню для всех
        await message.answer(
            "🎉 С возвращением! Выбери действие:",
            reply_markup=get_main_menu_inline()
        )

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Отдельная команда для админ-панели"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        await message.answer("❌ Нет доступа к админ-панели")
        return
    
    # Проверяем, заполнен ли профиль админа
    user = db.get_user(user_id)
    if not user or not user.get('profile_completed'):
        await message.answer("❌ Сначала заполни свой профиль через /start")
        return
    
    await message.answer(
        "👋 Добро пожаловать в панель администратора!",
        reply_markup=get_admin_main_inline()
    )

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    user_id = callback.from_user.id
    
    # Обновляем last_active
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (callback.message.date.isoformat(), user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating last_active: {e}")
    
    # Проверяем права админа для отображения правильного меню
    if user_id in Config.ADMIN_IDS:
        await callback.message.edit_text(
            "👋 Добро пожаловать в панель администратора!",
            reply_markup=get_admin_main_inline()
        )
    else:
        await callback.message.edit_text(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_inline()
        )
    await callback.answer()