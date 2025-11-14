from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from database import Database
from utils.states import RegistrationStates
from utils.keyboards import get_main_menu_keyboard

router = Router()
db = Database()

questions = db.get_questions()
current_question_index = 0

@router.message(RegistrationStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegistrationStates.waiting_age)

@router.message(RegistrationStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи возраст числом:")
        return
    
    age = int(message.text)
    if age < 12 or age > 100:
        await message.answer("Пожалуйста, введи реальный возраст:")
        return
    
    await state.update_data(age=age)
    await message.answer("Из какого ты города?")
    await state.set_state(RegistrationStates.waiting_city)

@router.message(RegistrationStates.waiting_city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Чем занимаешься (профессия/род деятельности)?")
    await state.set_state(RegistrationStates.waiting_profession)

@router.message(RegistrationStates.waiting_profession)
async def process_profession(message: Message, state: FSMContext):
    await state.update_data(profession=message.text)
    await message.answer(
        "Какие у тебя интересы/хобби? (перечисли через запятую)\n"
        "Например: программирование, путешествия, книги, спорт"
    )
    await state.set_state(RegistrationStates.waiting_interests)

@router.message(RegistrationStates.waiting_interests)
async def process_interests(message: Message, state: FSMContext):
    await state.update_data(interests=message.text)
    await message.answer(
        "Что ищешь в Random Coffee? (перечисли через запятую)\n"
        "Например: новые знакомства, бизнес-контакты, друзья, менторство"
    )
    await state.set_state(RegistrationStates.waiting_goals)

@router.message(RegistrationStates.waiting_goals)
async def process_goals(message: Message, state: FSMContext):
    await state.update_data(goals=message.text)
    await message.answer("Расскажи о себе кратко (2-3 предложения):")
    await state.set_state(RegistrationStates.waiting_about)

@router.message(RegistrationStates.waiting_about)
async def process_about(message: Message, state: FSMContext):
    await state.update_data(about=message.text)
    await message.answer("Как предпочитаешь общаться? (Telegram, email, другое)")
    await state.set_state(RegistrationStates.waiting_contact_preference)

@router.message(RegistrationStates.waiting_contact_preference)
async def process_contact_preference(message: Message, state: FSMContext):
    user_data = await state.get_data()
    
    # Сохраняем профиль
    success = db.update_user_profile(
        user_id=message.from_user.id,
        name=user_data['name'],
        age=user_data['age'],
        city=user_data['city'],
        profession=user_data['profession'],
        interests=user_data['interests'],
        goals=user_data['goals'],
        about=user_data['about'],
        contact_preference=message.text
    )
    
    if success:
        await message.answer(
            "🎉 Отлично! Твой профиль заполнен!\n\n"
            "Теперь ты в системе Random Coffee. Я буду подбирать тебе собеседников "
            "на основе твоих интересов и отправлять уведомления.\n\n"
            "Обычно мэтчинг происходит 1-2 раза в неделю. Жди приглашения! ✨",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "😔 Произошла ошибка при сохранении профиля. Попробуй позже.",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()