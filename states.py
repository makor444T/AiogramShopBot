from aiogram.fsm.state import State, StatesGroup

class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_delivery = State()
    waiting_for_confirmation = State()

class AdminAddProduct(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_desc = State()
    waiting_for_price = State()