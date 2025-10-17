# Telegram Bot Management System

## Overview
A comprehensive dual-bot Telegram system for managing subscription-based access to a private channel. The system consists of an admin bot for management and a user bot for customer interactions.

## Current State (Updated: October 14, 2025)
- ✅ Both bots running successfully
- ✅ Automatic channel membership management implemented
- ✅ Flexible subscription durations (minutes/days/months)
- ✅ Advanced user search and broadcast features
- ✅ Automatic expiry checking and user removal

## Recent Changes
- **October 14, 2025**: Complete system redesign with enhanced features
  - Implemented automatic channel add/remove functionality
  - Added flexible service duration system (1 minute to 1 year)
  - Created advanced broadcast system with user selection
  - Implemented username-based search with pagination
  - Enhanced UI with proper menu cleanup
  - Added automatic expiry checker that removes users from channel

## Project Architecture

### File Structure
```
.
├── main.py              # Main entry point, runs both bots
├── admin_bot.py         # Admin bot for subscription management
├── user_bot.py          # User bot for customer interactions
├── database.py          # Database operations (SQLite)
├── config.py            # Bot configuration and settings
└── requirements.txt     # Python dependencies
```

### Key Components

#### 1. Admin Bot (@navaviy_bot)
**Main Features:**
- **Service Management**: Create/edit/delete subscription services with flexible durations
- **User Search**: Search users by username with autocomplete
- **Statistics**: Paginated user list with subscription status
- **Broadcasting**: Send messages to all users or individual users
- **Channel Diagnostics**: Test channel permissions and bot setup
- **Purchase Confirmation**: Approve/reject user subscription requests

**Button Interface:**
- 💼 Управление услугами (Service Management)
- 🔎 Поиск пользователя (User Search)
- 📊 Статистика пользователей (User Statistics)
- ✉️ Рассылка всем (Broadcast All)
- 👤 Сообщение пользователю (Direct Message)
- 🔧 Диагностика канала (Channel Diagnostics)
- 🔔 Режим тишины (Silent Mode)

#### 2. User Bot (@Am_in_bot)
**Main Features:**
- **Subscription Purchase**: Browse and purchase available services
- **Subscription Status**: Check current subscription details
- **Contact Admin**: Send messages to administrators
- **Automatic Profile Updates**: Photo and username tracking

**Button Interface:**
- 🛍 Купить подписку / 🔄 Продлить подписку
- ℹ️ Моя подписка
- ✉️ Связаться с админом

#### 3. Database Schema
- **users**: User profiles with subscription data
- **services**: Available subscription services
- **pending_purchases**: Purchase requests awaiting approval
- **bot_settings**: Bot configuration storage

### Automated Systems

#### Automatic Channel Management
1. **On Purchase Confirmation**:
   - User subscription activated in database
   - Unique invite link created for user
   - Link sent to user via user bot
   - User marked as added to channel

2. **On Subscription Expiry**:
   - Expiry checker runs every hour (configurable)
   - Expired users automatically deactivated
   - Users removed from channel (ban + unban)
   - Expiry notification sent to users

#### Service Duration System
Supports three time units:
- **Minutes**: For short-term testing (1-525600 minutes)
- **Days**: For standard subscriptions (1-365 days)
- **Months**: For monthly plans (1-12 months)

## Configuration

### Required Setup
1. **Bot Tokens** (in config.py):
   - ADMIN_BOT_TOKEN: Admin bot token from @BotFather
   - USER_BOT_TOKEN: User bot token from @BotFather

2. **Channel Setup**:
   - PRIVATE_CHANNEL_ID: Your private channel ID (negative number)
   - Admin bot MUST be channel admin with permissions:
     - ✅ Invite Users via Link
     - ✅ Ban Users

3. **Admin Configuration**:
   - ADMIN_USER_IDS: List of admin Telegram user IDs

### Optional Settings
- EXPIRY_CHECK_INTERVAL: Seconds between expiry checks (default: 3600)
- SILENT_MODE: Send notifications silently (default: False)

## User Preferences
- Clean, intuitive button-based interface (no inline keyboards)
- Automatic menu cleanup to prevent clutter
- Professional Russian language interface
- Automatic user profile photo tracking
- Real-time subscription status updates

## Technical Details

### Dependencies
- aiogram 3.13.1: Telegram Bot API framework
- aiosqlite 0.20.0: Async SQLite database
- python-dotenv 1.0.0: Environment configuration

### Running the System
The system runs from `main.py` which:
1. Initializes the database
2. Starts the expiry checker (background task)
3. Starts admin bot polling
4. Starts user bot polling
5. Manages all tasks concurrently

### Workflow
```bash
python main.py
```

## Features Implementation Status

### ✅ Completed
- [x] Automatic channel membership management
- [x] Flexible service durations (minutes/days/months)
- [x] User search by username
- [x] Paginated user lists
- [x] Broadcast to all users
- [x] Direct message to specific users
- [x] Automatic expiry checking
- [x] Automatic user removal from channel
- [x] Clean button interface with menu cleanup
- [x] User profile photo tracking
- [x] Purchase request notifications
- [x] Subscription confirmation flow

### 🔄 Future Enhancements
- [ ] Payment integration (Stripe/YooKassa)
- [ ] Multi-language support
- [ ] Analytics dashboard
- [ ] Scheduled message broadcasting
- [ ] Admin activity logs
- [ ] Referral system

## Important Notes

### Channel Permissions
The admin bot MUST have these permissions in the private channel:
1. **Invite Users via Link**: Required to create invite links
2. **Ban Users**: Required to remove expired users

### Security
- Bot tokens stored in config.py (add to .gitignore)
- No hardcoded credentials in code
- Phone numbers optional, never required

### Debugging
- Channel diagnostics available in admin bot
- Silent mode toggle for testing
- Comprehensive logging in console

## Support
For issues or questions, use the admin bot's diagnostic tools or check the workflow logs.
