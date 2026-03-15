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

# ----------------------------
# 問題データ
# answer は 1〜4
# category は分野名
# ----------------------------
QUIZ_DATA = [
    {
        "category": "用語",
        "question": "AIとは何の略ですか？",
        "choices": [
            "Artificial Intelligence",
            "Automatic Internet",
            "Applied Interface",
            "Advanced Input",
        ],
        "answer": 1,
        "explanation": "AIは Artificial Intelligence（人工知能）の略です。"
    },
    {
        "category": "用語",
        "question": "プロンプトとして最も適切なのはどれですか？",
        "choices": [
            "AIへの指示文",
            "パソコン本体",
            "通信回線",
            "OSの名前",
        ],
        "answer": 1,
        "explanation": "プロンプトは、AIに与える指示や入力文のことです。"
    },
    {
        "category": "機械学習",
        "question": "機械学習の説明として適切なのはどれですか？",
        "choices": [
            "機械を分解して仕組みを学ぶこと",
            "データからパターンを学習する技術",
            "人がすべて手でルールを書くこと",
            "電源を自動で入れること",
        ],
        "answer": 2,
        "explanation": "機械学習はデータから特徴や傾向を学ぶ技術です。"
    },
    {
        "category": "機械学習",
        "question": "教師あり学習の説明として最も近いものはどれですか？",
        "choices": [
            "正解ラベルのないデータだけで学ぶ",
            "正解付きデータを使って学ぶ",
            "一切データを使わず学ぶ",
            "必ず画像だけを学ぶ",
        ],
        "answer": 2,
        "explanation": "教師あり学習は、正解付きデータを用いて学習させる方法です。"
    },
    {
        "category": "生成AI",
        "question": "生成AIの代表的な活用例として適切なのはどれですか？",
        "choices": [
            "文章や画像の生成",
            "電源コードの修理",
            "建物の自動建築",
            "道路工事の実施",
        ],
        "answer": 1,
        "explanation": "生成AIは文章、画像、音声などの新しいコンテンツ生成に使われます。"
    },
    {
        "category": "生成AI",
        "question": "ハルシネーションとして最も近いものはどれですか？",
        "choices": [
            "AIが学習を完全停止すること",
            "AIが事実でない内容をもっともらしく出すこと",
            "AIの処理速度が上がること",
            "画像の解像度が上がること",
        ],
        "answer": 2,
        "explanation": "ハルシネーションは、AIが誤情報を自然な文章で出力してしまう現象です。"
    },
    {
        "category": "法律倫理",
        "question": "個人情報を扱う場面で特に重要なのはどれですか？",
        "choices": [
            "無断で公開すること",
            "適切な管理と利用目的の明確化",
            "誰でも自由に閲覧できる状態にすること",
            "保存先を増やし続けること",
        ],
        "answer": 2,
        "explanation": "個人情報は適切に管理し、利用目的を明確にすることが重要です。"
    },
    {
        "category": "法律倫理",
        "question": "AI利用時の倫理面で重要な観点として適切なのはどれですか？",
        "choices": [
            "公平性や透明性への配慮",
            "結果が出れば根拠は不要",
            "偏りは多いほどよい",
            "説明責任は不要",
        ],
        "answer": 1,
        "explanation": "AIの利用では、公平性、透明性、説明責任などが重要です。"
    },
    {
        "category": "セキュリティ",
        "question": "パスワード管理として望ましいのはどれですか？",
        "choices": [
            "すべて同じ簡単な文字列にする",
            "強固で使い回ししない",
            "他人と共有する",
            "紙に貼って公開する",
        ],
        "answer": 2,
        "explanation": "パスワードは強固にし、使い回しを避けることが重要です。"
    },
    {
        "category": "セキュリティ",
        "question": "フィッシング詐欺への対策として適切なのはどれですか？",
        "choices": [
            "届いたURLをすぐ開く",
            "送信元やURLを確認する",
            "パスワードを毎回入力する",
            "警告を無視する",
        ],
        "answer": 2,
        "explanation": "不審なメールやURLは、送信元やリンク先を確認することが重要です。"
    },
]

CATEGORIES = ["用語", "機械学習", "生成AI", "法律倫理", "セキュリティ"]

# ユーザーごとの状態
user_state = {}
# 例:
# user_state[user_id] = {
#   "mode": "single" or "test",
#   "category": "用語" or None,
#   "current_quiz": quiz_dict,
#   "remaining": [quiz1, quiz2, ...],
#   "correct": 0,
#   "total": 10
# }

def build_quiz_text(quiz, prefix="【AIパスポート問題】"):
    return (
        f"{prefix}\n"
        f"分野：{quiz['category']}\n\n"
        f"{quiz['question']}\n\n"
        f"1. {quiz['choices'][0]}\n"
        f"2. {quiz['choices'][1]}\n"
        f"3. {quiz['choices'][2]}\n"
        f"4. {quiz['choices'][3]}\n\n"
        f"答えは 1〜4 で送ってください。"
    )

