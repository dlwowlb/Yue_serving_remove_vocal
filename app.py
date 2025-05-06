import os
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL_SEC', 5))

def get_live_chat_id(broadcast_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    resp = youtube.liveBroadcasts().list(
        part='snippet',
        id=broadcast_id
    ).execute()
    return resp['items'][0]['snippet']['liveChatId']

def poll_chat(live_chat_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    next_page_token = None

    while True:
        try:
            resp = youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part='snippet,authorDetails',
                pageToken=next_page_token,
            ).execute()

            for msg in resp.get('items', []):
                author = msg['authorDetails']['displayName']
                text   = msg['snippet']['displayMessage']
                timestamp = msg['snippet']['publishedAt']
                # TODO: Pub/Sub, BigQuery, Logging 등 원하는 처리
                print(f"[{timestamp}] {author}: {text}")

            next_page_token = resp.get('nextPageToken')
            interval = resp.get('pollingIntervalMillis', POLL_INTERVAL * 1000) / 1000.0
            time.sleep(interval)

        except HttpError as e:
            print("Error polling chat:", e)
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    # 환경변수 또는 파라미터로 받아올 수 있음
    BROADCAST_ID = os.environ['BROADCAST_ID']  
    chat_id = get_live_chat_id(BROADCAST_ID)
    print("LiveChatId:", chat_id)
    poll_chat(chat_id)
