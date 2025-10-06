from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pickle

# ------------------- Load trained ML models -------------------
# Risk level model
model = pickle.load(open("sleep_model.pkl", "rb"))

# Disorder prediction model (new)
#disorder_model = pickle.load(open("disorder_model.pkl", "rb"))
#disorder_encoder = pickle.load(open("disorder_encoder.pkl", "rb"))

# ------------------- Flask app setup -------------------
app = Flask(__name__)
app.secret_key = "your_secret_key"

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'mysql@123'   # your MySQL password
app.config['MYSQL_DB'] = 'Sleep'

mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth'

# ------------------- User class -------------------
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(id=user[0], username=user[1], email=user[2], password=user[3])
    return None

# ------------------- Authentication -------------------
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        action = request.form['action']
        username = request.form.get('username')
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        if action == 'register':
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            try:
                cur.execute("INSERT INTO users(username, email, password) VALUES(%s,%s,%s)",
                            (username, email, hashed_pw))
                mysql.connection.commit()
                flash("Registration successful! Please log in.", "success")
            except Exception:
                flash("Error: Email already exists!", "danger")
            cur.close()
            return redirect(url_for('auth'))

        elif action == 'login':
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            if user and bcrypt.check_password_hash(user[3], password):
                login_user(User(id=user[0], username=user[1], email=user[2], password=user[3]))
                return redirect(url_for('index'))
            else:
                flash("Invalid credentials!", "danger")

    return render_template('auth.html')

# ------------------- Home -------------------
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ------------------- Add Sleep Log -------------------
@app.route('/form', methods=['GET', 'POST'])
@login_required
def form():
    if request.method == 'POST':
        log_date = request.form['log_date']
        sleep_hours = float(request.form['sleep_hours'])
        interruptions = int(request.form['interruptions'])
        tiredness = int(request.form['tiredness'])
        screen_time = int(request.form['screen_time'])

        # Predict risk using ML model
        features = [[sleep_hours, interruptions, tiredness, screen_time]]
        risk_level = model.predict(features)[0]

        # Save log
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO sleep_logs(user_id, log_date, sleep_hours, interruptions, tiredness, screen_time, risk_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (current_user.id, log_date, sleep_hours, interruptions, tiredness, screen_time, risk_level))
        mysql.connection.commit()
        cur.close()

        return render_template('form.html', message=f"✅ Log saved! Predicted Risk Level: {risk_level}")

    return render_template('form.html')

# ------------------- View Logs -------------------
@app.route('/logs')
@login_required
def logs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM sleep_logs WHERE user_id = %s ORDER BY log_date DESC", (current_user.id,))
    logs = cur.fetchall()
    cur.close()
    return render_template('logs.html', logs=logs)

# 🔹 Predict Disorder from Saved Logs
@app.route('/predict-from-logs')
@login_required
def predict_from_logs():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT sleep_hours, interruptions, tiredness, screen_time, risk_level
        FROM sleep_logs 
        WHERE user_id = %s
        ORDER BY log_date DESC
        LIMIT 7
    """, (current_user.id,))
    logs = cur.fetchall()
    cur.close()

    if len(logs) < 3:
        return render_template("predict_from_logs.html", message="❌ Need at least 3 logs to predict disorder.")

    # Rule-based disorder logic
    disorder = "No clear disorder detected"
    last_logs = logs[:5]  # check recent 5 days max

    avg_sleep = sum([log[0] for log in last_logs]) / len(last_logs)
    avg_interruptions = sum([log[1] for log in last_logs]) / len(last_logs)
    avg_tiredness = sum([log[2] for log in last_logs]) / len(last_logs)

    if avg_sleep < 5 and avg_tiredness >= 3:
        disorder = "Possible Insomnia"
    elif avg_sleep > 9 and avg_tiredness >= 3:
        disorder = "Possible Hypersomnia"
    elif avg_interruptions >= 4:
        disorder = "Possible Sleep Apnea"

    return render_template("predict_from_logs.html", logs=last_logs, disorder=disorder)


# ------------------- Logout -------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth'))

# ------------------- Run -------------------
if __name__ == '__main__':
    app.run(debug=True)
