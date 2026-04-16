from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "secret123"

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

eng_path = "./english_fake_news_model"
eng_tokenizer = AutoTokenizer.from_pretrained(eng_path)
eng_model = AutoModelForSequenceClassification.from_pretrained(eng_path)
eng_model.to(device)
eng_model.eval()

tam_path = "./tamil_fake_news_model"
tam_tokenizer = AutoTokenizer.from_pretrained(tam_path)
tam_model = AutoModelForSequenceClassification.from_pretrained(tam_path)
tam_model.to(device)
tam_model.eval()

hin_path = "./hindi_fake_news_model"
hin_tokenizer = AutoTokenizer.from_pretrained(hin_path)
hin_model = AutoModelForSequenceClassification.from_pretrained(hin_path)
hin_model.to(device)
hin_model.eval()

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_name TEXT UNIQUE,
        password TEXT,
        owner_name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        is_verified INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            language TEXT,
            channel_id INTEGER,
            is_fake TEXT,
            confidence REAL,
            beneficiary TEXT,
            origin TEXT,
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        )
        """)

    conn.commit()
    conn.close()
    

@app.route('/')
def home():
    conn = get_db()
    news = conn.execute("""
        SELECT news.*, users.username as channel_name
        FROM news
        LEFT JOIN users ON news.channel_id = users.id
    """).fetchall()
    conn.close()

    return render_template("index.html", news=news)

@app.route('/channel_register', methods=['GET','POST'])
def channel_register():
    if request.method == 'POST':
        channel_name = request.form['channel_name']
        password = request.form['password']
        owner_name = request.form['owner_name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']

        conn = get_db()
        conn.execute("""
            INSERT INTO channels 
            (channel_name,password,owner_name,email,phone,address)
            VALUES (?,?,?,?,?,?)
        """, (channel_name,password,owner_name,email,phone,address))

        conn.commit()
        conn.close()

        return redirect(url_for('channel_login'))

    return render_template("channel_register.html")


@app.route('/user_register', methods=['GET','POST'])
def user_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        conn.execute("""
            INSERT INTO users (username,email,password)
            VALUES (?,?,?)
        """, (username,email,password))

        conn.commit()
        conn.close()

        return redirect(url_for('user_login'))

    return render_template("user_register.html")



@app.route('/channel_login', methods=['GET','POST'])
def channel_login():
    if request.method == 'POST':
        channel_name = request.form['channel_name']
        print(channel_name)
        password = request.form['password']
        print(password)

        conn = get_db()
        channel = conn.execute(
            "SELECT * FROM channels WHERE channel_name=? AND password=?",
            (channel_name, password)
        ).fetchone()
        conn.close()
        print(channel)

        if channel:
            session['channel_id'] = channel['id']
            session['channel_name'] = channel['channel_name']
            session['role'] = 'channel'
            return redirect(url_for('channel_dashboard'))

    return render_template("channel_login.html")


@app.route('/user_login', methods=['GET','POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username,password)
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['role'] = "user"
            session['username'] = user['username']
            return redirect(url_for('user_dashboard'))

    return render_template("user_login.html")

@app.route('/channel_dashboard')
def channel_dashboard():
    if 'channel_id' not in session:
        return redirect(url_for('channel_login'))

    conn = get_db()
    news = conn.execute(
        "SELECT * FROM news WHERE channel_id=?",
        (session['channel_id'],)
    ).fetchall()
    conn.close()

    return render_template("channel_dashboard.html", news=news)

@app.route('/user_dashboard')
def user_dashboard():
    # Ensure only users can access
    if 'role' not in session or session['role'] != "user":
        return redirect(url_for('user_login'))

    conn = get_db()

    # Fetch all news with proper channel names
    news = conn.execute("""
        SELECT news.*, channels.channel_name as channel_name
        FROM news
        JOIN channels ON news.channel_id = channels.id
        ORDER BY news.id DESC
    """).fetchall()

    conn.close()

    return render_template("user_dashboard.html", news=news)


@app.route('/upload', methods=['POST'])
def upload():

    print("SESSION:", session)

    if 'channel_id' not in session:
        print("Channel ID not found")
        return redirect(url_for('channel_login'))

    title = request.form['title']
    content = request.form['content']
    language = request.form['language']

    #print("DATA:", title, content, language)

    conn = get_db()
    conn.execute("""
        INSERT INTO news (title, content, language, channel_id)
        VALUES (?,?,?,?)
    """, (title, content, language, session['channel_id']))
    conn.commit()
    conn.close()

    #print("Inserted Successfully")

    return redirect(url_for('channel_dashboard'))


def predict_news(text, language):

    if language == "English":
        tokenizer = eng_tokenizer
        model = eng_model

    elif language == "Tamil":
        tokenizer = tam_tokenizer
        model = tam_model

    elif language == "Hindi":
        tokenizer = hin_tokenizer
        model = hin_model

    else:
        return "Unknown", 0

    inputs = tokenizer(
        text,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        confidence = torch.max(probs).item()
        prediction = torch.argmax(logits, dim=-1).item()

    label_map = {1: "Real", 0: "Fake"}

    return label_map[prediction], round(confidence * 100, 2)



government_keywords = [
    "central government", "prime minister", "bjp",
    "modi", "finance ministry", "union government"
]

opposition_keywords = [
    "congress", "rahul gandhi", "opposition",
    "state government", "tmc", "dmk", "aap"
]


negative_words = [
    "failed", "corruption", "scam", "shortfall",
    "loss", "illegal", "crisis", "controversy"
]

positive_words = [
    "success", "achievement", "growth",
    "benefit", "development", "improvement"
]


def detect_sentiment(text):

    text = text.lower()

    neg = sum(word in text for word in negative_words)
    pos = sum(word in text for word in positive_words)

    if neg > pos:
        return "Negative"
    elif pos > neg:
        return "Positive"
    else:
        return "Neutral"

    

def detect_political_side(text):

    text = text.lower()

    gov_score = sum(word in text for word in government_keywords)
    opp_score = sum(word in text for word in opposition_keywords)

    if gov_score > opp_score:
        return "Government"
    elif opp_score > gov_score:
        return "Opposition"
    else:
        return "Neutral"


def detect_beneficiary(text, is_fake):

    side = detect_political_side(text)
    sentiment = detect_sentiment(text)

    if not is_fake:
        return "Not Applicable"

    if side == "Government" and sentiment == "Negative":
        return "Opposition Benefits"

    elif side == "Opposition" and sentiment == "Negative":
        return "Government Benefits"

    elif side == "Government" and sentiment == "Positive":
        return "Government Benefits"

    elif side == "Opposition" and sentiment == "Positive":
        return "Opposition Benefits"

    else:
        return "Unclear Political Impact"

def detect_origin(text):
    if "twitter" in text.lower():
        return "Social Media"
    elif "official statement" in text.lower():
        return "Official Source"
    else:
        return "News Media"

@app.route('/detect/<int:id>', methods=['POST'])
def detect(id):

    if 'user_id' not in session:
        return jsonify({"error": "Login required"})

    conn = get_db()

    news = conn.execute(
        "SELECT content, language FROM news WHERE id=?",
        (id,)
    ).fetchone()

    if not news:
        return jsonify({"error": "News not found"})

    text = news['content']
    language = news['language']

    result, confidence = predict_news(text, language)


    is_fake_flag = True if result == "Fake" else False

    beneficiary = detect_beneficiary(text, is_fake_flag)
    origin = "Uploaded by Channel"

    conn.execute("""
        UPDATE news
        SET is_fake=?, confidence=?, beneficiary=?, origin=?
        WHERE id=?
    """, (result, confidence, beneficiary, origin, id))

    conn.commit()
    conn.close()

    return jsonify({
        "is_fake": result,
        "confidence": confidence,
        "beneficiary": beneficiary,
        "origin": origin
    })


@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('home'))


if __name__ == "__main__":
    create_tables()
    app.run(debug=False, port=600)
