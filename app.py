import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'gkz4_ultra_auto_chat'

# Ссылка на базу из настроек Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Создаем таблицы (добавлены balance и is_read)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            balance INTEGER DEFAULT 0
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
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ТВОИ ПЛЕЙСЫ (ПОЛНЫЙ СПИСОК)
GAMES_CONFIG = {
    "slap": {"name": "Slap Battles", "icon": "🖐️", "currency": "Слепы / R$", "options": ["Перчатка", "Бейдж", "Фарм"], "hint": "Название перчатки"},
    "bloxfruits": {"name": "Blox Fruits", "icon": "🍎", "currency": "Бели / R$", "options": ["Фрукт", "Меч", "Прокачка"], "hint": "LVL"},
    "99nights": {"name": "99 Ночей", "icon": "🌙", "currency": "Гемы", "options": ["Прожить дни", "Геймпас"], "hint": "Кол-во дней"},
    "garden": {"name": "Вырасти Сад", "icon": "🌱", "currency": "Шейкели", "options": ["Редкое семя", "Аккаунт"], "hint": "Растение"},
    "adopt": {"name": "Adopt Me!", "icon": "🐶", "currency": "Петы", "options": ["Неон пет", "Мега-неон"], "hint": "Какой пет?"},
    "ttd": {"name": "Toilet Tower Defense", "icon": "🚽", "currency": "Гемы", "options": ["Юнит", "Мифик"], "hint": "Имя юнита"},
    "ps99": {"name": "Pet Sim 99", "icon": "🐱", "currency": "Гемы", "options": ["Huge Пет", "Титаник"], "hint": "Имя пета"},
    "robux": {"name": "Робуксы", "icon": "🪙", "currency": "руб.", "options": ["Трансфер (1к3)", "Курс 1к2"], "hint": "Сколько R$?"}
}

# Чтобы баланс и уведомления были видны на всех страницах
@app.context_processor
def inject_user_data():
    if 'user' in session:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT balance FROM users WHERE username = %s', (session['user'],))
        res = cur.fetchone()
        cur.execute('SELECT COUNT(*) FROM chats WHERE recipient = %s AND is_read = FALSE', (session['user'],))
        unread = cur.fetchone()['count']
        cur.close()
        conn.close()
        return {'user_balance': res['balance'] if res else 0, 'unread_count': unread}
    return {'user_balance': 0, 'unread_count': 0}

@app.route('/')
def home():
    return render_template('index.html', games=GAMES_CONFIG, user=session.get('user'))

@app.route('/category/<game_key>')
def category(game_key):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products WHERE category = %s', (game_key,))
    items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('category.html', game=GAMES_CONFIG.get(game_key), game_key=game_key, items=items, user=session.get('user'))

@app.route('/chat/<recipient>')
def chat(recipient):
    if 'user' not in session: return redirect(url_for('login'))
    user = session['user']
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Помечаем сообщения как прочитанные, когда заходим в чат
    cur.execute('UPDATE chats SET is_read = TRUE WHERE sender = %s AND recipient = %s', (recipient, user))
    cur.execute('SELECT * FROM chats WHERE (sender = %s AND recipient = %s) OR (sender = %s AND recipient = %s) ORDER BY id', 
                (user, recipient, recipient, user))
    messages = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('chat.html', recipient=recipient, messages=messages, user=user)

@app.route('/get_unread_count')
def get_unread_count():
    if 'user' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM chats WHERE recipient = %s AND is_read = FALSE', (session['user'],))
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({"unread_count": count})
    return jsonify({"unread_count": 0})

@app.route('/send_message/<recipient>', methods=['POST'])
def send_message(recipient):
    if 'user' not in session: return jsonify({"status": "error"}), 403
    msg_text = request.form.get('text')
    msg_time = datetime.now().strftime("%H:%M")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO chats (sender, recipient, message, time) VALUES (%s, %s, %s, %s)',
                (session['user'], recipient, msg_text, msg_time))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"from": session['user'], "text": msg_text, "time": msg_time})

@app.route('/add/<game_key>', methods=['POST'])
def add_item(game_key):
    if 'user' not in session: return redirect(url_for('login'))
    name = f"{request.form.get('item_type')}: {request.form.get('custom_info')}"
    price = f"{request.form.get('price')} {GAMES_CONFIG[game_key]['currency']}"
    img = request.form.get('img') or "https://via.placeholder.com/200/222/fff?text=Gkz4"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO products (category, name, price, img, owner) VALUES (%s, %s, %s, %s, %s)',
                (game_key, name, price, img, session['user']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('category', game_key=game_key))

@app.route('/my_chats')
def my_chats():
    if 'user' not in session: return redirect(url_for('login'))
    user = session['user']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT sender FROM chats WHERE recipient = %s UNION SELECT DISTINCT recipient FROM chats WHERE sender = %s', (user, user))
    interlocutors = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('my_chats.html', interlocutors=interlocutors, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (u, p))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session['user'] = u
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (u, p))
            conn.commit()
            session['user'] = u
            return redirect(url_for('home'))
        except: return "Этот ник уже занят!"
        finally:
            cur.close()
            conn.close()
    return render_template('register.html')

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM products WHERE id = %s AND owner = %s', (item_id, session['user']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(request.referrer or url_for('home'))

@app.route('/logout')
def logout(): 
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)