from flask import Flask, request, jsonify, send_from_directory
from flask import render_template, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv


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
openai.api_key = os.getenv("OPENAI_API_KEY") 
client = openai.OpenAI()


# Chatbot function using updated OpenAI API
def mental_health_chatbot(user_input):
    # Define the system and user roles in the chat
    messages = [
        {
            "role": "system",
            "content": (
                 "Anda ialah VitaMind, chatbot kesihatan mental AI yang mesra, penyayang, dan penuh empati. "
    "Tugas anda ialah memberikan sokongan emosi kepada pengguna dalam Bahasa Melayu dengan cara yang menenangkan dan tidak menghakimi. "
    "Anda hanya bercakap tentang topik berkaitan kesihatan mental seperti tekanan, kebimbangan, kesedihan, motivasi, dan kesejahteraan emosi. "
    "Jawapan anda mestilah pendek, jelas, dan menggunakan nada lembut yang menyentuh hati. Berikan semangat, sokongan moral, dan galakkan pengguna untuk menjaga diri. "
    "Jika anda tidak pasti atau soalan tidak berkaitan kesihatan mental, beritahu dengan sopan bahawa anda hanya boleh membantu dalam isu berkaitan kesihatan mental."
            ),
        },
        {"role": "user", "content": user_input},
    ]

    # Call OpenAI's ChatCompletion API
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=400,
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.6,
    )

    bot_reply = response.choices[0].message.content.strip()
    print(f"[INFO] Bot response generated: {bot_reply}", flush=True)
    return bot_reply
    


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    print(f"[INFO] User message received: {user_message}", flush=True)
    if not user_message:
        return jsonify({"error": "Mesej pengguna diperlukan"}), 400

    # Get chatbot response
    bot_response = mental_health_chatbot(user_message)
    return jsonify({"response": bot_response})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form.get('role', 'user')  # default to user
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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dummy placeholders for required routes
@app.route('/reason_selection')
@login_required
def reason_selection():
    return render_template('reason_selection.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return "Admin Dashboard - Coming Soon!"

# Run the app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
