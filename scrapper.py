# ───────────────────────── scrapper.py ─────────────────────────
import csv, re, requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup

TERM         = "202440"                                 # Fall-24
CSV_FILENAME = f"ucr_courses_{TERM}.csv"
HEADERS      = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

# ---------- Banner helpers ----------
def banner_session(term: str) -> requests.Session:
    s = requests.Session()
    s.post(
        "https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/term/search?mode=search",
        data={"term": term}, headers=HEADERS, timeout=30
    )
    return s

def banner_sections(s: requests.Session, term: str) -> List[Dict[str, Any]]:
    sections, offset = [], 0
    while True:
        url = ("https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/"
               "searchResults/searchResults"
               f"?txt_term={term}&pageOffset={offset}&pageMaxSize=500"
               "&sortColumn=subjectDescription&sortDirection=asc")
        batch = s.get(url, headers=HEADERS, timeout=30).json()["data"]
        if not batch:
            break
        sections.extend(batch)
        offset += 500
    return sections

# ---------- build long-name → 4-letter map ----------
def build_desc2code(sections: List[Dict[str, Any]]) -> Dict[str, str]:
    mapping = {}
    for sec in sections:
        code = sec["subject"].strip().upper()
        desc = sec["subjectDescription"].strip()
        if desc:
            mapping[re.sub(r"\s+", "", desc.upper())] = code   # "COMPUTERSCIENCE" → "CS"
    return mapping

# ---------- prerequisite extractor ----------
CLAUSE_RE = re.compile(r"([A-Z][A-Z &]{1,})\s*(\d{1,4}[A-Z]?)")

def extract_prereq_string(sess, term, crn, desc2code, course_code):
    url = ("https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/"
           f"searchResults/getSectionPrerequisites?term={term}&courseReferenceNumber={crn}")
    try:
        html = sess.get(url, timeout=15).text
        if "No prerequisite information available" in html:
            return ""

        # ─── start of section you REPLACE ───
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).upper()
        # keep original strip: remove only "COURSE OR TEST:"
        text = re.sub(r"\bCOURSE\s+OR\s+TEST\b[:]?", "", text)

        parts  = re.split(r"\s+(AND|OR)\s+", text)      # split but keep ops
        tokens = []
        for part in parts:
            part = part.strip()
            if part in ("AND", "OR"):
                if tokens and tokens[-1] not in ("AND", "OR"):
                    tokens.append(part)
                continue

            # ← use finditer so **all** course tokens in this clause are captured
            for m in CLAUSE_RE.finditer(part):
                subj_raw, num = m.groups()
                key  = re.sub(r"\s+", "", subj_raw)
                code = desc2code.get(key, key[:4])
                cand = f"{code}{num.upper()}"

                if cand != course_code and cand not in tokens:
                    tokens.append(cand)

        if tokens and tokens[-1] in ("AND", "OR"):
            tokens.pop()
        # ─── end of replaced section ───

        return " ".join(tokens)

    except Exception as e:
        print(f"⚠️  prereq fetch error CRN {crn}: {e}")
        return ""

# ---------- CSV writer ----------
def write_csv(rows: List[Dict[str, Any]], filename: str):
    fieldnames = sorted({k for r in rows for k in r})
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"✅  {len(rows)} sections → {filename}")

# ---------- main ----------
def main():
    sess      = banner_session(TERM)
    sections  = banner_sections(sess, TERM)
    desc2code = build_desc2code(sections)

    for sec in sections:
        crn  = sec["courseReferenceNumber"]
        code = f"{sec['subject'].strip().upper()}{sec['courseNumber']}"
        sec["prerequisites"] = extract_prereq_string(sess, TERM, crn, desc2code, code)

    write_csv(sections, CSV_FILENAME)

if __name__ == "__main__":
    main()
# ───────────────────────────────────────────────────────────────
