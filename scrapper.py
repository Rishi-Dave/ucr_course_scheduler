# ───────────────────────── scrapper.py ─────────────────────────
import csv, re, requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup


TERM         = "202440"                                 # Fall-24
CSV_FILENAME = f"ucr_courses_{TERM}.csv"
HEADERS      = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}


# -------- BANNER SESSION & DATA --------
def banner_session(term: str) -> requests.Session:
    sess = requests.Session()
    sess.post(
        "https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/term/search?mode=search",
        data={"term": term}, headers=HEADERS, timeout=30
    )
    return sess


def banner_sections(sess: requests.Session, term: str) -> List[Dict[str, Any]]:
    sections, offset = [], 0
    while True:
        url = (
            "https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/"
            "searchResults/searchResults"
            f"?txt_term={term}&pageOffset={offset}&pageMaxSize=500"
            "&sortColumn=subjectDescription&sortDirection=asc"
        )
        batch = sess.get(url, headers=HEADERS, timeout=30).json()["data"]
        if not batch:
            break
        sections.extend(batch)
        offset += 500
    return sections


# -------- PREREQUISITE HELPERS --------
def build_regex_and_map(sections: List[Dict[str, Any]]):
    desc2code, tokens = {}, set()
    for s in sections:
        code = s["subject"].strip().upper()                 # e.g. "ANTH"
        desc = s["subjectDescription"].strip()             # e.g. "Anthropology"
        tokens.add(code)
        if desc:
            tokens.add(desc)
            desc2code[desc.upper()] = code

    token_regex = "|".join(
        sorted([re.sub(r"\s+", r"\\s*", re.escape(t)) for t in tokens], key=len, reverse=True)
    )
    course_re = re.compile(rf"((?:{token_regex})\s*\d{{1,4}}[A-Za-z]?)", flags=re.I)
    return course_re, desc2code


def clean_prereq_html(text: str, course_re: re.Pattern, desc2code: Dict[str, str]) -> str:
    raw = course_re.findall(text)
    cleaned = []
    for token in raw:
        token = token.upper().strip()
        match = re.match(r"([A-Z& ]+?)(\d{1,4}[A-Z]?)$", token)
        if not match:
            continue
        subj_raw, num = match.groups()
        subj_raw = subj_raw.strip()
        subj_code = (
            subj_raw if len(subj_raw) <= 4 and " " not in subj_raw
            else desc2code.get(subj_raw.replace(" ", ""), subj_raw[:4])
        )
        cleaned.append(f"{subj_code}{num}")
    unique = list(dict.fromkeys(cleaned))
    return " OR ".join(unique)


def fetch_prerequisites(sess: requests.Session,
                        term: str,
                        crn: str,
                        course_re: re.Pattern,
                        desc2code: Dict[str, str]) -> str:
    url = (
        "https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/"
        f"searchResults/getSectionPrerequisites?term={term}&courseReferenceNumber={crn}"
    )
    try:
        html = sess.get(url, timeout=15).text
        if "No prerequisite information available" in html:
            return ""
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        return clean_prereq_html(text, course_re, desc2code)
    except Exception as e:
        print(f"⚠️  prereq fetch fail CRN {crn}: {e}")
        return ""


# -------- CSV --------
def write_csv(rows: List[Dict[str, Any]], filename: str):
    fieldnames = sorted({k for r in rows for k in r})
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"✅  {len(rows)} sections → {filename}")


# -------- MAIN --------
def main():
    sess      = banner_session(TERM)
    sections  = banner_sections(sess, TERM)
    course_re, desc2code = build_regex_and_map(sections)

    for s in sections:
        crn = s["courseReferenceNumber"]
        s["prerequisites"] = fetch_prerequisites(sess, TERM, crn, course_re, desc2code)

    write_csv(sections, CSV_FILENAME)


if __name__ == "__main__":
    main()
# ───────────────────────────────────────────────────────────────
