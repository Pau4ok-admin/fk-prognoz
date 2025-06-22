from flask import Flask, render_template_string, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import datetime, pytz
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # заміни на свій секретний ключ

KYIV_TZ = pytz.timezone('Europe/Kiev')

# Початкові матчі
matches = [
    {
        'id': 1,
        'round': 1,
        'championship': 'Чемпіонат України',
        'team1': 'Таврія',
        'team2': 'Шахтар',
        'link_team1': 'https://example.com/tavria',
        'link_team2': 'https://example.com/shakhtar',
        'start_time': KYIV_TZ.localize(datetime.datetime(2025, 6, 20, 15, 0)),
        'status': 'finished',
        'score': '2-0',
        'result': 'P1'
    },
    {
        'id': 2,
        'round': 2,
        'championship': 'Англійська Прем’єр-ліга',
        'team1': 'Ман Сіті',
        'team2': 'Ліверпуль',
        'link_team1': 'https://example.com/mancity',
        'link_team2': 'https://example.com/liverpool',
        'start_time': KYIV_TZ.localize(datetime.datetime(2025, 6, 26, 0, 0)),
        'status': 'live',
        'score': '2-2',
        'result': ''
    },
    {
        'id': 3,
        'round': 3,
        'championship': 'Ліга Чемпіонів',
        'team1': 'Реал',
        'team2': 'Барселона',
        'link_team1': 'https://example.com/real',
        'link_team2': 'https://example.com/barcelona',
        'start_time': KYIV_TZ.localize(datetime.datetime(2025, 6, 28, 18, 0)),
        'status': 'upcoming',
        'score': '',
        'result': ''
    },
]

# Користувачі
users = {
    'admin': {
        'password_hash': generate_password_hash('admin'),
        'bets': {}
    }
}

def current_kyiv_time():
    return datetime.datetime.now(KYIV_TZ)

def calculate_leaderboard():
    board = {}
    for user, data in users.items():
        wins = losses = points = 0
        for m in matches:
            if m['status'] != 'finished':
                continue
            bet = data['bets'].get(m['id'])
            if not bet:
                continue
            if bet == m['result']:
                wins += 1
                points += 3
            else:
                losses += 1
                points -= 1
        board[user] = {'wins': wins, 'losses': losses, 'points': points}
    # Сортуємо за очками
    return dict(sorted(board.items(), key=lambda x: x[1]['points'], reverse=True))

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('user') != 'admin':
            return "Доступ заборонено", 403
        return f(*args, **kwargs)
    return wrapper

PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8" />
    <title>ФК Прогнози</title>
    <style>
    body { font-family: Arial, sans-serif; background: #111; color: #ddd; margin: 0; padding: 20px; }
    a { color: #55f; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .match { border: 1px solid #333; padding: 10px; margin-bottom: 10px; }
    .finished { background: #222; }
    .live { background: #300; }
    .upcoming { background: #033; }
    .bets { margin-top: 10px; }
    form { margin-top: 5px; }
    input[type=submit] { background: #555; color: white; border: none; padding: 5px 10px; cursor: pointer; }
    input[type=submit]:hover { background: #77f; }
    .leaderboard { margin-top: 20px; }
    </style>
</head>
<body>
<h1>Прогнози на матчі</h1>

{% if is_logged_in %}
<p>Привіт, {{ current_user }}! <a href="{{ url_for('logout') }}">Вийти</a></p>
{% else %}
<p><a href="{{ url_for('login') }}">Увійти</a> або <a href="{{ url_for('register') }}">Зареєструватися</a></p>
{% endif %}

<h2>Матчі</h2>

{% for match in left_matches %}
<div class="match {{ match.status }}">
    <strong>{{ match.championship }} — Раунд {{ match.round }}</strong><br/>
    <a href="{{ match.link_team1 }}" target="_blank">{{ match.team1 }}</a> — 
    <a href="{{ match.link_team2 }}" target="_blank">{{ match.team2 }}</a><br/>
    Старт: {{ match.start_time_local }}<br/>
    Статус: {{ match.status }}<br/>
    Рахунок: {{ match.score }}<br/>
    {% if is_logged_in %}
    <div class="bets">
        <form method="post" action="{{ url_for('make_bet', match_id=match.id) }}">
            <label><input type="radio" name="bet" value="P1" {% if bets.get(match.id) == 'P1' %}checked{% endif %}/> {{ match.team1 }} виграє</label><br/>
            <label><input type="radio" name="bet" value="P2" {% if bets.get(match.id) == 'P2' %}checked{% endif %}/> {{ match.team2 }} виграє</label><br/>
            <label><input type="radio" name="bet" value="Draw" {% if bets.get(match.id) == 'Draw' %}checked{% endif %}/> Нічия</label><br/>
            <input type="submit" value="Поставити" />
        </form>
    </div>
    {% endif %}
</div>
{% endfor %}

<h2>Майбутні матчі</h2>

{% for match in center_matches %}
<div class="match upcoming">
    <strong>{{ match.championship }} — Раунд {{ match.round }}</strong><br/>
    <a href="{{ match.link_team1 }}" target="_blank">{{ match.team1 }}</a> — 
    <a href="{{ match.link_team2 }}" target="_blank">{{ match.team2 }}</a><br/>
    Старт: {{ match.start_time_local }}<br/>
    Статус: {{ match.status }}<br/>
</div>
{% endfor %}

<h2>Турнірна таблиця</h2>
<div class="leaderboard">
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; color:#ddd;">
        <thead>
            <tr>
                <th>Користувач</th>
                <th>Виграші</th>
                <th>Програші</th>
                <th>Очки</th>
            </tr>
        </thead>
        <tbody>
            {% for user, stats in leaderboard.items() %}
            <tr>
                <td>{{ user }}</td>
                <td>{{ stats.wins }}</td>
                <td>{{ stats.losses }}</td>
                <td>{{ stats.points }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

</body>
</html>
'''

# Головна сторінка
@app.route('/')
def index():
    now = current_kyiv_time()
    for m in matches:
        if m['status'] == 'upcoming' and m['start_time'] <= now:
            m['status'] = 'live'
        m['start_time_local'] = m['start_time'].strftime('%H:%M %d.%m.%Y')

    left  = [m for m in matches if m['status'] in ('live', 'finished')]
    center= [m for m in matches if m['status'] == 'upcoming']

    user = session.get('user')
    bets = users[user]['bets'] if user in users else {}

    return render_template_string(
        PAGE_TEMPLATE,
        left_matches=left,
        center_matches=center,
        bets=bets,
        leaderboard=calculate_leaderboard(),
        is_logged_in=(user in users),
        current_user=user,
        is_admin=(user == 'admin')
    )

# Реєстрація
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users:
            return "Користувач вже існує!"
        users[username] = {
            'password_hash': generate_password_hash(password),
            'bets': {}
        }
        session['user'] = username
        return redirect(url_for('index'))
    return '''
    <form method="post">
      Користувач: <input name="username"/><br/>
      Пароль: <input type="password" name="password"/><br/>
      <input type="submit" value="Зареєструватись"/>
    </form>
    '''

# Логін
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users.get(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = username
            return redirect(url_for('index'))
        return "Невірний логін або пароль"
    return '''
    <form method="post">
      Користувач: <input name="username"/><br/>
      Пароль: <input type="password" name="password"/><br/>
      <input type="submit" value="Увійти"/>
    </form>
    '''

# Вихід
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# Робота зі ставками
@app.route('/bet/<int:match_id>', methods=['POST'])
def make_bet(match_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    bet = request.form.get('bet')
    if bet not in ['P1', 'P2', 'Draw']:
        return "Невірна ставка!"
    users[user]['bets'][match_id] = bet
    return redirect(url_for('index'))

# Адмін: додати матч (приклад)
@app.route('/admin/add_match', methods=['GET', 'POST'])
@admin_required
def add_match():
    if request.method == 'POST':
        try:
            new_id = max(m['id'] for m in matches) + 1
        except ValueError:
            new_id = 1
        matches.append({
            'id': new_id,
            'round': int(request.form['round']),
            'championship': request.form['championship'],
            'team1': request.form['team1'],
            'team2': request.form['team2'],
            'link_team1': request.form['link_team1'],
            'link_team2': request.form['link_team2'],
            'start_time': KYIV_TZ.localize(datetime.datetime.strptime(request.form['start_time'], '%Y-%m-%d %H:%M')),
            'status': 'upcoming',
            'score': '',
            'result': ''
        })
        return redirect(url_for('index'))
    return '''
    <form method="post">
      Раунд: <input name="round" type="number"/><br/>
      Чемпіонат: <input name="championship"/><br/>
      Команда 1: <input name="team1"/><br/>
      Команда 2: <input name="team2"/><br/>
      Посилання на команду 1: <input name="link_team1"/><br/>
      Посилання на команду 2: <input name="link_team2"/><br/>
      Дата і час старту (YYYY-MM-DD HH:MM): <input name="start_time"/><br/>
      <input type="submit" value="Додати матч"/>
    </form>
    '''

# Запуск сервера (для Render)
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
