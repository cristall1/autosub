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

ADMIN_BOT_TOKEN = config.ADMIN_BOT_TOKEN
PRIVATE_CHANNEL_ID = config.PRIVATE_CHANNEL_ID
ADMIN_IDS = config.ADMIN_USER_IDS

bot = Bot(token=ADMIN_BOT_TOKEN)
user_sender_bot = Bot(token=config.USER_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)


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


def get_admin_keyboard():
    """Main admin inline keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Управление услугами", callback_data="manage_services")],
        [InlineKeyboardButton(text="🔎 Поиск пользователя", callback_data="search_user"),
         InlineKeyboardButton(text="📊 Статистика пользователей", callback_data="stats")],
        [InlineKeyboardButton(text="✉️ Рассылка всем", callback_data="broadcast_all"),
         InlineKeyboardButton(text="👤 Сообщение пользователю", callback_data="direct_message")],
        [InlineKeyboardButton(text="🔧 Диагностика канала", callback_data="diagnostics"),
         InlineKeyboardButton(text="🔔 Режим тишины", callback_data="silent_mode")],
    ])
    return keyboard


@dp.message(Command("start"))
async def admin_start(message: types.Message, state: FSMContext):
    """Admin bot start command"""
    await state.clear()
    await message.answer(
        "🔐 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: types.CallbackQuery, state: FSMContext):
    """Back to admin menu"""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "manage_services")
async def manage_services(callback: types.CallbackQuery, state: FSMContext):
    """Service management menu"""
    await callback.answer()
    
    services = await db.get_services()
    if services:
        header = "💼 <b>Управление услугами:</b>\n\n"
        for s in services:
            unit = s.get('duration_unit', 'days')
            unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
            header += f"👉 <b>{s['name']}</b> - {int(s['price'])} руб. ({s['duration_days']} {unit_text})\n"
    else:
        header = "💼 <b>Управление услугами:</b>\n\nНет услуг"
    
    buttons = [[InlineKeyboardButton(text=f"👉 {s['name']}", callback_data=f"service_{s['id']}")] for s in services]
    buttons.append([InlineKeyboardButton(text="➕ Добавить услугу", callback_data="add_service")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(header, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("service_"))
async def service_actions(callback: types.CallbackQuery, state: FSMContext):
    """Service edit menu"""
    await callback.answer()
    
    service_id = int(callback.data.replace("service_", ""))
    service = await db.get_service_by_id(service_id)
    
    if not service:
        await callback.message.edit_text("Услуга не найдена", reply_markup=get_admin_keyboard())
        return
    
    await state.update_data(edit_service_id=service['id'])
    
    unit = service.get('duration_unit', 'days')
    unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
    
    actions_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data="rename_service"),
         InlineKeyboardButton(text="💰 Изменить цену", callback_data="edit_price")],
        [InlineKeyboardButton(text="⏱ Изменить срок", callback_data="edit_duration"),
         InlineKeyboardButton(text="🗑 Удалить услугу", callback_data="delete_service")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="manage_services")]
    ])
    
    service_info = f"<b>{service['name']}</b>\n\nЦена: {service['price']} руб.\nДлительность: {service['duration_days']} {unit_text}"
    await callback.message.edit_text(service_info, reply_markup=actions_kb, parse_mode="HTML")


@dp.callback_query(F.data == "add_service")
async def add_service_start(callback: types.CallbackQuery, state: FSMContext):
    """Start adding new service"""
    await callback.answer()
    await callback.message.edit_text("Введите название услуги:")
    await state.set_state(AddService.waiting_for_name)


@dp.message(AddService.waiting_for_name)
async def add_service_name(message: types.Message, state: FSMContext):
    await state.update_data(service_name=message.text.strip())
    await message.answer("Введите продолжительность (число от 1 до 525600):")
    await state.set_state(AddService.waiting_for_duration)


@dp.message(AddService.waiting_for_duration)
async def add_service_duration(message: types.Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0 or duration > 525600:
            raise ValueError("Некорректное значение")
        await state.update_data(service_duration=duration)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Минуты", callback_data="unit_minutes"),
             InlineKeyboardButton(text="Дни", callback_data="unit_days")],
            [InlineKeyboardButton(text="Месяцы", callback_data="unit_months")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="manage_services")]
        ])
        await message.answer("Выберите единицу измерения:", reply_markup=kb)
        await state.set_state(AddService.waiting_for_unit)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")


@dp.callback_query(F.data.startswith("unit_"), AddService.waiting_for_unit)
async def add_service_unit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    unit_map = {"unit_minutes": "minutes", "unit_days": "days", "unit_months": "months"}
    unit = unit_map.get(callback.data)
    
    if not unit:
        return
    
    await state.update_data(service_unit=unit)
    await callback.message.edit_text("Введите стоимость (в рублях):")
    await state.set_state(AddService.waiting_for_price)


@dp.message(AddService.waiting_for_price)
async def add_service_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(',', '.'))
        if price <= 0:
            raise ValueError("Цена должна быть положительным числом")
        
        data = await state.get_data()
        name = data.get("service_name")
        duration = data.get("service_duration")
        unit = data.get("service_unit", "days")
        
        await db.add_service(name, duration, price, unit)
        
        unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
        
        await message.answer(
            f"✅ Услуга добавлена:\n\n"
            f"<b>{name}</b>\n"
            f"Продолжительность: {duration} {unit_text}\n"
            f"Стоимость: {price} руб.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену.")


@dp.callback_query(F.data == "rename_service")
async def rename_service_start(callback: types.CallbackQuery, state: FSMContext):
    """Start renaming service"""
    await callback.answer()
    await callback.message.edit_text("Введите новое название:")
    await state.set_state(RenameService.waiting_for_name)


@dp.message(RenameService.waiting_for_name)
async def rename_service_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    service_id = data.get('edit_service_id')
    if not service_id:
        await message.answer("Ошибка: услуга не найдена", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    await db.update_service_name(service_id, message.text.strip())
    await message.answer("✅ Название обновлено.", reply_markup=get_admin_keyboard())
    await state.clear()


@dp.callback_query(F.data == "edit_price")
async def edit_price_start(callback: types.CallbackQuery, state: FSMContext):
    """Start editing service price"""
    await callback.answer()
    await callback.message.edit_text("Введите новую цену (в рублях):")
    await state.set_state(EditServicePrice.waiting_for_price)


@dp.message(EditServicePrice.waiting_for_price)
async def edit_price_finish(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(',', '.'))
        if price <= 0:
            raise ValueError("Цена должна быть положительным числом")
        
        data = await state.get_data()
        service_id = data.get('edit_service_id')
        if not service_id:
            await message.answer("Ошибка: услуга не найдена", reply_markup=get_admin_keyboard())
            await state.clear()
            return
        
        await db.update_service_price(service_id, price)
        await message.answer(f"✅ Цена обновлена: {price} руб.", reply_markup=get_admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену.")


@dp.callback_query(F.data == "edit_duration")
async def edit_duration_start(callback: types.CallbackQuery, state: FSMContext):
    """Start editing service duration"""
    await callback.answer()
    await callback.message.edit_text("Введите новую длительность (число):")
    await state.set_state(EditServiceDuration.waiting_for_duration)


@dp.message(EditServiceDuration.waiting_for_duration)
async def edit_duration_value(message: types.Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError("Продолжительность должна быть положительным числом")
        await state.update_data(new_duration=duration)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Минуты", callback_data="unit_minutes"),
             InlineKeyboardButton(text="Дни", callback_data="unit_days")],
            [InlineKeyboardButton(text="Месяцы", callback_data="unit_months")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")]
        ])
        await message.answer("Выберите единицу измерения:", reply_markup=kb)
        await state.set_state(EditServiceDuration.waiting_for_unit)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")


@dp.callback_query(F.data.startswith("unit_"), EditServiceDuration.waiting_for_unit)
async def edit_duration_unit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    unit_map = {"unit_minutes": "minutes", "unit_days": "days", "unit_months": "months"}
    unit = unit_map.get(callback.data)
    
    if not unit:
        return
    
    data = await state.get_data()
    service_id = data.get('edit_service_id')
    duration = data.get('new_duration')
    
    if not service_id:
        await callback.message.edit_text("Ошибка: не найден ID услуги", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    await db.update_service_duration(service_id, duration, unit)
    
    unit_text_display = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
    await callback.message.edit_text(
        f"✅ Длительность обновлена: {duration} {unit_text_display}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@dp.callback_query(F.data == "delete_service")
async def delete_service_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Confirm service deletion"""
    await callback.answer()
    
    data = await state.get_data()
    service_id = data.get('edit_service_id')
    if not service_id:
        await callback.message.edit_text("Ошибка: услуга не найдена", reply_markup=get_admin_keyboard())
        return
    
    await db.delete_service(service_id)
    await callback.message.edit_text("✅ Услуга удалена.", reply_markup=get_admin_keyboard())
    await state.clear()


