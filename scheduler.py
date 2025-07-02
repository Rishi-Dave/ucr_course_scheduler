# ─── scheduler.py ──────────────────────────────────────────────
import re
from typing import List, Dict, Any, Set
import csv, json

# ---------- helpers ----------
def parse_time(t: str):
    if not t or len(t) < 4:
        return None
    return int(t[:2]) * 60 + int(t[2:])  # minutes past midnight

def conflict(a, b):
    """Return True if two meeting dicts overlap in day/time."""
    if not a["days"] or not b["days"]:
        return False
    if not set(a["days"]) & set(b["days"]):
        return False
    return a["start"] < b["end"] and b["start"] < a["end"]

def prereq_met(prereq_str: str, completed: Set[str]):
    """
    Very simple evaluator: treat 'AND' / 'OR' literally.
    Example: 'CS010C AND CS111 OR MATH009C' passes if
    (CS010C and CS111)  OR  MATH009C is in completed.
    """
    if not prereq_str:
        return True
    tokens = prereq_str.split()
    stack = []
    cur_and = True
    for tok in tokens:
        if tok == "AND":
            cur_and = True
        elif tok == "OR":
            cur_and = False
        else:
            has = tok in completed
            if cur_and:
                stack.append(has and (stack.pop() if stack else True))
            else:
                stack.append(has or (stack.pop() if stack else False))
    return stack and stack[-1]

# ---------- main algorithm ----------
def build_schedule(
    sections: List[Dict[str, Any]],
    wish_scores: Dict[str, float],
    completed: Set[str],
    max_load: int = 4,
    min_units: int = 0,
    max_units: int = 21,
) -> List[Dict[str, Any]]:
    """
    Return list of chosen section dicts (size ≤ max_load) that maximizes total
    wish_score while respecting time/prereq/unit constraints.
    """

    # Pre-process sections once
    cleaned = []
    for s in sections:
        code = s["subjectCourse"]  # scrapper.py writes this "CS141"
        if code not in wish_scores:
            continue                       # not on wish-list
        if code in completed:
            continue                       # already taken

        mt = (s.get("meetingTimes") or [{}])[0]
        sec = {
            "code": code,
            "title": s["courseTitle"],
            "crn": s["courseReferenceNumber"],
            "days": mt.get("meetingDays", ""),
            "start": parse_time(mt.get("beginTime", "")),
            "end": parse_time(mt.get("endTime", "")),
            "units": int(s.get("creditHourLow", 4)),
            "score": wish_scores[code],
            "prereq": s["prerequisites"],
            "raw": s,                       # keep full row in case you need it
        }
        cleaned.append(sec)

    # Sort by score descending
    cleaned.sort(key=lambda x: x["score"], reverse=True)

    best_sched: List[Dict[str, Any]] = []
    best_score = -1

    def dfs(idx, sched, total_units, total_score):
        nonlocal best_sched, best_score
        # update best if valid
        if len(sched) <= max_load and min_units <= total_units <= max_units and total_score > best_score:
            best_sched = sched[:]
            best_score = total_score
        if len(sched) == max_load or idx == len(cleaned):
            return

        for i in range(idx, len(cleaned)):
            cand = cleaned[i]

            # time clash?
            if any(conflict(cand, s) for s in sched):
                continue
            # prereq unmet?
            if not prereq_met(cand["prereq"], completed):
                continue
            # unit overload?
            if total_units + cand["units"] > max_units:
                continue

            sched.append(cand)
            dfs(i + 1, sched, total_units + cand["units"], total_score + cand["score"])
            sched.pop()

    dfs(0, [], 0, 0)
    return [s["raw"] for s in best_sched]

    
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sections = list(csv.DictReader(open("ucr_courses_202440.csv")))
    major    = json.load(open("majors/computer_science.json"))["plan_by_quarter"]
    completed = set(input("Completed courses: ").upper().split(","))
    wish_scores = your_partner_scoring_fn(major, completed)

    schedule = build_schedule(sections, wish_scores, completed, 4)
    for s in schedule:
        mt = s["meetingTimes"][0]
        print(f"{s['subjectCourse']}  {mt['meetingDays']} {mt['beginTime']}-{mt['endTime']}")
