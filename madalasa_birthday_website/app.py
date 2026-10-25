import os, sqlite3, secrets, hmac, csv, io
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file, abort
from dotenv import load_dotenv
load_dotenv()
BASE=Path(__file__).resolve().parent; DB=Path(os.getenv('DATABASE_PATH',str(BASE/'instance'/'birthday.db'))); DB.parent.mkdir(exist_ok=True)
GALLERY=BASE/'static'/'gallery'; GALLERY.mkdir(parents=True,exist_ok=True)
app=Flask(__name__); app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=16*1024*1024)
CODE=os.getenv('VISITOR_PASSWORD','7021'); ADMIN_USER=os.getenv('ADMIN_USERNAME','admin'); ADMIN_PASS=os.getenv('ADMIN_PASSWORD','NiraAdmin@2026')
QUESTIONS=["What has been the most beautiful day of your life?","Who is your favourite person—the one who never judges you and always understands you?","Do you have a dream that you really want to achieve?","Is there anything you would like to tell me?","Have I ever done anything that hurt you or made you feel bad? If so, please tell me."]
def stamp(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def connect():
 c=sqlite3.connect(DB,timeout=20); c.row_factory=sqlite3.Row; return c
def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS visits(visitor TEXT PRIMARY KEY,started TEXT,last_seen TEXT,unlocked INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,visitor TEXT,event TEXT,details TEXT,created TEXT); CREATE TABLE IF NOT EXISTS responses(id INTEGER PRIMARY KEY,visitor TEXT,answer TEXT,created TEXT); CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY,visitor TEXT,qno INTEGER,question TEXT,answer TEXT,created TEXT); CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,visitor TEXT,name TEXT,rating INTEGER,message TEXT,memory TEXT,created TEXT,read INTEGER DEFAULT 0); CREATE INDEX IF NOT EXISTS idx_events_created ON events(created); CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created);''')
def vid():
 if 'visitor' not in session: session['visitor']=secrets.token_urlsafe(18)
 v=session['visitor']
 with connect() as c: c.execute('INSERT INTO visits(visitor,started,last_seen) VALUES(?,?,?) ON CONFLICT(visitor) DO UPDATE SET last_seen=excluded.last_seen',(v,stamp(),stamp()))
 return v
def event(name,details=''):
 with connect() as c: c.execute('INSERT INTO events(visitor,event,details,created) VALUES(?,?,?,?)',(vid(),name,str(details)[:300],stamp()))
def csrf():
 if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(24)
 return session['csrf']
app.jinja_env.globals['csrf_token']=csrf
@app.before_request
def check_csrf():
 if request.method=='POST':
  sent=request.form.get('csrf_token') or request.headers.get('X-CSRF-Token','')
  if not sent or not hmac.compare_digest(str(sent),str(session.get('csrf',''))): abort(400,'Form session expired. Refresh and try again.')
def admin(fn):
 @wraps(fn)
 def inner(*a,**kw):
  if not session.get('admin'): return redirect(url_for('admin_login'))
  return fn(*a,**kw)
 return inner
def unlocked(fn):
 @wraps(fn)
 def inner(*a,**kw):
  if not session.get('unlocked'): return redirect(url_for('home'))
  vid(); return fn(*a,**kw)
 return inner
@app.route('/',methods=['GET','POST'])
def home():
 vid()
 if request.method=='POST':
  if hmac.compare_digest(request.form.get('password',''),CODE):
   with connect() as c: c.execute('UPDATE visits SET unlocked=1 WHERE visitor=?',(vid(),))
   session['unlocked']=True; event('password_unlocked','Birthday code accepted'); return redirect(url_for('birthday'))
  event('password_failed','Incorrect birthday-page code'); flash('That code did not match. Try again 💚','error')
 return render_template('gate.html')
@app.route('/birthday')
@unlocked
def birthday(): event('birthday_page_opened','Birthday home'); return render_template('birthday.html',questions=QUESTIONS)
@app.post('/api/answer')
@unlocked
def save_answer():
 d=request.get_json(silent=True) or request.form; a=str(d.get('answer','')).lower()
 if a not in ('yes','no'): return jsonify(ok=False,error='Choose Yes or No.'),400
 with connect() as c: c.execute('INSERT INTO responses(visitor,answer,created) VALUES(?,?,?)',(vid(),a,stamp()))
 event('yes_no_answer','Answer: '+a); return jsonify(ok=True,message='Your answer has been saved 💚')
@app.post('/api/answers')
@unlocked
def save_answers():
 d=request.get_json(silent=True) or request.form; n=0
 with connect() as c:
  for i,q in enumerate(QUESTIONS,1):
   a=str(d.get('q'+str(i),'')).strip()
   if a: c.execute('INSERT INTO answers(visitor,qno,question,answer,created) VALUES(?,?,?,?,?)',(vid(),i,q,a[:5000],stamp())); n+=1
 event('questions_submitted',f'{n} answer(s) submitted'); return jsonify(ok=True,message=f'{n} answer(s) saved. Thank you 💚')
@app.post('/api/feedback')
@unlocked
def feedback():
 d=request.get_json(silent=True) or request.form; msg=str(d.get('message','')).strip()
 if not msg: return jsonify(ok=False,error='Please write a message first.'),400
 try: rating=int(d.get('rating',0) or 0)
 except: rating=0
 if rating not in range(6): rating=0
 with connect() as c: c.execute('INSERT INTO feedback(visitor,name,rating,message,memory,created) VALUES(?,?,?,?,?,?)',(vid(),str(d.get('name',''))[:100],rating,msg[:5000],str(d.get('memory',''))[:2000],stamp()))
 event('feedback_submitted','Feedback form submitted'); return jsonify(ok=True,message='Thank you for sharing your thoughts 💚')
@app.route('/gallery')
@unlocked
def gallery():
 photos=[{'name':p.name,'url':url_for('static',filename='gallery/'+p.name)} for p in sorted(GALLERY.iterdir()) if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.webp','.gif')]
 event('gallery_opened',f'{len(photos)} photos available'); return render_template('gallery.html',photos=photos)
@app.route('/letter')
@unlocked
def letter(): event('letter_opened','Birthday letter opened'); return render_template('letter.html')
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
 if request.method=='POST':
  if hmac.compare_digest(request.form.get('username',''),ADMIN_USER) and hmac.compare_digest(request.form.get('password',''),ADMIN_PASS): session.clear(); session['admin']=True; session['csrf']=secrets.token_urlsafe(24); return redirect(url_for('dashboard'))
  flash('Incorrect admin username or password.','error')
 return render_template('admin_login.html')
@app.post('/admin/logout')
@admin
def logout(): session.clear(); return redirect(url_for('admin_login'))
@app.route('/admin')
@admin
def dashboard():
 with connect() as c:
  stats={k:c.execute(q).fetchone()[0] for k,q in {'visits':'SELECT COUNT(*) FROM visits','unlocked':'SELECT COUNT(*) FROM visits WHERE unlocked=1','yes':"SELECT COUNT(*) FROM responses WHERE answer='yes'",'no':"SELECT COUNT(*) FROM responses WHERE answer='no'",'answers':'SELECT COUNT(*) FROM answers','feedback':'SELECT COUNT(*) FROM feedback','unread':'SELECT COUNT(*) FROM feedback WHERE read=0','events':'SELECT COUNT(*) FROM events'}.items()}
  recent=c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 15').fetchall()
 return render_template('admin_dashboard.html',stats=stats,recent=recent)
@app.route('/admin/feedback')
@admin
def feedback_list():
 q=request.args.get('q',''); status=request.args.get('status','all'); clauses=[]; params=[]
 if q: clauses.append('(message LIKE ? OR name LIKE ? OR memory LIKE ?)'); params += ['%'+q+'%']*3
 if status=='unread': clauses.append('read=0')
 if status=='read': clauses.append('read=1')
 sql='SELECT * FROM feedback'+((' WHERE '+' AND '.join(clauses)) if clauses else '')+' ORDER BY id DESC LIMIT 500'
 with connect() as c: rows=c.execute(sql,params).fetchall()
 return render_template('admin_feedback.html',rows=rows,q=q,status=status)
@app.post('/admin/feedback/<int:fid>/read')
@admin
def mark_read(fid):
 with connect() as c: c.execute('UPDATE feedback SET read=1 WHERE id=?',(fid,))
 return redirect(url_for('feedback_list'))
@app.post('/admin/feedback/<int:fid>/delete')
@admin
def delete_feedback(fid):
 with connect() as c: c.execute('DELETE FROM feedback WHERE id=?',(fid,))
 flash('Feedback deleted.','success'); return redirect(url_for('feedback_list'))
@app.route('/admin/answers')
@admin
def answers_list():
 with connect() as c: rows=c.execute('SELECT * FROM answers ORDER BY id DESC LIMIT 1000').fetchall()
 return render_template('admin_answers.html',rows=rows)
@app.route('/admin/interactions')
@admin
def interactions():
 selected=request.args.get('event','')
 with connect() as c:
  rows=c.execute('SELECT * FROM events'+(' WHERE event=?' if selected else '')+' ORDER BY id DESC LIMIT 1000',([selected] if selected else [])).fetchall(); types=[r[0] for r in c.execute('SELECT DISTINCT event FROM events ORDER BY event')]
 return render_template('admin_interactions.html',rows=rows,types=types,selected=selected)
@app.route('/admin/export.csv')
@admin
def export_csv():
 out=io.StringIO(); w=csv.writer(out); w.writerow(['Date','Name','Rating','Message','Favourite memory','Visitor session'])
 with connect() as c: rows=c.execute('SELECT created,name,rating,message,memory,visitor FROM feedback ORDER BY id DESC').fetchall()
 for row in rows:
  vals=[]
  for v in row:
   s='' if v is None else str(v); vals.append("'"+s if s.startswith(('=','+','-','@')) else s)
  w.writerow(vals)
 b=io.BytesIO(out.getvalue().encode('utf-8-sig')); b.seek(0); return send_file(b,mimetype='text/csv',as_attachment=True,download_name='birthday_feedback.csv')
@app.errorhandler(400)
def bad(err): return render_template('error.html',code=400,message=getattr(err,'description','Refresh and try again.')),400
@app.errorhandler(404)
def missing(err): return render_template('error.html',code=404,message='That page could not be found.'),404
init()
if __name__=='__main__':
 print('Website: http://127.0.0.1:5000 | Admin: http://127.0.0.1:5000/admin/login | admin / NiraAdmin@2026')
 app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
