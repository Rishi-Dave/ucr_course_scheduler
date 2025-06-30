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

    # Define the columns to extract for the course planner model
    # Note: 'faculty' and 'meetingsFaculty' are kept initially for parsing,
    # but their sub-fields will be promoted.
    selected_columns = [
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

    # Filter the DataFrame to include only the selected columns
    df_filtered = df[selected_columns].copy()

    # --- Process columns that contain stringified lists/dictionaries ---

    # Helper function to safely evaluate string literals
    def safe_literal_eval(val):
        try:
            # Check for NaN or empty string before evaluation
            if pd.isna(val) or val == '':
                return None
            return ast.literal_eval(val)
        except (ValueError, SyntaxError) as e:
            # In case of parsing error, return the original string or None if it's NaN
            return str(val) if not pd.isna(val) else None

    # Apply the safe_literal_eval to the specified columns
    for col in ['faculty', 'meetingsFaculty', 'prerequisites']:
        df_filtered[col] = df_filtered[col].apply(safe_literal_eval)

    # --- Flatten 'faculty' details into new top-level columns ---
    # We will take the display name and email of the first faculty member if available.
    df_filtered['facultyDisplayName'] = df_filtered['faculty'].apply(
        lambda x: x[0].get("displayName") if isinstance(x, list) and x and isinstance(x[0], dict) else None
    )
    df_filtered['facultyEmailAddress'] = df_filtered['faculty'].apply(
        lambda x: x[0].get("emailAddress") if isinstance(x, list) and x and isinstance(x[0], dict) else None
    )
    # Drop the original 'faculty' column as its info is now flattened
    df_filtered = df_filtered.drop(columns=['faculty'])


    # --- Process and Flatten 'meetingsFaculty' ---

    # This function extracts specific meeting time details
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

    # Apply the extraction function
    df_filtered['meetingsFaculty'] = df_filtered['meetingsFaculty'].apply(extract_meeting_details)
    df_filtered['creditHours'] = df_filtered['creditHours'].fillna("None")

    # Explode the 'meetingsFaculty' column to create new rows for each meeting time
    # This means a course with multiple meeting times will have multiple rows in the output.
    # We need to ensure that rows with no meetings are handled,
    # so we might fill empty lists with a placeholder dict if we want to retain those rows.
    # For now, courses without meetings will just not be exploded.
    df_exploded = df_filtered.explode('meetingsFaculty').reset_index(drop=True)

    # Now, promote the elements of the 'meetingsFaculty' dictionary into new columns
    # We must handle cases where 'meetingsFaculty' might be None (e.g., if original list was empty)
    df_exploded_final = pd.json_normalize(df_exploded['meetingsFaculty']).add_prefix('meeting_')

    # Concatenate the new meeting columns with the rest of the DataFrame
    # Drop the original 'meetingsFaculty' column before concatenation if it's still present
    # Check if 'meetingsFaculty' is still in df_exploded before dropping
    if 'meetingsFaculty' in df_exploded.columns:
        df_exploded = df_exploded.drop(columns=['meetingsFaculty'])

    # Ensure indices are aligned for concatenation
    df_final = pd.concat([df_exploded, df_exploded_final], axis=1)

    df_final = df_final.where(pd.notnull(df_final), None)

    # Convert the DataFrame to a list of dictionaries (JSON records)
    course_data = df_final.to_dict(orient='records')

    # Convert the list of dictionaries to a JSON string
    json_output = json.dumps(course_data, indent=4)

    return json_output


generated_json = generate_course_json("ucr_courses_202440.csv")

with open('ucr_courses_data.json', 'w') as f:
        f.write(generated_json)
print("\nJSON data saved to ucr_courses_data.json")