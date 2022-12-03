import json
import os
from datetime import datetime
import users_dao

#Cronjob libaries
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger

#Twilio third-party libary
from twilio.rest import Client

from flask import Flask
from flask import request

from db import db
from db import Course
from db import User
from db import Comment
from db import Post

app = Flask(__name__)
db_filename = "study.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

def run_text_notifications():
    """
    Sends text notifications to users depending on the current day
    """
    #Setting up the Twilio Service
    account_sid = "AC422d815a50767c353c6ab06fd0d1a21d"#os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = "463ec71ce398facc3af7a96c79bd6bde"#os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    #Getting all of the posts that need have messages sent to
    posts = Post.query.all()

    #Sending messages to users of posts that are scheduled on the same weekday
    for post in posts:
        time = datetime.strptime(post.meetupTime, "%m.%d.%y %H:%M:%S")
        if time.weekday() == datetime.today().weekday():
            users = post.post_attendees
            for user in users:
                message = client.messages \
                        .create(
                            body="Hi " + user.name +"! You have a study session today at " + str(time.time()) + ".",
                            from_='+13608032457',
                            to= user.number
                        )
                print(message.sid)

db.init_app(app)
with app.app_context():
    #db.drop_all()
    db.create_all()

    #Adding some preset courses at Cornell
    courses_file = open("courses.txt", "r")
    data = courses_file.read() 
    data_into_list = data.split("\n")
    courses_file.close()

    for i in range(0, len(data_into_list), 2):
        temp_code = data_into_list[i]
        temp_name = data_into_list[i+1]
        new_course = Course(
            code = temp_code, 
            name = temp_name
        )
        db.session.add(new_course)
    db.session.commit()

    #Scheduling text notifications to be run at midnight every weekday
    run_text_notifications()
    scheduler = BackgroundScheduler()
    trigger = OrTrigger([CronTrigger(day_of_week='sun', hour=0, minute= 0),
                     CronTrigger(day_of_week='mon', hour=0, minute = 0),
                     CronTrigger(day_of_week='tue', hour=0, minute = 0),
                     CronTrigger(day_of_week='wed', hour=0, minute = 0),
                     CronTrigger(day_of_week='thu', hour=0, minute = 0),
                     CronTrigger(day_of_week='fri', hour=0, minute = 0),
                     CronTrigger(day_of_week='sat', hour=0, minute = 0)])
    scheduler.add_job(run_text_notifications, trigger)
    scheduler.start()   

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

    new_user = User(
        username = username, 
        password = password,
        picture_id = "default"
    )
    db.session.add(new_user)
    db.session.commit()

    return success_response(new_user.serialize())

@app.route("/api/users/<int:user_id>/", methods = ["POST"])
def update_user(user_id):
    """
    Endpoint for updating the information for a user
    """
    body = json.loads(request.data)
    user = User.query.filter_by(id = user_id).first()

    if user is None:
        return json.dumps({"error" : "User does not exist"}), 404

    user.name = body.get("name", user.name)
    
    user.bio = body.get("bio", user.bio)

    user.grad_year = body.get("grad_year", user.grad_year)

    user.number = body.get("number", user.number)
    db.session.commit()
    return json.dumps(user.serialize()), 200

@app.route("/api/users/<int:user_id>/picture/", methods = ["POST"])
def update_picture(user_id):
    """
    Endpoint for updating a picture
    """
    body = json.loads(request.data)
    user = User.query.filter_by(id = user_id).first()

    if user is None:
        return json.dumps({"error" : "User does not exist"}), 404
    
    user.picture_id = body.get("picture_id", "default")

    db.session.commit()
    return json.dumps(user.serialize()), 200

@app.route("/api/users/<int:user_id>/")
def get_user(user_id):
    """
    Endpoint for getting a user by id
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error":"User not found!"}), 404

    return json.dumps(user.serialize()), 200

@app.route("/api/users/login/", methods=["POST"])
def login():
    """
    Endpoint for logging in a user
    """
    body = json.loads(request.data)
    username = body.get("username")
    password = body.get("password")

    if username is None or password is None:
        return failure_response("Missing username or password", 400)
    
    success, user = users_dao.verify_credentials(username, password)

    if not success:
        return failure_response("Incorrect username or password", 401)

    return success_response(user.serialize())

@app.route("/api/users/session/", methods=["POST"])
def update_session():
    """
    Endpoint for updating a user's session
    """
    success, update_token = extract_token(request)

    success_user, user = users_dao.renew_session(update_token)

    if not success_user:
        return failure_response("Invalid update token", 400)

    return success_response(user.serialize())

@app.route("/api/users/logout/", methods=["POST"])
def logout():
    """
    Endpoint for logging out a user
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)

    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)

    user.session_token = ""
    user.session_expiration = datetime.now()
    user.update_token = ""
    db.session.commit()

    return success_response({"message" : "You have successfully logged out"})

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
    db.session.commit()
    user = User.query.filter_by(id = user_id).first()
    return json.dumps(user.serialize()), 200

@app.route("/api/users/<int:user_id>/add/post/", methods = ["POST"])
def create_post_for_user(user_id):
    """
    Endpoint for creating a post for a user, requires authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
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
    course = body.get("course")
    if course is None:
        return json.dumps({"error" : "Course not found!"}), 400

    new_post = Post(
        header = header, 
        body = post_body, 
        timestamp = timestamp, 
        location = location, 
        meetup_time = meetup_time,
        user_id = user_id,
        course = course
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

@app.route("/api/posts/<int:post_id>/attend/<int:user_id>/", methods = ["POST"])
def user_attend_post(post_id, user_id):
    """
    Endpoint for having a user attend a post
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
    post = Post.query.filter_by(id = post_id).first()
    if post is None:
        return json.dumps({"error": "Post does not exist!"}), 404
    
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User does not exist!"}), 404
    
    post.post_attendees.append(user)
    db.session.commit()
    post = Post.query.filter_by(id = post_id).first()
    return json.dumps(post.serialize()), 200

@app.route("/api/posts/<int:post_id>/add/", methods = ["POST"])
def create_comment_for_post(post_id):
    """
    Endpoint for creating a comment for a post, requires authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
    post = Post.query.filter_by(id = post_id).first()
    if post is None:
        return json.dumps({"error": "Post does not exist!"}), 404
    
    body = json.loads(request.data)
    user_id = body.get("user_id")
    if user_id is None:
        return json.dumps({"error" : "User id not found!"}), 400
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User does not exist!"}), 404

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
    Endpoint for getting all the comments under a post, requires authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
    Comments = [comment.serialize() for comment in Comment.query.filter_by(post_id = post_id)]
    return json.dumps({"comments" : Comments}), 200
    
@app.route("/api/users/<int:user_id>/friend/<int:friend_id>/", methods = ["POST"])
def friend_user(user_id, friend_id):
    """
    Endpoint for friending two users, requires authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User not found!"})
    
    friend = User.query.filter_by(id = friend_id).first()
    if friend is None:
        return json.dumps({"error" : "Friend not found!"})
    
    user.befriend(friend)
    db.session.commit()
    return json.dumps(user.serialize()), 200

@app.route("/api/users/<int:user_id>/unfriend/<int:friend_id>/", methods = ["POST"])
def unfriend_user(user_id, friend_id):
    """
    Endpoint for unfriending two users, requires authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return failure_response("Could not extract session token", 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return json.dumps({"error" : "User not found!"})
    
    friend = User.query.filter_by(id = friend_id).first()
    if friend is None:
        return json.dumps({"error" : "Friend not found!"})
    
    user.unfriend(friend)
    db.session.commit()
    return json.dumps(user.serialize()), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
