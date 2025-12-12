import re
import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, PreCheckoutQuery, ContentType

from database import db
from texts import LEXICON
from keyboards import (
    get_main_keyboard, get_categories_kb, get_products_kb,
    get_product_detail_kb, get_cart_kb, get_delivery_kb, get_confirm_order_kb,
    get_order_decision_kb, get_lang_keyboard, get_settings_choice_kb, get_currency_keyboard,
    get_checkout_step_kb
)
from states import OrderState
from config import ADMIN_IDS, PAYMENT_TOKEN, EXCHANGE_RATES, CURRENCY_SIGNS

user_router = Router()
logger = logging.getLogger(__name__)


# --- ХЕЛПЕРИ ---
async def get_user_config(user_id: int):
    """Отримує мову, код валюти, знак валюти та курс"""
    lang, curr_code = await db.get_user_settings(user_id)
    rate = EXCHANGE_RATES.get(curr_code, 1)
    sign = CURRENCY_SIGNS.get(curr_code, 'грн')
    return lang, curr_code, sign, rate


def convert_price(price_uah, rate):
    return round(price_uah / rate, 2)


# --- Старт ---
@user_router.message(CommandStart())
async def cmd_start(message: types.Message):
    await db.add_user(message.from_user.id)

    # ЛОГ: Старт бота користувачем
    logger.info(f"USER_ACTION: User {message.from_user.id} (@{message.from_user.username}) started the bot.")

    await message.answer(LEXICON['ua']['select_lang'], reply_markup=get_lang_keyboard())


# --- НАЛАШТУВАННЯ ---
@user_router.message(F.text.in_([LEXICON['ua']['settings_btn'], LEXICON['en']['settings_btn']]))
async def settings_menu(message: types.Message):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    await message.answer(LEXICON[lang]['settings_menu'], reply_markup=get_settings_choice_kb(lang))


@user_router.callback_query(F.data == "settings_lang")
async def show_lang_selection(callback: types.CallbackQuery):
    await callback.message.edit_text("🇺🇦 Оберіть мову / 🇺🇸 Select language:", reply_markup=get_lang_keyboard())


@user_router.callback_query(F.data == "settings_curr")
async def show_curr_selection(callback: types.CallbackQuery):
    await callback.message.edit_text("💱 Оберіть валюту / Select currency:", reply_markup=get_currency_keyboard())


# --- Зміна Мови ---
@user_router.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    await db.set_user_language(callback.from_user.id, lang_code)

    logger.info(f"USER_ACTION: User {callback.from_user.id} changed language to {lang_code}.")

    await callback.message.delete()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        LEXICON[lang_code]['lang_set'],
        reply_markup=get_main_keyboard(lang_code, is_admin)
    )


# --- Зміна Валюти ---
@user_router.callback_query(F.data.startswith("setcurr_"))
async def set_currency(callback: types.CallbackQuery):
    curr_code = callback.data.split("_")[1]
    await db.set_user_currency(callback.from_user.id, curr_code)
    lang, _, _, _ = await get_user_config(callback.from_user.id)
    is_admin = callback.from_user.id in ADMIN_IDS

    logger.info(f"USER_ACTION: User {callback.from_user.id} changed currency to {curr_code}.")

    await callback.message.delete()
    await callback.message.answer(
        LEXICON[lang]['currency_set'] + curr_code,
        reply_markup=get_main_keyboard(lang, is_admin)
    )


# --- Інфо та Мої Замовлення ---
@user_router.message(Command("info"))
@user_router.message(F.text.in_([LEXICON['ua']['info_btn'], LEXICON['en']['info_btn']]))
async def cmd_info(message: types.Message):
    lang, curr, sign, _ = await get_user_config(message.from_user.id)
    await message.answer(f"{LEXICON[lang]['info_msg']}\nYour Currency: {curr} ({sign})")


