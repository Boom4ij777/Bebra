import telebot
from telebot import types
import json
import os

TOKEN = '8029992344:AAENU71rYtIQK1W0qV2H3x4ABjroCNkzzaU'  # Твой токен
ADMIN_ID = 7817919248  # Твой ID

bot = telebot.TeleBot(TOKEN)

MESSAGES_FILE = 'messages.json'
FILES_DB = 'files.json'
FILES_FOLDER = 'files'

if not os.path.exists(FILES_FOLDER):
    os.makedirs(FILES_FOLDER)

if os.path.exists(MESSAGES_FILE):
    with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
        messages_db = json.load(f)
else:
    messages_db = {}

if os.path.exists(FILES_DB):
    with open(FILES_DB, 'r', encoding='utf-8') as f:
        files_db = json.load(f)
else:
    files_db = []

def save_messages():
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages_db, f, ensure_ascii=False, indent=2)

def save_files():
    with open(FILES_DB, 'w', encoding='utf-8') as f:
        json.dump(files_db, f, ensure_ascii=False, indent=2)

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Отправить сообщение админу'))
    keyboard.add(types.KeyboardButton('Файлы'))
    if message.from_user.id == ADMIN_ID:
        keyboard.add(types.KeyboardButton('Добавить файл'))
        keyboard.add(types.KeyboardButton('Просмотреть все сообщения'))
    bot.send_message(message.chat.id, 'Привет! Выбери действие:', reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == 'Отправить сообщение админу')
def ask_message(message):
    msg = bot.send_message(message.chat.id, 'Напиши своё сообщение для админа:')
    bot.register_next_step_handler(msg, forward_to_admin)

def forward_to_admin(message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or 'Пользователь'
    text = message.text

    if user_id not in messages_db:
        messages_db[user_id] = []
    messages_db[user_id].append({'from': user_name, 'text': text})
    save_messages()

    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton('Ответить', callback_data=f'reply_{user_id}')
    markup.add(btn)
    try:
        bot.send_message(ADMIN_ID, f"Новое сообщение от {user_name} (id {user_id}):\n\n{text}", reply_markup=markup)
        bot.send_message(message.chat.id, 'Сообщение отправлено админу.')
    except Exception as e:
        bot.send_message(message.chat.id, f'Ошибка при отправке админу: {e}')

@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def handle_reply(call):
    user_id = call.data.split('_')[1]
    msg = bot.send_message(call.from_user.id, f'Напиши ответ для пользователя {user_id}:')
    bot.register_next_step_handler(msg, send_reply_to_user, user_id)
    bot.answer_callback_query(call.id)

def send_reply_to_user(message, user_id):
    text = message.text
    user_name = message.from_user.first_name or 'Админ'

    if user_id not in messages_db:
        messages_db[user_id] = []
    messages_db[user_id].append({'from': user_name, 'text': text})
    save_messages()

    try:
        bot.send_message(int(user_id), f'Ответ от администратора:\n\n{text}')
        bot.send_message(message.chat.id, 'Ответ отправлен пользователю.')
    except Exception as e:
        bot.send_message(message.chat.id, f'Ошибка при отправке пользователю: {e}')

@bot.message_handler(func=lambda m: m.text == 'Просмотреть все сообщения' and m.from_user.id == ADMIN_ID)
def show_all_messages(message):
    if not messages_db:
        bot.send_message(ADMIN_ID, 'Нет сообщений.')
        return

    text = 'Все сообщения:\n\n'
    for user_id, msgs in messages_db.items():
        text += f"Пользователь {user_id}:\n"
        for m in msgs:
            text += f"{m['from']}: {m['text']}\n"
        text += '\n'

    bot.send_message(ADMIN_ID, text)

@bot.message_handler(func=lambda m: m.text == 'Добавить файл' and m.from_user.id == ADMIN_ID)
def ask_file(message):
    msg = bot.send_message(message.chat.id, 'Отправь файл, который хочешь добавить:')
    bot.register_next_step_handler(msg, receive_file)

@bot.message_handler(content_types=['document'])
def receive_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_name = message.document.file_name
        file_path = os.path.join(FILES_FOLDER, file_name)

        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        if file_name not in files_db:
            files_db.append(file_name)
            save_files()

        bot.send_message(ADMIN_ID, f'Файл "{file_name}" успешно добавлен.')
    except Exception as e:
        bot.send_message(ADMIN_ID, f'Ошибка при сохранении файла: {e}')

@bot.message_handler(func=lambda m: m.text == 'Файлы')
def send_files_list(message):
    if not files_db:
        bot.send_message(message.chat.id, 'Файлов пока нет.')
        return

    markup = types.InlineKeyboardMarkup()
    for fname in files_db:
        markup.add(types.InlineKeyboardButton(fname, callback_data=f"file_{fname}"))

    bot.send_message(message.chat.id, "Доступные файлы:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('file_'))
def send_file(call):
    file_name = call.data[5:]
    file_path = os.path.join(FILES_FOLDER, file_name)

    try:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                bot.send_document(call.message.chat.id, f)
        else:
            bot.send_message(call.message.chat.id, "Файл не найден.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при отправке файла: {e}")

    bot.answer_callback_query(call.id)

print("✅ Бот активен")
bot.infinity_polling()
