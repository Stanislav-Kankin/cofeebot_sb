from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_city = State()
    waiting_profession = State()
    waiting_interests = State()
    waiting_goals = State()
    waiting_about = State()
    waiting_linkedin = State()
    waiting_contact_preference = State()


class AdminStates(StatesGroup):
    waiting_broadcast_message = State()
    waiting_manual_match_user1 = State()
    waiting_manual_match_user2 = State()
