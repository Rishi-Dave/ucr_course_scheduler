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

if __name__ == "__main__":
    coursesTaken = ["CS010A", "CS010B", "CS010C", "CS011", "MATH031", "MATH009C", "CS061", "CS100", "PHYS040A", "CS120A", "STAT010", "CS111"]
    coursesToTake = ["CS141", "CS150", "CS120B", "CS161", "STAT155", "ME009", "CS170", "CS171", "CS173", "PHYS040B", "PHYS040C"]
    # remove from list if prereqs aren't met
    mongo_client = connect_to_mongodb(MONGO_URI)

    if mongo_client:
        validCourses = prereqs_fullfilled(mongo_client, coursesTaken, coursesToTake)
        print(validCourses)


    general_interest_query = "courses that help me learn english" # Or derived from user's broader intent
    if general_interest_query:
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
                'limit': 10
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
        for i in result:
            print(i)

        mongo_client.close()
        print("MongoDB connection closed.")
    else:
        print("Could not connect to MongoDB. Embeddings not uploaded.")
    
    #scoring: keyword vector semantic search,' during valid time frame, 