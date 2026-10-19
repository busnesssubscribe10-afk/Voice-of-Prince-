import os

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "6441331047:AAElGOM9c8dxc-P4KW2yBXYH_4Mg2V-yRbg"

# Project Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
DECOR_DIR = os.path.join(ASSETS_DIR, "decorations")

# YouTube API Credentials
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_PICKLE_FILE = os.path.join(BASE_DIR, "token.json")
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

# Facebook API Credentials
FACEBOOK_PAGE_ID = "YOUR_PAGE_ID_HERE"
FACEBOOK_ACCESS_TOKEN = "YOUR_PAGE_ACCESS_TOKEN_HERE"

# Video Settings
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
FPS = 30

# Media Box Positions & Dimensions
MEDIA_BOX_WIDTH = 540
MEDIA_BOX_HEIGHT = 540

# Top Section Positions
TOP_BOX_X = 40
TOP_BOX_Y = 400
TOP_TEXT_X = 610
TOP_TEXT_Y = 620

# Bottom Section Positions
BOTTOM_BOX_X = 40
BOTTOM_BOX_Y = 1020
BOTTOM_TEXT_X = 610
BOTTOM_TEXT_Y = 1240

# Default Texts
DEFAULT_TOP_TEXT = "This video.!\n😌 💖"
DEFAULT_BOTTOM_TEXT = "My Reaction.!\n😅 ❤️‍🩹"

# Channel Details & Watermark
CHANNEL_NAME = "Voice of Prince"
WATERMARK_IMAGE = os.path.join(ASSETS_DIR, "watermark.png")
FLOWER_IMAGE = os.path.join(DECOR_DIR, "flower.png")

# Font Paths
BANGLA_FONT_PATH = os.path.join(FONTS_DIR, "bangla_font.ttf")
ENGLISH_FONT_PATH = os.path.join(FONTS_DIR, "english_font.ttf")

# Ensure necessary directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
os.makedirs(DECOR_DIR, exist_ok=True)