@dp.callback_query(F.data == "search_user")
async def search_user_start(callback: types.CallbackQuery, state: FSMContext):
    """Start user search"""
    await callback.answer()
    await callback.message.edit_text("Введите username для поиска (без @):")
    await state.set_state(SearchUser.waiting_for_query)


@dp.message(SearchUser.waiting_for_query)
async def search_user_query(message: types.Message, state: FSMContext):
    """Handle search query"""
    query = message.text.strip().lstrip('@')
    results = await db.search_users_by_username(query, limit=20)
    
    if not results:
        await message.answer("Ничего не найдено. Попробуйте другой запрос.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    buttons = []
    for u in results:
        username = u['username'] or f"id{u['user_id']}"
        status = "✅" if u['is_active'] else "❌"
        buttons.append([InlineKeyboardButton(text=f"{status} @{username}", callback_data=f"userprofile_{u['user_id']}")])
    
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("Выберите пользователя:", reply_markup=kb)
    await state.clear()


@dp.callback_query(F.data.startswith("userprofile_"))
async def show_user_profile(callback: types.CallbackQuery, state: FSMContext):
    """Show user profile with photo"""
    await callback.answer()
    
    user_id = int(callback.data.replace("userprofile_", ""))
    user = await db.get_user(user_id)
    
    if not user:
        await callback.message.edit_text("Пользователь не найден.", reply_markup=get_admin_keyboard())
        return
    
    username = user['username'] or f"id{user_id}"
    phone = user['phone_number'] or "—"
    status = "✅ Активна" if user['is_active'] else "❌ Неактивна"
    
    if user['subscription_end']:
        end_date = datetime.fromisoformat(user['subscription_end'])
        end_str = end_date.strftime("%d.%m.%Y %H:%M")
    else:
        end_str = "—"
    
    caption = (
        f"👤 <b>@{username}</b>\n\n"
        f"🆔 ID: {user_id}\n"
        f"📱 Телефон: {phone}\n"
        f"📊 Статус: {status}\n"
        f"📅 Подписка до: {end_str}"
    )
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")]])
    
    if user.get('photo_file_id'):
        await callback.message.delete()
        await bot.send_photo(
            callback.message.chat.id,
            user['photo_file_id'],
            caption=caption,
            parse_mode="HTML",
            reply_markup=back_kb
        )
    else:
        await callback.message.edit_text(caption + "\n\n📷 Нет фото", parse_mode="HTML", reply_markup=back_kb)


@dp.callback_query(F.data == "stats")
async def users_stats(callback: types.CallbackQuery, state: FSMContext):
    """Show paginated users list"""
    await callback.answer()
    await state.update_data(stats_offset=0)
    await send_users_page(callback.message, state, edit=True)


async def send_users_page(message: types.Message, state: FSMContext, edit: bool = False):
    """Send paginated users list"""
    data = await state.get_data()
    offset = data.get("stats_offset", 0)
    page = await db.get_users_paginated(offset=offset, limit=10)
    
    if not page:
        text = "Нет пользователей для отображения."
        kb = get_admin_keyboard()
        if edit:
            await message.edit_text(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        await state.clear()
        return
    
    lines = ["📊 <b>Пользователи:</b>\n"]
    for u in page:
        username = u['username'] or f"id{u['user_id']}"
        status = '✅' if u['is_active'] else '❌'
        end_str = datetime.fromisoformat(u['subscription_end']).strftime('%d.%m') if u['subscription_end'] else '—'
        lines.append(f"{status} @{username} до {end_str}")
    
    controls = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Предыдущая", callback_data="stats_prev"),
         InlineKeyboardButton(text="➡️ Следующая", callback_data="stats_next")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")]
    ])
    
    text = "\n".join(lines)
    if edit:
        await message.edit_text(text, reply_markup=controls, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=controls, parse_mode="HTML")


