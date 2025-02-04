import os
from flask import Flask, request, jsonify
import requests
import openai
import time
import dropbox
import json

app = Flask(__name__)

# カスタムモデル名を直接指定
CUSTOM_MODEL_NAME = "ft:gpt-4o-2024-08-06:plamoul::Ax4X09hy"

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
print("LINE_ACCESS_TOKEN:", LINE_ACCESS_TOKEN)

# APIキーも環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Dropbox API アクセストークン
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

def fetch_product_data_from_dropbox():
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        _, response = dbx.files_download("/product_data.json")
        product_data = json.loads(response.content.decode("utf-8"))
        print("Dropboxから取得したデータ:", product_data)
        return product_data
    except Exception as e:
        print(f"Dropboxからデータ取得エラー: {e}")
        return []

def find_product_info(product_name, product_data):
    for product in product_data:
        if product["product_name"] == product_name:
            return product["description"]
    return f"申し訳ありません。'{product_name}'に該当する製品情報が見つかりませんでした。"

@app.route("/", methods=["GET"])
def home():
    return f"LINE Bot is running with {CUSTOM_MODEL_NAME}!"

@app.route("/webhook", methods=["POST"])
def webhook():
    print("Webhook request received")
    body = request.json

    events = body.get("events", [])
    for event in events:
        if event["type"] == "message" and "text" in event["message"]:
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            # Dropboxからデータを取得
            product_data = fetch_product_data_from_dropbox()

            # 製品情報を検索
            product_info = find_product_info(user_message, product_data)

            # ChatGPTで応答を取得
            gpt_response = format_response(get_chatgpt_response(product_info))

            # LINEに返信を送信
            send_line_reply(reply_token, gpt_response)

    return jsonify({"status": "ok"}), 200

def get_chatgpt_response(user_message):
    start_time = time.time()
    try:
        response = openai.ChatCompletion.create(
            model=CUSTOM_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "あなたは日本語の専門知識を持つアシスタントです。"
                        "以下の条件を守って回答してください。"
                        "1. 文末は必ず『です・ます調』で終えること。"
                        "2. 短すぎる回答を避け、50～150文字程度で詳細に回答すること。"
                        "3. 質問に対して具体的で実用的な内容を提供すること。"
                        "4. 可能な限り親しみやすく、かつ丁寧に答えること。"
                        "例: 『ガストースはガス抜き性能が高い金型です。この技術により、成形品の品質が安定します。』"
                    )
                },
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,  # 応答のランダム性を調整
            max_tokens=300,   # 応答の最大長を設定
            api_key=OPENAI_API_KEY
        )
        print(f"Response time: {time.time() - start_time} seconds")
        return response.choices[0].message["content"]
    except Exception as e:
        print("OpenAI API error:", e)
        return "エラーが発生しました"

def format_response(response):
    if response.endswith("以上です。"):
        response = response[:-5]
    response += " 何か他に知りたいことがあればお知らせください。"
    return response

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