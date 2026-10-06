import os
import subprocess
import uuid
import re
from PIL import Image, ImageDraw, ImageFont
from config import (
    TEMP_DIR, CANVAS_WIDTH, CANVAS_HEIGHT, FPS,
    MEDIA_BOX_WIDTH, MEDIA_BOX_HEIGHT,
    TOP_BOX_X, TOP_BOX_Y, TOP_TEXT_X, TOP_TEXT_Y,
    BOTTOM_BOX_X, BOTTOM_BOX_Y, BOTTOM_TEXT_X, BOTTOM_TEXT_Y,
    BANGLA_FONT_PATH, ENGLISH_FONT_PATH,
    WATERMARK_IMAGE, FLOWER_IMAGE
)
from downloader import probe_media

EMOJI_FONT_PATH = os.path.join(os.path.dirname(BANGLA_FONT_PATH), "emoji_font.ttf")

def is_emoji_only_or_mostly(text: str) -> bool:
    # Check if text contains typical emojis
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2b50]",
        flags=re.UNICODE
    )
    return bool(emoji_pattern.search(text))

def draw_styled_text_block(draw: ImageDraw.ImageDraw, text: str, start_x: int, start_y: int):
    """
    Renders text and emojis cleanly line-by-line.
    Handles Bangla, English, and Color Emojis.
    """
    lines = text.split("\n")
    current_y = start_y
    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_y += 30
            continue

        has_bangla = any('\u0980' <= c <= '\u09FF' for c in stripped)
        has_emoji = is_emoji_only_or_mostly(stripped)

        if has_emoji and not has_bangla and len(stripped) <= 10:
            # Emoji line
            try:
                font = ImageFont.truetype(EMOJI_FONT_PATH, 48)
                draw.text((start_x, current_y), stripped, font=font, embedded_color=True)
                bbox = draw.textbbox((start_x, current_y), stripped, font=font)
                current_y += max(60, bbox[3] - bbox[1] + 15)
                continue
            except Exception:
                pass

        # Text line (English or Bangla)
        font_path = BANGLA_FONT_PATH if has_bangla else ENGLISH_FONT_PATH
        font = ImageFont.truetype(font_path, 48 if not has_bangla else 42)

        # Subtle shadow
        draw.text((start_x + 2, current_y + 2), stripped, font=font, fill=(210, 210, 210, 180))
        # Main text
        draw.text((start_x, current_y), stripped, font=font, fill=(25, 25, 25, 255))

        bbox = draw.textbbox((start_x, current_y), stripped, font=font)
        line_height = max(55, bbox[3] - bbox[1] + 16)
        current_y += line_height

