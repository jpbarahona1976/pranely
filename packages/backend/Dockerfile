# =============================================================================
# PRANELY Backend Dockerfile
# Multi-stage build for FastAPI
# =============================================================================

# ---- Dependencies ----
FROM python:3.12.7-slim AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp
COPY pyproject.toml /tmp/
RUN pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-root

# ---- Builder ----
# ---- Builder ----
FROM python:3.12.7-slim AS builder
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . /app

# ---- Runner ----
# ---- Runner ----
FROM python:3.12.7-slim AS runner
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
