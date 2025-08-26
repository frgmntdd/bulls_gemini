import telebot
import os

# Вставь сюда свой токен, который ты получил от BotFather
TOKEN = '8417793646:AAE8V8RpGHjL85w5HW4POmmealEhtqdFa68'

bot = telebot.TeleBot(TOKEN)

# --- Обработка команды /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаем клавиатуру с кнопками
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("👋 Поздороваться")
    item2 = telebot.types.KeyboardButton("❓ Задать вопрос")
    markup.add(item1, item2)

    # Отправляем приветственное сообщение с кнопками
    bot.send_message(message.chat.id,
                     "Привет! Я твой новый бот. Чем могу помочь?",
                     reply_markup=markup)

# --- Обработка текстовых сообщений ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "👋 Поздороваться":
        bot.send_message(message.chat.id, "И тебе привет! Как дела?")
    elif message.text == "❓ Задать вопрос":
        bot.send_message(message.chat.id, "Спрашивай, не стесняйся!")
    else:
        bot.send_message(message.chat.id, "Я пока не понимаю эту команду.")

# --- ЭТОТ КОД НУЖЕН ДЛЯ VERSEL ---
# Vercel будет обращаться к этому файлу.
# Мы не используем стандартный bot.polling(), так как Vercel работает по-другому.
# Вместо этого мы будем использовать вебхуки.

from flask import Flask, request

app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # Устанавливаем вебхук на адрес нашего приложения в Vercel
    # ВАЖНО: Вместо 'YOUR_VERCEL_APP_URL' нужно будет вставить реальный адрес
    # Но для локального тестирования этот код можно закомментировать.
    # Для деплоя на Vercel мы настроим это через переменные окружения.
    # bot.set_webhook(url='https://YOUR_VERCEL_APP_URL/' + TOKEN)
    return "!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))