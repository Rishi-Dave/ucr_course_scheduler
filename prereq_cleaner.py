# ─── prereq_cleaner.py  (minimal) ───
import pandas as pd

def extract_prerequisites(prereq_string: str):
    """
    Convert 'ANTH001 OR ANTH001H OR ANTH001W' → ['ANTH001', 'ANTH001H', 'ANTH001W']
    Returns [] if the cell is empty or NaN.
    """
    if not isinstance(prereq_string, str) or not prereq_string.strip():
        return []
    return [c.strip() for c in prereq_string.upper().split(" OR ") if c.strip()]

# Load the CSV written by scrapper.py
df = pd.read_csv("ucr_courses_202440.csv")

# Add the parsed list column
df["parsed_prerequisites"] = df["prerequisites"].apply(extract_prerequisites)

# Write out a new CSV (optional)
df.to_csv("ucr_courses_with_parsed_prereqs.csv", index=False, encoding="utf-8")
print("✅ parsed_prerequisites column added and file saved")
# ──────────────────────────────────────────
