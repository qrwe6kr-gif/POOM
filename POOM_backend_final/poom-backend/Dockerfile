# POOM 백엔드 컨테이너.
# Railway는 Dockerfile 없이도(Nixpacks) 배포되므로 이 파일은 이식성용이다 —
# Render·Fly·로컬 등 어디서도 같은 방식으로 뜨게 한다.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 의존성 레이어를 소스와 분리해 코드 변경 시 재설치를 피한다
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 배포 플랫폼(Railway/Render)이 PORT를 주입한다. 없으면 8000으로 뜬다.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
