import pandas as pd
import re
import os # Import os for path operations if needed, though not strictly required for this fix.

def extract_prerequisites(prereq_string):
    """
    Extracts prerequisite information from a string in the 'prerequisites' column.
    Handles 'OR' conditions and implicitly 'AND'ed conditions within each 'OR' block,
    and extracts course codes, minimum grades, and concurrency information.

    Args:
        prereq_string (str): The string from the 'prerequisites' column.

    Returns:
        list: A list of lists. Each inner list represents an 'OR' condition,
              and contains dictionaries for each 'AND'ed prerequisite within that condition.
              Example: [[{'course': 'CHEM001A', 'min_grade': 'C-', 'concurrent': True}],
                        [{'course': 'CHEM01HA', 'min_grade': 'C-', 'concurrent': True},
                         {'course': 'CHEM1HLA', 'min_grade': 'C-', 'concurrent': True}]]
              Returns an empty list if no prerequisites are found or the input is invalid.
    """
    if pd.isna(prereq_string) or not prereq_string.strip():
        return []

    # Remove the "Prerequisites:" prefix for easier parsing
    clean_string = prereq_string.replace("Prerequisites:", "").strip()

    all_prereqs_options = []

    # Regex to find a single course prerequisite detail block.
    # This pattern captures:
    # 1. The course code (e.g., BIOL005A, CS 010W)
    # 2. The minimum grade (optional)
    # 3. The concurrency statement (optional)
    # re.DOTALL is crucial as it allows '.' to match newlines, enabling parsing of multi-line details.
    course_details_pattern = re.compile(
        r'Course or Test:\s*([A-Z]{2,4}\s*\d{2,4}[A-Z]*)\s*'  # Capture course code (e.g., CS 010W, ENGL004AWPE)
        r'(?:\\n Minimum Grade of\s*([A-Z0-9\-\+]+))?'        # Optionally capture minimum grade
        r'(?:\\n\s*(May be taken concurrently|May not be taken concurrently)\.)?', # Optionally capture concurrency
        re.IGNORECASE | re.DOTALL
    )

    # Handle the case of simple prerequisites without nested parentheses like "Prerequisites:CS100"
    if '(' not in clean_string and ')' not in clean_string:
        # Attempt to match a single course code pattern
        simple_course_match = re.match(r'^([A-Z]{2,4}\s*\d{2,4}[A-Z]*)$', clean_string.strip(), re.IGNORECASE)
        if simple_course_match:
            course_code = simple_course_match.group(1).replace(" ", "").upper()
            all_prereqs_options.append([{
                'course': course_code,
                'min_grade': None,
                'concurrent': None
            }])
        return all_prereqs_options


    # If parentheses exist, proceed with splitting by OR conditions.
    # This split uses the pattern ")\nor\n(" to separate distinct OR blocks,
    # handling slight variations in newline characters.
    or_conditions_raw = re.split(r'\)\n?or\n?\(', clean_string)

    for condition_block_raw in or_conditions_raw:
        block_content = condition_block_raw.strip()
        # Remove any leading/trailing parentheses that might remain from the split or initial string.
        if block_content.startswith('('):
            block_content = block_content[1:]
        if block_content.endswith(')'):
            block_content = block_content[:-1]
        
        current_and_set = [] # This list will hold prerequisites that are ANDed together within this OR block

        # Find all individual course detail matches within the current 'OR' block.
        # Each match represents a prerequisite that is 'AND'ed with others in this block.
        for match in course_details_pattern.finditer(block_content):
            course_code = match.group(1).replace(" ", "").upper() # Normalize course code (e.g., "POSC 010" -> "POSC010")
            min_grade = match.group(2)
            concurrency_str = match.group(3)

            concurrent = None
            if concurrency_str:
                concurrent = "May be taken concurrently" in concurrency_str
            
            current_and_set.append({
                'course': course_code,
                'min_grade': min_grade,
                'concurrent': concurrent
            })
        
        # Add this set of ANDed prerequisites to the overall list of OR options,
        # but only if any prerequisites were successfully extracted from the block.
        if current_and_set:
            all_prereqs_options.append(current_and_set)

    return all_prereqs_options

# Load the CSV file
df = pd.read_csv('ucr_courses_202440.csv')

# Apply the function to the 'prerequisites' column to create a new column
df['parsed_prerequisites'] = df['prerequisites'].apply(extract_prerequisites)

# --- Diagnostic Prints ---
total_courses_with_raw_prereqs = df['prerequisites'].notna().sum()
total_courses_with_parsed_prereqs = df['parsed_prerequisites'].apply(lambda x: len(x) > 0).sum()

print(f"\nTotal courses with a raw 'prerequisites' string: {total_courses_with_raw_prereqs}")
print(f"Total courses with successfully 'parsed_prerequisites': {total_courses_with_parsed_prereqs}")
# --- End Diagnostic Prints ---


# Display some examples to verify the parsing
print("Examples of parsed prerequisites:")
# Filter for rows where prerequisites were actually parsed
example_rows = df[df['parsed_prerequisites'].apply(lambda x: len(x) > 0)]

if not example_rows.empty:
    # Display the course title, original prerequisite string, and the new parsed data
    for index, row in example_rows.head(10).iterrows():
        print(f"\nCourse Title: {row['courseTitle']}")
        print(f"Original Prereq String: {row['prerequisites']}")
        print(f"Parsed Prereqs: {row['parsed_prerequisites']}")
else:
    print("No entries with parsed prerequisites found in the DataFrame to display.")

# --- Corrected CSV Saving ---
# Define the new filename for the CSV that includes the parsed prerequisites
output_csv_filename = 'ucr_courses_with_parsed_prereqs.csv'

try:
    # Save the DataFrame with the new 'parsed_prerequisites' column to a new CSV file
    # index=False prevents Pandas from writing the DataFrame index as a column.
    # encoding='utf-8' ensures proper handling of various characters.
    df.to_csv(output_csv_filename, index=False, encoding='utf-8')
    print(f"\nSuccessfully wrote {len(df)} rows (including parsed prerequisites) to {output_csv_filename}")
except Exception as e:
    print(f"Error writing CSV to file: {e}")

