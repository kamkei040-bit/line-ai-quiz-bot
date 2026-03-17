from flask import Flask, request, abort
import os
import random

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from quiz_data import QUIZ_DATA

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("CHANNEL_ACCESS_TOKEN または CHANNEL_SECRET が設定されていません。")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


def send_reply(reply_token, text):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )


def format_quiz(quiz):
    choices_text = "\n".join(
        [f"{i + 1}. {choice}" for i, choice in enumerate(quiz["choices"])]
    )
    return (
        f"【AIパスポート問題】\n"
        f"分野：{quiz['category']}\n\n"
        f"{quiz['question']}\n\n"
        f"{choices_text}\n\n"
        f"答えは 1〜4 で入力してください。"
    )


def format_answer(quiz):
    correct_number = quiz["answer"]
    correct_text = quiz["choices"][correct_number - 1]
    return (
        f"【正解】\n"
        f"{correct_number}. {correct_text}\n\n"
        f"【解説】\n"
        f"{quiz['explanation']}"
    )


@app.route("/")
def home():
    return "AI Passport Quiz Bot is running!"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("Webhook error:", e)
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip()

    # 小文字化して判定しやすくする
    normalized = user_text.lower()

    if normalized in ["問題", "もんだい", "quiz", "q", "次", "つぎ", "next"]:
        quiz = random.choice(QUIZ_DATA)
        message = format_quiz(quiz)
        send_reply(event.reply_token, message)
        return

    # 1〜4 の入力で、ランダムに解答解説を返す簡易版
    # ※現状は「直前の問題を記憶する機能」は入れていません
    if user_text in ["1", "2", "3", "4"]:
        quiz = random.choice(QUIZ_DATA)
        message = (
            "※この版は整理版のため、回答番号に対してランダム問題の解説を返す簡易構成です。\n\n"
            + format_answer(quiz)
            + "\n\n次の問題は「問題」と送ってください。"
        )
        send_reply(event.reply_token, message)
        return

    help_message = (
        "AIパスポート問題botです。\n\n"
        "使い方：\n"
        "・「問題」→ ランダムで1問出題\n"
        "・「次」→ 次の問題を出題\n"
        "・「1」「2」「3」「4」→ 回答番号を送信\n\n"
        "まずは「問題」と送ってください。"
    )
    send_reply(event.reply_token, help_message)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