def generate_template_overlay(top_text: str, bottom_text: str, output_path: str):
    """Generates transparent PNG overlay containing text, card borders, flower, and watermark."""
    img = Image.new('RGBA', (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Subtle decorative borders around media boxes
    border_color = (205, 205, 210, 255)
    draw.rounded_rectangle(
        [TOP_BOX_X - 4, TOP_BOX_Y - 4, TOP_BOX_X + MEDIA_BOX_WIDTH + 4, TOP_BOX_Y + MEDIA_BOX_HEIGHT + 4],
        radius=12, outline=border_color, width=3
    )
    draw.rounded_rectangle(
        [BOTTOM_BOX_X - 4, BOTTOM_BOX_Y - 4, BOTTOM_BOX_X + MEDIA_BOX_WIDTH + 4, BOTTOM_BOX_Y + MEDIA_BOX_HEIGHT + 4],
        radius=12, outline=border_color, width=3
    )

    # 2. Text rendering
    draw_styled_text_block(draw, top_text, TOP_TEXT_X, TOP_TEXT_Y)
    draw_styled_text_block(draw, bottom_text, BOTTOM_TEXT_X, BOTTOM_TEXT_Y)

    # 3. Flower decoration (top-left)
    if os.path.exists(FLOWER_IMAGE):
        try:
            flower = Image.open(FLOWER_IMAGE).convert('RGBA')
            img.paste(flower, (0, 80), flower)
        except Exception as e:
            print(f"Could not paste flower: {e}")

    # 4. Watermark / Logo (bottom-right)
    if os.path.exists(WATERMARK_IMAGE):
        try:
            wm = Image.open(WATERMARK_IMAGE).convert('RGBA')
            wm_x = CANVAS_WIDTH - wm.width - 50
            wm_y = CANVAS_HEIGHT - wm.height - 180
            img.paste(wm, (wm_x, wm_y), wm)
        except Exception as e:
            print(f"Could not paste watermark: {e}")

    img.save(output_path, "PNG")
    return output_path

def build_reaction_video(
    top_media_path: str,
    bottom_media_path: str,
    top_text: str,
    bottom_text: str,
    audio_choice: str = "mute_bottom", # "mute_top", "mute_bottom", "keep_both"
    output_filename: str = None,
    trending_audio_path: str = None,
    trending_volume: float = 0.0 # 0.0 = mute (0.0001 fingerprint), 0.01 = 1%, 0.02 = 2%
) -> str:
    """
    Renders the final reaction video using FFmpeg.
    """
    uid = uuid.uuid4().hex[:8]
    if not output_filename:
        output_filename = f"final_reaction_{uid}.mp4"
    final_output = os.path.join(TEMP_DIR, output_filename)
    overlay_png = os.path.join(TEMP_DIR, f"overlay_{uid}.png")

    # Generate overlay PNG
    generate_template_overlay(top_text, bottom_text, overlay_png)

    # Probe media
    top_probe = probe_media(top_media_path)
    bottom_probe = probe_media(bottom_media_path)

    # Determine duration
    if top_probe['is_video'] and bottom_probe['is_video']:
        duration = max(top_probe['duration'], bottom_probe['duration'])
        if duration <= 1:
            duration = 15.0
    elif top_probe['is_video']:
        duration = top_probe['duration'] if top_probe['duration'] > 1 else 15.0
    elif bottom_probe['is_video']:
        duration = bottom_probe['duration'] if bottom_probe['duration'] > 1 else 15.0
    else:
        duration = 15.0

    duration = min(duration, 60.0)

    # Build inputs
    cmd = ['ffmpeg', '-y']

    # Input 0: White background
    cmd += ['-f', 'lavfi', '-i', f'color=c=white:s={CANVAS_WIDTH}x{CANVAS_HEIGHT}:d={duration:.2f}:r={FPS}']

    # Input 1: Top Media
    if not top_probe['is_video']:
        cmd += ['-loop', '1', '-t', f'{duration:.2f}', '-i', top_media_path]
    else:
        cmd += ['-stream_loop', '-1', '-i', top_media_path]

    # Input 2: Bottom Media
    if not bottom_probe['is_video']:
        cmd += ['-loop', '1', '-t', f'{duration:.2f}', '-i', bottom_media_path]
    else:
        cmd += ['-stream_loop', '-1', '-i', bottom_media_path]

    # Input 3: Overlay PNG
    cmd += ['-loop', '1', '-t', f'{duration:.2f}', '-i', overlay_png]

    # Input 4: Optional Trending Audio
    has_trending = trending_audio_path and os.path.exists(trending_audio_path)
    if has_trending:
        cmd += ['-stream_loop', '-1', '-i', trending_audio_path]

    # Video filters
    filter_complex = [
        f"[1:v]scale={MEDIA_BOX_WIDTH}:{MEDIA_BOX_HEIGHT}:force_original_aspect_ratio=increase,crop={MEDIA_BOX_WIDTH}:{MEDIA_BOX_HEIGHT},setsar=1[top_v]",
        f"[2:v]scale={MEDIA_BOX_WIDTH}:{MEDIA_BOX_HEIGHT}:force_original_aspect_ratio=increase,crop={MEDIA_BOX_WIDTH}:{MEDIA_BOX_HEIGHT},setsar=1[bot_v]",
        f"[0:v][top_v]overlay=x={TOP_BOX_X}:y={TOP_BOX_Y}:eof_action=pass[bg_top]",
        f"[bg_top][bot_v]overlay=x={BOTTOM_BOX_X}:y={BOTTOM_BOX_Y}:eof_action=pass[bg_both]",
        f"[bg_both][3:v]overlay=x=0:y=0:shortest=1[final_v]"
    ]

    # Audio filter routing
    has_top_audio = top_probe['is_video'] and top_probe['has_audio']
    has_bottom_audio = bottom_probe['is_video'] and bottom_probe['has_audio']

    if has_top_audio and has_bottom_audio:
        if audio_choice == "mute_top":
            filter_complex.append("[2:a]aresample=async=1[main_a]")
        elif audio_choice == "mute_bottom":
            filter_complex.append("[1:a]aresample=async=1[main_a]")
        else: # keep_both
            filter_complex.append("[1:a][2:a]amix=inputs=2:duration=longest:dropout_transition=2[main_a]")
    elif has_top_audio:
        filter_complex.append("[1:a]aresample=async=1[main_a]")
    elif has_bottom_audio:
        filter_complex.append("[2:a]aresample=async=1[main_a]")
    else:
        filter_complex.append(f"aevalsrc=0:d={duration:.2f}[main_a]")

    # Mix in trending audio if present
    if has_trending:
        vol = float(trending_volume)
        if vol <= 0.0:
            vol = 0.0001 # 0% Mute, retains algorithmic audio fingerprinting
        filter_complex.append(f"[4:a]volume={vol:.4f}[trend_a]")
        filter_complex.append("[main_a][trend_a]amix=inputs=2:duration=first:dropout_transition=2[final_a]")
    else:
        filter_complex.append("[main_a]anull[final_a]")

    cmd += [
        '-filter_complex', ";".join(filter_complex),
        '-map', '[final_v]',
        '-map', '[final_a]',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '22',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-t', f'{duration:.2f}',
        final_output
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with code {res.returncode}: {res.stderr[-500:]}")

    if os.path.exists(overlay_png):
        try:
            os.remove(overlay_png)
        except Exception:
            pass

    return final_output
