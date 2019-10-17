from flask import Flask, render_template, url_for, redirect, flash, request, jsonify
# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, IntegerField, SubmitField
# from wtforms.validators import InputRequired, Email, Length, EqualTo
from functools import wraps
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_cors import CORS
import forms
import database
import flask_login
import mysql.connector
import flask
app = Flask(__name__)
CORS(app)


app.config['SECRET_KEY'] = database.secretkey

login_manager = flask_login.LoginManager()
login_manager.init_app(app)



def dbConnect():
    db = mysql.connector.connect(
    host =  database.databaseInfo["host"],
    user = database.databaseInfo["user"],
    passwd = database.databaseInfo["passwd"],
    database = database.databaseInfo["database"]
    )
    return db


class User(flask_login.UserMixin):
    def get_reset_token(self,expires=600):
        s = Serializer(app.config['SECRET_KEY'],expires)
        return s.dumps({'username':self.id}).decode('utf-8')
    
    @staticmethod
    def verify_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            username = s.loads(token)['username']
        except:
            return None
        return User.query.get(username)
    def is_admin(self):
        db = dbConnect()
        cursor = db.cursor()
        account = cursor.execute('SELECT * FROM users WHERE(username = %s)'%('"'+self.id+'"'))
        account = cursor.fetchall()
        db.disconnect()
        return account[0][3] == 1




@login_manager.user_loader
def user_loader(username):
    db = dbConnect()
    cursor = db.cursor()
    account = cursor.execute('SELECT * FROM users WHERE(username = %s)'%('"'+username+'"'))
    account = cursor.fetchall()
    db.disconnect()
    if(account == []):
        return
    else:
        user = User()
        user.id = username
        return user

@login_manager.request_loader
def request_loader(request):
    try:
        username = request.form.get('username')
        db = dbConnect()
        cursor = db.cursor()
        account = cursor.execute('SELECT * FROM users WHERE(username = %s)'%('"'+username+'"'))
        account = cursor.fetchall()
        db.disconnect()
        if(account ==[]):
            return
        else:
            user = User()
            user.id = username

            # DO NOT ever store passwords in plaintext and always compare password
            # hashes using constant-time comparison!
            user.is_authenticated = check_password_hash(account[0][2],request.form['password'])

            return user
    except:
        return
    
@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'
def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if flask_login.current_user.is_admin() == True:
            return f(*args, **kwargs)
        else:
            return 'unauthorized'

    return wrap

@app.context_processor
def getLogged():
    return dict(loggedIn=flask_login.current_user.is_authenticated)

@app.context_processor
def isAdmin():
    isAdmin = False
    try:
        isAdmin = flask_login.current_user.is_admin()
    except:
        pass
    return dict(isAdmin=isAdmin)
    


@app.route('/')
def index():
    if flask_login.current_user.is_authenticated:
        if flask_login.current_user.is_admin():
            return flask.redirect(url_for('admin_home'))
        else:
            return flask.redirect(url_for('students'))
    else:
        return flask.redirect(url_for('login'))


@app.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = forms.userForm()
    db = dbConnect()
    cursor = db.cursor()
    
    if form.validate_on_submit():
        print('validated')
        sql = 'INSERT INTO users (username,password,isadmin,name,address,town,phonenumber,usercode) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)'
        generate_password_hash
        values = (form.username.data,generate_password_hash(form.password.data,method='sha256'),0,form.name.data,form.address.data,form.town.data,form.phone.data,form.code.data)
        cursor.execute(sql,values)
        sql = 'SELECT studentid FROM students WHERE(parentemail = "%s")'%(form.username.data)
        cursor.execute(sql)
        students = cursor.fetchall()
        if(students):
            sql = 'SELECT userid FROM users WHERE(username = "%s")'%(form.username.data)
            cursor.execute(sql)
            user = cursor.fetchone()
            sql = 'INSERT INTO pickup (userid,studentid) VALUES(%s,%s) ON DUPLICATE KEY UPDATE userid = %s'
            sqlparents = 'INSERT INTO parents (userid,studentid) VALUES(%s,%s) ON DUPLICATE KEY UPDATE userid = %s'
            for student in students:
                values = (user[0],student[0],user[0])
                cursor.execute(sql,values)
                cursor.execute(sqlparents,values)
                db.commit()
        db.commit()
        flask.redirect(url_for('add_user'))
    cursor.execute('SELECT * FROM users')
    desc = cursor.description
    columns = [col[0] for col in desc]
    users = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('add_user.html',form=form,users=users)

