from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мой профиль"), KeyboardButton(text="🔍 Найти собеседника")],
            [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )

def get_accept_match_keyboard(match_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{match_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{match_id}")
            ]
        ]
    )

def get_contact_keyboard(target_user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💌 Написать собеседнику", url=f"tg://user?id={target_user_id}")],
            [InlineKeyboardButton(text="✅ Подтвердить контакт", callback_data="contact_confirmed")]
        ]
    )

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="🔄 Запустить мэтчинг")],
            [KeyboardButton(text="🔙 В главное меню")]
        ],
        resize_keyboard=True
    )