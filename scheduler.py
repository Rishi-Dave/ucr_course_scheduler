"""
scheduler.py
────────────
Pure scheduling engine for UCR course data stored in ucr_courses_data.json.
• Works with docs that look like:

    {
      "subjectCourse": "CS141",
      "creditHours": 4.0,
      "meeting_meetingBeginTime": "1830",
      "meeting_meetingTypeDescription": "Lecture",
      ...
    }

• Picks a conflict-free, prerequisite-valid set of sections that maximises
  a “wish score” supplied by courseRanking.rank_courses().

NEW in this version
───────────────────
1. **Skips non-lecture sections** (so discussion / lab CRNs aren’t treated
   as separate courses).
2. **Never chooses more than one CRN for the same subjectCourse** —
   prevents duplicate lectures of the same class.
"""

from __future__ import annotations
import json, re
from typing import List, Dict, Any, Set


# ─── helpers ──────────────────────────────────────────────────────────
def _parse_minutes(t: str | None) -> int | None:
    """'1330' → 810 minutes. None if blank/invalid."""
    return int(t[:2]) * 60 + int(t[2:]) if t and t.isdigit() and len(t) >= 4 else None


def _days_str(sec: dict) -> str:
    """Convert boolean day flags → e.g. 'MWF' or 'TR'."""
    flags = [
        ("M", sec.get("meeting_meetingMonday")),
        ("T", sec.get("meeting_meetingTuesday")),
        ("W", sec.get("meeting_meetingWednesday")),
        ("R", sec.get("meeting_meetingThursday")),
        ("F", sec.get("meeting_meetingFriday")),
    ]
    return "".join(letter for letter, flag in flags if flag) or ""


def _overlap(a: dict, b: dict) -> bool:
    """Detect day & time clash between two sections."""
    if not a["days"] or not b["days"]:
        return False
    if not set(a["days"]) & set(b["days"]):
        return False
    return a["start"] < b["end"] and b["start"] < a["end"]


def _prereq_met(prereq_matrix: list[list[str]], completed: Set[str]) -> bool:
    """
    Banner prereqs are list-of-OR lists:
        [['CS010C'], ['CS111'], ['MATH009C', 'MATH09H']]
    True iff each inner list has at least ONE item in `completed`.
    """
    if not prereq_matrix:
        return True
    for or_block in prereq_matrix:
        if not any(c in completed for c in or_block if c != "nan"):
            return False
    return True


# ─── core scheduler ───────────────────────────────────────────────────
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

    clean: List[dict] = []
    for raw in sections:
        # 1️⃣  Skip non-lecture meeting types early
        if (raw.get("meeting_meetingTypeDescription") or "").lower() != "lecture":
            continue

        code = raw["subjectCourse"].strip().upper()
        if code not in wish_scores or code in completed:
            continue

        sec = {
            "raw":   raw,
            "code":  code,
            "score": wish_scores[code],
            "units": int(raw.get("creditHours", 4)),
            "days":  _days_str(raw),
            "start": _parse_minutes(raw.get("meeting_meetingBeginTime")),
            "end":   _parse_minutes(raw.get("meeting_meetingEndTime")),
            "prereq": raw.get("prerequisites", []),
        }
        clean.append(sec)

    clean.sort(key=lambda s: s["score"], reverse=True)

    best_sched: list[dict] = []
    best_score = -1

    def dfs(idx: int, chosen: list[dict], units: int, score: float):
        nonlocal best_sched, best_score
        if len(chosen) <= max_load and min_units <= units <= max_units and score > best_score:
            best_sched = chosen[:]
            best_score = score
        if idx == len(clean) or len(chosen) == max_load:
            return

        for i in range(idx, len(clean)):
            cand = clean[i]

            # 2️⃣  Skip if this course already selected (avoid duplicates)
            if any(s["code"] == cand["code"] for s in chosen):
                continue
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
    return [s["raw"] for s in best_sched]


# ─── optional CLI smoke test ──────────────────────────────────────────
if __name__ == "__main__":
    import argparse, sys
    p = argparse.ArgumentParser(description="Quick test scheduler.")
    p.add_argument("--json", required=True, help="ucr_courses_data.json")
    p.add_argument("--scores", required=True, help="JSON map {course: score}")
    p.add_argument("--completed", default="", help="CSV list of completed courses")
    p.add_argument("--load", type=int, default=4)
    args = p.parse_args()

    sections = json.load(open(args.json))
    wish_scores = json.load(open(args.scores))
    completed = {c.strip().upper() for c in args.completed.split(",") if c.strip()}

    sched = build_schedule(sections, wish_scores, completed, max_load=args.load)

    if not sched:
        sys.exit("❌ No feasible schedule.")
    print("\nChosen schedule")
    for s in sched:
        days = _days_str(s)
        print(f"{s['subjectCourse']:7} {s['courseTitle'][:40]:40} "
              f"{days or 'TBA':5} {s.get('meeting_meetingBeginTime','----')}-"
              f"{s.get('meeting_meetingEndTime','----')}")
