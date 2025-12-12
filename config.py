import os
from dotenv import load_dotenv

load_dotenv()

# --- КОНФІГУРАЦІЯ БОТА ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Токен платіжної системи
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

# --- АДМІНІСТРАТОРИ ---
env_admins = os.getenv("ADMIN_IDS")
if env_admins:
    ADMIN_IDS = [int(id_str) for id_str in env_admins.split(",")]
else:
    ADMIN_IDS = []

# --- КУРСИ ВАЛЮТ ---
EXCHANGE_RATES = {
    'UAH': 1,
    'USD': 42.0,
    'EUR': 45.0
}

CURRENCY_SIGNS = {
    'UAH': 'UAH',
    'USD': '$',
    'EUR': '€'
}