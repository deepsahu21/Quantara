# ── Quantara Backend ──────────────────────────────────────────────
# Multi-stage build: slim Python image with only runtime deps
# ──────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc / buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install dependencies first (layer cache) ─────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ────────────────────────────────────────
COPY . .

EXPOSE 8000

# Run with Uvicorn — 0.0.0.0 so Docker networking works
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
