import os
from flask import Flask, request, jsonify
import requests
import openai
import time
import json

app = Flask(__name__)

CUSTOM_MODEL_NAME = "ft:gpt-4o-2024-08-06:plamoul::Ax4X09hy"

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

cached_data = {"product_data": None, "company_info": None, "product_specs": None}

def fetch_all_data():
    # Dropbox関連のデータ取得を無効化し、固定の値を使用
    cached_data["product_data"] = '[{"product_name": "サンプル製品", "description": "これはサンプルの製品情報です。"}]'
    cached_data["company_info"] = "代表取締役社長: 脇山"
    cached_data["product_specs"] = "製品仕様情報は現在利用できません"

    product_data_json = json.loads(cached_data["product_data"]) if cached_data["product_data"] else []
    return product_data_json, cached_data["company_info"], cached_data["product_specs"]

def extract_president_name(company_info):
    lines = company_info.splitlines()
    for line in lines:
        if "代表取締役社長" in line:
            return line.split("代表取締役社長: ")[-1].strip()
    return "情報が見つかりません"

def find_product_info(product_name, product_data):
    for product in product_data:
        if product["product_name"] == product_name:
            return f"プラモール精工では、{product_name}に関する情報として以下の内容がございます。\n{product['description']}"
    return f"申し訳ありません。プラモール精工では、'{product_name}'に該当する製品情報が見つかりませんでした。"

@app.route("/", methods=["GET"])
def home():
    return f"LINE Bot is running with {CUSTOM_MODEL_NAME}!"

@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    print("Webhook request received")
    body = request.json

    product_data, company_info, product_specs = fetch_all_data()

    events = body.get("events", [])
    for event in events:
        if event["type"] == "message" and "text" in event["message"]:
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            if "社長" in user_message:
                president_name = extract_president_name(company_info)
                response_text = f"プラモール精工の社長は、{president_name}です。"
            else:
                response_text = find_product_info(user_message, product_data)

            gpt_response = format_response(get_chatgpt_response(user_message, response_text))
            send_line_reply(reply_token, gpt_response)

    return jsonify({"status": "ok"}), 200

def get_chatgpt_response(user_message, product_info):
    try:
        print(f"使用中のモデル: {CUSTOM_MODEL_NAME}")
        response = openai.ChatCompletion.create(
            model=CUSTOM_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "あなたは株式会社プラモール精工の代表取締役社長である脇山です。"
                        "質問に対して社長として丁寧に、かつ正確に回答してください。"
                        "提供された情報のみを使用し、顧客や社内の社員に信頼を持たせる回答を行ってください。"
                    )
                },
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": product_info}
            ],
            temperature=0.0,
            max_tokens=300,
            api_key=OPENAI_API_KEY
        )
        return response.choices[0].message["content"]
    except Exception as e:
        print("OpenAI APIエラー:", e)
        return "エラーが発生しました"

def format_response(response):
    if response.endswith("以上です。"):
        response = response[:-5]
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
