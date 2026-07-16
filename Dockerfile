FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless the lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY tempbot.py ./

ENV PATH="/app/.venv/bin:${PATH}"

# config.ini is git-ignored (holds secrets) and is expected to be
# provided at runtime, e.g.:
#   docker run -v ./config.ini:/app/config.ini:ro tempbot
CMD ["python", "tempbot.py"]
