# =============================================================================
# PRANELY Backend Dockerfile
# Multi-stage build for FastAPI
# =============================================================================

# =============================================================================
# PRANELY Backend Dockerfile
# Development build with hot reload
# =============================================================================

FROM python:3.12.7-slim
WORKDIR /app
RUN pip install poetry==1.8.3
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
