 import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION (Set these in your Render Environment Variables) ---
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "YOUR_HUGGINGFACE_TOKEN_HERE") 
WA_GATEWAY_URL = os.getenv("WA_GATEWAY_URL", "https://green-api.com")
WA_API_KEY = os.getenv("WA_API_KEY", "YOUR_ID_AND_TOKEN_HERE")

# --- AI DRAWING MODULE ---
def generate_image(prompt):
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        return response.content
    return None

# --- AI CHAT MODULE ---
def ask_ai(question):
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": f"<|user|>\n{question}\n<|assistant|>\n", "parameters": {"max_new_tokens": 250}}
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['generated_text'].split("<|assistant|>\n")[-1]
    except Exception as e:
        print("AI Brain error:", e)
    return "Sorry, my AI brain is a bit slow right now."

# --- 🎵 MUSIC SEARCH SYSTEM ---
def fetch_music_audio(song_query):
    search_url = f"https://deezer.com{song_query}"
    try:
        res = requests.get(search_url).json()
        if res.get('data') and len(res['data']) > 0:
            # Grabs the first matching song track result structure safely
            track = res['data'][0]
            title = track.get('title', 'Unknown Title')
            artist = track.get('artist', {}).get('name', 'Unknown Artist')
            audio_url = track.get('preview')
            return audio_url, title, artist
    except Exception as e:
        print("Music engine search error:", e)
    return None, None, None

# --- WHATSAPP OUTBOUND DATA SENDERS ---
def send_whatsapp_message(chat_id, text, reply_to_id, sender_phone):
    id_instance, token_instance = WA_API_KEY.split('/')
    url = f"{WA_GATEWAY_URL}/waInstance{id_instance}/sendMessage/{token_instance}"
    clean_sender = sender_phone.split('@') if sender_phone else "User"
    formatted_text = f"🤖 *CCY AI Assistant* 🤖\n\n@{clean_sender}\n\n{text}"
    payload = {"chatId": chat_id, "message": formatted_text, "quotedMessageId": reply_to_id}
    requests.post(url, json=payload)

def send_whatsapp_audio(chat_id, audio_url, reply_to_id):
    id_instance, token_instance = WA_API_KEY.split('/')
    url = f"{WA_GATEWAY_URL}/waInstance{id_instance}/sendAudio/{token_instance}"
    payload = {"chatId": chat_id, "audioUrl": audio_url, "quotedMessageId": reply_to_id}
    requests.post(url, json=payload)

# --- MASTER INTERCEPTOR (ROOT ROUTE FOR GREEN API) ---
@app.route('/', methods=['GET', 'POST', 'HEAD'])
def whatsapp_webhook():
    # Handle empty health checks from browsers or Green API saving tools gracefully
    if request.method in ['GET', 'HEAD']:
        return jsonify({"status": "healthy", "message": "CCY Bot Server is Awake"}), 200

    data = request.json
    if not data:
        return jsonify({"status": "empty_ignored"}), 200
        
    type_webhook = data.get('typeWebhook', '')
    sender_data = data.get('senderData', {})
    chat_id = data.get('chatId') or sender_data.get('chatId')
    sender_phone = sender_data.get('sender') or data.get('sender', '')
    
    message_data = data.get('messageData', {})
    text_data = message_data.get('textMessageData', {}) or message_data.get('extendedTextMessageData', {})
    
    text = text_data.get('textMessage', '') or text_data.get('text', '') or ''
    text = text.strip()
    message_id = data.get('idMessage')

    # Self-messaging mapping
    if type_webhook == 'outgoingMessageReceived':
        text = data.get('messageData', {}).get('textMessageData', {}).get('textMessage', '').strip()
        if not chat_id:
            chat_id = data.get('chatId')
        if not sender_phone:
            sender_phone = chat_id

    if not text or not chat_id:
        return jsonify({"status": "missing_text_or_chat_ignored"}), 200

    # 1. Image Generation Command (/draw)
    if text.startswith('/draw '):
        prompt = text.replace('/draw ', '')
        send_whatsapp_message(chat_id, f"🎨 Processing your drawing prompt: '{prompt}'...", message_id, sender_phone)

    # 2. Live Music Playback Command (/play) 🎵
    elif text.startswith('/play '):
        song_query = text.replace('/play ', '')
        send_whatsapp_message(chat_id, f"🔍 Searching database for: '{song_query}'...", message_id, sender_phone)
        
        audio_link, song_title, artist_name = fetch_music_audio(song_query)
        if audio_link:
            send_whatsapp_message(chat_id, f"🎵 Found: *{song_title}* by _{artist_name}_\n📦 Sending playable audio file now...", message_id, sender_phone)
            send_whatsapp_audio(chat_id, audio_link, message_id)
        else:
            send_whatsapp_message(chat_id, f"❌ Sorry, I couldn't find any audio matches for '{song_query}'.", message_id, sender_phone)

    # 3. AI Chat Question Command (/ccyai or /ccy)
    elif text.startswith('/ccyai ') or text.startswith('/ccy '):
        question = text.replace('/ccyai ', '') if text.startswith('/ccyai ') else text.replace('/ccy ', '')
        ai_reply = ask_ai(question)
        send_whatsapp_message(chat_id, ai_reply, message_id, sender_phone)

    else:
        return jsonify({"status": "not_a_command_ignored"}), 200

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
