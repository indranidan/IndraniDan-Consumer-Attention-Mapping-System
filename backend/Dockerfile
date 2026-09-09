# =============================================================================
# CAMS Backend & AI Services — Production Dockerfile
# =============================================================================
# - Base image: Official Python 3.11 Slim on Debian
# - Hardened: Non-root user execution, layer caching, minimal attack surface
# - System libraries: Headless OpenCV, MediaPipe runtime, FFmpeg, PostgreSQL driver
# =============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app

# Install system runtime dependencies for OpenCV headless, MediaPipe, FFmpeg, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libgles2 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies with pip layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/backend/requirements.txt

# Install AI module dependencies (CPU-only PyTorch to minimize image size)
COPY ai/requirements.txt /app/ai/requirements.txt
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r /app/ai/requirements.txt

# Copy backend application source and AI engine packages
COPY backend /app/backend
COPY ai /app/ai

# Create non-root system user and prepare persistent storage directories
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser && \
    mkdir -p /app/storage/uploads \
             /app/storage/outputs/ai_jobs \
             /app/storage/outputs/reports \
             /app/outputs/ai_jobs && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

WORKDIR /app/backend

HEALTHCHECK --interval=20s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
