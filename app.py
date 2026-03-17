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

# -----------------------------------
# ユーザーごとの出題状態をメモリ上で保持
# ※ Render再起動などで消えます
# -----------------------------------
user_sessions = {}


def send_reply(reply_token, text):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )


def get_user_id(event):
    # user / group / room いずれでも source 内に user_id があれば優先
    source = event.source
    if hasattr(source, "user_id") and source.user_id:
        return source.user_id

    # 念のため fallback
    return "unknown_user"


def format_quiz(quiz, number=None):
    choices_text = "\n".join(
        [f"{i + 1}. {choice}" for i, choice in enumerate(quiz["choices"])]
    )

    header = "【AIパスポート問題】"
    if number is not None:
        header = f"【AIパスポート問題 第{number}問】"

    return (
        f"{header}\n"
        f"分野：{quiz['category']}\n\n"
        f"{quiz['question']}\n\n"
        f"{choices_text}\n\n"
        f"答えは 1〜4 で入力してください。"
    )


def format_result_message(quiz, user_answer):
    correct_number = quiz["answer"]
    correct_text = quiz["choices"][correct_number - 1]

    if user_answer == correct_number:
        judge = "⭕ 正解です！"
    else:
        judge = f"❌ 不正解です。\nあなたの回答：{user_answer}. {quiz['choices'][user_answer - 1]}"

    return (
        f"{judge}\n\n"
        f"【正解】\n"
        f"{correct_number}. {correct_text}\n\n"
        f"【解説】\n"
        f"{quiz['explanation']}"
    )


def start_new_quiz_for_user(user_id):
    quiz = random.choice(QUIZ_DATA)

    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_quiz": None,
            "question_count": 0,
            "correct_count": 0,
        }

    user_sessions[user_id]["current_quiz"] = quiz
    user_sessions[user_id]["question_count"] += 1

    return quiz, user_sessions[user_id]["question_count"]


def get_help_message():
    return (
        "AIパスポート問題botです。\n\n"
        "【使い方】\n"
        "・「問題」→ 1問出題\n"
        "・「次」→ 次の問題を出題\n"
        "・「1」「2」「3」「4」→ 回答\n"
        "・「スコア」→ 現在の正答数を表示\n"
        "・「リセット」→ 成績をリセット\n"
        "・「ヘルプ」→ この説明を表示\n\n"
        "まずは「問題」と送ってください。"
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
    normalized = user_text.lower()
    user_id = get_user_id(event)

    # セッション未作成なら初期化
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_quiz": None,
            "question_count": 0,
            "correct_count": 0,
        }

    session = user_sessions[user_id]

    # ----------------------------
    # 問題出題
    # ----------------------------
    if normalized in ["問題", "もんだい", "quiz", "q", "次", "つぎ", "next"]:
        quiz, number = start_new_quiz_for_user(user_id)
        send_reply(event.reply_token, format_quiz(quiz, number))
        return

    # ----------------------------
    # 回答処理
    # ----------------------------
    if user_text in ["1", "2", "3", "4"]:
        if session["current_quiz"] is None:
            send_reply(
                event.reply_token,
                "まだ問題が出題されていません。\nまずは「問題」と送ってください。"
            )
            return

        user_answer = int(user_text)
        current_quiz = session["current_quiz"]

        if user_answer == current_quiz["answer"]:
            session["correct_count"] += 1

        result_message = format_result_message(current_quiz, user_answer)

        total = session["question_count"]
        correct = session["correct_count"]

        # 回答後は current_quiz を空にする
        session["current_quiz"] = None

        send_reply(
            event.reply_token,
            result_message
            + f"\n\n【現在の成績】\n{correct} / {total} 問正解"
            + "\n\n次の問題は「問題」または「次」と送ってください。"
        )
        return

    # ----------------------------
    # スコア表示
    # ----------------------------
    if normalized in ["スコア", "score", "成績"]:
        total = session["question_count"]
        correct = session["correct_count"]
        unanswered = 1 if session["current_quiz"] is not None else 0

        message = (
            "【現在の成績】\n"
            f"正解数：{correct}\n"
            f"出題数：{total}\n"
        )

        if unanswered:
            message += "\n未回答の問題が1問あります。"

        send_reply(event.reply_token, message)
        return

    # ----------------------------
    # リセット
    # ----------------------------
    if normalized in ["リセット", "reset", "初期化"]:
        user_sessions[user_id] = {
            "current_quiz": None,
            "question_count": 0,
            "correct_count": 0,
        }
        send_reply(event.reply_token, "成績をリセットしました。\n「問題」と送ると再開できます。")
        return

    # ----------------------------
    # ヘルプ
    # ----------------------------
    if normalized in ["ヘルプ", "help", "使い方"]:
        send_reply(event.reply_token, get_help_message())
        return

    # ----------------------------
    # その他
    # ----------------------------
    send_reply(event.reply_token, get_help_message())


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
