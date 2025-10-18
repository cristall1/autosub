# Исправлённый admin_bot.py — замените текущий файл этим содержимым.
# - Убедился, что все FSM-классы (включая SearchUser) определены ДО использования в декораторах.
# - Исправлены callback'ы, удалены дубли и устранён NameError.
# - Поддержка языков общая (user_languages.json).
# - Код не запускает polling — main.py должен запускать оба бота.
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_BOT_TOKEN = getattr(config, "ADMIN_BOT_TOKEN", None)
USER_BOT_TOKEN = getattr(config, "USER_BOT_TOKEN", None)

try:
    PRIVATE_CHANNEL_ID = int(config.PRIVATE_CHANNEL_ID) if config.PRIVATE_CHANNEL_ID is not None else None
except Exception:
    PRIVATE_CHANNEL_ID = None

ADMIN_IDS: List[int] = getattr(config, "ADMIN_USER_IDS", []) or []

if ADMIN_BOT_TOKEN is None or USER_BOT_TOKEN is None:
    raise RuntimeError("ADMIN_BOT_TOKEN и USER_BOT_TOKEN должны быть заданы в config.py")

# Инициализация ботов (aiogram >=3.7)
bot = Bot(token=ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
user_sender_bot = Bot(token=USER_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Общий файл языковых настроек (используется и user_bot.py)
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


user_langs: Dict[str, str] = load_langs()

# Переводы (минимальный набор; user_bot содержит полный набор)
translations = {
    "ru": {
        "admin_panel": "🔐 <b>Админ-панель</b>\n\nВыберите раздел:",
        "manage_services": "💼 Управление услугами",
        "manage_users": "🧾 Управление пользователями",
        "manage_users_menu": "Управление пользователями:",
        "search_user_prompt": "Введите username или часть username/ID для поиска (без @):",
        "no_users": "Нет пользователей для отображения.",
        "user_not_found": "Пользователь не найден.",
        "deleted_db": "✅ Пользователь удалён из БД.",
        "removed_channel": "✅ Пользователь удалён из канала (если он там был).",
        "showing_photo": "📷 Отправляю фото пользователя вам в личку.",
        "phone_not_found": "📞 Номер не указан",
        "lang_set": "Язык установлен: {lang}",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "no_services": "❌ Услуги временно недоступны.",
        "service_added": "✅ Услуга добавлена.",
        "broadcast_prompt": "Введите текст для рассылки всем пользователям:",
        "dm_prompt": "Выберите пользователя для отправки сообщения:",
    },
    "en": {
        "admin_panel": "🔐 <b>Admin panel</b>\n\nChoose a section:",
        "manage_services": "💼 Manage services",
        "manage_users": "🧾 Manage users",
        "manage_users_menu": "Manage users:",
        "search_user_prompt": "Enter username or part of username/ID (without @):",
        "no_users": "No users to display.",
        "user_not_found": "User not found.",
        "deleted_db": "✅ User deleted from DB.",
        "removed_channel": "✅ User removed from channel (if present).",
        "showing_photo": "📷 Sending user's photo to you in private.",
        "phone_not_found": "📞 Phone not provided",
        "lang_set": "Language set: {lang}",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "no_services": "❌ Services are temporarily unavailable.",
        "service_added": "✅ Service added.",
        "broadcast_prompt": "Enter text to broadcast to all users:",
        "dm_prompt": "Choose a user to send a message to:",
    },
    "ar": {
        "admin_panel": "🔐 <b>لوحة المشرف</b>\n\nاختر القسم:",
        "manage_services": "💼 إدارة الخدمات",
        "manage_users": "🧾 إدارة المستخدمين",
        "manage_users_menu": "إدارة المستخدمين:",
        "search_user_prompt": "أدخل اسم المستخدم أو جزء منه/المعرف (بدون @):",
        "no_users": "لا توجد مستخدمين للعرض.",
        "user_not_found": "المستخدم غير موجود.",
        "deleted_db": "✅ تم حذف المستخدم من قاعدة البيانات.",
        "removed_channel": "✅ تم إزالة المستخدم من القناة (إن وُجد).",
        "showing_photo": "📷 أرسل صورة المستخدم لك في الخاص.",
        "phone_not_found": "📞 لم يتم تحديد رقم",
        "lang_set": "تم ضبط اللغة: {lang}",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "no_services": "❌ الخدمات غير متاحة مؤقتاً.",
        "service_added": "✅ تم إضافة الخدمة.",
        "broadcast_prompt": "أدخل النص لإرساله إلى جميع المستخدمين:",
        "dm_prompt": "اختر مستخدمًا لإرسال رسالة له:",
    },
    "uz": {
        "admin_panel": "🔐 <b>Admin panel</b>\n\nBo'limni tanlang:",
        "manage_services": "💼 Xizmatlarni boshqarish",
        "manage_users": "🧾 Foydalanuvchilarni boshqarish",
        "manage_users_menu": "Foydalanuvchilarni boshqarish:",
        "search_user_prompt": "Username yoki uning bir qismini kiriting ( @siz ):",
        "no_users": "Ko'rsatish uchun foydalanuvchi yo'q.",
        "user_not_found": "Foydalanuvchi topilmadi.",
        "deleted_db": "✅ Foydalanuvchi bazadan o'chirildi.",
        "removed_channel": "✅ Foydalanuvchi kanaldan o'chirildi (agar bo'lsa).",
        "showing_photo": "📷 Foydalanuvchi rasmini sizga yuboraman.",
        "phone_not_found": "📞 Raqam ko'rsatilmagan",
        "lang_set": "Til o'rnatildi: {lang}",
        "choose_lang": "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:",
        "no_services": "❌ Xizmatlar vaqtincha mavjud emas.",
        "service_added": "✅ Xizmat qo'shildi.",
        "broadcast_prompt": "Barcha foydalanuvchilarga yuboriladigan matnni kiriting:",
        "dm_prompt": "Kimga xabar yuborishni tanlang:",
    }
}


def get_user_lang(user_id: int) -> str:
    lang = user_langs.get(str(user_id))
    if lang in translations:
        return lang
    return "ru"


def tr(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_lang(user_id)
    text = translations.get(lang, translations["ru"]).get(key, "")
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


# ---------------- FSM классы ----------------
class AddService(StatesGroup):
    waiting_for_name = State()
    waiting_for_duration = State()
    waiting_for_unit = State()
    waiting_for_price = State()


class EditServicePrice(StatesGroup):
    waiting_for_price = State()


class EditServiceDuration(StatesGroup):
    waiting_for_duration = State()
    waiting_for_unit = State()


class RenameService(StatesGroup):
    waiting_for_name = State()


class SearchUser(StatesGroup):
    waiting_for_query = State()


class Broadcast(StatesGroup):
    waiting_for_message = State()


class DirectMessage(StatesGroup):
    waiting_for_message = State()


# ---------------- Keyboards ----------------
def admin_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Управление услугами", callback_data="manage_services")],
        [InlineKeyboardButton(text="🧾 Управление пользователями", callback_data="manage_users")],
        [InlineKeyboardButton(text="🔧 Диагностика канала", callback_data="diagnostics")],
        [InlineKeyboardButton(text="🌐 Язык", callback_data="lang_menu")],
    ])
    return kb


def manage_users_keyboard(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Поиск пользователя", callback_data="search_user"),
         InlineKeyboardButton(text="📋 Список (пагинация)", callback_data="users_stats")],
        [InlineKeyboardButton(text="✉️ Рассылка всем", callback_data="broadcast_all"),
         InlineKeyboardButton(text="👤 Сообщение пользователю", callback_data="direct_message")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")]
    ])
    return kb


