from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from config import Config
import logging
import json
import asyncio
import csv
import io
from datetime import datetime

from database import Database
from utils.keyboards import (
    get_match_decision_inline, 
    get_chat_created_inline, 
    get_match_success_inline,
    get_main_menu_inline,
    get_admin_management_inline
)
from services.matcher import MatchMaker

router = Router()
db = Database()
match_maker = MatchMaker(db)

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS


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
            f"🔗 Предпочтительный канал для связи: {partner.get('contact_preference', 'не указаны')}\n\n"
            f"Изучите информацию и LinkedIn профиль, затем примите решение:"
        )
        
        await bot.send_message(
            user_id,
            message_text,
            reply_markup=get_match_decision_inline(match_id, partner.get('linkedin_url'))
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
                   u1.username as user1_username, u2.username as user2_username,
                   u1.linkedin_url as user1_linkedin, u2.linkedin_url as user2_linkedin
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

async def notify_both_accepted(bot: Bot, match_id: int):
    """Уведомляет обоих пользователей о взаимном принятии мэтча"""
    match = db.get_match(match_id)
    if not match:
        return
    
    user1_id = match['user1_id']
    user2_id = match['user2_id']
    
    # Создаем эффект салюта
    celebration_text = "🎉 🎊 🎉 🎊 🎉\n\n"
    
    message_text = (
        f"{celebration_text}"
        f"💫 Отлично! Оба участника приняли мэтч!\n\n"
        f"👤 Вы познакомились с {match['user2_name'] if user1_id else match['user1_name']}\n\n"
        f"Теперь вы можете начать общение! 🚀"
    )
    
    # Отправляем сообщение обоим пользователям
    try:
        await bot.send_message(user1_id, message_text, reply_markup=get_chat_created_inline(user2_id, match['user2_username']))
        await bot.send_message(user2_id, message_text, reply_markup=get_chat_created_inline(user1_id, match['user1_username']))
        
        # Через 30 секунд отправляем запрос об успешности мэтча
        await asyncio.sleep(30)
        
        followup_text = (
            "📊 Как прошло ваше знакомство?\n\n"
            "Пожалуйста, оцените успешность мэтча:"
        )
        
        await bot.send_message(user1_id, followup_text, reply_markup=get_match_success_inline(match_id))
        await bot.send_message(user2_id, followup_text, reply_markup=get_match_success_inline(match_id))
        
    except Exception as e:
        logger.error(f"Error notifying users about mutual acceptance: {e}")

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
                "Новые мэтчи запускаются администратором вручную.",
                reply_markup=get_main_menu_inline()
            )
            await callback.answer()
    else:
        await callback.message.edit_text(
            "Пока нет новых предложений для тебя. 🔍\n\n"
            "Новые мэтчи запускаются администратором вручную. "
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
    
    # Обновляем статус принятия пользователем
    success = db.update_match_acceptance(match_id, user_id, True)
    
    if success:
        # Логируем действие
        db.log_user_action(user_id, "accepted_match", 
                          match_info['user2_id'] if user_id == match_info['user1_id'] else match_info['user1_id'])
        
        # Проверяем, приняли ли оба пользователя
        updated_match = db.get_match(match_id)
        if updated_match and updated_match.get('chat_created'):
            # Оба приняли - уведомляем их
            await callback.message.edit_text(
                "✅ Ты принял приглашение! Ожидаем решения собеседника...\n\n"
                "Как только оба примут мэтч, вы сможете начать общение! 🚀"
            )
            
            # Уведомляем обоих о взаимном принятии
            await notify_both_accepted(bot, match_id)
        else:
            await callback.message.edit_text(
                "✅ Ты принял приглашение! Ожидаем решения собеседника...\n\n"
                "Как только оба примут мэтч, вы сможете начать общение! 🚀"
            )
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

@router.callback_query(F.data.startswith("success_"))
async def match_success(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    db.set_match_success(match_id, True)
    db.log_user_action(user_id, "match_success", match_id)
    
    await callback.message.edit_text(
        "🎉 Отлично! Рады, что мэтч прошел успешно!\n\n"
        "Спасибо за участие в Random Coffee! 💫",
        reply_markup=get_main_menu_inline()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("fail_"))
async def match_fail(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    db.set_match_success(match_id, False)
    db.log_user_action(user_id, "match_fail", match_id)
    
    await callback.message.edit_text(
        "😔 Жаль, что мэтч не удался.\n\n"
        "Не расстраивайся! В следующий раз обязательно повезет! 🍀",
        reply_markup=get_main_menu_inline()
    )
    await callback.answer()

@router.callback_query(F.data == "start_chat")
async def start_chat(callback: CallbackQuery):
    await callback.message.edit_text(
        "💬 Отлично! Приятного общения!\n\n"
        "Не забудьте обменяться контактами и договориться о времени встречи! 🚀",
        reply_markup=get_main_menu_inline()
    )
    await callback.answer()

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