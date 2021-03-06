# project/server/models.py


import datetime

from flask import current_app

from project.server import db, bcrypt


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    registered_on = db.Column(db.DateTime, nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, email, password, admin=False):
        self.email = email
        self.password = bcrypt.generate_password_hash(
            password, current_app.config.get("BCRYPT_LOG_ROUNDS")
        ).decode("utf-8")
        self.registered_on = datetime.datetime.now()
        self.admin = admin

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return "<User {0}>".format(self.email)


class Document(db.Model):
    """
    Document upload by user to extract skill
    """

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_type = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(1000), nullable=False)
    created_on = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, nullable=True)  # User.id
    filename = db.Column(db.String(1000), nullable=True)
    path = db.Column(db.String(1255), nullable=True)

    def __init__(self, content_type, title, created_by, filename, path):
        self.content_type = content_type
        self.title = title
        self.created_on = datetime.datetime.now()
        self.created_by = created_by
        self.filename = filename
        self.path = path

    def get_id(self):
        return self.id

    def __repr__(self):
        return "<Document {0}>".format(self.title)

    def set_content(self, content):
        self.content = content

    def get_content(self):
        return self.content
