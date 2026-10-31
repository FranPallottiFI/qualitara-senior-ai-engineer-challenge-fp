FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Dependencies first (cached layer), including the dev group so tests run in the image.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen

COPY alembic.ini ./
COPY app/ app/
COPY migrations/ migrations/
COPY seed/ seed/
COPY tests/ tests/
