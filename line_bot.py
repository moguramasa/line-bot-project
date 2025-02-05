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

# キャッシュ用データ格納
cached_data = {"product_data": None, "company_info": None, "product_specs": None}

# Dropboxからデータを取得しキャッシュ
def fetch_all_data():
    if not cached_data["product_data"]:
        cached_data["product_data"] = fetch_data_from_dropbox("/product_data.json")
        cached_data["company_info"] = fetch_data_from_dropbox("/company_info.txt")
        cached_data["product_specs"] = fetch_data_from_dropbox("/product_specs.csv")

    product_data_json = json.loads(cached_data["product_data"]) if cached_data["product_data"] else []
    return product_data_json, cached_data["company_info"], cached_data["product_specs"]

def fetch_data_from_dropbox(file_path):
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        _, response = dbx.files_download(file_path)
        return response.content.decode("utf-8")
    except Exception as e:
        print(f"Dropboxからデータ取得エラー: {e}")
        return ""

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

    # Dropboxからすべてのデータを取得
    product_data, company_info, product_specs = fetch_all_data()

    events = body.get("events", [])
    for event in events:
        if event["type"] == "message" and "text" in event["message"]:
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            # 質問内容によって応答を切り替え
            if "社長" in user_message:
                response_text = company_info.strip()
            else:
                response_text = find_product_info(user_message, product_data)

            # ChatGPTで応答を取得
            gpt_response = format_response(get_chatgpt_response(user_message, response_text))

            # LINEに返信を送信
            send_line_reply(reply_token, gpt_response)

    return jsonify({"status": "ok"}), 200

def get_chatgpt_response(user_message, product_info):
    start_time = time.time()
    try:
        print(f"使用中のモデル: {CUSTOM_MODEL_NAME}")  # モデル名を確認
        print("リクエスト送信中...")

        response = openai.ChatCompletion.create(
            model=CUSTOM_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "あなたは日本語の専門知識を持つアシスタントです。"
                        "以下の条件を守って回答してください。"
                        "提供された情報のみを使用してください。"
                    )
                },
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": product_info}
            ],
            temperature=0.0,  # ランダム性を抑制
            max_tokens=300,
            api_key=OPENAI_API_KEY
        )

        print("API応答:", response)  # APIレスポンスを出力
        print(f"Response time: {time.time() - start_time} seconds")
        return response.choices[0].message["content"]
    except Exception as e:
        print("OpenAI APIエラー:", e)
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
