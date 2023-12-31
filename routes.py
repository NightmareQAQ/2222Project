from flask import (Flask, render_template, url_for, flash, redirect, request,
                   abort)
from flask_login import (login_user, current_user, logout_user,
                         login_required, LoginManager)
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config['SECRET_KEY'] = '1234567890'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)  # Add this line
rooms = {}  # Add this line

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# FIXME: USE FLASK BLUEPRINT MAYBE
from forms import (RegistrationForm, LoginForm, UpdateAccountForm, PostForm,
                   CommentForm)
from models import User, Post, Comment
from utils import save_image
from admin import ModelViewControl

admin = Admin(app)
admin.add_view(ModelViewControl(User, db.session))
admin.add_view(ModelViewControl(Post, db.session))
admin.add_view(ModelViewControl(Comment, db.session))


# SECTION: MAIN ROUTES
@app.route("/")
def index():
    return render_template("index.jinja")
@app.route("/root")
def root():
    return render_template("index.jinja")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('home.html', title='home', posts=posts)


@app.route("/users")
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.date_created.desc()) \
        .paginate(page=page, per_page=10)
    return render_template('users.html', title='users', users=users)


@app.route("/category/<string:category>")
def category(category):
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(category=category) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=10)
    return render_template('category.html',
                           title='category: <string:category', posts=posts)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account has been created! You can now log in', 'success')
    return render_template('register.html', title='register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user.role == 'banned':
            flash('This account has been banned', 'danger')
        elif user:
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('home'))
        else:
            flash('Login failed, please check email and password', 'danger')
    return render_template('login.html', title='login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.image.data:
            image_file = save_image(form.image.data)
            current_user.prof_pic = image_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.description = form.description.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.description.data = current_user.description
    image_file = url_for('static',
                         filename='prof_pics/' + current_user.prof_pic)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            user_post=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('new_post.html', title='new post',
                           form=form, legend='New Post')


@app.route("/post/<string:post_id>/view", methods=['GET', 'POST'])
def view_post(post_id):
    page = request.args.get('page', 1, type=int)
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_comment=post) \
        .order_by(Comment.time_posted.desc()) \
        .paginate(page=page, per_page=10)
    return render_template('view_post.html', title=post.title,
                           post=post, comments=comments)


@app.route("/post/<int:post_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_post != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.category = form.category.data
        db.session.commit()
        flash('Your post has been edited!', 'success')
        return redirect(url_for('view_post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.category.data = post.category
    return render_template('new_post.html', title='Edit Post',
                           form=form, legend='Edit Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_post != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/post/<int:post_id>/status", methods=['GET', 'POST'])
@login_required
def lock_unlock_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_post != current_user:
        abort(403)
    if post.status == 'unlock':
        post.status = 'locked'
        flash('Your post has been Locked!', 'success')
    else:
        post.status = 'unlock'
        flash('Your post has been Unlocked!', 'success')
    db.session.commit()
    return redirect(url_for('view_post', post_id=post.id))


@app.route("/comment/<int:post_id>/new", methods=['GET', 'POST'])
@login_required
def new_comment(post_id):
    post = Post.query.get_or_404(post_id)
    if post.status == 'locked':
        abort(403)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            post_comment=post,
            user_comment=current_user)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been created!', 'success')
        return redirect(url_for('view_post', post_id=post.id))
    return render_template('new_comment.html', title='Comment',
                           form=form, legend='Post comment')


@app.route("/view_user/<string:username>")
def view_user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('view_user.html', title='view_user', user=user)


@app.route("/view_user/<string:username>/posts")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_post=user) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', title='user_posts', user=user,
                           posts=posts)


@app.route("/view_user/<string:username>/comments")
def user_comments(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    comments = Comment.query.filter_by(user_comment=user) \
        .order_by(Comment.time_posted.desc()) \
        .paginate(page=page, per_page=10)
    return render_template('user_comments.html', title='user_comments',
                           user=user, comments=comments)


# SECTION: ERRORHANDLER
@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html'), 500


def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/chat", methods=["POST", "GET"])
def c2():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("c2.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("c2.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("c2.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("c2.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("c2"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

@app.route("/about")
def about():
    return render_template('about.jinja', title='About')
