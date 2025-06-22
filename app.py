from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import datetime, pytz
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # ← замени на свой, чтобы безопасно

KYIV_TZ = pytz.timezone('Europe/Kiev')

# ---------- Початкові матчі ----------
matches = [
    # ... как у тебя
]

# ---------- Користувачі ----------
users = {
    # Убедимся, что есть админ с ником pau4ok
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

# ---------- ROUTES ----------

@app.route('/')
def index():
    now = current_kyiv_time()
    for m in matches:
        if m['status'] == 'upcoming' and m['start_time'] <= now:
            m['status'] = 'live'
        m['start_time_local'] = m['start_time'].strftime('%H:%M %d.%m.%Y')

    left = [m for m in matches if m['status'] in ('live', 'finished')]
    center = [m for m in matches if m['status'] == 'upcoming']

    user = session.get('user')
    bets = users[user]['bets'] if user in users else {}
    leaderboard = calculate_leaderboard()

    return render_template_string(
        PAGE_TEMPLATE,
        left_matches=left,
        center_matches=center,
        bets=bets,
        leaderboard=leaderboard,
        is_logged_in=(user in users),
        current_user=user,
        is_admin=(user == 'pau4ok')
    )


@app.route('/make_bets', methods=['POST'])
def make_bets():
    if 'user' not in session:
        return redirect('/login')
    u = session['user']
    b = users[u]['bets']
    for m in matches:
        val = request.form.get(f'bet_{m["id"]}', '')
        if val in ('P1', 'X', 'P2'):
            b[m['id']] = val
        else:
            b.pop(m['id'], None)
    return redirect('/')


# --- Новый роут для сброса результатов ---

@app.route('/admin/reset_results', methods=['POST'])
@admin_required
def admin_reset_results():
    # Обнуляем W, L, Pts для всех игроков — то есть просто очищаем ставки, чтобы в таблице не было результатов
    for data in users.values():
        data['bets'].clear()
    return redirect('/')


# --- Новый роут для удаления пользователя (кроме админа) ---

@app.route('/admin/delete_user/<username>', methods=['POST'])
@admin_required
def admin_delete_user(username):
    username = username.lower()
    if username == 'pau4ok':
        return "Неможливо видалити адміна!", 400
    if username in users:
        users.pop(username)
    return redirect('/')


# ---------- AUTH ---------- (сделаем админом pau4ok, пароль Paukov1405)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nick = request.form['username'].strip().lower()
        pwd = request.form['password']
        if nick in users:
            return "Нік зайнятий"
        users[nick] = {'password_hash': generate_password_hash(pwd), 'bets': {}}
        session['user'] = nick
        return redirect('/')
    return '''<h2>Реєстрація</h2>
              <form method=post>
                Нік:<input name=username required><br>
                Пароль:<input type=password name=password required><br>
                <button>OK</button>
              </form>'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nick = request.form['username'].strip().lower()
        pwd = request.form['password']
        if nick in users and check_password_hash(users[nick]['password_hash'], pwd):
            session['user'] = nick
            return redirect('/')
        return "Невірний нік або пароль"
    return '''<h2>Вхід</h2>
              <form method=post>
                Нік:<input name=username required><br>
                Пароль:<input type=password name=password required><br>
                <button>OK</button>
              </form>'''


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# --- Твой остальной код (админ добавление матчей, редактирование, удаление, ...) остается без изменений ---

# ---------- HTML шаблон с изменениями ----------
PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8"/>
<title>Ставки на матчі</title>
<style>
 body {
    margin:0;padding:0;font-family:Arial,sans-serif;
    background:url("https://content.rozetka.com.ua/goods/images/big/27254638.jpg") no-repeat center fixed;
    background-size:cover;color:#222;overflow-x:hidden;
 }
 .container {
    display:flex; max-width:1600px; margin:0 auto; width:100%;
    height:100vh; padding:10px; box-sizing:border-box;
    flex-wrap: wrap;
 }
 .block {
    position:relative; background:rgba(255,255,255,.6); margin:5px; padding:10px; border-radius:8px;
    overflow-y:auto; flex-shrink:0; display:flex; flex-direction:column;
 }
 .left {width:38%}
 .center {width:42%}
 .right {width:18%}
 .block::before {
    content:"";
    background:url("https://footking.mobi/union/logo/big3.jpg?r=222") no-repeat center;
    background-size:contain; opacity:.15; position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%); width:60%; height:60%; pointer-events:none; z-index:0;
 }
 .block>* {position:relative; z-index:1;}
 table {width:100%; border-collapse:collapse; font-size:14px; max-width:100%;}
 th,td {padding:6px; border:1px solid #aaa; text-align:center;}
 .champ-col {text-align:center; white-space:normal; word-wrap:break-word;}
 .btn {padding:5px 8px; margin:2px; border:none; border-radius:4px; cursor:pointer; color:#fff; background:#337ab7; font-size:12px}
 .btn-danger {background:#d9534f}
 .btn-success {background:#5cb85c}
 .btn-small {padding:2px 6px; font-size:10px;}
 a {color:#337ab7; text-decoration:none;}
 a:hover {text-decoration:underline;}
 .status-live {background:#5cb85c; color:#fff; font-weight:bold; padding:3px 6px; border-radius:4px;}
 .status-finished {background:#d9534f; color:#fff; font-weight:bold; padding:3px 6px; border-radius:4px;}
 .delete-user-btn {
    background:#d9534f; border:none; color:#fff; font-weight:bold; cursor:pointer; margin-right:5px;
    border-radius:50%; width:22px; height:22px; line-height:20px; font-size:14px;
 }
 /* Адаптивность */
 @media (max-width: 900px) {
    .container {flex-direction: column; height:auto;}
    .left, .center, .right {width: 100%;}
    .block {height:auto; max-height:none;}
 }
</style>

<script>
function confirmUserDeletion(username) {
    if (confirm(`Ви впевнені, що хочете видалити гравця "${username}"?`)) {
        // Создадим и отправим POST форму
        let form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/delete_user/${username}`;
        document.body.appendChild(form);
        form.submit();
    }
}
function confirmResetResults() {
    if (confirm("Ви впевнені, що хочете скинути таблицю результатів (W, L, Pts)?")) {
        document.getElementById('reset-results-form').submit();
    }
}
</script>

</head>
<body>

<div class="container">

<!-- Лівий блок -->
<div class="left block"><h2>Матчі в процесі / завершені</h2>
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
 <hr>
 <h3>Додати матч</h3>
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
<div class="right block">
  <h2>Таблиця лідерів</h2>

  {% if is_admin %}
  <form id="reset-results-form" method="post" action="{{url_for('admin_reset_results')}}">
    <button type="button" class="btn btn-danger btn-small" onclick="confirmResetResults()">Скинути результати</button>
  </form>
  {% endif %}

  <table>
   <tr><th></th><th>Нік</th><th>W</th><th>L</th><th>Pts</th></tr>
   {% for u,s in leaderboard.items() %}
     <tr>
       <td>
         {% if is_admin and u != 'pau4ok' %}
         <button title="Видалити гравця" class="delete-user-btn" onclick="confirmUserDeletion('{{u}}')">×</button>
         {% endif %}
       </td>
       <td>{{u}}</td><td>{{s.wins}}</td><td>{{s.losses}}</td><td>{{s.points}}</td>
     </tr>
   {% endfor %}
  </table>
</div>

</div>

</body>
</html>
'''

import os

if __name__ == '__main__':
    # При запуске убедимся, что админ существует
    if 'pau4ok' not in users:
        users['pau4ok'] = {'password_hash': generate_password_hash('Paukov1405'), 'bets': {}}

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
