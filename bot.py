import os
import re
import uuid
import datetime
import pytz
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from config import (
    TELEGRAM_BOT_TOKEN,
    DEFAULT_TOP_TEXT,
    DEFAULT_BOTTOM_TEXT,
    TEMP_DIR,
    CHANNEL_NAME
)
from downloader import is_youtube_url, download_youtube_media, download_trending_audio, probe_media
from video_engine import build_reaction_video
from youtube_uploader import upload_video_to_youtube
from admin_manager import is_admin, get_admins, add_admin, remove_admin, MASTER_ADMIN_ID

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation States
(
    TOP_TEXT,
    TOP_MEDIA,
    BOTTOM_TEXT,
    BOTTOM_MEDIA,
    AUDIO_CHOICE,
    TRENDING_AUDIO_INPUT,
    TRENDING_AUDIO_VOL,
    VIDEO_META,
    UPLOAD_CHOICE,
    SCHEDULE_TIME
) = range(10)

DEFAULT_TITLE = f"Amazing Reaction Video 🔥 #Shorts #{CHANNEL_NAME.replace(' ', '')}"
DEFAULT_DESCRIPTION = f"Welcome to {CHANNEL_NAME}! Enjoy this reaction short.\n\n#Shorts #VoiceOfPrince #Viral #Trending #Reactions"

def check_auth(func):
    """Decorator to restrict access strictly to authorized admins."""
    async def wrapper(update_or_msg, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = getattr(update_or_msg, 'effective_user', None)
        if not user and hasattr(update_or_msg, 'from_user'):
            user = update_or_msg.from_user

        if user and not is_admin(user.id):
            uid = user.id
            denied_msg = (
                f"⛔ **অ্যাক্সেস ডিনাইড (Access Denied)!**\n\n"
                f"আপনি এই বট ব্যবহার করার অনুমোদিত অ্যাডমিন নন।\n"
                f"আপনার টেলিগ্রাম আইডি: `{uid}`\n\n"
                f"এই বটে অ্যাক্সেস পেতে মূল অ্যাডমিনকে আপনার আইডিটি পাঠান।"
            )
            if hasattr(update_or_msg, 'callback_query') and update_or_msg.callback_query:
                await update_or_msg.callback_query.answer("⛔ অ্যাক্সেস অনুমোদিত নয়!", show_alert=True)
            elif hasattr(update_or_msg, 'effective_message') and update_or_msg.effective_message:
                await update_or_msg.effective_message.reply_text(denied_msg, parse_mode="Markdown")
            elif hasattr(update_or_msg, 'reply_text'):
                await update_or_msg.reply_text(denied_msg, parse_mode="Markdown")
            return ConversationHandler.END

        return await func(update_or_msg, context, *args, **kwargs)
    return wrapper

# Persistent Menu Keyboard
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🎬 নতুন ভিডিও তৈরি করুন", "👑 অ্যাডমিন প্যানেল"],
        ["❌ কাজ বাতিল করুন"]
    ],
    resize_keyboard=True
)

# ================= Admin Commands =================

