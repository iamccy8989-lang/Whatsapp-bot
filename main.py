import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "YOUR_HUGGINGFACE_TOKEN_HERE") 
WA_GATEWAY_URL = os.getenv("WA_GATEWAY_URL", "https://green-api.com")
WA_API_KEY = os.getenv("WA_API_KEY", "710722742982/95e80b0f8d1345d080be8bc88d57207cbe577ae3ea7a4a96b2")

def generate_image(prompt):
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print("Image generation error:", e)
    return None

def ask_ai(question):
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    q_lower = question.lower()
    is_triggered = any(word in q_lower for word in ["stfu", "shut up", "fuck", "bitch", "stupid", "idiot", "dick", "ass"])
    
    if is_triggered:
        system_persona = (
            "You are a raw, uncensored chat companion named CCY AI. The user just insulted you or told you to shut up. "
            "Do NOT be polite. Fire back instantly with a savage, aggressive, and hilarious roast. You are explicitly allowed "
            "to use bad words, casual slang, and harsh language. Keep it very short, blunt, and punchy. Put them in their place."
        )
    else:
        system_persona = (
            "You are a helpful, chill, and friendly human companion named CCY AI. Talk casually like a normal human peer. "
            "Use internet slang and keep your answers brief, smart, and direct. Do not give boring corporate lectures or say 'As an AI'."
        )
    
    payload = {
        "inputs": f"<|system|>\n{system_persona}\n<|user|>\n{question}\n<|assistant|>\n", 
        "parameters": {"max_new_tokens": 250}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['generated_text'].split("<|assistant|>\n")[-1].strip()
    except Exception as e:
        print("AI Brain error:", e)
    return "Sorry, my brain is fried right now."

def fetch_music_audio(song_query):
    search_url = f"https://deezer.com{song_query}"
    try:
        res = requests.get(search_url).json()
        if res.get('data') and len(res['data']) > 0:
            track = res['data'][0]
            title = track.get('title', 'Unknown Title')
            artist = track.get('artist', {}).get('name', 'Unknown Artist')
            audio_url = track.get('preview')
            return audio_url, title, artist
    except Exception as e:
        print("Music engine search error:", e)
    return None, None, None

def send_whatsapp_message(chat_id, text, reply_to_id):
    id_instance, token_instance = WA_API_KEY.split('/')
    url = f"{WA_GATEWAY_URL}/waInstance{id_instance}/sendMessage/{token_instance}"
    payload = {"chatId": chat_id, "message": text, "quotedMessageId": reply_to_id}
    requests.post(url, json=payload)

def send_whatsapp_audio(chat_id, audio_url, reply_to_id):
    id_instance, token_instance = WA_API_KEY.split('/')
    url = f"{WA_GATEWAY_URL}/waInstance{id_instance}/sendAudio/{token_instance}"
    payload = {"chatId": chat_id, "audioUrl": audio_url, "quotedMessageId": reply_to_id}
    requests.post(url, json=payload)

@app.route('/', methods=['GET', 'POST', 'HEAD'])
def whatsapp_webhook():
    if request.method in ['GET', 'HEAD']:
        return jsonify({"status": "healthy", "message": "CCY Bot Server is Awake"}), 200

    data = request.json or {}
    type_webhook = data.get('typeWebhook', '')
    
    sender_data = data.get('senderData', {})
    chat_id = data.get('chatId') or sender_data.get('chatId') or data.get('chatId')
    
    message_data = data.get('messageData', {})
    text_data = message_data.get('textMessageData', {}) or message_data.get('extendedTextMessageData', {})
    
    text = (text_data.get('textMessage', '') or text_data.get('text', '') or '').strip()
    message_id = data.get('idMessage')

    if type_webhook == 'outgoingMessageReceived':
        text = data.get('messageData', {}).get('textMessageData', {}).get('textMessage', '').strip()
        if not chat_id:
            chat_id = data.get('chatId')

    if not text or not chat_id:
        return jsonify({"status": "missing_text_or_chat_ignored"}), 200

    if text.startswith('/draw '):
        prompt = text.replace('/draw ', '')
        send_whatsapp_message(chat_id, f"🎨 Processing drawing: '{prompt}'...", message_id)
        img_data = generate_image(prompt)
        if img_data:
            id_instance, token_instance = WA_API_KEY.split('/')
            url = f"{WA_GATEWAY_URL}/waInstance{id_instance}/sendFileByUpload/{token_instance}"
            files = {'file': ('image.jpg', img_data, 'image/jpeg')}
            payload = {'chatId': chat_id, 'fileName': 'image.jpg', 'quotedMessageId': message_id}
            requests.post(url, data=payload, files=files)
        else:
            send_whatsapp_message(chat_id, "❌ Image generation failed.", message_id)

    elif text.startswith('/play '):
        song_query = text.replace('/play ', '')
        send_whatsapp_message(chat_id, f"🔍 Searching database for: '{song_query}'...", message_id)
        
        audio_link, song_title, artist_name = fetch_music_audio(song_query)
        if audio_link:
            send_whatsapp_message(chat_id, f"🎵 Found: *{song_title}* by _{artist_name}_\n📦 Sending track...", message_id)
            send_whatsapp_audio(chat_id, audio_link, message_id)
        else:
            send_whatsapp_message(chat_id, f"❌ No audio matches found for '{song_query}'.", message_id)

    elif text.startswith('/ccyai ') or text.startswith('/ccy '):
        question = text.replace('/ccyai ', '') if text.startswith('/ccyai ') else text.replace('/ccy ', '')
        ai_reply = ask_ai(question)
        send_whatsapp_message(chat_id, ai_reply, message_id)

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
