import logging
from aiogram import Bot
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from filters import IsAdmin
from keyboards import get_admin_keyboard, get_delete_item_kb, get_order_decision_kb, get_orders_list_kb
from states import AdminAddProduct
from texts import LEXICON

admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

logger = logging.getLogger(__name__)


# --- ХЕЛПЕР ДЛЯ ЛОКАЛІЗАЦІЇ АДМІНКИ ---
def get_admin_loc_data(lang='ua'):
    loc_data = {
        'ua': {
            'header': "📦 <b>Список замовлень:</b>\nОберіть замовлення для перегляду:",
            'empty': "Список замовлень порожній.",
            'order': "Замовлення",
            'status': "Статус",
            'user': "Клієнт",
            'phone': "Телефон",
            'addr': "Адреса",
            'deliv': "Доставка",
            'items': "Товари",
            'total': "Всього",
            'actions': "Дії:",
            'approved_admin': "✅ Замовлення #{id} ПРИЙНЯТО.",
            'rejected_admin': "❌ Замовлення #{id} ВІДХИЛЕНО.",
        },
        'en': {
            'header': "📦 <b>Orders List:</b>\nSelect an order to view details:",
            'empty': "Orders list is empty.",
            'order': "Order",
            'status': "Status",
            'user': "Client",
            'phone': "Phone",
            'addr': "Address",
            'deliv': "Delivery",
            'items': "Items",
            'total': "Total",
            'actions': "Actions:",
            'approved_admin': "✅ Order #{id} APPROVED.",
            'rejected_admin': "❌ Order #{id} REJECTED.",
        }
    }
    return loc_data.get(lang, loc_data['ua'])


# ОБРОБНИК КНОПКИ АДМІН-ПАНЕЛІ
@admin_router.message(F.text.in_([LEXICON['ua']['admin_btn'], LEXICON['en']['admin_btn']]))
@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    await message.answer("Панель адміністратора v2.0", reply_markup=get_admin_keyboard())


# --- Додавання товару ---
@admin_router.message(Command("add_item"))
async def start_add_item(message: types.Message, state: FSMContext):
    await message.answer("Введіть назву товару:")
    await state.set_state(AdminAddProduct.waiting_for_name)


@admin_router.message(AdminAddProduct.waiting_for_name)
async def add_item_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть категорію (наприклад: Ноутбуки, Смартфони):")
    await state.set_state(AdminAddProduct.waiting_for_category)


@admin_router.message(AdminAddProduct.waiting_for_category)
async def add_item_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Введіть опис товару:")
    await state.set_state(AdminAddProduct.waiting_for_desc)


