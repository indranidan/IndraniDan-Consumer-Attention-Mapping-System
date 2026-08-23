# Multi-stage / optimized Python Dockerfile for CAMS Backend & AI Services
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install system runtime dependencies for OpenCV, MediaPipe, and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/backend/requirements.txt

# Copy source code and models
COPY backend /app/backend
COPY ai /app/ai

ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
