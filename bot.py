import telebot
import os
import google.generativeai as genai
from flask import Flask, request

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
# Берем токены из переменных окружения Vercel. Это безопасно.
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Инициализация ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Проверяем, что ключ Gemini API доступен
if not GEMINI_API_KEY:
    # Эта ошибка будет видна в логах Vercel, если вы забудете добавить ключ
    raise ValueError("Не найден GEMINI_API_KEY. Добавьте его в переменные окружения Vercel.")

# Конфигурируем API Gemini
genai.configure(api_key=GEMINI_API_KEY)
# Используем самую свежую и мощную модель
model = genai.GenerativeModel('gemini-2.5-flash')


# --- ОБРАБОТЧИКИ КОМАНД TELEGRAM ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("👋 Привет!")
    markup.add(item1)
    bot.send_message(message.chat.id,
                     "Привет! Я чат-бот на базе Google Gemini 1.5 Pro. Задай мне любой вопрос.",
                     reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Основной обработчик текстовых сообщений"""

    # 1. Отправляем сообщение-заглушку и сохраняем его
    # Это дает пользователю понять, что запрос принят в работу
    placeholder_message = bot.send_message(message.chat.id, "⏳ Думаю над вашим вопросом...")

    try:
        # 2. Отправляем запрос в Gemini
        # Мы не используем больше историю чата, каждое сообщение - новый запрос.
        # Это делает бота более надежным на stateless платформах вроде Vercel.
        print(f"Пользователь {message.from_user.id} отправил запрос: {message.text}") # Логирование для отладки
        response = model.generate_content(message.text)
        
        # 3. Редактируем сообщение-заглушку, заменяя его на ответ от Gemini
        bot.edit_message_text(chat_id=placeholder_message.chat.id,
                              message_id=placeholder_message.message_id,
                              text=response.text)

    except Exception as e:
        # 4. Если произошла ошибка, сообщаем об этом пользователю
        # Логируем ошибку, чтобы видеть ее в консоли Vercel
        print(f"!!! Произошла ошибка при обработке запроса: {e}")
        
        error_text = (
            "😥 Ой, что-то пошло не так при обращении к Gemini.\n\n"
            "Возможно, в моем ответе содержался контент, который нарушает правила безопасности.\n\n"
            f"**Техническая информация:**\n`{e}`"
        )
        # Редактируем сообщение-заглушку, заменяя его на текст ошибки
        bot.edit_message_text(chat_id=placeholder_message.chat.id,
                              message_id=placeholder_message.message_id,
                              text=error_text,
                              parse_mode='Markdown')


# --- СЕКЦИЯ ДЛЯ РАБОТЫ НА VERSEL ---
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
    # Автоматическая установка вебхука с использованием системной переменной VERCEL_URL
    bot.set_webhook(url=f'https://{os.environ.get("VERCEL_URL")}/{TELEGRAM_TOKEN}')
    return "Вебхук успешно установлен", 200