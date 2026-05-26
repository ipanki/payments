FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY app/ app/
COPY alembic.ini .

RUN uv sync --no-dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

ENTRYPOINT ["sh", "-c", "uv run alembic upgrade head && exec \"$@\"", "--"]
CMD ["uv", "run", "payments-api"]
