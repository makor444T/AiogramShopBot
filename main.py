import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN
from handlers_user import user_router
from handlers_admin import admin_router
from database import db

# --- НАЛАШТУВАННЯ ЛОГУВАННЯ ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler("shop_actions.log", encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

async def health_check(request):
    return web.Response(text="Bot is running OK")

async def start_web_server():
    # Render
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"SYSTEM: Web server started on port {port}")

async def main():
    # Створюємо таблиці в БД
    await db.create_tables()
    logger.info("SYSTEM: Database initialized successfully.")

    # Запускаємо веб-сервер (ОБОВ'ЯЗКОВО для Render)
    await start_web_server()

    # Запускаємо бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("SYSTEM: Bot started polling...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SYSTEM: Bot stopped by user")