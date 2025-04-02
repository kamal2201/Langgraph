import os
import pymongo
from pymongo import MongoClient
from typing import Optional

class DatabaseConnection:
    """
    Class to handle MongoDB connection for the E-AdaptiveLearning system.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern to ensure only one database connection is created.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, connection_string: Optional[str] = None, db_name: Optional[str] = None):
        """
        Initialize the database connection.
        
        Args:
            connection_string (str, optional): MongoDB connection string. If None, uses config.
            db_name (str, optional): Database name. If None, uses config.
        """
        # Skip initialization if already initialized (singleton pattern)
        if self._initialized:
            return
            
        # Import config here to avoid circular imports
        from backend import config
        
        # Get connection details from parameters or config
        self.connection_string = connection_string or config.MONGODB_URI
        self.db_name = db_name or config.MONGODB_DB
        
        # Initialize client and database as None
        self.client = None
        self.db = None
        
        # Mark as initialized
        self._initialized = True
    
    def connect(self) -> None:
        """
        Establish connection to MongoDB.
        """
        try:
            # Create MongoDB client
            self.client = MongoClient(self.connection_string)
            
            # Get database
            self.db = self.client[self.db_name]
            
            # Test connection
            self.client.admin.command('ping')
            print(f"Connected to MongoDB: {self.db_name}")
            
        except pymongo.errors.ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            raise
    
    def get_database(self):
        """
        Get the MongoDB database instance.
        
        Returns:
            Database: pymongo database object
        """
        if not self.client or not self.db:
            self.connect()
        return self.db
    
    def get_collection(self, collection_name: str):
        """
        Get a specific collection from the database.
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Collection: pymongo collection object
        """
        if not self.client or not self.db:
            self.connect()
        return self.db[collection_name]
    
    def close(self) -> None:
        """
        Close the MongoDB connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            print("MongoDB connection closed")

# Create a default instance
db_connection = DatabaseConnection()

def get_db_connection() -> DatabaseConnection:
    """
    Get the database connection instance.
    
    Returns:
        DatabaseConnection: Singleton instance of DatabaseConnection
    """
    return db_connection