from openai import AzureOpenAI
import json
import os

client = AzureOpenAI(
  azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"], 
  api_key=os.environ['AZURE_OPENAI_API_KEY'],  
  api_version = "2024-12-01-preview"
)
deployment= "text-embedding-3-small"
JSON_FILE_PATH = "ucr_courses_data.json"


def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")

    try:
        response = client.embeddings.create(input=text, model=deployment)
        return response.data[0].embedding
    except:
        print(f"Error calling Azure OpenAI:")
        return ""

def getVector():

    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            courses_data = json.load(f)
        #print(f"Successfully loaded {len(courses_data)} course records from {JSON_FILE_PATH}")
    except FileNotFoundError:
        print(f"Error: The file '{JSON_FILE_PATH}' was not found. Please ensure it's in the correct directory.")


    embeddings_data = []
    count = 0
    for course in courses_data:
        text = f"{course['subjectCourse']} {course['courseTitle']}"

        embedding = get_embedding(text)
        embeddings_data.append({
            "course_id": course['subjectCourse'], # Or your unique section ID
            "text": text,
            "embedding": embedding
        })

    return embeddings_data

print(getVector())