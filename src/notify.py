import json
import os
from datetime import datetime
import users_dao


from db import db
from flask import Flask
from flask import request
from db import Course
from db import User
from db import Comment
from db import Post

app = Flask(__name__)
db_filename = "study.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    #db.drop_all()
    db.create_all()