@app.route('/checkin', methods=['GET', 'POST'])
@admin_required
def checkin():
    db = dbConnect()
    cursor = db.cursor()
    if request.method == "POST":  
        selected = request.form.getlist('checkinbox')
        for id in selected:
            cursor.execute('UPDATE students SET ischeckedin = 1 WHERE studentid = %s'%(id))
            cursor.execute("SET time_zone = 'US/Eastern'")
            sql = 'INSERT INTO actions (action,user,studentid) VALUES(%s,%s,%s)'
            values = ('Checkin',flask_login.current_user.id,id)
            cursor.execute(sql,values)
            db.commit()
        
        return flask.redirect(url_for('checkin'))
    
    cursor.execute('SELECT * FROM students WHERE (ischeckedin = 0)')
    desc = cursor.description
    columns = [col[0] for col in desc]
    notCheckedIn = [dict(zip(columns,row)) for row in cursor]
    print(notCheckedIn)
    cursor.execute('SELECT * FROM students WHERE (ischeckedin = 1)')
    desc = cursor.description
    columns = [col[0] for col in desc]
    checkedIn = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('checkin.html',notCheckedIn=notCheckedIn,checkedIn=checkedIn)


@app.route('/checkout', methods=['GET', 'POST'])
@admin_required
def checkout():
    db = dbConnect()
    cursor = db.cursor()
    if request.method == "POST":
        selected = request.form.getlist('checkoutbox')
        for id in selected:
            cursor.execute('UPDATE students SET ischeckedin = 0 WHERE studentid = %s'%(id))
            cursor.execute("SET time_zone = 'US/Eastern'")
            sql = 'INSERT INTO actions (action,user,studentid) VALUES(%s,%s,%s)'
            values = ('Checkout',flask_login.current_user.id,id)
            cursor.execute(sql,values)
            db.commit()
        return flask.redirect(url_for('checkout'))
    cursor.execute('SELECT * FROM students WHERE (ischeckedin = 0)')
    desc = cursor.description
    columns = [col[0] for col in desc]
    notCheckedIn = [dict(zip(columns,row)) for row in cursor]
    cursor.execute('SELECT * FROM students WHERE (ischeckedin = 1)')
    desc = cursor.description
    columns = [col[0] for col in desc]
    checkedIn = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('checkout.html',notCheckedIn=notCheckedIn,checkedIn=checkedIn)

@app.route('/login', methods=['GET', 'POST'])
def login():
    
    form = forms.loginForm()
    if form.validate_on_submit():
        username = form.username.data
        db = dbConnect()
        cursor = db.cursor()
        account = cursor.execute('SELECT * FROM users WHERE(username = %s)'%('"'+username+'"'))
        account = cursor.fetchall()
        db.disconnect()
        if(not(account == [])):
            #change password stuff
            if (check_password_hash(account[0][2], form.password.data)): 
                user = User()
                user.id = username
                flask_login.login_user(user)
                return flask.redirect(flask.url_for('index'))

        return render_template('login.html',form=form,invalid=True)
    return render_template('login.html',form=form)

@app.route('/change_password', methods=['GET','POST'])
@flask_login.login_required
def changePsw():
    form = forms.changePasswordForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            db = dbConnect()
            cursor = db.cursor()
            cursor.execute('SELECT password FROM users WHERE(username = "%s")'%(flask_login.current_user.id))
            password = cursor.fetchone()
            db.disconnect()
            if(check_password_hash(password[0],form.password.data)):
                cursor.execute('UPDATE users SET password = "%s" WHERE(username = "%s")'%(generate_password_hash(form.newPassword.data,method='sha256'),flask_login.current_user.id))
                db.commit()
                return flask.redirect(flask.url_for('index'))
            else:
                return "bad password"
                
    return render_template('change_password.html',form=form,user=flask_login.current_user.id)

@app.route('/admin_home')
@admin_required
def admin_home():

    return render_template('admin_home.html')

