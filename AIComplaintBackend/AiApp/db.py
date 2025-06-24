import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
connection_string = os.getenv("MONGODB_URI")

try:
    client = MongoClient(connection_string)
    client.server_info()
    print("Successfully connected to MongoDB!")

    db = client['complaint_database']
    
    # Create collection without validation first
    if 'complaints' not in db.list_collection_names():
        db.create_collection("complaints")
        print("Collection 'complaints' created successfully")

    # Updated validator with new fields
    validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['time', 'date', 'profile_name', 'complaint_query', 'department', 'priority_score'],
            'properties': {
                '_id': {'bsonType': 'objectId'},
                'time': {'bsonType': 'string'},
                'date': {'bsonType': 'string'},
                'profile_name': {'bsonType': 'string'},
                'image_link': {'bsonType': 'string'},
                'video_link': {'bsonType': 'string'},
                'complaint_query': {'bsonType': 'string'},
                'priority_score': {'bsonType': 'int'},
                'department': {'bsonType': 'string'},
                'recommended_officer': {'bsonType': 'string'},
                'ai_analysis': {
                    'bsonType': 'object',
                    'properties': {
                        'sentiment': {'bsonType': 'string'},
                        'urgency_level': {'bsonType': 'string'},
                        'category': {'bsonType': 'string'},
                        'summary': {'bsonType': 'string'},
                        'suggested_actions': {'bsonType': 'array', 'items': {'bsonType': 'string'}}
                    }
                },
                'status': {
                    'bsonType': 'string',
                    'enum': ['rejected','in_progress', 'resolved', 'pending_review']
                }
            }
        }
    }

    db.command('collMod', 'complaints', validator=validator)
    print("Collection validator updated successfully")
    
    complaints_collection = db['complaints']

except Exception as e:
    print(f"Failed to connect to MongoDB: {str(e)}")
    raise