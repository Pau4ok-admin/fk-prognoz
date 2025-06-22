from flask import Flask, render_template_string, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import datetime, pytz
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
users = {'admin': {'password_hash': generate_password_hash('admin'), 'bets': {}}}

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
                wins += 1; points += 3
            else:
                losses += 1; points -= 1
        board[user] = {'wins': wins, 'losses': losses, 'points': points}
    return dict(sorted(board.items(), key=lambda x: x[1]['points'], reverse=True))

def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if session.get('user') != 'admin':
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

</div></body></html>
'''

# ---------- ROUTES ----------
@app.route('/')
def index():
    now = current_kyiv_time()
    for m in matches:
        if m['status']=='upcoming' and m['start_time']<=now:
            m['status']='live'
        m['start_time_local'] = m['start_time'].strftime('%H:%M %d.%m.%Y')

    left  = [m for m in matches if m['status'] in ('live','finished')]
    center= [m for m in matches if m['status']=='upcoming']

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
        is_admin=(user=='admin')
    )

# --------- Auth ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        nick=request.form['username'].strip().lower()
        pwd=request.form['password']
        if nick in users: return "Нік зайнятий"
        users[nick]={'password_hash':generate_password_hash(pwd),'bets':{}}
        session['user']=nick
        return redirect('/')
    return '<h2>Реєстрація</h2><form method=post>Нік:<input name=username required><br>Пароль:<input type=password name=password required><br><button>OK</button></form>'

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        nick=request.form['username'].strip().lower()
        pwd=request.form['password']
        if nick in users and check_password_hash(users[nick]['password_hash'],pwd):
            session['user']=nick; return redirect('/')
        return "Невірний нік або пароль"
    return '<h2>Вхід</h2><form method=post>Нік:<input name=username required><br>Пароль:<input type=password name=password required><br><button>OK</button></form>'

@app.route('/logout')
def logout():
    session.pop('user',None); return redirect('/')

# --------- Bets ----------
@app.route('/make_bets', methods=['POST'])
def make_bets():
    if 'user' not in session: return redirect('/login')
    u=session['user']; b=users[u]['bets']
    for m in matches:
        val=request.form.get(f'bet_{m["id"]}','')
        if val in ('P1','X','P2'): b[m['id']]=val
        else: b.pop(m['id'],None)
    return redirect('/')

# --------- Admin ----------
@app.route('/admin/add_match', methods=['POST'])
@admin_required
def admin_add_match():
    try:
        new={
            'id':get_next_match_id(),
            'round':int(request.form['round']),
            'championship':request.form['championship'],
            'team1':request.form['team1'],'team2':request.form['team2'],
            'link_team1':request.form['link_team1'],'link_team2':request.form['link_team2'],
            'start_time':KYIV_TZ.localize(datetime.datetime.strptime(request.form['start_time'],'%Y-%m-%dT%H:%M')),
            'status':'upcoming','score':'','result':''
        }
        matches.append(new)
    except Exception as e: return f'Помилка: {e}',400
    return redirect('/')

@app.route('/admin/delete_match/<int:match_id>', methods=['POST'])
@admin_required
def admin_delete_match(match_id):
    global matches; matches=[m for m in matches if m['id']!=match_id]
    for u in users.values(): u['bets'].pop(match_id,None)
    return redirect('/')

@app.route('/admin/toggle_status/<int:match_id>', methods=['POST'])
@admin_required
def admin_toggle_status(match_id):
    for m in matches:
        if m['id']==match_id:
            m['status']='finished' if m['status']=='live' else 'live'
            break
    return redirect('/')

@app.route('/admin/update_score/<int:match_id>', methods=['POST'])
@admin_required
def admin_update_score(match_id):
    sc=request.form['score'].strip(); res=request.form['result']
    for m in matches:
        if m['id']==match_id:
            m['score']=sc; m['result']=res if res in ('P1','X','P2') else ''
            if m['result']: m['status']='finished'
            break
    return redirect('/')

@app.route('/admin/edit_match/<int:match_id>', methods=['GET','POST'])
@admin_required
def admin_edit_match(match_id):
    m=next((x for x in matches if x['id']==match_id),None)
    if not m: return "Матч не знайдено"
    if request.method=='POST':
        try:
            m.update(
                round=int(request.form['round']),
                championship=request.form['championship'],
                team1=request.form['team1'], team2=request.form['team2'],
                link_team1=request.form['link_team1'], link_team2=request.form['link_team2']
            )
            m['start_time']=KYIV_TZ.localize(datetime.datetime.strptime(request.form['start_time'],'%Y-%m-%dT%H:%M'))
            return redirect('/')
        except Exception as e: return f'Помилка: {e}',400
    return f'''
    <h2>Редагувати матч #{match_id}</h2>
    <form method="post">
      Тур:<input type=number name=round value="{m['round']}" required><br/>
      Чемпіонат:<input name=championship value="{m['championship']}" required><br/>
      Team1:<input name=team1 value="{m['team1']}" required><br/>
      Link1:<input name=link_team1 value="{m['link_team1']}" required><br/>
      Team2:<input name=team2 value="{m['team2']}" required><br/>
      Link2:<input name=link_team2 value="{m['link_team2']}" required><br/>
      Час:<input type=datetime-local name=start_time value="{m['start_time'].strftime('%Y-%m-%dT%H:%M')}" required><br/>
      <button>Зберегти</button>
    </form><p><a href="/">Назад</a></p>
    '''

if __name__ == '__main__':
    app.run(debug=True)
