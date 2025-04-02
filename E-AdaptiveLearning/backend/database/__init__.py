"""
E-AdaptiveLearning Database Module

This package handles all database interactions for the E-AdaptiveLearning system,
including connection management and CRUD operations for learning data.
"""

from .connection import DatabaseConnection, get_db_connection
from .db_handler import DatabaseHandler

__all__ = [
    'DatabaseConnection',
    'get_db_connection',
    'DatabaseHandler'
]