from flask import Flask, render_template_string, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import datetime, pytz
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # ← для безпеки заміни на свій

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
    'pau4ok': {'password_hash': generate_password_hash('Paukov1405'), 'bets': {}}
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
        if session.get('user') != 'pau4ok':
            return "Доступ заборонено", 403
        return f(*a, **kw)
    return wrapper

# ---------- HTML шаблон ----------
PAGE_TEMPLATE = '''
<!DOCTYPE html><html lang="uk"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1">
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
 
 /* Адаптивність */
 @media (max-width: 768px) {
   .container {
     flex-direction: column;
     height: auto;
   }
   .left, .center, .right {
     width: 100% !important;
     margin-bottom: 10px;
   }
 }
</style></head><body>
<div class="container">

<!-- Лівий блок -->
<div class="left block"><h2>Матчі в процесі / завершені</h2>

{% if is_admin %}
<form method="post" action="{{ url_for('admin_reset_results') }}">
  <button class="btn btn-danger" style="margin-bottom:10px;">Оновити результати</button>
</form>
<form method="post" action="{{ url_for('admin_delete_user') }}">
  <label>Видалити користувача (крім себе):</label>
  <select name="del_user" required>
    {% for u in users %}
      {% if u != current_user %}
        <option value="{{u}}">{{u}}</option>
      {% endif %}
    {% endfor %}
  </select>
  <button class="btn btn-danger">Видалити</button>
</form>
{% endif %}

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
      <button class="btn">OK</button>
    </form>
    <form style="display:inline" method="post" action="{{url_for('admin_delete_match',match_id=m.id)}}">
      <button class="btn btn-danger">DEL</button>
    </form>
  </td>
  {% endif %}
 </tr>
 {% endfor %}
</table>
</div>

<!-- Центральний блок -->
<div class="center block"><h2>Матчі для ставок</h2>
{% if not is_logged_in %}
  <p><a href="{{url_for('login')}}">Увійти</a> або <a href="{{url_for('register')}}">зареєструватися</a>.</p>
{% else %}
  <p>Привіт, {{current_user}}! <a href="{{url_for('logout')}}">Вийти</a></p>
  <form method="post" action="{{url_for('make_bets')}}">
  <table>
   <tr><th>Тур</th><th class="champ-col">Чемпіонат</th><th>Команди</th><th>Час</th><th>Ставка</th><th>Дії</th></tr>
   {% for m in center_matches %}
   <tr>
    <td>{{m.round}}</td>
    <td class="champ-col">{{m.championship.replace(' ','<br>')|safe}}</td>
    <td><a href="{{m.link_team1}}" target="_blank">{{m.team1}}</a> - <a href="{{m.link_team2}}" target="_blank">{{m.team2}}</a></td>
    <td>{{m.start_time_local}}</td>
    <td>
      <label><input type="radio" name="bet_{{m.id}}" value="P1" {% if bets.get(m.id)=='P1' %}checked{% endif %}> П1</label>
      <label><input type="radio" name="bet_{{m.id}}" value="X"  {% if bets.get(m.id)=='X'  %}checked{% endif %}> Х</label>
      <label><input type="radio" name="bet_{{m.id}}" value="P2" {% if bets.get(m.id)=='P2' %}checked{% endif %}> П2</label>
      <label><input type="radio" name="bet_{{m.id}}" value=""   {% if bets.get(m.id) is none %}checked{% endif %}> —</label>
    </td>
    <td>
      {% if is_admin %}
        <a href="{{url_for('admin_edit_match',match_id=m.id)}}">Редагувати</a> |
        <form style="display:inline" method="post" action="{{url_for('admin_delete_match',match_id=m.id)}}">
          <button class="btn btn-danger">DEL</button>
        </form>
      {% else %}—{% endif %}
    </td>
   </tr>
   {% endfor %}
  </table>
  <button class="btn">Зберегти ставки</button>
  </form>
{% endif %}
{% if is_admin %}
 <hr><h3>Додати матч</h3>
 <form method="post" action="{{url_for('admin_add_match')}}">
   Тур:<input type="number" name="round" required><br/>
   Чемпіонат:<input type="text" name="championship" required><br/>
   Команда 1:<input type="text" name="team1" required><br/>
   URL 1:<input type="url" name="link_team1" placeholder="https://..." required><br/>
   Команда 2:<input type="text" name="team2" required><br/>
   URL 2:<input type="url" name="link_team2" placeholder="https://..." required><br/>
   Час (Київ):<input type="datetime-local" name="start_time" required><br/>
   <button class="btn btn-success">Додати</button>
 </form>
{% endif %}
</div>

<!-- Правий блок -->
<div class="right block"><h2>Таблиця лідерів</h2>
<table>
 <tr><th>Нік</th><th>W</th><th>L</th><th>Pts</th></tr>
 {% for u,s in leaderboard.items() %}
   <tr><td>{{u}}</td><td>{{s.wins}}</td><td>{{s.losses}}</td><td>{{s.points}}</td></tr>
 {% endfor %}
</table>
</div>

</div>
</body></html>
'''

# ----------- Маршрути ------------