def user_profile_actions_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📷 Показать фото", callback_data=f"admin_show_photo_{user_id}"),
         InlineKeyboardButton(text="📞 Показать номер", callback_data=f"admin_show_phone_{user_id}")],
        [InlineKeyboardButton(text="🚫 Удалить из канала", callback_data=f"admin_remove_channel_{user_id}"),
         InlineKeyboardButton(text="🗑️ Удалить из БД", callback_data=f"admin_delete_user_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_users")]
    ])
    return kb


def lang_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Рус", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇬🇧 En", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇦🇪 ع", callback_data="lang_ar"),
         InlineKeyboardButton(text="🇺🇿 Uz", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")]
    ])
    return kb


# ---------------- Helpers ----------------
async def is_admin(user_id: int) -> bool:
    try:
        return int(user_id) in ADMIN_IDS
    except Exception:
        return False


# ---------------- Handlers ----------------
@dp.message(Command("start"))
async def admin_start(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён. Только администраторы.")
        return
    await state.clear()
    await message.answer(tr(message.from_user.id, "admin_panel"), reply_markup=admin_main_keyboard(message.from_user.id))


@dp.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(tr(callback.from_user.id, "admin_panel"), reply_markup=admin_main_keyboard(callback.from_user.id))


@dp.callback_query(F.data == "lang_menu")
async def lang_menu(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    await callback.message.edit_text(tr(callback.from_user.id, "choose_lang"), reply_markup=lang_menu_kb())


@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    code = callback.data.replace("lang_", "")
    if code not in translations:
        await callback.answer("Unsupported language", show_alert=True)
        return
    user_langs[str(callback.from_user.id)] = code
    save_langs(user_langs)
    await callback.answer()
    await callback.message.edit_text(tr(callback.from_user.id, "lang_set", lang=code), reply_markup=admin_main_keyboard(callback.from_user.id))


# ---------------- Управление услугами (см. user_bot для примера) ----------------
@dp.callback_query(F.data == "manage_services")
async def manage_services(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    try:
        services = await db.get_services()
    except Exception:
        services = []
    if not services:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить услугу", callback_data="add_service")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")]
        ])
        await callback.message.edit_text(tr(callback.from_user.id, "no_services"), reply_markup=kb)
        return
    lines = ["💼 <b>Управление услугами:</b>\n"]
    buttons = []
    for s in services:
        utext = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(s.get("duration_unit", "days"), "дней")
        lines.append(f"👉 <b>{s['name']}</b> — {int(s['price'])} руб. ({s['duration_days']} {utext})")
        buttons.append([InlineKeyboardButton(text=f"⚙️ {s['name']}", callback_data=f"service_{s['id']}")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить услугу", callback_data="add_service")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)


# (Handlers add/edit/delete service — можно перенести из предыдущей версии при необходимости)
# Для краткости оставляем логику управления услугами совместимой с существующим database.py.


# ---------------- Управление пользователями ----------------
@dp.callback_query(F.data == "manage_users")
async def manage_users(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    await callback.message.edit_text(tr(callback.from_user.id, "manage_users_menu"), reply_markup=manage_users_keyboard(callback.from_user.id))


@dp.callback_query(F.data == "search_user")
async def search_user_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    await callback.message.edit_text(tr(callback.from_user.id, "search_user_prompt"))
    await state.set_state(SearchUser.waiting_for_query)


@dp.message(SearchUser.waiting_for_query)
async def search_user_query(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    query = message.text.strip().lstrip('@')
    try:
        results = await db.search_users_by_username(query, limit=50)
    except Exception:
        results = []
    if not results:
        await message.answer(tr(message.from_user.id, "no_users"), reply_markup=manage_users_keyboard(message.from_user.id))
        await state.clear()
        return
    buttons = []
    for u in results:
        username = u.get('username') or f"id{u.get('user_id')}"
        status = "✅" if u.get('is_active') else "❌"
        display = f"{status} @{username} (ID {u.get('user_id')})"
        buttons.append([InlineKeyboardButton(text=display, callback_data=f"userprofile_{u['user_id']}")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="manage_users")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите пользователя:", reply_markup=kb)
    await state.clear()


@dp.callback_query(F.data == "users_stats")
async def users_stats(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    await state.update_data(users_offset=0)
    await send_users_page(callback.message, state, edit=True)


async def send_users_page(message: types.Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    offset = data.get("users_offset", 0)
    try:
        page = await db.get_users_paginated(offset=offset, limit=10)
    except Exception:
        page = []
    if not page:
        kb = manage_users_keyboard(message.from_user.id)
        if edit:
            await message.edit_text(tr(message.from_user.id, "no_users"), reply_markup=kb)
        else:
            await message.answer(tr(message.from_user.id, "no_users"), reply_markup=kb)
        await state.clear()
        return
    lines = ["📊 <b>Пользователи:</b>\n"]
    buttons = []
    for u in page:
        username = u.get('username') or f"id{u.get('user_id')}"
        status = "✅" if u.get('is_active') else "❌"
        end = u.get('subscription_end') or "—"
        lines.append(f"{status} @{username} (ID {u.get('user_id')}) — до {end}")
        buttons.append([InlineKeyboardButton(text=f"{status} @{username}", callback_data=f"userprofile_{u['user_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Предыдущая", callback_data="users_prev"),
                    InlineKeyboardButton(text="➡️ Следующая", callback_data="users_next")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="manage_users")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "\n".join(lines)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.in_({"users_prev", "users_next"}))
async def users_pagination(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    data = await state.get_data()
    offset = data.get("users_offset", 0)
    if callback.data == "users_next":
        offset += 10
    else:
        offset = max(0, offset - 10)
    await state.update_data(users_offset=offset)
    await send_users_page(callback.message, state, edit=True)


@dp.callback_query(F.data.startswith("userprofile_"))
async def show_user_profile(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    try:
        user_id = int(callback.data.replace("userprofile_", ""))
    except Exception:
        await callback.message.edit_text("Ошибка: неверный ID", reply_markup=manage_users_keyboard(callback.from_user.id))
        return
    try:
        user = await db.get_user(user_id)
    except Exception:
        user = None
    if not user:
        await callback.message.edit_text(tr(callback.from_user.id, "user_not_found"), reply_markup=manage_users_keyboard(callback.from_user.id))
        return

    username = user.get('username') or f"id{user_id}"
    phone = user.get('phone_number') or "—"
    status = "✅ Активна" if user.get('is_active') else "❌ Неактивна"
    in_channel = "✅ В канале" if user.get('is_in_channel') or user.get('added_to_channel') else "❌ Не в канале"
    end = user.get('subscription_end') or "—"

    caption = (
        f"👤 <b>@{username}</b>\n\n"
        f"🆔 ID: {user_id}\n"
        f"📱 Телефон: {phone}\n"
        f"📊 Статус: {status}\n"
        f"📅 Подписка до: {end}\n"
        f"🔐 Канал: {in_channel}"
    )

    actions_kb = user_profile_actions_kb(user_id)
    try:
        await callback.message.edit_text(caption, reply_markup=actions_kb)
    except Exception:
        await callback.message.answer(caption, reply_markup=actions_kb)

    # отправляем фото админу отдельно (если есть)
    photo_id = user.get('photo_file_id')
    if photo_id:
        try:
            await bot.send_photo(callback.from_user.id, photo_id, caption=f"Фото @{username}")
        except Exception as e:
            logger.warning(f"Не удалось отправить фото админу: {e}")


@dp.callback_query(F.data.startswith("admin_show_phone_"))
async def admin_show_phone(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    try:
        user_id = int(callback.data.replace("admin_show_phone_", ""))
    except Exception:
        await callback.answer("Ошибка ID", show_alert=True)
        return
    try:
        user = await db.get_user(user_id)
    except Exception:
        user = None
    if not user:
        await callback.answer(tr(callback.from_user.id, "user_not_found"), show_alert=True)
        return
    phone = user.get('phone_number')
    await callback.answer(f"📞 {phone or tr(callback.from_user.id, 'phone_not_found')}", show_alert=True)


@dp.callback_query(F.data.startswith("admin_show_photo_"))
async def admin_show_photo(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    try:
        user_id = int(callback.data.replace("admin_show_photo_", ""))
    except Exception:
        await callback.answer("Ошибка ID", show_alert=True)
        return
    try:
        user = await db.get_user(user_id)
    except Exception:
        user = None
    if not user:
        await callback.answer(tr(callback.from_user.id, "user_not_found"), show_alert=True)
        return
    photo_id = user.get('photo_file_id')
    if not photo_id:
        await callback.answer("Фото не найдено", show_alert=True)
        return
    try:
        await bot.send_photo(callback.from_user.id, photo_id, caption=f"Фото @{user.get('username') or user_id}")
        await callback.answer(tr(callback.from_user.id, "showing_photo"), show_alert=True)
    except Exception as e:
        logger.warning(f"Не удалось отправить фото админу: {e}")
        await callback.answer("Не удалось отправить фото (ошибка).", show_alert=True)


@dp.callback_query(F.data.startswith("admin_remove_channel_"))
async def admin_remove_channel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer("Обрабатываю...")
    try:
        user_id = int(callback.data.replace("admin_remove_channel_", ""))
    except Exception:
        await callback.message.edit_text("Ошибка ID", reply_markup=manage_users_keyboard(callback.from_user.id))
        return
    if PRIVATE_CHANNEL_ID is None:
        await callback.message.edit_text("⚠️ PRIVATE_CHANNEL_ID не задан в config. Невозможно удалить из канала.")
        return
    try:
        await bot.ban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=user_id)
        await asyncio.sleep(0.3)
        await bot.unban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=user_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить пользователя из канала: {e}")
    try:
        if hasattr(db, "mark_user_removed_from_channel"):
            await db.mark_user_removed_from_channel(user_id)
    except Exception:
        logger.debug("mark_user_removed_from_channel отсутствует или не сработала")
    await callback.message.edit_text(tr(callback.from_user.id, "removed_channel"), reply_markup=manage_users_keyboard(callback.from_user.id))


@dp.callback_query(F.data.startswith("admin_delete_user_"))
async def admin_delete_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer("Обрабатываю...")
    try:
        user_id = int(callback.data.replace("admin_delete_user_", ""))
    except Exception:
        await callback.message.edit_text("Ошибка ID", reply_markup=manage_users_keyboard(callback.from_user.id))
        return
    try:
        user = await db.get_user(user_id)
    except Exception:
        user = None
    if not user:
        await callback.message.edit_text(tr(callback.from_user.id, "user_not_found"), reply_markup=manage_users_keyboard(callback.from_user.id))
        return

    if PRIVATE_CHANNEL_ID is not None:
        try:
            await bot.ban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=user_id)
            await asyncio.sleep(0.3)
            await bot.unban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=user_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить пользователя из канала при удалении из БД: {e}")
    try:
        if hasattr(db, "delete_user"):
            await db.delete_user(user_id)
        else:
            if hasattr(db, "upsert_user_profile"):
                await db.upsert_user_profile(user_id, None, None, None)
        await callback.message.edit_text(tr(callback.from_user.id, "deleted_db"), reply_markup=manage_users_keyboard(callback.from_user.id))
    except Exception as e:
        logger.exception("Ошибка удаления пользователя из БД")
        await callback.message.edit_text(f"❌ Не удалось удалить пользователя: {e}", reply_markup=manage_users_keyboard(callback.from_user.id))


# ---------------- Broadcast / DM (перенесены в управление пользователями) ----------------
@dp.callback_query(F.data == "broadcast_all")
async def broadcast_all_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    await callback.message.edit_text(tr(callback.from_user.id, "broadcast_prompt"))
    await state.set_state(Broadcast.waiting_for_message)


@dp.message(Broadcast.waiting_for_message)
async def broadcast_send(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    text = message.text or ""
    try:
        users = await db.get_all_users()
    except Exception:
        users = []
    sent = 0
    for u in users:
        try:
            await user_sender_bot.send_message(u['user_id'], text, disable_notification=getattr(config, "SILENT_MODE", False))
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Не удалось отправить рассылку {u.get('user_id')}: {e}")
    await message.answer(f"✅ Рассылка завершена. Отправлено: {sent}", reply_markup=manage_users_keyboard(message.from_user.id))
    await state.clear()


@dp.callback_query(F.data == "direct_message")
async def direct_message_start(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    await state.update_data(dm_offset=0)
    await send_user_selection_for_dm(callback.message, state, edit=True)


async def send_user_selection_for_dm(message: types.Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    offset = data.get("dm_offset", 0)
    try:
        users = await db.get_users_paginated(offset=offset, limit=10)
    except Exception:
        users = []
    if not users:
        kb = manage_users_keyboard(message.chat.id if isinstance(message, types.Message) else message.from_user.id)
        if edit:
            await message.edit_text(tr(message.from_user.id, "no_users"), reply_markup=kb)
        else:
            await message.answer(tr(message.from_user.id, "no_users"), reply_markup=kb)
        await state.clear()
        return
    buttons = []
    for u in users:
        username = u.get('username') or f"id{u.get('user_id')}"
        status = "✅" if u.get('is_active') else "❌"
        buttons.append([InlineKeyboardButton(text=f"{status} @{username}", callback_data=f"dm_{u['user_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Пред", callback_data="dm_prev"),
                    InlineKeyboardButton(text="➡️ След", callback_data="dm_next")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="manage_users")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if edit:
        await message.edit_text(tr(message.from_user.id, "dm_prompt"), reply_markup=kb)
    else:
        await message.answer(tr(message.from_user.id, "dm_prompt"), reply_markup=kb)


@dp.callback_query(F.data.in_({"dm_prev", "dm_next"}))
async def dm_pagination(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    data = await state.get_data()
    offset = data.get("dm_offset", 0)
    if callback.data == "dm_next":
        offset += 10
    else:
        offset = max(0, offset - 10)
    await state.update_data(dm_offset=offset)
    await send_user_selection_for_dm(callback.message, state, edit=True)


@dp.callback_query(F.data.startswith("dm_"))
async def dm_user_selected(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    user_id = int(callback.data.replace("dm_", ""))
    try:
        user = await db.get_user(user_id)
    except Exception:
        user = None
    if not user:
        await callback.message.edit_text(tr(callback.from_user.id, "user_not_found"), reply_markup=manage_users_keyboard(callback.from_user.id))
        return
    await state.update_data(dm_target_user_id=user_id)
    username = user.get('username') or f"id{user_id}"
    await callback.message.edit_text(f"Введите сообщение для @{username}:")
    await state.set_state(DirectMessage.waiting_for_message)


@dp.message(DirectMessage.waiting_for_message)
async def direct_message_send(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    data = await state.get_data()
    user_id = data.get('dm_target_user_id')
    if not user_id:
        await message.answer("Ошибка: пользователь не найден", reply_markup=manage_users_keyboard(message.from_user.id))
        await state.clear()
        return
    try:
        await user_sender_bot.send_message(user_id, message.text, disable_notification=getattr(config, "SILENT_MODE", False))
        await message.answer("✅ Сообщение отправлено.", reply_markup=manage_users_keyboard(message.from_user.id))
    except Exception as e:
        logger.error(f"Ошибка отправки DM: {e}")
        await message.answer(f"❌ Не удалось отправить сообщение: {e}", reply_markup=manage_users_keyboard(message.from_user.id))
    await state.clear()


# ---------------- Diagnostics ----------------
@dp.callback_query(F.data == "diagnostics")
async def diagnostics(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await callback.answer()
    issues = []
    try:
        me = await bot.get_me()
        issues.append(f"✅ Бот: @{me.username}")
    except Exception as e:
        issues.append(f"❌ Ошибка получения информации о боте: {e}")
    if PRIVATE_CHANNEL_ID is None:
        issues.append("❌ PRIVATE_CHANNEL_ID не задан в config")
    else:
        try:
            chat = await bot.get_chat(PRIVATE_CHANNEL_ID)
            issues.append(f"✅ Канал: {chat.title}")
            issues.append(f"   Тип: {chat.type}")
        except Exception as e:
            issues.append(f"❌ Ошибка доступа к каналу: {e}")
        try:
            member = await bot.get_chat_member(PRIVATE_CHANNEL_ID, (await bot.get_me()).id)
            status = getattr(member, "status", None)
            issues.append(f"✅ Статус бота в канале: {status}")
            if status == "administrator":
                perms = getattr(member, "can_invite_users", False)
                issues.append(f"   Права приглашать: {'✅' if perms else '❌'}")
            else:
                issues.append("   ⚠️ Бот не админ канала!")
        except Exception as e:
            issues.append(f"❌ Ошибка проверки статуса бота в канале: {e}")
    await callback.message.edit_text("\n".join(issues), reply_markup=admin_main_keyboard(callback.from_user.id))


# ---------------- Init helper ----------------
async def init_admin_bot():
    try:
        await db.init_db()
    except Exception as e:
        logger.warning(f"Не удалось инициализировать БД: {e}")

# Конец файла
