import asyncio
import logging
from aiogram import Bot, Dispatcher
from datetime import datetime

from config import Config
from database import Database
from services.matcher import MatchMaker

# Import handlers
from handlers.start import router as start_router
from handlers.registration import router as registration_router
from handlers.matching import router as matching_router
from handlers.profile import router as profile_router
from handlers.admin import router as admin_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

# Register routers
dp.include_router(start_router)
dp.include_router(registration_router)
dp.include_router(matching_router)
dp.include_router(profile_router)
dp.include_router(admin_router)

# Initialize database and services
db = Database()
match_maker = MatchMaker(db)

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Bot started!")
    logger.info("Автоматическое расписание отключено. Используйте админ-панель для ручного запуска мэтчинга.")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Bot stopped!")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())