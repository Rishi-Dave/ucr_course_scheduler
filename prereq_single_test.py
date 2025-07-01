# ─── prereq_single_test.py  (compatible with new extractor) ───
import argparse, re, requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any

HEADERS = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

def banner_session(term: str) -> requests.Session:
    s = requests.Session()
    s.post("https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/term/search?mode=search",
           data={"term": term}, headers=HEADERS, timeout=30)
    return s

def banner_sections(s: requests.Session, term: str) -> List[Dict[str, Any]]:
    """Pull ALL sections for the term (loop every 500 rows)."""
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

# ---------- build name→code map ----------
def build_desc2code(sections):
    m = {}
    for s in sections:
        code = s["subject"].strip().upper()
        desc = s["subjectDescription"].strip()
        if desc:
            m[re.sub(r"\s+", "", desc.upper())] = code  # 'COMPUTERSCIENCE' → 'CS'
    return m

# ---------- new extractor (same as in scrapper) ----------
def clean_prereqs(sess, term, crn, desc2code, course_code):
    url = ("https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/"
           f"searchResults/getSectionPrerequisites?term={term}&courseReferenceNumber={crn}")
    html = sess.get(url, timeout=15).text
    if "No prerequisite information available" in html:
        return "(no prerequisites)"

    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).upper()
    
    parts = re.split(r"\s+(AND|OR)\s+", text)
    out   = []
    clause_re = re.compile(r"([A-Z][A-Z &]{1,})\s*(\d{1,4}[A-Z]?)")

    for part in parts:
        part = part.strip()
        if part in ("AND", "OR"):
            if out and out[-1] not in ("AND", "OR"):
                out.append(part)
            continue
        m = clause_re.search(part)
        if not m: continue
        subj_raw, num = m.groups()
        key = re.sub(r"\s+", "", subj_raw)
        code = desc2code.get(key, key[:4])
        candidate = f"{code}{num.upper()}"
        if candidate != course_code:
            out.append(candidate)

    # drop trailing AND/OR
    if out and out[-1] in ("AND", "OR"):
        out.pop()
    return " ".join(out) if out else "(self-reference only)"

# ---------- CLI ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", required=True, help="Banner term (e.g. 202440)")
    ap.add_argument("--crn",  required=True, help="Course Reference Number")
    args = ap.parse_args()

    sess      = banner_session(args.term)
    sections  = banner_sections(sess, args.term)
    desc2code = build_desc2code(sections)

    # find the course's own code for self-reference skip
    self_code = None
    for s in sections:
        if s["courseReferenceNumber"] == args.crn:
            self_code = f"{s['subject'].strip().upper()}{s['courseNumber']}"
            break
    if not self_code:
        print("CRN not found in term data.")
        exit()

    print(clean_prereqs(sess, args.term, args.crn, desc2code, self_code))
