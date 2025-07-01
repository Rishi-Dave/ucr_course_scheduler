import json
import ast

ORIGINAL_COURSE_DATA_PATH = "ucr_courses_data.json"

EMBEDDINGS_JSON_PATH = "vectors.txt" # Make sure this matches your file name

OUTPUT_ENRICHED_JSON_PATH = "ucr_courses_data_with_embeddings.json"

def load_json_data(file_path):
    """Loads JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded {len(data)} records from JSON: {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}. Check file format.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None

def load_embeddings_from_txt(file_path):
    """
    Loads embeddings data from a TXT file containing a stringified Python list.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Safely evaluate the string as a Python literal (list of dicts)
            data = ast.literal_eval(content)
        print(f"Successfully loaded {len(data)} embeddings from TXT: {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: Embeddings TXT file not found at {file_path}")
        return None
    except (ValueError, SyntaxError) as e:
        print(f"Error: Could not safely evaluate content from {file_path} as a Python list. Check TXT file format.")
        print(f"Details: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading embeddings from {file_path}: {e}")
        return None

def merge_embeddings_into_courses(courses_data, embeddings_data):

    if not courses_data:
        print("No original course data to merge into.")
        return []
    if not embeddings_data:
        print("No embeddings data provided. Returning original course data without embeddings.")
        return courses_data
    embeddings_map = {item['course_id']: item['embedding'] for item in embeddings_data if 'course_id' in item and 'embedding' in item}
    
    print(f"Prepared map for {len(embeddings_map)} embeddings.")

    merged_courses = []
    courses_with_embeddings = 0
    courses_without_embeddings = 0

    for course in courses_data:

        course_identifier = course.get('subjectCourse')


        if course_identifier and course_identifier in embeddings_map:
            course['course_title_vector'] = embeddings_map[course_identifier]
            courses_with_embeddings += 1
        else:
            # If no embedding is found, you might want to add a None or an empty list
            # or just skip adding the field. For Atlas Search, it's fine if the field is absent.
            course['course_title_vector'] = None # Explicitly set to None if no embedding found
            courses_without_embeddings += 1
            # print(f"Debug: No embedding found for course identifier: {course_identifier} (Course: {course.get('courseTitle')})")


        merged_courses.append(course)

    print(f"Merged summary: {courses_with_embeddings} courses received embeddings. {courses_without_embeddings} courses did not find a matching embedding.")
    return merged_courses

def save_json_data(data, file_path):
    """Saves data to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4) # Use indent for pretty printing
        print(f"Successfully saved merged data to {file_path}")
    except Exception as e:
        print(f"Error saving data to {file_path}: {e}")

if __name__ == "__main__":
    print("Starting data merge process...")
    
    # 1. Load the original UCR courses JSON data
    original_courses_data = load_json_data(ORIGINAL_COURSE_DATA_PATH)

    # 2. Load the list of embeddings
    embeddings_list_data = load_embeddings_from_txt(EMBEDDINGS_JSON_PATH)

    if original_courses_data and embeddings_list_data:
        # 3. Merge the embeddings into the original course data
        enriched_courses = merge_embeddings_into_courses(original_courses_data, embeddings_list_data)

        # 4. Save the new, enriched JSON data to a new file
        if enriched_courses:
            save_json_data(enriched_courses, OUTPUT_ENRICHED_JSON_PATH)
            print(f"\nYour enriched JSON file '{OUTPUT_ENRICHED_JSON_PATH}' is now ready.")
            print("You can use this file to insert into MongoDB Atlas,")
            print("and then create an Atlas Search index on the 'course_title_vector' field.")
    else:
        print("Cannot proceed with merge: Required JSON files were not loaded successfully.")

