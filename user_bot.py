import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import database as db
import config

USER_BOT_TOKEN = config.USER_BOT_TOKEN
ADMIN_BOT_TOKEN = config.ADMIN_BOT_TOKEN

bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)

ADMIN_CHAT_ID = config.ADMIN_USER_IDS[0] if config.ADMIN_USER_IDS else None


class Purchase(StatesGroup):
    selecting_service = State()


class ContactAdmin(StatesGroup):
    waiting_for_message = State()


def get_main_keyboard(active: bool = False):
    """Get main user inline keyboard"""
    buttons = []
    if active:
        buttons.append([InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="buy_subscription")])
    else:
        buttons.append([InlineKeyboardButton(text="🛍 Купить подписку", callback_data="buy_subscription")])
    buttons.append([InlineKeyboardButton(text="ℹ️ Моя подписка", callback_data="my_subscription")])
    buttons.append([InlineKeyboardButton(text="✉️ Связаться с админом", callback_data="contact_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(Command("start"))
async def user_start(message: types.Message):
    """User bot start command"""
    photo_file_id = None
    try:
        photos = await bot.get_user_profile_photos(message.from_user.id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception as e:
        logging.error(f"Failed to get user photo on start: {e}")
    
    try:
        await db.upsert_user_profile(
            user_id=message.from_user.id,
            username=message.from_user.username,
            phone_number=None,
            photo_file_id=photo_file_id
        )
    except Exception as e:
        logging.error(f"Failed to upsert user profile: {e}")
    
    subscription = await db.get_user_subscription(message.from_user.id)
    is_active = subscription and subscription.get('is_active', False)
    
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Этот бот предоставляет доступ к приватному каналу.\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(active=is_active),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "contact_admin")
async def contact_admin_start(callback: types.CallbackQuery, state: FSMContext):
    """Start contact admin flow"""
    await callback.answer()
    await callback.message.edit_text("Напишите ваше сообщение администратору:")
    await state.set_state(ContactAdmin.waiting_for_message)


@dp.message(ContactAdmin.waiting_for_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    """Send message to admin"""
    text = message.text
    
    for admin_id in config.ADMIN_USER_IDS or []:
        try:
            await admin_bot.send_message(
                admin_id,
                f"💬 Сообщение от @{message.from_user.username or 'user'} (ID {message.from_user.id}):\n\n{text}"
            )
        except Exception as e:
            logging.error(f"Failed to send message to admin {admin_id}: {e}")
    
    subscription = await db.get_user_subscription(message.from_user.id)
    is_active = subscription and subscription.get('is_active', False)
    
    await state.clear()
    await message.answer("✅ Сообщение отправлено администратору.", reply_markup=get_main_keyboard(active=is_active))


@dp.callback_query(F.data == "buy_subscription")
async def buy_subscription_start(callback: types.CallbackQuery, state: FSMContext):
    """Start subscription purchase"""
    await callback.answer()
    
    services = await db.get_services()
    
    if not services:
        await callback.message.edit_text("❌ К сожалению, услуги временно недоступны")
        return
    
    buttons = []
    for s in services:
        unit = s.get('duration_unit', 'days')
        unit_label = {"minutes": "мин", "days": "дн", "months": "мес"}.get(unit, "дн")
        price_str = f"{int(s['price'])} руб."
        duration_str = f"({s['duration_days']} {unit_label})"
        label = f"👉 {s['name']} - {price_str} {duration_str}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"service_{s['id']}")])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_purchase")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "🛍 <b>Выберите услугу:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await state.set_state(Purchase.selecting_service)


@dp.callback_query(F.data == "cancel_purchase")
async def cancel_purchase(callback: types.CallbackQuery, state: FSMContext):
    """Cancel purchase"""
    await callback.answer()
    await state.clear()
    
    subscription = await db.get_user_subscription(callback.from_user.id)
    is_active = subscription and subscription.get('is_active', False)
    
    await callback.message.edit_text(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Этот бот предоставляет доступ к приватному каналу.\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(active=is_active),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("service_"), Purchase.selecting_service)
async def select_service(callback: types.CallbackQuery, state: FSMContext):
    """Handle service selection"""
    await callback.answer()
    
    service_id = int(callback.data.replace("service_", ""))
    service = await db.get_service_by_id(service_id)
    
    if not service:
        await callback.message.edit_text("Услуга не найдена.")
        return
    
    await state.update_data(service_id=service["id"], service=service)
    
    phone_number = None
    try:
        user_row = await db.get_user(callback.from_user.id)
        if user_row and user_row.get("phone_number"):
            phone_number = user_row["phone_number"]
    except Exception:
        pass
    
    await process_purchase(callback, state, phone_number)


async def process_purchase(callback: types.CallbackQuery, state: FSMContext, phone_number: str | None):
    """Process the purchase request"""
    data = await state.get_data()
    service = data['service']
    
    user = callback.from_user
    username = user.username or f"id{user.id}"
    
    photo_file_id = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception as e:
        logging.error(f"Failed to get user photo: {e}")
    
    try:
        await db.upsert_user_profile(user.id, user.username, phone_number, photo_file_id)
    except Exception:
        pass
    
    purchase_id = await db.add_pending_purchase(
        user.id,
        username,
        phone_number,
        data['service_id']
    )
    
    await send_admin_notification(
        user.id,
        username,
        phone_number,
        service,
        purchase_id,
        photo_file_id
    )
    
    unit = service.get('duration_unit', 'days')
    unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
    
    subscription = await db.get_user_subscription(callback.from_user.id)
    is_active = subscription and subscription.get('is_active', False)
    
    await callback.message.edit_text(
        "✅ <b>Заявка отправлена!</b>\n\n"
        f"Услуга: <b>{service['name']}</b>\n"
        f"Цена: {int(service['price'])} руб.\n"
        f"Срок: {service['duration_days']} {unit_text}\n\n"
        "Ожидайте подтверждения от администратора.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(active=is_active)
    )
    
    await state.clear()


async def send_admin_notification(user_id: int, username: str, phone_number: str | None, service: dict, purchase_id: int, photo_file_id: str | None):
    """Send purchase notification to admin"""
    unit = service.get('duration_unit', 'days')
    unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
    
    price_formatted = f"{int(service['price']):,}".replace(',', ' ')
    text = (
        f"🛍 <b>Новая заявка на покупку!</b>\n\n"
        f"👤 Пользователь: @{username}\n"
        f"🆔 ID: {user_id}\n"
        f"📱 Телефон: {phone_number or 'Не указан'}\n\n"
        f"📦 Услуга: <b>{service['name']}</b>\n"
        f"💰 Цена: {price_formatted} ₽\n"
        f"⏱ Срок: {service['duration_days']} {unit_text}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{purchase_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{purchase_id}")
        ]
    ])
    
    for admin_id in config.ADMIN_USER_IDS or []:
        try:
            if photo_file_id:
                await admin_bot.send_photo(
                    admin_id,
                    photo_file_id,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await admin_bot.send_message(
                    admin_id,
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            logging.info(f"Notification sent to admin {admin_id}")
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")


@dp.callback_query(F.data == "my_subscription")
async def check_subscription(callback: types.CallbackQuery):
    """Check subscription status"""
    await callback.answer()
    
    subscription = await db.get_user_subscription(callback.from_user.id)
    
    if not subscription or not subscription.get('subscription_end'):
        is_active = False
        text = "ℹ️ У вас нет активной подписки.\n\nДля покупки нажмите кнопку ниже."
    else:
        subscription_end = datetime.fromisoformat(subscription['subscription_end'])
        is_active = subscription.get('is_active', False) and subscription_end > datetime.now()
        
        if is_active:
            time_left = subscription_end - datetime.now()
            days = time_left.days
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            
            time_str = []
            if days > 0:
                time_str.append(f"{days} дн.")
            if hours > 0:
                time_str.append(f"{hours} ч.")
            if minutes > 0 or not time_str:
                time_str.append(f"{minutes} мин.")
            
            text = (
                f"✅ <b>Подписка активна</b>\n\n"
                f"📅 До: {subscription_end.strftime('%d.%m.%Y %H:%M')}\n"
                f"⏳ Осталось: {' '.join(time_str)}"
            )
        else:
            text = "❌ <b>Подписка истекла</b>\n\nДля продления нажмите кнопку ниже."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(active=is_active),
        parse_mode="HTML"
    )


async def send_expiry_notification(user_id: int):
    """Send expiry notification to user"""
    try:
        await bot.send_message(
            user_id,
            "⚠️ <b>Ваша подписка истекла</b>\n\n"
            "Доступ к каналу закрыт.\n\n"
            "Для продления подписки используйте /start",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Failed to send expiry notification to {user_id}: {e}")


async def send_invite_link(user_id: int, invite_link: str):
    """Send channel invite link to user"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Присоединиться к каналу", url=invite_link)]
        ])
        
        await bot.send_message(
            user_id,
            "✅ <b>Подписка активирована!</b>\n\n"
            "Нажмите кнопку ниже, чтобы присоединиться к приватному каналу:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Failed to send invite link to {user_id}: {e}")
