from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from texts import LEXICON


# --- НАЛАШТУВАННЯ ---
def get_settings_choice_kb(lang='ua') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON[lang]['change_lang_btn'], callback_data="settings_lang")
    builder.button(text=LEXICON[lang]['change_curr_btn'], callback_data="settings_curr")
    builder.adjust(1)
    return builder.as_markup()


def get_lang_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="setlang_ua")
    builder.button(text="🇺🇸 English", callback_data="setlang_en")
    builder.adjust(2)
    return builder.as_markup()


def get_currency_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 UAH (Гривня)", callback_data="setcurr_UAH")
    builder.button(text="🇺🇸 USD (Dollar)", callback_data="setcurr_USD")
    builder.button(text="🇪🇺 EUR (Euro)", callback_data="setcurr_EUR")
    builder.adjust(1)
    return builder.as_markup()


# --- Головне меню ---
def get_main_keyboard(lang='ua', is_admin=False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    buttons = LEXICON[lang]['main_menu_btn']
    for btn_text in buttons:
        builder.button(text=btn_text)

    if is_admin:
        builder.button(text=LEXICON[lang]['admin_btn'])
        builder.adjust(2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 1)

    return builder.as_markup(resize_keyboard=True)


# --- Каталог ---
def get_categories_kb(categories: list, lang='ua') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        # Отримуємо переклад категорії, якщо його немає - залишаємо оригінал
        display_name = LEXICON[lang].get('categories', {}).get(cat, cat)

        # Передаємо в callback оригінальну назву (ключ), а показуємо переклад
        builder.button(text=f"📂 {display_name}", callback_data=f"category_{cat}")
    builder.adjust(2)
    return builder.as_markup()


def get_products_kb(products: list, lang='ua', currency_sign='грн', rate=1.0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        price = round(product['price'] / rate, 2)
        builder.button(
            text=f"{product['name']} - {price} {currency_sign}",
            callback_data=f"product_{product['id']}"
        )

    builder.button(text=LEXICON[lang]['back_cats'], callback_data="back_to_cats")
    builder.adjust(1)
    return builder.as_markup()


def get_product_detail_kb(product_id: int, category: str, lang='ua') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON[lang]['add_cart'], callback_data=f"add_cart_{product_id}")
    builder.button(text=LEXICON[lang]['back_cats'], callback_data=f"category_{category}")
    builder.adjust(1)
    return builder.as_markup()


# --- Кошик ---
def get_cart_kb(cart_items: list, lang='ua') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not cart_items:
        builder.button(text=LEXICON[lang]['catalog_btn'], callback_data="back_to_cats")
        return builder.as_markup()

    for item in cart_items:
        builder.button(text=f"❌ {item['name']}", callback_data=f"del_cart_{item['cart_id']}")

    builder.button(text=LEXICON[lang]['cart_clear'], callback_data="clear_cart")
    builder.button(text=LEXICON[lang]['cart_checkout'], callback_data="checkout_start")
    builder.button(text=LEXICON[lang]['back_menu'], callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


# Клавіатура для етапів введення (Ім'я, Телефон, Адреса)
def get_checkout_step_kb(lang='ua', show_back=True) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    if show_back:
        builder.button(text=LEXICON[lang]['back_step'])

    builder.button(text=LEXICON[lang]['cancel'])

    # Якщо є "Назад", то 2 кнопки в ряд, якщо ні - 1
    builder.adjust(2 if show_back else 1)
    return builder.as_markup(resize_keyboard=True)


def get_delivery_kb(lang='ua', currency_sign='грн', rate=1.0) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    exp_price = round(100 / rate, 2)

    builder.button(text=LEXICON[lang]['delivery_std'])
    builder.button(text=f"{LEXICON[lang]['delivery_exp']} (+{exp_price} {currency_sign})")

    # Кнопки навігації
    builder.button(text=LEXICON[lang]['back_step'])
    builder.button(text=LEXICON[lang]['cancel'])

    builder.adjust(1, 1, 2)  # Доставка, Доставка, [Назад, Скасувати]
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_confirm_order_kb(lang='ua') -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=LEXICON[lang]['confirm_btn'])

    # Кнопки навігації
    builder.button(text=LEXICON[lang]['back_step'])
    builder.button(text=LEXICON[lang]['cancel'])

    builder.adjust(1, 2)  # Підтвердити, [Назад, Скасувати]
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# --- Адмінка ---
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="/add_item")
    builder.button(text="/remove_item")
    builder.button(text="/orders")
    builder.button(text="/start")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_delete_item_kb(products_list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products_list:
        builder.button(text=f"❌ {product['name']}", callback_data=f"admin_del_{product['id']}")
    builder.adjust(1)
    return builder.as_markup()


def get_orders_list_kb(orders_list, loc_texts) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for o in orders_list:
        status_icon = {
            'pending': '⏳', 'paid': '✅', 'approved': '🚚', 'rejected': '❌'
        }.get(o['status'], '❓')

        currency = o['currency_code'] if o['currency_code'] else 'UAH'

        btn_text = f"#{o['id']} {status_icon} | {o['total_price']} {currency}"
        builder.button(text=btn_text, callback_data=f"view_order_{o['id']}")

    builder.button(text="🔄 Оновити / Refresh", callback_data="admin_refresh_orders")
    builder.adjust(1)
    return builder.as_markup()


def get_order_decision_kb(order_id: int, show_actions=True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if show_actions:
        builder.button(text="✅ Прийняти", callback_data=f"approve_{order_id}")
        builder.button(text="❌ Відхилити", callback_data=f"reject_{order_id}")

    builder.button(text="🔙 До списку", callback_data="admin_back_orders")

    if show_actions:
        builder.adjust(2, 1)
    else:
        builder.adjust(1)

    return builder.as_markup()