@app.route('/add_students', methods=['POST','GET'])
#@flask_login.login_required
@admin_required
def add_students():
    form = forms.insertForm()
    username = request.form.get('username')
    db =dbConnect()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM students')
    desc = cursor.description
    columns = [col[0] for col in desc]
    students = [dict(zip(columns,row)) for row in cursor]
    print('before')
    
    if form.validate_on_submit():
        print("validated")
        print(form.studentName.data)
        print(form.parentName.data)
        sql = 'INSERT INTO students (studentname,birthday,parentname,parentphone,parentemail,address,town) VALUES(%s,%s,%s,%s,%s,%s,%s)'
        values = (form.studentName.data, form.birthday.data, form.parentName.data, form.parentPhone.data, form.email.data,form.address.data,form.town.data)
        cursor.execute(sql,values)
        db.commit()    
        sql = 'SELECT userid FROM users WHERE(username = "%s")'%(form.email.data)
        cursor.execute(sql)
        user = cursor.fetchone()
        if(user):
            sql = 'SELECT studentid FROM students WHERE(studentname = "%s" AND parentemail = "%s")'%(form.studentName.data,form.email.data)
            cursor.execute(sql)
            studentid = cursor.fetchone()
            studentid = studentid[0]
            sql = 'INSERT INTO pickup (userid, studentid) VALUES(%s,%s) ON DUPLICATE KEY UPDATE studentid = %s'
            sqlparents = 'INSERT INTO parents (userid,studentid) VALUES(%s,%s) ON DUPLICATE KEY UPDATE userid = %s'
            values = (user[0],studentid,studentid)
            cursor.execute(sql,values)
            cursor.execute(sqlparents,values)
            db.commit()
        db.disconnect()
        return redirect(url_for('add_students'))
    db.disconnect()
    #     studentName = StringField('studentName', validators=[InputRequired()])
    # parentName = StringField('parentName', validators=[InputRequired()])
    # age = IntegerField('age',validators=[InputRequired()])
    # parentPhone = IntegerField('parentPhone',validators=[InputRequired()])
    # email = StringField('email',validators=[InputRequired(),Email()])

    return render_template('add_students.html', form=form,students=students)

@app.route('/parents_checkout', methods=['POST','GET'])
@flask_login.login_required
def parents_checkout():
    loggedIn = flask_login.current_user.is_authenticated
    email = flask_login.current_user.id
    db = dbConnect()
    cursor = db.cursor()
    if request.method == "POST":
        selected = request.form.getlist('checkoutbox')
        for id in selected:
            cursor.execute('UPDATE students SET ischeckedin = 0 WHERE studentid = %s'%(id))
            cursor.execute("SET time_zone = 'US/Eastern'")
            sql = 'INSERT INTO actions (action,user,studentid) VALUES(%s,%s,%s)'
            values = ('Checkout',flask_login.current_user.id,id)
            cursor.execute(sql,values)
            db.commit()
        return flask.redirect(url_for('students'))
    
    # sql = "SELECT userid from users WHERE(username = '%s')" %(email)
    # cursor.execute(sql)
    # userid = cursor.fetchone()


    sql = "SELECT students.studentname, students.studentid, students.ischeckedin, users.name FROM users JOIN pickup USING(userid) JOIN students USING(studentid) WHERE (users.username ='%s' AND students.ischeckedin = 1)"%(email)
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    students = [dict(zip(columns,row)) for row in cursor]

    allCheckedOut = True
    if(students):
        allCheckedOut = False

    db.disconnect()
    return render_template('parents_checkout.html', students=students,allCheckedOut=allCheckedOut)


@app.route('/parents_checkin', methods=['POST','GET'])
@flask_login.login_required
def parents_checkin():
    email = flask_login.current_user.id
    db = dbConnect()
    cursor = db.cursor()
    if request.method == "POST":
        selected = request.form.getlist('checkinbox')
        for id in selected:
            cursor.execute('UPDATE students SET ischeckedin = 1 WHERE studentid = %s'%(id))
            cursor.execute("SET time_zone = 'US/Eastern'")
            sql = 'INSERT INTO actions (action,user,studentid) VALUES(%s,%s,%s)'
            values = ('Checkin',flask_login.current_user.id,id)
            cursor.execute(sql,values)
            db.commit()
        return flask.redirect(url_for('students'))
    sql = "SELECT students.studentname, students.studentid, students.ischeckedin, users.name FROM users JOIN pickup USING(userid) JOIN students USING(studentid) WHERE (users.username ='%s')"%(email)
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    students = [dict(zip(columns,row)) for row in cursor]
    return render_template('parents_checkin.html',students=students)



@app.route('/pickup_list', methods=['POST','GET'])
@admin_required
def pickup_list():
    db = dbConnect()
    cursor = db.cursor()

    sql = "SELECT username,name,userid FROM users WHERE (isadmin = 0)"
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    users = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    
    return render_template('pickup_list.html',users=users)

