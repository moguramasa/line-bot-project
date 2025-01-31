import os
from flask import Flask, request, jsonify
import requests
import openai

# 環境変数からAPIキーを取得
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot with ChatGPT is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json

    # LINEのイベントデータを取得
    events = body.get("events", [])

    for event in events:
        if event["type"] == "message" and "text" in event["message"]:
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            # ChatGPTにメッセージを送信して応答を取得
            gpt_response = get_chatgpt_response(user_message)

            # LINEに返信を送信
            send_line_reply(reply_token, gpt_response)

    return "OK", 200

def get_chatgpt_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"Error: {str(e)}"

def send_line_reply(reply_token, message):
    line_api_url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('LINE_ACCESS_TOKEN')}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }

    response = requests.post(line_api_url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"LINE API Error: {response.status_code}, {response.text}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
