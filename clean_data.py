import pandas as pd
import json
import ast # Used for safely evaluating strings containing Python literal structures

def generate_course_json(csv_file_path):
    """
    Loads course data from a CSV, extracts specified fields,
    parses nested stringified JSON/Python literals, and
    converts the data into a list of JSON objects, with 'faculty'
    and 'meetingsFaculty' details flattened into top-level columns.

    Args:
        csv_file_path (str): The path to the input CSV file.

    Returns:
        str: A JSON string containing the extracted course data,
             or None if an error occurs.
    """
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_file_path}")
        return None
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

    selected_columns = [
        'subjectCourse', 
        'courseDisplay',
        'courseNumber',
        'subject',
        'courseTitle',
        'creditHours',
        'faculty', # Will be flattened
        'instructionalMethodDescription',
        'isSectionLinked',
        'maximumEnrollment',
        'seatsAvailable',
        'meetingsFaculty', # Will be exploded and flattened
        'term',
        'termDesc',
        'waitAvailable',
        'waitCapacity',
        'waitCount',
        'prerequisites' # Kept as is, assuming no further flattening needed here
    ]

    df_filtered = df[selected_columns].copy()

    def safe_literal_eval(val):
        try:
            if pd.isna(val) or val == '':
                return None
            return ast.literal_eval(val)
        except (ValueError, SyntaxError) as e:
            return str(val) if not pd.isna(val) else None
    

    def process_prerequisites(prereq_str):
        if pd.isna(prereq_str) or prereq_str == '':
            return [] # Return an empty list for missing prerequisites
        # Split by ' OR ' and strip any leading/trailing whitespace from each element
        return [p.strip() for p in str(prereq_str).split(' OR ')]

    # Apply safe_literal_eval to 'faculty' and 'meetingsFaculty'
    for col in ['faculty', 'meetingsFaculty']:
        df_filtered[col] = df_filtered[col].apply(safe_literal_eval)

    # Apply the custom process_prerequisites function to the 'prerequisites' column
    df_filtered['prerequisites'] = df_filtered['prerequisites'].apply(process_prerequisites)

    df_filtered['facultyDisplayName'] = df_filtered['faculty'].apply(
        lambda x: x[0].get("displayName") if isinstance(x, list) and x and isinstance(x[0], dict) else None
    )
    df_filtered['facultyEmailAddress'] = df_filtered['faculty'].apply(
        lambda x: x[0].get("emailAddress") if isinstance(x, list) and x and isinstance(x[0], dict) else None
    )
    df_filtered = df_filtered.drop(columns=['faculty'])


    def extract_meeting_details(meetings_list):
        if not meetings_list:
            return []
        processed_meetings = []
        for m in meetings_list:
            if isinstance(m, dict) and "meetingTime" in m and isinstance(m["meetingTime"], dict):
                meeting_time = m["meetingTime"]
                processed_meetings.append({
                    "meetingBeginTime": meeting_time.get("beginTime"),
                    "meetingEndTime": meeting_time.get("endTime"),
                    "meetingBuildingDescription": meeting_time.get("buildingDescription"),
                    "meetingRoom": meeting_time.get("room"),
                    "meetingMonday": meeting_time.get("monday", False),
                    "meetingTuesday": meeting_time.get("tuesday", False),
                    "meetingWednesday": meeting_time.get("wednesday", False),
                    "meetingThursday": meeting_time.get("thursday", False),
                    "meetingFriday": meeting_time.get("friday", False),
                    "meetingSaturday": meeting_time.get("saturday", False),
                    "meetingSunday": meeting_time.get("sunday", False),
                    "meetingStartDate": meeting_time.get("startDate"),
                    "meetingEndDate": meeting_time.get("endDate"),
                    "meetingTypeDescription": meeting_time.get("meetingTypeDescription")
                })
        return processed_meetings

    df_filtered['meetingsFaculty'] = df_filtered['meetingsFaculty'].apply(extract_meeting_details)
    df_filtered['creditHours'] = df_filtered['creditHours'].fillna("None")

    df_exploded = df_filtered.explode('meetingsFaculty').reset_index(drop=True)

    df_exploded_final = pd.json_normalize(df_exploded['meetingsFaculty']).add_prefix('meeting_')


    if 'meetingsFaculty' in df_exploded.columns:
        df_exploded = df_exploded.drop(columns=['meetingsFaculty'])

    df_final = pd.concat([df_exploded, df_exploded_final], axis=1)

    df_final = df_final.where(pd.notnull(df_final), None)

    course_data = df_final.to_dict(orient='records')

    json_output = json.dumps(course_data, indent=4)

    return json_output


generated_json = generate_course_json("ucr_courses_202440.csv")

with open('ucr_courses_data.json', 'w') as f:
        f.write(generated_json)
print("\nJSON data saved to ucr_courses_data.json")