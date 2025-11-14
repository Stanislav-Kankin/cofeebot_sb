from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
import logging

from database import Database
from utils.keyboards import get_accept_match_keyboard, get_contact_keyboard, get_main_menu_keyboard
from services.matcher import MatchMaker

router = Router()
db = Database()
match_maker = MatchMaker(db)

logger = logging.getLogger(__name__)

@router.message(F.text == "🔍 Найти собеседника")
async def find_match(message: Message):
    user_id = message.from_user.id
    
    # Проверяем заполнен ли профиль
    user = db.get_user(user_id)
    if not user or not user.get('profile_completed'):
        await message.answer(
            "Сначала заполни свой профиль через команду /start",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Ищем pending мэтчи
    pending_matches = db.get_pending_matches(user_id)
    
    if pending_matches:
        for match in pending_matches:
            await send_match_proposal(message, match)
    else:
        await message.answer(
            "Пока нет новых предложений для тебя. 🔍\n\n"
            "Новые мэтчи обычно появляются 1-2 раза в неделю. "
            "Проверяй позже или убедись, что твой профиль заполнен полностью.",
            reply_markup=get_main_menu_keyboard()
        )

async def send_match_proposal(message: Message, match: dict):
    """Отправляет предложение мэтча пользователю"""
    user_id = message.from_user.id
    
    # Определяем кто собеседник
    if match['user1_id'] == user_id:
        partner_id = match['user2_id']
    else:
        partner_id = match['user1_id']
    
    partner = db.get_user(partner_id)
    
    if not partner:
        return
    
    common_interests = match.get('common_interests', '[]')
    try:
        import json
        interests_list = json.loads(common_interests)
        common_text = ", ".join(interests_list) if interests_list else "общие интересы"
    except:
        common_text = "общие интересы"
    
    message_text = (
        f"🎯 Найден потенциальный собеседник!\n\n"
        f"👤 Имя: {partner['name']}\n"
        f"🏙 Город: {partner.get('city', 'не указан')}\n"
        f"💼 Профессия: {partner.get('profession', 'не указана')}\n"
        f"🎯 Цели: {partner.get('goals', 'не указаны')}\n"
        f"📝 О себе: {partner.get('about', 'не указано')}\n\n"
        f"✨ Совпадения: {common_text}\n"
        f"🔗 Контакты: {partner.get('contact_preference', 'не указаны')}\n\n"
        f"Хочешь пообщаться с этим человеком?"
    )
    
    await message.answer(
        message_text,
        reply_markup=get_accept_match_keyboard(match['id'])
    )

@router.callback_query(F.data.startswith("accept_"))
async def accept_match(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Обновляем статус мэтча
    success = db.update_match_status(match_id, "accepted")
    
    if success:
        # Получаем информацию о мэтче
        match = db.get_pending_matches(user_id)
        match_info = next((m for m in match if m['id'] == match_id), None)
        
        if match_info:
            # Определяем партнера
            if match_info['user1_id'] == user_id:
                partner_id = match_info['user2_id']
            else:
                partner_id = match_info['user1_id']
            
            partner = db.get_user(partner_id)
            
            if partner:
                # Логируем действие
                db.log_user_action(user_id, "accepted_match", partner_id)
                
                await callback.message.edit_text(
                    f"🎉 Отлично! Ты принял приглашение от {partner['name']}!\n\n"
                    f"Можешь написать собеседнику прямо сейчас:",
                    reply_markup=get_contact_keyboard(partner_id)
                )
                
                # Уведомляем партнера
                from main import bot
                try:
                    await bot.send_message(
                        partner_id,
                        f"🎉 {callback.from_user.first_name} принял(а) твое приглашение на общение!\n\n"
                        f"Можешь написать собеседнику:",
                        reply_markup=get_contact_keyboard(user_id)
                    )
                except Exception as e:
                    logger.error(f"Error notifying partner: {e}")
    
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject_match(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[1])
    
    db.update_match_status(match_id, "rejected")
    await callback.message.edit_text("❌ Хорошо, предложение отклонено. Жди следующих мэтчей!")
    await callback.answer()

@router.callback_query(F.data == "contact_confirmed")
async def confirm_contact(callback: CallbackQuery):
    await callback.message.edit_text(
        "✅ Отлично! Приятного общения! 🎉\n\n"
        "Не забудь через несколько дней проверить новые предложения!"
    )
    db.log_user_action(callback.from_user.id, "contact_confirmed")
    await callback.answer()