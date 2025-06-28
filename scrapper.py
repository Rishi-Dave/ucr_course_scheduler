import requests
from requests import request
from requests.cookies import RequestsCookieJar
import csv
import os
from bs4 import BeautifulSoup
from prereq_cleaner import cleanpreReqs
JSESSIONID = requests.get("https://registrationssb.ucr.edu").cookies["JSESSIONID"]
term = "202440"

def fetch_prerequisites(session: requests.Session, term: str, course_reference_number: str) -> str:
    try:
        url = f"https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/searchResults/getSectionPrerequisites?term={term}&courseReferenceNumber={course_reference_number}"
        response = session.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if no prerequisites
        if "No prerequisite information available" in response.text:
            return ""
        
        # Extract prerequisite text from the structured HTML
        prereq_section = soup.find('section', {'aria-labelledby': 'preReqs'})
        if not prereq_section:
            return ""
        
        # Get all <pre> tags which contain the prerequisite text
        pre_tags = prereq_section.find_all('pre')
        if not pre_tags:
            return ""
        
        # Combine all prerequisite text
        prerequisite_text = ''.join(tag.get_text().strip() for tag in pre_tags)
        return prerequisite_text.strip() if prerequisite_text else ""
        
    except Exception as e:
        print(f"Error fetching prerequisites for CRN {course_reference_number}: {e}")
        return ""


def fetch_course_data():
    session = requests.Session()
    session.get("https://registrationssb.ucr.edu")
    
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

    session.post(
        "https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/term/search?mode=search",
        data={"term": term},
        headers=headers,
    )

    url = f"https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/searchResults/searchResults?txt_term={term}&pageOffset=0&pageMaxSize=1&sortColumn=subjectDescription&sortDirection=asc"
    response = session.get(url, headers=headers)
    response.raise_for_status()


    totalCount = response.json()["totalCount"]
    print(f"Total courses available: {totalCount}")


    pageMaxSize = 500  # max request size
    courses = []
    prereqs = []
    pageOffset = 0

    while pageOffset < totalCount:
        print(f"Fetching courses {pageOffset} to {min(pageOffset + pageMaxSize, totalCount)}...")
        url = f"https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/searchResults/searchResults?&txt_term={term}&startDatepicker=&endDatepicker=&pageOffset={pageOffset}&pageMaxSize={pageMaxSize}&sortColumn=subjectDescription&sortDirection=asc"

        response = session.get(url, headers = headers)
        response.raise_for_status()

        new_courses = response.json()["data"]

        if not new_courses:
            print("No more courses available.")
            break

        courses.extend(new_courses)

        pageOffset += pageMaxSize #getting next 500 sections

        if len(new_courses) < pageMaxSize:
            break
    
    print(f"Successfully fetched {len(courses)} courses")

    print("Fetching prerequisites for all courses...")
    for i, course in enumerate(courses):
        if (i + 1) % 100 == 0:
            print(f"Fetched prerequisites for {i + 1}/{len(courses)} courses...")
        
        crn = course.get("courseReferenceNumber")
        if crn:
            prerequisites = fetch_prerequisites(session, term, crn)
            course["prerequisites"] = prerequisites



    return courses
def getUniqueCourses():
    courses = fetch_course_data()
    unique_crns = set()
    uniqueCourses = []
    for course in courses:
        crn = course.get("courseReferenceNumber")
        if crn and crn not in unique_crns:
            unique_crns.add(crn)
            uniqueCourses.append(course)
    print(f"Original courses count: {len(courses)}")
    print(f"Unique courses count: {len(uniqueCourses)}")

    return uniqueCourses

def coursesCSV(courses: list):
    csv_output_filename = f"ucr_courses_{term}.csv"
    courses_output = courses
    current_directory = os.getcwd()
    print(f"\nCSV will be saved in: {current_directory}")
    if courses: # Only proceed if there's data to write
        # Get all unique keys from all dictionaries to use as CSV headers
        # This ensures all possible columns are included, even if some dictionaries miss a key
        all_keys = set()
        for course_dict in courses_output:
            all_keys.update(course_dict.keys())
        fieldnames = sorted(list(all_keys)) # Sort keys for consistent column order

        try:
            with open(csv_output_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader() # Writes the header row
                for row in courses:
                    writer.writerow(row) # Writes each course dictionary as a row

            print(f"\nSuccessfully wrote {len(courses)} courses to {csv_output_filename}")
        except Exception as e:
            print(f"Error writing CSV to file: {e}")
    else:
        print("No unique courses to write to CSV.")


if __name__ == "__main__":
    courses = getUniqueCourses()
    coursesCSV(courses)
    cleanpreReqs()