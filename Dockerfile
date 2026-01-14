# syntax=docker/dockerfile:1.5
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" appuser

COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chmod +x /app/entrypoint.sh

USER appuser

# ENTRYPOINT ["sh", "/app/entrypoint.sh"]
