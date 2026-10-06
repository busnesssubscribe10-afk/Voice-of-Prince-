# 🎬 Voice of Prince — Automated YouTube Shorts Reaction Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/FFmpeg-v9.0-green?style=for-the-badge&logo=ffmpeg" alt="FFmpeg">
  <img src="https://img.shields.io/badge/yt--dlp-2024+-red?style=for-the-badge&logo=youtube" alt="yt-dlp">
  <img src="https://img.shields.io/badge/Telegram-Bot%20API-informational?style=for-the-badge&logo=telegram" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/YouTube%20API-v3-red?style=for-the-badge&logo=youtube" alt="YouTube Data API">
</p>

An all-in-one automated video reaction generator and YouTube Shorts publishing suite powered by **Python**, **FFmpeg**, **yt-dlp**, and **Telegram Bot**. 

Designed specifically for the YouTube Channel **Voice of Prince**, this system automates downloading, editing, branding, mixing viral audio tracks, and uploading/scheduling directly from your smartphone via Telegram.

---

## 🌟 Key Features

- **⚡ 9:16 Shorts Template Generation**: Automatically stitches top and bottom media into a clean, modern reaction card layout (1080x1920) with borders and floral decorations.
- **📥 yt-dlp Engine**: Accepts YouTube Shorts/Videos links and downloads them with maximum speed and fidelity. Also supports direct Telegram photo/video uploads.
- **✍️ Flexible Typography**: Full support for Bengali (`Kalpurush`), English (`Segoe UI`), and Color Emojis (`Segoe UI Emoji`) for both top and bottom text cards.
- **🔊 Smart Audio Routing**: Choose to mute top media, mute bottom media, or mix both audio streams cleanly without clipping or desync.
- **🔥 Viral Song Integration (Algorithm Booster)**: Add any trending song/video link. The song is mixed at **0% volume (100% Mute)** or 1%-2% subtle volume. The audio fingerprint is recognized by YouTube's algorithm to tag the Short under the trending audio without disturbing the primary voice.
- **🏷️ Automated Branding**: Embeds the official **Voice of Prince** watermark badge in every generated short.
- **📤 Instant & Scheduled Uploads**:
  - **Now (এখনই আপলোড)**: Instantly publishes video as public to YouTube.
  - **Schedule (শিডিউল আপলোড)**: Schedules publication via YouTube Data API v3 (`publishAt`) with preset options (1 hr, 3 hrs, 5 hrs, tomorrow morning, or custom `YYYY-MM-DD HH:MM`).
- **📝 Custom Titles & Hashtags**: Add custom titles and viral hashtags manually before uploading, or proceed with one-click defaults.
- **🔒 Admin Panel & Access Control**: Only authorized Telegram Chat IDs can access the bot. Master Admin (`7190342953`) can add or remove admins via `/addadmin` and `/removeadmin`.
- **🖥️ 100% Windows & RDP Ready**: Includes one-click setup (`setup_rdp.bat`) and resilient launcher (`run.bat`) with persistent auto-restarting.

---

## 📁 Project Architecture

```
Voice-of-Prince/
├── bot.py                  # Telegram Bot interactive wizard and controller
├── video_engine.py         # FFmpeg filter complex layout & rendering engine
├── downloader.py           # yt-dlp downloading and ffprobe inspection
├── youtube_uploader.py     # YouTube Data API v3 OAuth2 uploader & scheduler
├── admin_manager.py        # Admin security control and persistence (admins.json)
├── config.py               # Central configuration (tokens, paths, canvas dimensions)
├── auth_youtube.bat        # One-time YouTube OAuth authorization script
├── run.bat                 # Quick launcher with auto-restart loop
├── setup_rdp.bat           # One-click automated installer for Windows RDP
├── requirements.txt        # Python dependency declarations
├── GUIDE.txt               # Complete deployment and configuration guide (in Bengali)
├── assets/
│   ├── fonts/              # Typography fonts (Bengali, English, Emoji)
│   ├── decorations/        # Floral branch decoration PNGs
│   └── watermark.png       # Official "Voice of Prince" branding badge
└── temp/                   # Temporary directory for video processing
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **FFmpeg** installed and added to system `PATH`
- **Git**

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/busnesssubscribe10-afk/Voice-of-Prince-.git
cd Voice-of-Prince-
```

Install Python requirements:
```bash
pip install -r requirements.txt
```

### 3. YouTube Authorization (One-Time)
1. Place your `client_secrets.json` from Google Cloud Console in the root directory.
2. Double-click `auth_youtube.bat` (or run `python youtube_uploader.py`).
3. Select your YouTube Google Account in the browser and allow permissions.
4. `token.json` will be generated. Copying this folder to an RDP will retain login credentials without needing a browser.

### 4. Running the Bot
Double-click `run.bat` or run:
```bash
python bot.py
```

---

## 📱 Telegram Bot Interactive Workflow

1. Open your Telegram bot and send `/start` or `/create` (or use the persistent menu bar button).
2. **Step 1 (Top Text)**: Choose default (`This video.!`) or send custom text.
3. **Step 2 (Top Media)**: Send a YouTube link or upload a video/photo.
4. **Step 3 (Bottom Text)**: Choose default (`My Reaction.!`) or send custom text.
5. **Step 4 (Bottom Media)**: Send a reaction photo or YouTube video link.
6. **Audio Selection**: If both are videos, choose:
   - `🔇 Mute Top Video`
   - `🔇 Mute Bottom Video`
   - `🔊 Keep Both Audio`
7. **Step 5 (Viral Audio)**: Provide a trending YouTube video link for algorithmic boost (set to 0% Mute by default), or skip.
8. **Step 6 (Title & Hashtags)**: Write a custom title and hashtags (Line 1: Title, Line 2: Tags), or click default.
9. **Step 7 (Upload Option)**:
   - `⚡ Now`: Publishes immediately to YouTube.
   - `⏰ Schedule`: Choose a schedule time (1h, 3h, 5h, tomorrow 9am, or custom date/time).
   - `🎬 Only Preview`: Renders video and sends preview to Telegram without uploading.
10. The completed video and live YouTube Shorts URL are delivered directly into your Telegram chat.

---

## 👑 Admin Panel Commands

| Command | Description |
| :--- | :--- |
| `/create` | 🎬 Starts the video creation wizard |
| `/admin` | 👑 Views the list of authorized administrators |
| `/addadmin <chat_id>` | ➕ Grants bot access to a new Telegram Chat ID |
| `/removeadmin <chat_id>` | ➖ Revokes bot access from an existing admin |
| `/cancel` | ❌ Cancels the current wizard operation |

---

## 💻 Windows RDP Deployment

When moving to a fresh Windows RDP or new machine:
1. Copy the entire project folder (including `token.json` and `client_secrets.json`).
2. Run `setup_rdp.bat`. It will automatically:
   - Verify Python (installs silently if missing).
   - Verify FFmpeg (downloads essentials if missing).
   - Install and upgrade all dependencies via `pip`.
   - Start the bot with continuous auto-restart monitoring.

---

## 📄 License

This software is developed for private automation and content production for **Voice of Prince**. All rights reserved.