@app.route('/pickup/<username>', methods=['POST','GET'])
@admin_required
def user_pickup(username):
    user = username
    db =dbConnect()
    cursor = db.cursor()
    if request.method == "POST":
        if 'removebox' in request.form:
            selected = request.form.getlist('removebox')
            print(selected)
            for id in selected:
                print(id)
                cursor.execute('DELETE FROM pickup WHERE(userid = %s AND studentid = %s)'%(user,id))
                db.commit()
        elif 'addbox' in request.form:
            selected = request.form.getlist('addbox')
            print(selected)
            for id in selected:
                print(id)
                sql = 'INSERT INTO pickup (userid, studentid) VALUES (%s,%s) ON DUPLICATE KEY UPDATE userid = %s'
                values = (user,id,user)

                cursor.execute(sql,values)
                db.commit()

                
        db.disconnect()
        return flask.redirect(url_for('user_pickup',username=user))



    

    sql = "SELECT students.studentname, students.studentid, users.name FROM users JOIN pickup USING(userid) JOIN students USING(studentid) WHERE (users.userid ='%s')"%(user)
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    students = [dict(zip(columns,row)) for row in cursor]


    sql = "SELECT studentname, parentemail,studentid FROM students"
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    allStudents = [dict(zip(columns,row)) for row in cursor]
    if(students):
        db.disconnect()
        return render_template('user_pickup.html',students=students,allStudents=allStudents)
    else:
        cursor.execute('SELECT username FROM users WHERE (userid = %s)'%(user))
        name = cursor.fetchone()
        return render_template('no_students_user_pickup.html',name=name,allStudents=allStudents)


@app.route('/students')
@flask_login.login_required
def students():
    db = dbConnect()
    cursor = db.cursor()
    sql = "SELECT students.studentname, students.studentid, students.ischeckedin, users.name FROM users JOIN pickup USING(userid) JOIN students USING(studentid) WHERE (users.username ='%s')"%(flask_login.current_user.id)
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    students = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('students.html',students=students)

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('logout.html')

@app.route('/all_students')
@admin_required
def all_students():
    db = dbConnect()
    cursor=db.cursor()
    sql = "SELECT * FROM students"
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    students = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('all_students.html',students=students)





@app.route('/edit_student/<id>', methods=['POST','GET'])
@admin_required
def edit_student(id):
    form = forms.editStudentsForm()
    db = dbConnect()
    cursor = db.cursor()
    if form.validate_on_submit():
        sql = "UPDATE students SET studentname = '%s', parentname = '%s', parentphone = %s, parentemail='%s', address = '%s', town = '%s', birthday = '%s' WHERE (studentid =%s)"%(form.studentName.data, form.parentName.data, form.parentPhone.data, form.email.data, form.address.data, form.town.data, form.birthday.data,id)
        cursor.execute(sql)
        db.commit()
        db.disconnect()
        return flask.redirect(url_for('all_students'))
    cursor.execute("SELECT * FROM students WHERE(studentid = %s)"%(id))
    desc = cursor.description
    columns = [col[0] for col in desc]
    student = [dict(zip(columns,row)) for row in cursor]
    student=student[0]
    db.disconnect()
    return render_template('edit_student.html',student=student,form=form)



@app.route('/delete_student/<id>', methods=['POST','GET'])
@admin_required
def delete_student(id):
    db = dbConnect()
    cursor = db.cursor()
    cursor.execute('DELETE FROM students WHERE(studentid = %s)'%(id))
    cursor.execute('DELETE FROM pickup WHERE(studentid = %s)'%(id))
    db.commit()
    return flask.redirect(url_for('all_students'))




@app.route('/edit_user/<id>', methods=['POST','GET'])
@admin_required
def edit_user(id):
    form = forms.editusersForm()
    db = dbConnect()
    cursor = db.cursor()
    if form.validate_on_submit():
        sql = "UPDATE users SET parentname = '%s', parentphone = %s, parentemail='%s', address = '%s', town = '%s', birthday = '%s' WHERE (userid =%s)"%(form.parentName.data, form.parentPhone.data, form.email.data, form.address.data, form.town.data, form.birthday.data,id)
        cursor.execute(sql)
        db.commit()
        db.disconnect()
        return flask.redirect(url_for('all_users'))
    cursor.execute("SELECT * FROM users WHERE(userid = %s)"%(id))
    desc = cursor.description
    columns = [col[0] for col in desc]
    user = [dict(zip(columns,row)) for row in cursor]
    user=user[0]
    db.disconnect()
    return render_template('edit_user.html',user=user,form=form)





@app.route('/all_users')
@admin_required
def all_users():
    db=dbConnect()
    cursor = db.cursor()
    sql = "SELECT * FROM users"
    cursor.execute(sql)
    desc = cursor.description
    columns = [col[0] for col in desc]
    users = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('all_users.html', users=users)


