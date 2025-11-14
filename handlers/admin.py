from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from services.matcher import MatchMaker
from utils.states import AdminStates
from utils.keyboards import get_admin_keyboard, get_main_menu_keyboard
from config import Config

router = Router()
db = Database()
match_maker = MatchMaker(db)

def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

@router.message(F.text == "⚙️ Админка")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет доступа к админке")
        return
    
    await message.answer(
        "👨‍💻 Панель администратора",
        reply_markup=get_admin_keyboard()
    )

@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_user_stats()
    
    message_text = (
        "📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
        f"🟢 Активных: {stats.get('active_users', 0)}\n"
        f"📝 Заполненных профилей: {stats.get('completed_profiles', 0)}\n"
        f"💫 Успешных мэтчей: {stats.get('successful_matches', 0)}\n"
    )
    
    await message.answer(message_text)

@router.message(F.text == "🔄 Запустить мэтчинг")
async def run_matching(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("🔄 Запускаю мэтчинг...")
    
    matches_count = match_maker.run_matching_round()
    
    await message.answer(f"✅ Мэтчинг завершен! Создано {matches_count} новых пар.")

@router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "Введите сообщение для рассылки (поддерживается разметка):",
        reply_markup=get_main_menu_keyboard()
    )
    await state.set_state(AdminStates.waiting_broadcast_message)

@router.message(AdminStates.waiting_broadcast_message)
async def send_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.text
    active_users = db.get_all_active_users()
    
    await message.answer(f"📤 Начинаю рассылку для {len(active_users)} пользователей...")
    
    success_count = 0
    from main import bot
    
    for user in active_users:
        try:
            await bot.send_message(user['user_id'], broadcast_text)
            success_count += 1
        except Exception as e:
            continue
    
    await message.answer(f"✅ Рассылка завершена! Доставлено: {success_count}/{len(active_users)}")
    await state.clear()

@router.message(F.text == "👥 Пользователи")
async def show_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    active_users = db.get_all_active_users()
    
    if not active_users:
        await message.answer("Нет активных пользователей")
        return
    
    # Показываем первых 10 пользователей
    users_text = "👥 Последние 10 активных пользователей:\n\n"
    
    for i, user in enumerate(active_users[:10], 1):
        users_text += f"{i}. {user.get('name', 'No name')} (@{user.get('username', 'no username')})\n"
        users_text += f"   🏙 {user.get('city', 'Не указан')} | 📅 {user.get('matches_count', 0)} мэтчей\n\n"
    
    await message.answer(users_text)