"""
Neymar haqida Telegram bot
--------------------------
Funksiyalar:
  /start   - salomlashish va menyu
  /bio     - Neymar haqida qisqa ma'lumot
  /stats   - karyera statistikasi
  /news    - so'nggi yangiliklar (Google News RSS orqali)
  /quiz    - viktorina (bir nechta savol)
  Oddiy xabar -> AI bilan erkin suhbat (Neymar mavzusida)

Ishga tushirish:
  1) pip install -r requirements.txt
  2) .env faylida TELEGRAM_BOT_TOKEN va (ixtiyoriy) ANTHROPIC_API_KEY ni to'ldiring
  3) python bot.py
"""

import logging
import os
import random
import html
import feedparser
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # AI suhbat uchun (ixtiyoriy)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Statik ma'lumotlar (2026-yil boshigacha bo'lgan ma'lumotlar asosida;
# eng so'nggi raqamlar uchun /news buyrug'idan foydalaning)
# ---------------------------------------------------------------------------

BIO_TEXT = (
    "⚽️ <b>Neymar da Silva Santos Júnior</b>\n\n"
    "📅 Tug'ilgan sana: 5-fevral, 1992\n"
    "🌍 Tug'ilgan joyi: Mogi das Cruzes, Braziliya\n"
    "🎽 Pozitsiyasi: Hujumchi / Qanot hujumchisi\n\n"
    "Braziliyalik yulduz Santos klubida professional futbolni boshlagan, "
    "so'ngra Barcelona, Paris Saint-Germain va Al-Hilal kabi klublarda o'ynagan. "
    "U texnik mahorati, driblingi va gol pas berish qobiliyati bilan mashhur."
)

STATS_TEXT = (
    "📊 <b>Karyera statistikasi (asosiy bosqichlar)</b>\n\n"
    "🔹 Santos: 2009–2013\n"
    "🔹 Barcelona: 2013–2017 (MSN uchligi: Messi-Suárez-Neymar)\n"
    "🔹 Paris Saint-Germain: 2017–2023\n"
    "🔹 Al-Hilal (Saudiya Arabistoni): 2023 yildan\n\n"
    "🏆 Yutuqlari: Copa Libertadores, Champions League, ko'plab milliy chempionatlar, "
    "Olimpiada oltin medali (2016, Braziliya milliy jamoasi bilan).\n\n"
    "ℹ️ Aniq gol/pas statistikasi doimiy o'zgarib turadi — so'nggi raqamlarni "
    "/news orqali yoki rasmiy manbalardan tekshiring."
)

QUIZ_QUESTIONS = [
    {
        "question": "Neymar qaysi klubda professional futbolni boshlagan?",
        "options": ["Barcelona", "Santos", "PSG", "Flamengo"],
        "correct": 1,
    },
    {
        "question": "Neymar qaysi yili Barcelonaga o'tgan?",
        "options": ["2011", "2013", "2015", "2017"],
        "correct": 1,
    },
    {
        "question": "2016-yilgi Olimpiada o'yinlarida Braziliya qaysi medalni yutgan (Neymar ishtirokida)?",
        "options": ["Kumush", "Bronza", "Oltin", "Medal yo'q"],
        "correct": 2,
    },
    {
        "question": "Neymar tug'ilgan mamlakat qaysi?",
        "options": ["Argentina", "Portugaliya", "Braziliya", "Ispaniya"],
        "correct": 2,
    },
]

NEWS_RSS_URL = "https://news.google.com/rss/search?q=Neymar&hl=uz&gl=UZ&ceid=UZ:uz"