@app.route('/delete_user/<id>', methods=['POST','GET'])
@admin_required
def delete_user(id):
    db = dbConnect()
    cursor = db.cursor()
    cursor.execute('DELETE FROM users WHERE(userid = %s)'%(id))
    cursor.execute('DELETE FROM pickup WHERE(userid = %s)'%(id))
    db.commit()
    return flask.redirect(url_for('all_users'))

def new_route():
    return render_template('index.html')

@app.route('/test',methods=['POST','GET'])
def test():
    if request.method == "POST":
        db = dbConnect()
        cursor = db.cursor()
        code = request.form.get('code')
        students = request.form.getlist('checkoutbox')
        username = request.form.get('userbox')
        if code:
            cursor.execute('SELECT userid,username FROM users WHERE(usercode = %s)'%(code))
            
            account = cursor.fetchone()
            if account:
                username = account[1]
                account = account[0]
                sql = "SELECT students.studentname, students.studentid, students.ischeckedin, users.name FROM users JOIN pickup USING(userid) JOIN students USING(studentid) WHERE (users.userid ='%s' AND students.ischeckedin=1)"%(account)
                cursor.execute(sql)
                desc = cursor.description
                columns = [col[0] for col in desc]
                students = [dict(zip(columns,row)) for row in cursor]
                print(students)
                db.disconnect()
                return render_template('students_checkout.html',students=students,username=username)
            db.disconnect()
            return flask.redirect(url_for('test'))
        elif students:
            print(students)
            print(username)
            for id in students:
                cursor.execute('UPDATE students SET ischeckedin = 0 WHERE studentid = %s'%(id))
                cursor.execute("SET time_zone = 'US/Eastern'")
                sql = 'INSERT INTO actions (action,user,studentid) VALUES(%s,%s,%s)'
                values = ('Checkout',username,id)
                cursor.execute(sql,values)
                db.commit()
            return flask.redirect(url_for('test'))
    return render_template('test.html')

@app.route('/_actions/<date>')
@admin_required
def actions_json(date):
    date = date.split('-')
    year = str(date[0])
    month = str(date[1])
    day = str(date[2])
    db = dbConnect()
    cursor = db.cursor()
    cursor.execute('select date from actions WHERE (date > "%s 00:00:00" AND date < "%s 23:59:59")'%(year+'-'+month+'-'+day,year+'-'+month+'-'+day))
    desc = cursor.description
    columns = [col[0] for col in desc]
    actions = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return jsonify(actions)

@app.route('/logs')
@admin_required
def logs():
    db = dbConnect()
    cursor = db.cursor()
    cursor.execute('select date from actions group by DATE_FORMAT(Date, "%c %Y")')
    desc = cursor.description
    columns = [col[0] for col in desc]
    dates = [dict(zip(columns,row)) for row in cursor]
    months = {1:"January", 2:"February", 3:"March", 4:"April", 5:"May", 6:"June", 7:"July", 8:"August", 9:"September", 10:"October", 11:"November", 12:"December"}
    db.disconnect()
    return render_template('logs.html', dates = dates, months=months)

@app.route('/logs/<year_month>')
@admin_required
def logs_month(year_month):
    date = year_month.split('-')
    year = str(date[0])
    month = str(date[1])
    db = dbConnect()
    cursor = db.cursor()
    sql = "SELECT date from actions WHERE(MONTH(date) = %s AND YEAR(date) = %s)"%(month,year)
    sql += " group by DATE_FORMAT(Date, '%c %d %Y')"
    cursor.execute(sql)
    # cursor.execute("SELECT date from actions WHERE(MONTH(date) = %s AND YEAR(date) = %s)"%(month,year))
    desc = cursor.description
    columns = [col[0] for col in desc]
    days = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('logs_month.html',days=days)

@app.route('/logs/<year_month>/<day>')
@admin_required
def logs_day(year_month, day):
    date = year_month.split('-')
    year = str(date[0])
    month = str(date[1])
    day = day
    db = dbConnect()
    cursor = db.cursor()
    cursor.execute('select date from actions WHERE (date > "%s 00:00:00" AND date < "%s 23:59:59")'%(year+'-'+month+'-'+day,year+'-'+month+'-'+day))
    desc = cursor.description
    columns = [col[0] for col in desc]
    actions = [dict(zip(columns,row)) for row in cursor]
    db.disconnect()
    return render_template('logs_day.html',actions=actions)
    
# @app.route("/", methods=['POST','GET'])
# def index():
#     form = Form()
    
#     return render_template('index.html',form=form)