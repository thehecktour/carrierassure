# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Multi-stage Dockerfile for Django app with Poetry, auto-migrate
#          on startup, slim image, dev target."
# Modifications: Switched from pip+requirements.txt to Poetry, added
#                migrate in CMD via shell script so it runs before the
#                server on every container start, separated dev/prod targets.
# --- END AI-ASSISTED ---

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

FROM base AS development

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]


FROM base AS production

COPY . .

RUN addgroup --system appgroup && adduser --system --group appuser
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn src.wsgi:application --bind 0.0.0.0:8000 --workers 2"]