@dp.callback_query(F.data.in_({"stats_prev", "stats_next"}))
async def stats_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Handle stats pagination"""
    await callback.answer()
    
    data = await state.get_data()
    offset = data.get("stats_offset", 0)
    
    if callback.data == "stats_next":
        offset += 10
    else:
        offset = max(0, offset - 10)
    
    await state.update_data(stats_offset=offset)
    await send_users_page(callback.message, state, edit=True)


@dp.callback_query(F.data == "broadcast_all")
async def broadcast_all_start(callback: types.CallbackQuery, state: FSMContext):
    """Start broadcast to all users"""
    await callback.answer()
    await callback.message.edit_text("Введите текст для рассылки всем пользователям:")
    await state.update_data(broadcast_all=True)
    await state.set_state(Broadcast.waiting_for_message)


@dp.message(Broadcast.waiting_for_message)
async def broadcast_send_all(message: types.Message, state: FSMContext):
    """Send broadcast to all users"""
    text = message.text
    users = await db.get_all_users()
    sent = 0
    
    for u in users:
        try:
            await user_sender_bot.send_message(
                u['user_id'],
                text,
                disable_notification=getattr(config, "SILENT_MODE", False)
            )
            sent += 1
            await asyncio.sleep(0.05)  # Anti-flood
        except Exception as e:
            logging.error(f"Broadcast failed to {u['user_id']}: {e}")
    
    await message.answer(f"✅ Рассылка завершена. Отправлено: {sent}", reply_markup=get_admin_keyboard())
    await state.clear()


@dp.callback_query(F.data == "direct_message")
async def direct_message_start(callback: types.CallbackQuery, state: FSMContext):
    """Start direct message to user"""
    await callback.answer()
    
    users = await db.get_all_users()
    if not users:
        await callback.message.edit_text("Нет пользователей для отправки сообщений.", reply_markup=get_admin_keyboard())
        return
    
    await state.update_data(dm_offset=0)
    await send_user_selection_page(callback.message, state, edit=True)


async def send_user_selection_page(message: types.Message, state: FSMContext, edit: bool = False):
    """Send user selection page for DM"""
    data = await state.get_data()
    offset = data.get("dm_offset", 0)
    users = await db.get_users_paginated(offset=offset, limit=10)
    
    if not users:
        kb = get_admin_keyboard()
        text = "Нет пользователей."
        if edit:
            await message.edit_text(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        await state.clear()
        return
    
    buttons = []
    for u in users:
        username = u['username'] or f"id{u['user_id']}"
        status = "✅" if u['is_active'] else "❌"
        buttons.append([InlineKeyboardButton(text=f"{status} @{username}", callback_data=f"dm_{u['user_id']}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Пред", callback_data="dm_prev"),
                    InlineKeyboardButton(text="➡️ След", callback_data="dm_next")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="admin_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "Выберите пользователя:"
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.in_({"dm_prev", "dm_next"}))
async def dm_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Handle DM user selection pagination"""
    await callback.answer()
    
    data = await state.get_data()
    offset = data.get("dm_offset", 0)
    
    if callback.data == "dm_next":
        offset += 10
    else:
        offset = max(0, offset - 10)
    
    await state.update_data(dm_offset=offset)
    await send_user_selection_page(callback.message, state, edit=True)


