from flask import Flask, request, abort
import os
import random

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    MessagingApi,
    Configuration,
    ApiClient,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ユーザーごとの現在の問題を一時保存
# 本格運用ではDB推奨ですが、まずは簡単版
user_quiz_state = {}

# AI用語クイズ
QUIZ_DATA = [
    {
        "question": "AIとは何の略ですか？",
        "choices": [
            "Artificial Intelligence",
            "Automatic Internet",
            "Advanced Input",
            "Applied Information",
        ],
        "answer": 1,
        "explanation": "AIは Artificial Intelligence（人工知能）の略です。"
    },
    {
        "question": "ChatGPTが得意なのはどれですか？",
        "choices": [
            "自然な文章の生成",
            "自動で料理を作ること",
            "自動で車を修理すること",
            "空を飛ぶこと",
        ],
        "answer": 1,
        "explanation": "ChatGPTは自然言語の理解と文章生成が得意です。"
    },
    {
        "question": "プロンプトとは何ですか？",
        "choices": [
            "AIに与える指示文",
            "パソコンの画面",
            "マウスの右ボタン",
            "インターネット回線",
        ],
        "answer": 1,
        "explanation": "プロンプトは、AIに対する指示や入力文のことです。"
    },
    {
        "question": "機械学習とは何ですか？",
        "choices": [
            "機械を掃除する技術",
            "データからパターンを学ぶ技術",
            "機械を分解する作業",
            "電源を入れる方法",
        ],
        "answer": 2,
        "explanation": "機械学習はデータから傾向やルールを学習する技術です。"
    },
    {
        "question": "画像生成AIでできることとして近いのはどれですか？",
        "choices": [
            "文章から画像を作る",
            "画像を食べる",
            "電気代を自動で払う",
            "家を建てる",
        ],
        "answer": 1,
        "explanation": "画像生成AIは、文章指示から画像を作ることができます。"
    },
]


def get_quiz_text(quiz):
    lines = [
        f"【AI用語クイズ】\n{quiz['question']}",
        "",
        f"1. {quiz['choices'][0]}",
        f"2. {quiz['choices'][1]}",
        f"3. {quiz['choices'][2]}",
        f"4. {quiz['choices'][3]}",
        "",
        "答えは 1〜4 で送ってください。",
    ]
    return "\n".join(lines)


def make_reply(text):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        return line_bot_api, [TextMessage(text=text)]


@app.route("/")
def home():
    return "LINE BOT OK"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("error:", e)
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text.strip()

    reply_text = ""

    # 開始系
    if user_text in ["クイズ", "くいず", "問題", "スタート", "開始"]:
        quiz = random.choice(QUIZ_DATA)
        user_quiz_state[user_id] = quiz
        reply_text = get_quiz_text(quiz)

    # 回答系
    elif user_text in ["1", "2", "3", "4"]:
        if user_id not in user_quiz_state:
            reply_text = "先に「クイズ」と送ってください。"
        else:
            quiz = user_quiz_state[user_id]
            user_answer = int(user_text)

            if user_answer == quiz["answer"]:
                reply_text = (
                    f"⭕ 正解！\n\n"
                    f"{quiz['explanation']}\n\n"
                    f"次の問題をやるなら「クイズ」と送ってください。"
                )
            else:
                correct_choice_text = quiz["choices"][quiz["answer"] - 1]
                reply_text = (
                    f"❌ 不正解\n\n"
                    f"正解は {quiz['answer']}. {correct_choice_text}\n"
                    f"{quiz['explanation']}\n\n"
                    f"次の問題をやるなら「クイズ」と送ってください。"
                )

            del user_quiz_state[user_id]

    # ヘルプ
    elif user_text in ["help", "ヘルプ", "使い方"]:
        reply_text = (
            "【使い方】\n"
            "・「クイズ」で問題開始\n"
            "・「1」「2」「3」「4」で回答\n"
            "・もう一度やるときは「クイズ」"
        )

    else:
        reply_text = (
            "AI用語クイズBOTです。\n"
            "「クイズ」と送ると4択問題を出します。"
        )

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    app.run()