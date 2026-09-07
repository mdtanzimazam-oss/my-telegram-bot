import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

TOKEN = os.getenv("8683427174:AAH2UgFOWhpcQez8Rh3i6YSqJ-yCrlUquRU")

user_links = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\nSend me any video link, and I will download it for you! 🤖"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id

    if user_text.startswith("http://") or user_text.startswith("https://"):
        user_links[user_id] = user_text

        keyboard = [
            [
                InlineKeyboardButton("🎵 MP3 Audio", callback_data="dl_mp3"),
                InlineKeyboardButton("🎬 Best Video", callback_data="dl_video"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🔗 **Link detected:**\n`{user_text}`\n\nSelect format to download:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ Please send a valid URL/link.")

def download_media(url, is_audio=False):
    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'max_filesize': 50 * 1024 * 1024,
    }

    if is_audio:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if is_audio:
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"

        return filename

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    url = user_links.get(user_id)
    if not url:
        await query.edit_message_text("❌ Link session expired. Please send the link again.")
        return

    choice = query.data
    is_audio = choice == "dl_mp3"

    await query.edit_message_text("⏳ Downloading media... Please wait.")

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, is_audio)

        await query.edit_message_text("📤 Uploading file to Telegram...")

        with open(file_path, 'rb') as file:
            if is_audio:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=file)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=file)

        if os.path.exists(file_path):
            os.remove(file_path)

        await query.delete_message()

    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_click))

print("🤖 Download Bot is active...")
app.run_polling()
