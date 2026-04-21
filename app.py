import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'gkz4_ultra_auto_chat'

# Ссылка на базу из настроек Render
DATABASE_URL = os.environ.get('DATABASE_URL') [cite: 1]

def get_db_connection():
    # Подключаемся к PostgreSQL
    conn = psycopg2.connect(DATABASE_URL, sslmode='require') [cite: 1]
    return conn

def init_db():
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor() [cite: 1]
    # Создаем таблицы, если их еще нет в базе
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            category TEXT,
            name TEXT,
            price TEXT,
            img TEXT,
            owner TEXT
        );
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY,
            sender TEXT,
            recipient TEXT,
            message TEXT,
            time TEXT,
            is_read BOOLEAN DEFAULT FALSE
        );
    ''') [cite: 1]
    conn.commit() [cite: 1]
    cur.close() [cite: 1]
    conn.close() [cite: 1]

# Запускаем создание таблиц
init_db() [cite: 1]

GAMES_CONFIG = {
    "slap": {"name": "Slap Battles", "icon": "🖐️", "currency": "Слепы / R$", "options": ["Перчатка", "Бейдж", "Фарм"], "hint": "Название перчатки"},
    "bloxfruits": {"name": "Blox Fruits", "icon": "🍎", "currency": "Бели / R$", "options": ["Фрукт", "Меч", "Прокачка"], "hint": "LVL"},
    "99nights": {"name": "99 Ночей", "icon": "🌙", "currency": "Гемы", "options": ["Прожить дни", "Геймпас"], "hint": "Кол-во дней"},
    "garden": {"name": "Вырасти Сад", "icon": "🌱", "currency": "Шейкели", "options": ["Редкое семя", "Аккаунт"], "hint": "Растение"},
    "adopt": {"name": "Adopt Me!", "icon": "🐶", "currency": "Петы", "options": ["Неон пет", "Мега-неон"], "hint": "Какой пет?"},
    "ttd": {"name": "Toilet Tower Defense", "icon": "🚽", "currency": "Гемы", "options": ["Юнит", "Мифик"], "hint": "Имя юнита"},
    "ps99": {"name": "Pet Sim 99", "icon": "🐱", "currency": "Гемы", "options": ["Huge Пет", "Титаник"], "hint": "Имя пета"},
    "robux": {"name": "Робуксы", "icon": "🪙", "currency": "руб.", "options": ["Трансфер (1к3)", "Курс 1к2"], "hint": "Сколько R$?"}
} [cite: 1]

# Контекстный процессор для счетчика непрочитанных сообщений
@app.context_processor
def inject_unread_count():
    if 'user' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM chats WHERE recipient = %s AND is_read = FALSE', (session['user'],))
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return dict(total_unread=count)
    return dict(total_unread=0)

@app.route('/')
def home():
    return render_template('index.html', games=GAMES_CONFIG, user=session.get('user')) [cite: 1]

@app.route('/category/<game_key>')
def category(game_key):
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor(cursor_factory=RealDictCursor) [cite: 1]
    cur.execute('SELECT * FROM products WHERE category = %s', (game_key,)) [cite: 1]
    items = cur.fetchall() [cite: 1]
    cur.close() [cite: 1]
    conn.close() [cite: 1]
    return render_template('category.html', game=GAMES_CONFIG.get(game_key), game_key=game_key, items=items, user=session.get('user')) [cite: 1]

@app.route('/my_chats')
def my_chats():
    if 'user' not in session: return redirect(url_for('login')) [cite: 1]
    user = session['user'] [cite: 1]
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Считаем непрочитанные от каждого собеседника
    cur.execute('''
        SELECT interlocutor, COUNT(id) FILTER (WHERE is_read = FALSE AND recipient = %s) as unread_count
        FROM (
            SELECT id, recipient, is_read, CASE WHEN sender = %s THEN recipient ELSE sender END as interlocutor
            FROM chats
            WHERE sender = %s OR recipient = %s
        ) sub
        GROUP BY interlocutor
    ''', (user, user, user, user))
    
    chats_info = cur.fetchall()
    cur.close() [cite: 1]
    conn.close() [cite: 1]
    return render_template('my_chats.html', chats_info=chats_info, user=user)

@app.route('/chat/<recipient>')
def chat(recipient):
    if 'user' not in session: return redirect(url_for('login')) [cite: 1]
    user = session['user'] [cite: 1]
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor(cursor_factory=RealDictCursor) [cite: 1]
    
    # Помечаем сообщения как прочитанные при входе в чат
    cur.execute('UPDATE chats SET is_read = TRUE WHERE sender = %s AND recipient = %s', (recipient, user))
    conn.commit()

    cur.execute('SELECT * FROM chats WHERE (sender = %s AND recipient = %s) OR (sender = %s AND recipient = %s) ORDER BY id', 
                (user, recipient, recipient, user)) [cite: 1]
    messages = cur.fetchall() [cite: 1]
    cur.close() [cite: 1]
    conn.close() [cite: 1]
    return render_template('chat.html', recipient=recipient, messages=messages, user=user) [cite: 1]

@app.route('/send_message/<recipient>', methods=['POST'])
def send_message(recipient):
    if 'user' not in session: return jsonify({"status": "error"}), 403 [cite: 1]
    msg_text = request.form.get('text') [cite: 1]
    msg_time = datetime.now().strftime("%H:%M") [cite: 1]
    
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor() [cite: 1]
    cur.execute('INSERT INTO chats (sender, recipient, message, time) VALUES (%s, %s, %s, %s)',
                (session['user'], recipient, msg_text, msg_time)) [cite: 1]
    conn.commit() [cite: 1]
    cur.close() [cite: 1]
    conn.close() [cite: 1]
    return jsonify({"from": session['user'], "text": msg_text, "time": msg_time}) [cite: 1]

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password') [cite: 1]
        conn = get_db_connection() [cite: 1]
        cur = conn.cursor(cursor_factory=RealDictCursor) [cite: 1]
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (u, p)) [cite: 1]
        user = cur.fetchone() [cite: 1]
        cur.close() [cite: 1]
        conn.close() [cite: 1]
        if user:
            session['user'] = u [cite: 1]
            return redirect(url_for('home')) [cite: 1]
    return render_template('login.html') [cite: 1]

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password') [cite: 1]
        conn = get_db_connection() [cite: 1]
        cur = conn.cursor() [cite: 1]
        try:
            cur.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (u, p)) [cite: 1]
            conn.commit() [cite: 1]
            session['user'] = u [cite: 1]
            return redirect(url_for('home')) [cite: 1]
        except:
            return "Этот ник уже занят!" [cite: 1]
        finally:
            cur.close() [cite: 1]
            conn.close() [cite: 1]
    return render_template('register.html') [cite: 1]

@app.route('/add/<game_key>', methods=['POST'])
def add_item(game_key):
    if 'user' not in session: return redirect(url_for('login')) [cite: 1]
    name = f"{request.form.get('item_type')}: {request.form.get('custom_info')}" [cite: 1]
    price = f"{request.form.get('price')} {GAMES_CONFIG[game_key]['currency']}" [cite: 1]
    img = request.form.get('img') or "https://via.placeholder.com/200/222/fff?text=Gkz4" [cite: 1]
    
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor() [cite: 1]
    cur.execute('INSERT INTO products (category, name, price, img, owner) VALUES (%s, %s, %s, %s, %s)',
                (game_key, name, price, img, session['user'])) [cite: 1]
    conn.commit() [cite: 1]
    cur.close() [cite: 1]
    conn.close() [cite: 1]
    return redirect(url_for('category', game_key=game_key)) [cite: 1]

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session: return redirect(url_for('login')) [cite: 1]
    conn = get_db_connection() [cite: 1]
    cur = conn.cursor() [cite: 1]
    cur.execute('DELETE FROM products WHERE id = %s AND owner = %s', (item_id, session['user'])) [cite: 1]
    conn.commit() [cite: 1]
    cur.close() [cite: 1]
    conn.close() [cite: 1]
    return redirect(request.referrer or url_for('home')) [cite: 1]

@app.route('/logout')
def logout(): 
    session.pop('user', None) [cite: 1]
    return redirect(url_for('home')) [cite: 1]

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) [cite: 1]
    app.run(host='0.0.0.0', port=port) [cite: 1]