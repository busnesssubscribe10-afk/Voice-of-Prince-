import os
import json
import datetime
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import CLIENT_SECRETS_FILE, TOKEN_PICKLE_FILE, YOUTUBE_UPLOAD_SCOPE, CHANNEL_NAME

def get_youtube_service():
    """
    Authenticates and returns YouTube API service.
    Uses token.json if available. Automatically refreshes expired token.
    If not available, falls back to InstalledAppFlow if client_secrets.json exists.
    """
    creds = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PICKLE_FILE, YOUTUBE_UPLOAD_SCOPE)
        except Exception as e:
            print(f"Error loading {TOKEN_PICKLE_FILE}: {e}")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            with open(TOKEN_PICKLE_FILE, "w") as token:
                token.write(creds.to_json())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"'{CLIENT_SECRETS_FILE}' পাওয়া যায়নি! অনুগ্রহ করে Google Cloud Console থেকে client_secrets.json ফাইলটি রাখুন।"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, YOUTUBE_UPLOAD_SCOPE)
            creds = flow.run_local_server(port=0)
            # Save credentials for portability
            with open(TOKEN_PICKLE_FILE, "w") as token:
                token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_video_to_youtube(
    video_path: str,
    title: str = None,
    description: str = None,
    schedule_time_iso: str = None # ISO format UTC e.g. "2026-10-06T20:00:00Z"
) -> dict:
    """
    Uploads a video to YouTube.
    If schedule_time_iso is provided, video is uploaded as scheduled (private with publishAt).
    Otherwise, video is published immediately as public.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    youtube = get_youtube_service()

    now_str = datetime.datetime.now().strftime("%d %b %Y %I:%M %p")
    if not title:
        title = f"Amazing Reaction Video 🔥 #Shorts #VoiceOfPrince {now_str}"
    elif "#Shorts" not in title:
        title = f"{title} #Shorts"

    if not description:
        description = f"Welcome to {CHANNEL_NAME}! Enjoy this reaction short.\n\n#Shorts #Viral #Trending #Reactions"

    # Status body
    if schedule_time_iso:
        # YouTube requires scheduled videos to have privacyStatus='private'
        status_body = {
            "privacyStatus": "private",
            "publishAt": schedule_time_iso,
            "selfDeclaredMadeForKids": False
        }
    else:
        status_body = {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }

    body = {
        "snippet": {
            "title": title[:100], # YouTube max title length 100
            "description": description,
            "tags": ["Shorts", "Reaction", "Trending", "Viral", "রহমত ওয়াইটি", "YouTube Shorts"],
            "categoryId": "24" # Entertainment
        },
        "status": status_body
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 4
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"Uploading to YouTube: {progress}%")

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"Video uploaded successfully! URL: {video_url}")

    return {
        "id": video_id,
        "url": video_url,
        "title": title,
        "scheduled": bool(schedule_time_iso),
        "publishAt": schedule_time_iso
    }

if __name__ == "__main__":
    import sys
    print("Testing / Authorizing YouTube API...")
    try:
        service = get_youtube_service()
        print("YouTube Authentication SUCCESSFUL! token.json is ready and fully portable.")
    except Exception as e:
        print(f"YouTube Auth Info: {e}")
