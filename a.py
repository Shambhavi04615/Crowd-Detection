from pymongo import MongoClient

# MongoDB connection string
MONGO_URI = (
    "mongodb+srv://harsh:hT6jMhF2ZKJ64GW2"
    "@crowd.wy6e3yo.mongodb.net/sample_mflix"
    "?retryWrites=true&w=majority&appName=crowd"
)

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["sample_mflix"]             # Your database
collection = db["sessions"]             # Your collection

# Dummy data to insert
dummy_data = {
    "user_id": "user123",
    "session_start": "2025-06-11T18:30:00Z",
    "duration_minutes": 45,
    "location": "Main Hall A",
    "crowd_count": 27
}

# Insert dummy document
inserted_id = collection.insert_one(dummy_data).inserted_id
print(f"Inserted document with ID: {inserted_id}")

# Fetch and display inserted document
fetched_doc = collection.find_one({"_id": inserted_id})
print("Fetched Document:")
print(fetched_doc)
