import asyncio
import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

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

async def scheduled_matching():
    """Запуск мэтчинга по расписанию"""
    logger.info("Running scheduled matching...")
    try:
        matches_count = match_maker.run_matching_round()
        logger.info(f"Scheduled matching completed. Created {matches_count} matches")
    except Exception as e:
        logger.error(f"Error in scheduled matching: {e}")

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Bot started!")
    
    # Настройка планировщика
    scheduler = AsyncIOScheduler()
    
    # Мэтчинг каждый понедельник и четверг в 10:00
    scheduler.add_job(
        scheduled_matching,
        CronTrigger(day_of_week='mon,thu', hour=10, minute=0)
    )
    
    scheduler.start()
    logger.info("Scheduler started")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Bot stopped!")
    # Можно добавить закрытие соединений с БД

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())