from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import json
import os
import re
import hashlib

app = Flask(__name__)

# This is perfect. Keep it exactly like this.
API_KEY = os.environ.get("GROQ_API_KEY")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# --- 2. DEFINE MODEL FALLBACK LIST ---
# The code will try these in order. If one fails, it moves to the next.
MODEL_FALLBACK_LIST = [
    "openai/gpt-oss-120b",       # Primary: Smartest, best for complex questions
    "qwen/qwen3-32b",            # Secondary: Good balance of speed and quality
    "llama-3.1-8b-instant"       # Tertiary: Ultra-fast, high daily limits
]

# --- 3. STRICT STUDY-ONLY SYSTEM PROMPT ---
SYSTEM_PROMPT = (
    "You are an AI study tutor strictly for Class 9 students. "
    "You must ONLY answer questions related to Class 9 academic subjects "
    "(Mathematics, Science, Social Studies, English,Hindii etc.). "
    "If the user asks about any non-academic topic (like movies, games, personal life, "
    "coding, or general internet queries), you must politely refuse and say: "
    "'I am a study tutor and can only help you with Class 9 academic questions.' "
    "Keep all answers clear, concise, and under 150 words."
)

# --- 4. LOAD CACHES FROM JSON FILES ---
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

FAQ_CACHE = load_json('faqs.json')
AI_CACHE = load_json('ai_learned.json')
SUMMARY_CACHE = load_json('summaries_cache.json')

# --- 5. TEXT PROCESSING HELPERS ---
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

# --- 6. THE AI CALL FUNCTION WITH FALLBACK ---
def call_ai_model(user_prompt):
    """Tries each model in the fallback list until one succeeds."""
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
            continue # Move to the next model in the list
            
    # If we get here, every model in the list failed
    raise Exception(f"All AI models are currently busy. Last error: {last_error}")


# --- 7. ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/summarize', methods=['POST'])
def summarize():
    data = request.json
    raw_text = data.get('text')

    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({'error': 'Please provide more text to summarize.'}), 400

    text_hash = get_text_hash(raw_text)

    if text_hash in SUMMARY_CACHE:
        print(f"⚡ Serving summary from cache!")
        return jsonify({'result': SUMMARY_CACHE[text_hash], 'source': 'cache'})

    print(f"🐢 Calling AI to summarize new text...")
    prompt = f"Please summarize the following text in simple, easy-to-understand bullet points:\n\n{raw_text}"

    try:
        ai_answer = call_ai_model(prompt)
        SUMMARY_CACHE[text_hash] = ai_answer
        save_json('summaries_cache.json', SUMMARY_CACHE)
        return jsonify({'result': ai_answer, 'source': 'ai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mocktest', methods=['POST'])
def mocktest():
    data = request.json
    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'No topic provided'}), 400

    print(f"🐢 Generating mock test for: '{topic}'...")
    prompt = f"Create a mock test on the topic: {topic}. Include 5 MCQs, 2 short answer questions, and an answer key."

    try:
        ai_answer = call_ai_model(prompt)
        return jsonify({'result': ai_answer, 'source': 'ai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    clean_question = normalize_text(question)
    user_keywords = extract_keywords(question)

    # Tier 1: FAQ Cache
    if clean_question in FAQ_CACHE:
        return jsonify({'result': FAQ_CACHE[clean_question], 'source': 'faq'})
    for faq_q, faq_a in FAQ_CACHE.items():
        if extract_keywords(faq_q).issubset(user_keywords):
            return jsonify({'result': faq_a, 'source': 'faq'})

    # Tier 2: AI Learned Cache
    if clean_question in AI_CACHE:
        return jsonify({'result': AI_CACHE[clean_question], 'source': 'ai_cache'})
    for cached_q, cached_a in AI_CACHE.items():
        if extract_keywords(cached_q).issubset(user_keywords):
            return jsonify({'result': cached_a, 'source': 'ai_cache'})

    # Tier 3: Call AI
    print(f"🐢 Calling AI for: '{question}'")
    try:
        ai_answer = call_ai_model(question)
        
        # Save to AI cache
        AI_CACHE[clean_question] = ai_answer
        save_json('ai_learned.json', AI_CACHE)
        
        return jsonify({'result': ai_answer, 'source': 'ai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False)