from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging
import csv
import io
from datetime import datetime
from aiogram.types import BufferedInputFile
from database import Database
from services.matcher import MatchMaker
from utils.states import AdminStates

from utils.keyboards import (
    get_admin_main_inline, get_admin_matching_inline,
    get_admin_management_inline,
    get_main_menu_inline, get_admin_settings_inline,
    get_back_to_admin_inline,
)
from config import Config

router = Router()
db = Database()
match_maker = MatchMaker(db)

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

    #==== Вспомогательные функции для csv ====

def clean_csv_value(value):
    """Очищает значение для CSV, убирая лишние символы"""
    if value is None:
        return ''
    
    value_str = str(value).strip()
    
    # Заменяем все проблемные символы на запятые с пробелами
    replacements = ['\t', '    ', '   ', '  ']  # табуляции и множественные пробелы
    for replacement in replacements:
        value_str = value_str.replace(replacement, ', ')
    
    # Убираем лишние пробелы
    value_str = ' '.join(value_str.split())
    
    # Убираем дублирующиеся запятые
    while ', ,' in value_str:
        value_str = value_str.replace(', ,', ',')
    
    value_str = value_str.strip(' ,')
    
    return value_str

def format_date(date_string):
    """Форматирует дату для лучшей читаемости"""
    if not date_string:
        return ''
    
    # Пытаемся разобрать разные форматы дат
    try:
        # Убираем временную зону если есть
        if '+' in date_string:
            date_string = date_string.split('+')[0]
        
        # Пробуем разные форматы
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
            try:
                dt = datetime.strptime(date_string.strip(), fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        # Если не удалось распарсить, возвращаем как есть
        return date_string
    except:
        return date_string

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


@router.callback_query(F.data == "admin_cleanup_matches")
async def admin_cleanup_matches(callback: CallbackQuery):
    """Очистка всех мэтчей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    try:
        success = db.cleanup_matches()
        
        if success:
            await callback.message.edit_text(
                "🧹 Все мэтчи успешно очищены!\n\n"
                "Теперь можно запускать новый раунд мэтчинга.",
                reply_markup=get_admin_matching_inline()
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка при очистке мэтчей",
                reply_markup=get_admin_matching_inline()
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при очистке: {e}",
            reply_markup=get_admin_matching_inline()
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

# ===== ЭКСПОРТ CSV =====


@router.callback_query(F.data == "admin_export_csv")
async def admin_export_csv(callback: CallbackQuery):
    """Экспорт данных в CSV"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    try:
        # Создаем CSV файл в памяти с разделителем табуляции
        output = io.StringIO()
        writer = csv.writer(output, delimiter='\t', quoting=csv.QUOTE_ALL)  # Используем табуляцию как разделитель
        
        # Заголовки для пользователей
        writer.writerow([
            'User ID', 'Username', 'Name', 'Age', 'City', 'Profession', 
            'Interests', 'Goals', 'About', 'LinkedIn URL', 'Contact Preference',
            'Registration Date', 'Last Active', 'Is Active', 'Matches Count', 'Profile Completed'
        ])
        
        # Данные пользователей
        users = db.get_all_active_users()
        for user in users:
            # Очищаем и форматируем данные
            writer.writerow([
                user.get('user_id', ''),
                user.get('username', ''),
                user.get('name', ''),
                user.get('age', ''),
                user.get('city', ''),
                user.get('profession', ''),
                clean_csv_value(user.get('interests', '')),
                clean_csv_value(user.get('goals', '')),
                clean_csv_value(user.get('about', '')),
                user.get('linkedin_url', ''),
                user.get('contact_preference', ''),
                format_date(user.get('registration_date', '')),
                format_date(user.get('last_active', '')),
                user.get('is_active', ''),
                user.get('matches_count', ''),
                user.get('profile_completed', '')
            ])
        
        # Перемещаем указатель в начало
        output.seek(0)
        
        # Создаем файл для отправки
        csv_file = BufferedInputFile(
            output.getvalue().encode('utf-8-sig'),
            filename=f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv"  # Меняем расширение на TSV
        )
        
        await callback.message.answer_document(
            document=csv_file,
            caption=f"📊 Экспорт данных пользователей (TSV формат)\n\n"
                   f"Всего пользователей: {len(users)}\n"
                   f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                   f"Формат: TSV (табуляция как разделитель)"
        )
        
        await callback.answer("✅ Файл успешно экспортирован!")
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при экспорте CSV: {e}",
            reply_markup=get_admin_management_inline()
        )
        await callback.answer()



@router.callback_query(F.data == "admin_export_matches_csv")
async def admin_export_matches_csv(callback: CallbackQuery):
    """Экспорт мэтчей в CSV"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    try:
        # Создаем CSV файл в памяти
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)  # Добавляем QUOTE_ALL
        
        # Заголовки для мэтчей
        writer.writerow([
            'Match ID', 'User1 ID', 'User1 Name', 'User2 ID', 'User2 Name',
            'Match Score', 'Common Interests', 'Status', 'Created Date',
            'Accepted Date', 'Is Forced', 'User1 Accepted', 'User2 Accepted',
            'Chat Created', 'Match Successful'
        ])
        
        # Получаем все мэтчи
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, u1.name as user1_name, u2.name as user2_name
            FROM matches m
            LEFT JOIN users u1 ON m.user1_id = u1.user_id
            LEFT JOIN users u2 ON m.user2_id = u2.user_id
            ORDER BY m.created_date DESC
        ''')
        
        matches = cursor.fetchall()
        conn.close()
        
        for match in matches:
            writer.writerow([
                match[0],  # id
                match[1],  # user1_id
                match[14] if len(match) > 14 else '',  # user1_name
                match[2],  # user2_id
                match[15] if len(match) > 15 else '',  # user2_name
                match[3],  # match_score
                clean_csv_value(match[4] if len(match) > 4 else ''),  # common_interests
                match[5] if len(match) > 5 else '',  # status
                format_date(match[6] if len(match) > 6 else ''),  # created_date
                format_date(match[7] if len(match) > 7 else ''),  # accepted_date
                match[8] if len(match) > 8 else '',  # is_forced
                match[9] if len(match) > 9 else '',  # user1_accepted
                match[10] if len(match) > 10 else '',  # user2_accepted
                match[11] if len(match) > 11 else '',  # chat_created
                match[12] if len(match) > 12 else ''   # match_successful
            ])
        
        # Перемещаем указатель в начало
        output.seek(0)
        
        # Создаем файл для отправки
        csv_file = BufferedInputFile(
            output.getvalue().encode('utf-8-sig'),  # Меняем на utf-8-sig для Excel
            filename=f"matches_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        await callback.message.answer_document(
            document=csv_file,
            caption=f"📊 Экспорт данных мэтчей\n\n"
                   f"Всего мэтчей: {len(matches)}\n"
                   f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.answer("✅ Файл мэтчей успешно экспортирован!")
        
    except Exception as e:
        logger.error(f"Error exporting matches CSV: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при экспорте мэтчей CSV: {e}",
            reply_markup=get_admin_management_inline()
        )
        await callback.answer()

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