# Configuration file for Telegram Bot System

# Bot Tokens
ADMIN_BOT_TOKEN = "7960533394:AAHUP9N6NqevWLQwS2JC2DLP0A4BXEUDMd4"
USER_BOT_TOKEN = "7369558316:AAGToxWV6pmSuG6ZdOl6m3IVPeJRG5lFu6g"

# Channel Configuration
# ВАЖНО: Не используйте публичную ссылку! Бот будет создавать персональные пригласительные ссылки.
# To get PRIVATE_CHANNEL_ID:
# 1. Forward a message from your channel to @userinfobot
# 2. Copy the channel ID (it will be negative number)
# 3. Paste it here
PRIVATE_CHANNEL_ID = -1003009524347  # REPLACE THIS WITH YOUR ACTUAL CHANNEL ID

# ⚠️ ОБЯЗАТЕЛЬНАЯ НАСТРОЙКА:
# Добавьте ADMIN бота (@kanalilgabot) в ваш канал как администратора с правами:
# ✅ Приглашать пользователей через ссылку (Invite Users via Link)
# ✅ Управление пользователями (Ban users)
# Без этих прав бот не сможет добавлять/удалять пользователей!

# Admin Configuration
# To get your admin user ID:
# 1. Send a message to @userinfobot
# 2. Copy your user ID
# 3. Add it to the list below
ADMIN_USER_IDS = [5912983856]  # Example: [123456789, 987654321]

# Default Service Configuration
DEFAULT_SERVICE_NAME = "1 месяц подписки"
DEFAULT_SERVICE_DURATION = 30  # days
DEFAULT_SERVICE_PRICE = 15000.0  # rubles

# Check interval for expired subscriptions (in seconds)
EXPIRY_CHECK_INTERVAL = 3600  # 1 hour

# Bot silent mode: when True, user-facing messages are sent without notifications
SILENT_MODE = False

