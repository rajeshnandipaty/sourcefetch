"""RAG: retrieve relevant passages, then answer strictly from them.

The same discipline as the rest of this portfolio: the model is only allowed to
speak from retrieved text, must cite each claim with a [n] marker, and must say
so when the answer isn't in the context rather than reaching for outside
knowledge. If no API key is configured, we skip generation entirely and return
the top passages verbatim (extractive mode), so retrieval is still demonstrable
and the app never hard-depends on a paid call.
"""

from __future__ import annotations
import os
from typing import List, Dict, Any

from .store import VectorStore
from .embeddings import get_embedder

GEN_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = """You answer questions about medical billing and coding policy using ONLY the \
numbered context passages provided. Rules:

- Use only the passages. Do not add facts, codes, or policy from outside knowledge.
- Cite every claim with the passage number(s) it comes from, like [1] or [2][3].
- If the passages do not contain the answer, say exactly what is missing instead of guessing.
- Be concise and direct. No preamble, no restating the question.
- This is educational guidance over reference text, not billing advice or a guarantee of payment."""


class Rag:
    def __init__(self):
        self.embedder = get_embedder()
        self.store = VectorStore()

    def retrieve(self, question: str, k: int = 5) -> List[Dict[str, Any]]:
        qvec = self.embedder.embed_query(question)
        return self.store.query(qvec, k=k)

    def answer(self, question: str, k: int = 5) -> Dict[str, Any]:
        hits = self.retrieve(question, k=k)
        citations = [
            {"n": i + 1, "source": h["source"], "index": h["index"], "score": h["score"]}
            for i, h in enumerate(hits)
        ]

        if not hits:
            return {
                "mode": "empty",
                "answer": "Nothing has been ingested yet. Run scripts/ingest.py first.",
                "citations": [],
                "contexts": [],
            }

        if os.getenv("ANTHROPIC_API_KEY"):
            generated = self._generate(question, hits)
            if generated is not None:
                return {
                    "mode": "generated",
                    "answer": generated,
                    "citations": citations,
                    "contexts": hits,
                }

        # Extractive fallback: hand back the strongest passages.
        top = hits[: min(2, len(hits))]
        extractive = "\n\n".join(f"[{i + 1}] ({h['source']}) {h['text']}" for i, h in enumerate(top))
        return {
            "mode": "extractive",
            "answer": extractive,
            "citations": citations[: len(top)],
            "contexts": hits,
        }

    def _generate(self, question: str, hits: List[Dict[str, Any]]) -> str | None:
        try:
            import anthropic

            client = anthropic.Anthropic()
            context = "\n\n".join(
                f"[{i + 1}] (source: {h['source']})\n{h['text']}" for i, h in enumerate(hits)
            )
            user = f"Context passages:\n\n{context}\n\nQuestion: {question}"
            resp = client.messages.create(
                model=GEN_MODEL,
                max_tokens=700,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception as e:  # never let generation break the endpoint
            print(f"generation failed, using extractive fallback: {e}")
            return None
