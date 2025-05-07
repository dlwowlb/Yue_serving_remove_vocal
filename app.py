# requirements.txt에는 google-api-python-client, google-cloud-firestore 등이 명시되어야 함.

import os
import time
from googleapiclient.discovery import build
from google.cloud import firestore

# 환경변수에서 API 키와 채널 ID 불러오기
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# Firestore 클라이언트 초기화
db = firestore.Client()

def collect_youtube_livechat(request):
    # 1. 라이브 영상 ID 검색
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    search_response = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        type="video",
        eventType="live"
    ).execute()
    live_video_id = None
    for item in search_response.get("items", []):
        if item["snippet"].get("liveBroadcastContent") == "live":
            live_video_id = item["id"]["videoId"]
            break
    if not live_video_id:
        return "No live video currently."

    # 2. 라이브 채팅 ID 획득
    video_response = youtube.videos().list(
        part="liveStreamingDetails",
        id=live_video_id
    ).execute()
    items = video_response.get("items", [])
    if not items:
        return "Live video details not found."
    live_chat_id = items[0]["liveStreamingDetails"].get("activeLiveChatId")
    if not live_chat_id:
        return "No active live chat."

    # 3. 라이브 채팅 메시지 수집 (5초 간격)
    next_page_token = None
    while True:
        chat_response = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=next_page_token
        ).execute()
        messages = chat_response.get("items", [])
        for msg in messages:
            author = msg["authorDetails"].get("displayName")
            text = msg["snippet"].get("displayMessage")
            published = msg["snippet"].get("publishedAt")
            message_id = msg.get("id")
            data = {
                "video_id": live_video_id,
                "author": author,
                "message": text,
                "publishedAt": published
            }
            # Firestore에 저장
            if message_id:
                db.collection("LiveChatMessages").document(message_id).set(data)
            else:
                db.collection("LiveChatMessages").add(data)
        # 다음 토큰 및 인터벌 처리
        next_page_token = chat_response.get("nextPageToken")
        poll_interval = chat_response.get("pollingIntervalMillis", 5000)
        if not next_page_token:
            break
        time.sleep(poll_interval / 1000.0)
    return f"Collected messages from live chat {live_chat_id}."
