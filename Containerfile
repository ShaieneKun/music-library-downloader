FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first so this layer is cached across code changes.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py ./
COPY src ./src

# Everything persistent lives under /data: songs, Drive auth/state, logs.
RUN adduser -u 5678 --disabled-password --gecos "" appuser \
    && mkdir -p /data \
    && chown -R appuser /app /data
USER appuser

ENV DESTINATION_FOLDER=/data/songs \
    STATE_DIR=/data/state \
    LOG_DIR=/data/logs
VOLUME /data

CMD ["python", "main.py", "run"]
