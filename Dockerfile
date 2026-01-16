# syntax=docker/dockerfile:1.5
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Tashkent

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg postgresql-client tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/backups \
    && chown -R appuser:appuser /app/backups

COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
