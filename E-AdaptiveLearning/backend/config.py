import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Application settings
APP_NAME = "E-AdaptiveLearning"
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
TESTING = os.getenv("TESTING", "False").lower() == "true"
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS", "7"))

# API settings
API_VERSION = "1.0.0"
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# AI Model settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.5"))
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-1.0-pro")

# Learning settings
DEFAULT_DIFFICULTY_LEVEL = int(os.getenv("DEFAULT_DIFFICULTY_LEVEL", "3"))
MAX_DIFFICULTY_LEVEL = 5
MIN_DIFFICULTY_LEVEL = 1
DEFAULT_QUIZ_QUESTIONS = int(os.getenv("DEFAULT_QUIZ_QUESTIONS", "5"))
MAX_QUIZ_QUESTIONS = int(os.getenv("MAX_QUIZ_QUESTIONS", "10"))

# Database settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "e_adaptive_learning")
MONGODB_CONNECT_TIMEOUT_MS = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))

# Collection names
COLLECTIONS = {
    "students": "students",
    "learning_logs": "learning_logs",
    "interactions": "interactions",
    "quizzes": "quizzes",
    "quiz_questions": "quiz_questions",
    "quiz_answers": "quiz_answers",
    "quiz_results": "quiz_results",
    "progress_reports": "progress_reports",
    "learning_patterns": "learning_patterns",
    "progress_summaries": "progress_summaries",
    "study_plans": "study_plans",
    "resource_recommendations": "resource_recommendations",
    "curriculum": "curriculum",
    "student_levels": "student_levels"
}

# Cache settings
CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")
CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))  # 5 minutes
CACHE_THRESHOLD = int(os.getenv("CACHE_THRESHOLD", "1000"))  # Maximum number of items

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": LOG_LEVEL,
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "e_adaptive_learning.log"),
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}

# CORS settings
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"

# Feature flags
FEATURES = {
    "enable_quiz_master": os.getenv("ENABLE_QUIZ_MASTER", "True").lower() == "true",
    "enable_progress_tracker": os.getenv("ENABLE_PROGRESS_TRACKER", "True").lower() == "true",
    "enable_learning_guide": os.getenv("ENABLE_LEARNING_GUIDE", "True").lower() == "true",
    "enable_ai_tutor": os.getenv("ENABLE_AI_TUTOR", "True").lower() == "true",
    "enable_dashboard": os.getenv("ENABLE_DASHBOARD", "True").lower() == "true",
    "enable_caching": os.getenv("ENABLE_CACHING", "True").lower() == "true",
    "enable_auto_difficulty_adjust": os.getenv("ENABLE_AUTO_DIFFICULTY_ADJUST", "True").lower() == "true",
}

# Timeout settings (in seconds)
TIMEOUTS = {
    "model_request": int(os.getenv("MODEL_REQUEST_TIMEOUT", "30")),
    "database_operation": int(os.getenv("DATABASE_OPERATION_TIMEOUT", "10")),
    "api_request": int(os.getenv("API_REQUEST_TIMEOUT", "60")),
}

# Rate limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/hour")
RATE_LIMIT_API = os.getenv("RATE_LIMIT_API", "1000/hour")

# Get environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Check if we're in a production environment and have critical configs
if ENVIRONMENT == "production":
    if SECRET_KEY == "dev-secret-key-change-in-production":
        raise ValueError("Production environment requires a secure SECRET_KEY!")
    
    if not GOOGLE_API_KEY:
        raise ValueError("Production environment requires GOOGLE_API_KEY!")

def get_model_config(model_name=None):
    """
    Get configuration for a specific model or the default model.
    
    Args:
        model_name (str, optional): Name of the model
        
    Returns:
        dict: Model configuration
    """
    models = {
        "gemini-1.5-flash": {
            "temperature": float(os.getenv("GEMINI_1_5_FLASH_TEMPERATURE", "0.5")),
            "api_key": GOOGLE_API_KEY,
        },
        "gemini-1.5-pro": {
            "temperature": float(os.getenv("GEMINI_1_5_PRO_TEMPERATURE", "0.7")),
            "api_key": GOOGLE_API_KEY,
        },
        "gemini-1.0-pro": {
            "temperature": float(os.getenv("GEMINI_1_0_PRO_TEMPERATURE", "0.7")),
            "api_key": GOOGLE_API_KEY,
        }
    }
    
    if model_name and model_name in models:
        return models[model_name]
    
    return models[DEFAULT_MODEL]

def get_db_config():
    """
    Get database configuration.
    
    Returns:
        dict: Database configuration
    """
    return {
        "uri": MONGODB_URI,
        "db_name": MONGODB_DB,
        "connect_timeout_ms": MONGODB_CONNECT_TIMEOUT_MS,
        "server_selection_timeout_ms": MONGODB_SERVER_SELECTION_TIMEOUT_MS,
        "collections": COLLECTIONS
    }