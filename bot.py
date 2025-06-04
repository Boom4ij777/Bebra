import os
import requests
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.contrib.middlewares.logging import LoggingMiddleware

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv("TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Генерация случайного логина
def generate_random_login(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# Получение письма
def get_messages(login, domain):
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# Получение содержимого письма
def get_mail_content(login, domain, message_id):
    url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={message_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {}

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Нажми /mail чтобы сгенерировать временную почту.")

@dp.message_handler(commands=['mail'])
async def cmd_mail(message: types.Message):
    login = generate_random_login()
    domain = "1secmail.com"
    email = f"{login}@{domain}"
    
    await message.answer(f"Вот твоя временная почта:\n📧 {email}\n\nЧерез минуту напиши /inbox чтобы проверить входящие.")
    
    # Сохраняем логин и домен в память (в реальном проекте использовать базу данных)
    with open(f"{message.from_user.id}.txt", "w") as f:
        f.write(f"{login},{domain}")

@dp.message_handler(commands=['inbox'])
async def cmd_inbox(message: types.Message):
    try:
        with open(f"{message.from_user.id}.txt", "r") as f:
            login, domain = f.read().split(",")
    except FileNotFoundError:
        await message.answer("Сначала сгенерируй почту с помощью /mail")
        return

    messages = get_messages(login, domain)
    if not messages:
        await message.answer("📭 Пока нет новых писем.")
    else:
        reply = "📬 Входящие письма:\n"
        for msg in messages:
            content = get_mail_content(login, domain, msg['id'])
            reply += f"\n📨 От: {msg['from']}\nТема: {msg['subject']}\nСообщение: {content.get('textBody', '')[:200]}...\n"
        await message.answer(reply)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)