@dp.callback_query(F.data.startswith("dm_"))
async def direct_message_user_selected(callback: types.CallbackQuery, state: FSMContext):
    """Handle user selection for DM"""
    await callback.answer()
    
    if callback.data in {"dm_prev", "dm_next"}:
        return
    
    user_id = int(callback.data.replace("dm_", ""))
    user = await db.get_user(user_id)
    
    if not user:
        await callback.message.edit_text("Пользователь не найден.", reply_markup=get_admin_keyboard())
        return
    
    username = user['username'] or f"id{user_id}"
    await state.update_data(dm_target_user_id=user_id)
    await callback.message.edit_text(f"Введите сообщение для @{username}:")
    await state.set_state(DirectMessage.waiting_for_message)


@dp.message(DirectMessage.waiting_for_message)
async def direct_message_send(message: types.Message, state: FSMContext):
    """Send direct message to user"""
    data = await state.get_data()
    user_id = data.get('dm_target_user_id')
    
    if not user_id:
        await message.answer("Ошибка: пользователь не найден", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    try:
        await user_sender_bot.send_message(
            user_id,
            message.text,
            disable_notification=getattr(config, "SILENT_MODE", False)
        )
        await message.answer("✅ Сообщение отправлено.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}", reply_markup=get_admin_keyboard())
    
    await state.clear()


@dp.callback_query(F.data == "diagnostics")
async def channel_diagnostics(callback: types.CallbackQuery):
    """Perform channel diagnostics"""
    await callback.answer()
    
    issues = []
    
    try:
        me = await bot.get_me()
        issues.append(f"✅ Бот: @{me.username}")
    except Exception as e:
        issues.append(f"❌ Ошибка проверки прав бота: {e}")
    
    await callback.message.edit_text("\n".join(issues), reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "silent_mode")
async def silent_mode_status(callback: types.CallbackQuery):
    """Show silent mode status"""
    await callback.answer()
    status = "✅ Включен" if getattr(config, 'SILENT_MODE', False) else "❌ Выключен"
    await callback.message.edit_text(f"Режим тишины: {status}", reply_markup=get_admin_keyboard())


@dp.callback_query(F.data.startswith("approve_"))
async def approve_purchase(callback: types.CallbackQuery):
    """Approve purchase request - УЛУЧШЕННАЯ ВЕРСИЯ"""
    await callback.answer("⏳ Обрабатываю...")
    
    purchase_id = int(callback.data.replace("approve_", ""))
    purchase = await db.get_pending_purchase(purchase_id)
    
    if not purchase:
        await callback.message.edit_text("❌ Заявка не найдена")
        return
    
    service = await db.get_service_by_id(purchase['service_id'])
    if not service:
        await callback.message.edit_text("❌ Услуга не найдена")
        return
    
    # 1. АКТИВИРУЕМ ПОДПИСКУ В БД
    try:
        end_date = await db.activate_user_subscription(
            purchase['user_id'],
            purchase['username'],
            purchase['phone_number'],
            service['duration_days'],
            service.get('duration_unit', 'days')
        )
        logging.info(f"✅ Subscription activated for user {purchase['user_id']} until {end_date}")
    except Exception as e:
        logging.error(f"❌ Failed to activate subscription: {e}")
        await callback.message.edit_text(f"❌ Ошибка активации подписки: {e}")
        return
    
    # 2. СОЗДАЕМ ПЕРСОНАЛЬНУЮ ССЫЛКУ НА КАНАЛ
    invite_link = None
    try:
        # Проверяем права бота
        me = await bot.get_me()
        member = await bot.get_chat_member(PRIVATE_CHANNEL_ID, me.id)
        
        if member.status != "administrator" or not member.can_invite_users:
            raise Exception("⚠️ Бот не имеет прав администратора или прав на приглашение пользователей!")
        
        # Создаем персональную одноразовую ссылку
        invite = await bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID,
            member_limit=1,  # Одноразовая ссылка
            name=f"Подписка {purchase['username']}"
        )
        invite_link = invite.invite_link
        
        await db.mark_user_added_to_channel(purchase['user_id'])
        logging.info(f"✅ Invite link created for user {purchase['user_id']}")
        
    except Exception as e:
        logging.error(f"❌ Failed to create invite link: {e}")
        await callback.message.edit_text(
            f"⚠️ Подписка активирована, но ошибка создания ссылки:\n{e}\n\n"
            f"Проверьте права бота в канале через /start → Диагностика"
        )
        return
    
    # 3. МГНОВЕННО ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ
    try:
        unit = service.get('duration_unit', 'days')
        unit_text = {"minutes": "минут", "days": "дней", "months": "месяцев"}.get(unit, "дней")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Присоединиться к каналу", url=invite_link)]
        ])
        
        await user_sender_bot.send_message(
            purchase['user_id'],
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"📦 Услуга: <b>{service['name']}</b>\n"
            f"⏱ Срок: {service['duration_days']} {unit_text}\n"
            f"📅 Действует до: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👇 Нажмите кнопку ниже, чтобы присоединиться к приватному каналу:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logging.info(f"✅ Notification sent to user {purchase['user_id']}")
        
    except Exception as e:
        logging.error(f"❌ Failed to send notification to user: {e}")
        await callback.message.edit_text(
            f"⚠️ Подписка активирована и ссылка создана, но не удалось отправить уведомление юзеру:\n{e}"
        )
        return
    
    # 4. УДАЛЯЕМ ЗАЯВКУ ИЗ БД
    await db.delete_pending_purchase(purchase_id)
    
    # 5. УВЕДОМЛЯЕМ АДМИНА ОБ УСПЕХЕ
    await callback.message.edit_text(
        f"✅ <b>Подписка успешно активирована!</b>\n\n"
        f"👤 Пользователь: @{purchase['username']}\n"
        f"📦 Услуга: {service['name']}\n"
        f"📅 До: {end_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔗 Персональная ссылка отправлена пользователю",
        parse_mode="HTML"
    )
    
    logging.info(f"✅ Purchase {purchase_id} approved successfully!")


@dp.callback_query(F.data.startswith("reject_"))
async def reject_purchase(callback: types.CallbackQuery):
    """Reject purchase request"""
    await callback.answer()
    
    purchase_id = int(callback.data.replace("reject_", ""))
    purchase = await db.get_pending_purchase(purchase_id)
    
    if not purchase:
        await callback.message.edit_text("❌ Заявка не найдена")
        return
    
    await db.delete_pending_purchase(purchase_id)
    
    try:
        await user_sender_bot.send_message(
            purchase['user_id'],
            "❌ <b>Ваша заявка на подписку отклонена администратором.</b>\n\n"
            "Если у вас есть вопросы, свяжитесь с поддержкой через /start → Связаться с админом",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Failed to send rejection notice: {e}")
    
    await callback.message.edit_text(f"❌ Заявка отклонена для @{purchase['username']}")


async def main():
    """Main function to run admin bot"""
    await db.init_db()
    logging.info("Admin bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())append(f"❌ Ошибка получения info бота: {e}")
    
    try:
        chat = await bot.get_chat(PRIVATE_CHANNEL_ID)
        issues.append(f"✅ Канал найден: {chat.title}")
        issues.append(f"   Тип: {chat.type}")
    except Exception as e:
        issues.append(f"❌ Ошибка доступа к каналу: {e}")
    
    try:
        member = await bot.get_chat_member(PRIVATE_CHANNEL_ID, (await bot.get_me()).id)
        issues.append(f"✅ Статус бота в канале: {member.status}")
        
        if member.status == "administrator":
            perms = member.can_invite_users
            issues.append(f"   Права на приглашение: {'✅' if perms else '❌'}")
        else:
            issues.append(f"   ⚠️ Бот не админ канала!")
    except Exception as e:
        issues.
