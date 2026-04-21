import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'gkz4_ultra_auto_chat'

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Добавлена колонка balance в таблицу users
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

# Контекстный процессор теперь передает и баланс пользователя
@app.context_processor
def inject_user_data():
    data = {'unread_count': 0, 'user_balance': 0}
    if 'user' in session:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Получаем количество сообщений
            cur.execute('SELECT COUNT(*) FROM chats WHERE recipient = %s AND is_read = FALSE', (session['user'],))
            data['unread_count'] = cur.fetchone()[0]
            # Получаем текущий баланс
            cur.execute('SELECT balance FROM users WHERE username = %s', (session['user'],))
            res = cur.fetchone()
            if res: data['user_balance'] = res[0]
            cur.close()
            conn.close()
        except: pass
    return data

GAMES_CONFIG = {
    "slap": {"name": "Slap Battles", "icon": "🖐️", "currency": "R$", "options": ["Перчатка", "Бейдж", "Фарм"], "hint": "Название перчатки"},
    "bloxfruits": {"name": "Blox Fruits", "icon": "🍎", "currency": "Бели", "options": ["Фрукт", "Меч", "Прокачка"], "hint": "LVL"},
    "robux": {"name": "Робуксы", "icon": "🪙", "currency": "руб.", "options": ["Трансфер (1к3)", "Курс 1к2"], "hint": "Сколько R$?"}
}

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

# Страница пополнения баланса
@app.route('/pay', methods=['GET', 'POST'])
def pay():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        amount = int(request.form.get('amount', 0))
        if amount > 0:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE users SET balance = balance + %s WHERE username = %s', (amount, session['user']))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('home'))
    return render_template('pay.html')

# Функция покупки товара
@app.route('/buy/<int:item_id>')
def buy_item(item_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Ищем товар
    cur.execute('SELECT * FROM products WHERE id = %s', (item_id,))
    product = cur.fetchone()
    
    if not product:
        cur.close()
        conn.close()
        return "Товар не найден"

    # Извлекаем цену (убираем текст, оставляем только цифры)
    try:
        price = int(''.join(filter(str.isdigit, product['price'])))
    except: price = 0

    # Проверяем баланс покупателя
    cur.execute('SELECT balance FROM users WHERE username = %s', (session['user'],))
    buyer_balance = cur.fetchone()['balance']

    if buyer_balance >= price:
        # 1. Снимаем деньги у покупателя
        cur.execute('UPDATE users SET balance = balance - %s WHERE username = %s', (price, session['user']))
        # 2. Начисляем деньги продавцу
        cur.execute('UPDATE users SET balance = balance + %s WHERE username = %s', (price, product['owner']))
        # 3. Отправляем авто-сообщение продавцу
        msg_time = datetime.now().strftime("%H:%M")
        msg_text = f"🤖 СИСТЕМА: Пользователь {session['user']} купил ваш товар '{product['name']}' за {price} руб. Свяжитесь для передачи!"
        cur.execute('INSERT INTO chats (sender, recipient, message, time, is_read) VALUES (%s, %s, %s, %s, FALSE)', 
                    ('SYSTEM', product['owner'], msg_text, msg_time))
        
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('chat', recipient=product['owner']))
    else:
        cur.close()
        conn.close()
        return "Недостаточно средств! Пополните баланс."

# Остальные функции (сообщения, логин и т.д.)
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

@app.route('/chat/<recipient>')
def chat(recipient):
    if 'user' not in session: return redirect(url_for('login'))
    user = session['user']
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('UPDATE chats SET is_read = TRUE WHERE sender = %s AND recipient = %s', (recipient, user))
    conn.commit()
    cur.execute('SELECT * FROM chats WHERE (sender = %s AND recipient = %s) OR (sender = %s AND recipient = %s) ORDER BY id', (user, recipient, recipient, user))
    messages = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('chat.html', recipient=recipient, messages=messages, user=user)

@app.route('/send_message/<recipient>', methods=['POST'])
def send_message(recipient):
    if 'user' not in session: return jsonify({"status": "error"}), 403
    msg_text = request.form.get('text')
    msg_time = datetime.now().strftime("%H:%M")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO chats (sender, recipient, message, time, is_read) VALUES (%s, %s, %s, %s, FALSE)', (session['user'], recipient, msg_text, msg_time))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"sender": session['user'], "message": msg_text, "time": msg_time})

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

@app.route('/logout')
def logout(): 
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)