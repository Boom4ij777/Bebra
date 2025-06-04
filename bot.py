import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from random import choice
import string

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

API = "https://www.1secmail.com/api/v1/"

def generate_login(length=10):
    return ''.join(choice(string.ascii_lowercase + string.digits) for _ in range(length))

users = {}

@dp.message(commands=["start"])
async def start(message: types.Message):
    login = generate_login()
    domain = "1secmail.com"
    email = f"{login}@{domain}"
    users[message.from_user.id] = {"login": login, "domain": domain}
    await message.answer(f"📩 Ваша временная почта:
<code>{email}</code>

Нажмите кнопку ниже, чтобы проверить входящие.", reply_markup=get_keyboard())

def get_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Проверить входящие", callback_data="check_mail")
    return builder.as_markup()

@dp.callback_query(lambda c: c.data == "check_mail")
async def check_mail(callback: types.CallbackQuery):
    user = users.get(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Сначала нажмите /start")
        return

    login = user["login"]
    domain = user["domain"]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API}?action=getMessages&login={login}&domain={domain}") as resp:
            messages = await resp.json()
            if not messages:
                await callback.message.answer("📭 Новых писем нет.")
                return
            text = "📨 Найденные письма:

"
            for msg in messages:
                text += f"🔹 <b>От:</b> {msg['from']}
🔹 <b>Тема:</b> {msg['subject']}
🔹 ID: <code>{msg['id']}</code>

"
            await callback.message.answer(text + "✉ Чтобы прочитать письмо, напиши /read ID")

@dp.message(lambda message: message.text.startswith("/read"))
async def read_message(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("❌ Используйте: /read ID")
        return

    msg_id = parts[1]
    user = users.get(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала нажмите /start")
        return

    login = user["login"]
    domain = user["domain"]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API}?action=readMessage&login={login}&domain={domain}&id={msg_id}") as resp:
            msg = await resp.json()
            text = f"📨 <b>От:</b> {msg['from']}
<b>Тема:</b> {msg['subject']}

{msg['textBody'] or 'Нет текста'}"
            await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())