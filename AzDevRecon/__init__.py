from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os
import psycopg2 as pg
from flask_socketio import SocketIO, emit
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(BASE_PATH , "site.db")
app = Flask(__name__)
app.config['SECRET_KEY'] = '46546@#$%&#$%yhsdrfhsdfh6@&||@^&'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

socketio = SocketIO(app, async_mode="threading")

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from AzDevRecon import routes
