from flask import Flask, render_template_string, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import datetime, pytz, os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey123'          # ← заміни для безпеки
KYIV_TZ = pytz.timezone('Europe/Kiev')

# ---------- Початкові матчі ----------
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

# ---------- Користувачі ----------
users = {
    'Pau4ok': {'password_hash': generate_password_hash('Paukov1405'), 'bets': {}}
}

# ---------- Допоміжні ----------
def get_next_match_id():
    return max((m['id'] for m in matches), default=0) + 1

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
    return dict(sorted(board.items(), key=lambda x: x[1]['points'], reverse=True))

def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if session.get('user') != 'Pau4ok':
            return "Доступ заборонено", 403
        return f(*a, **kw)
    return wrapper

# ---------- HTML шаблон ----------
PAGE_TEMPLATE = '''
<!DOCTYPE html><html lang="uk"><head><meta charset="UTF-8"/>
<title>Ставки на матчі</title>
<style>
 body{margin:0;padding:0;font-family:Arial,sans-serif;
      background:url("https://content.rozetka.com.ua/goods/images/big/27254638.jpg") no-repeat center fixed;
      background-size:cover;color:#222;overflow-x:hidden;}
 /* симетричні краї + обмеження ширини */
 .container{display:flex;max-width:1600px;margin:0 auto;width:100%;
            height:100vh;padding:10px;box-sizing:border-box;}
 .block{position:relative;background:rgba(255,255,255,.6);margin:5px;padding:10px;border-radius:8px;
        overflow-y:auto;flex-shrink:0;display:flex;flex-direction:column;}
 .left{width:38%}.center{width:42%}.right{width:18%}
 .block::before{content:"";background:url("https://footking.mobi/union/logo/big3.jpg?r=222") no-repeat center;
                background-size:contain;opacity:.15;position:absolute;top:50%;left:50%;
                transform:translate(-50%,-50%);width:60%;height:60%;pointer-events:none;z-index:0;}
 .block>*{position:relative;z-index:1;}
 table{width:100%;border-collapse:collapse;font-size:14px;max-width:100%;}
 th,td{padding:6px;border:1px solid #aaa;text-align:center;}
 .champ-col{text-align:center;white-space:normal;word-wrap:break-word;}
 .btn{padding:5px 8px;margin:2px;border:none;border-radius:4px;cursor:pointer;color:#fff;background:#337ab7;font-size:12px}
 .btn-danger{background:#d9534f}.btn-success{background:#5cb85c}
 a{color:#337ab7;text-decoration:none;}a:hover{text-decoration:underline;}
 .status-live{background:#5cb85c;color:#fff;font-weight:bold;padding:3px 6px;border-radius:4px;}
 .status-finished{background:#d9534f;color:#fff;font-weight:bold;padding:3px 6px;border-radius:4px;}
</style></head><body>
<div class="container">

<!-- Лівий блок -->
<div class="left block"><h2>Матчі в процесі / завершені</h2>
<form method="post" action="{{ url_for('reset_leaderboard') }}">
{% if is_admin %}
<button class="btn btn-danger" type="submit">Оновити результати</button>
{% endif %}
</form>
<table>
 <tr><th>Тур</th><th class="champ-col">Чемпіонат</th><th>Команди</th><th>Час</th><th>Рахунок</th><th>Результат</th><th>Статус</th>{% if is_admin %}<th>Дії</th>{% endif %}</tr>
 {% for m in left_matches %}
 <tr>
  <td>{{m.round}}</td>
  <td class="champ-col">{{m.championship.replace(' ','<br>')|safe}}</td>
  <td><a href="{{m.link_team1}}" target="_blank">{{m.team1}}</a> - <a href="{{m.link_team2}}" target="_blank">{{m.team2}}</a></td>
  <td>{{m.start_time_local}}</td>
  <td>{{m.score or '-'}}</td>
  <td>
    {% if m.status=='live' and not m.result %}
      LIVE
    {% else %}
      {% if   m.result=='P1' %}П1
      {% elif m.result=='X'  %}Х
      {% elif m.result=='P2' %}П2
      {% else %}---{% endif %}
    {% endif %}
  </td>
  <td>{% if m.status=='live' %}<span class="status-live">LIVE</span>{% else %}<span class="status-finished">Завершено</span>{% endif %}</td>
  {% if is_admin %}
  <td>
    <form style="display:inline" method="post" action="{{url_for('admin_toggle_status',match_id=m.id)}}">
      <button class="btn {% if m.status=='live' %}btn-danger{% else %}btn-success{% endif %}">
        {% if m.status=='live' %}Завершити{% else %}LIVE{% endif %}
      </button>
    </form>
    <form style="display:inline" method="post" action="{{url_for('admin_update_score',match_id=m.id)}}">
      <input name="score" value="{{m.score}}" size="5">
      <select name="result">
        <option value=""  {% if not m.result %}selected{% endif %}>---</option>
        <option value="P1" {% if m.result=='P1' %}selected{% endif %}>П1</option>
        <option value="X"  {% if m.result=='X'  %}selected{% endif %}>Х</option>
        <option value="P2" {% if m.result=='P2' %}selected{% endif %}>П2</option>
      </select>
      <button class="btn btn-success" type="submit">Оновити</button>
    </form>
    <form style="display:inline" method="post" action="{{url_for('admin_delete_match',match_id=m.id)}}">
      <button class="btn btn-danger" type="submit" onclick="return confirm('Видалити цей матч?')">Видалити</button>
    </form>
  </td>
  {% endif %}
 </tr>
 {% endfor %}
</table>

<hr>

<h2>Зареєстровані гравці</h2>
<table>
  <tr><th>Нік</th><th>Перемоги</th><th>Поразки</th><th>Очки</th>{% if is_admin %}<th>Дії</th>{% endif %}</tr>
  {% for u, s in leaderboard.items() %}
  <tr>
    <td>{{u}}</td>
    <td>{{s.wins}}</td>
    <td>{{s.losses}}</td>
    <td>{{s.points}}</td>
    {% if is_admin %}
    <td>
      <form style="display:inline" method="post" action="{{ url_for('admin_delete_user', username=u) }}">
        {% if u != 'Pau4ok' %}
        <button class="btn btn-danger" type="submit" onclick="return confirm('Видалити користувача {{u}}?')">Видалити</button>
        {% endif %}
      </form>
    </td>
    {% endif %}
  </tr>
  {% endfor %}
</table>
</div>

<!-- Центр -->
<div class="center block">
<h2>Вхід / Реєстрація</h2>
{% if error %}
<p style="color:red">{{error}}</p>
{% endif %}
{% if not user %}
<form method="post" action="{{ url_for('login') }}">
  <label>Нік:<br><input name="username" required></label><br>
  <label>Пароль:<br><input type="password" name="password" required></label><br>
  <button class="btn btn-success" type="submit">Увійти</button>
</form>
<hr>
<form method="post" action="{{ url_for('register') }}">
  <label>Нік:<br><input name="username" required></label><br>
  <label>Пароль:<br><input type="password" name="password" required></label><br>
  <button class="btn btn-primary" type="submit">Зареєструватися</button>
</form>
{% else %}
<p>Привіт, <b>{{user}}</b>! <a href="{{ url_for('logout') }}">Вийти</a></p>
{% endif %}
</div>

<!-- Правий блок -->
<div class="right block">
<h2>Таблиця лідерів</h2>
<table>
<tr><th>Нік</th><th>Перемоги</th><th>Поразки</th><th>Очки</th></tr>
{% for u, s in leaderboard.items() %}
<tr>
  <td>{{u}}</td><td>{{s.wins}}</td><td>{{s.losses}}</td><td>{{s.points}}</td>
</tr>
{% endfor %}
</table>
</div>

</div></body></html>
'''

