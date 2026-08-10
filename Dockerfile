# Builder stage
FROM python:3.10-slim-bullseye AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final stage
FROM python:3.10-slim-bullseye

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libsm6 libxrender1 libxext6 libgomp1 && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy only installed packages from builder
COPY --from=builder /install /usr/local

# Copy only required application files
COPY app.py .
COPY config.py .
COPY models.py .
COPY models ./models

EXPOSE 5000

CMD ["gunicorn", "--workers=1", "--threads=2", "--timeout=120", "--bind=0.0.0.0:5000", "app:app"]