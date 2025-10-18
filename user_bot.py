# Полный исправленный user_bot.py — замените текущий файл этим содержимым
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токены
USER_BOT_TOKEN = getattr(config, "USER_BOT_TOKEN", None)
ADMIN_BOT_TOKEN = getattr(config, "ADMIN_BOT_TOKEN", None)
if USER_BOT_TOKEN is None or ADMIN_BOT_TOKEN is None:
    raise RuntimeError("USER_BOT_TOKEN и ADMIN_BOT_TOKEN должны быть заданы в config.py")

# PRIVATE_CHANNEL_ID (опционально)
try:
    PRIVATE_CHANNEL_ID = int(config.PRIVATE_CHANNEL_ID) if config.PRIVATE_CHANNEL_ID is not None else None
except Exception:
    PRIVATE_CHANNEL_ID = None

# Инициализация ботов (aiogram >=3.7)
bot = Bot(token=USER_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
admin_bot = Bot(token=ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Файл с языковыми настройками (используется и admin_bot)
LANG_FILE = "user_languages.json"

def load_langs() -> Dict[str, str]:
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить {LANG_FILE}: {e}")
    return {}

def save_langs(m: Dict[str, str]):
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить {LANG_FILE}: {e}")

user_langs = load_langs()

# Набор переводов (минимальный; можно расширить)
translations = {
    "ru": {
        "welcome": "👋 <b>Добро пожаловать!</b>\n\nЭтот бот предоставляет доступ к приватному каналу.\n\nВыберите действие:",
        "buy": "🛍️ Купить подписку",
        "renew": "🔄 Продлить подписку",
        "cancel": "✖️ Отменить подписку",
        "my_subscription": "ℹ️ Моя подписка",
        "contact_admin": "✉️ Связаться с админом",
        "no_services": "❌ Услуги временно недоступны.",
        "request_sent": "✅ Заявка отправлена! Ожидайте подтверждения администрации.",
        "no_subscription": "ℹ️ У вас нет активной подписки.\n\nДля покупки нажмите кнопку ниже.",
        "subscription_active": "✅ <b>Подписка активна</b>\n\n📅 До: {date}\n⏳ Осталось: {left}",
        "subscription_expired": "❌ <b>Подписка истекла</b>\n\nДля продления нажмите кнопку ниже.",
        "cancel_confirm": "Вы действительно хотите отменить подписку? Это действие закроет доступ к каналу.",
        "cancel_done": "✅ Ваша подписка отменена. Доступ к каналу закрыт.",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "lang_set": "Язык установлен: {lang}",
        "no_admin_notify": "❗ Не удалось отправить уведомление админам. Проверьте ADMIN_USER_IDS."
    },
    "en": {
        "welcome": "👋 <b>Welcome!</b>\n\nThis bot provides access to a private channel.\n\nChoose an action:",
        "buy": "🛍️ Buy subscription",
        "renew": "🔄 Renew subscription",
        "cancel": "✖️ Cancel subscription",
        "my_subscription": "ℹ️ My subscription",
        "contact_admin": "✉️ Contact admin",
        "no_services": "❌ Services are temporarily unavailable.",
        "request_sent": "✅ Request sent! Wait for admin confirmation.",
        "no_subscription": "ℹ️ You don't have an active subscription.\n\nTo buy, use the button below.",
        "subscription_active": "✅ <b>Subscription active</b>\n\n📅 Until: {date}\n⏳ Left: {left}",
        "subscription_expired": "❌ <b>Subscription expired</b>\n\nTo renew, use the button below.",
        "cancel_confirm": "Do you really want to cancel the subscription? This will close access to the channel.",
        "cancel_done": "✅ Your subscription has been cancelled. Channel access closed.",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "lang_set": "Language set: {lang}",
        "no_admin_notify": "❗ Failed to notify admins. Check ADMIN_USER_IDS."
    },
    "ar": {
        "welcome": "👋 <b>مرحباً!</b>\n\nهذا البوت يمنحك الوصول إلى القناة الخاصة.\n\nاختر إجراء:",
        "buy": "🛍️ شراء الاشتراك",
        "renew": "🔄 تجديد الاشتراك",
        "cancel": "✖️ إلغاء الاشتراك",
        "my_subscription": "ℹ️ اشتراكي",
        "contact_admin": "✉️ تواصل مع المشرف",
        "no_services": "❌ الخدمات غير متاحة مؤقتاً.",
        "request_sent": "✅ تم إرسال الطلب! انتظر تأكيد المشرف.",
        "no_subscription": "ℹ️ ليس لديك اشتراك نشط.\n\nللشراء اضغط الزر أدناه.",
        "subscription_active": "✅ <b>الاشتراك نشط</b>\n\n📅 حتى: {date}\n⏳ المتبقي: {left}",
        "subscription_expired": "❌ <b>انتهى الاشتراك</b>\n\nللتمديد اضغط الزر أدناه.",
        "cancel_confirm": "هل تريد حقاً إلغاء الاشتراك؟ سيؤدي هذا إلى إغلاق الوصول إلى القناة.",
        "cancel_done": "✅ تم إلغاء اشتراكك. تم إغلاق الوصول إلى القناة.",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "lang_set": "تم ضبط اللغة: {lang}",
        "no_admin_notify": "❗ فشل في إبلاغ المشرفين. تحقق من ADMIN_USER_IDS."
    },
    "uz": {
        "welcome": "👋 <b>Xush kelibsiz!</b>\n\nUshbu bot sizga xususiy kanalga kirish imkonini beradi.\n\nHarakatni tanlang:",
        "buy": "🛍️ Obunani sotib olish",
        "renew": "🔄 Obunani yangilash",
        "cancel": "✖️ Obunani bekor qilish",
        "my_subscription": "ℹ️ Mening obunam",
        "contact_admin": "✉️ Admin bilan bog'lanish",
        "no_services": "❌ Xizmatlar vaqtincha mavjud emas.",
        "request_sent": "✅ So'rov yuborildi! Admin tasdig'ini kuting.",
        "no_subscription": "ℹ️ Sizda faol obuna yo'q.\n\nSotib olish uchun pastdagi tugmani bosing.",
        "subscription_active": "✅ <b>Obuna faol</b>\n\n📅 Gacha: {date}\n⏳ Qoldi: {left}",
        "subscription_expired": "❌ <b>Obuna muddati tugagan</b>\n\nYangilash uchun pastdagi tugmani bosing.",
        "cancel_confirm": "Obunani bekor qilmoqchimisiz? Bu kanalga kirishni yopadi.",
        "cancel_done": "✅ Obunangiz bekor qilindi. Kanalga kirish yopildi.",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "lang_set": "Til o'rnatildi: {lang}",
        "no_admin_notify": "❗ Adminlarga xabar jo'natilmadi. ADMIN_USER_IDS ni tekshiring."
    }
}

def get_user_lang(user_id: int) -> str:
    code = user_langs.get(str(user_id))
    return code if code in translations else "ru"

def tr(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_lang(user_id)
    text = translations.get(lang, translations["ru"]).get(key, "")
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

# FSM
class Purchase(StatesGroup):
    selecting_service = State()

class ContactAdmin(StatesGroup):
    waiting_for_message = State()

def get_main_keyboard(user_id: int, active: bool = False) -> InlineKeyboardMarkup:
    lang = get_user_lang(user_id)
    strings = translations.get(lang, translations["ru"])
    buttons = []
    if active:
        buttons.append([InlineKeyboardButton(text=strings["renew"], callback_data="buy_subscription")])
        buttons.append([InlineKeyboardButton(text=strings["cancel"], callback_data="cancel_subscription")])
    else:
        buttons.append([InlineKeyboardButton(text=strings["buy"], callback_data="buy_subscription")])
    buttons.append([InlineKeyboardButton(text=strings["my_subscription"], callback_data="my_subscription")])
    buttons.append([InlineKeyboardButton(text=strings["contact_admin"], callback_data="contact_admin")])
    # language buttons
    buttons.append([
        InlineKeyboardButton(text="🇷🇺 Рус", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 En", callback_data="lang_en"),
        InlineKeyboardButton(text="🇦🇪 ع", callback_data="lang_ar"),
        InlineKeyboardButton(text="🇺🇿 Uz", callback_data="lang_uz"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# LANGUAGE handlers
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    code = callback.data.replace("lang_", "")
    if code not in translations:
        await callback.answer("Unsupported language", show_alert=True)
        return
    user_langs[str(callback.from_user.id)] = code
    save_langs(user_langs)
    await callback.answer()
    active = await _is_active(callback.from_user.id)
    await callback.message.edit_text(tr(callback.from_user.id, "lang_set", lang=code), reply_markup=get_main_keyboard(callback.from_user.id, active=active))

# helper to check DB active state and synchronise expiry
async def _is_active(user_id: int) -> bool:
    try:
        subscription = await db.get_user_subscription(user_id)
    except Exception:
        return False
    if not subscription:
        return False
    active = bool(subscription.get("is_active", False))
    end = subscription.get("subscription_end")
    if end:
        try:
            end_dt = datetime.fromisoformat(end) if isinstance(end, str) else end
            if isinstance(end_dt, datetime) and end_dt <= datetime.now():
                # deactivate in DB to keep consistent
                try:
                    if hasattr(db, "deactivate_user_subscription"):
                        await db.deactivate_user_subscription(user_id)
                    elif hasattr(db, "set_user_subscription_active"):
                        await db.set_user_subscription_active(user_id, False)
                except Exception:
                    logger.debug("Не удалось деактивировать подписку при сверке")
                return False
        except Exception:
            pass
    return active

# START
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    # save profile photo if possible
    photo_file_id = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception:
        photo_file_id = None
    try:
        if hasattr(db, "upsert_user_profile"):
            await db.upsert_user_profile(user.id, user.username, None, photo_file_id)
    except Exception:
        logger.debug("upsert_user_profile failed (ignored)")

    # ask language if not set
    if str(user.id) not in user_langs:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Рус", callback_data="lang_ru"),
             InlineKeyboardButton(text="🇬🇧 En", callback_data="lang_en"),
             InlineKeyboardButton(text="🇦🇪 ع", callback_data="lang_ar"),
             InlineKeyboardButton(text="🇺🇿 Uz", callback_data="lang_uz")]
        ])
        await state.clear()
        await message.answer(translations["ru"]["choose_lang"], reply_markup=kb)
        return

    active = await _is_active(user.id)
    await state.clear()
    await message.answer(tr(user.id, "welcome"), reply_markup=get_main_keyboard(user.id, active=active))

# contact admin
@dp.callback_query(F.data == "contact_admin")
async def contact_admin_start(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(tr(callback.from_user.id, "contact_admin"))
    await dp.current_state(user=callback.from_user.id).set_state(ContactAdmin.waiting_for_message)

@dp.message(ContactAdmin.waiting_for_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    text = message.text or ""
    admins = getattr(config, "ADMIN_USER_IDS", []) or []
    sent_any = False
    for admin_id in admins:
        try:
            await admin_bot.send_message(admin_id, f"💬 Сообщение от @{message.from_user.username or 'user'} (ID {message.from_user.id}):\n\n{text}")
            sent_any = True
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение админу {admin_id}: {e}")
    if not sent_any:
        await message.answer(tr(message.from_user.id, "no_admin_notify"))
    try:
        subscription = await db.get_user_subscription(message.from_user.id)
    except Exception:
        subscription = None
    is_active = bool(subscription and subscription.get("is_active", False))
    await state.clear()
    await message.answer("✅ " + tr(message.from_user.id, "request_sent"), reply_markup=get_main_keyboard(message.from_user.id, active=is_active))

# buy flow (simplified)
@dp.callback_query(F.data == "buy_subscription")
async def buy_subscription_start(callback: types.CallbackQuery):
    await callback.answer()
    try:
        services = await db.get_services()
    except Exception:
        services = []
    if not services:
        await callback.message.edit_text(tr(callback.from_user.id, "no_services"))
        return
    buttons = []
    for s in services:
        unit = s.get("duration_unit", "days")
        u_lbl = {"minutes": "мин", "days": "дн", "months": "мес"}.get(unit, "дн")
        price = int(s.get("price", 0))
        buttons.append([InlineKeyboardButton(text=f"👉 {s['name']} — {price} руб. ({s['duration_days']} {u_lbl})", callback_data=f"service_{s['id']}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_purchase")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("🛍️ <b>Выберите услугу:</b>", reply_markup=kb)

@dp.callback_query(F.data == "cancel_purchase")
async def cancel_purchase_cb(callback: types.CallbackQuery):
    await callback.answer()
    active = await _is_active(callback.from_user.id)
    await callback.message.edit_text("Действие отменено.", reply_markup=get_main_keyboard(callback.from_user.id, active=active))

@dp.callback_query(F.data.startswith("service_"))
async def service_selected(callback: types.CallbackQuery):
    await callback.answer()
    try:
        service_id = int(callback.data.replace("service_", ""))
    except Exception:
        await callback.message.edit_text("Ошибка: неверный ID услуги.")
        return
    try:
        service = await db.get_service_by_id(service_id)
    except Exception:
        service = None
    if not service:
        await callback.message.edit_text("Услуга не найдена.")
        return

    user = callback.from_user
    username = user.username or f"id{user.id}"
    photo_file_id = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception:
        photo_file_id = None
    try:
        if hasattr(db, "upsert_user_profile"):
            await db.upsert_user_profile(user.id, user.username, None, photo_file_id)
    except Exception:
        logger.debug("upsert_user_profile failed (ignored)")
    try:
        purchase_id = await db.add_pending_purchase(user.id, username, None, service_id)
    except Exception:
        await callback.message.edit_text("❌ Ошибка создания заявки. Попробуйте позже.")
        return
    await send_admin_notification(user.id, username, None, service, purchase_id, photo_file_id)
    unit = service.get("duration_unit", "days")
    unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
    await callback.message.edit_text(
        tr(callback.from_user.id, "request_sent") + "\n\n"
        f"Услуга: <b>{service['name']}</b>\n"
        f"Цена: {int(service['price'])} руб.\n"
        f"Срок: {service['duration_days']} {unit_text}",
        reply_markup=get_main_keyboard(callback.from_user.id, active=False)
    )

async def send_admin_notification(user_id: int, username: str, phone_number: Optional[str], service: dict, purchase_id: int, photo_file_id: Optional[str]):
    admins = getattr(config, "ADMIN_USER_IDS", []) or []
    sent_any = False
    unit = service.get("duration_unit", "days")
    unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
    price = int(service.get("price", 0))
    text = (
        f"📦 <b>Новая заявка на покупку</b>\n\n"
        f"👤 Пользователь: @{username}\n"
        f"🆔 ID: {user_id}\n"
        f"📱 Телефон: {phone_number or 'Не указан'}\n\n"
        f"📦 Услуга: <b>{service['name']}</b>\n"
        f"💰 Цена: {price} ₽\n"
        f"⏱ Срок: {service['duration_days']} {unit_text}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{purchase_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{purchase_id}")]
    ])
    for admin_id in admins:
        try:
            if photo_file_id:
                await admin_bot.send_photo(admin_id, photo_file_id, caption=text, reply_markup=kb)
            else:
                await admin_bot.send_message(admin_id, text, reply_markup=kb)
            sent_any = True
        except Exception as e:
            logger.warning(f"Не удалось уведомить админа {admin_id}: {e}")
    if not sent_any:
        logger.error("Не удалось уведомить ни одного админа о заявке.")

# MY SUBSCRIPTION
@dp.callback_query(F.data == "my_subscription")
async def my_subscription(callback: types.CallbackQuery):
    await callback.answer()
    try:
        subscription = await db.get_user_subscription(callback.from_user.id)
    except Exception:
        subscription = None
    if not subscription or not subscription.get("subscription_end"):
        await callback.message.edit_text(tr(callback.from_user.id, "no_subscription"), reply_markup=get_main_keyboard(callback.from_user.id, active=False))
        return
    try:
        end_dt = datetime.fromisoformat(subscription["subscription_end"]) if isinstance(subscription["subscription_end"], str) else subscription["subscription_end"]
    except Exception:
        end_dt = None
    is_active = bool(subscription.get("is_active", False) and end_dt and end_dt > datetime.now())
    if is_active and end_dt:
        remain = end_dt - datetime.now()
        days = remain.days
        hours = remain.seconds // 3600
        minutes = (remain.seconds % 3600) // 60
        parts = []
        if days > 0:
            parts.append(f"{days} дн.")
        if hours > 0:
            parts.append(f"{hours} ч.")
        if minutes > 0 or not parts:
            parts.append(f"{minutes} мин.")
        left = " ".join(parts)
        await callback.message.edit_text(tr(callback.from_user.id, "subscription_active", date=end_dt.strftime("%d.%m.%Y %H:%M"), left=left), reply_markup=get_main_keyboard(callback.from_user.id, active=True))
    else:
        try:
            if hasattr(db, "deactivate_user_subscription"):
                await db.deactivate_user_subscription(callback.from_user.id)
            elif hasattr(db, "set_user_subscription_active"):
                await db.set_user_subscription_active(callback.from_user.id, False)
        except Exception:
            logger.debug("Не удалось синхронизировать статус подписки")
        await callback.message.edit_text(tr(callback.from_user.id, "subscription_expired"), reply_markup=get_main_keyboard(callback.from_user.id, active=False))

# CANCEL SUBSCRIPTION
@dp.callback_query(F.data == "cancel_subscription")
async def cancel_subscription_prompt(callback: types.CallbackQuery):
    await callback.answer()
    try:
        subscription = await db.get_user_subscription(callback.from_user.id)
    except Exception:
        subscription = None
    if not subscription or not subscription.get("is_active"):
        await callback.message.answer("❌ " + tr(callback.from_user.id, "no_subscription"))
        await callback.message.edit_text(tr(callback.from_user.id, "no_subscription"), reply_markup=get_main_keyboard(callback.from_user.id, active=False))
        return
    yes_label = translations[get_user_lang(callback.from_user.id)]["cancel_confirm_buttons"][0] if "cancel_confirm_buttons" in translations.get(get_user_lang(callback.from_user.id), {}) else "✅ Подтвердить"
    no_label = translations[get_user_lang(callback.from_user.id)]["cancel_confirm_buttons"][1] if "cancel_confirm_buttons" in translations.get(get_user_lang(callback.from_user.id), {}) else "❌ Отменить"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=yes_label, callback_data="confirm_cancel_subscription"),
         InlineKeyboardButton(text=no_label, callback_data="cancel_cancel_subscription")]
    ])
    await callback.message.edit_text(tr(callback.from_user.id, "cancel_confirm"), reply_markup=kb)

@dp.callback_query(F.data == "cancel_cancel_subscription")
async def cancel_cancel_subscription(callback: types.CallbackQuery):
    await callback.answer()
    active = await _is_active(callback.from_user.id)
    await callback.message.edit_text("Отменено.", reply_markup=get_main_keyboard(callback.from_user.id, active=active))

@dp.callback_query(F.data == "confirm_cancel_subscription")
async def confirm_cancel_subscription(callback: types.CallbackQuery):
    await callback.answer("Обрабатываю...")
    user_id = callback.from_user.id
    try:
        if hasattr(db, "deactivate_user_subscription"):
            await db.deactivate_user_subscription(user_id)
        elif hasattr(db, "set_user_subscription_active"):
            await db.set_user_subscription_active(user_id, False)
        elif hasattr(db, "clear_user_subscription"):
            await db.clear_user_subscription(user_id)
        else:
            raise RuntimeError("DB: нет функции для деактивации подписки")
    except Exception as e:
        logger.exception("Ошибка деактивации подписки")
        await callback.message.edit_text(tr(user_id, "cancel_done"), reply_markup=get_main_keyboard(user_id, active=True))
        return
    if PRIVATE_CHANNEL_ID is not None:
        try:
            await admin_bot.ban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=user_id)
            await asyncio.sleep(0.3)
            await admin_bot.unban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=user_id)
            if hasattr(db, "mark_user_removed_from_channel"):
                try:
                    await db.mark_user_removed_from_channel(user_id)
                except Exception:
                    logger.debug("Не удалось отметить удаление в БД")
        except Exception as e:
            logger.warning(f"Не удалось удалить из канала: {e}")
    try:
        await callback.message.edit_text(tr(user_id, "cancel_done"), reply_markup=get_main_keyboard(user_id, active=False))
    except Exception:
        pass
    admins = getattr(config, "ADMIN_USER_IDS", []) or []
    notif_text = tr(user_id, "admin_notify_cancel", username=callback.from_user.username or "", id=user_id) if "admin_notify_cancel" in translations[get_user_lang(user_id)] else f"Пользователь @{callback.from_user.username or ''} (ID {user_id}) отменил подписку."
    sent_any = False
    for admin_id in admins:
        try:
            await admin_bot.send_message(admin_id, notif_text)
            sent_any = True
        except Exception:
            logger.warning("Не удалось уведомить админа об отмене подписки.")
    if not sent_any:
        logger.warning("Не удалось уведомить ни одного админа о снятии подписки пользователем.")

# SEND expiry notification — this function is required by main.py
async def send_expiry_notification(user_id: int):
    """Отправляет юзеру уведомление об истечении подписки."""
    try:
        await bot.send_message(user_id, "⚠️ <b>Ваша подписка истекла</b>\n\nДоступ к каналу закрыт.\n\nДля покупки/продления используйте /start")
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление об истечении подписки пользователю {user_id}: {e}")

# helper to send invite link (admin_bot uses this pattern; keep present)
async def send_invite_link(user_id: int, invite_link: str):
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Присоединиться к каналу", url=invite_link)]
        ])
        await bot.send_message(user_id, "✅ <b>Подписка активирована!</b>\n\nНажмите кнопку ниже, чтобы присоединиться к приватному каналу:", reply_markup=kb)
    except Exception as e:
        logger.warning(f"Не удалось отправить инвайт ссылку пользователю {user_id}: {e}")

# init helper
async def init_user_bot():
    try:
        await db.init_db()
    except Exception:
        logger.debug("init_db not available or failed")

# Exported names: dp, bot, send_expiry_notification, init_user_bot are present for main.py