# --------- Маршрути ---------

@app.route('/')
def index():
    user = session.get('user')
    is_admin = (user == 'Pau4ok')

    # Форматування часу для показу
    left_matches = []
    for m in matches:
        dt_local = m['start_time'].astimezone(KYIV_TZ)
        m_copy = m.copy()
        m_copy['start_time_local'] = dt_local.strftime('%d.%m %H:%M')
        left_matches.append(m_copy)

    leaderboard = calculate_leaderboard()

    error = session.pop('error', None)

    return render_template_string(PAGE_TEMPLATE,
                                  left_matches=left_matches,
                                  leaderboard=leaderboard,
                                  user=user,
                                  is_admin=is_admin,
                                  error=error)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username not in users or not check_password_hash(users[username]['password_hash'], password):
        session['error'] = "Нік або пароль мають помилку"
        return redirect(url_for('index'))

    session['user'] = username
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if username in users:
        session['error'] = "Зайнято"
        return redirect(url_for('index'))

    users[username] = {'password_hash': generate_password_hash(password), 'bets': {}}
    session['user'] = username
    return redirect(url_for('index'))

@app.route('/reset_leaderboard', methods=['POST'])
@admin_required
def reset_leaderboard():
    for user in users:
        users[user]['bets'] = {}
    return redirect(url_for('index'))

@app.route('/admin/delete_user/<username>', methods=['POST'])
@admin_required
def admin_delete_user(username):
    if username in users and username != 'Pau4ok':
        users.pop(username)
    return redirect(url_for('index'))

@app.route('/admin/toggle_status/<int:match_id>', methods=['POST'])
@admin_required
def admin_toggle_status(match_id):
    match = next((m for m in matches if m['id'] == match_id), None)
    if match:
        if match['status'] == 'live':
            match['status'] = 'finished'
        else:
            match['status'] = 'live'
    return redirect(url_for('index'))

@app.route('/admin/update_score/<int:match_id>', methods=['POST'])
@admin_required
def admin_update_score(match_id):
    match = next((m for m in matches if m['id'] == match_id), None)
    if match:
        match['score'] = request.form.get('score', '')
        match['result'] = request.form.get('result', '')
        # Якщо результат оновлено і статус не finished - автоматично ставимо finished
        if match['result'] and match['status'] != 'finished':
            match['status'] = 'finished'
    return redirect(url_for('index'))

@app.route('/admin/delete_match/<int:match_id>', methods=['POST'])
@admin_required
def admin_delete_match(match_id):
    global matches
    matches = [m for m in matches if m['id'] != match_id]
    return redirect(url_for('index'))

# --------- Запуск ---------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
