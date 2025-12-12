import motor.motor_asyncio
from app.core.config import settings

# Global client variable to be initialized on startup
client: motor.motor_asyncio.AsyncIOMotorClient = None

async def connect_to_mongo():
    global client
    print("Connecting to MongoDB...")
    try:
        # Connect to MongoDB
        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        # The next line validates the connection
        await client.admin.command('ping')
        print("Connected to MongoDB!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        # Optionally, raise an exception or exit the application if the DB is critical

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Closed MongoDB connection.")

def get_master_db():
    """Returns the Master Database client."""
    if client is None:
        raise ConnectionError("MongoDB client is not initialized.")
    return client[settings.MASTER_DB_NAME]

def get_mongo_client():
    """Returns the raw MongoDB client object."""
    if client is None:
        raise ConnectionError("MongoDB client is not initialized.")
    return client