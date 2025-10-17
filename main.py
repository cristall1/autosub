import asyncio
import logging
from aiogram import Bot
import database as db
import config
from admin_bot import dp as admin_dp, bot as admin_bot
from user_bot import dp as user_dp, bot as user_bot, send_expiry_notification

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PRIVATE_CHANNEL_ID = config.PRIVATE_CHANNEL_ID
CHECK_INTERVAL = getattr(config, 'EXPIRY_CHECK_INTERVAL', 3600)


async def check_and_remove_expired_users():
    """Check for expired subscriptions and remove users from channel"""
    while True:
        try:
            check_interval = await db.get_shortest_active_subscription_seconds()
            logger.info(f"Next expiry check in {check_interval} seconds")
            await asyncio.sleep(check_interval)
            
            logger.info("Checking for expired subscriptions...")
            
            expired_user_ids = await db.deactivate_expired_subscriptions()
            
            if expired_user_ids:
                logger.info(f"Found {len(expired_user_ids)} expired subscriptions")
                
                for user_id in expired_user_ids:
                    try:
                        await admin_bot.ban_chat_member(
                            chat_id=PRIVATE_CHANNEL_ID,
                            user_id=user_id
                        )
                        
                        await admin_bot.unban_chat_member(
                            chat_id=PRIVATE_CHANNEL_ID,
                            user_id=user_id
                        )
                        
                        await db.mark_user_removed_from_channel(user_id)
                        
                        await send_expiry_notification(user_id)
                        
                        logger.info(f"Removed user {user_id} from channel")
                    except Exception as e:
                        logger.error(f"Failed to remove user {user_id} from channel: {e}")
            else:
                logger.info("No expired subscriptions found")
                
        except Exception as e:
            logger.error(f"Error in expiry checker: {e}")


async def main():
    """Main function to run both bots"""
    await db.init_db()
    await db.init_default_bot_config()
    logger.info("Database initialized")
    
    expiry_task = asyncio.create_task(check_and_remove_expired_users())
    logger.info("Expiry checker started")
    
    admin_task = asyncio.create_task(admin_dp.start_polling(admin_bot))
    logger.info("Admin bot started")
    
    user_task = asyncio.create_task(user_dp.start_polling(user_bot))
    logger.info("User bot started")
    
    logger.info("All systems running!")
    
    await asyncio.gather(expiry_task, admin_task, user_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
