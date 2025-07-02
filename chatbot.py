"""
chatbot.py
──────────
Simple console chatbot that:
1.  Asks the student for completed courses & preferences.
2.  Calls partner's courseRanking.rank_courses() to get wish scores.
3.  Feeds wish scores into scheduler.build_schedule().
4.  Prints a conflict-free schedule.
"""

import csv, json, pathlib, sys
from prompt_toolkit import prompt

from scheduler import build_schedule
from courseRanking import rank_courses  # <- you implemented this refactor!

# ── config ────────────────────────────────────────────────────────────
TERM          = "202440"
CSV_PATH      = pathlib.Path(f"ucr_courses_{TERM}.csv")
MAJOR_PLAN    = pathlib.Path("majors/computer_science.json")

if not CSV_PATH.exists():
    sys.exit(f"❌ Banner CSV not found: {CSV_PATH}")
if not MAJOR_PLAN.exists():
    sys.exit(f"❌ Major plan not found: {MAJOR_PLAN}")

sections = list(csv.DictReader(open(CSV_PATH)))
major_plan = json.load(open(MAJOR_PLAN))["plan_by_quarter"]
major_flat = [c for quarter in major_plan for c in quarter]

print("🤖  Welcome to UCR schedule bot!")
completed = {
    c.strip().upper()
    for c in prompt("Enter completed courses (comma-sep): ").split(",")
    if c.strip()
}

desired_load = int(prompt("How many courses do you want this quarter? "))

preference_query = prompt(
    "Tell me anything about preferred days/times/topics (or leave blank): "
)

# candidate list = still-needed major courses + any elective codes you know
courses_to_take = [c for c in major_flat if c not in completed]

# ── partner's ranking algorithm ──────────────────────────────────────
ranked_docs = rank_courses(
    courses_taken=list(completed),
    preference_query=preference_query,
    courses_to_take=courses_to_take,
    top_k=100,
)

wish_scores = {d["course_id"]: d["score"] for d in ranked_docs}

if not wish_scores:
    sys.exit("❌ No ranked courses returned. Check ranking logic / DB.")

schedule = build_schedule(
    sections=sections,
    wish_scores=wish_scores,
    completed=completed,
    max_load=desired_load,
)

print("\n🗓️  Final schedule")
if not schedule:
    sys.exit("Could not build a valid schedule with given preferences.")

for s in schedule:
    mt = s["meetingTimes"][0]
    days = mt.get("meetingDays", "")
    print(f"{s['subjectCourse']:7} {s['courseTitle'][:40]:40} "
          f"{days:5} {mt.get('beginTime','----')}-{mt.get('endTime','----')}")
