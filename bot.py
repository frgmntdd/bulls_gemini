import telebot
import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from flask import Flask, request

# --- НАСТРОЙКИ И КОНСТАНТЫ ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Тайм-аут для запроса к Gemini в секундах. Должен быть меньше тайм-аута Vercel (10-15с)
GEMINI_REQUEST_TIMEOUT = 9 

# --- ИНИЦИАЛИЗАЦИЯ ---
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY должны быть установлены в переменных окружения.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# Используем самую мощную доступную модель в публичном API
model = genai.GenerativeModel('gemini-1.5-pro-latest')


# --- ОСНОВНАЯ ЛОГИКА БОТА ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    bot.send_message(message.chat.id, "Привет! Я бот на базе Gemini 1.5 Pro. Задайте мне вопрос, и я постараюсь ответить.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Основной обработчик текстовых сообщений с надежной обработкой ошибок и тайм-аутом."""
    
    placeholder = None
    try:
        # 1. Сразу отправляем сообщение-заглушку.
        placeholder = bot.reply_to(message, "⏳ Обрабатываю ваш запрос...")

        # 2. Делаем запрос к Gemini с установленным тайм-аутом.
        # Это ключевое изменение для предотвращения "вечного зависания".
        response = model.generate_content(
            message.text,
            request_options={'timeout': GEMINI_REQUEST_TIMEOUT}
        )

        # 3. Если ответ получен, редактируем заглушку.
        bot.edit_message_text(
            chat_id=placeholder.chat.id,
            message_id=placeholder.message_id,
            text=response.text
        )

    # 4. Обрабатываем ВСЕ возможные ошибки, чтобы бот никогда не молчал.
    except google_exceptions.DeadlineExceeded:
        # Эта ошибка возникает, если наш тайм-аут (9с) сработал.
        print(f"[ERROR] Тайм-аут запроса для пользователя {message.from_user.id}")
        bot.edit_message_text(
            chat_id=placeholder.chat.id,
            message_id=placeholder.message_id,
            text="😥 **Не удалось получить ответ вовремя.**\n\nМодель слишком долго думала над вашим запросом. Попробуйте упростить вопрос или повторить попытку позже."
        )

    except google_exceptions.GoogleAPICallError as e:
        # Ошибки, связанные с самим API Google (неправильный ключ, модель не найдена и т.д.)
        print(f"[ERROR] Ошибка API Google: {e}")
        bot.edit_message_text(
            chat_id=placeholder.chat.id,
            message_id=placeholder.message_id,
            text=f"😥 **Произошла ошибка на стороне API Google.**\n\nТехническая информация:\n`{e}`"
        )
    
    except Exception as e:
        # Ловим все остальные ошибки (проблемы с сетью, ошибки в нашем коде и т.д.)
        print(f"[ERROR] Непредвиденная ошибка: Тип: {type(e).__name__}, Детали: {e}")
        # Проверяем, существует ли еще placeholder, прежде чем его редактировать
        if placeholder:
            bot.edit_message_text(
                chat_id=placeholder.chat.id,
                message_id=placeholder.message_id,
                text=f"😥 **Произошла непредвиденная ошибка.**\n\nПожалуйста, попробуйте еще раз. Если проблема повторится, значит что-то серьезно сломалось.\n\nТехническая информация:\n`{e}`"
            )


# --- СЕКЦИЯ ДЛЯ VERSEL ---
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
    return "Вебхук успешно установлен", 200