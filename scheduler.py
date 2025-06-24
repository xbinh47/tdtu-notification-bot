import asyncio
import logging
from datetime import datetime, time, timedelta
from app import main as check_notifications

# Configure logging with timezone
import os
os.environ['TZ'] = 'Asia/Ho_Chi_Minh'  # Set system timezone to UTC+7

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [UTC+7] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Schedule times (24-hour format)
SCHEDULE_TIMES = [
    time(12, 0),  # 12:00 PM
    time(18, 0),  # 6:00 PM
]

def get_next_run_time():
    """Calculate the next scheduled run time"""
    now = datetime.now()
    today = now.date()
    
    # Check if any scheduled time is still today
    for schedule_time in SCHEDULE_TIMES:
        next_run = datetime.combine(today, schedule_time)
        if next_run > now:
            return next_run
    
    # If all times have passed today, get the first time tomorrow
    tomorrow = datetime.combine(today, SCHEDULE_TIMES[0]) + timedelta(days=1)
    return tomorrow

async def scheduler():
    """Run notification check at 12:00 and 18:00 daily"""
    logger.info("🕐 TDTU Notification Scheduler Started")
    logger.info("⏰ Running daily at 12:00 PM and 6:00 PM")
    
    while True:
        try:
            next_run = get_next_run_time()
            now = datetime.now()
            wait_seconds = (next_run - now).total_seconds()
            
            logger.info(f"⏳ Next check scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏳ Waiting {wait_seconds/3600:.1f} hours...")
            
            # Wait until the next scheduled time
            await asyncio.sleep(wait_seconds)
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"🔄 Starting scheduled check at {current_time}")
            
            # Run the notification check
            await check_notifications()
            
            logger.info("✅ Scheduled check completed")
            
        except Exception as e:
            logger.error(f"❌ Error in scheduled check: {e}")
            # Wait 5 minutes before retrying on error
            logger.info("⏳ Waiting 5 minutes before retry...")
            await asyncio.sleep(300)

if __name__ == '__main__':
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler stopped by user")
    except Exception as e:
        logger.error(f"💥 Scheduler crashed: {e}") 