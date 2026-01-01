"""
Configuration file for RentEase application.
You can override these settings using environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('ai_apis.env')

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'adet_rentease')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    
    # AI Configuration
    GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
    GEMINI_MODEL = 'gemini-2.0-flash'

