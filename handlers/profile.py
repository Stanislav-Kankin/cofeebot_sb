from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from utils.keyboards import get_profile_actions_inline, get_main_menu_inline, get_edit_profile_inline, get_settings_inline
from utils.states import RegistrationStates

router = Router()
db = Database()

@router.callback_query(F.data == "my_profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user or not user.get('profile_completed'):
        await callback.message.edit_text(
            "Профиль не заполнен. Используй /start для регистрации",
            reply_markup=get_main_menu_inline()
        )
        return
    
    profile_text = (
        f"👤 Твой профиль:\n\n"
        f"📝 Имя: {user.get('name', 'Не указано')}\n"
        f"🎂 Возраст: {user.get('age', 'Не указан')}\n"
        f"🏙 Город: {user.get('city', 'Не указан')}\n"
        f"💼 Профессия: {user.get('profession', 'Не указана')}\n"
        f"🎯 Интересы: {user.get('interests', 'Не указаны')}\n"
        f"🎯 Цели: {user.get('goals', 'Не указаны')}\n"
        f"📖 О себе: {user.get('about', 'Не указано')}\n"
        f"📞 Контакты: {user.get('contact_preference', 'Не указаны')}\n\n"
        f"💫 Успешных мэтчей: {user.get('matches_count', 0)}\n"
    )
    
    await callback.message.edit_text(
        profile_text,
        reply_markup=get_profile_actions_inline()
    )
    await callback.answer()

@router.callback_query(F.data == "my_stats")
async def show_user_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("Профиль не найден")
        return
    
    stats_text = (
        f"📈 Твоя статистика:\n\n"
        f"💫 Всего мэтчей: {user.get('matches_count', 0)}\n"
        f"📅 В системе с: {user.get('registration_date', 'Неизвестно')[:10]}\n"
        f"🟢 Статус: {'Активен' if user.get('is_active') else 'Неактивен'}\n\n"
        f"Продолжай участвовать в мэтчинге! 🚀"
    )
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_main_menu_inline()
    )
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    """Команда для перезаполнения профиля"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start")
        return
    
    await message.answer(
        "🔄 Начинаем заполнение профиля заново.\n\n"
        "Как тебя зовут?"
    )
    await state.set_state(RegistrationStates.waiting_name)


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "✏️ Что хочешь изменить в профиле?",
        reply_markup=get_edit_profile_inline()
    )
    await callback.answer()

@router.message(F.text == "📊 Мой профиль")
async def show_profile_message(message: Message):
    """Обработчик для reply кнопки"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user or not user.get('profile_completed'):
        await message.answer(
            "Профиль не заполнен. Используй /start для регистрации",
            reply_markup=get_main_menu_inline()
        )
        return
    
    profile_text = (
        f"👤 Твой профиль:\n\n"
        f"📝 Имя: {user.get('name', 'Не указано')}\n"
        f"🎂 Возраст: {user.get('age', 'Не указан')}\n"
        f"🏙 Город: {user.get('city', 'Не указан')}\n"
        f"💼 Профессия: {user.get('profession', 'Не указана')}\n"
        f"🎯 Интересы: {user.get('interests', 'Не указаны')}\n"
        f"🎯 Цели: {user.get('goals', 'Не указаны')}\n"
        f"📖 О себе: {user.get('about', 'Не указано')}\n"
        f"📞 Контакты: {user.get('contact_preference', 'Не указаны')}\n\n"
        f"💫 Успешных мэтчей: {user.get('matches_count', 0)}\n"
    )
    
    await message.answer(
        profile_text,
        reply_markup=get_profile_actions_inline()
    )

@router.message(F.text == "📈 Статистика")
async def show_user_stats_message(message: Message):
    """Обработчик для reply кнопки"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    stats_text = (
        f"📈 Твоя статистика:\n\n"
        f"💫 Всего мэтчей: {user.get('matches_count', 0)}\n"
        f"📅 В системе с: {user.get('registration_date', 'Неизвестно')[:10]}\n"
        f"🟢 Статус: {'Активен' if user.get('is_active') else 'Неактивен'}\n\n"
        f"Продолжай участвовать в мэтчинге! 🚀"
    )
    
    await message.answer(
        stats_text,
        reply_markup=get_main_menu_inline()
    )


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Показ настроек пользователя"""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("Профиль не найден")
        return
    
    settings_text = (
        "⚙️ Настройки профиля\n\n"
        f"👤 Имя: {user.get('name', 'Не указано')}\n"
        f"📧 Контакты: {user.get('contact_preference', 'Не указаны')}\n"
        f"🟢 Статус: {'Активен' if user.get('is_active') else 'Неактивен'}\n\n"
        "Выбери действие:"
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_inline()
    )
    await callback.answer()

@router.message(Command("check_profile"))
async def check_profile_status(message: Message):
    """Проверка статуса профиля"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Ты не зарегистрирован в системе. Используй /start")
        return
    
    if user.get('profile_completed'):
        profile_info = (
            f"✅ Твой профиль заполнен!\n\n"
            f"👤 Имя: {user.get('name', 'Не указано')}\n"
            f"📅 Зарегистрирован: {user.get('registration_date', 'Неизвестно')[:10]}\n"
            f"🟢 Статус: {'Активен' if user.get('is_active') else 'Неактивен'}\n\n"
            f"Используй /profile чтобы перезаполнить профиль"
        )
    else:
        profile_info = (
            f"❌ Твой профиль не заполнен.\n\n"
            f"Чтобы заполнить профиль, используй:\n"
            f"• /start - начать заполнение\n"
            f"• /profile - перезаполнить профиль"
        )
    
    await message.answer(profile_info)

@router.callback_query(F.data == "toggle_active")
async def toggle_active(callback: CallbackQuery):
    """Включение/выключение активности"""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("Профиль не найден")
        return
    
    new_status = not user.get('is_active', True)
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = ? WHERE user_id = ?",
            (new_status, user_id)
        )
        conn.commit()
        conn.close()
        
        status_text = "неактивен" if new_status else "активен"
        await callback.answer(f"Статус изменен: теперь ты {status_text}")
        
        # Обновляем сообщение
        await show_settings(callback)
    except Exception as e:
        await callback.answer("Ошибка при изменении статуса")