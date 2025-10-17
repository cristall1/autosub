import aiosqlite
import asyncio
from datetime import datetime, timedelta
import logging

DATABASE_FILE = "bot_database.db"


async def init_db():
    """Initialize the database with required tables"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                phone_number TEXT,
                subscription_end TEXT,
                is_active INTEGER DEFAULT 0,
                photo_file_id TEXT,
                added_to_channel INTEGER DEFAULT 0,
                channel_member_removed INTEGER DEFAULT 0
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                price REAL NOT NULL,
                duration_unit TEXT DEFAULT 'days'
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                phone_number TEXT,
                service_id INTEGER,
                created_at TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        await db.commit()
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
        await db.commit()
        
        cursor = await db.execute("SELECT COUNT(*) FROM services")
        count = await cursor.fetchone()
        if count[0] == 0:
            import config
            await db.execute(
                "INSERT INTO services (name, duration_days, price, duration_unit) VALUES (?, ?, ?, ?)",
                (config.DEFAULT_SERVICE_NAME, config.DEFAULT_SERVICE_DURATION, config.DEFAULT_SERVICE_PRICE, 'days')
            )
            await db.commit()


async def add_service(name: str, duration_days: int, price: float, duration_unit: str = 'days'):
    """Add a new service/plan"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            "INSERT INTO services (name, duration_days, price, duration_unit) VALUES (?, ?, ?, ?)",
            (name, duration_days, price, duration_unit)
        )
        await db.commit()


async def get_services():
    """Get all available services"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("SELECT id, name, duration_days, price, duration_unit FROM services")
        rows = await cursor.fetchall()
        return [{"id": row[0], "name": row[1], "duration_days": row[2], "price": row[3], "duration_unit": row[4] or 'days'} for row in rows]


async def update_service_price(service_id: int, new_price: float):
    """Update service price"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("UPDATE services SET price = ? WHERE id = ?", (new_price, service_id))
        await db.commit()


async def update_service_duration(service_id: int, new_duration: int, duration_unit: str = 'days'):
    """Update service duration"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("UPDATE services SET duration_days = ?, duration_unit = ? WHERE id = ?", (new_duration, duration_unit, service_id))
        await db.commit()


async def delete_service(service_id: int):
    """Delete a service"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM services WHERE id = ?", (service_id,))
        await db.commit()


async def update_service_name(service_id: int, new_name: str):
    """Update service name"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("UPDATE services SET name = ? WHERE id = ?", (new_name, service_id))
        await db.commit()


async def add_pending_purchase(user_id: int, username: str, phone_number: str | None, service_id: int):
    """Add a pending purchase for admin confirmation"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        created_at = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO pending_purchases (user_id, username, phone_number, service_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, phone_number, service_id, created_at)
        )
        await db.commit()
        cursor = await db.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        return row[0]


async def get_pending_purchase(purchase_id: int):
    """Get pending purchase details"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT user_id, username, phone_number, service_id FROM pending_purchases WHERE id = ?",
            (purchase_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "phone_number": row[2],
                "service_id": row[3]
            }
        return None


async def delete_pending_purchase(purchase_id: int):
    """Delete a pending purchase"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM pending_purchases WHERE id = ?", (purchase_id,))
        await db.commit()


async def activate_user_subscription(user_id: int, username: str, phone_number: str | None, duration_value: int, duration_unit: str = 'days'):
    """Activate or extend user subscription with flexible time units"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()

        base = datetime.now()
        if row and row[0]:
            current_end = datetime.fromisoformat(row[0])
            if current_end > datetime.now():
                base = current_end

        unit = (duration_unit or 'days').lower()
        if unit in ('second', 'seconds'):
            new_end = base + timedelta(seconds=duration_value)
        elif unit in ('minute', 'minutes'):
            new_end = base + timedelta(minutes=duration_value)
        elif unit in ('month', 'months'):
            new_end = base + timedelta(days=30 * duration_value)
        else:
            new_end = base + timedelta(days=duration_value)

        await db.execute(
            """
            INSERT INTO users (user_id, username, phone_number, subscription_end, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                phone_number = COALESCE(excluded.phone_number, phone_number),
                subscription_end = excluded.subscription_end,
                is_active = 1
            """,
            (user_id, username, phone_number, new_end.isoformat())
        )
        await db.commit()
        return new_end


async def get_user_subscription(user_id: int):
    """Get user subscription status"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT subscription_end, is_active FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "subscription_end": row[0],
                "is_active": row[1]
            }
        return None


async def get_all_users():
    """Get all users with their subscription status"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT user_id, username, phone_number, subscription_end, is_active, photo_file_id FROM users"
        )
        rows = await cursor.fetchall()
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "phone_number": row[2],
                "subscription_end": row[3],
                "is_active": row[4],
                "photo_file_id": row[5]
            }
            for row in rows
        ]


async def deactivate_expired_subscriptions():
    """Deactivate expired subscriptions and return list of expired user IDs"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE subscription_end < ? AND is_active = 1",
            (now,)
        )
        expired_users = [row[0] for row in await cursor.fetchall()]
        
        if expired_users:
            await db.execute(
                "UPDATE users SET is_active = 0 WHERE subscription_end < ? AND is_active = 1",
                (now,)
            )
            await db.commit()
        
        return expired_users


