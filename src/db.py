from flask_sqlalchemy import SQLAlchemy
import hashlib
import datetime
import os

import bcrypt

db = SQLAlchemy()

association_table_users = db.Table(
    "association_table_users",
    db.Column("course_id", db.Integer, db.ForeignKey("course.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

association_table_friends = db.Table(
    "association_table_friends",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), index=True),
    db.Column("friend_id", db.Integer, db.ForeignKey("user.id")),
    db.UniqueConstraint("user_id", "friend_id", name="unique_friendships"))

association_table_post_members = db.Table(
    "association_table_post_members",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("post_id", db.Integer, db.ForeignKey("post.id"))
)

# your classes here
class Post(db.Model):
    """
    Has a many to one relationship with users
    Has a one to many relationship with comments
    """
    __tablename__ = "post"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    header = db.Column(db.String, nullable = False)
    body = db.Column(db.String, nullable = False)
    timestamp = db.Column(db.String, nullable = False)
    location = db.Column(db.String, nullable = True)
    meetup_time = db.Column(db.String, nullable = True)
    course = db.Column(db.String, nullable = True)
    comments = db.relationship("Comment", cascade = "delete")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable = False)
    post_attendees = db.relationship(
        "User", 
        secondary = association_table_post_members, 
        back_populates = "posts_attending"
    )

    def __init__(self, **kwargs):
        """
        Initializes a post object
        """
        self.header = kwargs.get("header")
        self.body = kwargs.get("body")
        self.timestamp = kwargs.get("timestamp")
        self.location = kwargs.get("location")
        self.meetup_time = kwargs.get("meetup_time")
        self.user_id = kwargs.get("user_id")
        self.course = kwargs.get("course")

    def serialize(self):
        """
        Serializes a post object
        """
        return {
            "id" : self.id,
            "header" : self.header,
            "body" : self.body,
            "timestamp" : self.timestamp,
            "location" : self.location,
            "meetupTime" : self.meetupTime,
            "user_id" : self.user_id,
            "course" : self.course,
            "comments" : [comment.serialize() for comment in self.comments],
            "post_attendees" : [user.simple_serialize() for user in self.post_attendees]
        }
    
    def simple_serialize(self):
        """
        Simple serializes a post object
        """
        return {
            "id" : self.id,
            "header" : self.header,
            "body" : self.body,
            "timestamp" : self.timestamp,
            "location" : self.location,
            "meetupTime" : self.meetupTime,
            "user_id" : self.user_id,
            "course" : self.course,
            "comments" : [comment.serialize() for comment in self.comments],
        }

class Comment(db.Model):
    """
    Has a many to one relationship with posts
    Has a many to one relationship with users
    """
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    body = db.Column(db.String, nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable = False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable = False)

    def __init__(self, **kwargs):
        """
        Initializes a comment object
        """
        self.body = kwargs.get("body")
        self.user_id = kwargs.get("user_id")
        self.post_id = kwargs.get("post_id")

    def serialize(self):
        """
        Serializes a comment object
        """
        return {
            "body" : self.body,
            "user_id" : self.user_id,
            "post_id" : self.post_id
        }
    

class Course(db.Model):
    """
    Has a many to many relationship with users
    """
    __tablename__ = "course"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    code = db.Column(db.Integer, nullable = False)
    name = db.Column(db.String, nullable = False)
    users = db.relationship("User", secondary = association_table_users, back_populates = "courses")

    def __init__(self, **kwargs):
        """
        Initializes a course object
        """
        self.code = kwargs.get("code", 0)
        self.name = kwargs.get("name", "")

    def serialize(self):
        """
        Serializes a course object
        """
        return {
            "id" : self.id,
            "code" : self.code,
            "name" : self.name,
            "users" : [user.simple_serialize() for user in self.users]
        }
    
    def simple_serialize(self):
        """
        Serializes a course object without the users field
        """
        return {
            "id" : self.id,
            "code" : self.code,
            "name" : self.name
        }

class User(db.Model):
    """
    Has a one to many and many to many relationship with posts
    Has a one to many relationship with comments
    Has a many to many relationship with courses
    """
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    #User information
    username = db.Column(db.String, nullable = False, unique = True)
    password_digest = db.Column(db.String, nullable=False)

    #Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    name = db.Column(db.String, nullable = True)
    bio = db.Column(db.String, nullable = True)
    grad_year = db.Column(db.Integer, nullable = True)
    picture_id = db.Column(db.String, nullable = False)
    number = db.Column(db.String, nullable = True)
    posts = db.relationship("Post", cascade = "delete")
    comments = db.relationship("Comment", cascade = "delete")
    courses = db.relationship("Course", secondary = association_table_users, back_populates = "users")
    posts_attending = db.relationship("Post", 
        secondary = association_table_post_members, 
        back_populates = "post_attendees")
    friends = db.relationship("User",
        secondary=association_table_friends,
        primaryjoin=id==association_table_friends.c.user_id,
        secondaryjoin=id==association_table_friends.c.friend_id
    )

    def __init__ (self, **kwargs):
        """
        Initializes a User object
        """
        self.username = kwargs.get("username")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.renew_session()
        self.name = kwargs.get("name")
        self.bio = kwargs.get("bio")
        self.grad_year = kwargs.get("grad_year")
        self.picture_id = kwargs.get("picture_id")
        self.number = kwargs.get("number")

    def serialize(self):
        """
        Serializes a User object
        """
        return {
            "id" : self.id,
            "username" : self.username,
            "name" : self.name,
            "bio" : self.bio,
            "grad_year" : self.grad_year,
            "picture_id" : self.picture_id,
            "number" : self.number,
            "posts" : [post.serialize() for post in self.posts],
            "comments" : [comment.serialize() for comment in self.comments],
            "courses" : [c.simple_serialize() for c in self.courses],
            "posts_attending" : [post.simple_serialize() for post in self.posts_attending],
            "friends" : [f.simple_serialize() for f in self.friends],
            "session_token": self.session_token,
            "session_expiration" : str(self.session_expiration),
            "update_token" : self.update_token
        }

    def simple_serialize(self):
        """
        Serializes a User object without courses and without posts
        """
        return {
            "id" : self.id,
            "username" : self.username,
            "name" : self.name,
            "bio" : self.bio,
            "grad_year" : self.grad_year,
            "picture_id" : self.picture_id,
            "number" : self.number,
            "comments" : [comment.serialize() for comment in self.comments]
        }

    def befriend(self, friend):
        if friend not in self.friends:
            self.friends.append(friend)
            friend.friends.append(self)

    def unfriend(self, friend):
        if friend in self.friends:
            self.friends.remove(friend)
            friend.friends.remove(self)
    
    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token

