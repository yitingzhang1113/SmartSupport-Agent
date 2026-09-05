"""
Run the evaluation set against SmartSupport and record raw answers.

Two modes:
  http  (default) POST each question to /api/langgraph/query exactly as the
        storefront and console do, parse the SSE stream, keep the final text.
        Measures the whole system: routing, guardrails, KG, policy RAG.
  kg    Invoke the knowledge-graph sub-workflow in-process and also record the
        generated Cypher, validation errors and row counts per task. Use it to
        measure Text2Cypher changes (validation loop, value recall) directly.

Each run writes eval/runs/<tag>.jsonl with one record per question:
  {id, answer, latency_s, clarify, error, conversation_id, cyphers?}

Usage:
  python eval/run_eval.py --tag baseline
  python eval/run_eval.py --tag baseline_kg --mode kg --only kg,catalog_trap
  python eval/run_eval.py --tag smoke --limit 5 --concurrency 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SET_PATH = ROOT / "eval" / "data" / "eval_set.jsonl"
RUNS_DIR = ROOT / "eval" / "runs"


def load_set(path: Path, only: set[str] | None, limit: int | None) -> list[dict]:
    items = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if only:
        items = [i for i in items if i["category"] in only]
    if limit:
        items = items[:limit]
    return items


# ---------------------------------------------------------------- http mode
async def ask_http(client, base: str, question: str, timeout: float) -> dict:
    """POST one question and fold the SSE stream into {answer, clarify, error, conversation_id}."""
    out = {"answer": "", "clarify": False, "error": None, "conversation_id": None}
    data = {"query": question, "user_id": "1"}
    try:
        async with client.stream("POST", f"{base}/api/langgraph/query", data=data, timeout=timeout) as resp:
            out["conversation_id"] = resp.headers.get("x-conversation-id")
            if resp.status_code != 200:
                out["error"] = f"HTTP {resp.status_code}"
                return out
            buf = ""
            async for chunk in resp.aiter_text():
                buf += chunk
                lines = buf.split("\n")
                buf = lines.pop() or ""
                for ln in lines:
                    if not ln.startswith("data: "):
                        continue
                    payload = ln[6:]
                    if payload == "[DONE]":
                        continue
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        out["answer"] += payload
                        continue
                    if isinstance(obj, str):
                        out["answer"] += obj
                    elif isinstance(obj, dict):
                        if obj.get("interruption"):
                            out["clarify"] = True
                        if obj.get("error"):
                            out["error"] = str(obj["error"])
                        if obj.get("conversation_id"):
                            out["conversation_id"] = obj["conversation_id"]
    except Exception as e:  # timeout, connection reset, ...
        out["error"] = f"{type(e).__name__}: {e}"
    out["answer"] = out["answer"].strip()
    return out


async def run_http(items, base, concurrency, timeout, out_path):
    import httpx

    sem = asyncio.Semaphore(concurrency)
    results = {}

    async with httpx.AsyncClient() as client:

        async def one(it):
            async with sem:
                t0 = time.perf_counter()
                r = await ask_http(client, base, it["question"], timeout)
                r["latency_s"] = round(time.perf_counter() - t0, 2)
                r["id"] = it["id"]
                results[it["id"]] = r
                flag = "CLARIFY" if r["clarify"] else ("ERROR" if r["error"] else "ok")
                print(f"[{len(results):3d}/{len(items)}] {it['id']} {flag:7s} {r['latency_s']:6.1f}s  {it['question'][:60]}", flush=True)

        await asyncio.gather(*(one(it) for it in items))

    write_results(items, results, out_path)


# ------------------------------------------------------------------ kg mode
async def run_kg(items, concurrency, timeout, out_path):
    """Call the compiled KG workflow directly and keep the Cypher trace."""
    from app.lg_agent.lg_builder import get_kg_workflow

    workflow = get_kg_workflow()
    sem = asyncio.Semaphore(concurrency)
    results = {}

    def cypher_trace(state) -> list[dict]:
        trace = []
        for c in state.get("cyphers", []) or []:
            trace.append(
                {
                    "task": (c.get("task") or [""])[-1] if isinstance(c.get("task"), list) else c.get("task"),
                    "statement": c.get("statement"),
                    "errors": c.get("errors") or [],
                    "n_records": len(c.get("records") or []),
                    "steps": c.get("steps") or [],
                }
            )
        return trace

    async def one(it):
        async with sem:
            t0 = time.perf_counter()
            r = {"id": it["id"], "answer": "", "clarify": False, "error": None, "conversation_id": None, "cyphers": [], "steps": []}
            try:
                state = await asyncio.wait_for(
                    workflow.ainvoke({"question": it["question"], "data": [], "history": []}), timeout=timeout
                )
                r["answer"] = (state.get("answer") or "").strip()
                r["cyphers"] = cypher_trace(state)
                r["steps"] = state.get("steps") or []
            except Exception as e:
                r["error"] = f"{type(e).__name__}: {e}"
            r["latency_s"] = round(time.perf_counter() - t0, 2)
            results[it["id"]] = r
            n_err = sum(1 for c in r["cyphers"] if c["errors"])
            print(f"[{len(results):3d}/{len(items)}] {it['id']} {'ERROR' if r['error'] else 'ok':5s} {r['latency_s']:6.1f}s cyphers={len(r['cyphers'])} with_errors={n_err}  {it['question'][:50]}", flush=True)

    await asyncio.gather(*(one(it) for it in items))
    write_results(items, results, out_path)


def write_results(items, results, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(results[it["id"]], ensure_ascii=False) + "\n")
    n_err = sum(1 for r in results.values() if r["error"])
    n_cl = sum(1 for r in results.values() if r["clarify"])
    lat = sorted(r["latency_s"] for r in results.values())
    p50 = lat[len(lat) // 2] if lat else 0
    print(f"\nwrote {len(results)} results to {out_path.relative_to(ROOT)}  errors={n_err} clarify={n_cl} p50_latency={p50}s")
    print(f"score with: python eval/score_eval.py {out_path.stem}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="run name; results go to eval/runs/<tag>.jsonl")
    ap.add_argument("--mode", choices=["http", "kg"], default="http")
    ap.add_argument("--base", default="http://localhost:8010")
    ap.add_argument("--set", default=str(SET_PATH))
    ap.add_argument("--only", default=None, help="comma-separated categories, e.g. kg,policy")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=180.0)
    a = ap.parse_args()

    items = load_set(Path(a.set), set(a.only.split(",")) if a.only else None, a.limit)
    out_path = RUNS_DIR / f"{a.tag}.jsonl"
    print(f"{len(items)} questions, mode={a.mode}, concurrency={a.concurrency} -> {out_path.relative_to(ROOT)}\n")
    if a.mode == "http":
        asyncio.run(run_http(items, a.base, a.concurrency, a.timeout, out_path))
    else:
        asyncio.run(run_kg(items, a.concurrency, a.timeout, out_path))


if __name__ == "__main__":
    main()
