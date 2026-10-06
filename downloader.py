import os
import re
import json
import uuid
import subprocess
import yt_dlp
from config import TEMP_DIR

def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    yt_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})'
    return bool(re.search(yt_regex, url))

def download_youtube_media(url: str, output_prefix: str = "yt_media") -> str:
    """Downloads YouTube video/short to temp directory and returns absolute path."""
    unique_id = uuid.uuid4().hex[:8]
    output_template = os.path.join(TEMP_DIR, f"{output_prefix}_{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'noplaylist': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp might change extension when merging to mp4
        base, _ = os.path.splitext(filename)
        mp4_filename = base + ".mp4"
        if os.path.exists(mp4_filename):
            return mp4_filename
        return filename

def download_trending_audio(url: str) -> str:
    """Downloads audio of a trending YouTube video to temp directory."""
    unique_id = uuid.uuid4().hex[:8]
    output_template = os.path.join(TEMP_DIR, f"trending_{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'noplaylist': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename

def probe_media(file_path: str) -> dict:
    """
    Returns media metadata using ffprobe:
    - is_video (bool)
    - has_audio (bool)
    - duration (float)
    - width (int)
    - height (int)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    image_exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
    if ext in image_exts:
        # Check image with ffprobe or PIL
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json', file_path
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            width = data['streams'][0]['width']
            height = data['streams'][0]['height']
            return {
                'is_video': False,
                'has_audio': False,
                'duration': 0.0,
                'width': width,
                'height': height
            }
        except Exception:
            return {
                'is_video': False,
                'has_audio': False,
                'duration': 0.0,
                'width': 1080,
                'height': 1080
            }

    # For videos
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'stream=codec_type,width,height,duration:format=duration',
        '-of', 'json', file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        
        has_video = False
        has_audio = False
        width = 1080
        height = 1080
        duration = 0.0

        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                has_video = True
                width = int(stream.get('width', 1080))
                height = int(stream.get('height', 1080))
                if 'duration' in stream and stream['duration']:
                    try:
                        duration = max(duration, float(stream['duration']))
                    except ValueError:
                        pass
            elif stream.get('codec_type') == 'audio':
                has_audio = True

        if 'format' in data and 'duration' in data['format']:
            try:
                duration = max(duration, float(data['format']['duration']))
            except ValueError:
                pass

        return {
            'is_video': has_video,
            'has_audio': has_audio,
            'duration': duration,
            'width': width,
            'height': height
        }
    except Exception as e:
        print(f"Error probing {file_path}: {e}")
        return {
            'is_video': True,
            'has_audio': True,
            'duration': 15.0,
            'width': 1080,
            'height': 1080
        }
