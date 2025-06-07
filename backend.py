from flask import Flask, request, jsonify, send_from_directory
from flask import render_template, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import json
import difflib

# Load the custom chatbot dataset
with open('vitamind_dataset.json', 'r', encoding='utf-8') as f:
    chatbot_dataset = json.load(f)


app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(10))  # 'user' or 'admin'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



load_dotenv()



def mental_health_chatbot(user_input):
    user_input = user_input.lower()
    selected_reason = session.get('reason', None)
    best_match = None
    highest_ratio = 0.0

    for entry in chatbot_dataset:
         # Only compare entries with the matching reason
        if entry.get('reason') != selected_reason:
            continue

        dataset_input = entry['user_input'].lower()
        ratio = difflib.SequenceMatcher(None, user_input, dataset_input).ratio()

        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = entry['bot_reply']

    # If no good match, send default empathetic message
    if highest_ratio < 0.4:
        return "Saya faham perasaan awak tu... Cerita sikit lagi, saya sedia nak dengar dan bantu ikut kemampuan saya 😊"

    return best_match



@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Mesej pengguna diperlukan"}), 400


    bot_response = mental_health_chatbot(user_message)
    return jsonify({"response": bot_response})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


    import os
    


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        admin_username = 'srhfqh'
        role = 'admin' if username == admin_username else 'user'
        
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('reason_selection'))
        return 'Login failed'
    return render_template('login.html')


from flask import session

@app.route('/reason_selection', methods=['GET', 'POST'])
@login_required
def reason_selection():
    if request.method == 'POST':
        # get selected reason from form button
        selected_reason = request.form.get('reason')
        if selected_reason:
            # save reason in user session
            session['reason'] = selected_reason
            return redirect(url_for('chat_page'))  # your chat page route
    return render_template('reason_selection.html')


@app.route('/chat')
@login_required
def chat_page():
    reason = session.get('reason', None)
    # you can pass the reason to your chat page template
    return render_template('chat.html', reason=reason)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('reason_selection'))
    return render_template('admin_dashboard.html')

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
