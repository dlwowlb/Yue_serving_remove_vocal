import os
import googleapiclient.discovery

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')  # API 키를 환경변수 등에서 불러오기
CHANNEL_ID = "UC............"  # 대상 채널의 ID (예: UC로 시작하는 고유 ID)

youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# 채널에서 라이브 상태인 영상 검색
search_response = youtube.search().list(
    part="snippet",
    channelId=CHANNEL_ID,
    type="video",
    eventType="live"    # 라이브 중인 영상만 필터
).execute()

live_video_id = None
for item in search_response.get("items", []):
    # 검색 결과 중 'liveBroadcastContent'가 'live'인 항목을 확인
    if item["snippet"].get("liveBroadcastContent") == "live":
        live_video_id = item["id"]["videoId"]
        break

if not live_video_id:
    print("현재 라이브 중인 영상이 없습니다.")

if live_video_id:
    video_response = youtube.videos().list(
        part="liveStreamingDetails",
        id=live_video_id
    ).execute()
    items = video_response.get("items", [])
    if items:
        live_chat_id = items[0]["liveStreamingDetails"].get("activeLiveChatId")
        print(f"Live Chat ID: {live_chat_id}")
    else:
        live_chat_id = None
        print("영상 상세 정보를 가져오지 못했습니다.")


import time
from google.cloud import firestore

# Firestore 초기화 (Cloud Function 환경에서는 기본 인증으로 프로젝트에 연결됨)
db = firestore.Client()
collection = db.collection("LiveChatMessages")  # 저장할 컬렉션 이름

if live_chat_id:
    next_page_token = None
    polling_interval = 5000  # 기본 5초 (밀리초)
    while True:
        chat_response = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=next_page_token
        ).execute()

        # 응답에서 메시지 리스트 가져오기
        messages = chat_response.get("items", [])
        for msg in messages:
            # 메시지 정보 추출
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
            # Firestore에 메시지 저장 (document ID를 메시지 ID로 설정)
            if message_id:
                collection.document(message_id).set(data)
            else:
                collection.add(data)
            print(f"[{published}] {author}: {text}")

        # 다음 페이지 토큰 및 폴링 간격 갱신
        next_page_token = chat_response.get("nextPageToken")
        polling_interval = chat_response.get("pollingIntervalMillis", 5000)
        if not next_page_token:
            # 더 가져올 토큰이 없으면 (스트림 종료 등) 루프 종료
            print("라이브 채팅이 종료되었거나 더 이상 메시지가 없습니다.")
            break

        # pollingIntervalMillis 동안 대기 (밀리초를 초로 변환)
        time.sleep(polling_interval / 1000.0)
