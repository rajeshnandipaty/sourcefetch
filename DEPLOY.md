# Deploying SourceFetch

SourceFetch containerizes cleanly and runs on Google Cloud Run. The image builds
the vector index at build time using the offline embedder, so the container is
self-contained — no API key and no model download required to run.

## Two modes — and which one to deploy

- **Public demo (recommended): no API key.** The app serves retrieval-only
  ("extractive") answers — it returns the passages it retrieved, ranked by
  similarity. This is safe to expose publicly: there is no paid API call to
  abuse, and it still demonstrates the retrieval pipeline, the vector store, and
  the citation UI.
- **Full answers: with a key.** Set `ANTHROPIC_API_KEY` and the app composes
  grounded, cited answers with Claude. Each request costs a fraction of a cent,
  so enable this only where you control access.

## Run the container locally

```bash
docker build -t sourcefetch .
docker run -p 8080:8080 sourcefetch
# open http://localhost:8080
```

For full (Claude-composed) answers locally, pass your key:

```bash
docker run -p 8080:8080 -e ANTHROPIC_API_KEY=sk-ant-... sourcefetch
```

## Deploy to Google Cloud Run

Prerequisites: a Google Cloud project with billing enabled, and the gcloud CLI
installed and authenticated (`gcloud auth login`).

```bash
gcloud config set project YOUR_PROJECT_ID

# Cloud Build reads the Dockerfile, builds the image, and deploys it.
gcloud run deploy sourcefetch \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi
```

Cloud Run prints a public URL when it finishes. That URL is your live demo link —
put it on your portfolio next to the repo.

### Optional: enable Claude answers on Cloud Run

Store the key in Secret Manager rather than passing it on the command line:

```bash
echo -n "sk-ant-..." | gcloud secrets create anthropic-key --data-file=-
gcloud run services update sourcefetch \
  --region us-central1 \
  --update-secrets ANTHROPIC_API_KEY=anthropic-key:latest
```

With the key enabled, anyone who reaches the URL can spend your API credit. For a
public portfolio demo, leaving it in extractive mode is the safer choice.

## Notes

- The image uses the offline hashing embedder by default. To deploy with semantic
  (Hugging Face) embeddings, add `sentence-transformers` to the build and set
  `EMBEDDINGS_BACKEND=sentence-transformers` — the model downloads at build time,
  which makes the image larger.
- If a dependency wheel is unavailable on the slim base image, switch the
  Dockerfile's base to `python:3.12` (non-slim) or add `build-essential`.
- The sample index is tiny, so 512Mi is plenty. If you ingest the full CMS
  manuals, bump `--memory` accordingly.
