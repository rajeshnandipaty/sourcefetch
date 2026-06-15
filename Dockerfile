# SourceFetch — container image for local Docker or Google Cloud Run.
#
# The vector index is built INTO the image at build time from the sample corpus
# using the offline hashing embedder, so the running container needs no network
# and no API key to serve answers. Generated (Claude) answers are optional: set
# ANTHROPIC_API_KEY at deploy time to enable them. With no key, the app serves
# retrieval-only ("extractive") answers — the safe mode for a public demo.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    EMBEDDINGS_BACKEND=hashing

WORKDIR /app

# Dependencies first, for layer caching. If a wheel is unavailable on slim,
# switch the base image to python:3.12 (non-slim) or add build-essential here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY . .

# Bake the vector index into the image (offline; uses the hashing embedder).
RUN python scripts/ingest.py

EXPOSE 8080

# Cloud Run injects PORT (defaults to 8080 locally). Shell form so $PORT expands.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
