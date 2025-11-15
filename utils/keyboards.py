from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

# ===== INLINE КНОПКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ =====

def get_main_menu_inline():
    """Главное меню с inline кнопками"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile"),
                InlineKeyboardButton(text="🔍 Найти собеседника", callback_data="find_match")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="my_stats"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
            ]
        ]
    )

def get_match_decision_inline(match_id: int, linkedin_url: str = None):
    """Кнопки для принятия/отклонения мэтча с LinkedIn"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Принять мэтч", callback_data=f"accept_{match_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{match_id}")
        ]
    ]
    
    if linkedin_url:
        keyboard.append([
            InlineKeyboardButton(text="🔗 LinkedIn профиль", url=linkedin_url)
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_match_success_inline(match_id: int):
    """Кнопки для оценки успешности мэтча"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Мэтч удался", callback_data=f"success_{match_id}"),
                InlineKeyboardButton(text="❌ Мэтч неудался", callback_data=f"fail_{match_id}")
            ]
        ]
    )

def get_chat_created_inline(partner_user_id: int, partner_username: str = None):
    """Кнопки после создания чата"""
    buttons = []
    
    if partner_username:
        buttons.append([
            InlineKeyboardButton(
                text="💌 Написать в Telegram", 
                url=f"https://t.me/{partner_username}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="💌 Написать собеседнику", 
                url=f"tg://user?id={partner_user_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🎉 Начать общение!", callback_data="start_chat")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_profile_actions_inline():
    """Действия с профилем"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile"),
                InlineKeyboardButton(text="🔍 Найти собеседника", callback_data="find_match")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="my_stats"),
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
            ]
        ]
    )

# ===== INLINE КНОПКИ ДЛЯ АДМИНА =====

def get_admin_main_inline():
    """Главное меню админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="🔍 Мэтчинг", callback_data="admin_matching"),
                InlineKeyboardButton(text="🔄 Быстрый мэтчинг", callback_data="admin_quick_match")
            ],
            [
                InlineKeyboardButton(text="⚙️ Управление", callback_data="admin_management")
            ],
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
            ]
        ]
    )

def get_admin_matching_inline():
    """Меню мэтчинга для админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Запустить мэтчинг", callback_data="admin_run_matching"),
                InlineKeyboardButton(text="🎯 Принудительный мэтчинг", callback_data="admin_force_matching")
            ],
            [
                InlineKeyboardButton(text="📋 Ожидающие мэтчи", callback_data="admin_pending_matches"),
                InlineKeyboardButton(text="👥 Создать мэтч вручную", callback_data="admin_create_match")
            ],
            [
                InlineKeyboardButton(text="🧹 Очистить все мэтчи", callback_data="admin_cleanup_matches")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")
            ]
        ]
    )

def get_admin_management_inline():
    """Меню управления"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="🐛 Отладка", callback_data="admin_debug")
            ],
            [
                InlineKeyboardButton(text="📊 Экспорт пользователей", callback_data="admin_export_csv"),
                InlineKeyboardButton(text="💫 Экспорт мэтчей", callback_data="admin_export_matches_csv")
            ],
            [
                InlineKeyboardButton(text="📊 Детальная статистика", callback_data="admin_detailed_stats"),
                InlineKeyboardButton(text="🔧 Настройки", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")
            ]
        ]
    )

def get_back_to_admin_inline():
    """Кнопка возврата в админ-панель"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_main")]
        ]
    )

def get_back_to_main_inline():
    """Кнопка возврата в главное меню"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ]
    )

# ===== REPLY КНОПКИ (для совместимости) =====

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мой профиль"), KeyboardButton(text="🔍 Найти собеседника")],
            [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )

def get_edit_profile_inline():
    """Кнопки для редактирования профиля"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data="edit_name"),
                InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_age")
            ],
            [
                InlineKeyboardButton(text="🏙 Город", callback_data="edit_city"),
                InlineKeyboardButton(text="💼 Профессия", callback_data="edit_profession")
            ],
            [
                InlineKeyboardButton(text="🎯 Интересы", callback_data="edit_interests"),
                InlineKeyboardButton(text="🎯 Цели", callback_data="edit_goals")
            ],
            [
                InlineKeyboardButton(text="📝 О себе", callback_data="edit_about"),
                InlineKeyboardButton(text="🔗 LinkedIn", callback_data="edit_linkedin")
            ],
            [
                InlineKeyboardButton(text="📞 Контакты", callback_data="edit_contacts")
            ],
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
            ]
        ]
    )

def get_settings_inline():
    """Кнопки настроек пользователя"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile"),
                InlineKeyboardButton(text="🟢 Вкл/Выкл", callback_data="toggle_active")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="my_stats"),
                InlineKeyboardButton(text="🔍 Найти собеседника", callback_data="find_match")
            ],
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
            ]
        ]
    )

def get_admin_settings_inline():
    """Кнопки настроек админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="🧹 Очистка", callback_data="admin_cleanup")
            ],
            [
                InlineKeyboardButton(text="🔧 Настройки БД", callback_data="admin_db_settings"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_management")
            ]
        ]
    )