# SourceFetch

> Ask a plain-English question about billing and coding policy and get an answer drawn **only** from the source manuals, with every claim citing the passage it came from. Retrieval-augmented generation over reference text, with an evaluation harness that measures whether it actually works.

<img width="1920" height="1200" alt="SF3" src="https://github.com/user-attachments/assets/dcd47495-4492-4e39-a136-2ecbe4be5a37" />

<img width="1920" height="1200" alt="SF6" src="https://github.com/user-attachments/assets/6170097f-92df-4f54-8030-7a83014af82f" />

Billers and coders live inside dense policy PDFs (NCCI Policy Manual, Claims Processing Manual, modifier guidance) searching for the one paragraph that settles a question. SourceFetch turns that corpus into a question-answering service: it retrieves the relevant passages from a vector store and has a model answer strictly from them, citing each passage inline. It's the companion to [ScrubCheck](https://github.com/rajeshnandipaty/scrubcheck). ScrubCheck flags *that* a claim will deny while SourceFetch answers *why* from the manual.

## What it does

- **Retrieves** the most relevant passages for a question from a ChromaDB vector store (cosine similarity over embeddings).
- **Answers** the question using a model that is constrained to the retrieved passages by citing each claim with a `[n]` marker, and states when the passages don't contain the answer rather than inventing one.
- **Shows its work** with the retrieved passages and their similarity scores; they are returned alongside the answer and the citation markers link to them.
- **Runs with no key and no model download** by default. An offline embedder plus an extractive answer mode comprises the whole pipeline out of the box.

```
GET  /api/status   what's loaded, which embedder, which answer mode
POST /api/search   retrieval only (passages + similarity scores)
POST /api/ask      retrieve + grounded, cited answer
```

## The architecture

The same discipline runs through this whole portfolio: **the model is only allowed to speak from retrieved facts.** That principle shapes every layer here.

- **Retrieval is the substance while generation is the phrasing.** The vector search decides *what* the answer can be built from. The model only decides how to say it, and is restricted (in the system prompt) from adding any policy, code, or fact that isn't in the retrieved passages. If the passages don't answer the question, the correct output should be "the passages don't cover this" instead of a guess.
- **Citations are first-class.** Every claim carries a `[n]` that maps to a specific retrieved passage. This is the honest version of RAG: the user can check the model against its sources, and the UI makes that one click.
- **It degrades instead of breaking.** No API key leads to returns of top passages verbatim (extractive mode). No `sentence-transformers` install leads to using an offline hashing embedder. The service should not depend too heavily on a paid call or a model download to be useful.

```
question ─▶ embed ─▶ Chroma top-k ─▶ assemble cited context ─▶ Claude (grounded) ─▶ answer + citations
                                                   └────────────── or ──────────────▶ top passages (extractive)
```

### Embeddings: offline by default, semantic when you want it

`EMBEDDINGS_BACKEND` selects how text becomes vectors:

- `hashing` (default): a `HashingVectorizer` over word 1–2 grams. Offline, deterministic, no download. Essentially lexical, so it's "good enough to show the pipeline and rank correctly," and not semantically strong. It exists so the app runs anywhere instantly.
- `sentence-transformers`: `all-MiniLM-L6-v2` from the Hugging Face ecosystem for real semantic retrieval that handles paraphrased questions. Install the optional extra and re-ingest.

Changing the backend changes the vector space, so re-run ingestion after switching (the ingest script rebuilds the collection).

## Does it work?

`scripts/evaluate.py` scores the pipeline against a small gold set (`eval/qa.jsonl`):

- **Retrieval (always, offline):** `hit@k` and **MRR** of the expected source document.
- **Generation (with a key):** whether the answer contains the expected fact, plus an **LLM-as-judge** check that the answer is actually supported by the retrieved passages and asserts nothing beyond them.

On the shipped sample corpus with the offline lexical backend:

```
hit@3: 14/14 = 1.00
MRR:     0.952
```

The set deliberately includes paraphrased questions with little vocabulary overlap, which would've dragged the lexical backend down). The metric should have a real range, and not simply sit at 1.0.

## Setup

### Requirements

- Python 3.10+
- An Anthropic API key is **optional but strongly preferred** (enables synthesized answers and the grounding eval)

