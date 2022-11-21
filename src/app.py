import json
import os
from datetime import datetime


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
    db.create_all()

# generalized response formats
def success_response(data, code=200):
    """
    Generalized success response function
    """
    return json.dumps(data), code

def failure_response(message, code=404):
    """
    Generalized failure response function
    """
    return json.dumps({"error": message}), code

def extract_token(request):
    """
    Helper function that extracts the token from the header of a request
    """
    auth_header = request.headers.get("Authorization")
    
    if auth_header is None:
        return False, failure_response("Missing authorization header.", 400)

    # Header looks like "Authorization : Bearer <token>"
    bearer_token = auth_header.replace("Bearer ", "").strip()

    if bearer_token is None or not bearer_token:  #HUUUH
        return False, failure_response("Invalid authorization header", 400)
    return True, bearer_token

# your routes here
@app.route("/api/courses/")
def get_courses():
    """
    Endpoint for getting all courses
    """
    Courses = [course.serialize() for course in Course.query.all()]
    return json.dumps({"courses" : Courses}), 200

@app.route("/api/courses/", methods = ["POST"])
def create_course():
    """
    Endpoint for creating a course
    """
    body = json.loads(request.data)
    code = body.get("code")
    if code is None:
        return json.dumps({"error" : "Code not found!"}), 400
    name = body.get("name")
    if name is None:
        return json.dumps({"error" : "Name not found!"}), 400
    new_course = Course(
        code = code, 
        name = name
    )
    db.session.add(new_course)
    db.session.commit()
    return json.dumps(new_course.serialize()), 201

@app.route("/api/courses/<int:course_id>/")
def get_course(course_id):
    """
    Endpoint for getting a course by id
    """
    course = Course.query.filter_by(id = course_id).first()
    if course is None:
        return json.dumps({"error": "Course not found!"}), 404

    return json.dumps(course.serialize()), 200

@app.route("/api/courses/<int:course_id>/", methods = ["DELETE"])
def delete_course(course_id):
    """
    Endpoint for deleting a task by id
    """
    course = Course.query.filter_by(id = course_id).first()
    if course is None:
        return json.dumps({"error" : "Course not found!"}), 404
    
    db.session.delete(course)
    db.session.commit()
    return json.dumps(course.serialize()), 200

@app.route("/api/users/")
def get_users():
    """
    Endpoint for getting all users
    """
    Users = [user.serialize() for user in User.query.all()]
    return json.dumps({"users" : Users}), 200

@app.route("/api/users/", methods = ["POST"])
def create_user():
    """
    Endpoint for creating a new user
    """
    body = json.loads(request.data)
    username = body.get("username")
    if username is None:
        return json.dumps({"error" : "Username not found!"}), 400
    
    user = User.query.filter_by(username = username).first()
    if user is not None:
        return json.dumps({"error" : "Username already exists!"}), 400


    password = body.get("password")
    if password is None:
        return json.dumps({"error": "Password not found!"}), 400
    
    name = body.get("name")
    if name is None:
        return json.dumps({"error" : "Name not found!"}), 400
    bio = body.get("bio")
    # if bio is None:
    #     return json.dumps({"error" : "Bio not found!"}), 400
    gradYear = body.get("gradYear")
    if gradYear is None:
        return json.dumps({"error" : "Graduation year not found!"}), 400
    new_user = User(
        username = username, 
        name = name, 
        bio = bio, 
        gradYear = gradYear,
        password = password
    )
    db.session.add(new_user)
    db.session.commit()
    return json.dumps(new_user.serialize()), 201

@app.route("/api/users/<int:user_id>/")
def get_user(user_id):
    """
    Endpoint for getting a user by id
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error":"User not found!"}), 404

    return json.dumps(user.serialize()), 200

@app.route("/api/users/<int:user_id>/add/course/", methods = ["POST"])
def add_course_to_user(user_id):
    """
    Endpoint for adding a course to a user
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User not found!"}), 404
    body = json.loads(request.data)
    course_id = body.get("course_id")

    course = Course.query.filter_by(id = course_id).first()
    if course is None:
        return json.dumps({"error" : "Course does not exist!"}), 404
    
    user.courses.append(course)
    #course.users.append(user)
    db.session.commit()
    user = User.query.filter_by(id = user_id).first()
    return json.dumps(user.serialize()), 200

@app.route("/api/users/<int:user_id>/add/post/", methods = ["POST"])
def create_post_for_user(user_id):
    """
    Endpoint for creating a post for a user
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User not found!"}), 404

    
    body = json.loads(request.data)
    header = body.get("header")
    if header is None:
        return json.dumps({"error" : "Header not found!"}), 400
    post_body = body.get("body")
    if post_body is None:
        return json.dumps({"error" : "Body not found!"}), 400
    timestamp = str(datetime.now())
    location = body.get("location")
    if location is None:
        return json.dumps({"error" : "Location not found!"}), 400
    meetup_time = body.get("meetup_time")
    if meetup_time is None:
        return json.dumps({"error" : "Meetup time not found!"}), 400

    new_post = Post(
        header = header, 
        body = post_body, 
        timestamp = timestamp, 
        location = location, 
        meetupTime = meetup_time,
        user_id = user_id
    )

    db.session.add(new_post)
    db.session.commit()
    return json.dumps(new_post.serialize()), 201

@app.route("/api/posts/")
def get_posts():
    """
    Endpoint for getting all posts
    """
    Posts = [post.serialize() for post in Post.query.all()]
    return json.dumps({"posts" : Posts}), 200

@app.route("/api/posts/<int:post_id>/add/", methods = ["POST"])
def create_comment_for_post(post_id):
    """
    Endpoint for creating a comment for a post
    """
    post = Post.query.filter_by(id = post_id).first()
    if post is None:
        return json.dumps({"error": "Post does not exist"}), 404
    
    body = json.loads(request.data)
    user_id = body.get("user_id")
    if user_id is None:
        return json.dumps({"error" : "User id not found!"}), 400
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User does not exist"}), 404

    commentBody = body.get("body")
    if commentBody is None:
        return json.dumps({"error" : "Comment body not found!"}), 400

    new_comment = Comment(
        body = commentBody,
        user_id = user_id,
        post_id = post_id
    )

    db.session.add(new_comment)
    db.session.commit()
    return json.dumps(new_comment.serialize()), 201

@app.route("/api/posts/<int:post_id>/")
def get_comments_for_post(post_id):
    """
    Endpoint for getting all the comments under a post
    """
    Comments = [comment.serialize() for comment in Comment.query.filter_by(post_id = post_id)]
    return json.dumps({"comments" : Comments}), 200
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
