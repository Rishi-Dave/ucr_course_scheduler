import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, BulkWriteError
import os
import dotenv

dotenv.load_dotenv()

# --- Configuration ---
# Path to the JSON file containing your embeddings data
# This file is assumed to be in the format: {"course_id_1": [embedding_list_1], "course_id_2": [embedding_list_2], ...}
EMBEDDINGS_JSON_PATH = "ucr_courses_data_with_embeddings.json" # Make sure this matches your file name
password = os.environ["mongodb_pass"]
# Your MongoDB connection string (from MongoDB Atlas or local)
# Replace <username>, <password>, and cluster details
MONGO_URI = f"mongodb+srv://rdave009:{password}@cluster0.srsdcbr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# For local MongoDB:
# MONGO_URI = "mongodb://localhost:27017/"

# Database and collection for your EMBEDDINGS data
DATABASE_NAME = "course_catalog"  # You can use the same database as your main course data
EMBEDDINGS_COLLECTION_NAME = "course_vectors" # A new collection just for embeddings

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

def load_embeddings_file(file_path):
    """
    Loads embeddings data from a JSON file containing a dictionary
    where values are the embedding lists.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f) # Use json.load() since it's a JSON file
        print(f"Successfully loaded {len(data)} embedding entries from JSON: {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: Embeddings JSON file not found at {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {file_path}. Check file format.")
        print(f"Details: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading embeddings from {file_path}: {e}")
        return None

def transform_embeddings_for_mongo(embeddings_dict):
    """
    Transforms the {'course_id': [embedding_list]} dictionary into a
    list of documents: [{'course_id': '...', 'embedding': [...]}, ...]
    """
    if not embeddings_dict:
        return []
    
    transformed_list = []
    for course_id, embedding_list in embeddings_dict.items():
        # Ensure the value is actually a list (the embedding)
        if isinstance(embedding_list, list):
            transformed_list.append({
                "course_id": course_id,
                "embedding": embedding_list
            })
        else:
            print(f"Warning: Skipping {course_id} as its value is not a list (embedding).")
    
    print(f"Transformed {len(transformed_list)} embeddings into MongoDB-ready documents.")
    return transformed_list

def insert_data_into_collection(client, db_name, collection_name, documents_to_insert):
    """Inserts a list of documents into a specified MongoDB collection."""
    db = client[db_name]
    collection = db[collection_name]

    print(f"Attempting to insert {len(documents_to_insert)} documents into '{collection_name}'...")
    


    if not documents_to_insert: # Final check to ensure the list isn't empty
        print("Error: Documents list is empty after processing. Nothing to insert.")
        return

    # Optional: Clear existing data in the collection before inserting
    # collection.delete_many({})
    # print("Existing data cleared.")

    try:
        result = collection.insert_many(documents_to_insert, ordered=False)
        print(f"Successfully inserted {len(result.inserted_ids)} documents.")
    except BulkWriteError as bwe:
        print(f"BulkWriteError occurred. Some documents might not have been inserted.")
        print("Error details:", bwe.details)
        print(f"Successfully inserted {bwe.details.get('nInserted', 0)} documents before errors.")
    except Exception as e:
        print(f"An unexpected error occurred during insertion: {e}")

if __name__ == "__main__":
    print("Starting embeddings upload process...")
    
    # 1. Load your embeddings data from the JSON file (as a dictionary)
    raw_embeddings_dict = load_embeddings_file(EMBEDDINGS_JSON_PATH)

    if raw_embeddings_dict:
        # 2. Transform the dictionary into a list of MongoDB-ready documents
        mongo_embeddings_docs = transform_embeddings_for_mongo(raw_embeddings_dict)

        if mongo_embeddings_docs:
            # 3. Connect to MongoDB Atlas
            mongo_client = connect_to_mongodb(MONGO_URI)

            if mongo_client:
                # 4. Insert the transformed embeddings into the separate collection
                insert_data_into_collection(mongo_client, DATABASE_NAME, EMBEDDINGS_COLLECTION_NAME, mongo_embeddings_docs)
                
                # 5. Close the MongoDB connection
                mongo_client.close()
                print("MongoDB connection closed.")
            else:
                print("Could not connect to MongoDB. Embeddings not uploaded.")
        else:
            print("No MongoDB-ready documents generated from embeddings data. Nothing to upload.")
    else:
        print("No raw embeddings data loaded from JSON file. Nothing to process or upload.")