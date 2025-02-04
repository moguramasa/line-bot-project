import os
from flask import Flask, request, jsonify
import requests
import openai

app = Flask(__name__)

# カスタムモデル名を環境変数から取得（環境変数が設定されていない場合はデフォルトを使用）
CUSTOM_MODEL_NAME = os.getenv("CUSTOM_MODEL_NAME", "ft:gpt-4o-2024-08-06:plamoul::AwzZfZgn")

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
print("LINE_ACCESS_TOKEN:", LINE_ACCESS_TOKEN)
# APIキーも環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return f"LINE Bot is running with {CUSTOM_MODEL_NAME}!"

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json

    events = body.get("events", [])
    for event in events:
        if event["type"] == "message" and "text" in event["message"]:
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            # ChatGPTで応答を取得
            gpt_response = get_chatgpt_response(user_message)

            # LINEに返信を送信
            send_line_reply(reply_token, gpt_response)

    return jsonify({"status": "ok"})

def get_chatgpt_response(user_message):
    response = openai.ChatCompletion.create(
        model=CUSTOM_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        api_key=OPENAI_API_KEY
    )
    return response.choices[0].message["content"]

def send_line_reply(reply_token, message):
    line_api_url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(line_api_url, headers=headers, json=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
