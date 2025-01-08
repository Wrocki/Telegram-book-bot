import os
import telebot
import sqlite3
import logging
from datetime import datetime
from flask import Flask, request

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація бота
TOKEN = '7616371832:AAEqIUW6AYrb8jKiGURyuZYcVfnOVu94hr8'
bot = telebot.TeleBot(TOKEN)

# Ініціалізація Flask для webhook
app = Flask(__name__)

# Підключення до бази даних
def get_db():
    if not hasattr(get_db, 'database'):
        get_db.database = sqlite3.connect('books.db', check_same_thread=False)
        get_db.database.execute('''CREATE TABLE IF NOT EXISTS books
                                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                  title TEXT,
                                  author TEXT,
                                  file_id TEXT,
                                  added_date TIMESTAMP)''')
        get_db.database.commit()
    return get_db.database

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@bot.message_handler(commands=['start'])
def start(message):
    try:
        bot.reply_to(message, 
                    "Вітаю! Я бот для зберігання та пошуку книг.\n"
                    "Команди:\n"
                    "/add - додати нову книгу\n"
                    "/search - шукати книгу\n"
                    "/help - допомога")
        logger.info(f"User {message.from_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        bot.reply_to(message, "Сталася помилка. Спробуйте пізніше.")

@bot.message_handler(commands=['help'])
def help(message):
    try:
        bot.reply_to(message, 
                    "Як користуватися ботом:\n\n"
                    "1. Щоб додати книгу:\n"
                    "   - Відправте команду /add\n"
                    "   - Відправте файл книги\n"
                    "   - Відправте інформацію про книгу\n\n"
                    "2. Щоб знайти книгу:\n"
                    "   - Відправте команду /search\n"
                    "   - Введіть назву книги або автора\n\n"
                    "3. Підтримувані формати файлів:\n"
                    "   - PDF, EPUB, DOC, DOCX, TXT")
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        bot.reply_to(message, "Помилка. Спробуйте пізніше.")

@bot.message_handler(commands=['add'])
def add_book(message):
    try:
        bot.reply_to(message, "Надішліть файл книги")
        bot.register_next_step_handler(message, process_document)
    except Exception as e:
        logger.error(f"Error in add_book handler: {e}")
        bot.reply_to(message, "Помилка. Спробуйте ще раз.")

def process_document(message):
    try:
        if message.document:
            file_id = message.document.file_id
            bot.reply_to(message, 
                        "Тепер надішліть інформацію про книгу у форматі:\n"
                        "Назва: [назва книги]\n"
                        "Автор: [автор книги]")
            bot.register_next_step_handler(message, save_book_info, file_id)
        else:
            bot.reply_to(message, "Будь ласка, надішліть файл книги.")
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        bot.reply_to(message, "Помилка при обробці файлу.")

def save_book_info(message, file_id):
    try:
        text = message.text.split('\n')
        title = text[0].split(': ')[1].strip()
        author = text[1].split(': ')[1].strip()
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, file_id, added_date) VALUES (?, ?, ?, ?)",
            (title, author, file_id, datetime.now())
        )
        db.commit()
        
        bot.reply_to(message, f"Книга '{title}' автора {author} успішно збережена!")
        logger.info(f"Book saved: {title} by {author}")
    except Exception as e:
        logger.error(f"Error saving book info: {e}")
        bot.reply_to(message, "Неправильний формат даних. Спробуйте ще раз.")

@bot.message_handler(commands=['search'])
def search(message):
    try:
        bot.reply_to(message, "Введіть назву книги або автора для пошуку:")
        bot.register_next_step_handler(message, process_search)
    except Exception as e:
        logger.error(f"Error in search handler: {e}")
        bot.reply_to(message, "Помилка. Спробуйте пізніше.")

def process_search(message):
    try:
        search_query = message.text.lower()
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            "SELECT * FROM books WHERE LOWER(title) LIKE ? OR LOWER(author) LIKE ?",
            (f"%{search_query}%", f"%{search_query}%")
        )
        results = cursor.fetchall()
        
        if results:
            for book in results:
                response = f"Знайдено книгу:\nНазва: {book[1]}\nАвтор: {book[2]}"
                bot.send_message(message.chat.id, response)
                bot.send_document(message.chat.id, book[3])
            logger.info(f"Found {len(results)} books for query: {search_query}")
        else:
            bot.reply_to(message, "Книг не знайдено.")
    except Exception as e:
        logger.error(f"Error in search process: {e}")
        bot.reply_to(message, "Помилка при пошуку.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, 
                "Я розумію тільки команди:\n"
                "/start - почати роботу\n"
                "/add - додати книгу\n"
                "/search - шукати книгу\n"
                "/help - допомога")

if __name__ == "__main__":
    # Налаштування webhook для серверного режиму
    server_host = os.getenv('HOST', '0.0.0.0')
    server_port = int(os.getenv('PORT', 8443))
    
    # Запуск Flask сервера
    app.run(host=server_host, port=server_port)