def pick_one_quiz(category=None, exclude_questions=None):
    pool = QUIZ_DATA
    if category:
        pool = [q for q in pool if q["category"] == category]
    if exclude_questions:
        pool = [q for q in pool if q["question"] not in exclude_questions]
    if not pool:
        return None
    return random.choice(pool)

def start_single_quiz(user_id, category=None):
    quiz = pick_one_quiz(category=category)
    if not quiz:
        return "その分野の問題がまだありません。"

    user_state[user_id] = {
        "mode": "single",
        "category": category,
        "current_quiz": quiz,
        "remaining": [],
        "correct": 0,
        "total": 1
    }

    prefix = "【AIパスポート1問】"
    return build_quiz_text(quiz, prefix=prefix)

def start_test_quiz(user_id, category=None, total=10):
    pool = QUIZ_DATA if category is None else [q for q in QUIZ_DATA if q["category"] == category]

    if len(pool) == 0:
        return "その分野の問題がまだありません。"

    total = min(total, len(pool))
    selected = random.sample(pool, total)

    first_quiz = selected[0]
    remaining = selected[1:]

    user_state[user_id] = {
        "mode": "test",
        "category": category,
        "current_quiz": first_quiz,
        "remaining": remaining,
        "correct": 0,
        "total": total
    }

    category_text = f"（分野：{category}）" if category else ""
    prefix = f"【AIパスポート {total}問テスト開始】{category_text}\n1/{total}問目"
    return build_quiz_text(first_quiz, prefix=prefix)

def handle_answer(user_id, answer_text):
    if user_id not in user_state:
        return "先に「クイズ」または「10問」と送ってください。"

    state = user_state[user_id]
    quiz = state["current_quiz"]
    user_answer = int(answer_text)
    is_correct = user_answer == quiz["answer"]

    if is_correct:
        state["correct"] += 1
        result_text = f"⭕ 正解！\n\n{quiz['explanation']}"
    else:
        correct_choice_text = quiz["choices"][quiz["answer"] - 1]
        result_text = (
            f"❌ 不正解\n\n"
            f"正解は {quiz['answer']}. {correct_choice_text}\n"
            f"{quiz['explanation']}"
        )

    if state["mode"] == "single":
        del user_state[user_id]
        return result_text + "\n\n次の問題をやるなら「クイズ」と送ってください。"

    # test mode
    answered_count = state["total"] - len(state["remaining"])

    if state["remaining"]:
        next_quiz = state["remaining"].pop(0)
        state["current_quiz"] = next_quiz
        next_number = answered_count + 1

        next_text = build_quiz_text(
            next_quiz,
            prefix=f"【次の問題】\n{next_number}/{state['total']}問目"
        )
        return (
            f"{result_text}\n\n"
            f"現在 {answered_count}/{state['total']}問終了 "
            f"（正解 {state['correct']}問）\n\n"
            f"{next_text}"
        )
    else:
        score_text = (
            f"{result_text}\n\n"
            f"【テスト終了】\n"
            f"正解数：{state['correct']} / {state['total']}"
        )

        if state["correct"] == state["total"]:
            score_text += "\n素晴らしいです！満点です。"
        elif state["correct"] >= max(1, int(state["total"] * 0.8)):
            score_text += "\nかなり仕上がっています。"
        elif state["correct"] >= max(1, int(state["total"] * 0.6)):
            score_text += "\n順調です。復習するとさらに安定します。"
        else:
            score_text += "\n基礎用語の復習から固めるのがおすすめです。"

        del user_state[user_id]
        return score_text + "\n\nもう一度やるなら「10問」と送ってください。"

def help_text():
    return (
        "【使い方】\n"
        "・クイズ → ランダムで1問\n"
        "・10問 → ランダムで10問テスト\n"
        "・用語 / 機械学習 / 生成AI / 法律倫理 / セキュリティ → 分野別1問\n"
        "・用語10問 / 機械学習10問 など → 分野別テスト\n"
        "・1 / 2 / 3 / 4 → 回答\n"
        "・ヘルプ → 使い方表示"
    )

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

    if user_text in ["1", "2", "3", "4"]:
        reply_text = handle_answer(user_id, user_text)

    elif user_text in ["クイズ", "1問"]:
        reply_text = start_single_quiz(user_id)

    elif user_text == "10問":
        reply_text = start_test_quiz(user_id, total=10)

    elif user_text in CATEGORIES:
        reply_text = start_single_quiz(user_id, category=user_text)

    elif user_text.endswith("10問"):
        category_name = user_text.replace("10問", "").strip()
        if category_name in CATEGORIES:
            reply_text = start_test_quiz(user_id, category=category_name, total=10)
        else:
            reply_text = "その分野は未対応です。ヘルプで使い方を確認してください。"

    elif user_text in ["ヘルプ", "help", "使い方"]:
        reply_text = help_text()

    else:
        reply_text = (
            "AIパスポート試験対策BOTです。\n"
            "「クイズ」「10問」「ヘルプ」と送ってください。"
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