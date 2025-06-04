import logging
import random
import string
import asyncio
import requests
import os
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

API_BASE = "https://api.mail.tm"
logging.basicConfig(level=logging.INFO)

# Получаем токен из .env или переменных Railway
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения почты по user_id
user_accounts = {}

def create_account():
    response = requests.get(f"{API_BASE}/domains")
    domain = response.json()['hydra:member'][0]['domain']

    login = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{login}@{domain}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    data = {"address": email, "password": password}
    r = requests.post(f"{API_BASE}/accounts", json=data)
    r.raise_for_status()
    return email, password

def get_token(email, password):
    data = {"address": email, "password": password}
    r = requests.post(f"{API_BASE}/token", json=data)
    r.raise_for_status()
    return r.json()['token']

def get_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE}/messages", headers=headers)
    r.raise_for_status()
    return r.json()

def read_message(token, message_id):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE}/messages/{message_id}", headers=headers)
    r.raise_for_status()
    return r.json()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! Я бот для временной почты.\n"
        "/create - Создать новый email\n"
        "/inbox - Посмотреть входящие\n"
        "/read <id> - Прочитать письмо"
    )

@dp.message_handler(commands=['create'])
async def create_handler(message: types.Message):
    await message.answer("Создаю временный email...")
    try:
        email, password = create_account()
        token = get_token(email, password)
        user_accounts[message.from_user.id] = {"email": email, "password": password, "token": token}
        await message.answer(f"Создан email:\n📧 {email}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message_handler(commands=['inbox'])
async def inbox_handler(message: types.Message):
    user = user_accounts.get(message.from_user.id)
    if not user:
        await message.answer("Сначала создай почту командой /create")
        return
    token = user["token"]
    try:
        data = get_messages(token)
        if data['hydra:totalItems'] == 0:
            await message.answer("Писем нет.")
            return
        response = ""
        for msg in data['hydra:member']:
            response += f"📩 ID: {msg['id']}\nТема: {msg['subject']}\nОт: {msg['from']['address']}\n\n"
        await message.answer(response)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message_handler(commands=['read'])
async def read_handler(message: types.Message):
    args = message.get_args().strip()
    user = user_accounts.get(message.from_user.id)
    if not user:
        await message.answer("Сначала создай почту командой /create")
        return
    if not args:
        await message.answer("Напиши команду так: /read <id>")
        return
    try:
        msg = read_message(user["token"], args)
        content = msg.get("text") or msg.get("html") or "(пусто)"
        await message.answer(f"📬 Тема: {msg['subject']}\n\n{content}")
    except Exception as e:
        await message.answer(f"Ошибка при чтении: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)