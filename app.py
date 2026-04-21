import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'gkz4_ultra_auto_chat'

# ОБНОВЛЕННАЯ КОНФИГУРАЦИЯ ИГР (Все разделы, о которых ты просил)
GAMES_CONFIG = {
    "slap": {
        "name": "Slap Battles", "icon": "🖐️", "currency": "Слепы / R$", 
        "options": ["Перчатка", "Бейдж", "Фарм"], "hint": "Название перчатки"
    },
    "bloxfruits": {
        "name": "Blox Fruits", "icon": "🍎", "currency": "Бели / R$", 
        "options": ["Фрукт", "Меч", "Прокачка"], "hint": "Название фрукта или LVL"
    },
    "99nights": {
        "name": "99 Ночей", "icon": "🌙", "currency": "Гемы", 
        "options": ["Прожить дни", "Геймпас", "Предметы"], "hint": "Кол-во дней или предмет"
    },
    "garden": {
        "name": "Вырасти Сад", "icon": "🌱", "currency": "Шейкели", 
        "options": ["Редкое семя", "Удобрение", "Аккаунт"], "hint": "Что за растение?"
    },
    "adopt": {
        "name": "Adopt Me!", "icon": "🐶", "currency": "Петы", 
        "options": ["Неон пет", "Мега-неон", "Яйцо"], "hint": "Какой пет?"
    },
    "ttd": {
        "name": "Toilet Tower Defense", "icon": "🚽", "currency": "Гемы", 
        "options": ["Юнит", "Мифик", "Годли"], "hint": "Имя юнита"
    },
    "ps99": {
        "name": "Pet Sim 99", "icon": "🐱", "currency": "Гемы", 
        "options": ["Huge Пет", "Титаник", "Алмазы"], "hint": "Имя пета или сумма"
    },
    "robux": {
        "name": "Робуксы", "icon": "🪙", "currency": "руб.", 
        "options": ["Трансфер (1к3)", "Курс 1к2"], "hint": "Сколько R$?"
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'database.json')

def load_db():
    if not os.path.exists(DB_FILE):
        save_db({"users": {}, "products": [], "chats": []})
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"users": {}, "products": [], "chats": []}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def home():
    return render_template('index.html', games=GAMES_CONFIG, user=session.get('user'))

@app.route('/category/<game_key>')
def category(game_key):
    db = load_db()
    conf = GAMES_CONFIG.get(game_key)
    if not conf:
        return redirect(url_for('home'))
    items = [p for p in db['products'] if p.get('category') == game_key]
    return render_template('category.html', game=conf, game_key=game_key, items=items, user=session.get('user'))

@app.route('/add/<game_key>', methods=['POST'])
def add_item(game_key):
    if 'user' not in session: return redirect(url_for('login'))
    db = load_db()
    db['products'].append({
        "id": len(db['products']) + 1, "category": game_key,
        "name": f"{request.form.get('item_type')}: {request.form.get('custom_info')}",
        "price": f"{request.form.get('price')} {GAMES_CONFIG[game_key]['currency']}",
        "img": request.form.get('img') or "https://via.placeholder.com/200/222/fff?text=Gkz4+Market",
        "owner": session['user']
    })
    save_db(db)
    return redirect(url_for('category', game_key=game_key))

@app.route('/my_chats')
def my_chats():
    if 'user' not in session: return redirect(url_for('login'))
    db = load_db(); user = session['user']; interlocutors = set()
    for m in db.get('chats', []):
        if m['from'] == user: interlocutors.add(m['to'])
        if m['to'] == user: interlocutors.add(m['from'])
    return render_template('my_chats.html', interlocutors=list(interlocutors), user=user)

@app.route('/chat/<recipient>')
def chat(recipient):
    if 'user' not in session: return redirect(url_for('login'))
    db = load_db(); user = session['user']
    messages = [m for m in db.get('chats', []) if (m['from'] == user and m['to'] == recipient) or (m['from'] == recipient and m['to'] == user)]
    return render_template('chat.html', recipient=recipient, messages=messages, user=user)

@app.route('/send_message/<recipient>', methods=['POST'])
def send_message(recipient):
    if 'user' not in session: return jsonify({"status": "error"}), 403
    db = load_db()
    msg_data = {
        "from": session['user'], 
        "to": recipient, 
        "text": request.form.get('text'), 
        "time": datetime.now().strftime("%H:%M")
    }
    db['chats'].append(msg_data)
    save_db(db)
    return jsonify(msg_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = load_db(); u, p = request.form.get('username'), request.form.get('password')
        if db['users'].get(u) == p: 
            session['user'] = u
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = load_db(); u, p = request.form.get('username'), request.form.get('password')
        if u and u not in db['users']: 
            db['users'][u] = p
            save_db(db)
            session['user'] = u
            return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/logout')
def logout(): 
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session: return redirect(url_for('login'))
    db = load_db()
    db['products'] = [p for p in db['products'] if not (p.get('id') == item_id and p.get('owner') == session['user'])]
    save_db(db)
    return redirect(request.referrer or url_for('home'))

# ЗАПУСК (С ПОДДЕРЖКОЙ ПОРТА ДЛЯ RENDER)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)