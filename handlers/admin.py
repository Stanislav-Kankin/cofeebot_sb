from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

from database import Database
from services.matcher import MatchMaker
from utils.states import AdminStates

from utils.keyboards import (
    get_admin_main_inline, get_admin_matching_inline,
    get_admin_scheduler_inline,
    get_admin_management_inline, get_schedule_date_inline,
    get_main_menu_inline, get_admin_settings_inline,
    get_back_to_admin_inline
)
from config import Config

router = Router()
db = Database()
match_maker = MatchMaker(db)

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

# ===== КОМАНДА /admin =====


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    """Главная админ команда с inline кнопками"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа к админ-панели")
        return

    # Очищаем состояние на всякий случай
    await state.clear()

    # Проверяем, заполнен ли профиль админа
    user = db.get_user(message.from_user.id)
    if not user or not user.get('profile_completed'):
        await message.answer("❌ Сначала заполни свой профиль через /start")
        return

    await message.answer(
        "👨‍💻 Панель администратора Random Coffee\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_inline()
    )

# ===== INLINE ОБРАБОТЧИКИ АДМИН-ПАНЕЛИ =====


@router.callback_query(F.data == "admin_main")
async def admin_main(callback: CallbackQuery, state: FSMContext):
    """Главное меню админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    # Очищаем состояние при возврате в главное меню
    await state.clear()

    await callback.message.edit_text(
        "👨‍💻 Панель администратора Random Coffee\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    stats = db.get_user_stats()
    active_users = db.get_all_active_users()

    message_text = (
        "📊 Статистика системы:\n\n"
        f"👥 Пользователи: {stats.get('total_users', 0)}\n"
        f"🟢 Активные: {stats.get('active_users', 0)}\n"
        f"📝 Заполненные профили: {stats.get('completed_profiles', 0)}\n"
        f"💫 Успешные мэтчи: {stats.get('successful_matches', 0)}\n"
        f"⏳ Ожидающие решения: {stats.get('pending_matches', 0)}\n"
        f"📅 Запланированные: {stats.get('scheduled_matches', 0)}\n\n"
        f"🔍 Готовы к мэтчингу: {len(active_users)} пользователей"
    )

    await callback.message.edit_text(
        message_text,
        reply_markup=get_admin_main_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Список пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    active_users = db.get_all_active_users()

    if not active_users:
        await callback.message.edit_text(
            "❌ Нет активных пользователей",
            reply_markup=get_admin_main_inline()
        )
        return

    message_text = f"👥 Активные пользователи ({len(active_users)}):\n\n"

    for i, user in enumerate(active_users[:10], 1):
        pending_matches = len(db.get_pending_matches(user['user_id']))
        message_text += (
            f"{i}. {user.get('name', 'No name')}\n"
            f"   👤 @{user.get('username', 'no username')}\n"
            f"   🆔 <code>{user['user_id']}</code>\n"
            f"   🏙 {user.get('city', 'Не указан')}\n"
            f"   💫 Мэтчей: {user.get('matches_count', 0)} | "
            f"⏳ Ожидает: {pending_matches}\n\n"
        )

    if len(active_users) > 10:
        message_text += f"... и еще {len(active_users) - 10} пользователей"

    await callback.message.edit_text(
        message_text,
        reply_markup=get_admin_main_inline(),
        parse_mode="HTML"
    )
    await callback.answer()

# ===== РАЗДЕЛ МЭТЧИНГА =====


@router.callback_query(F.data == "admin_matching")
async def admin_matching(callback: CallbackQuery, state: FSMContext):
    """Меню мэтчинга"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    # Очищаем состояние при входе в меню мэтчинга
    await state.clear()

    active_users = db.get_all_active_users()

    await callback.message.edit_text(
        f"🔍 Управление мэтчингом\n\n"
        f"Активных пользователей: {len(active_users)}\n"
        f"Выберите действие:",
        reply_markup=get_admin_matching_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_run_matching")
async def admin_run_matching(callback: CallbackQuery, bot: Bot):
    """Запуск умного мэтчинга"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    active_users = db.get_all_active_users()

    if len(active_users) < 2:
        await callback.message.edit_text(
            "❌ Недостаточно пользователей для мэтчинга (нужно минимум 2)",
            reply_markup=get_admin_matching_inline()
        )
        return

    await callback.message.edit_text("🔄 Запускаю умный мэтчинг...")

    matches_count = match_maker.run_matching_round(force_all=False)

    if matches_count > 0:
        # Уведомляем пользователей
        notified_count = 0
        for user in active_users:
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
                            success = await send_match_proposal(
                                bot, user['user_id'], partner, match['id'])
                            if success:
                                notified_count += 1
                except Exception as e:
                    logger.error(
                        f"Error notifying user {user['user_id']}: {e}"
                        )

        await callback.message.edit_text(
            f"✅ Умный мэтчинг завершен!\n\n"
            f"• Создано пар: {matches_count}\n"
            f"• Уведомлений отправлено: {notified_count}\n"
            f"• Всего пользователей: {len(active_users)}",
            reply_markup=get_admin_matching_inline()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось создать пары. Возможно, все пользователи уже были в парах друг с другом.\n\n"
            "Попробуйте:\n"
            "• Принудительный мэтчинг (игнорирует историю)\n"
            "• Очистить старые мэтчи через 'Очистка'\n"
            "• Создать мэтч вручную",
            reply_markup=get_admin_matching_inline()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_force_matching")
async def admin_force_matching(callback: CallbackQuery, bot: Bot):
    """Принудительный мэтчинг"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    active_users = db.get_all_active_users()

    if len(active_users) < 2:
        await callback.message.edit_text(
            "❌ Недостаточно пользователей для мэтчинга",
            reply_markup=get_admin_matching_inline()
        )
        return

    await callback.message.edit_text("🎯 Запускаю принудительный мэтчинг...")

    matches_count = match_maker.run_matching_round(force_all=True)

    if matches_count > 0:
        # Уведомляем пользователей
        notified_count = 0
        for user in active_users:
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
                            success = await send_match_proposal(
                                bot, user['user_id'], partner, match['id']
                                )
                            if success:
                                notified_count += 1
                except Exception as e:
                    logger.error(
                        f"Error notifying user {user['user_id']}: {e}"
                        )

        await callback.message.edit_text(
            f"✅ Принудительный мэтчинг завершен!\n\n"
            f"Создано пар: {matches_count}\n"
            f"Уведомлений отправлено: {notified_count}",
            reply_markup=get_admin_matching_inline()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось создать пары даже в принудительном режиме.\n\n"
            "Попробуйте:\n"
            "• Создать мэтч вручную\n"
            "• Проверить, что у пользователей заполнены профили",
            reply_markup=get_admin_matching_inline()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_pending_matches")
async def admin_pending_matches(callback: CallbackQuery):
    """Список ожидающих мэтчей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    pending_matches = db.get_all_pending_matches()

    if not pending_matches:
        await callback.message.edit_text(
            "⏳ Нет ожидающих мэтчей",
            reply_markup=get_admin_matching_inline()
        )
        return

    message_text = f"⏳ Ожидающие мэтчи ({len(pending_matches)}):\n\n"

    for i, match in enumerate(pending_matches[:10], 1):
        forced_text = " 🎯" if match.get('is_forced') else ""
        message_text += (
            f"{i}. {match.get('user1_name', 'Unknown')} (<code>{match['user1_id']}</code>) + "
            f"{match.get('user2_name', 'Unknown')} (<code>{match['user2_id']}</code>)\n"
            f"   💫 Баллы: {match.get('match_score', 0)}{forced_text}\n"
            f"   📅 Создан: {match.get('created_date', '')[:10]}\n\n"
        )

    if len(pending_matches) > 10:
        message_text += f"... и еще {len(pending_matches) - 10} мэтчей"

    await callback.message.edit_text(
        message_text,
        reply_markup=get_admin_matching_inline(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_create_match")
async def admin_create_match_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания мэтча вручную"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    active_users = db.get_all_active_users()
    
    if len(active_users) < 2:
        await callback.message.edit_text(
            "❌ Недостаточно пользователей для создания мэтча",
            reply_markup=get_admin_matching_inline()
        )
        return

    # Формируем список пользователей для выбора
    users_text = "👥 Выберите первого пользователя (введите ID):\n\n"
    for user in active_users[:10]:  # Показываем первые 10
        users_text += f"🆔 <code>{user['user_id']}</code> - {user.get('name', 'No name')} (@{user.get('username', 'no username')})\n"
    
    if len(active_users) > 10:
        users_text += f"\n... и еще {len(active_users) - 10} пользователей"

    await callback.message.edit_text(
        users_text,
        reply_markup=get_back_to_admin_inline(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_manual_match_user1)
    await callback.answer()

@router.message(AdminStates.waiting_manual_match_user1)
async def process_manual_match_user1(message: Message, state: FSMContext):
    """Обработка выбора первого пользователя"""
    if not is_admin(message.from_user.id):
        return

    try:
        user1_id = int(message.text.strip())
        user1 = db.get_user(user1_id)
        
        if not user1:
            await message.answer("❌ Пользователь не найден. Введите корректный ID:")
            return
        
        await state.update_data(user1_id=user1_id, user1_name=user1.get('name', 'Unknown'))
        
        active_users = db.get_all_active_users()
        users_text = f"✅ Первый пользователь: {user1.get('name')} (ID: <code>{user1_id}</code>)\n\n"
        users_text += "👥 Выберите второго пользователя (введите ID):\n\n"
        
        for user in [u for u in active_users if u['user_id'] != user1_id][:10]:
            users_text += f"🆔 <code>{user['user_id']}</code> - {user.get('name', 'No name')} (@{user.get('username', 'no username')})\n"
        
        await message.answer(
            users_text,
            reply_markup=get_back_to_admin_inline(),
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.waiting_manual_match_user2)
        
    except ValueError:
        await message.answer("❌ Введите числовой ID пользователя:")

@router.message(AdminStates.waiting_manual_match_user2)
async def process_manual_match_user2(message: Message, state: FSMContext, bot: Bot):
    """Обработка выбора второго пользователя и создание мэтча"""
    if not is_admin(message.from_user.id):
        return

    try:
        user2_id = int(message.text.strip())
        state_data = await state.get_data()
        user1_id = state_data['user1_id']
        user1_name = state_data['user1_name']
        
        if user1_id == user2_id:
            await message.answer("❌ Нельзя создать мэтч с самим собой. Введите другой ID:")
            return
        
        user2 = db.get_user(user2_id)
        
        if not user2:
            await message.answer("❌ Пользователь не найден. Введите корректный ID:")
            return
        
        # Создаем мэтч
        success = match_maker.create_specific_match(user1_id, user2_id)
        
        if success:
            # Уведомляем пользователей
            user1_matches = db.get_pending_matches(user1_id)
            user2_matches = db.get_pending_matches(user2_id)
            
            # Находим созданный мэтч
            latest_match = None
            for match in user1_matches + user2_matches:
                if (match['user1_id'] == user1_id and match['user2_id'] == user2_id) or \
                   (match['user1_id'] == user2_id and match['user2_id'] == user1_id):
                    latest_match = match
                    break
            
            notified_count = 0
            if latest_match:
                # Уведомляем первого пользователя
                success1 = await send_match_proposal(bot, user1_id, user2, latest_match['id'])
                if success1:
                    notified_count += 1
                
                # Уведомляем второго пользователя
                success2 = await send_match_proposal(bot, user2_id, db.get_user(user1_id), latest_match['id'])
                if success2:
                    notified_count += 1
            
            await message.answer(
                f"✅ Мэтч создан успешно!\n\n"
                f"👥 {user1_name} + {user2.get('name', 'Unknown')}\n"
                f"📤 Уведомлений отправлено: {notified_count}/2",
                reply_markup=get_admin_matching_inline()
            )
        else:
            await message.answer(
                "❌ Не удалось создать мэтч. Возможно:\n"
                "• Такая пара уже существует\n"
                "• Пользователи уже были в паре ранее\n"
                "• Ошибка базы данных",
                reply_markup=get_admin_matching_inline()
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите числовой ID пользователя:")

# ===== РАЗДЕЛ ПЛАНИРОВЩИКА =====


@router.callback_query(F.data == "admin_scheduler")
async def admin_scheduler(callback: CallbackQuery, state: FSMContext):
    """Меню планировщика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    # Очищаем состояние
    await state.clear()

    scheduled_matches = db.get_scheduled_matches()
    active_scheduled = [
        m for m in scheduled_matches if m['status'] == 'scheduled'
        ]

    await callback.message.edit_text(
        f"📅 Планировщик мэтчинга\n\n"
        f"Активных расписаний: {len(active_scheduled)}\n"
        f"Выберите действие:",
        reply_markup=get_admin_scheduler_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_schedule_match")
async def admin_schedule_match(callback: CallbackQuery):
    """Запланировать мэтчинг"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    await callback.message.edit_text(
        "📅 Выберите дату для мэтчинга:",
        reply_markup=get_schedule_date_inline()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_"))
async def process_schedule_date(callback: CallbackQuery, bot: Bot):
    """Обработка выбора даты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    date_str = callback.data.split("_")[1]

    # Создаем запланированный мэтч
    match_id = db.create_scheduled_match(date_str)

    if match_id > 0:
        # Запускаем мэтчинг сразу для тестирования
        active_users = db.get_all_active_users()
        matches_count = match_maker.run_matching_round(force_all=True)
        
        notified_count = 0
        if matches_count > 0:
            for user in active_users:
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

        await callback.message.edit_text(
            f"✅ Мэтчинг запланирован на {date_str}\n\n"
            f"ID расписания: {match_id}\n"
            f"Создано пар: {matches_count}\n"
            f"Уведомлений отправлено: {notified_count}",
            reply_markup=get_admin_scheduler_inline()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при планировании мэтчинга",
            reply_markup=get_admin_scheduler_inline()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_view_schedules")
async def admin_view_schedules(callback: CallbackQuery):
    """Просмотр активных расписаний"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    scheduled_matches = db.get_scheduled_matches()

    if not scheduled_matches:
        await callback.message.edit_text(
            "📅 Нет активных расписаний",
            reply_markup=get_admin_scheduler_inline()
        )
        return

    message_text = "📅 Активные расписания:\n\n"

    for match in scheduled_matches[:10]:
        status_icon = "🟢" if match['status'] == 'scheduled' else "✅"
        message_text += (
            f"{status_icon} {match['match_date'][:10]}\n"
            f"   Статус: {match['status']}\n"
            f"   Создано: {match['created_date'][:16]}\n\n"
        )

    await callback.message.edit_text(
        message_text,
        reply_markup=get_admin_scheduler_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_run_scheduled")
async def admin_run_scheduled(callback: CallbackQuery, bot: Bot):
    """Запуск запланированного мэтчинга сейчас"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    await callback.message.edit_text("🔄 Запускаю мэтчинг по расписанию...")

    active_users = db.get_all_active_users()
    
    if len(active_users) < 2:
        await callback.message.edit_text(
            "❌ Недостаточно пользователей для мэтчинга",
            reply_markup=get_admin_scheduler_inline()
        )
        return

    # Создаем запись о запланированном мэтче
    from datetime import datetime
    db.create_scheduled_match(datetime.now().isoformat())
    
    # Запускаем мэтчинг
    matches_count = match_maker.run_matching_round(force_all=True)
    
    notified_count = 0
    if matches_count > 0:
        for user in active_users:
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

    await callback.message.edit_text(
        f"✅ Мэтчинг по расписанию завершен!\n\n"
        f"Создано пар: {matches_count}\n"
        f"Уведомлений отправлено: {notified_count}",
        reply_markup=get_admin_scheduler_inline()
    )
    await callback.answer()

# ===== РАЗДЕЛ УПРАВЛЕНИЯ =====


@router.callback_query(F.data == "admin_management")
async def admin_management(callback: CallbackQuery, state: FSMContext):
    """Меню управления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    # Очищаем состояние
    await state.clear()

    await callback.message.edit_text(
        "⚙️ Дополнительные инструменты управления\n\n"
        "Выберите действие:",
        reply_markup=get_admin_management_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_quick_match")
async def admin_quick_match(callback: CallbackQuery, bot: Bot):
    """Быстрый мэтчинг из главного меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    active_users = db.get_all_active_users()

    if len(active_users) < 2:
        await callback.answer("❌ Недостаточно пользователей")
        return

    await callback.message.edit_text("⚡ Запускаю быстрый мэтчинг...")

    matches_count = match_maker.run_matching_round(force_all=True)

    if matches_count > 0:
        # Быстро уведомляем пользователей
        notified_count = 0
        for user in active_users:
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
                            success = await send_match_proposal(
                                bot, user['user_id'], partner, match['id']
                                )
                            if success:
                                notified_count += 1
                except Exception as e:
                    logger.error(
                        f"Error notifying user {user['user_id']}: {e}"
                        )

        await callback.message.edit_text(
            f"✅ Быстрый мэтчинг завершен!\n\n"
            f"Создано {matches_count} пар\n"
            f"Отправлено {notified_count} уведомлений 🚀",
            reply_markup=get_admin_main_inline()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось создать пары",
            reply_markup=get_admin_main_inline()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_cleanup")
async def admin_cleanup(callback: CallbackQuery):
    """Очистка старых данных"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Удаляем rejected мэтчи старше 30 дней
        cursor.execute("DELETE FROM matches WHERE status = 'rejected' AND created_date < datetime('now', '-30 days')")
        rejected_deleted = cursor.rowcount

        # Удаляем completed scheduled matches старше 7 дней
        cursor.execute("DELETE FROM scheduled_matches WHERE status = 'completed' AND completed_date < datetime('now', '-7 days')")
        scheduled_deleted = cursor.rowcount

        conn.commit()
        conn.close()

        await callback.message.edit_text(
            f"🧹 Очистка завершена!\n\n"
            f"• Удалено rejected мэтчей: {rejected_deleted}\n"
            f"• Удалено старых расписаний: {scheduled_deleted}",
            reply_markup=get_admin_management_inline()
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при очистке: {e}",
            reply_markup=get_admin_management_inline()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_debug")
async def admin_debug(callback: CallbackQuery):
    """Отладочная информация"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    active_users = db.get_all_active_users()

    debug_info = "🐛 Отладочная информация:\n\n"
    debug_info += f"Активных пользователей: {len(active_users)}\n\n"

    for user in active_users[:5]:
        pending_matches = db.get_pending_matches(user['user_id'])
        debug_info += f"👤 {user.get('name')} (<code>{user['user_id']}</code>):\n"
        debug_info += f"   • Ожидающих мэтчей: {len(pending_matches)}\n"
        debug_info += f"   • Интересы: {user.get('interests', 'Нет')[:30]}...\n\n"

    # Тест мэтчинга между первыми двумя пользователями
    if len(active_users) >= 2:
        user1 = active_users[0]
        user2 = active_users[1]
        score, common = match_maker.calculate_match_score(user1, user2)
        debug_info += f"🔍 Тест мэтчинга:\n"
        debug_info += f"   {user1.get('name')} + {user2.get('name')}\n"
        debug_info += f"   Баллы: {score}\n"
        debug_info += f"   Общие интересы: {', '.join(common) if common else 'Нет'}\n"
        
        # Проверяем, были ли уже в паре
        have_previous = match_maker.have_previous_match(user1['user_id'], user2['user_id'])
        debug_info += f"   Были в паре ранее: {'Да' if have_previous else 'Нет'}\n"

    await callback.message.edit_text(
        debug_info,
        reply_markup=get_admin_management_inline(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Настройки админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    await callback.message.edit_text(
        "🔧 Настройки администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_settings_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_db_settings")
async def admin_db_settings(callback: CallbackQuery):
    """Настройки базы данных"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    # Пересоздаем таблицы для обновления структуры
    try:
        db.init_db()
        await callback.answer("✅ Структура БД обновлена")
        
        # Обновляем сообщение
        await admin_settings(callback)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}")

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

async def send_match_proposal(bot: Bot, user_id: int, partner: dict, match_id: int):
    """Отправляет предложение мэтча пользователю"""
    try:
        from handlers.matching import send_match_proposal as send_proposal
        return await send_proposal(bot, user_id, partner, match_id)
    except Exception as e:
        logger.error(f"Error in admin match proposal: {e}")
        return False

# ===== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ =====


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    user_id = callback.from_user.id

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