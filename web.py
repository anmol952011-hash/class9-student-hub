from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import json
import os
import re
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-this-in-production")

# --- SECURITY CONFIGURATION ---
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "false").lower() == "true",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)

IS_PRODUCTION = os.environ.get("RENDER", "false").lower() == "true"
if IS_PRODUCTION:
    print("🔒 Production mode: HTTPS enforced")
    Talisman(app)
else:
    print("🛠️ Development mode: HTTPS disabled")
    Talisman(app, force_https=False)

# --- AI CLIENT ---
API_KEY = os.environ.get("GROQ_API_KEY")
client = OpenAI(api_key=API_KEY, base_url="https://api.groq.com/openai/v1")

MODEL_FALLBACK_LIST = [
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant"
]

SYSTEM_PROMPT = (
    "You are an AI study tutor strictly for Class 9 students. "
    "You must ONLY answer questions related to Class 9 academic subjects "
    "(Mathematics, Science, Social Studies, English, Hindi, etc.). "
    "If the user asks about any non-academic topic (like movies, games, personal life, "
    "coding, or general internet queries), you must politely refuse and say: "
    "'I am a study tutor and can only help you with Class 9 academic questions.' "
    "Keep all answers clear, concise, and under 150 words."
)

# --- FILE HELPERS ---
def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Load caches
FAQ_CACHE = load_json('faqs.json')
AI_CACHE = load_json('ai_learned.json')
SUMMARY_CACHE = load_json('summaries_cache.json')
USERS = load_json('users.json')

# --- TEXT HELPERS ---
STOP_WORDS = {
    "what", "is", "the", "a", "an", "of", "define", "explain",
    "meaning", "do", "you", "mean", "by", "tell", "me", "about",
    "please", "help", "how", "does", "can", "in", "to", "and", "or"
}

def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text.lower()).strip()

def extract_keywords(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    words = text.split()
    return set(w for w in words if w not in STOP_WORDS)

def get_text_hash(text):
    cleaned = " ".join(text.split())
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()

# --- AUTH HELPERS ---
def current_user():
    return session.get('user')

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Please log in first.'}), 401
        return f(*args, **kwargs)
    return decorated

# --- AI CALL WITH FALLBACK ---
def call_ai_model(user_prompt):
    last_error = "All models failed."
    for model_name in MODEL_FALLBACK_LIST:
        try:
            print(f"🤖 Trying model: {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500
            )
            print(f"✅ Success with {model_name}")
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Model {model_name} failed: {e}")
            last_error = str(e)
            continue
    raise Exception(f"All AI models are busy. Last error: {last_error}")


# ============ ROUTES ============

@app.route('/')
def home():
    return render_template('index.html')


# --- AUTH ROUTES ---
@app.route('/api/signup', methods=['POST'])
@limiter.limit("5 per minute")
def signup():
    data = request.json
    # We now use email instead of username
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    
    # Email validation using regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'error': 'Please enter a valid email address.'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    users = load_json('users.json')
    if email in users:
        return jsonify({'error': 'An account with this email already exists.'}), 400

    users[email] = {
        'password': generate_password_hash(password),
        'questions_asked': 0
    }
    save_json('users.json', users)
    session['user'] = email
    print(f"👤 New user signed up: {email}")
    return jsonify({'success': True, 'email': email})


@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    users = load_json('users.json')
    user = users.get(email)

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    session['user'] = email
    print(f"👤 User logged in: {email}")
    return jsonify({'success': True, 'email': email})


@app.route('/api/me')
def me():
    if 'user' in session:
        return jsonify({'logged_in': True, 'email': session['user']})
    return jsonify({'logged_in': False})

# --- SUMMARIZE ---
@app.route('/api/summarize', methods=['POST'])
@limiter.limit("10 per minute")
def summarize():
    data = request.json
    raw_text = data.get('text')

    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({'error': 'Please provide more text to summarize.'}), 400

    text_hash = get_text_hash(raw_text)
    if text_hash in SUMMARY_CACHE:
        print("⚡ Summary served from cache!")
        return jsonify({'result': SUMMARY_CACHE[text_hash], 'source': 'cache'})

    print("🐢 Calling AI to summarize...")
    prompt = f"Please summarize the following text in simple, easy-to-understand bullet points:\n\n{raw_text}"

    try:
        ai_answer = call_ai_model(prompt)
        SUMMARY_CACHE[text_hash] = ai_answer
        save_json('summaries_cache.json', SUMMARY_CACHE)
        return jsonify({'result': ai_answer, 'source': 'ai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- MOCK TEST ---
@app.route('/api/mocktest', methods=['POST'])
@limiter.limit("5 per minute")
def mocktest():
    data = request.json
    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'No topic provided'}), 400

    print(f"🐢 Generating mock test for: '{topic}'")
    prompt = f"Create a mock test on the topic: {topic}. Include 5 MCQs, 2 short answer questions, and an answer key."

    try:
        ai_answer = call_ai_model(prompt)
        return jsonify({'result': ai_answer, 'source': 'ai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- ASK AI ---
@app.route('/api/ask', methods=['POST'])
@limiter.limit("15 per minute")
def ask_question():
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    clean_question = normalize_text(question)
    user_keywords = extract_keywords(question)

    # Tier 1: FAQ cache
    if clean_question in FAQ_CACHE:
        return jsonify({'result': FAQ_CACHE[clean_question], 'source': 'faq'})
    for faq_q, faq_a in FAQ_CACHE.items():
        if extract_keywords(faq_q).issubset(user_keywords):
            return jsonify({'result': faq_a, 'source': 'faq'})

    # Tier 2: AI learned cache
    if clean_question in AI_CACHE:
        return jsonify({'result': AI_CACHE[clean_question], 'source': 'ai_cache'})
    for cached_q, cached_a in AI_CACHE.items():
        if extract_keywords(cached_q).issubset(user_keywords):
            return jsonify({'result': cached_a, 'source': 'ai_cache'})

    # Tier 3: Call AI
    print(f"🐢 Calling AI for: '{question}'")
    try:
        ai_answer = call_ai_model(question)
        AI_CACHE[clean_question] = ai_answer
        save_json('ai_learned.json', AI_CACHE)

        # Increment user's question count
        if 'user' in session:
            users = load_json('users.json')
            if session['user'] in users:
                users[session['user']]['questions_asked'] = users[session['user']].get('questions_asked', 0) + 1
                save_json('users.json', users)

        return jsonify({'result': ai_answer, 'source': 'ai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)