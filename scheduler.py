import asyncio
import logging
from datetime import datetime
from app import main as check_notifications

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def scheduler():
    """Run notification check every 1 minute"""
    logger.info("🕐 TDTU Notification Scheduler Started")
    logger.info("⏰ Running every 1 minute...")
    
    while True:
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"🔄 Starting scheduled check at {current_time}")
            
            # Run the notification check
            await check_notifications()
            
            logger.info("✅ Scheduled check completed")
            
        except Exception as e:
            logger.error(f"❌ Error in scheduled check: {e}")
        
        # Wait 1 minute before next check
        logger.info("⏳ Waiting 1 minute until next check...")
        await asyncio.sleep(60)  # 60 seconds = 1 minute

if __name__ == '__main__':
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler stopped by user")
    except Exception as e:
        logger.error(f"💥 Scheduler crashed: {e}") 