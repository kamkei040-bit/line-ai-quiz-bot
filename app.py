import os
import json
import random
import hmac
import hashlib
import base64
import requests
from flask import Flask, request, abort

app = Flask(__name__)

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

# クイズ問題
QUIZ_DATA = [
    {
        "question": "AIがもっともらしい誤情報を生成する現象は？",
        "choices": ["ハルシネーション", "DX", "API", "IoT"],
        "answer": 0,
        "explanation": "ハルシネーションはAIが事実ではない内容を生成する現象です。"
    },
    {
        "question": "AIへの指示文を何と呼ぶ？",
        "choices": ["トークン", "プロンプト", "GPU", "API"],
        "answer": 1,
        "explanation": "プロンプトはAIへの指示文です。"
    },
    {
        "question": "Large Language Model の略は？",
        "choices": ["LLM", "CPU", "OCR", "SNS"],
        "answer": 0,
        "explanation": "LLMは大規模言語モデルのことです。"
    },
    {
        "question": "データの偏りで結果が偏る問題は？",
        "choices": ["DX", "バイアス", "OCR", "API"],
        "answer": 1,
        "explanation": "AIの判断が偏る原因になります。"
    },
    {
        "question": "創作物を守る権利は？",
        "choices": ["個人情報", "著作権", "DX", "API"],
        "answer": 1,
        "explanation": "著作権は創作物を守る権利です。"
    }
]

USER_STATE = {}

# ---------------------------
# 署名検証
# ---------------------------
def verify_signature(body, signature):

    hash = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()

    expected_signature = base64.b64encode(hash).decode()

    return hmac.compare_digest(expected_signature, signature)

# ---------------------------
# LINE返信
# ---------------------------
def reply_message(reply_token, text):

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }

    requests.post(
        LINE_REPLY_URL,
        headers=headers,
        data=json.dumps(payload)
    )

# ---------------------------
# クイズ出題
# ---------------------------
def start_quiz(user_id):

    quiz = random.choice(QUIZ_DATA)

    USER_STATE[user_id] = quiz

    text = f"""【AIクイズ】

{quiz["question"]}

1. {quiz["choices"][0]}
2. {quiz["choices"][1]}
3. {quiz["choices"][2]}
4. {quiz["choices"][3]}

数字で答えてください。
"""

    return text

# ---------------------------
# 回答判定
# ---------------------------
def check_answer(user_id, text):

    if user_id not in USER_STATE:
        return "先に『AIテスト』と送ってください。"

    quiz = USER_STATE[user_id]

    try:
        answer = int(text) - 1
    except:
        return "1〜4で答えてください。"

    correct = quiz["answer"]

    if answer == correct:

        msg = f"""⭕ 正解！

{quiz["explanation"]}

次の問題は
AIテスト
と送ってください。
"""

    else:

        msg = f"""❌ 不正解

正解
{correct+1}. {quiz["choices"][correct]}

{quiz["explanation"]}

次の問題は
AIテスト
と送ってください。
"""

    USER_STATE.pop(user_id, None)

    return msg

# ---------------------------
# 動作確認
# ---------------------------
@app.route("/", methods=["GET"])
def home():
    return "LINE BOT RUNNING", 200

# ---------------------------
# LINE Webhook
# ---------------------------
@app.route("/callback", methods=["POST"])
def callback():

    signature = request.headers.get('X-Line-Signature')
    body = request.get_data()

    if not verify_signature(body, signature):
        abort(400)

    data = json.loads(body)

    for event in data["events"]:

        if event["type"] != "message":
            continue

        if event["message"]["type"] != "text":
            continue

        reply_token = event["replyToken"]
        user_id = event["source"]["userId"]
        text = event["message"]["text"]

        # クイズ開始
        if text == "AIテスト":

            msg = start_quiz(user_id)

            reply_message(reply_token, msg)

        # 回答
        elif text in ["1","2","3","4"]:

            msg = check_answer(user_id, text)

            reply_message(reply_token, msg)

        else:

            msg = """使い方

AIテスト
→ AIクイズ開始

1〜4
→ 回答"""

            reply_message(reply_token, msg)

    return "OK"

# ---------------------------
# Render用
# ---------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
