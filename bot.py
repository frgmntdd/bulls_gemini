import telebot
import os
import google.generativeai as genai
from flask import Flask, request

# --- НАСТРОЙКИ ---
# Получаем токены из переменных окружения Vercel
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# --- Инициализация модели Gemini ---
# Проверяем, есть ли ключ API
if not GEMINI_API_KEY:
    raise ValueError("Не найден GEMINI_API_KEY. Убедитесь, что он добавлен в переменные окружения.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro')
# Создаем "чистый" чат для старта
chat = model.start_chat(history=[])

# --- Обработка команды /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаем клавиатуру с кнопкой для сброса диалога
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("🔄 Новый диалог")
    markup.add(item1)

    bot.send_message(message.chat.id,
                     "Привет! Я чат-бот на базе Google Gemini. Просто напиши мне что-нибудь, и я отвечу. \n\nЕсли захочешь начать разговор с чистого листа, нажми 'Новый диалог'.",
                     reply_markup=markup)

# --- Обработка текстовых сообщений ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    global chat # Объявляем, что будем использовать глобальную переменную chat

    # Если пользователь хочет начать новый диалог
    if message.text == "🔄 Новый диалог":
        # Создаем новый, чистый объект чата
        chat = model.start_chat(history=[])
        bot.send_message(message.chat.id, "Отлично, начинаем разговор с начала. Что хочешь обсудить?")
        return # Выходим из функции, чтобы не отправлять это сообщение в Gemini

    try:
        # Показываем пользователю, что мы "думаем"
        bot.send_chat_action(message.chat.id, 'typing')

        # Отправляем сообщение пользователя в Gemini и получаем ответ
        response = chat.send_message(message.text)

        # Отправляем ответ от Gemini пользователю
        bot.send_message(message.chat.id, response.text)

    except Exception as e:
        # Если что-то пошло не так
        print(f"Произошла ошибка: {e}")
        bot.send_message(message.chat.id, "Ой, что-то пошло не так. Попробуй спросить еще раз чуть позже.")


# --- Секция для работы на Vercel ---
app = Flask(__name__)

@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f'https://{os.environ.get("VERCEL_URL")}/{TELEGRAM_TOKEN}')
    return "Вебхук установлен", 200

# Для локального запуска (если понадобится)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))