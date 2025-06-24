import asyncio
import os
import json
import aiohttp
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import aiofiles
import logging
import re
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Environment variables  
USER = "52000018"
PASSWORD = "TDTU6877"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1386929056020430888/1wGHNeeG9LwaYctSFpapbXyUw8gk16SB1QD27VJtBo-ALRrmcXmkxjjLxjivUvS7D-i2"

async def send_discord_webhook(title, description, url, color=0x00AE86):
    """Send a message to Discord webhook"""
    try:
        embed = {
            "title": title,
            "description": description,
            "url": url,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "TDTU Notification Bot"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
                if response.status == 204:
                    logger.info(f"✅ Sent to Discord: {title[:50]}...")
                    return True
                else:
                    logger.error(f"❌ Discord webhook failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error sending Discord webhook: {e}")
        return False



async def get_category_notifications(the_loai_id: str, category_name: str):
    """Scrape notifications using category-based URL with Firefox"""
    new_contents = []
    new_notifications = []

    async with async_playwright() as p:
        browser = None
        try:
            logger.info(f"🚀 Starting notification check for {category_name} (TheLoaiID={the_loai_id})")
            
            # Launch Firefox browser
            browser = await p.firefox.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context(
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
                viewport={'width': 1366, 'height': 768}
            )
            page = await context.new_page()

            # Navigate to login page
            logger.info("🔐 Logging into TDTU portal...")
            await page.goto('https://stdportal.tdtu.edu.vn/')
            await page.fill('#txtUser', USER)
            await page.fill('#txtPass', PASSWORD)
            await page.click('#btnLogIn')
            await page.wait_for_timeout(3000)

            # Navigate to student news
            logger.info("📰 Accessing student news...")
            await page.goto('https://studentnews.tdtu.edu.vn/Home/Index')
            await page.goto(f'https://studentnews.tdtu.edu.vn/ChuDe/ThongBaoChuDe?TheLoaiID={the_loai_id}')

            # Wait for the notifications div to load
            await page.wait_for_selector('#div_lstThongBao', timeout=15000)

            # Scroll to load all notifications
            logger.info("📜 Loading all notifications...")
            last_height = await page.evaluate('document.querySelector("#div_lstThongBao").scrollHeight')
            
            while True:
                await page.evaluate('document.querySelector("#div_lstThongBao").scrollTo(0, document.querySelector("#div_lstThongBao").scrollHeight)')
                await page.wait_for_timeout(1000)
                
                new_height = await page.evaluate('document.querySelector("#div_lstThongBao").scrollHeight')
                if new_height == last_height:
                    break
                last_height = new_height

            # Get all notification items
            list_items = page.locator('.list-item')
            count = await list_items.count()
            logger.info(f"📋 Found {count} notification items")

            # Read existing notifications
            read_notifications = await read_from_file(f'readed_noti_category_{the_loai_id}.txt')

            # Extract new notifications
            for i in range(count):
                item = list_items.nth(i)
                
                # Get title
                title_element = item.locator('.title')
                title = await title_element.get_attribute('title')
                
                # Get ID from onclick attribute
                link_element = item.locator('.link-detail')
                onclick = await link_element.get_attribute('onclick')
                
                if onclick:
                    id_match = re.search(r'Detail/(\d+)', onclick)
                    if id_match:
                        notification_id = id_match.group(1)
                        
                        if notification_id not in read_notifications:
                            logger.info(f'🆕 NEW: {title[:60]}...')
                            new_notifications.append(notification_id)
                            new_contents.append(title)

            # Update read notifications file
            if new_notifications:
                updated_notifications = read_notifications + new_notifications
                async with aiofiles.open(f'readed_noti_category_{the_loai_id}.txt', 'w') as f:
                    await f.write('\n'.join(updated_notifications))
                logger.info(f"💾 Updated tracking file with {len(new_notifications)} new notifications")

        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            raise e
        finally:
            if browser:
                try:
                    await browser.close()
                except:
                    pass

    return new_contents, new_notifications, count



async def read_from_file(file_path: str):
    """Read notifications from file"""
    try:
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            return [line.strip() for line in content.strip().split('\n') if line.strip()]
    except FileNotFoundError:
        logger.info(f'📁 Creating new tracking file: {file_path}')
        async with aiofiles.open(file_path, 'w') as f:
            await f.write('')
        return []
    except Exception as error:
        logger.error(f'Error reading file: {error}')
        raise error

async def process_category(category_id: str, category_name: str):
    """Process notifications for a single category"""
    try:
        logger.info(f"{'='*60}")
        logger.info(f"🔍 Processing {category_name} (ID: {category_id})")
        logger.info(f"{'='*60}")
        
        new_contents, new_notifications, total_count = await get_category_notifications(category_id, category_name)
        
        # Send individual notifications to Discord
        sent_count = 0
        if new_contents:
            logger.info(f"📤 Sending {len(new_contents)} new notifications to Discord...")
            
            # Send notifications in chunks to avoid rate limiting
            for i, (title, notification_id) in enumerate(zip(new_contents, new_notifications)):
                url = f"https://studentnews.tdtu.edu.vn/ThongBao/Detail/{notification_id}"
                
                # Create description with notification number
                description = f"**Notification #{i+1}** of {len(new_contents)} new notifications\n📅 Category: {category_name}"
                
                success = await send_discord_webhook(title, description, url)
                if success:
                    sent_count += 1
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
        
        # No individual summary needed
        
        logger.info(f"✅ {category_name} completed: {sent_count}/{len(new_contents)} sent successfully")
        return len(new_contents), sent_count
        
    except Exception as e:
        logger.error(f"❌ Error processing {category_name}: {e}")
        # Send error notification
        error_embed = {
            "title": f"⚠️ Error in {category_name}",
            "description": f"Failed to check notifications: {str(e)}",
            "color": 0xe74c3c,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(DISCORD_WEBHOOK_URL, json={"embeds": [error_embed]})
        except:
            pass
        
        return 0, 0



async def main():
    """Main function to check all notification categories and departments"""
    logger.info("🤖 TDTU Notification Webhook Bot Starting...")
    logger.info(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Categories to monitor
    categories = [
        ("11", "Academic & Graduation"),
    ]
    
    total_new = 0
    total_sent = 0
    
    # Process each category
    for category_id, category_name in categories:
        new_count, sent_count = await process_category(category_id, category_name)
        total_new += new_count
        total_sent += sent_count
        
        # Add delay between categories
        await asyncio.sleep(2)
    
    # Only send summary if no new notifications found
    if total_new == 0:
        no_news_embed = {
            "title": "📰 TDTU Notifications",
            "description": "✅ No new notifications found\nAll notifications are up to date",
            "color": 0x95a5a6,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": f"Checked at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(DISCORD_WEBHOOK_URL, json={"embeds": [no_news_embed]})
        except:
            pass
    
    logger.info(f"🏁 Bot completed! {total_new} new notifications found, {total_sent} sent to Discord")

if __name__ == '__main__':
    asyncio.run(main()) 