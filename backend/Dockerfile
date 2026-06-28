# Nua Backend — FastAPI + Motor (MongoDB driver)
# Used by Fly.io, Railway, Render, Docker Compose — anywhere that speaks Docker.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Native deps for cryptography, bcrypt, etc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir emergentintegrations \
      --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Copy the app
COPY . .

EXPOSE 8001

# Use uvicorn directly (single worker; Fly handles horizontal scaling).
# --proxy-headers respects the X-Forwarded-* set by Fly's edge.
CMD ["uvicorn", "server:app", \
     "--host", "0.0.0.0", \
     "--port", "8001", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
