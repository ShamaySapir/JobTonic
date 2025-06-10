# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /app/deps

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /app/deps /app/deps
COPY app.py .
COPY src/ ./src

ENV PYTHONPATH=/app/deps:/app/src

# ENTRYPOINT ["uvicorn", "app:app", \
#             "--host", "0.0.0.0", \
#             "--port", "8080", \
#             "--workers", "4", \
#             "--log-level", "info"]
# ENTRYPOINT ["python", "app.py"]