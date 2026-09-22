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
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        try:
            return response.json()['generated_text'].split("<|assistant|>\n")[-1]
        except:
            return "I couldn't process that response."
    return "Sorry, my AI brain is a bit slow right now."

# --- WHATSAPP OUTBOUND (WITH SENDER TAGS) ---
def send_whatsapp_message(chat_id, text, reply_to_id, sender_phone):
    id_instance, token_instance = WA_API_KEY.split('/')
    url = f"{WA_GATEWAY_URL}/waInstance{id_instance}/sendMessage/{token_instance}"
    
    clean_sender = sender_phone.split('@')[0]
    formatted_text = f"🤖 *CCY AI Assistant* 🤖\n\n@{clean_sender}\n\n{text}"
    
    payload = {
        "chatId": chat_id, 
        "message": formatted_text, 
        "quotedMessageId": reply_to_id
    }
    requests.post(url, json=payload)

# --- WEBHOOK INTERCEPTOR ---
@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.json
    
    sender_data = data.get('senderData', {})
    chat_id = sender_data.get('chatId') 
    sender_phone = sender_data.get('sender', '')
    
    message_data = data.get('messageData', {})
    text_data = message_data.get('textMessageData', {})
    text = text_data.get('textMessage', '').strip()
    message_id = data.get('idMessage')

    if not text or not chat_id:
        return jsonify({"status": "ignored"}), 200

    # 1. Image Generation
    if text.startswith('/draw '):
        prompt = text.replace('/draw ', '')
        send_whatsapp_message(chat_id, f"🎨 Processing your drawing prompt: '{prompt}'...", message_id, sender_phone)

    # 2. AI Question Answering
    elif text.startswith('/ccyai ') or text.startswith('/ccy '):
        question = text.replace('/ccyai ', '') if text.startswith('/ccyai ') else text.replace('/ccy ', '')
        ai_reply = ask_ai(question)
        send_whatsapp_message(chat_id, ai_reply, message_id, sender_phone)

    else:
        return jsonify({"status": "ignored"}), 200

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
