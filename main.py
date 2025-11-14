import asyncio
import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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

async def scheduled_matching():
    """Запуск мэтчинга по расписанию"""
    logger.info("Running scheduled matching...")
    try:
        # Создаем запись о запланированном мэтче
        db.create_scheduled_match(datetime.now().isoformat())
        
        # Запускаем мэтчинг с принудительным созданием пар
        matches_count = match_maker.run_matching_round(force_all=True)
        
        if matches_count > 0:
            # Уведомляем пользователей
            active_users = db.get_all_active_users()
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
                                from handlers.matching import send_match_proposal
                                success = await send_match_proposal(bot, user['user_id'], partner, match['id'])
                                if success:
                                    notified_count += 1
                    except Exception as e:
                        logger.error(f"Error notifying user {user['user_id']}: {e}")
        
        logger.info(f"Scheduled matching completed. Created {matches_count} matches, notified {notified_count} users")
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

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())