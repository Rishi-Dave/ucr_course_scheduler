"""
chatbot.py  –  CS-major aware
─────────────────────────────
1. Loads quarter sections from ucr_courses_data.json
2. Loads CS major plan (required, tech-elective, breadth pools)
3. Builds a schedule in two phases:
      a) core plan courses
      b) if slots remain, pulls tech electives / breadth courses
"""

import json, pathlib, sys, textwrap
from typing import List, Dict, Any, Set

from scheduler import build_schedule
from courseRanking import rank_courses   # needs rank_courses() refactor

# ── file locations ───────────────────────────────────────────────────
COURSE_JSON = pathlib.Path("ucr_courses_data.json")
PLAN_FILE   = pathlib.Path("cs_course_plan.json")

if not COURSE_JSON.exists():
    sys.exit(f"❌ Course file not found: {COURSE_JSON}")
if not PLAN_FILE.exists():
    sys.exit(f"❌ Plan file not found: {PLAN_FILE}")

sections: List[Dict[str, Any]] = json.load(open(COURSE_JSON))
plan             = json.load(open(PLAN_FILE))
plan_courses     = {c.strip().upper() for q in plan["plan_by_quarter"] for c in q}
tech_electives   = {c.strip().upper() for c in plan.get("tech_elective_pool", [])}
breadth_pool     = {c.strip().upper() for c in plan.get("engr_breadth_pool", [])}

print("🤖  Welcome to UCR Schedule Bot (CS major)")
completed: Set[str] = {
    c.strip().upper() for c in input("Enter completed courses (comma-sep): ").split(",") if c.strip()
}
desired_load = int(input("How many courses this quarter? "))
pref_query   = input("Any day/time/topic preferences (optional): ")

# ─── Phase 1: required plan courses ──────────────────────────────────
core_needed = [c for c in plan_courses if c not in completed]

ranked_core = rank_courses(
    courses_taken=list(completed),
    preference_query=pref_query,
    courses_to_take=core_needed,
    top_k=200
)
wish_scores = {d["course_id"]: d["score"] for d in ranked_core}

schedule = build_schedule(sections, wish_scores, completed, desired_load)

# ─── Phase 2: fill with electives / breadth if still short ───────────
if len(schedule) < desired_load:
    remaining_slots = desired_load - len(schedule)

    already_chosen = {s["subjectCourse"] for s in schedule}
    extra_pool = (tech_electives | breadth_pool) - completed - already_chosen

    if extra_pool:
        print(f"⚠️  Only {len(schedule)} core courses fit. "
              f"Pulling electives/breadth for {remaining_slots} more slot(s).")

        # Enhance preference query so LLM understands why extras are needed
        pref_query_extras = (pref_query + " If core courses are unavailable, "
                             "recommend technical electives or breadth courses "
                             "for the remaining slots.").strip()

        ranked_extra = rank_courses(
            courses_taken=list(completed),
            preference_query=pref_query_extras,
            courses_to_take=list(extra_pool),
            top_k=200
        )

        # Merge new scores, keep existing ones higher priority if duplicated
        for d in ranked_extra:
            wish_scores.setdefault(d["course_id"], d["score"])

        schedule = build_schedule(sections, wish_scores, completed, desired_load)

# ─── present result ──────────────────────────────────────────────────
print("\n🗓️  Final schedule")
if not schedule:
    sys.exit("Could not build a valid schedule with given constraints.")

def day_flags_to_str(sec: Dict[str, Any]) -> str:
    return "".join(
        l for l, flag in zip(
            "MTWRF",
            [sec["meeting_meetingMonday"],
             sec["meeting_meetingTuesday"],
             sec["meeting_meetingWednesday"],
             sec["meeting_meetingThursday"],
             sec["meeting_meetingFriday"]]
        ) if flag
    ) or "TBA"

for s in schedule:
    days  = day_flags_to_str(s)
    begin = s.get("meeting_meetingBeginTime", "----")
    end   = s.get("meeting_meetingEndTime", "----")
    print(f"{s['subjectCourse']:7} {s['courseTitle'][:38]:38} {days:5} {begin}-{end}")
