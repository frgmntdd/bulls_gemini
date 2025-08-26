import telebot
import os
import google.generativeai as genai
from flask import Flask, request
import time
import threading

# --- НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ ---

# Безопасно получаем токены из переменных окружения Vercel
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Проверяем наличие токенов при запуске
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY должны быть установлены в переменных окружения.")

# Инициализируем Telegram бота и API Gemini
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
# Используем самую быструю и современную модель
model = genai.GenerativeModel('gemini-2.5-flash')

# Множество для отслеживания ID пользователей, чьи запросы в обработке
# Это наша защита от одновременных запросов от одного юзера
processing_requests = set()


# --- ОСНОВНАЯ ЛОГИКА БОТА ---

def edit_placeholder_message(message, stop_event):
    """
    Функция для анимации сообщения "Думаю...".
    Она запускается в отдельном потоке.
    """
    animation_chars = ['⏳', '🧠', '💡', '✍️']
    start_time = time.time()
    i = 0
    while not stop_event.is_set():
        elapsed_time = int(time.time() - start_time)
        char = animation_chars[i % len(animation_chars)]
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=f"{char} Думаю... ({elapsed_time}с)"
            )
            i += 1
            time.sleep(1.2) # Обновляем чуть реже секунды, чтобы не спамить API Telegram
        except telebot.apihelper.ApiTelegramException as e:
            # Если сообщение не найдено (уже заменено ответом) или не изменилось, просто выходим
            if e.result.status_code == 400:
                break
        except Exception:
            break # Выходим при любой другой ошибке


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    bot.send_message(message.chat.id, "Привет! Я твой обновленный бот на базе Gemini 1.5 Flash. Задай мне любой вопрос.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Основной обработчик текстовых сообщений"""
    user_id = message.from_user.id

    # 1. Проверяем, не обрабатывается ли уже другой запрос от этого пользователя
    if user_id in processing_requests:
        bot.reply_to(message, "Пожалуйста, подождите ответа на предыдущий вопрос, прежде чем задавать новый.")
        return

    # 2. Добавляем пользователя в список обрабатываемых и отправляем заглушку
    processing_requests.add(user_id)
    placeholder = bot.reply_to(message, "⏳ Получил ваш вопрос...")

    # 3. Запускаем анимацию в отдельном потоке
    stop_event = threading.Event()
    animation_thread = threading.Thread(target=edit_placeholder_message, args=(placeholder, stop_event))
    animation_thread.start()

    try:
        # 4. Отправляем запрос в Gemini
        response = model.generate_content(message.text)
        
        # 5. Останавливаем анимацию и редактируем сообщение, вставляя ответ
        stop_event.set()
        animation_thread.join() # Ждем завершения потока анимации
        bot.edit_message_text(
            chat_id=placeholder.chat.id,
            message_id=placeholder.message_id,
            text=response.text
        )

    except Exception as e:
        # 6. В случае любой ошибки, останавливаем анимацию и сообщаем об этом
        stop_event.set()
        animation_thread.join()
        print(f"!!! Произошла ошибка: {e}") # Логируем для отладки на Vercel
        
        # Пытаемся извлечь причину блокировки из ошибки, если она есть
        error_message = str(e)
        if "response.prompt_feedback" in error_message:
            error_details = "Мой ответ был заблокирован из-за нарушения правил безопасности. Попробуйте переформулировать запрос."
        else:
            error_details = f"Техническая информация:\n`{error_message}`"

        bot.edit_message_text(
            chat_id=placeholder.chat.id,
            message_id=placeholder.message_id,
            text=f"😥 Ой, не удалось получить ответ.\n\n{error_details}",
            parse_mode='Markdown'
        )
    finally:
        # 7. В любом случае (успех или ошибка) убираем пользователя из списка
        processing_requests.remove(user_id)


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