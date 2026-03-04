# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Multi-stage Dockerfile for Django app, slim image, dev target."
# Modifications: Added PYTHONDONTWRITEBYTECODE, non-root user for production
#                stage, separated dev/prod targets.
# --- END AI-ASSISTED ---

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ------------------------------------------------------------------
# Development stage — usado pelo docker-compose por padrão
# ------------------------------------------------------------------
FROM base AS development

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ------------------------------------------------------------------
# Production stage — build com: docker build --target production
# ------------------------------------------------------------------
FROM base AS production

COPY . .

RUN addgroup --system appgroup && adduser --system --group appuser
USER appuser

EXPOSE 8000
CMD ["gunicorn", "src.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