# ---------------------------------------------------------------------------
# Buyruqlar
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 Bio", callback_data="bio"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📰 Yangiliklar", callback_data="news"),
         InlineKeyboardButton("🧠 Viktorina", callback_data="quiz")],
    ]
    await update.message.reply_text(
        "👋 Salom! Men Neymar haqidagi botman.\n\n"
        "Quyidagi bo'limlardan birini tanlang yoki menga shunchaki savol yozing — "
        "men Neymar haqida suhbatlashaman!",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def bio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(BIO_TEXT, parse_mode=ParseMode.HTML)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(STATS_TEXT, parse_mode=ParseMode.HTML)


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Yangiliklar qidirilmoqda...")
    try:
        feed = feedparser.parse(NEWS_RSS_URL)
        entries = feed.entries[:5]
        if not entries:
            await update.message.reply_text("Hozircha yangilik topilmadi. Keyinroq urinib ko'ring.")
            return
        lines = ["📰 <b>So'nggi yangiliklar:</b>\n"]
        for entry in entries:
            title = html.escape(entry.title)
            link = entry.link
            lines.append(f"• <a href='{link}'>{title}</a>")
        await update.message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("⚠️ Yangiliklarni yuklashda xatolik yuz berdi.")


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_quiz_question(update.message.chat_id, context)


async def send_quiz_question(chat_id, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(QUIZ_QUESTIONS)
    context.chat_data["current_quiz"] = q
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"quiz_{i}")]
        for i, opt in enumerate(q["options"])
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🧠 {q['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------------------------------------------------------
# Callback tugmalar (inline keyboard)
# ---------------------------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "bio":
        await query.message.reply_text(BIO_TEXT, parse_mode=ParseMode.HTML)
    elif data == "stats":
        await query.message.reply_text(STATS_TEXT, parse_mode=ParseMode.HTML)
    elif data == "news":
        await news_command_from_query(query, context)
    elif data == "quiz":
        await send_quiz_question(query.message.chat_id, context)
    elif data.startswith("quiz_"):
        await handle_quiz_answer(query, context, int(data.split("_")[1]))


async def news_command_from_query(query, context):
    await query.message.reply_text("🔎 Yangiliklar qidirilmoqda...")
    try:
        feed = feedparser.parse(NEWS_RSS_URL)
        entries = feed.entries[:5]
        if not entries:
            await query.message.reply_text("Hozircha yangilik topilmadi.")
            return
        lines = ["📰 <b>So'nggi yangiliklar:</b>\n"]
        for entry in entries:
            title = html.escape(entry.title)
            lines.append(f"• <a href='{entry.link}'>{title}</a>")
        await query.message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"News error: {e}")
        await query.message.reply_text("⚠️ Xatolik yuz berdi.")


async def handle_quiz_answer(query, context, selected_index):
    q = context.chat_data.get("current_quiz")
    if not q:
        await query.message.reply_text("Avval /quiz buyrug'ini yuboring.")
        return
    if selected_index == q["correct"]:
        await query.message.reply_text("✅ To'g'ri javob!")
    else:
        correct_opt = q["options"][q["correct"]]
        await query.message.reply_text(f"❌ Noto'g'ri. To'g'ri javob: {correct_opt}")
    context.chat_data["current_quiz"] = None


# ---------------------------------------------------------------------------
# Erkin suhbat (AI) — oddiy matn xabarlar uchun
# ---------------------------------------------------------------------------

async def free_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if not ANTHROPIC_API_KEY:
        await update.message.reply_text(
            "🤖 Erkin suhbat uchun AI ulanmagan.\n"
            "Buni yoqish uchun .env faylida ANTHROPIC_API_KEY ni to'ldiring.\n\n"
            "Hozircha /bio, /stats, /news yoki /quiz buyruqlaridan foydalaning."
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=(
                "Sen Neymar haqida ma'lumot beruvchi futbol boti san. "
                "Faqat Neymar, uning karyerasi, klublari va futbol mavzusida "
                "o'zbek tilida qisqa va aniq javob ber."
            ),
            messages=[{"role": "user", "content": user_text}],
        )
        answer = response.content[0].text
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        await update.message.reply_text("⚠️ Javob berishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")


# ---------------------------------------------------------------------------
# Ishga tushirish
# ---------------------------------------------------------------------------

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN topilmadi. .env faylida TELEGRAM_BOT_TOKEN=... deb qo'shing."
        )

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bio", bio_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_chat))

    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
      
