import json
import os
import logging
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import database

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


def load_buttons():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    buttons = config["buttons"]
    per_row = config.get("buttons_per_row", 2)
    keyboard = []
    for i in range(0, len(buttons), per_row):
        row = [
            InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])
            for btn in buttons[i:i + per_row]
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


async def get_user_photo(user, context):
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await context.bot.get_file(photos.photos[0][-1].file_id)
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    except Exception:
        pass
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_url = await get_user_photo(user, context)
    database.upsert_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
        photo_url=photo_url,
    )
    database.log_action(user.id, "start", "Started the bot")

    keyboard = load_buttons()
    await update.message.reply_text(
        "Welcome! Choose an option:",
        reply_markup=keyboard,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    photo_url = await get_user_photo(user, context)
    database.upsert_user(
        user_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
        photo_url=photo_url,
    )
    database.log_action(user.id, "button_click", query.data)

    await query.edit_message_text(
        text=f"{query.data}",
        reply_markup=load_buttons(),
    )


def main():
    database.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
