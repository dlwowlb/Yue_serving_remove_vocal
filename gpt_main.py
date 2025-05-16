import os
import time
import json
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 환경변수에서 API 키와 채널 ID를 불러옵니다
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID       = os.getenv("CHANNEL_ID")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

if not YOUTUBE_API_KEY or not CHANNEL_ID:
    raise RuntimeError("환경변수 YOUTUBE_API_KEY와 CHANNEL_ID를 설정해주세요.")
if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 OPENAI_API_KEY를 설정해주세요.")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

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


def classify_message(text: str) -> str:
    """GPT API를 호출하여 chat 코멘트를 genre, instrument, mood, gender 형태로 분류합니다."""
    system_prompt = (
        "당신은 음악 채팅 메시지를 '장르, 악기, 분위기, 성별' 키워드로 요약하는 분류기입니다. "
        "각 속성은 단어 하나로 표현하고 쉼표로 구분하여 한 문장으로 출력해주세요."
    )
    user_prompt = f"분류할 메시지: '{text}'"

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    return resp.choices[0].message.content.strip()


def poll_and_classify_interval(live_chat_id: str, interval: float = 30.0):
    """채팅을 계속 폴링하며, 지정된 interval(초)마다 한 번씩 전체 메시지를 분류합니다."""
    next_page_token = None
    buffer_msgs = []
    start_time = time.time()
    log_file = open("chats.log", "a", encoding="utf-8")
    try:
        while True:
            resp = youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part="snippet,authorDetails",
                pageToken=next_page_token
            ).execute()

            # 메시지 버퍼링
            for msg in resp.get("items", []):
                buffer_msgs.append(msg["snippet"].get("displayMessage"))

            next_page_token = resp.get("nextPageToken")
            time.sleep(resp.get("pollingIntervalMillis", 5000) / 1000.0)

            # interval 경과 시 분류 수행
            if time.time() - start_time >= interval:
                if buffer_msgs:
                    combined = " \n".join(buffer_msgs)
                    try:
                        classification = classify_message(combined)
                        print(f"Classification (last {interval}s): {classification}", flush=True)
                        log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Last {interval}s -> {classification}\n")
                    except Exception as e:
                        print(f"Classification error: {e}")
                        log_file.write(f"Classification error: {e}\n")
                    buffer_msgs = []
                start_time = time.time()
    except HttpError as e:
        print(f"HTTP Error: {e}")
    except KeyboardInterrupt:
        print("폴링 종료")
    finally:
        log_file.close()


def main():
    # 라이브 스트림 및 채팅 활성화 대기
    while True:
        vid = get_live_video_id()
        if vid:
            print(f"Live Video ID: {vid}")
            break
        print("현재 라이브 스트리밍을 찾을 수 없습니다. 60초 후 재시도합니다.")
        time.sleep(60)

    while True:
        chat_id = get_live_chat_id(vid)
        if chat_id:
            print(f"Live Chat ID: {chat_id}")
            break
        print("라이브 채팅이 활성화되지 않았습니다. 60초 후 재시도합니다.")
        time.sleep(60)

    # 30초마다 메시지 분류
    poll_and_classify_interval(chat_id, interval=30.0)


if __name__ == "__main__":
    main()
