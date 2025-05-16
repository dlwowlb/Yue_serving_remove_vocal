# 1. 베이스 이미지
FROM python:3.9-slim

# 2. 작업 디렉터리 설정
WORKDIR /app

# 3. 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 복사
COPY gpt_main.py .

# 5. 환경변수 안내 (실행 시 docker run -e 로 설정)
#    예: -e YOUTUBE_API_KEY=YOUR_KEY -e CHANNEL_ID=UCxxxxxx
ENV YOUTUBE_API_KEY=""
ENV CHANNEL_ID=""
ENV OPENAI_API_KEY=""

# 6. 실행
CMD ["python", "gpt_main.py"]
