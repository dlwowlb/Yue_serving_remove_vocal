FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

# Cloud Run이 기동되면 main.py가 바로 실행되도록 ENTRYPOINT 설정
ENTRYPOINT ["python", "main.py"]