### Run it (offline, no key)

```bash
git clone https://github.com/rajeshnandipaty/sourcefetch.git
cd sourcefetch
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/ingest.py            # chunk + embed the sample corpus into Chroma
uvicorn app.main:app --reload       # serve at http://localhost:8000
```

Open `http://localhost:8000` and ask a question.

### Turn on grounded answers and semantic search

```bash
cp .env.example .env                # add ANTHROPIC_API_KEY
pip install -r requirements-semantic.txt          # Hugging Face embeddings (optional)
# in .env: EMBEDDINGS_BACKEND=sentence-transformers
python scripts/ingest.py            # re-ingest under the new embedder
uvicorn app.main:app --reload
```

### Measure it

```bash
python scripts/evaluate.py --k 5
```

## Using real policy documents

The sample corpus in `corpus/` is **illustrative**. Short documents are modeled on public CMS topics (PTP edits, MUEs, modifiers 25 / 59 / X, the global package, add-on codes). Clearly marked as *not authoritative*. To answer from the real manuals, drop the actual CMS policy PDFs into `corpus/` and re-ingest:

```bash
cp ~/Downloads/ncci_policy_manual_chapters/*.pdf corpus/
python scripts/ingest.py
```

Ingestion reads `.md`, `.txt`, and `.pdf` (via `pypdf`), so the real PDFs work without conversion. The CMS NCCI Policy Manual and related guidance are public and free.

## What I learned

- **The retriever vs. the model:** It's tempting to lean on the model to "know" billing policy. But a model that half-remembers a manual can be less efficient in a domain where the exact wording of a rule decides whether a claim pays. Putting a vector search in front, and forbidding the model from going beyond what it retrieves, should make answers trustworthy. "I don't see that in the manual" is a notable feature.
- **Citations change the trust model.** Once every claim points at a passage, the user stops having to take the model's word for anything. That one design decision did more for credibility than any prompt tuning.
- **Embeddings are a swappable layer, and saying so matters.** The offline lexical backend lets anyone run the thing in ten seconds; the Hugging Face semantic backend is the real-quality path. Building the abstraction so they're interchangeable, as well as being upfront that the default is lexical, probably beats pretending a demo is production.
- **An eval harness is excellent insurance.** A dozen gold questions and two metrics turned vague confidence into a defendable number, and can surface exactly which paraphrases the lexical backend mishandles.

## Hosting

The retrieval layer is cheap and safe to expose, so SourceFetch can run as a public demo on Google Cloud Run in retrieval-only mode — see [DEPLOY.md](DEPLOY.md). The generated-answer layer makes paid API calls, so it stays key-gated (enable it only where access is controlled). The source is here, and a short demo video is on [my portfolio](https://rajeshnandipaty.com/projects).

## Not billing advice

SourceFetch is an educational tool over sample and public reference text. Answers are limited to whatever has been ingested. **It is not a substitute for a certified coder or official CMS guidance, and it does not guarantee payment.**

## Project layout

```
sourcefetch/
├── app/
│   ├── main.py          FastAPI app: /api/status, /api/search, /api/ask, static UI
│   ├── rag.py           retrieve → assemble cited context → grounded answer (+ extractive fallback)
│   ├── embeddings.py    embedder abstraction: hashing (offline) | sentence-transformers (HF)
│   ├── store.py         ChromaDB wrapper (self-supplied embeddings; no model download)
│   ├── chunking.py      paragraph-aware chunking with overlap
│   └── static/
│       └── index.html   single-page UI; citations link to retrieved passages
├── scripts/
│   ├── ingest.py        corpus → chunks → embeddings → Chroma (rebuilds cleanly)
│   └── evaluate.py      retrieval (hit@k, MRR) + optional grounding eval
├── corpus/              sample policy documents (illustrative; replace with real PDFs)
├── eval/
│   └── qa.jsonl         gold questions for evaluation
├── requirements.txt              core (offline-capable)
├── requirements-semantic.txt     optional Hugging Face embeddings
├── Dockerfile                    builds the index in; runs on Cloud Run
├── DEPLOY.md                     local Docker + Cloud Run deployment guide
├── .dockerignore
├── .env.example
└── .gitignore
```
