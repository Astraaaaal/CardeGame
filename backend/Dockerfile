FROM python:3.12-slim

WORKDIR /app

# Dépendances système pour asyncpg et Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render fournit $PORT ; --proxy-headers pour récupérer la vraie IP client (rate limit).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
