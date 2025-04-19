import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuration ---
app = Flask(__name__)
# IMPORTANT: Change this to a random, secret value in a real application!
# You can generate one using: python -c 'import os; print(os.urandom(24))'
app.config['SECRET_KEY'] = 'your_very_secret_and_random_key_here'
app.config['DATA_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to '/login' if @login_required fails
login_manager.login_message_category = 'info' # Bootstrap class for flash message

# --- User Model (Simplified - In-memory/JSON) ---
# In a real app, use a database! For simplicity, we store one user here.
# You could expand this to load from a users.json file.
# To generate a hash: print(generate_password_hash('your_password', method='pbkdf2:sha256'))
hashed_password = 'pbkdf2:sha256:1000000$iO0PT22lkPdEPbIg$882687fb051530224eeb782781e4fed8fcd7d31bec625df282f87ba13c7c53d5' # PASTE YOUR HASHED PASSWORD HERE

users = {
    'admin': { # Username
        'password_hash': hashed_password,
        'id': '1' # Must be a string for Flask-Login
        }
}

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        # Normally query a database here
        for username, data in users.items():
             if data['id'] == user_id:
                 return User(data['id'], username, data['password_hash'])
        return None

    @staticmethod
    def get_by_username(username):
        if username in users:
            data = users[username]
            return User(data['id'], username, data['password_hash'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Helper Functions ---
def load_json_data(filename):
    """Loads data from a JSON file in the data folder."""
    filepath = os.path.join(app.config['DATA_FOLDER'], filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None # Or return default structure like [] or {}
    except json.JSONDecodeError:
        flash(f"Error decoding JSON from {filename}", "danger")
        return None # Or default

def save_json_data(filename, data):
    """Saves data to a JSON file in the data folder."""
    filepath = os.path.join(app.config['DATA_FOLDER'], filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        flash(f"Error saving data to {filename}: {e}", "danger")
        return False

# --- Routes ---
@app.route('/')
def index():
    """Displays the main CV page."""
    user_info = load_json_data('user_info.json') or {}
    experience = load_json_data('experience.json') or []
    education = load_json_data('education.json') or []
    skills = load_json_data('skills.json') or []
    projects = load_json_data('projects.json') or []

    # Only keep the first project per category
    seen_categories = set()
    unique_projects = []
    for project in projects:
        category = project.get('category')
        if category and category not in seen_categories:
            unique_projects.append(project)
            seen_categories.add(category)

    return render_template('index.html',
                           user_info=user_info,
                           experience=experience,
                           education=education,
                           skills=skills,
                           projects=unique_projects)
    
    

    
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('manage_projects'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.get_by_username(username)

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash('Logged in successfully!', 'success')
            # Redirect to the page they were trying to access, or manage_projects
            next_page = request.args.get('next')
            return redirect(next_page or url_for('manage_projects'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logs the user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))





from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




@app.route('/manage_projects', methods=['GET', 'POST'])
@login_required
def manage_projects():
    projects = load_json_data('projects.json') or []

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            title = request.form.get('project_title')
            url = request.form.get('project_url')
            description = request.form.get('project_description')
            cover = request.form.get('project_cover')
            category = request.form.get('project_category')
            file = request.files.get('project_cover_file')
            
            
                    # If a file was uploaded and it's valid
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                cover = file_path  # Overwrite URL with uploaded file path

            action = request.form.get('action')
            index = request.form.get('project_index')


            if not title or not description:
                flash('Project Title and Description are required.', 'warning')
            else:
                projects.append({
                    "title": title,
                    "url": url or "#",
                    "description": description,
                    "cover": cover,
                    "category": category
                })
                if save_json_data('projects.json', projects):
                    flash('Project added successfully!', 'success')
                return redirect(url_for('manage_projects'))

        elif action == 'delete':
            index = int(request.form.get('project_index'))
            if 0 <= index < len(projects):
                deleted = projects.pop(index)
                if save_json_data('projects.json', projects):
                    flash(f"Deleted project: {deleted['title']}", 'info')
            return redirect(url_for('manage_projects'))

        elif action == 'edit':
            index = int(request.form.get('project_index'))
            if 0 <= index < len(projects):
                projects[index] = {
                    "title": request.form.get('project_title'),
                    "url": request.form.get('project_url'),
                    "description": request.form.get('project_description'),
                    "cover": request.form.get('project_cover'),
                    "category": request.form.get('project_category')
                }
                if save_json_data('projects.json', projects):
                    flash('Project updated successfully!', 'success')
            return redirect(url_for('manage_projects'))
    # PAGINATION logic
    page = int(request.args.get('page', 1))
    per_page = 1
    total_projects = len(projects)
    total_pages = (total_projects + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    projects_paginated = projects[start:end]

    return render_template('manage_projects.html',
                           projects=projects_paginated,
                           current_page=page,
                           total_pages=total_pages)

@app.route('/category/<category>')
def view_category(category):
    """Displays all projects in the given category with pagination."""
    projects = load_json_data('projects.json') or []

    # Filter the projects by category
    filtered_projects = [p for p in projects if p.get('category') == category]

    # Pagination logic
    page = int(request.args.get('page', 1))
    per_page = 2  # adjust for 3 per row, 2 rows
    total_projects = len(filtered_projects)
    total_pages = (total_projects + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_projects = filtered_projects[start:end]

    return render_template('category.html',
                           category=category,
                           projects=paginated_projects,
                           current_page=page,
                           total_pages=total_pages)


@app.route('/project/<int:project_index>')
def project_detail(project_index):
    projects = load_json_data('projects.json') or []

    if 0 <= project_index < len(projects):
        project = projects[project_index]
        return render_template('project_detail.html', project=project)
    else:
        flash('Project not found.', 'danger')
        return redirect(url_for('index'))


# --- Run the App ---
if __name__ == '__main__':
    print(generate_password_hash("your_password_here", method='pbkdf2:sha256'))

 
    app.run(host='0.0.0.0', port=5000, debug=True)
