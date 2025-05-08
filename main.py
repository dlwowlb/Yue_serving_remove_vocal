import os
import time
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 환경변수에서 API 키와 채널 ID 불러오기
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID       = os.getenv("CHANNEL_ID")

if not YOUTUBE_API_KEY or not CHANNEL_ID:
    raise RuntimeError("환경변수 YOUTUBE_API_KEY와 CHANNEL_ID를 설정해주세요.")

# YouTube API 클라이언트 초기화
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def get_live_video_id():
    """채널에서 현재 라이브 중인 영상의 ID를 반환."""
    resp = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        type="video",
        eventType="live"
    ).execute()
    for item in resp.get("items", []):
        if item["snippet"].get("liveBroadcastContent") == "live":
            return item["id"]["videoId"]
    return None

def get_live_chat_id(video_id: str):
    """영상 ID로부터 liveChatId 반환."""
    resp = youtube.videos().list(
        part="liveStreamingDetails",
        id=video_id
    ).execute()
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["liveStreamingDetails"].get("activeLiveChatId")

def poll_live_chat(live_chat_id: str):
    """liveChatId로 채팅을 폴링하고 결과를 stdout 및 파일에 기록."""
    next_page_token = None
    log_file = open("chats.log", "a", encoding="utf-8")
    try:
        while True:
            resp = youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part="snippet,authorDetails",
                pageToken=next_page_token
            ).execute()
            for msg in resp.get("items", []):
                rec = {
                    "id":        msg.get("id"),
                    "author":    msg["authorDetails"].get("displayName"),
                    "message":   msg["snippet"].get("displayMessage"),
                    "timestamp": msg["snippet"].get("publishedAt")
                }
                line = json.dumps(rec, ensure_ascii=False)
                print(line)
                log_file.write(line + "\n")
            next_page_token = resp.get("nextPageToken")
            interval = resp.get("pollingIntervalMillis", 5000) / 1000.0
            time.sleep(interval)
    except HttpError as e:
        print(f"HTTP Error: {e}")
    except KeyboardInterrupt:
        print("폴링 종료")
    finally:
        log_file.close()

def main():
    vid = get_live_video_id()
    if not vid:
        print("현재 라이브 스트리밍을 찾을 수 없습니다.")
        return
    print(f"Live Video ID: {vid}")

    chat_id = get_live_chat_id(vid)
    if not chat_id:
        print("라이브 채팅이 활성화되지 않았습니다.")
        return
    print(f"Live Chat ID: {chat_id}")

    poll_live_chat(chat_id)

if __name__ == "__main__":
    main()
