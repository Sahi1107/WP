import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Post, Comment, init_db, Tournament, Stats, PostLikes, Media

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sports_social.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# File upload settings
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max size for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi'}

# Initialize the database
init_db(app)
migrate = Migrate(app, db)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route: Tournaments
@app.route('/tournaments', methods=['GET', 'POST'])
@login_required
def tournaments_page():
    tournaments = Tournament.query.all()
    filtered_tournaments = tournaments
    
    if request.method == 'POST':
        sport = request.form['sport']
        region = request.form['region']
        date = request.form['date']
        
        if sport != 'all':
            filtered_tournaments = [t for t in filtered_tournaments if t.sport == sport]
        if region != 'all':
            filtered_tournaments = [t for t in filtered_tournaments if t.region == region]
        if date:
            filtered_tournaments = [t for t in filtered_tournaments if t.date >= date]
    
    return render_template('tournaments.html', tournaments=filtered_tournaments)

# Route: Stats
@app.route('/stats', methods=['GET', 'POST'])
@login_required
def stats():
    search_results = []
    
    if request.method == 'POST':
        query = request.form['query'].lower()
        search_results = Stats.query.filter(Stats.name.ilike(f'%{query}%') | Stats.team.ilike(f'%{query}%')).all()
    
    return render_template('stats.html', search_results=search_results)

# Route: Home
@app.route('/')
@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/terms')
@login_required
def terms():
    return render_template('terms.html')

# @app.route('/social')
# @login_required
# def social():
#     user_posts = Post.query.filter_by(user_id=current_user.id).all()

#     return render_template('social.html', posts=user_posts)


@app.route('/explore')
@login_required
def explore():
    return render_template('explore.html')

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

# Route: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Route: Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/social', methods=['GET', 'POST'])
@login_required
def posts():
    my_posts = request.args.get('my_posts', 'true') == 'true'

    if my_posts:
        user_posts = Post.query.filter_by(user_id=current_user.id).all()
    else:
        user_posts = Post.query.all()

    # Get the ids of posts that the current user has liked
    liked_post_ids = {like.post_id for like in PostLikes.query.filter_by(user_id=current_user.id).all()}

    if request.method == 'POST':
        file = request.files.get('media')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            media_type = 'image' if filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif')) else 'video'
            file_data = file.read()
            new_media = Media(
                user_id=current_user.id,
                filename=filename,
                media_type=media_type,
                data=file_data
            )
            db.session.add(new_media)
            db.session.commit()

            caption = request.form.get('caption')
            new_post = Post(
                user_id=current_user.id,
                username=current_user.username,
                caption=caption,
                media_id=new_media.id
            )
            db.session.add(new_post)
            db.session.commit()

        return redirect(url_for('posts', my_posts='true'))

    return render_template('social.html', posts=user_posts, current_user=current_user, liked_post_ids=liked_post_ids)


@app.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)  # Get the post or return 404 if not found

    # Check if the user has already liked this post
    existing_like = PostLikes.query.filter_by(post_id=post_id, user_id=current_user.id).first()

    if existing_like:
        # User is unliking the post
        db.session.delete(existing_like)
        post.likes -= 1  # Decrease like count
    else:
        # User is liking the post
        new_like = PostLikes(post_id=post.id, user_id=current_user.id)  # Ensure post.id is used
        db.session.add(new_like)
        post.likes += 1  # Increase like count

    db.session.commit()
    
    return jsonify({'likes': post.likes})  # Return the updated like count



@app.route('/get_users')
@login_required
def get_users():
    users = User.query.filter(User.id != current_user.id).all()  # Exclude the logged-in user
    return jsonify([{'username': user.username} for user in users])

# Route: Share a Post
@app.route('/share_post/<int:post_id>')
@login_required
def share_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.shares += 1
    db.session.commit()
    return redirect(url_for('posts'))

@app.route('/comment_post/<int:post_id>', methods=['POST'])
@login_required
def comment_post(post_id):
    comment_text = request.form.get('comment')  # Get comment text from the form
    
    if comment_text:
        new_comment = Comment(
            post_id=post_id,
            user_id=current_user.id,
            comment_text=comment_text,
            date_posted=datetime.utcnow()
        )
        db.session.add(new_comment)
        db.session.commit()
        
        # Return the new comment's data to the frontend
        return jsonify({
            'username': current_user.username,
            'comment_text': comment_text
        })
    
@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    # Fetch the post
    post = Post.query.get(post_id)
    if post:
        # Optionally delete related comments
        Comment.query.filter_by(post_id=post_id).delete()
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
    else:
        flash('Post not found.', 'error')
    return redirect(url_for('posts'))

@app.route('/media/<int:media_id>')
def media(media_id):
    media_item = Media.query.get_or_404(media_id)
    return Response(media_item.data, mimetype='image/jpeg' if media_item.media_type == 'image' else 'video/mp4')

if __name__ == '__main__':
    app.run(debug=True)
