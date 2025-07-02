import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, BulkWriteError
import os
from openai import AzureOpenAI
import dotenv

dotenv.load_dotenv()

client = AzureOpenAI(
  azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"], 
  api_key=os.environ['AZURE_OPENAI_API_KEY'],  
  api_version = "2024-12-01-preview"
)
deployment= "gpt-4o"
embeddingsdeployment = "text-embedding-3-small"
password = os.environ["mongodb_pass"]

MONGO_URI = f"mongodb+srv://rdave009:{password}@cluster0.srsdcbr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "course_catalog"  # You can use the same database as your main course data
EMBEDDINGS_COLLECTION_NAME = "course_vectors"
COURSES_COLLECTION_NAME = "courses"


def connect_to_mongodb(uri):
    """Establishes a connection to MongoDB."""
    try:
        client = MongoClient(uri)
        client.admin.command('ismaster')
        print("MongoDB connection successful!")
        return client
    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")
        return None

def fetch_all_courses_from_db(client):
    """
    Fetches all course documents from the specified collection.
    """
    if not client:
        return []

    try:
        db = client[DATABASE_NAME]
        courses_collection = db[COURSES_COLLECTION_NAME]
        
        # Fetch all documents from the collection
        all_courses = list(courses_collection.find({}))
        print(f"Fetched {len(all_courses)} courses from '{COURSES_COLLECTION_NAME}'.")
        return all_courses
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return []

def fetch_course_by_id(client, course_id):
    """
    Fetches a single course document by its subjectCourse ID.
    """
    if not client:
        return None

    try:
        db = client[DATABASE_NAME]
        courses_collection = db[COURSES_COLLECTION_NAME]
        
        course = courses_collection.find_one({"subjectCourse": course_id})
        '''
        if course:
            print(f"Fetched course: {course['subjectCourse']} - {course['courseTitle']}")
        else:
            print(f"Course with ID '{course_id}' not found.")
        '''
        return course
    except Exception as e:
        print(f"Error fetching course by ID: {e}")
        return None
    
def prereqs_fullfilled(client, coursesTaken, coursesToTake):
    validCourses = []
    for course in coursesToTake:
        courseDict = fetch_course_by_id(client, course)
        if courseDict:
            validCourse = True
            for prereqList in courseDict['prerequisites']:
                prereqsMissed = 0
                for prereq in prereqList:
                    if prereq in coursesTaken:
                        break
                    elif prereq == "nan":
                        break
                    else:
                        prereqsMissed+=1
                if prereqsMissed == len(prereqList):
                    print(f"{course} prerequisites are not fullfilled")
                    validCourse = False
                    break
            if(validCourse):
                validCourses.append(course)
    return validCourses 


def score_embeddings(mongo_client, query, validCourses):
    if query:
        query_embedding = client.embeddings.create(
            input=[general_interest_query],
            model="text-embedding-3-small"
        ).data[0].embedding

        # Perform vector search on your 'course_embeddings' collection
        # (assuming you've inserted your course_id -> embedding data there)
        # This will find course_ids that are semantically similar.
        # You'll need to fetch the full details for these course_ids from your main course collection.
        
        pipeline = [
            {
                '$vectorSearch': {
                'index': 'vector_index', 
                'path': 'embedding', 
                'queryVector': query_embedding,
                'numCandidates': 10000,
                'limit': 50,
                "filter": {                               
                    "course_id": { "$in": validCourses }
                    }
                }
            }, {
                '$project': {
                '_id': 0, 
                "course_id": 1,
                'plot': 1, 
                'title': 1, 
                'score': {
                    '$meta': 'vectorSearchScore'
                    }
                }
            }
        ]
        
        result = mongo_client[DATABASE_NAME][EMBEDDINGS_COLLECTION_NAME].aggregate(pipeline)
        vector_similarity_scores = []
        added_courses = set()
        for i in result:
            if(i["course_id"] in added_courses):
                continue
            vector_similarity_scores.append(i)
            added_courses.add(i["course_id"])

        return vector_similarity_scores

def get_user_preferences(query):
    prompt = f"""
            Given this query from the user: {query},

    """
def get_llm_score(course, query, semantic_similarity_score):
    """
    Constructs a prompt and calls OpenAI to get a score for a candidate schedule/section,
    incorporating semantic relevance.
    """
    
    # Calculate semantic similarity for the candidate if a general_query_embedding is provided
    
    # Craft the prompt to the LLM
    prompt = f"""
    You are an academic advisor. A student wants to find courses that fit their preferences.
    Student's Preferences: {query}
    
    Here is a specific course section being considered:
    Course: {course['subjectCourse']} - {course['courseTitle']}
    Days: Monday - {course['meeting_meetingMonday']}, Tuesday  - {course['meeting_meetingTuesday']}, Wednesday - {course['meeting_meetingWednesday']}, Thursday - {course['meeting_meetingThursday']}, Friday - {course['meeting_meetingFriday']}
    /Times(In Military Time, Morning is 800 - 1100, Afternoon is 1200 - 1500, Evening is 1600- 1900): {course['meeting_meetingBeginTime']} - {course['meeting_meetingEndTime']}
    [Other details]
    
    This course has a semantic similarity score of {semantic_similarity_score} to the student's broader interests (where 1.0 is a perfect match).
    
    On a scale of 1 to 10... considering all preferences including semantic fit, output just the score
    Score:
    """

    try:
        messages = [{"role": "user", "content": prompt}]  
        response = client.chat.completions.create(model=deployment, messages=messages, max_tokens=600, temperature = 0.1)
        return response.choices[0].message.content
    except:
        print(f"Error calling Azure OpenAI:")
        return ""



if __name__ == "__main__":
    coursesTaken = ["CS010A", "CS010B", "CS010C", "CS011", "MATH031", "MATH009C", "CS061", "CS100", "PHYS040A", "CS120A", "STAT010", "CS111"]
    coursesToTake = ["CS141", "CS150", "CS120B", "CS161", "STAT155", "ME009", "CS170", "CS171", "CS173", "PHYS040B", "PHYS040C"]
    # remove from list if prereqs aren't met
    mongo_client = connect_to_mongodb(MONGO_URI)

    if mongo_client:
        


        validCourses = prereqs_fullfilled(mongo_client, coursesTaken, coursesToTake)


        general_interest_query = "CS141 and CS150" # Or derived from user's broader intent
        vector_similarity_score = score_embeddings(mongo_client, general_interest_query, validCourses)
        
        for i in vector_similarity_score:
            courses = list(mongo_client[DATABASE_NAME][COURSES_COLLECTION_NAME].find({"subjectCourse" : i["course_id"]}))
            for course in courses:
                print(f"{i["course_id"]}: {course["meeting_meetingBeginTime"]} - {course["meeting_meetingEndTime"]}")
                print(get_llm_score(course, general_interest_query, i["score"]))

        
        mongo_client.close()
        print("MongoDB connection closed.")
    else:
        print("Could not connect to MongoDB. Embeddings not uploaded.")
    
    #scoring: keyword vector semantic search,' during valid time frame, 