@check_auth
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays current admin list and instructions to add/remove admins."""
    admins = get_admins()
    admin_list_str = "\n".join([f"• `{a}`" + (" 👑 (Master)" if a == MASTER_ADMIN_ID else "") for a in admins])
    
    msg = (
        f"👑 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
        f"**বর্তমান অনুমোদিত অ্যাডমিন তালিকা:**\n"
        f"{admin_list_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"➕ **নতুন অ্যাডমিন যোগ করতে লিখুন:**\n"
        f"`/addadmin <chat_id>`\n"
        f"উদাহরণ: `/addadmin 1234567890`\n\n"
        f"➖ **অ্যাডমিন বাতিল করতে লিখুন:**\n"
        f"`/removeadmin <chat_id>`"
    )
    await update.effective_message.reply_text(msg, reply_markup=MAIN_MENU_KEYBOARD, parse_mode="Markdown")

@check_auth
async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a new admin by Chat ID."""
    if not context.args:
        await update.effective_message.reply_text("❌ ফরম্যাট: `/addadmin <chat_id>` (যেমন: `/addadmin 1234567890`)", parse_mode="Markdown")
        return
    try:
        new_id = int(context.args[0])
        if add_admin(new_id):
            await update.effective_message.reply_text(f"✅ আইডি `{new_id}` সফলভাবে নতুন অ্যাডমিন হিসেবে যোগ করা হয়েছে!", parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(f"ℹ️ আইডি `{new_id}` ইতিমধ্যে অ্যাডমিন তালিকায় রয়েছে।", parse_mode="Markdown")
    except ValueError:
        await update.effective_message.reply_text("❌ সঠিক নিউমেরিক চ্যাট আইডি দিন!")

@check_auth
async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes an admin by Chat ID."""
    if not context.args:
        await update.effective_message.reply_text("❌ ফরম্যাট: `/removeadmin <chat_id>`", parse_mode="Markdown")
        return
    try:
        target_id = int(context.args[0])
        if target_id == MASTER_ADMIN_ID:
            await update.effective_message.reply_text("❌ মূল মাস্টার অ্যাডমিনকে রিমুভ করা যাবে না!", parse_mode="Markdown")
            return
        if remove_admin(target_id):
            await update.effective_message.reply_text(f"✅ আইডি `{target_id}` অ্যাডমিন তালিকা থেকে বাদ দেওয়া হয়েছে!", parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(f"❌ আইডি `{target_id}` অ্যাডমিন তালিকায় পাওয়া যায়নি।", parse_mode="Markdown")
    except ValueError:
        await update.effective_message.reply_text("❌ সঠিক নিউমেরিক চ্যাট আইডি দিন!")

# ================= Wizard Workflow =================

@check_auth
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point when user runs /start or /create."""
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("⏩ ডিফল্ট ব্যবহার করুন (This video.!)", callback_data="skip_top_text")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_msg = (
        f"👋 **স্বাগতম YouTube Reaction Shorts Creator বটে!**\n\n"
        f"চ্যানেল: **{CHANNEL_NAME}**\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 **স্টেপ ১: উপরের টেক্সট (Top Text)**\n\n"
        f"ডিফল্ট রাখতে নিচের বাটনে চাপ দিন অথবা যা লিখতে চান তা লিখে মেসেজ পাঠান:\n"
        f"(উদাহরণ: `This video.!\n😌 💖`)"
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")
        
    return TOP_TEXT

@check_auth
async def handle_top_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles top text input."""
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data['top_text'] = DEFAULT_TOP_TEXT
        msg = update.callback_query.message
    else:
        text = update.message.text.strip()
        context.user_data['top_text'] = text if text else DEFAULT_TOP_TEXT
        msg = update.message

    prompt = (
        f"✅ **টপ টেক্সট সেট করা হয়েছে:**\n`{context.user_data['top_text']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 **স্টেপ ২: উপরের ভিডিও বা ছবি (Top Media)**\n\n"
        f"YouTube Shorts বা Video-র লিংক পাঠান (স্বয়ংক্রিয়ভাবে yt-dlp দিয়ে নামানো হবে),\n"
        f"অথবা সরাসরি ভিডিও/ছবি আপলোড করুন:"
    )
    await msg.reply_text(prompt, parse_mode="Markdown")
    return TOP_MEDIA

@check_auth
async def handle_top_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles top media (YouTube URL or uploaded video/image)."""
    status_msg = await update.message.reply_text("⏳ মিডিয়া প্রসেস করা হচ্ছে...")
    media_path = None

    try:
        if update.message.text and is_youtube_url(update.message.text.strip()):
            url = update.message.text.strip()
            await status_msg.edit_text("📥 yt-dlp দিয়ে ইউটিউব ভিডিও ডাউনলোড হচ্ছে...")
            media_path = download_youtube_media(url, output_prefix="top_media")
        elif update.message.video:
            await status_msg.edit_text("📥 টেলিগ্রাম থেকে ভিডিও ডাউনলোড হচ্ছে...")
            f = await update.message.video.get_file()
            ext = os.path.splitext(f.file_path)[1] or ".mp4"
            media_path = os.path.join(TEMP_DIR, f"top_upload_{uuid.uuid4().hex[:6]}{ext}")
            await f.download_to_drive(media_path)
        elif update.message.photo:
            await status_msg.edit_text("📥 টেলিগ্রাম থেকে ছবি ডাউনলোড হচ্ছে...")
            f = await update.message.photo[-1].get_file()
            media_path = os.path.join(TEMP_DIR, f"top_upload_{uuid.uuid4().hex[:6]}.jpg")
            await f.download_to_drive(media_path)
        elif update.message.document:
            await status_msg.edit_text("📥 ফাইল ডাউনলোড হচ্ছে...")
            f = await update.message.document.get_file()
            ext = os.path.splitext(f.file_path)[1] or ".mp4"
            media_path = os.path.join(TEMP_DIR, f"top_upload_{uuid.uuid4().hex[:6]}{ext}")
            await f.download_to_drive(media_path)
        else:
            await status_msg.edit_text("❌ দয়া করে একটি সঠিক YouTube লিংক অথবা ভিডিও/ছবি পাঠান!")
            return TOP_MEDIA

        context.user_data['top_media_path'] = media_path
        probe = probe_media(media_path)
        context.user_data['top_probe'] = probe

        keyboard = [
            [InlineKeyboardButton("⏩ ডিফল্ট ব্যবহার করুন (My Reaction.!)", callback_data="skip_bottom_text")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(
            f"✅ **টপ মিডিয়া সংরক্ষিত হয়েছে!**\n"
            f"(টাইপ: {'ভিডিও 📹' if probe['is_video'] else 'ছবি 🖼️'})\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 **স্টেপ ৩: নিচের রিঅ্যাকশন টেক্সট (Reaction Text)**\n\n"
            f"ডিফল্ট রাখতে নিচের বাটনে চাপ দিন অথবা যা লিখতে চান লিখে মেসেজ পাঠান:\n"
            f"(উদাহরণ: `My Reaction.!\n😅 ❤️‍🩹`)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return BOTTOM_TEXT

    except Exception as e:
        logger.error(f"Error handling top media: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ মিডিয়া ডাউনলোড করতে সমস্যা হয়েছে: {str(e)}")
        return TOP_MEDIA

@check_auth
async def handle_bottom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles bottom text input."""
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data['bottom_text'] = DEFAULT_BOTTOM_TEXT
        msg = update.callback_query.message
    else:
        text = update.message.text.strip()
        context.user_data['bottom_text'] = text if text else DEFAULT_BOTTOM_TEXT
        msg = update.message

    prompt = (
        f"✅ **রিঅ্যাকশন টেক্সট সেট করা হয়েছে:**\n`{context.user_data['bottom_text']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🖼️ **স্টেপ ৪: নিচের মিডিয়া (Reaction Media)**\n\n"
        f"রিঅ্যাকশন ছবি বা ভিডিও পাঠান (অথবা YouTube লিংক দিন):"
    )
    await msg.reply_text(prompt, parse_mode="Markdown")
    return BOTTOM_MEDIA

@check_auth
async def handle_bottom_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles bottom media (YouTube URL or uploaded image/video)."""
    status_msg = await update.message.reply_text("⏳ মিডিয়া প্রসেস করা হচ্ছে...")
    media_path = None

    try:
        if update.message.text and is_youtube_url(update.message.text.strip()):
            url = update.message.text.strip()
            await status_msg.edit_text("📥 yt-dlp দিয়ে ইউটিউব ভিডিও ডাউনলোড হচ্ছে...")
            media_path = download_youtube_media(url, output_prefix="bot_media")
        elif update.message.video:
            await status_msg.edit_text("📥 টেলিগ্রাম থেকে ভিডিও ডাউনলোড হচ্ছে...")
            f = await update.message.video.get_file()
            ext = os.path.splitext(f.file_path)[1] or ".mp4"
            media_path = os.path.join(TEMP_DIR, f"bot_upload_{uuid.uuid4().hex[:6]}{ext}")
            await f.download_to_drive(media_path)
        elif update.message.photo:
            await status_msg.edit_text("📥 টেলিগ্রাম থেকে ছবি ডাউনলোড হচ্ছে...")
            f = await update.message.photo[-1].get_file()
            media_path = os.path.join(TEMP_DIR, f"bot_upload_{uuid.uuid4().hex[:6]}.jpg")
            await f.download_to_drive(media_path)
        elif update.message.document:
            await status_msg.edit_text("📥 ফাইল ডাউনলোড হচ্ছে...")
            f = await update.message.document.get_file()
            ext = os.path.splitext(f.file_path)[1] or ".mp4"
            media_path = os.path.join(TEMP_DIR, f"bot_upload_{uuid.uuid4().hex[:6]}{ext}")
            await f.download_to_drive(media_path)
        else:
            await status_msg.edit_text("❌ দয়া করে একটি সঠিক ছবি, ভিডিও বা YouTube লিংক পাঠান!")
            return BOTTOM_MEDIA

        context.user_data['bottom_media_path'] = media_path
        probe = probe_media(media_path)
        context.user_data['bottom_probe'] = probe

        # Check if both are videos
        top_probe = context.user_data.get('top_probe', {})
        both_are_videos = top_probe.get('is_video') and probe.get('is_video')

        if both_are_videos:
            keyboard = [
                [InlineKeyboardButton("🔇 উপরের ভিডিও মিউট (Option 1)", callback_data="audio_mute_top")],
                [InlineKeyboardButton("🔇 নিচের ভিডিও মিউট (Option 2)", callback_data="audio_mute_bottom")],
                [InlineKeyboardButton("🔊 দুটি ভিডিওর সাউন্ডই থাকবে", callback_data="audio_keep_both")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text(
                "🔊 **ভিডিও অডিও অপশন:**\n\n"
                "আপনি দুটি ভিডিও ব্যবহার করছেন। কোন ভিডিওটির অডিও মিউট রাখতে চান?",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return AUDIO_CHOICE
        else:
            context.user_data['audio_choice'] = "default"
            return await ask_trending_audio(status_msg, context)

    except Exception as e:
        logger.error(f"Error handling bottom media: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ মিডিয়া ডাউনলোড করতে সমস্যা হয়েছে: {str(e)}")
        return BOTTOM_MEDIA

@check_auth
async def handle_audio_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes user audio mute selection."""
    query = update.callback_query
    await query.answer()

    choice_map = {
        "audio_mute_top": "mute_top",
        "audio_mute_bottom": "mute_bottom",
        "audio_keep_both": "keep_both"
    }
    context.user_data['audio_choice'] = choice_map.get(query.data, "mute_bottom")
    return await ask_trending_audio(query.message, context)

# Internal transition helper: No @check_auth decorator
async def ask_trending_audio(message, context: ContextTypes.DEFAULT_TYPE):
    """Prompts for optional Trending Sound to boost viral algorithm."""
    keyboard = [
        [InlineKeyboardButton("⏩ স্কিপ করুন (ভাইরাল গান ছাড়া)", callback_data="skip_trending_audio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    prompt = (
        "🔥 **স্টেপ ৫: ভাইরাল সং / ভিডিও লিংক (Viral Algorithm Boost)**\n\n"
        "এখানে যেকোনো ভাইরাল ভিডিও বা ট্রেন্ডিং গানের YouTube লিংক দিন।\n\n"
        "🔇 **অ্যালগরিদম বুস্ট:** গানটি ব্যাকগ্রাউন্ডে **১০০% মিউটে (০% ভলিউম)** রাখা হবে, যাতে আপনার মূল ভিডিওর আসল ভয়েস অক্ষত থাকে। কিন্তু YouTube অ্যালগরিদম ভিডিওটিকে ভাইরাল গানের সাথে যুক্ত করে দ্রুত পুশ করবে!\n\n"
        "ইউটিউব লিংক পাঠান অথবা নিচের বাটনে চাপ দিন:"
    )
    await message.reply_text(prompt, reply_markup=reply_markup, parse_mode="Markdown")
    return TRENDING_AUDIO_INPUT

@check_auth
async def handle_trending_audio_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles trending sound YouTube link or skip."""
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data['trending_audio_path'] = None
        context.user_data['trending_volume'] = 0.0
        return await ask_video_metadata(update.callback_query.message, context)

    text = update.message.text.strip()
    if not is_youtube_url(text):
        await update.message.reply_text("❌ দয়া করে একটি সঠিক YouTube লিংক পাঠান অথবা স্কিপ করতে বাটনে চাপ দিন:")
        return TRENDING_AUDIO_INPUT

    status_msg = await update.message.reply_text("📥 ভাইরাল সাউন্ড ট্র্যাক নামানো হচ্ছে...")
    try:
        audio_path = download_trending_audio(text)
        context.user_data['trending_audio_path'] = audio_path
        # Default volume is strictly 0.0 (Muted) as requested!
        context.user_data['trending_volume'] = 0.0

        keyboard = [
            [InlineKeyboardButton("✅ মিউটে রেখে এগিয়ে যান (০% সাউন্ড)", callback_data="trend_vol_0")],
            [InlineKeyboardButton("🔈 ১% সাউন্ড", callback_data="trend_vol_1"),
             InlineKeyboardButton("🔉 ২% সাউন্ড", callback_data="trend_vol_2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(
            "✅ **ভাইরাল গান সফলভাবে যোগ করা হয়েছে!**\n\n"
            "🔇 এটি ডিফল্টভাবে **মিউটে (০% ভলিউমে)** থাকবে যাতে আপনার মূল কণ্ঠ পুরোপুরি স্পষ্ট থাকে।\n\n"
            "সরাসরি এগিয়ে যেতে নিচের বাটনে চাপুন (অথবা চাইলে ১-২% হালকা সাউন্ড সিলেক্ট করতে পারেন):",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return TRENDING_AUDIO_VOL
    except Exception as e:
        logger.error(f"Error downloading trending audio: {e}")
        await status_msg.edit_text(f"⚠️ ভাইরাল অডিও ডাউনলোড করা যায়নি: {str(e)}\nগান ছাড়াই এগিয়ে যাওয়া হচ্ছে...")
        context.user_data['trending_audio_path'] = None
        context.user_data['trending_volume'] = 0.0
        return await ask_video_metadata(status_msg, context)

@check_auth
async def handle_trending_audio_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves trending audio volume selection."""
    query = update.callback_query
    await query.answer()

    vol_map = {
        "trend_vol_0": 0.0,
        "trend_vol_1": 0.01,
        "trend_vol_2": 0.02
    }
    context.user_data['trending_volume'] = vol_map.get(query.data, 0.0)
    vol_desc = "১০০% মিউট (০%)" if context.user_data['trending_volume'] == 0.0 else f"{int(context.user_data['trending_volume'] * 100)}% সাউন্ড"
    await query.message.reply_text(f"✅ ভাইরাল গানের ভলিউম: **{vol_desc}** সেট করা হয়েছে।", parse_mode="Markdown")
    return await ask_video_metadata(query.message, context)

# Internal transition helper: No @check_auth decorator
async def ask_video_metadata(message, context: ContextTypes.DEFAULT_TYPE):
    """Asks for manual YouTube title, hashtags, and description."""
    keyboard = [
        [InlineKeyboardButton("⏩ ডিফল্ট টাইটেল ও হ্যাশট্যাগ ব্যবহার করুন", callback_data="skip_video_meta")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    prompt = (
        "📝 **স্টেপ ৬: ভিডিও টাইটেল ও হ্যাশট্যাগ (Title & Hashtags)**\n\n"
        "ভিডিওর জন্য টাইটেল এবং হ্যাশট্যাগ/ডেসক্রিপশন লিখে পাঠান।\n\n"
        "💡 **লেখার নিয়ম:**\n"
        "প্রথম লাইনে **টাইটেল** লিখবেন এবং পরবর্তী লাইনে **হ্যাশট্যাগ বা বিবরণ** লিখবেন।\n"
        "যেমন:\n"
        "`ভিডিওটি শেষ পর্যন্ত দেখুন 😂🔥`\n"
        "`#Shorts #VoiceOfPrince #Viral #Trending`\n\n"
        "অথবা সরাসরি ডিফল্ট রাখতে নিচের বাটনে চাপ দিন:"
    )
    await message.reply_text(prompt, reply_markup=reply_markup, parse_mode="Markdown")
    return VIDEO_META

@check_auth
async def handle_video_meta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes user input for title and description/hashtags."""
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data['video_title'] = DEFAULT_TITLE
        context.user_data['video_description'] = DEFAULT_DESCRIPTION
        msg = update.callback_query.message
    else:
        text = update.message.text.strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) == 1:
            title = lines[0]
            desc = f"{lines[0]}\n\n#Shorts #VoiceOfPrince #Viral #Trending #Reactions"
        elif len(lines) > 1:
            title = lines[0]
            desc = "\n".join(lines[1:])
        else:
            title = DEFAULT_TITLE
            desc = DEFAULT_DESCRIPTION

        if "#Shorts" not in title:
            title = f"{title} #Shorts"

        context.user_data['video_title'] = title
        context.user_data['video_description'] = desc
        msg = update.message

    summary_text = (
        f"✅ **টাইটেল ও ডেসক্রিপশন সেভ করা হয়েছে:**\n\n"
        f"📌 **টাইটেল:** `{context.user_data['video_title']}`\n"
        f"🏷️ **ডেসক্রিপশন/হ্যাশট্যাগ:**\n`{context.user_data['video_description']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    await msg.reply_text(summary_text, parse_mode="Markdown")
    return await ask_upload_option(msg, context)

# Internal transition helper: No @check_auth decorator
async def ask_upload_option(message, context: ContextTypes.DEFAULT_TYPE):
    """Presents upload mode options: Now vs Schedule vs Preview."""
    keyboard = [
        [InlineKeyboardButton("⚡ Now (এখনই আপলোড)", callback_data="upload_now")],
        [InlineKeyboardButton("⏰ Schedule (শিডিউল আপলোড)", callback_data="upload_schedule")],
        [InlineKeyboardButton("🎬 Only Preview (শুধু ভিডিও দেখান)", callback_data="preview_only")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"🚀 **স্টেপ ৭: ইউটিউব আপলোড অপশন:**\n\n"
        f"ভিডিওটি কখন আপনার **'{CHANNEL_NAME}'** চ্যানেলে প্রকাশ করতে চান?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return UPLOAD_CHOICE

@check_auth
async def handle_upload_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles selection between Now, Schedule, and Preview."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "upload_now":
        context.user_data['upload_mode'] = "now"
        context.user_data['schedule_time_iso'] = None
        return await start_generation_pipeline(query.message, context)

    elif action == "preview_only":
        context.user_data['upload_mode'] = "preview"
        context.user_data['schedule_time_iso'] = None
        return await start_generation_pipeline(query.message, context)

    elif action == "upload_schedule":
        context.user_data['upload_mode'] = "schedule"
        
        tz = pytz.timezone("Asia/Dhaka")
        now_bd = datetime.datetime.now(tz)

        keyboard = [
            [
                InlineKeyboardButton("⏳ ১ ঘণ্টা পর", callback_data="sched_plus_1h"),
                InlineKeyboardButton("⏳ ৩ ঘণ্টা পর", callback_data="sched_plus_3h")
            ],
            [
                InlineKeyboardButton("⏳ ৫ ঘণ্টা পর", callback_data="sched_plus_5h"),
                InlineKeyboardButton("🌅 কাল সকাল ৯টায়", callback_data="sched_tomorrow_9am")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            f"⏰ **শিডিউলের সময় নির্বাচন করুন:**\n\n"
            f"বর্তমান বাংলাদেশ সময়: `{now_bd.strftime('%Y-%m-%d %I:%M %p')}`\n\n"
            f"নিচের বাটনে চাপুন অথবা নির্দিষ্ট সময় লিখে মেসেজ দিন:\n"
            f"ফরম্যাট: `YYYY-MM-DD HH:MM`\n"
            f"যেমন: `{now_bd.strftime('%Y-%m-%d')} 21:00`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return SCHEDULE_TIME

@check_auth
async def handle_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes preset button or custom date-time input."""
    tz = pytz.timezone("Asia/Dhaka")
    now_bd = datetime.datetime.now(tz)
    target_dt = None
    msg = None

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        msg = query.message
        data = query.data

        if data == "sched_plus_1h":
            target_dt = now_bd + datetime.timedelta(hours=1)
        elif data == "sched_plus_3h":
            target_dt = now_bd + datetime.timedelta(hours=3)
        elif data == "sched_plus_5h":
            target_dt = now_bd + datetime.timedelta(hours=5)
        elif data == "sched_tomorrow_9am":
            tomorrow = now_bd + datetime.timedelta(days=1)
            target_dt = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        msg = update.message
        text = update.message.text.strip()
        try:
            naive_dt = datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")
            target_dt = tz.localize(naive_dt)
        except Exception:
            await msg.reply_text(
                "❌ ফরম্যাট সঠিক হয়নি! দয়া করে এই ফরম্যাটে দিন: `YYYY-MM-DD HH:MM`\n"
                "উদাহরণ: `2026-10-06 21:30`",
                parse_mode="Markdown"
            )
            return SCHEDULE_TIME

    if target_dt <= now_bd:
        await msg.reply_text("❌ শিডিউল টাইম বর্তমান সময়ের চেয়ে ভবিষ্যতের হতে হবে! আবার চেষ্টা করুন:")
        return SCHEDULE_TIME

    utc_dt = target_dt.astimezone(pytz.utc)
    schedule_iso = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    context.user_data['schedule_time_iso'] = schedule_iso
    context.user_data['display_sched_time'] = target_dt.strftime("%d %b %Y, %I:%M %p (BD Time)")

    return await start_generation_pipeline(msg, context)

# Internal transition helper: No @check_auth decorator
async def start_generation_pipeline(message, context: ContextTypes.DEFAULT_TYPE):
    """Generates the reaction video and handles YouTube upload/schedule."""
    status_msg = await message.reply_text("🎬 **ভিডিও জেনারেশন শুরু হয়েছে...**\nঅনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।", parse_mode="Markdown")

    top_media = context.user_data.get('top_media_path')
    bottom_media = context.user_data.get('bottom_media_path')
    top_text = context.user_data.get('top_text', DEFAULT_TOP_TEXT)
    bottom_text = context.user_data.get('bottom_text', DEFAULT_BOTTOM_TEXT)
    audio_choice = context.user_data.get('audio_choice', 'mute_bottom')
    upload_mode = context.user_data.get('upload_mode', 'preview')
    schedule_iso = context.user_data.get('schedule_time_iso')
    video_title = context.user_data.get('video_title', DEFAULT_TITLE)
    video_description = context.user_data.get('video_description', DEFAULT_DESCRIPTION)
    trending_audio_path = context.user_data.get('trending_audio_path')
    trending_vol = context.user_data.get('trending_volume', 0.0)

    try:
        # Step 1: Video Rendering
        await status_msg.edit_text("⚙️ **FFmpeg দিয়ে ভিডিও কম্পোজ ও অডিও মিক্স করা হচ্ছে...**")
        final_video_path = build_reaction_video(
            top_media_path=top_media,
            bottom_media_path=bottom_media,
            top_text=top_text,
            bottom_text=bottom_text,
            audio_choice=audio_choice,
            trending_audio_path=trending_audio_path,
            trending_volume=trending_vol
        )

        # Step 2: Handle YouTube Upload / Schedule
        yt_info = None
        if upload_mode in ["now", "schedule"]:
            await status_msg.edit_text(
                f"📤 **YouTube চ্যানেলে আপলোড হচ্ছে ('{CHANNEL_NAME}')...**\n" +
                (f"⏰ শিডিউল সময়: {context.user_data.get('display_sched_time')}" if schedule_iso else "⚡ পাবলিক মোড")
            )
            try:
                yt_info = upload_video_to_youtube(
                    video_path=final_video_path,
                    title=video_title,
                    description=video_description,
                    schedule_time_iso=schedule_iso
                )
            except Exception as yt_err:
                logger.error(f"YouTube Upload Failed: {yt_err}")
                await status_msg.reply_text(
                    f"⚠️ ইউটিউবে স্বয়ংক্রিয় আপলোড হয়নি:\n`{str(yt_err)}`\n\n"
                    f"নোট: ইউটিউব এপিআই অথেন্টিকেশনের জন্য auth_youtube.bat চালান। আপনার তৈরি হওয়া ভিডিও নিচে দেওয়া হলো!"
                )

        # Step 3: Send video preview to user via Telegram
        await status_msg.edit_text("📤 তৈরি হওয়া ভিডিওটি টেলিগ্রামে পাঠানো হচ্ছে...")
        
        import html
        safe_title = html.escape(str(video_title))
        safe_channel = html.escape(str(CHANNEL_NAME))
        safe_sched_time = html.escape(str(context.user_data.get('display_sched_time', '')))

        caption = (
            f"🎉 <b>আপনার Shorts ভিডিও সফলভাবে তৈরি হয়েছে!</b>\n\n"
            f"📌 <b>টাইটেল:</b> {safe_title}\n"
            f"🏷️ <b>চ্যানেল:</b> {safe_channel}\n"
        )
        if trending_audio_path:
            trend_vol_txt = "মিউট (০%)" if trending_vol == 0.0 else f"{int(trending_vol*100)}%"
            caption += f"🎵 <b>ভাইরাল সাউন্ড ট্র্যাক:</b> অ্যালগরিদম ট্যাগ সক্রিয় (ভলিউম: {trend_vol_txt})\n"

        if yt_info:
            yt_url = yt_info.get('url', '')
            if yt_info.get('scheduled'):
                caption += f"\n⏰ <b>YouTube Scheduled:</b> {safe_sched_time}\n🔗 <b>লিংক:</b> {yt_url}"
            else:
                caption += f"\n✅ <b>YouTube Live:</b>\n🔗 <b>লিংক:</b> {yt_url}"

        caption += "\n\nনতুন ভিডিও তৈরি করতে /start বা /create লিখুন।"

        with open(final_video_path, 'rb') as video_file:
            try:
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as send_err:
                logger.warning(f"HTML reply_video failed, falling back to plain text: {send_err}")
                await message.reply_video(
                    video=video_file,
                    caption=f"🎉 আপনার Shorts ভিডিও তৈরি হয়েছে!\n\nটাইটেল: {video_title}\nচ্যানেল: {CHANNEL_NAME}\n" + (f"ইউটিউব লিংক: {yt_info.get('url', '')}" if yt_info else ""),
                    parse_mode=None
                )

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error in pipeline: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ ভিডিও জেনারেট করতে সমস্যা হয়েছে:\n`{str(e)}`")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels current flow."""
    context.user_data.clear()
    await update.message.reply_text("❌ প্রক্রিয়াটি বাতিল করা হয়েছে। নতুন ভিডিও তৈরি করতে /create লিখুন।", reply_markup=MAIN_MENU_KEYBOARD)
    return ConversationHandler.END

async def post_init_setup(app):
    """Configures Telegram Bot Menu commands."""
    commands = [
        BotCommand("create", "🎬 নতুন ভিডিও তৈরি করুন"),
        BotCommand("admin", "👑 অ্যাডমিন প্যানেল"),
        BotCommand("cancel", "❌ বর্তমান কাজ বাতিল করুন")
    ]
    try:
        await app.bot.set_my_commands(commands)
        logger.info("Telegram Bot Menu commands set successfully!")
    except Exception as e:
        logger.error(f"Failed to set bot commands menu: {e}")

def main():
    """Starts Telegram Bot with robust timeout settings and retry logic."""
    print("Telegram Bot is starting...")

    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=60.0,
        http_version="1.1"
    )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(request).post_init(post_init_setup).build()

    # Admin Management Command Handlers
    app.add_handler(CommandHandler('admin', admin_panel))
    app.add_handler(CommandHandler('admins', admin_panel))
    app.add_handler(MessageHandler(filters.Regex('^👑 অ্যাডমিন প্যানেল$'), admin_panel))
    app.add_handler(CommandHandler('addadmin', add_admin_cmd))
    app.add_handler(CommandHandler('removeadmin', remove_admin_cmd))

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('create', start),
            MessageHandler(filters.Regex('^🎬 নতুন ভিডিও তৈরি করুন$'), start)
        ],
        states={
            TOP_TEXT: [
                CallbackQueryHandler(handle_top_text, pattern="^skip_top_text$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_top_text)
            ],
            TOP_MEDIA: [
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_top_media)
            ],
            BOTTOM_TEXT: [
                CallbackQueryHandler(handle_bottom_text, pattern="^skip_bottom_text$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bottom_text)
            ],
            BOTTOM_MEDIA: [
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_bottom_media)
            ],
            AUDIO_CHOICE: [
                CallbackQueryHandler(handle_audio_choice, pattern="^audio_")
            ],
            TRENDING_AUDIO_INPUT: [
                CallbackQueryHandler(handle_trending_audio_input, pattern="^skip_trending_audio$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trending_audio_input)
            ],
            TRENDING_AUDIO_VOL: [
                CallbackQueryHandler(handle_trending_audio_vol, pattern="^trend_vol_")
            ],
            VIDEO_META: [
                CallbackQueryHandler(handle_video_meta, pattern="^skip_video_meta$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_meta)
            ],
            UPLOAD_CHOICE: [
                CallbackQueryHandler(handle_upload_choice, pattern="^(upload_now|upload_schedule|preview_only)$")
            ],
            SCHEDULE_TIME: [
                CallbackQueryHandler(handle_schedule_time, pattern="^sched_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_time)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(filters.Regex('^❌ কাজ বাতিল করুন$'), cancel)
        ],
        per_chat=True,
        per_user=True,
        per_message=False
    )

    app.add_handler(conv_handler)
    print("Bot is successfully polling for updates... Press Ctrl+C to stop.")
    app.run_polling(bootstrap_retries=10, timeout=30)

if __name__ == '__main__':
    main()
