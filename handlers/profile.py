from aiogram import Router, F
from aiogram.types import Message

from database import Database
from utils.keyboards import get_main_menu_keyboard

router = Router()
db = Database()

@router.message(F.text == "📊 Мой профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user or not user.get('profile_completed'):
        await message.answer(
            "Профиль не заполнен. Используй /start для регистрации",
            reply_markup=get_main_menu_keyboard()
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
    
    await message.answer(profile_text)

@router.message(F.text == "📈 Статистика")
async def show_user_stats(message: Message):
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
    
    await message.answer(stats_text)