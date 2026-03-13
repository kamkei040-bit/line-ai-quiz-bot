import os
import json
import hmac
import hashlib
import base64
import random
from typing import Dict, Any

import requests
from flask import Flask, request, abort

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("環境変数 LINE_CHANNEL_ACCESS_TOKEN が未設定です。")

if not LINE_CHANNEL_SECRET:
    raise ValueError("環境変数 LINE_CHANNEL_SECRET が未設定です。")

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

# ユーザーごとの出題状態を一時保存
USER_STATE: Dict[str, Dict[str, Any]] = {}

# 問題データ
QUIZ_DATA = [
    {
        "question": "AIがもっともらしい誤情報を生成する現象は？",
        "choices": ["ハルシネーション", "プロンプト", "トークン", "DX"],
        "answer_index": 0,
        "explanation": "ハルシネーションは、AIが事実ではない内容をもっともらしく生成する現象です。"
    },
    {
        "question": "AIへの指示文のことは？",
        "choices": ["バイアス", "プロンプト", "AGI", "著作権"],
        "answer_index": 1,
        "explanation": "プロンプトは、AIに対して与える指示文です。"
    },
    {
        "question": "大量の文章データで学習した大規模言語モデルは？",
        "choices": ["OCR", "CPU", "LLM", "DX"],
        "answer_index": 2,
        "explanation": "LLM は Large Language Model の略で、大規模言語モデルです。"
    },
    {
        "question": "データの偏りによってAIの結果が偏ることを何という？",
        "choices": ["自動化", "バイアス", "透明性", "著作権"],
        "answer_index": 1,
        "explanation": "バイアスは、データや判断の偏りのことです。"
    },
    {
        "question": "創作物を守る法律上の権利は？",
        "choices": ["個人情報", "著作権", "機密情報", "プライバシー"],
        "answer_index": 1,
        "explanation": "著作権は、文章・画像・音楽などの創作物を守る権利です。"
    },
    {
        "question": "AIの判断過程が説明しやすいことを何という？",
        "choices": ["透明性", "自動化", "規制", "学習率"],
        "answer_index": 0,
        "explanation": "透明性は、AIの判断や動作が分かりやすく説明できることです。"
    },
    {
        "question": "文章や画像などを新しく作り出すAIを何という？",
        "choices": ["検索AI", "生成AI", "監視AI", "認証AI"],
        "answer_index": 1,
        "explanation": "生成AIは、文章・画像・音声などを新しく生成するAIです。"
    },
    {
        "question": "AIの安全な利用や管理のためのルール整備を何という？",
        "choices": ["AIガバナンス", "プロンプト", "トークン化", "レンダリング"],
        "answer_index": 0,
        "explanation": "AIガバナンスは、AIを安全かつ適切に運用するための管理や統制です。"
    },
    {
        "question": "個人を特定できる情報を何という？",
        "choices": ["機密情報", "個人情報", "著作物", "公開情報"],
        "answer_index": 1,
        "explanation": "個人情報は、氏名や住所など個人を特定できる情報です。"
    },
    {
        "question": "業務をデジタル技術で変革することを何という？",
        "choices": ["API", "DX", "GPU", "OCR"],
        "answer_index": 1,
        "explanation": "DX は Digital Transformation の略で、デジタル技術による業務変革です。"
    }
]


def verify_signature(request_body: bytes, signature: str) -> bool:
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        request_body,
        hashlib.sha256
    ).digest()
    computed_signature = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed_signature, signature)


def reply_message(reply_token: str, text: str) -> None:
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

    response = requests.post(
        LINE_REPLY_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=10
    )
    print("LINE reply status:", response.status_code)
    print("LINE reply body:", response.text)


def build_quiz_text(quiz: Dict[str, Any]) -> str:
    lines = [
        "【AI用語クイズ】",
        "",
        quiz["question"],
        ""
    ]

    for i, choice in enumerate(quiz["choices"], start=1):
        lines.append(f"{i}. {choice}")

    lines.extend([
        "",
        "1〜4の数字で答えてください。"
    ])
    return "\n".join(lines)


def start_quiz_for_user(user_id: str) -> str:
    quiz = random.choice(QUIZ_DATA)
    USER_STATE[user_id] = {
        "quiz": quiz
    }
    return build_quiz_text(quiz)


def check_answer(user_id: str, user_text: str) -> str:
    state = USER_STATE.get(user_id)
    if not state:
        return "先に「AIテスト」と送ってください。"

    quiz = state["quiz"]

    try:
        selected_index = int(user_text) - 1
    except ValueError:
        return "1〜4の数字で答えてください。"

    correct_index = quiz["answer_index"]

    if selected_index == correct_index:
        result = (
            "⭕ 正解です！\n\n"
            f"正解：{quiz['choices'][correct_index]}\n"
            f"{quiz['explanation']}\n\n"
            "次の問題は\nAIテスト\nと送ってください。"
        )
    else:
        result = (
            "❌ 不正解です。\n\n"
            f"正解：{correct_index + 1}. {quiz['choices'][correct_index]}\n"
            f"{quiz['explanation']}\n\n"
            "次の問題は\nAIテスト\nと送ってください。"
        )

    USER_STATE.pop(user_id, None)
    return result


@app.route("/", methods=["GET"])
def home():
    return "LINE AI Quiz Bot is running!", 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data()

    if not verify_signature(body, signature):
        abort(400)

    payload = request.get_json(silent=True)
    if not payload:
        return "OK", 200

    for event in payload.get("events", []):
        if event.get("type") != "message":
            continue

        message = event.get("message", {})
        if message.get("type") != "text":
            continue

        reply_token = event.get("replyToken")
        user_text = message.get("text", "").strip()
        user_id = event.get("source", {}).get("userId", "unknown")

        if user_text == "AIテスト":
            text = start_quiz_for_user(user_id)
            reply_message(reply_token, text)
            continue

        if user_text in ["1", "2", "3", "4"]:
            text = check_answer(user_id, user_text)
            reply_message(reply_token, text)
            continue

        help_text = (
            "使い方\n\n"
            "AIテスト\n"
            "→ AI用語クイズを1問出します\n\n"
            "1〜4\n"
            "→ 答えます"
        )
        reply_message(reply_token, help_text)

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
