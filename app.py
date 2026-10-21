import os,sqlite3
from functools import wraps
from flask import Flask,render_template,request,redirect,url_for,session,flash,abort,send_from_directory
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,'student_hub.db'); UP=os.path.join(BASE,'uploads'); PH=os.path.join(UP,'photos'); DOC=os.path.join(UP,'documents')
os.makedirs(PH,exist_ok=True); os.makedirs(DOC,exist_ok=True)
app=Flask(__name__); app.secret_key='student-hub-change-this-key'; app.config['MAX_CONTENT_LENGTH']=10*1024*1024

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init():
 c=db(); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL);CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE NOT NULL,name TEXT NOT NULL,register_no TEXT UNIQUE NOT NULL,dob TEXT,gender TEXT,department TEXT,year TEXT,college TEXT,phone TEXT,email TEXT,address TEXT,cgpa TEXT,photo TEXT,document TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL,service TEXT NOT NULL,description TEXT,status TEXT NOT NULL DEFAULT "Pending",admin_note TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
 if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone(): c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",('admin',generate_password_hash('admin123'),'admin'))
 c.commit(); c.close()
def role(r):
 def deco(f):
  @wraps(f)
  def w(*a,**k):
   if session.get('role')!=r: flash('Please login first.','warning'); return redirect(url_for('admin_login' if r=='admin' else 'login'))
   return f(*a,**k)
  return w
 return deco
def upload(f,folder,exts):
 if not f or not f.filename:return None
 ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else ''
 if ext not in exts: raise ValueError('Unsupported file type')
 n=os.path.splitext(secure_filename(f.filename))[0]+'_'+os.urandom(5).hex()+'.'+ext; f.save(os.path.join(folder,n)); return n
@app.route('/')
def home():
 c=db(); a=c.execute('SELECT COUNT(*) n FROM students').fetchone()['n']; b=c.execute('SELECT COUNT(*) n FROM requests').fetchone()['n']; d=c.execute("SELECT COUNT(*) n FROM requests WHERE status='Completed'").fetchone()['n']; c.close(); return render_template('home.html',students=a,requests=b,completed=d)
