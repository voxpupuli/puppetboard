from puppetboard.core import get_app
from flask_sqlalchemy import SQLAlchemy
import datetime


app = get_app()
db = SQLAlchemy(app)


class Users(db.Model):
    created = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    modified = db.Column(db.DateTime, default=datetime.datetime.now,
                         onupdate=datetime.datetime.now, nullable=False)
    id = db.Column(db.Integer, unique=True, primary_key=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return '{}/{}/{}'.format(self.id, self.username, self.password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id