@admin_router.message(AdminAddProduct.waiting_for_desc)
async def add_item_desc(message: types.Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Введіть ціну (числом):")
    await state.set_state(AdminAddProduct.waiting_for_price)


@admin_router.message(AdminAddProduct.waiting_for_price)
async def add_item_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        data = await state.get_data()
        await db.add_product(data['name'], data['desc'], price, data['category'])

        # ЛОГ: Адмін додав товар
        logger.info(f"ADMIN_ACTION: Admin {message.from_user.id} ADDED product '{data['name']}' ({price} UAH).")

        await message.answer(f"✅ Товар '{data['name']}' у категорії '{data['category']}' додано!",
                             reply_markup=get_admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("Ціна має бути числом.")


# --- Видалення ---
@admin_router.message(Command("remove_item"))
async def cmd_remove_item(message: types.Message):
    products = await db.get_all_products()
    if not products:
        await message.answer("Каталог порожній.")
        return
    await message.answer("Натисніть на товар, щоб видалити його:", reply_markup=get_delete_item_kb(products))


@admin_router.callback_query(F.data.startswith("admin_del_"))
async def process_delete(callback: types.CallbackQuery):
    p_id = int(callback.data.split("_")[-1])
    await db.delete_product(p_id)

    # ЛОГ: Адмін видалив товар
    logger.info(f"ADMIN_ACTION: Admin {callback.from_user.id} DELETED product ID {p_id}.")

    await callback.answer("Товар видалено!")
    products = await db.get_all_products()
    await callback.message.edit_reply_markup(reply_markup=get_delete_item_kb(products))

@admin_router.message(Command("orders"))
async def cmd_view_orders_list(message: types.Message):
    lang, _ = await db.get_user_settings(message.from_user.id)
    loc = get_admin_loc_data(lang)

    # Беремо останні 20 замовлень
    orders_list = await db.get_orders(limit=20)

    if not orders_list:
        await message.answer(loc['empty'])
        return

    kb = get_orders_list_kb(orders_list, loc)
    await message.answer(loc['header'], reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_refresh_orders")
@admin_router.callback_query(F.data == "admin_back_orders")
async def refresh_orders_list(callback: types.CallbackQuery):
    lang, _ = await db.get_user_settings(callback.from_user.id)
    loc = get_admin_loc_data(lang)

    orders_list = await db.get_orders(limit=20)

    if not orders_list:
        await callback.message.edit_text(loc['empty'])
        return

    kb = get_orders_list_kb(orders_list, loc)
    # Перевіряємо, чи змінився текст/клавіатура, щоб не ловити помилку "message not modified"
    try:
        await callback.message.edit_text(loc['header'], reply_markup=kb, parse_mode="HTML")
    except:
        await callback.answer("Список оновлено")


@admin_router.callback_query(F.data.startswith("view_order_"))
async def view_single_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])

    # Отримуємо дані для відображення
    lang, _ = await db.get_user_settings(callback.from_user.id)
    loc = get_admin_loc_data(lang)
    order = await db.get_order(order_id)

    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    # Формування тексту
    currency = order['currency_code'] if order['currency_code'] else "UAH"

    # Мапінг статусів
    status_map = {
        'pending': loc['pending'] if 'pending' in loc else '⏳ Pending',
        'paid': loc['paid'] if 'paid' in loc else '✅ Paid',
        'approved': loc['approved'] if 'approved' in loc else '✅ Approved',
        'rejected': loc['rejected'] if 'rejected' in loc else '❌ Rejected'
    }
    status_txt = status_map.get(order['status'], order['status'])

    text = (
        f"🆔 <b>{loc['order']} #{order['id']}</b>\n"
        f"📊 {loc['status']}: {status_txt}\n\n"
        f"👤 {loc['user']}: {order['user_name']} (ID: {order['user_id']})\n"
        f"📞 {loc['phone']}: {order['user_phone']}\n"
        f"📍 {loc['addr']}: {order['user_address']}\n"
        f"🚚 {loc['deliv']}: {order['delivery_method']}\n\n"
        f"📜 {loc['items']}:\n{order['items_text']}\n\n"
        f"💰 <b>{loc['total']}: {order['total_price']} {currency}</b>"
    )

    # Показуємо кнопки дій тільки якщо статус 'paid' або 'pending'
    show_actions = order['status'] in ['paid', 'pending']
    kb = get_order_decision_kb(order_id, show_actions=show_actions)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("approve_"))
async def approve_order(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])

    # Оновлюємо статус
    await db.update_order_status(order_id, "approved")

    # ЛОГ: Адмін схвалив замовлення
    logger.info(f"ADMIN_ORDER: Admin {callback.from_user.id} APPROVED Order #{order_id}.")

    # Локалізація відповіді адміну
    lang, _ = await db.get_user_settings(callback.from_user.id)
    loc = get_admin_loc_data(lang)

    admin_msg = loc['approved_admin'].replace("{id}", str(order_id))

    # Редагуємо повідомлення: прибираємо кнопки дій, залишаємо кнопку "Назад"
    kb = get_order_decision_kb(order_id, show_actions=False)
    await callback.message.edit_text(admin_msg, reply_markup=kb)

    # Сповіщення користувача
    order = await db.get_order(order_id)
    if order:
        try:
            user_lang, _ = await db.get_user_settings(order['user_id'])
            msg_text = LEXICON[user_lang]['order_approved'].replace("{id}", str(order_id))
            await bot.send_message(order['user_id'], msg_text)
        except Exception as e:
            logger.error(f"Error sending msg to user {order['user_id']}: {e}")


@admin_router.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])

    await db.update_order_status(order_id, "rejected")

    # ЛОГ: Адмін відхилив замовлення
    logger.info(f"ADMIN_ORDER: Admin {callback.from_user.id} REJECTED Order #{order_id}.")

    lang, _ = await db.get_user_settings(callback.from_user.id)
    loc = get_admin_loc_data(lang)

    admin_msg = loc['rejected_admin'].replace("{id}", str(order_id))

    kb = get_order_decision_kb(order_id, show_actions=False)
    await callback.message.edit_text(admin_msg, reply_markup=kb)

    order = await db.get_order(order_id)
    if order:
        try:
            user_lang, _ = await db.get_user_settings(order['user_id'])
            msg_text = LEXICON[user_lang]['order_rejected'].replace("{id}", str(order_id))
            await bot.send_message(order['user_id'], msg_text)
        except Exception as e:
            logger.error(f"Error sending msg to user {order['user_id']}: {e}")