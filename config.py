"""
Configuration settings for Campus Assets application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # MongoDB configuration
    MONGODB_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/campus_assets'
    MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME') or 'campus_assets'
    
    # Firebase configuration
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
    FIREBASE_AUTH_URI = os.environ.get('FIREBASE_AUTH_URI')
    FIREBASE_TOKEN_URI = os.environ.get('FIREBASE_TOKEN_URI')
    
    # GROQ API configuration
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = os.environ.get('GROQ_MODEL') or 'llama3-8b-8192'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
    
    # Email configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MASTER_ADMIN_EMAIL = os.environ.get('MASTER_ADMIN_EMAIL')