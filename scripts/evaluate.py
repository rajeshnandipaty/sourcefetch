#!/usr/bin/env python3
"""Evaluate the RAG pipeline.

Most RAG demos ship with no measurement at all. This one reports how well it
actually does on a small gold set (eval/qa.jsonl):

  Retrieval (always, offline):
    hit@k   fraction of questions whose expected source doc appears in the top-k
    MRR     mean reciprocal rank of the expected source doc

  Grounding (only if ANTHROPIC_API_KEY is set):
    contains the answer's expected substring, AND
    an LLM-as-judge check that the answer is supported by the retrieved passages
    and does not assert facts beyond them.

    python scripts/evaluate.py
    python scripts/evaluate.py --k 5
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.rag import Rag, GEN_MODEL  # noqa: E402


def load_qa(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def judge_grounded(question: str, answer: str, contexts) -> bool | None:
    """Ask the model whether the answer is supported by the retrieved passages."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        ctx = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(contexts))
        prompt = (
            "You are checking whether an answer is fully supported by the given passages.\n\n"
            f"Passages:\n{ctx}\n\nQuestion: {question}\nAnswer: {answer}\n\n"
            "Reply with exactly one word: GROUNDED if every claim in the answer is "
            "supported by the passages, or UNSUPPORTED if any claim is not."
        )
        resp = client.messages.create(
            model=GEN_MODEL,
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}],
        )
        verdict = "".join(b.text for b in resp.content if b.type == "text").strip().upper()
        return verdict.startswith("GROUNDED")
    except Exception as e:
        print(f"  (judge skipped: {e})")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    qa = load_qa(ROOT / "eval" / "qa.jsonl")
    rag = Rag()
    if rag.store.count() == 0:
        print("Index is empty. Run scripts/ingest.py first.")
        sys.exit(1)

    use_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
    print(f"Evaluating {len(qa)} questions  |  k={args.k}  |  embedder={rag.embedder.name}  |  "
          f"grounding judge={'on (' + GEN_MODEL + ')' if use_llm else 'off'}\n")

    hits = 0
    rr_sum = 0.0
    substr_ok = 0
    grounded_ok = 0
    grounded_n = 0

    for row in qa:
        q = row["question"]
        expected = row["expected_source"]
        retrieved = rag.retrieve(q, k=args.k)
        ranks = [i + 1 for i, h in enumerate(retrieved) if h["source"] == expected]
        rank = ranks[0] if ranks else 0
        if rank:
            hits += 1
            rr_sum += 1.0 / rank
        mark = f"rank {rank}" if rank else "MISS"

        line = f"  [{mark:>6}] {q[:62]}"
        if use_llm:
            res = rag.answer(q, k=args.k)
            ans = res["answer"]
            sub = row.get("expect_substring", "").lower()
            if sub and sub in ans.lower():
                substr_ok += 1
            g = judge_grounded(q, ans, res["contexts"])
            if g is not None:
                grounded_n += 1
                grounded_ok += 1 if g else 0
                line += f"  | grounded={'Y' if g else 'N'}"
        print(line)

    n = len(qa)
    print("\n--- Retrieval ---")
    print(f"  hit@{args.k}: {hits}/{n} = {hits/n:.2f}")
    print(f"  MRR:     {rr_sum/n:.3f}")
    if use_llm:
        print("\n--- Generation ---")
        print(f"  substring match: {substr_ok}/{n} = {substr_ok/n:.2f}")
        if grounded_n:
            print(f"  grounded (LLM judge): {grounded_ok}/{grounded_n} = {grounded_ok/grounded_n:.2f}")
    else:
        print("\n(Set ANTHROPIC_API_KEY to also score answer substring match and grounding.)")


if __name__ == "__main__":
    main()
