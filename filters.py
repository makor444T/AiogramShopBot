from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS

class IsAdmin(BaseFilter):
    """
    Фільтр перевіряє, чи є користувач адміністратором.
    Працює як для повідомлень (Message), так і для кнопок (CallbackQuery).
    """
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        # Перевіряємо ID користувача у списку адмінів
        return event.from_user.id in ADMIN_IDS