@user_router.message(F.text.in_([LEXICON['ua']['orders_btn'], LEXICON['en']['orders_btn']]))
async def cmd_my_orders(message: types.Message):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    orders = await db.get_user_orders(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS

    if not orders:
        await message.answer(LEXICON[lang]['no_orders'], reply_markup=get_main_keyboard(lang, is_admin))
        return

    loc = {
        'ua': {
            'status_lbl': "Статус", 'total_lbl': "Сума", 'delivery_lbl': "Доставка",
            'paid': "✅ Оплачено", 'approved': "✅ Підтверджено", 'rejected': "❌ Скасовано",
            'pending': "⏳ Очікується", 'Standard': "Стандарт", 'Express': "Експрес"
        },
        'en': {
            'status_lbl': "Status", 'total_lbl': "Total price", 'delivery_lbl': "Delivery Method",
            'paid': "✅ Paid", 'approved': "✅ Approved", 'rejected': "❌ Cancelled",
            'pending': "⏳ Pending", 'Standard': "Standard", 'Express': "Express"
        }
    }

    current_loc = loc.get(lang, loc['ua'])
    text = LEXICON[lang]['my_orders_title']
    for o in orders:
        status_key = o['status']
        status_str = current_loc.get(status_key, status_key)
        delivery_key = o['delivery_method']
        delivery_str = current_loc.get(delivery_key, delivery_key)
        curr_code = o['currency_code'] if o['currency_code'] else "UAH"

        text += (
            f"🆔 #{o['id']}\n"
            f"📅 {current_loc['status_lbl']}: {status_str}\n"
            f"💰 {current_loc['total_lbl']}: {o['total_price']} {curr_code}\n"
            f"🚚 {current_loc['delivery_lbl']}: {delivery_str}\n"
            f"📜 {o['items_text']}\n"
            f"──────────────────\n"
        )
    await message.answer(text, parse_mode="HTML")


# --- Каталог ---
@user_router.message(Command("catalog"))
@user_router.message(F.text.in_([LEXICON['ua']['catalog_btn'], LEXICON['en']['catalog_btn']]))
@user_router.callback_query(F.data == "back_to_menu")
async def show_categories(message: types.Message | types.CallbackQuery):
    user_id = message.from_user.id
    lang, _, _, _ = await get_user_config(user_id)

    categories = await db.get_categories()
    text = LEXICON[lang]['choose_cat']
    kb = get_categories_kb(categories, lang)

    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@user_router.callback_query(F.data == "back_to_cats")
async def back_to_cats_handler(callback: types.CallbackQuery):
    lang, _, _, _ = await get_user_config(callback.from_user.id)
    categories = await db.get_categories()
    await callback.message.edit_text(LEXICON[lang]['choose_cat'], reply_markup=get_categories_kb(categories, lang))


@user_router.callback_query(F.data.startswith("category_"))
async def show_products_in_category(callback: types.CallbackQuery):
    lang, curr, sign, rate = await get_user_config(callback.from_user.id)
    category = callback.data.replace("category_", "")

    products = await db.get_products_by_category(category)

    if not products:
        await callback.answer(LEXICON[lang]['empty_cat'])
        return

    cat_display = LEXICON[lang].get('categories', {}).get(category, category)
    cat_label = LEXICON[lang].get('cat_label', 'Category:')

    await callback.message.edit_text(
        f"{cat_label} <b>{cat_display}</b>",
        reply_markup=get_products_kb(products, lang, sign, rate),
        parse_mode="HTML"
    )


@user_router.callback_query(F.data.startswith("product_"))
async def show_product_detail(callback: types.CallbackQuery):
    lang, curr, sign, rate = await get_user_config(callback.from_user.id)
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product(product_id)

    price_conv = convert_price(product['price'], rate)
    cat_display = LEXICON[lang].get('categories', {}).get(product['category'], product['category'])

    text = (
        f"📦 <b>{product['name']}</b>\n"
        f"📝 {product['desc']}\n"
        f"📂 {cat_display}\n"
        f"💰 {price_conv} {sign}"
    )
    await callback.message.edit_text(text,
                                     reply_markup=get_product_detail_kb(product_id, product['category'], lang),
                                     parse_mode="HTML")


# --- Кошик ---
@user_router.callback_query(F.data.startswith("add_cart_"))
async def add_to_cart_handler(callback: types.CallbackQuery):
    lang, _, _, _ = await get_user_config(callback.from_user.id)
    product_id = int(callback.data.split("_")[-1])
    await db.add_to_cart(callback.from_user.id, product_id)

    # ЛОГ: Додавання в кошик
    logger.info(f"USER_ACTION: User {callback.from_user.id} added product ID {product_id} to cart.")

    await callback.answer(LEXICON[lang]['added_cart'], show_alert=True)


@user_router.message(Command("cart"))
@user_router.message(F.text.in_([LEXICON['ua']['cart_btn'], LEXICON['en']['cart_btn']]))
async def show_cart(message: types.Message):
    lang, curr, sign, rate = await get_user_config(message.from_user.id)
    cart_items = await db.get_cart(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS

    if not cart_items:
        await message.answer(LEXICON[lang]['cart_empty'], reply_markup=get_main_keyboard(lang, is_admin))
        return

    total_uah = sum(item['price'] * item['quantity'] for item in cart_items)
    total_conv = convert_price(total_uah, rate)

    text = LEXICON[lang]['cart_title']
    unit = "/pcs" if lang == 'en' else "/шт"
    for item in cart_items:
        item_price_conv = convert_price(item['price'], rate)
        sum_item_conv = convert_price(item['price'] * item['quantity'], rate)

        if item['quantity'] > 1:
            text += f"• {item['name']} x{item['quantity']} = {sum_item_conv} {sign} ({item_price_conv}{unit})\n"
        else:
            text += f"• {item['name']} x{item['quantity']} = {sum_item_conv} {sign}\n"

    text += f"\n💰 <b>Total: {total_conv} {sign}</b>"

    await message.answer(text, reply_markup=get_cart_kb(cart_items, lang), parse_mode="HTML")


@user_router.callback_query(F.data.startswith("del_cart_"))
async def delete_cart_item(callback: types.CallbackQuery):
    lang, curr, sign, rate = await get_user_config(callback.from_user.id)
    cart_id = int(callback.data.split("_")[-1])
    await db.delete_from_cart(cart_id)

    cart_items = await db.get_cart(callback.from_user.id)
    if not cart_items:
        await callback.message.edit_text(LEXICON[lang]['cart_empty'], reply_markup=get_cart_kb([], lang))
        return

    total_uah = sum(item['price'] * item['quantity'] for item in cart_items)
    total_conv = convert_price(total_uah, rate)

    text = LEXICON[lang]['cart_title']
    unit = "/pcs" if lang == 'en' else "/шт"
    for item in cart_items:
        item_price_conv = convert_price(item['price'], rate)
        sum_item_conv = convert_price(item['price'] * item['quantity'], rate)

        if item['quantity'] > 1:
            text += f"• {item['name']} x{item['quantity']} = {sum_item_conv} {sign} ({item_price_conv}{unit})\n"
        else:
            text += f"• {item['name']} x{item['quantity']} = {sum_item_conv} {sign}\n"

    text += f"\n💰 <b>Total: {total_conv} {sign}</b>"

    await callback.message.edit_text(text, reply_markup=get_cart_kb(cart_items, lang), parse_mode="HTML")


@user_router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: types.CallbackQuery):
    lang, _, _, _ = await get_user_config(callback.from_user.id)
    await db.clear_cart(callback.from_user.id)
    await callback.message.edit_text(LEXICON[lang]['cleared'])

@user_router.message(StateFilter(OrderState), F.text.in_([LEXICON['ua']['cancel'], LEXICON['en']['cancel']]))
async def cancel_order_global(message: types.Message, state: FSMContext):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS
    await state.clear()

    logger.info(f"USER_ACTION: User {message.from_user.id} cancelled checkout process.")

    await message.answer(LEXICON[lang]['cancelled'], reply_markup=get_main_keyboard(lang, is_admin))


# Кнопка "Назад" для кожного кроку
@user_router.message(OrderState.waiting_for_name, F.text.in_([LEXICON['ua']['back_step'], LEXICON['en']['back_step']]))
async def back_from_name(message: types.Message, state: FSMContext):
    await cancel_order_global(message, state)


@user_router.message(OrderState.waiting_for_phone, F.text.in_([LEXICON['ua']['back_step'], LEXICON['en']['back_step']]))
async def back_to_name(message: types.Message, state: FSMContext):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    await state.set_state(OrderState.waiting_for_name)
    await message.answer(LEXICON[lang]['checkout_name'], reply_markup=get_checkout_step_kb(lang, show_back=False))


@user_router.message(OrderState.waiting_for_address,
                     F.text.in_([LEXICON['ua']['back_step'], LEXICON['en']['back_step']]))
async def back_to_phone(message: types.Message, state: FSMContext):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    await state.set_state(OrderState.waiting_for_phone)
    await message.answer(LEXICON[lang]['checkout_phone'], reply_markup=get_checkout_step_kb(lang, show_back=True))


@user_router.message(OrderState.waiting_for_delivery,
                     F.text.in_([LEXICON['ua']['back_step'], LEXICON['en']['back_step']]))
async def back_to_address(message: types.Message, state: FSMContext):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    await state.set_state(OrderState.waiting_for_address)
    await message.answer(LEXICON[lang]['checkout_addr'], reply_markup=get_checkout_step_kb(lang, show_back=True))


@user_router.message(OrderState.waiting_for_confirmation,
                     F.text.in_([LEXICON['ua']['back_step'], LEXICON['en']['back_step']]))
async def back_to_delivery(message: types.Message, state: FSMContext):
    lang, _, sign, rate = await get_user_config(message.from_user.id)
    await state.set_state(OrderState.waiting_for_delivery)
    await message.answer(LEXICON[lang]['checkout_method'], reply_markup=get_delivery_kb(lang, sign, rate))


@user_router.callback_query(F.data == "checkout_start")
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    lang, _, _, _ = await get_user_config(callback.from_user.id)
    await callback.message.answer(LEXICON[lang]['checkout_name'],
                                  reply_markup=get_checkout_step_kb(lang, show_back=False))
    await state.set_state(OrderState.waiting_for_name)
    await callback.answer()


@user_router.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    await state.update_data(user_name=message.text)
    await message.answer(LEXICON[lang]['checkout_phone'], reply_markup=get_checkout_step_kb(lang, show_back=True))
    await state.set_state(OrderState.waiting_for_phone)


@user_router.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    lang, _, _, _ = await get_user_config(message.from_user.id)
    if not re.match(r'^\+?\d{10,15}$', message.text):
        await message.answer("⚠️ Format: +380XXXXXXXXX")
        return
    await state.update_data(user_phone=message.text)
    await message.answer(LEXICON[lang]['checkout_addr'], reply_markup=get_checkout_step_kb(lang, show_back=True))
    await state.set_state(OrderState.waiting_for_address)


@user_router.message(OrderState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    lang, _, sign, rate = await get_user_config(message.from_user.id)
    await state.update_data(user_address=message.text)
    await message.answer(LEXICON[lang]['checkout_method'], reply_markup=get_delivery_kb(lang, sign, rate))
    await state.set_state(OrderState.waiting_for_delivery)


@user_router.message(OrderState.waiting_for_delivery)
async def process_delivery(message: types.Message, state: FSMContext):
    lang, curr, sign, rate = await get_user_config(message.from_user.id)
    is_admin = message.from_user.id in ADMIN_IDS

    delivery_price_uah = 0
    delivery_method = "Standard"

    if "Express" in message.text or "Експрес" in message.text:
        delivery_price_uah = 100
        delivery_method = "Express"
    elif "Standard" in message.text or "Стандарт" in message.text:
        delivery_method = "Standard"
    else:
        await message.answer("Будь ласка, оберіть спосіб доставки кнопкою.")
        return

    cart_items = await db.get_cart(message.from_user.id)
    if not cart_items:
        await message.answer(LEXICON[lang]['cart_empty'], reply_markup=get_main_keyboard(lang, is_admin))
        await state.clear()
        return

    products_total_uah = sum(item['price'] * item['quantity'] for item in cart_items)
    total_price_uah = products_total_uah + delivery_price_uah

    delivery_conv = convert_price(delivery_price_uah, rate)
    total_conv = convert_price(total_price_uah, rate)

    items_text = "\n".join([f"{i['name']} x{i['quantity']}" for i in cart_items])

    await state.update_data(
        delivery_method=delivery_method,
        items_text=items_text,
        total_price_uah=total_price_uah,
        total_price_conv=total_conv,
        currency_code=curr
    )

    data = await state.get_data()

    # Отримуємо локалізовану назву доставки для відображення
    deliv_key = 'check_exp' if delivery_method == "Express" else 'check_std'
    deliv_display = LEXICON[lang][deliv_key]

    confirm_text = (
        f"<b>{LEXICON[lang]['check_header']}</b>\n\n"
        f"{LEXICON[lang]['check_items']}\n{items_text}\n"
        f"{LEXICON[lang]['check_delivery']} {deliv_display} ({delivery_conv} {sign})\n"
        f"👤 {data['user_name']}\n"
        f"📞 {data['user_phone']}\n"
        f"📍 {data['user_address']}\n\n"
        f"<b>{LEXICON[lang]['check_total']} {total_conv} {sign}</b>"
    )

    await message.answer(confirm_text, reply_markup=get_confirm_order_kb(lang), parse_mode="HTML")
    await state.set_state(OrderState.waiting_for_confirmation)


@user_router.message(F.text.in_([LEXICON['ua']['confirm_btn'], LEXICON['en']['confirm_btn']]),
                     OrderState.waiting_for_confirmation)
async def confirm_order(message: types.Message, state: FSMContext, bot):
    lang, curr, sign, rate = await get_user_config(message.from_user.id)
    data = await state.get_data()

    amount_in_cents = int(data['total_price_conv'] * 100)

    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title=LEXICON[lang]['invoice_title'],
            description=LEXICON[lang]['invoice_desc'],
            payload=f"order_combined_{message.from_user.id}",
            provider_token=PAYMENT_TOKEN,
            currency=curr,
            prices=[LabeledPrice(label="Order", amount=amount_in_cents)],
            start_parameter="create_invoice"
        )
    except Exception as e:
        logger.error(f"Invoice error for user {message.from_user.id}: {e}")
        await message.answer(f"Invoice Error: {e}")


@user_router.pre_checkout_query()
async def checkout_process(pre_checkout_query: PreCheckoutQuery, bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@user_router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message, state: FSMContext, bot):
    lang, curr, sign, _ = await get_user_config(message.from_user.id)
    data = await state.get_data()
    is_admin = message.from_user.id in ADMIN_IDS

    order_data = {
        "user_id": message.from_user.id,
        "user_name": data['user_name'],
        "user_phone": data['user_phone'],
        "user_address": data['user_address'],
        "delivery_method": data['delivery_method'],
        "items_text": data['items_text'],
        "total_price": data['total_price_conv'],
        "currency_code": curr,
        "status": "paid"
    }

    order_id = await db.add_order(order_data)
    await db.clear_cart(message.from_user.id)

    # ЛОГ: Успішна оплата та створення замовлення
    logger.info(
        f"ORDER_NEW: Order #{order_id} PAID by User {message.from_user.id}. Total: {data['total_price_conv']} {curr}.")

    success_msg = LEXICON[lang]['success_pay'].replace("{id}", str(order_id))

    await message.answer(success_msg, reply_markup=get_main_keyboard(lang, is_admin), parse_mode="HTML")

    admin_text = (
        f"💰 <b>Нове замовлення #{order_id}</b>\n"
        f"👤 {data['user_name']} ({data['user_phone']})\n"
        f"📍 {data['user_address']}\n"
        f"🚚 {data['delivery_method']}\n"
        f"📦 Товари:\n{data['items_text']}\n"
        f"💰 Сума: {data['total_price_conv']} {curr}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=get_order_decision_kb(order_id),
                                   parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send admin notification to {admin_id}: {e}")

    await state.clear()