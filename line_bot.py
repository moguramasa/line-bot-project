import os
from flask import Flask, request, jsonify
import requests
import openai

app = Flask(__name__)

# カスタムモデルを直接指定
CUSTOM_MODEL_NAME = "ft:gpt-4o-mini-2024-07-18:plamoul::AvghQ5ci"

# OpenAI APIキーをコード内で直接指定（例、変更してください）
OPENAI_API_KEY = "sk-your-key-here"

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot with Custom ChatGPT model is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json

    # LINEのイベントデータを取得
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
    # OpenAI APIへのリクエスト
    response = openai.ChatCompletion.create(
        model=CUSTOM_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        api_key=OPENAI_API_KEY  # APIキーを直接渡す
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

# 実行コード
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
