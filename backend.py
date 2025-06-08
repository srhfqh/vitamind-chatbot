from flask import Flask, request, jsonify, send_from_directory
from flask import render_template, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file
import json
import difflib
from datetime import datetime


with open('vitamind_dataset.json', 'r', encoding='utf-8') as f:
    chatbot_dataset = json.load(f)


app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.environ.get('SECRET_KEY', 'vitamind_default_secret_key')
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reason = db.Column(db.String(100))
    message = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


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



@app.route('/chat_api', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Mesej pengguna diperlukan"}), 400


    bot_response = mental_health_chatbot(user_message)
    return jsonify({"response": bot_response})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/start_chat', methods=['POST'])
@login_required
def start_chat():
    reason = request.form.get('reason')
    session['reason'] = reason
    return redirect(url_for('chat'))




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            raw_password = request.form['password']
            hashed_password = generate_password_hash(raw_password)

          
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return "Nama pengguna sudah wujud. Sila guna nama lain."

            
            if username.lower() == 'adminvitamind': 
                role = 'admin'
            else:
                role = 'user'

           
            new_user = User(username=username, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()

            print("✅ User registered:", username, "Role:", role)

            return redirect(url_for('login'))

        except Exception as e:
            print("🚨 Registration Error:", e, flush=True)
            return "Telah berlaku ralat semasa pendaftaran. Sila cuba lagi.", 500

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            print(f"📥 Trying login: username={username}, password={password}")

            user = User.query.filter_by(username=username).first()
            print(f"🔍 DB user: {user}")

            if user:
                print(f"User entered password: {password}")
                print(f"🧂 Hashed password in DB: {user.password}")
                print(f"✅ Password match: {check_password_hash(user.password, password)}")

            if user and check_password_hash(user.password, password):
                user.last_login = datetime.now()
                db.session.commit()
                login_user(user)
                print(f"✅ Login success: {user.username}, role={user.role}")
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('reason_selection'))
            else:
                print("❌ Login failed: Invalid username or password", flush=True)

        except Exception as e:
            print(f"🚨 Error during login: {e}", flush=True)

        return 'Ralat semasa login. Sila cuba lagi.'

    return render_template('login.html')




from flask import session

@app.route('/reason_selection', methods=['GET', 'POST'])
@login_required
def reason_selection():
    if request.method == 'POST':
        selected_reason = request.form.get('reason')
        if selected_reason:
            session['reason'] = selected_reason
            return redirect(url_for('chat_page'))  
    return render_template('reason_selection.html')


@app.route('/chat')
@login_required
def chat_page():
    reason = session.get('reason', None)
  
    return render_template('chat.html', reason=reason)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('reason_selection'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/add_dataset_entry', methods=['POST'])
@login_required
def add_dataset_entry():
    if current_user.role != 'admin':
        return redirect(url_for('reason_selection'))

    new_entry = {
        "reason": request.form.get('reason'),
        "user_input": request.form.get('user_input'),
        "bot_reply": request.form.get('bot_reply')
    }
    with open('vitamind_dataset.json', 'r+', encoding='utf-8') as f:
        data = json.load(f)
        data.append(new_entry)
        f.seek(0)
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.truncate()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export_dataset')
@login_required
def export_dataset():
    if current_user.role != 'admin':
        return redirect(url_for('reason_selection'))
    return send_file('vitamind_dataset.json', as_attachment=True)

@app.route('/admin/upload_dataset', methods=['POST'])
@login_required
def upload_dataset():
    if current_user.role != 'admin':
        return redirect(url_for('reason_selection'))

    file = request.files['dataset_file']
    if file and file.filename.endswith('.json'):
        file.save('vitamind_dataset.json')
        return redirect(url_for('admin_dashboard'))
    return "Fail tidak sah. Hanya .json dibenarkan.", 400

@app.route('/debug-users')
def debug_users():
    users = User.query.all()
    user_list = [{'id': u.id, 'username': u.username, 'role': u.role} for u in users]
    return jsonify(user_list)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



with app.app_context():
    db.create_all()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
