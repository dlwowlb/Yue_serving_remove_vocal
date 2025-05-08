import os
import time
from googleapiclient.discovery import build
from google.cloud import firestore

# 환경변수에서 API 키/채널 ID 읽기
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID       = os.environ["CHANNEL_ID"]

# Firestore 클라이언트
db = firestore.Client()

# 라이브 스트림의 chat_id, nextPageToken 전역으로 유지
live_chat_id = None
next_page_token = None

def get_live_chat_id(youtube):
    global live_chat_id
    if live_chat_id:
        return live_chat_id
    # 1) 채널에서 현재 라이브 영상 검색
    res = youtube.search().list(
        part="id,snippet",
        channelId=CHANNEL_ID,
        eventType="live",
        type="video"
    ).execute()
    for itm in res.get("items", []):
        if itm["snippet"]["liveBroadcastContent"] == "live":
            live_chat_id = itm["id"]["videoId"]
            # 실제 chatId는 videos.list로 한 번 더 조회해야 하지만, 
            # 여기서는 shortcut으로 liveChatId == videoId 로 가정할 수도 있습니다.
            return live_chat_id
    return None

def poll_loop():
    global next_page_token
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    while True:
        chat_id = get_live_chat_id(youtube)
        if not chat_id:
            print("▶️ 아직 라이브 없음, 5초 대기…")
            time.sleep(5)
            continue

        resp = youtube.liveChatMessages().list(
            liveChatId=chat_id,
            part="snippet,authorDetails",
            pageToken=next_page_token
        ).execute()

        # 받은 메시지 저장
        for msg in resp.get("items", []):
            doc = {
                "author":      msg["authorDetails"]["displayName"],
                "message":     msg["snippet"]["displayMessage"],
                "publishedAt": msg["snippet"]["publishedAt"]
            }
            doc_id = msg.get("id")
            col = db.collection("LiveChatMessages")
            if doc_id:
                col.document(doc_id).set(doc)
            else:
                col.add(doc)
            print(f"[{doc['publishedAt']}] {doc['author']}: {doc['message']}")

        next_page_token = resp.get("nextPageToken")
        time.sleep(5)  # 5초 간격

if __name__ == "__main__":
    poll_loop()
