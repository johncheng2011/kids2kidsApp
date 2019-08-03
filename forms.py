from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField
from wtforms.validators import InputRequired, Email, Length, EqualTo, ValidationError
import mysql.connector
import database

class loginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired()],render_kw={"placeholder": "Username"})
    password = PasswordField('password', validators=[InputRequired()],render_kw={"placeholder": "Password"})
    submit = SubmitField('Log In')

#insert students
class insertForm(FlaskForm):
    studentName = StringField('studentName', validators=[InputRequired()])
    parentName = StringField('parentName', validators=[InputRequired()])
    birthday = StringField('birthday',validators=[InputRequired()])
    parentPhone = IntegerField('parentPhone',validators=[InputRequired()])
    email = StringField('email',validators=[InputRequired(),Email()])
    address = StringField('address',validators=[InputRequired()])
    town = StringField('town',validators=[InputRequired()])

    submit = SubmitField('submit')
    def validate_studentName(self,studentName):
        db = mysql.connector.connect(
        host =  database.databaseInfo["host"],
        user = database.databaseInfo["user"],
        passwd = database.databaseInfo["passwd"],
        database = database.databaseInfo["database"]
    )
        cursor = db.cursor()
        cursor.execute('SELECT * FROM students WHERE(studentname = "%s" AND parentemail = "%s")'%(studentName.data, self.email.data))
        student = cursor.fetchone()
        if(student):
            print("ffdsa")
            raise ValidationError('student exists')


#edit students
class editStudentsForm(FlaskForm):
    studentName = StringField('studentName', validators=[InputRequired()])
    parentName = StringField('parentName', validators=[InputRequired()])
    birthday = StringField('birthday',validators=[InputRequired()])
    parentPhone = IntegerField('parentPhone',validators=[InputRequired()])
    email = StringField('email',validators=[InputRequired(),Email()])
    address = StringField('address',validators=[InputRequired()])
    town = StringField('town',validators=[InputRequired()])
    submit = SubmitField('submit')



#insert/edit users
class userForm(FlaskForm):
    username = StringField('username', validators=[InputRequired()])
    address = StringField('address', validators=[InputRequired()])
    town = StringField('town', validators=[InputRequired()])
    phone = IntegerField('phone',validators=[InputRequired()])
    password = PasswordField('password', validators=[InputRequired(),EqualTo('confirm')])
    confirm = PasswordField('confirmPassword')
    name = StringField('name',validators=[InputRequired()])
    code = IntegerField('code',validators=[InputRequired()])
    submit = SubmitField('submit')

    def validate_username(self,username):
        db = mysql.connector.connect(
        host =  database.databaseInfo["host"],
        user = database.databaseInfo["user"],
        passwd = database.databaseInfo["passwd"],
        database = database.databaseInfo["database"]
    )
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE(username = %s)'%('"'+username.data+'"'))
        account = cursor.fetchone()
        print("asdf")
        if(account):
            print("ffdsa")
            raise ValidationError('email exists')



class editusersForm(FlaskForm):
    username = StringField('address', validators=[InputRequired()])
    address = StringField('address', validators=[InputRequired()])
    town = StringField('town', validators=[InputRequired()])
    phone = IntegerField('phone',validators=[InputRequired()])
    name = StringField('name',validators=[InputRequired()])
    code = IntegerField('code',validators=[InputRequired()])
    submit = SubmitField('submit')

    def validate_code(self):
        db = mysql.connector.connect(
        host =  database.databaseInfo["host"],
        user = database.databaseInfo["user"],
        passwd = database.databaseInfo["passwd"],
        database = database.databaseInfo["database"]
    )
        cursor = db.cursor()
        cursor.execute('SELECT username FROM users WHERE(usercode = %s)'%(self.code))
        account = cursor.fetchone()
        if(account):
            if(account[0] != self.username):
                raise ValidationError('Code Already Taken')




class changePasswordForm(FlaskForm):
    password = PasswordField('password', validators=[InputRequired()])
    newPassword = PasswordField('newPassword',validators=[InputRequired()])
    submit = SubmitField('submit')

class RequestResetForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(),Email()])
    submit = SubmitField('submit')

class testForm(FlaskForm):
    username = StringField('username',validators=[InputRequired()])
    submit = SubmitField('submit')