from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, IntegerField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.fields.html5 import EmailField
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, IPAddress
from AzDevRecon import app, db
from AzDevRecon.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class DashboardForm(FlaskForm):
    access_token = StringField('PAT/Access Token', validators=[ DataRequired(message="Access token is required."), Length(min=10, message="Access token must be at least 10 characters long.")], render_kw={"placeholder": "PAT/Access Token"})
    organization = StringField('Organization', validators=[DataRequired()], render_kw={"placeholder": "Organization"})
    submit = SubmitField('Submit')