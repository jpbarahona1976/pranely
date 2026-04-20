# =============================================================================
# PRANELY Backend Dockerfile
# Multi-stage build for FastAPI
# =============================================================================

# ---- Dependencies ----
FROM python:3.12.7-slim AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY packages/backend/pyproject.toml /tmp/
RUN pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-venv --no-root

# ---- Builder ----
FROM python:3.12.7-slim AS builder
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY packages/backend/ /app
RUN pip install --no-deps -e .

# ---- Runner ----
FROM python:3.12.7-slim AS runner
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY --from=builder /app /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
