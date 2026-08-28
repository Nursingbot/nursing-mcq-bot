import os
import json
import sqlite3
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# अपना Telegram numeric user ID बाद में यहाँ डालना
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

PREMIUM_PRICE = 49

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    premium INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0
)
""")

conn.commit()


def add_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()


def is_premium(user_id):
    cursor.execute(
        "SELECT premium FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    return bool(row and row[0] == 1)


def set_premium(user_id, value=1):
    cursor.execute(
        "UPDATE users SET premium=? WHERE user_id=?",
        (value, user_id)
    )
    conn.commit()


def add_score(user_id):
    cursor.execute(
        "UPDATE users SET score=score+1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def get_score(user_id):
    cursor.execute(
        "SELECT score FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else 0


# =========================
# QUESTIONS
# =========================

try:
    with open("questions.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
except Exception:
    QUESTIONS = []


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    add_user(user.id)

    keyboard = [
        [
            InlineKeyboardButton("🆓 Free MCQ", callback_data="free")
        ],
        [
            InlineKeyboardButton("📝 Mock Test", callback_data="mock")
        ],
        [
            InlineKeyboardButton("📊 My Score", callback_data="score")
        ],
        [
            InlineKeyboardButton(
                "🔒 Premium ₹49",
                callback_data="premium"
            )
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help")
        ],
    ]

    await update.message.reply_text(
        f"🩺 *Nursing Prep Pro*\n\n"
        f"📚 GNM | ANM | B.Sc Nursing\n"
        f"📝 Nursing MCQ & Mock Tests\n"
        f"🏆 Premium Question Bank\n\n"
        f"👇 नीचे से option चुनें:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =========================
# SEND QUESTION
# =========================

async def send_question(query, user_id):

    if not QUESTIONS:
        await query.message.reply_text(
            "❌ अभी questions.json में कोई question नहीं मिला।"
        )
        return

    question = random.choice(QUESTIONS)

    text = question.get("question", "Question missing")
    options = question.get("options", [])
    answer = question.get("answer", 0)

    keyboard = []

    for i, option in enumerate(options):
        keyboard.append([
            InlineKeyboardButton(
                option,
                callback_data=f"ans:{answer}:{i}"
            )
        ])

    await query.message.reply_text(
        f"🩺 *Nursing MCQ*\n\n{text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    add_user(user_id)

    data = query.data

    # FREE MCQ
    if data == "free":
        await send_question(query, user_id)
        return

    # NEXT / MOCK
    if data == "mock":
        await send_question(query, user_id)
        return

    # SCORE
    if data == "score":
        score = get_score(user_id)

        await query.message.reply_text(
            f"📊 *Your Score*\n\n"
            f"Correct Answers: {score}",
            parse_mode="Markdown",
        )
        return

    # PREMIUM
    if data == "premium":

        if is_premium(user_id):
            await query.message.reply_text(
                "✅ आपका Premium पहले से active है।"
            )
            await send_question(query, user_id)
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 Pay ₹49",
                    callback_data="pay"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data="back"
                )
            ],
        ]

        await query.message.reply_text(
            "🔒 *Premium Nursing Pack*\n\n"
            "💰 Price: ₹49\n\n"
            "Premium में मिलेगा:\n"
            "✅ Premium MCQs\n"
            "✅ Mock Tests\n"
            "✅ Answer Checking\n"
            "✅ Score System\n"
            "✅ Premium Question Bank\n\n"
            "👇 Premium लेने के लिए नीचे दबाएँ।",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    # PAYMENT INSTRUCTION
    if data == "pay":

        await query.message.reply_text(
            "💰 *Premium Price: ₹49*\n\n"
            "Payment करने के बाद अपना Telegram User ID "
            "admin को भेजें।\n\n"
            "⚠️ अभी payment verification manual है।\n"
            "Payment verify होने के बाद admin आपके Premium को activate करेगा।\n\n"
            "अपना User ID देखने के लिए /id लिखें।",
            parse_mode="Markdown",
        )
        return

    # HELP
    if data == "help":

        await query.message.reply_text(
            "❓ *Help*\n\n"
            "/start - Main Menu\n"
            "/id - अपना User ID\n"
            "/score - अपना Score\n"
            "/premium - Premium जानकारी",
            parse_mode="Markdown",
        )
        return

    # BACK
    if data == "back":
        await start_from_callback(query)
        return

    # ANSWER
    if data.startswith("ans:"):

        parts = data.split(":")

        correct = int(parts[1])
        selected = int(parts[2])

        if selected == correct:
            add_score(user_id)

            await query.message.reply_text(
                "✅ *सही उत्तर!*\n\n"
                "बहुत बढ़िया! 🎉",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text(
                "❌ *गलत उत्तर!*\n\n"
                f"सही option: {correct + 1}",
                parse_mode="Markdown",
            )

        keyboard = [
            [
                InlineKeyboardButton(
                    "➡️ Next Question",
                    callback_data="free"
                )
            ]
        ]

        await query.message.reply_text(
            "अगला question:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# =========================
# CALLBACK START
# =========================

async def start_from_callback(query):

    keyboard = [
        [
            InlineKeyboardButton("🆓 Free MCQ", callback_data="free")
        ],
        [
            InlineKeyboardButton("📝 Mock Test", callback_data="mock")
        ],
        [
            InlineKeyboardButton("📊 My Score", callback_data="score")
        ],
        [
            InlineKeyboardButton(
                "🔒 Premium ₹49",
                callback_data="premium"
            )
        ],
    ]

    await query.message.reply_text(
        "🩺 *Nursing Prep Pro*\n\n"
        "👇 Option चुनें:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =========================
# COMMANDS
# =========================

async def user_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"🆔 आपका Telegram User ID:\n\n"
        f"`{update.effective_user.id}`",
        parse_mode="Markdown",
    )


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    add_user(update.effective_user.id)

    score = get_score(update.effective_user.id)

    await update.message.reply_text(
        f"📊 आपका Score: {score}"
    )


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if is_premium(user_id):
        await update.message.reply_text(
            "✅ आपका Premium active है।"
        )
    else:
        await update.message.reply_text(
            "🔒 Premium Nursing Pack\n\n"
            "💰 Price: ₹49\n\n"
            "Premium MCQ और Mock Test पाने के लिए /start दबाएँ।"
        )


# =========================
# ADMIN COMMAND
# =========================

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ आप admin नहीं हैं।"
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n/approve USER_ID"
        )
        return

    try:
        user_id = int(context.args[0])
        add_user(user_id)
        set_premium(user_id, 1)

        await update.message.reply_text(
            f"✅ Premium activated for {user_id}"
        )

    except ValueError:
        await update.message.reply_text(
            "❌ सही User ID डालें।"
        )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable missing.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", user_id_command))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("approve", approve_command))

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("🤖 Nursing Prep Pro Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
