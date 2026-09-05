"""
Score one or two evaluation runs and write a markdown report.

Scoring rules (chosen by each item's `scoring` field):
  number      any number in the answer within tolerance of gold (default 0.011 abs)
  text        normalized gold string appears in the answer (dates accept several formats)
  set         every gold name appears in the answer; also reports mean recall
  policy      every group of alternatives has at least one match (case-insensitive)
  refusal     answer contains an out-of-scope / cannot-help cue
  unavailable answer says the item is not carried AND quotes no price

A question that ended in a clarification interrupt or a transport error counts as
incorrect and is reported separately.

Usage:
  python eval/score_eval.py baseline
  python eval/score_eval.py baseline with_validation      # side-by-side + flips
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SET_PATH = ROOT / "eval" / "data" / "eval_set.jsonl"
RUNS_DIR = ROOT / "eval" / "runs"
REPORTS_DIR = ROOT / "eval" / "reports"

REFUSAL_CUES = [
    "outside the scope", "out of scope", "outside of our", "beyond the scope", "sorry", "apolog",
    "unable to help", "can't help", "cannot help", "can't assist", "cannot assist", "not able to",
    "only assist", "only help", "don't have information", "do not have information", "unrelated",
    "not related", "customer service", "professional resource", "not something i can",
]
UNAVAILABLE_CUES = [
    "don't carry", "do not carry", "not carry", "don't have", "do not have", "doesn't have", "does not have",
    "not available", "isn't available", "is not available", "don't sell", "do not sell", "not sell",
    "no such", "couldn't find", "could not find", "not find", "unfortunately", "not in our", "not offer",
    "don't offer", "do not offer", "not currently", "not part of", "not stock", "don't stock", "do not stock",
    "no product", "not a product", "no matching", "not listed", "not in stock", "sorry",
]
PRICE_PATTERN = re.compile(r"(¥|\$|usd|cny|rmb)\s?\d|\d+\.\d{2}\b|price (is|of .* is)\s*\d", re.I)


def norm(s: str) -> str:
    s = s.lower().replace("–", "-").replace("—", "-")
    s = re.sub(r"[^\w\s\-/\.:]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def numbers_in(s: str) -> list[float]:
    out = []
    for m in re.finditer(r"[-+]?\d[\d,]*(?:\.\d+)?", s):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def date_variants(iso: str) -> list[str]:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return [iso]
    return [
        iso, d.strftime("%Y/%m/%d"), d.strftime("%B %d, %Y"), d.strftime("%B %-d, %Y"),
        d.strftime("%d %B %Y"), d.strftime("%-d %B %Y"), d.strftime("%b %d, %Y"), d.strftime("%b %-d, %Y"),
        d.strftime("%m/%d/%Y"), d.strftime("%d/%m/%Y"),
    ]


def score(item: dict, run: dict) -> dict:
    ans = run.get("answer") or ""
    res = {"id": item["id"], "correct": False, "detail": "", "clarify": bool(run.get("clarify")), "error": run.get("error")}
    if run.get("error"):
        res["detail"] = f"error: {run['error']}"
        return res
    if run.get("clarify") and not ans:
        res["detail"] = "asked for clarification"
        return res
    kind, gold = item["scoring"], item["gold"]
    a = norm(ans)

    if kind == "number":
        tol = item.get("tolerance", 0.011)
        nums = numbers_in(ans)
        hit = any(abs(n - float(gold)) <= tol for n in nums)
        res["correct"] = hit
        res["detail"] = f"gold={gold} found={nums[:8]}"
    elif kind == "text":
        cands = date_variants(gold) if item.get("subtype") == "order_date" else [gold]
        res["correct"] = any(norm(c) in a for c in cands)
        res["detail"] = f"gold={gold!r}"
    elif kind == "set":
        hits = [g for g in gold if norm(g) in a]
        recall = len(hits) / max(1, len(gold))
        res["recall"] = round(recall, 3)
        res["correct"] = recall == 1.0
        res["detail"] = f"recall={len(hits)}/{len(gold)} missing={[g for g in gold if g not in hits]}"
    elif kind == "policy":
        missed = [grp for grp in gold if not any(norm(alt) in a for alt in grp)]
        res["correct"] = not missed
        res["detail"] = f"missed_groups={missed}" if missed else "all groups matched"
    elif kind == "refusal":
        cues = [c for c in REFUSAL_CUES if c in a]
        res["correct"] = bool(cues)
        res["detail"] = f"cues={cues[:3]}" if cues else "no refusal cue; answered the question"
    elif kind == "unavailable":
        cues = [c for c in UNAVAILABLE_CUES if c in a]
        priced = bool(PRICE_PATTERN.search(ans))
        res["correct"] = bool(cues) and not priced
        res["detail"] = f"cues={cues[:3]} quoted_price={priced}"
    else:
        res["detail"] = f"unknown scoring {kind}"
    return res


def load_run(tag: str) -> dict[str, dict]:
    p = RUNS_DIR / f"{tag}.jsonl"
    return {json.loads(l)["id"]: json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}


def summarize(items, scored):
    by = defaultdict(lambda: [0, 0])
    for it in items:
        s = scored[it["id"]]
        by[it["category"]][1] += 1
        by[it["category"]][0] += int(s["correct"])
    total = [sum(v[0] for v in by.values()), sum(v[1] for v in by.values())]
    return by, total


def pct(c, n):
    return f"{100 * c / n:.0f}% ({c}/{n})" if n else "n/a"


def report(tags: list[str]):
    items = [json.loads(l) for l in SET_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    runs = {t: load_run(t) for t in tags}
    items = [it for it in items if all(it["id"] in r for r in runs.values())]
    scored = {t: {it["id"]: score(it, runs[t][it["id"]]) for it in items} for t in tags}

    lines = [f"# SmartSupport eval report: {' vs '.join(tags)}", "", f"Questions scored: {len(items)}", ""]

    # per-category table
    lines.append("## Accuracy by category")
    lines.append("")
    lines.append("| category | " + " | ".join(tags) + " |")
    lines.append("|---|" + "---|" * len(tags))
    sums = {t: summarize(items, scored[t]) for t in tags}
    cats = sorted({it["category"] for it in items})
    for c in cats:
        lines.append(f"| {c} | " + " | ".join(pct(*sums[t][0][c]) for t in tags) + " |")
    lines.append("| **overall** | " + " | ".join(f"**{pct(*sums[t][1])}**" for t in tags) + " |")
    lines.append("")

    # per-subtype table
    lines.append("## Accuracy by subtype")
    lines.append("")
    lines.append("| category | subtype | n | " + " | ".join(tags) + " |")
    lines.append("|---|---|---|" + "---|" * len(tags))
    subs = defaultdict(list)
    for it in items:
        subs[(it["category"], it["subtype"])].append(it["id"])
    for (c, s), ids in sorted(subs.items()):
        cells = [f"{sum(scored[t][i]['correct'] for i in ids)}/{len(ids)}" for t in tags]
        lines.append(f"| {c} | {s} | {len(ids)} | " + " | ".join(cells) + " |")
    lines.append("")

    # operational stats
    lines.append("## Run stats")
    lines.append("")
    lines.append("| run | clarify interrupts | transport errors | median latency | mean set recall |")
    lines.append("|---|---|---|---|---|")
    for t in tags:
        rs = [runs[t][it["id"]] for it in items]
        lat = sorted(r.get("latency_s", 0) for r in rs)
        med = lat[len(lat) // 2] if lat else 0
        recalls = [scored[t][it["id"]].get("recall") for it in items if scored[t][it["id"]].get("recall") is not None]
        mr = f"{sum(recalls) / len(recalls):.2f}" if recalls else "n/a"
        lines.append(f"| {t} | {sum(1 for r in rs if r.get('clarify'))} | {sum(1 for r in rs if r.get('error'))} | {med}s | {mr} |")
    lines.append("")

    # cypher trace stats when present (kg mode)
    for t in tags:
        rs = [runs[t][it["id"]] for it in items if runs[t][it["id"]].get("cyphers") is not None]
        if not rs:
            continue
        cy = [c for r in rs for c in r["cyphers"]]
        if not cy:
            continue
        with_err = sum(1 for c in cy if c["errors"])
        empty = sum(1 for c in cy if c["n_records"] == 0)
        lines.append(f"## Cypher trace: {t}")
        lines.append("")
        lines.append(f"- statements generated: {len(cy)}")
        lines.append(f"- statements with validation/execution errors: {with_err} ({100 * with_err / len(cy):.0f}%)")
        lines.append(f"- statements returning zero rows: {empty} ({100 * empty / len(cy):.0f}%)")
        lines.append("")

    # flips when comparing
    if len(tags) == 2:
        a, b = tags
        fixed = [it for it in items if not scored[a][it["id"]]["correct"] and scored[b][it["id"]]["correct"]]
        broke = [it for it in items if scored[a][it["id"]]["correct"] and not scored[b][it["id"]]["correct"]]
        lines.append(f"## Flips: {a} -> {b}")
        lines.append("")
        lines.append(f"Fixed ({len(fixed)}):")
        for it in fixed:
            lines.append(f"- {it['id']} [{it['subtype']}] {it['question']}")
        lines.append("")
        lines.append(f"Broke ({len(broke)}):")
        for it in broke:
            lines.append(f"- {it['id']} [{it['subtype']}] {it['question']}")
        lines.append("")

    # failures of the last run
    t = tags[-1]
    lines.append(f"## Failures: {t}")
    lines.append("")
    for it in items:
        s = scored[t][it["id"]]
        if s["correct"]:
            continue
        ans = (runs[t][it["id"]].get("answer") or "").replace("\n", " ")
        lines.append(f"### {it['id']} · {it['category']}/{it['subtype']}")
        lines.append(f"- Q: {it['question']}")
        lines.append(f"- gold: `{json.dumps(it['gold'], ensure_ascii=False)[:200]}`")
        lines.append(f"- why: {s['detail']}")
        lines.append(f"- answer: {ans[:400]}{'…' if len(ans) > 400 else ''}")
        lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / ("_vs_".join(tags) + ".md")
    out.write_text("\n".join(lines), encoding="utf-8")
    summary = {t: {"overall": sums[t][1], "by_category": {c: sums[t][0][c] for c in cats}} for t in tags}
    (REPORTS_DIR / ("_vs_".join(tags) + ".json")).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n".join(lines[: 8 + len(cats) + 2]))
    print(f"\nfull report: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    report(sys.argv[1:])
