import os
import time
from googleapiclient.discovery import build
from google.cloud import firestore

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID       = os.environ["CHANNEL_ID"]

db = firestore.Client()

def collect_youtube_livechat(request):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    # 1) 현재 라이브 영상 검색
    search_res = youtube.search().list(
        part="snippet", channelId=CHANNEL_ID,
        type="video", eventType="live"
    ).execute()
    live_vid = next(
        (i["id"]["videoId"] for i in search_res.get("items", [])
         if i["snippet"].get("liveBroadcastContent")=="live"),
        None
    )
    if not live_vid:
        return "No live video."

    # 2) 채팅 ID 조회
    vid_res = youtube.videos().list(
        part="liveStreamingDetails", id=live_vid
    ).execute()
    details = vid_res.get("items", [{}])[0].get("liveStreamingDetails", {})
    live_chat_id = details.get("activeLiveChatId")
    if not live_chat_id:
        return "No active chat."

    # 3) 채팅 메시지 폴링 및 Firestore 저장
    next_token = None
    while True:
        chat_res = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=next_token
        ).execute()
        for msg in chat_res.get("items", []):
            doc = {
                "video_id":    live_vid,
                "author":      msg["authorDetails"]["displayName"],
                "message":     msg["snippet"]["displayMessage"],
                "publishedAt": msg["snippet"]["publishedAt"]
            }
            msg_id = msg.get("id")
            if msg_id:
                db.collection("LiveChatMessages").document(msg_id).set(doc)
            else:
                db.collection("LiveChatMessages").add(doc)
        next_token = chat_res.get("nextPageToken")
        interval = chat_res.get("pollingIntervalMillis", 5000)
        if not next_token:
            break
        time.sleep(interval / 1000.0)
    return f"Collected from chat {live_chat_id}"
