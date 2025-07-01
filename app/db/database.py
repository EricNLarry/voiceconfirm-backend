from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def get_database() -> AsyncIOMotorClient:
    """Get database instance."""
    return db.database

async def connect_to_mongo():
    """Create database connection."""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.database_name]
        
        # Test the connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes for better performance."""
    try:
        # Users collection indexes
        await db.database.users.create_index("email", unique=True)
        await db.database.users.create_index("created_at")
        
        # Orders collection indexes
        await db.database.orders.create_index("user_id")
        await db.database.orders.create_index("order_id")
        await db.database.orders.create_index("confirmation_status")
        await db.database.orders.create_index("created_at")
        
        # Call logs collection indexes
        await db.database.call_logs.create_index("order_id")
        await db.database.call_logs.create_index("user_id")
        await db.database.call_logs.create_index("created_at")
        
        # Integrations collection indexes
        await db.database.integrations.create_index("user_id")
        await db.database.integrations.create_index("platform")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

# Dependency to get database
async def get_db():
    return await get_database()

