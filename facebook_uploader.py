import os
import json
import time
import logging
import requests

from config import FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def check_facebook_config() -> bool:
    """Returns True if Facebook Page ID and Access Token are configured."""
    return bool(FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN 
                and FACEBOOK_PAGE_ID != "YOUR_PAGE_ID_HERE"
                and FACEBOOK_ACCESS_TOKEN != "YOUR_PAGE_ACCESS_TOKEN_HERE")


def upload_video_to_facebook(
    video_path: str,
    title: str = None,
    description: str = None,
    schedule_time_unix: int = None
) -> dict:
    """
    Uploads a video to Facebook Page as a Reel.
    
    Args:
        video_path: Path to the video file (MP4)
        title: Video title
        description: Video description/caption
        schedule_time_unix: Unix timestamp for scheduled publishing (optional)
    
    Returns:
        dict with keys: id, url, title, scheduled
    """
    if not check_facebook_config():
        raise ValueError(
            "Facebook কনফিগারেশন সেট করা হয়নি!\n"
            "config.py ফাইলে FACEBOOK_PAGE_ID এবং FACEBOOK_ACCESS_TOKEN সেট করুন।\n"
            "বিস্তারিত জানতে FacebookGuide.txt পড়ুন।"
        )
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    file_size = os.path.getsize(video_path)
    if not title:
        title = "Amazing Reaction Video 🔥 #Shorts #Reels"
    if not description:
        description = title
    
    logger.info(f"Starting Facebook Reels upload: {title}")
    logger.info(f"Video file size: {file_size / (1024*1024):.2f} MB")
    
    # ========== Phase 1: Initialize Upload Session ==========
    init_url = f"{GRAPH_API_BASE}/{FACEBOOK_PAGE_ID}/video_reels"
    init_params = {
        "upload_phase": "start",
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    logger.info("Phase 1: Initializing Facebook upload session...")
    init_response = requests.post(init_url, data=init_params)
    
    if init_response.status_code != 200:
        error_data = init_response.json().get("error", {})
        raise RuntimeError(
            f"Facebook upload initialization failed: "
            f"{error_data.get('message', init_response.text)}"
        )
    
    init_data = init_response.json()
    video_id = init_data.get("video_id")
    upload_url = init_data.get("upload_url")
    
    if not video_id:
        raise RuntimeError(f"Facebook did not return video_id: {init_data}")
    
    logger.info(f"Upload session initialized. Video ID: {video_id}")
    
    # ========== Phase 2: Upload Video Binary ==========
    logger.info("Phase 2: Uploading video binary data...")
    
    # If upload_url is provided, upload directly to it
    if upload_url:
        with open(video_path, "rb") as video_file:
            upload_headers = {
                "Authorization": f"OAuth {FACEBOOK_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size)
            }
            upload_response = requests.post(
                upload_url,
                headers=upload_headers,
                data=video_file.read()
            )
    else:
        # Fallback: upload via graph API
        upload_endpoint = f"{GRAPH_API_BASE}/{video_id}"
        with open(video_path, "rb") as video_file:
            upload_headers = {
                "Authorization": f"OAuth {FACEBOOK_ACCESS_TOKEN}",
                "offset": "0",
                "file_size": str(file_size)
            }
            upload_response = requests.post(
                upload_endpoint,
                headers=upload_headers,
                data=video_file.read()
            )
    
    if upload_response.status_code != 200:
        error_data = upload_response.json().get("error", {}) if upload_response.text else {}
        raise RuntimeError(
            f"Facebook video binary upload failed: "
            f"{error_data.get('message', upload_response.text)}"
        )
    
    logger.info("Video binary uploaded successfully.")
    
    # ========== Phase 3: Finish Upload (Publish) ==========
    logger.info("Phase 3: Finishing upload and publishing...")
    
    finish_url = f"{GRAPH_API_BASE}/{FACEBOOK_PAGE_ID}/video_reels"
    finish_params = {
        "upload_phase": "finish",
        "access_token": FACEBOOK_ACCESS_TOKEN,
        "video_id": video_id,
        "title": title[:255],  # Facebook title limit
        "description": description
    }
    
    if schedule_time_unix:
        finish_params["scheduled_publish_time"] = schedule_time_unix
        finish_params["published"] = "false"
    
    finish_response = requests.post(finish_url, data=finish_params)
    
    if finish_response.status_code != 200:
        error_data = finish_response.json().get("error", {}) if finish_response.text else {}
        logger.warning(
            f"Facebook finish phase returned status {finish_response.status_code}: "
            f"{error_data.get('message', finish_response.text)}"
        )
        # Even if finish fails, video might still be processing
    
    finish_data = finish_response.json() if finish_response.text else {}
    success = finish_data.get("success", False)
    
    if success:
        logger.info(f"Facebook Reel published successfully! Video ID: {video_id}")
    else:
        logger.info(f"Facebook upload completed (processing). Video ID: {video_id}")
    
    video_url = f"https://www.facebook.com/reel/{video_id}"
    
    return {
        "id": video_id,
        "url": video_url,
        "title": title,
        "scheduled": bool(schedule_time_unix),
        "success": success
    }


def upload_video_as_post(
    video_path: str,
    title: str = None,
    description: str = None,
    schedule_time_unix: int = None
) -> dict:
    """
    Alternative: Uploads video as a regular Facebook Page video post (not Reel).
    Use this as fallback if Reels API has issues.
    """
    if not check_facebook_config():
        raise ValueError("Facebook কনফিগারেশন সেট করা হয়নি!")
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if not title:
        title = "Amazing Reaction Video 🔥"
    if not description:
        description = title
    
    upload_url = f"{GRAPH_API_BASE}/{FACEBOOK_PAGE_ID}/videos"
    
    params = {
        "access_token": FACEBOOK_ACCESS_TOKEN,
        "title": title[:255],
        "description": description
    }
    
    if schedule_time_unix:
        params["scheduled_publish_time"] = schedule_time_unix
        params["published"] = "false"
    
    with open(video_path, "rb") as video_file:
        files = {"source": (os.path.basename(video_path), video_file, "video/mp4")}
        response = requests.post(upload_url, data=params, files=files)
    
    if response.status_code != 200:
        error_data = response.json().get("error", {}) if response.text else {}
        raise RuntimeError(
            f"Facebook video post upload failed: "
            f"{error_data.get('message', response.text)}"
        )
    
    result = response.json()
    video_id = result.get("id", "")
    
    return {
        "id": video_id,
        "url": f"https://www.facebook.com/{FACEBOOK_PAGE_ID}/videos/{video_id}",
        "title": title,
        "scheduled": bool(schedule_time_unix),
        "success": True
    }


if __name__ == "__main__":
    print("========================================")
    print("  Facebook Upload Configuration Check")
    print("========================================")
    if check_facebook_config():
        print(f"✅ Facebook Page ID: {FACEBOOK_PAGE_ID}")
        print(f"✅ Access Token: {FACEBOOK_ACCESS_TOKEN[:20]}...")
        print("\nFacebook কনফিগারেশন সঠিকভাবে সেটআপ করা হয়েছে!")
    else:
        print("❌ Facebook কনফিগারেশন সেটআপ করা হয়নি!")
        print("\nconfig.py ফাইলে নিচের ভ্যালুগুলো সেট করুন:")
        print("  FACEBOOK_PAGE_ID = 'আপনার_পেজ_আইডি'")
        print("  FACEBOOK_ACCESS_TOKEN = 'আপনার_পেজ_এক্সেস_টোকেন'")
        print("\nবিস্তারিত জানতে FacebookGuide.txt পড়ুন।")
