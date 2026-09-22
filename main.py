import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION (Set these in your cloud environment) ---
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "YOUR_HUGGINGFACE_TOKEN_HERE") 
WA_GATEWAY_URL = os.getenv("WA_GATEWAY_URL", "YOUR_GATEWAY_URL_HERE")
WA_API_KEY = os.getenv("WA_API_KEY", "YOUR_API_KEY_HERE")

# --- AI IMAGE GENERATION (/draw) ---
def generate_image(prompt):
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        return response.content
    return None

# --- AI QUESTION ANSWERING (Chat via /ccyai or /ccy) ---
def ask_ai(question):
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": f"<|user|>\n{question}\n<|assistant|>\n", "parameters": {"max_new_tokens": 250}}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        try:
            return response.json()['generated_text'].split("<|assistant|>\n")[-1]
        except:
            return "I couldn't process that response."
    return "Sorry, my AI brain is a bit slow right now."

# --- MUSIC SCRAPER SYSTEM (/music) ---
def fetch_music_audio(song_query):
    search_url = f"https://deezer.com{song_query}"
    try:
        res = requests.get(search_url).json()
        if res.get('data'):
            return res['data']['preview']
    except Exception as e:
        print("Music search error:", e)
    return None

# --- WHATSAPP GATEWAY OUTBOUND HITS ---
def send_whatsapp_message(chat_id, text, reply_to_id):
    url = f"{WA_GATEWAY_URL}/messages/send"
    payload = {"chatId": chat_id, "text": text, "replyMessageId": reply_to_id}
    headers = {"Authorization": f"Bearer {WA_API_KEY}", "Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)

def send_whatsapp_audio(chat_id, audio_url, reply_to_id):
    url = f"{WA_GATEWAY_URL}/messages/send-audio"
    payload = {"chatId": chat_id, "audioUrl": audio_url, "isVoiceNote": True, "replyMessageId": reply_to_id}
    headers = {"Authorization": f"Bearer {WA_API_KEY}", "Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)

# --- WEBHOOK INTERCEPTOR ---
@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.json
    
    message = data.get('message', {})
    text = message.get('text', '').strip()
    chat_id = data.get('chatId')
    message_id = message.get('id')
    
    if not text or not chat_id:
        return jsonify({"status": "ignored"}), 200

    # 1. Handle Image Command
    if text.startswith('/draw '):
        prompt = text.replace('/draw ', '')
        send_whatsapp_message(chat_id, "🎨 Generating your art, please wait...", message_id)
        send_whatsapp_message(chat_id, f"✅ Image generation triggered for: '{prompt}'", message_id)

    # 2. Handle Music Command
    elif text.startswith('/music '):
        song_query = text.replace('/music ', '')
        send_whatsapp_message(chat_id, f"🎵 Searching for '{song_query}' and converting to voice note...", message_id)
        audio_link = fetch_music_audio(song_query)
        if audio_link:
            send_whatsapp_audio(chat_id, audio_link, message_id)
        else:
            send_whatsapp_message(chat_id, "❌ Sorry, I couldn't find that song.", message_id)

    # 3. Handle AI Chat Commands (/ccyai or /ccy)
    elif text.startswith('/ccyai ') or text.startswith('/ccy '):
        # Strip away the command prefixes to grab just the actual question
        if text.startswith('/ccyai '):
            question = text.replace('/ccyai ', '')
        else:
            question = text.replace('/ccy ', '')
            
        ai_reply = ask_ai(question)
        send_whatsapp_message(chat_id, ai_reply, message_id)

    # If it is a normal text message without any command prefix, the bot completely ignores it
    else:
        return jsonify({"status": "ignored"}), 200

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
  
