"""
scheduler.py
────────────
Pure–logic engine: pick a conflict-free, prerequisite-valid schedule that
maximises a “wish score” (supplied by courseRanking.rank_courses).

No I/O except loading data if you run this file directly.
"""

from __future__ import annotations
import csv, json, re
from pathlib import Path
from typing import Dict, List, Any, Set


# ──── helpers ──────────────────────────────────────────────────────────
def _parse_minutes(t: str | None) -> int | None:
    """'1330' → 810. Returns None if blank/invalid."""
    if t and len(t) >= 4 and t.isdigit():
        return int(t[:2]) * 60 + int(t[2:])
    return None


def _overlap(a: dict, b: dict) -> bool:
    """Detect meeting-time clash between two section dicts."""
    if not a["days"] or not b["days"]:
        return False
    if not set(a["days"]) & set(b["days"]):
        return False
    return a["start"] < b["end"] and b["start"] < a["end"]


# very light Boolean evaluator for strings like
#  'CS010C AND CS111 AND MATH009C OR MATH09HC'
def _prereq_met(expr: str, completed: Set[str]) -> bool:
    if not expr:
        return True

    tokens = expr.split()
    need_and = []
    cur_and_group = []

    for tok in tokens + ["OR"]:         # sentinel
        if tok == "AND":
            continue
        if tok == "OR":
            if cur_and_group:
                need_and.append(all(c in completed for c in cur_and_group))
            cur_and_group = []
        else:
            cur_and_group.append(tok)
    return any(need_and)


# ──── main algorithm ───────────────────────────────────────────────────
def build_schedule(
    sections: List[Dict[str, Any]],
    wish_scores: Dict[str, float],
    completed: Set[str],
    max_load: int = 4,
    min_units: int = 0,
    max_units: int = 21,
) -> List[Dict[str, Any]]:
    """
    Returns list of chosen *section dicts* (≤ max_load) with maximum
    total wish_score, no clashes, prereqs satisfied, units in range.
    """

    # ── pre-process ────────────────────────────────────────────────────
    clean: List[dict] = []
    for raw in sections:
        code = raw["subjectCourse"]
        if code not in wish_scores or code in completed:
            continue                     # not desired or already finished

        mt = (raw.get("meetingTimes") or [{}])[0]
        sec = {
            "raw":   raw,
            "code":  code,
            "score": wish_scores[code],
            "units": int(raw.get("creditHourLow", 4)),
            "days":  mt.get("meetingDays", ""),
            "start": _parse_minutes(mt.get("beginTime")),
            "end":   _parse_minutes(mt.get("endTime")),
            "prereq": raw["prerequisites"],
        }
        clean.append(sec)

    clean.sort(key=lambda s: s["score"], reverse=True)

    # ── DFS branch-and-bound search ───────────────────────────────────
    best_sched: list[dict] = []
    best_score = -1

    def dfs(idx: int, chosen: list[dict], units: int, score: float):
        nonlocal best_sched, best_score
        # update best
        if len(chosen) <= max_load and min_units <= units <= max_units and score > best_score:
            best_sched = chosen[:]
            best_score = score
        # prune
        if idx == len(clean) or len(chosen) == max_load:
            return

        for i in range(idx, len(clean)):
            cand = clean[i]
            if units + cand["units"] > max_units:
                continue
            if not _prereq_met(cand["prereq"], completed):
                continue
            if any(_overlap(cand, s) for s in chosen):
                continue

            chosen.append(cand)
            dfs(i + 1, chosen, units + cand["units"], score + cand["score"])
            chosen.pop()

    dfs(0, [], 0, 0)
    return [s["raw"] for s in best_sched]   # return original Banner dicts


# ──── optional CLI runner (handy for smoke tests) ─────────────────────
if __name__ == "__main__":
    import argparse, sys, textwrap

    p = argparse.ArgumentParser(
        description="Pick best schedule given wish-scores JSON."
    )
    p.add_argument("--csv",  required=True, help="Banner CSV, e.g. ucr_courses_202440.csv")
    p.add_argument("--scores", required=True, help="JSON file {course: score}")
    p.add_argument("--completed", default="", help="CSV list of courses already taken")
    p.add_argument("--load", type=int, default=4)
    args = p.parse_args()

    sections = list(csv.DictReader(open(args.csv)))
    wish_scores = json.load(open(args.scores))
    completed = {c.strip().upper() for c in args.completed.split(",") if c.strip()}

    sched = build_schedule(sections, wish_scores, completed, max_load=args.load)

    print("\nChosen schedule")
    if not sched:
        sys.exit("❌ No feasible schedule.")
    for s in sched:
        mt = s["meetingTimes"][0]
        days = mt.get("meetingDays", "")
        print(f"{s['subjectCourse']:7} {s['courseTitle'][:40]:40} "
              f"{days:5} {mt.get('beginTime','----')}-{mt.get('endTime','----')}")
