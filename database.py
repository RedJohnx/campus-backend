"""
Database connection and initialization utilities for MongoDB Atlas.
"""
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global database connection
db = None
client = None

def init_db():
    """Initialize MongoDB connection and create indexes."""
    global db, client
    
    try:
        # Create MongoDB client
        client = MongoClient(
            Config.MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,         # 10 second connection timeout
            socketTimeoutMS=20000           # 20 second socket timeout
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB Atlas")
        
        # Get database
        db = client[Config.MONGODB_DB_NAME]
        
        # Create indexes for better performance
        create_indexes()
        
        # Initialize predefined departments
        initialize_departments()
        
        return True
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

def get_db():
    """Get database instance."""
    global db
    if db is None:
        init_db()
    return db

def create_indexes():
    """Create database indexes for optimized queries."""
    try:
        # Resources collection indexes
        db.resources.create_index([("department", ASCENDING)])
        db.resources.create_index([("location", ASCENDING)])
        db.resources.create_index([("device_name", ASCENDING)])
        db.resources.create_index([("created_at", ASCENDING)])
        db.resources.create_index([("department", ASCENDING), ("location", ASCENDING)])
        
        # Users collection indexes
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.users.create_index([("uid", ASCENDING)], unique=True)
        db.users.create_index([("role", ASCENDING)])
        
        # Departments collection indexes
        db.departments.create_index([("name", ASCENDING)], unique=True)
        
        # Chat sessions collection indexes
        db.chat_sessions.create_index([("user_id", ASCENDING)])
        db.chat_sessions.create_index([("created_at", ASCENDING)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

def initialize_departments():
    """Initialize predefined departments in the database."""
    from models import DepartmentModel
    from datetime import datetime, timezone
    
    predefined_departments = [
        "Aerospace Engineering",
        "Artificial Intelligence & Data Science",
        "Artificial Intelligence & Machine Learning",
        "Biotechnology",
        "Chemical Engineering",
        "Civil Engineering",
        "Computer Science & Engineering",
        "Computer Science & Engineering (Artificial Intelligence & Machine Learning)",
        "Computer Science & Engineering (Cyber Security)",
        "Electrical & Electronics Engineering",
        "Electronics & Communication Engineering",
        "Electronics & Instrumentation Engineering",
        "Electronics & Telecommunication Engineering",
        "Industrial Engineering & Management",
        "Information Science & Engineering",
        "Mechanical Engineering",
        "Medical Electronics Engineering",
        "Architecture"
    ]
    
    try:
        departments_collection = db.departments
        initialized_count = 0
        
        for dept_name in predefined_departments:
            # Check if department already exists
            existing_dept = departments_collection.find_one({"name": dept_name})
            
            if not existing_dept:
                # Use the model to create properly formatted document
                department_data = {"name": dept_name, "locations": []}
                department_doc = DepartmentModel.create_department_document(department_data)
                departments_collection.insert_one(department_doc)
                initialized_count += 1
        
        logger.info(f"Initialized {initialized_count} new predefined departments (total: {len(predefined_departments)})")
        
    except Exception as e:
        logger.error(f"Error initializing departments: {e}")

def test_connection():
    """Test MongoDB connection and return status."""
    try:
        if client is None:
            return False, "Database not initialized"
        
        # Test connection with ping
        client.admin.command('ping')
        
        # Test database access
        collections = db.list_collection_names()
        
        return True, f"Connection successful. Database: {Config.MONGODB_DB_NAME}, Collections: {len(collections)}"
        
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def close_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")