@app.route('/register',methods=['GET','POST'])
def register():
 if request.method=='POST':
  f=request.form
  if not all(f.get(x,'').strip() for x in ('username','password','name','register_no')): flash('Fill all required fields.','danger'); return render_template('register.html')
  c=db()
  try:
   uid=c.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',(f['username'].strip(),generate_password_hash(f['password']),'student')).lastrowid
   c.execute('INSERT INTO students(user_id,name,register_no,dob,gender,department,year,college,phone,email,address,cgpa) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(uid,f['name'].strip(),f['register_no'].strip(),f.get('dob',''),f.get('gender',''),f.get('department',''),f.get('year',''),f.get('college',''),f.get('phone',''),f.get('email',''),f.get('address',''),f.get('cgpa',''))); c.commit(); flash('Account created. Please login.','success'); return redirect(url_for('login'))
  except sqlite3.IntegrityError: c.rollback(); flash('Username or register number already exists.','danger')
  finally:c.close()
 return render_template('register.html')
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  c=db(); u=c.execute("SELECT * FROM users WHERE username=? AND role='student'",(request.form.get('username','').strip(),)).fetchone(); c.close()
  if u and check_password_hash(u['password'],request.form.get('password','')): session.clear(); session.update(user_id=u['id'],username=u['username'],role='student'); return redirect(url_for('dashboard'))
  flash('Invalid student login.','danger')
 return render_template('login.html')
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
 if request.method=='POST':
  c=db(); u=c.execute("SELECT * FROM users WHERE username=? AND role='admin'",(request.form.get('username','').strip(),)).fetchone(); c.close()
  if u and check_password_hash(u['password'],request.form.get('password','')): session.clear(); session.update(user_id=u['id'],username=u['username'],role='admin'); return redirect(url_for('admin'))
  flash('Invalid admin login.','danger')
 return render_template('admin_login.html')
@app.route('/logout')
def logout(): session.clear(); flash('Logged out.','info'); return redirect(url_for('home'))
@app.route('/student/dashboard')
@role('student')
def dashboard():
 c=db(); s=c.execute('SELECT * FROM students WHERE user_id=?',(session['user_id'],)).fetchone(); r=c.execute('SELECT * FROM requests WHERE student_id=? ORDER BY id DESC',(s['id'],)).fetchall(); c.close(); return render_template('dashboard.html',student=s,requests=r)
@app.route('/student/profile',methods=['GET','POST'])
@role('student')
def profile():
 c=db(); s=c.execute('SELECT * FROM students WHERE user_id=?',(session['user_id'],)).fetchone()
 if request.method=='POST':
  f=request.form; photo=s['photo']; document=s['document']
  try:
   if request.files.get('photo') and request.files['photo'].filename: photo=upload(request.files['photo'],PH,{'png','jpg','jpeg','gif','webp'})
   if request.files.get('document') and request.files['document'].filename: document=upload(request.files['document'],DOC,{'pdf','png','jpg','jpeg','doc','docx'})
   c.execute('UPDATE students SET name=?,register_no=?,dob=?,gender=?,department=?,year=?,college=?,phone=?,email=?,address=?,cgpa=?,photo=?,document=? WHERE user_id=?',(f.get('name',''),f.get('register_no',''),f.get('dob',''),f.get('gender',''),f.get('department',''),f.get('year',''),f.get('college',''),f.get('phone',''),f.get('email',''),f.get('address',''),f.get('cgpa',''),photo,document,session['user_id'])); c.commit(); flash('Profile updated.','success'); return redirect(url_for('profile'))
  except (sqlite3.IntegrityError,ValueError) as e: c.rollback(); flash(str(e),'danger')
 s=c.execute('SELECT * FROM students WHERE user_id=?',(session['user_id'],)).fetchone(); c.close(); return render_template('profile.html',student=s)
@app.route('/student/services',methods=['GET','POST'])
@role('student')
def services():
 c=db(); s=c.execute('SELECT id FROM students WHERE user_id=?',(session['user_id'],)).fetchone()
 if request.method=='POST':
  service=request.form.get('service',''); desc=request.form.get('description','');
  if service: c.execute('INSERT INTO requests(student_id,service,description) VALUES(?,?,?)',(s['id'],service,desc)); c.commit(); flash('Request submitted.','success'); return redirect(url_for('services'))
 r=c.execute('SELECT * FROM requests WHERE student_id=? ORDER BY id DESC',(s['id'],)).fetchall(); c.close(); return render_template('services.html',requests=r)
@app.route('/contact',methods=['GET','POST'])
def contact():
 if request.method=='POST':
  c=db(); c.execute('INSERT INTO messages(name,email,message) VALUES(?,?,?)',(request.form.get('name',''),request.form.get('email',''),request.form.get('message',''))); c.commit(); c.close(); flash('Message sent.','success'); return redirect(url_for('contact'))
 return render_template('contact.html')
@app.route('/admin')
@role('admin')
def admin():
 c=db(); stats={x:c.execute(q).fetchone()['n'] for x,q in {'students':'SELECT COUNT(*) n FROM students','requests':'SELECT COUNT(*) n FROM requests','pending':"SELECT COUNT(*) n FROM requests WHERE status='Pending'",'completed':"SELECT COUNT(*) n FROM requests WHERE status='Completed'"}.items()}; recent=c.execute('SELECT r.*,s.name,s.register_no FROM requests r JOIN students s ON s.id=r.student_id ORDER BY r.id DESC LIMIT 8').fetchall(); c.close(); return render_template('admin.html',stats=stats,recent=recent)
@app.route('/admin/students')
@role('admin')
def students():
 q=request.args.get('q',''); c=db(); like='%'+q+'%'; rows=c.execute('SELECT s.*,u.username FROM students s JOIN users u ON u.id=s.user_id WHERE s.name LIKE ? OR s.register_no LIKE ? OR s.department LIKE ? ORDER BY s.id DESC',(like,like,like)).fetchall(); c.close(); return render_template('students.html',students=rows,q=q)
@app.route('/admin/student/<int:sid>')
@role('admin')
def student(sid):
 c=db(); s=c.execute('SELECT s.*,u.username FROM students s JOIN users u ON u.id=s.user_id WHERE s.id=?',(sid,)).fetchone(); r=c.execute('SELECT * FROM requests WHERE student_id=? ORDER BY id DESC',(sid,)).fetchall(); c.close(); abort(404) if not s else None; return render_template('student.html',student=s,requests=r)
@app.route('/admin/requests')
@role('admin')
def requests_admin():
 status=request.args.get('status','All'); c=db();
 if status in {'Pending','Approved','Rejected','Completed'}: r=c.execute('SELECT r.*,s.name,s.register_no FROM requests r JOIN students s ON s.id=r.student_id WHERE r.status=? ORDER BY r.id DESC',(status,)).fetchall()
 else:r=c.execute('SELECT r.*,s.name,s.register_no FROM requests r JOIN students s ON s.id=r.student_id ORDER BY r.id DESC').fetchall()
 c.close(); return render_template('requests.html',requests=r,status=status)
@app.route('/admin/request/<int:rid>',methods=['POST'])
@role('admin')
def update(rid):
 st=request.form.get('status','Pending'); note=request.form.get('note',''); c=db(); c.execute('UPDATE requests SET status=?,admin_note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(st,note,rid)); c.commit(); c.close(); flash('Request updated.','success'); return redirect(url_for('requests_admin'))
@app.route('/admin/messages')
@role('admin')
def messages(): c=db(); r=c.execute('SELECT * FROM messages ORDER BY id DESC').fetchall(); c.close(); return render_template('messages.html',messages=r)
@app.route('/uploads/<kind>/<name>')
@role('admin')
def files(kind,name): return send_from_directory(PH if kind=='photos' else DOC,name)
if __name__=='__main__': init(); app.run(debug=True)