async def get_service_by_id(service_id: int):
    """Get service by ID"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("SELECT id, name, duration_days, price, duration_unit FROM services WHERE id = ?", (service_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "duration_days": row[2],
                "price": row[3],
                "duration_unit": row[4] or 'days'
            }
        return None


async def upsert_user_profile(user_id: int, username: str | None, phone_number: str | None, photo_file_id: str | None):
    """Create or update user profile fields"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, phone_number, subscription_end, is_active, photo_file_id)
            VALUES (?, ?, ?, NULL, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(?, username),
                phone_number = COALESCE(?, phone_number),
                photo_file_id = COALESCE(?, photo_file_id)
            """,
            (user_id, username, phone_number, photo_file_id, username, phone_number, photo_file_id)
        )
        await db.commit()


async def get_user(user_id: int):
    """Get single user by id"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            "SELECT user_id, username, phone_number, subscription_end, is_active, photo_file_id, added_to_channel FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "phone_number": row[2],
            "subscription_end": row[3],
            "is_active": row[4],
            "photo_file_id": row[5],
            "added_to_channel": row[6] if len(row) > 6 else 0
        }


async def search_users_by_username(query: str, offset: int = 0, limit: int = 20):
    """Search users by username (case-insensitive, contains) with pagination"""
    like = f"%{query.lower()}%"
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            """
            SELECT user_id, username, phone_number, subscription_end, is_active, photo_file_id
            FROM users
            WHERE LOWER(COALESCE(username, '')) LIKE ?
            ORDER BY username IS NULL, username
            LIMIT ? OFFSET ?
            """,
            (like, limit, offset)
        )
        rows = await cursor.fetchall()
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "phone_number": row[2],
                "subscription_end": row[3],
                "is_active": row[4],
                "photo_file_id": row[5]
            }
            for row in rows
        ]


async def get_users_paginated(offset: int = 0, limit: int = 20):
    """Get users with pagination (alphabetical by username)"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute(
            """
            SELECT user_id, username, phone_number, subscription_end, is_active, photo_file_id
            FROM users
            ORDER BY username IS NULL, username
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "phone_number": row[2],
                "subscription_end": row[3],
                "is_active": row[4],
                "photo_file_id": row[5]
            }
            for row in rows
        ]


async def mark_user_added_to_channel(user_id: int):
    """Mark user as added to channel"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            "UPDATE users SET added_to_channel = 1, channel_member_removed = 0 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def mark_user_removed_from_channel(user_id: int):
    """Mark user as removed from channel"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            "UPDATE users SET channel_member_removed = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_bot_setting(key: str, default: str = None):
    """Get bot setting value"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_bot_setting(key: str, value: str):
    """Set bot setting value"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def get_shortest_active_subscription_seconds():
    """Get the time in seconds until the next subscription expires"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        now = datetime.now()
        cursor = await db.execute(
            "SELECT subscription_end FROM users WHERE is_active = 1 AND subscription_end > ? ORDER BY subscription_end ASC LIMIT 1",
            (now.isoformat(),)
        )
        row = await cursor.fetchone()
        if row:
            expiry_time = datetime.fromisoformat(row[0])
            seconds_until_expiry = (expiry_time - now).total_seconds()
            return max(30, min(seconds_until_expiry, 3600))
        return 3600


async def get_bot_config(key: str, default: str = None):
    """Get user bot configuration value"""
    return await get_bot_setting(f"userbot_{key}", default)


async def set_bot_config(key: str, value: str):
    """Set user bot configuration value"""
    await set_bot_setting(f"userbot_{key}", value)


async def init_default_bot_config():
    """Initialize default bot configuration"""
    defaults = {
        "welcome_message": "👋 <b>Добро пожаловать!</b>\n\nЭтот бот предоставляет доступ к приватному каналу.\n\nВыберите действие:",
        "btn_buy": "🛍 Купить подписку",
        "btn_renew": "🔄 Продлить подписку",
        "btn_my_sub": "ℹ️ Моя подписка",
        "btn_contact": "✉️ Связаться с админом"
    }
    
    async with aiosqlite.connect(DATABASE_FILE) as db:
        for key, value in defaults.items():
            cursor = await db.execute(
                "SELECT value FROM bot_settings WHERE key = ?",
                (f"userbot_{key}",)
            )
            if not await cursor.fetchone():
                await db.execute(
                    "INSERT INTO bot_settings (key, value) VALUES (?, ?)",
                    (f"userbot_{key}", value)
                )
        await db.commit()
