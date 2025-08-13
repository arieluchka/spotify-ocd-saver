"""
Database module for Spotify OCD Saver
Handles SQLite database creation, connection, and table management
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from schemas import (
    TABLE_CREATION_STATEMENTS,
    CREATE_INDEXES,
    INSERT_DEFAULT_STREAMING_SERVICES,
    INSERT_DEFAULT_LYRICS_SERVICES,
    INSERT_DEFAULT_TRIGGER_CATEGORY,
    DEFAULT_STREAMING_SERVICES,
    DEFAULT_LYRICS_SERVICES,
    DEFAULT_TRIGGER_CATEGORIES
)


class DatabaseManager:
    """Manages SQLite database connections and operations"""
    
    def __init__(self, db_path: str = "spotify_ocd_saver.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
    
    def database_exists(self) -> bool:
        """Check if database file already exists"""
        return self.db_path.exists() and self.db_path.is_file()
    
    def connect(self) -> sqlite3.Connection:
        """
        Create connection to SQLite database
        
        Returns:
            SQLite connection object
        """
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            # Enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
        
        return self.connection
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def create_tables(self):
        """Create all required tables if they don't exist"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Create all tables using schemas from separate file
        for create_statement in TABLE_CREATION_STATEMENTS:
            cursor.execute(create_statement)
        
        # Create indexes for better performance
        for index_statement in CREATE_INDEXES:
            cursor.execute(index_statement)
        
        conn.commit()
        print("Database tables created successfully!")
    
    def initialize_database(self, force_recreate: bool = False):
        """
        Initialize the database with all tables
        
        Args:
            force_recreate: If True, recreate database even if it exists
        """
        if self.database_exists() and not force_recreate:
            print(f"Database already exists at: {self.db_path}")
            print("Connecting to existing database...")
            self.connect()
            return
        
        if force_recreate and self.database_exists():
            print(f"Removing existing database: {self.db_path}")
            os.remove(self.db_path)
        
        print(f"Creating new database at: {self.db_path}")
        self.connect()
        self.create_tables()
        self.insert_default_data()
    
    def insert_default_data(self):
        """Insert default data for streaming and lyrics services"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Insert default streaming services
        cursor.executemany(INSERT_DEFAULT_STREAMING_SERVICES, DEFAULT_STREAMING_SERVICES)
        
        # Insert default lyrics services
        cursor.executemany(INSERT_DEFAULT_LYRICS_SERVICES, DEFAULT_LYRICS_SERVICES)
        
        # Insert default trigger word categories
        cursor.executemany(INSERT_DEFAULT_TRIGGER_CATEGORY, DEFAULT_TRIGGER_CATEGORIES)
        
        conn.commit()
        print("Default data inserted successfully!")


def create_database(db_path: str = "spotify_ocd_saver.db", force_recreate: bool = False) -> DatabaseManager:
    """
    Convenience function to create and initialize database
    
    Args:
        db_path: Path to the SQLite database file
        force_recreate: If True, recreate database even if it exists
        
    Returns:
        DatabaseManager instance
    """
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_database(force_recreate)
    return db_manager


if __name__ == "__main__":
    # Example usage
    db = create_database()
    print(f"Database initialized at: {db.db_path}")
    db.close()
