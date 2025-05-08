# 1. 베이스 이미지
FROM python:3.9-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 복사 & 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 애플리케이션 코드 복사
COPY main.py .

# 5. 컨테이너 포트(HTTP 트리거용) 설정
ENV PORT=8080
EXPOSE 8080

# 6. 진입점
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:collect_youtube_livechat"]
