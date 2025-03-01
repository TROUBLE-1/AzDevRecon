from AzDevRecon import db, login_manager
from flask_login import UserMixin
from sqlalchemy.sql import expression
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get((user_id))
 
class User(db.Model, UserMixin):
    id = db.Column(db.String(), primary_key=True)
    username = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(100))


class AccessTokenSubmission(db.Model):
    __tablename__ = 'access_token_submissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(), nullable=False)
    token = db.Column(db.String(), nullable=False)
    organization_name = db.Column(db.String(), nullable=False)

    def __repr__(self):
        return f"<AccessTokenSubmission id={self.id} organization_name={self.organization_name}>"    