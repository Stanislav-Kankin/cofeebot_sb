from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
import json

from database import Database
from utils.keyboards import get_accept_match_inline, get_contact_inline, get_main_menu_inline
from services.matcher import MatchMaker

router = Router()
db = Database()
match_maker = MatchMaker(db)

logger = logging.getLogger(__name__)

async def send_match_proposal(bot: Bot, user_id: int, partner: dict, match_id: int):
    """Отправляет предложение мэтча пользователю"""
    try:
        # Получаем полную информацию о мэтче для common_interests
        match_info = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT common_interests, is_forced FROM matches WHERE id = ?
            ''', (match_id,))
            row = cursor.fetchone()
            if row:
                match_info = {
                    'common_interests': row[0],
                    'is_forced': bool(row[1])
                }
            conn.close()
        except Exception as e:
            logger.error(f"Error getting match info: {e}")
        
        common_text = "случайное знакомство"
        if match_info and match_info['common_interests']:
            try:
                common_interests = json.loads(match_info['common_interests'])
                if common_interests and common_interests != ["случайное знакомство"]:
                    common_text = ", ".join(common_interests)
            except:
                pass
        
        forced_text = " 🎯" if match_info and match_info.get('is_forced') else ""
        
        message_text = (
            f"🎯 Найден потенциальный собеседник{forced_text}!\n\n"
            f"👤 Имя: {partner['name']}\n"
            f"🏙 Город: {partner.get('city', 'не указан')}\n"
            f"💼 Профессия: {partner.get('profession', 'не указана')}\n"
            f"🎯 Цели: {partner.get('goals', 'не указаны')}\n"
            f"📝 О себе: {partner.get('about', 'не указано')}\n\n"
            f"✨ Совпадения: {common_text}\n"
            f"🔗 Контакты: {partner.get('contact_preference', 'не указаны')}\n\n"
            f"Хочешь пообщаться с этим человеком?"
        )
        
        await bot.send_message(
            user_id,
            message_text,
            reply_markup=get_accept_match_inline(match_id)
        )
        return True
    except Exception as e:
        logger.error(f"Error sending match proposal to {user_id}: {e}")
        return False

def get_match_info_from_db(match_id: int):
    """Получает информацию о мэтче напрямую из базы"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, u1.name as user1_name, u2.name as user2_name,
                   u1.username as user1_username, u2.username as user2_username
            FROM matches m
            LEFT JOIN users u1 ON m.user1_id = u1.user_id
            LEFT JOIN users u2 ON m.user2_id = u2.user_id
            WHERE m.id = ?
        ''', (match_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    except Exception as e:
        logger.error(f"Error getting match info: {e}")
        return None

@router.message(Command("match"))
async def manual_match(message: Message, bot: Bot):
    """Ручной запуск мэтчинга (для тестирования)"""
    users = db.get_all_active_users()
    
    if len(users) < 2:
        await message.answer("Недостаточно пользователей для мэтчинга")
        return
    
    # Используем существующий метод мэтчинга
    matches_count = match_maker.run_matching_round(force_all=True)
    
    if matches_count > 0:
        # Уведомляем пользователей
        notified_count = 0
        for user in users:
            pending_matches = db.get_pending_matches(user['user_id'])
            if pending_matches:
                try:
                    for match in pending_matches:
                        if match['user1_id'] == user['user_id']:
                            partner_id = match['user2_id']
                        else:
                            partner_id = match['user1_id']
                        
                        partner = db.get_user(partner_id)
                        if partner:
                            success = await send_match_proposal(bot, user['user_id'], partner, match['id'])
                            if success:
                                notified_count += 1
                except Exception as e:
                    logger.error(f"Error notifying user {user['user_id']}: {e}")
        
        await message.answer(f"Мэтчинг завершен! Создано {matches_count} пар, отправлено {notified_count} уведомлений")
    else:
        await message.answer("Не удалось создать пары")

@router.callback_query(F.data == "find_match")
async def find_match(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    
    # Проверяем заполнен ли профиль
    user = db.get_user(user_id)
    if not user or not user.get('profile_completed'):
        await callback.message.edit_text(
            "Сначала заполни свой профиль через команду /start",
            reply_markup=get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Ищем pending мэтчи
    pending_matches = db.get_pending_matches(user_id)
    
    if pending_matches:
        sent_count = 0
        for match in pending_matches:
            # Определяем кто собеседник
            if match['user1_id'] == user_id:
                partner_id = match['user2_id']
            else:
                partner_id = match['user1_id']
            
            partner = db.get_user(partner_id)
            
            if partner:
                success = await send_match_proposal(bot, user_id, partner, match['id'])
                if success:
                    sent_count += 1
        
        if sent_count > 0:
            await callback.answer(f"🔍 Найдено {sent_count} новых предложений!")
        else:
            await callback.message.edit_text(
                "Пока нет новых предложений для тебя. 🔍\n\n"
                "Новые мэтчи обычно появляются 1-2 раза в неделю.",
                reply_markup=get_main_menu_inline()
            )
            await callback.answer()
    else:
        await callback.message.edit_text(
            "Пока нет новых предложений для тебя. 🔍\n\n"
            "Новые мэтчи обычно появляются 1-2 раза в неделю. "
            "Проверяй позже или убедись, что твой профиль заполнен полностью.",
            reply_markup=get_main_menu_inline()
        )
        await callback.answer()

@router.callback_query(F.data.startswith("accept_"))
async def accept_match(callback: CallbackQuery, bot: Bot):
    match_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Сначала получаем информацию о мэтче ДО обновления статуса
    match_info = get_match_info_from_db(match_id)
    
    if not match_info:
        await callback.message.edit_text(
            "❌ Ошибка: информация о мэтче не найдена",
            reply_markup=get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Определяем кто партнер
    if match_info['user1_id'] == user_id:
        partner_id = match_info['user2_id']
    else:
        partner_id = match_info['user1_id']
    
    partner = db.get_user(partner_id)
    
    if not partner:
        await callback.message.edit_text(
            "❌ Ошибка: информация о собеседнике не найдена",
            reply_markup=get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Обновляем статус мэтча
    success = db.update_match_status(match_id, "accepted")
    
    if success:
        # Логируем действие
        db.log_user_action(user_id, "accepted_match", partner_id)
        
        await callback.message.edit_text(
            f"🎉 Отлично! Ты принял приглашение от {partner['name']}!\n\n"
            f"Можешь написать собеседнику прямо сейчас:",
            reply_markup=get_contact_inline(partner_id, partner.get('username'))
        )
        
        # Уведомляем партнера
        try:
            await bot.send_message(
                partner_id,
                f"🎉 {callback.from_user.first_name} принял(а) твое приглашение на общение!\n\n"
                f"Можешь написать собеседнику:",
                reply_markup=get_contact_inline(user_id, callback.from_user.username)
            )
        except Exception as e:
            logger.error(f"Error notifying partner: {e}")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при принятии мэтча",
            reply_markup=get_main_menu_inline()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject_match(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[1])
    
    db.update_match_status(match_id, "rejected")
    await callback.message.edit_text(
        "❌ Хорошо, предложение отклонено. Жди следующих мэтчей!",
        reply_markup=get_main_menu_inline()
    )
    await callback.answer()

@router.callback_query(F.data == "contact_confirmed")
async def confirm_contact(callback: CallbackQuery):
    await callback.message.edit_text(
        "✅ Отлично! Приятного общения! 🎉\n\n"
        "Не забудь через несколько дней проверить новые предложения!",
        reply_markup=get_main_menu_inline()
    )
    db.log_user_action(callback.from_user.id, "contact_confirmed")
    await callback.answer()

@router.callback_query(F.data == "new_match")
async def request_new_match(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 Ищу нового собеседника...",
        reply_markup=get_main_menu_inline()
    )
    await callback.answer("Скоро появятся новые предложения!")

@router.message(Command("status"))
async def check_status(message: Message):
    """Проверка статуса пользователя"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Ты не зарегистрирован. Используй /start")
        return
    
    if not user.get('profile_completed'):
        await message.answer("❌ Профиль не заполнен. Заверши регистрацию через /start")
        return
    
    pending_matches = db.get_pending_matches(user_id)
    stats = db.get_user_stats()
    
    status_text = (
        f"📊 Твой статус:\n\n"
        f"👤 Имя: {user.get('name', 'Не указано')}\n"
        f"💫 Успешных мэтчей: {user.get('matches_count', 0)}\n"
        f"🔍 Ожидающих предложений: {len(pending_matches)}\n\n"
        f"📈 По системе:\n"
        f"• Пользователей: {stats.get('total_users', 0)}\n"
        f"• Активных: {stats.get('active_users', 0)}\n"
        f"• Всего мэтчей: {stats.get('successful_matches', 0)}\n\n"
    )
    
    if pending_matches:
        status_text += "🎯 У тебя есть новые предложения! Нажми '🔍 Найти собеседника'"
    else:
        status_text += "⏳ Новых предложений пока нет. Жди уведомления!"
    
    await message.answer(status_text)