@app.route('/')
def index():
    is_logged_in = 'user' in session
    current_user = session.get('user')
    is_admin = (current_user == 'pau4ok')
    
    # Ліві матчі — всі окрім тих, що "upcoming"
    left_matches = [m.copy() for m in matches if m['status'] in ['live', 'finished']]
    for m in left_matches:
        m['start_time_local'] = m['start_time'].astimezone(KYIV_TZ).strftime('%d.%m %H:%M')
    
    # Центральні матчі — для ставок, статус upcoming
    center_matches = [m.copy() for m in matches if m['status'] == 'upcoming']
    for m in center_matches:
        m['start_time_local'] = m['start_time'].astimezone(KYIV_TZ).strftime('%d.%m %H:%M')

    leaderboard = calculate_leaderboard()
    
    # Ставки користувача
    bets = users.get(current_user, {}).get('bets', {}) if is_logged_in else {}
    
    return render_template_string(PAGE_TEMPLATE,
                                  left_matches=left_matches,
                                  center_matches=center_matches,
                                  leaderboard=leaderboard,
                                  is_logged_in=is_logged_in,
                                  current_user=current_user,
                                  is_admin=is_admin,
                                  users=users,
                                  bets=bets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username'].lower()
        password = request.form['password']
        if user in users and check_password_hash(users[user]['password_hash'], password):
            session['user'] = user
            return redirect(url_for('index'))
        else:
            return "Невірний логін або пароль", 401
    return '''
    <h2>Вхід</h2>
    <form method="post">
        Нік: <input name="username"><br/>
        Пароль: <input type="password" name="password"><br/>
        <button>Увійти</button>
    </form>
    '''

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username'].lower()
        password = request.form['password']
        if user in users:
            return "Такий нік вже існує", 400
        users[user] = {'password_hash': generate_password_hash(password), 'bets': {}}
        session['user'] = user
        return redirect(url_for('index'))
    return '''
    <h2>Реєстрація</h2>
    <form method="post">
        Нік: <input name="username"><br/>
        Пароль: <input type="password" name="password"><br/>
        <button>Зареєструватися</button>
    </form>
    '''

@app.route('/make_bets', methods=['POST'])
def make_bets():
    if 'user' not in session:
        return "Не авторизовані", 403
    user = session['user']
    for m in matches:
        bet_val = request.form.get(f'bet_{m["id"]}')
        if bet_val in ['P1','X','P2','']:
            if bet_val == '':
                users[user]['bets'].pop(m['id'], None)
            else:
                users[user]['bets'][m['id']] = bet_val
    return redirect(url_for('index'))

# --- Адмінські дії ---

@app.route('/admin/reset_results', methods=['POST'])
@admin_required
def admin_reset_results():
    # Очистити ставки всіх користувачів
    for user_data in users.values():
        user_data['bets'] = {}
    # Скинути результати і статус матчів
    for m in matches:
        m['result'] = ''
        m['score'] = ''
        if m['status'] == 'finished':
            m['status'] = 'upcoming'
    return redirect(url_for('index'))

@app.route('/admin/delete_user', methods=['POST'])
@admin_required
def admin_delete_user():
    del_user = request.form.get('del_user')
    if del_user and del_user in users and del_user != 'pau4ok':
        users.pop(del_user)
    return redirect(url_for('index'))

@app.route('/admin/toggle_status/<int:match_id>', methods=['POST'])
@admin_required
def admin_toggle_status(match_id):
    m = next((x for x in matches if x['id'] == match_id), None)
    if m:
        if m['status'] == 'live':
            m['status'] = 'finished'
        elif m['status'] == 'finished':
            m['status'] = 'upcoming'
        elif m['status'] == 'upcoming':
            m['status'] = 'live'
    return redirect(url_for('index'))

@app.route('/admin/update_score/<int:match_id>', methods=['POST'])
@admin_required
def admin_update_score(match_id):
    m = next((x for x in matches if x['id'] == match_id), None)
    if m:
        m['score'] = request.form.get('score', '')
        m['result'] = request.form.get('result', '')
    return redirect(url_for('index'))

@app.route('/admin/delete_match/<int:match_id>', methods=['POST'])
@admin_required
def admin_delete_match(match_id):
    global matches
    matches = [m for m in matches if m['id'] != match_id]
    return redirect(url_for('index'))

@app.route('/admin/add_match', methods=['POST'])
@admin_required
def admin_add_match():
    try:
        new_id = get_next_match_id()
        round_num = int(request.form['round'])
        championship = request.form['championship']
        team1 = request.form['team1']
        link_team1 = request.form['link_team1']
        team2 = request.form['team2']
        link_team2 = request.form['link_team2']
        # datetime-local to datetime obj
        start_time_str = request.form['start_time']
        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
        start_time = KYIV_TZ.localize(start_time)
        
        matches.append({
            'id': new_id,
            'round': round_num,
            'championship': championship,
            'team1': team1,
            'link_team1': link_team1,
            'team2': team2,
            'link_team2': link_team2,
            'start_time': start_time,
            'status': 'upcoming',
            'score': '',
            'result': ''
        })
    except Exception as e:
        return f"Помилка: {e}", 400
    return redirect(url_for('index'))


import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

