# Echoes of the Terminal — Web 버전 Docker 이미지
# 빌드:  docker build -t echoes-web .
# 실행:  docker run -p 8000:8000 echoes-web
# fly.io: fly deploy (fly.toml 별도 설정)

FROM python:3.12-slim

WORKDIR /app

# 의존성 레이어 (캐시 활용)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 실행 (단일 워커 — 세션 인메모리, 스케일아웃 시 Redis 세션 필요)
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
