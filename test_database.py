"""
Test script for database creation and basic operations
"""

import os
from database import DatabaseManager, create_database
from models import TriggerWordCategory, TriggerWord, Song


def test_database_creation():
    """Test database creation and table setup"""
    
    # Test database path
    test_db_path = "test_spotify_ocd_saver.db"
    
    # Remove test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print(f"Removed existing test database: {test_db_path}")
    
    print("=" * 50)
    print("Testing Database Creation")
    print("=" * 50)
    
    # Test 1: Create new database
    print("\n1. Creating new database...")
    db = create_database(test_db_path)
    
    # Test 2: Verify database exists
    print("\n2. Verifying database exists...")
    assert db.database_exists(), "Database should exist after creation"
    print("✓ Database file exists")
    
    # Test 3: Check if tables were created
    print("\n3. Checking if tables were created...")
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        'trigger_word_categories',
        'trigger_words', 
        'streaming_services',
        'lyrics_services',
        'songs',
        'trigger_timestamps'
    ]
    
    for table in expected_tables:
        assert table in tables, f"Table {table} should exist"
        print(f"✓ Table '{table}' exists")
    
    # Test 4: Check default data
    print("\n4. Checking default data...")
    
    # Check streaming services
    cursor.execute("SELECT COUNT(*) FROM streaming_services")
    streaming_count = cursor.fetchone()[0]
    assert streaming_count > 0, "Should have default streaming services"
    print(f"✓ Found {streaming_count} streaming services")
    
    # Check lyrics services
    cursor.execute("SELECT COUNT(*) FROM lyrics_services")
    lyrics_count = cursor.fetchone()[0]
    assert lyrics_count > 0, "Should have default lyrics services"
    print(f"✓ Found {lyrics_count} lyrics services")
    
    # Check trigger word categories
    cursor.execute("SELECT COUNT(*) FROM trigger_word_categories")
    category_count = cursor.fetchone()[0]
    assert category_count > 0, "Should have default category"
    print(f"✓ Found {category_count} trigger word categories")
    
    # Test 5: Test existing database handling
    print("\n5. Testing existing database handling...")
    db2 = create_database(test_db_path)  # Should connect to existing
    assert db2.database_exists(), "Should recognize existing database"
    print("✓ Properly handled existing database")
    
    # Test 6: Test basic data insertion
    print("\n6. Testing basic data insertion...")
    
    # Insert a trigger word category
    cursor.execute("""
        INSERT INTO trigger_word_categories (name, description)
        VALUES (?, ?)
    """, ("Profanity", "Words containing profanity"))
    
    # Get the category ID
    category_id = cursor.lastrowid
    
    # Insert a trigger word
    cursor.execute("""
        INSERT INTO trigger_words (word, category_id)
        VALUES (?, ?)
    """, ("badword", category_id))
    
    # Insert a song
    cursor.execute("""
        INSERT INTO songs (title, artist, album, duration_ms, spotify_id)
        VALUES (?, ?, ?, ?, ?)
    """, ("Test Song", "Test Artist", "Test Album", 180000, "test_spotify_id"))
    
    conn.commit()
    print("✓ Successfully inserted test data")
    
    # Test 7: Test data retrieval
    print("\n7. Testing data retrieval...")
    
    # Retrieve categories
    cursor.execute("SELECT id, name, description FROM trigger_word_categories WHERE name = ?", ("Profanity",))
    category = cursor.fetchone()
    assert category is not None, "Should find inserted category"
    print(f"✓ Retrieved category: {category[1]} - {category[2]}")
    
    # Retrieve trigger words
    cursor.execute("SELECT word FROM trigger_words WHERE category_id = ?", (category_id,))
    word = cursor.fetchone()
    assert word is not None, "Should find inserted trigger word"
    print(f"✓ Retrieved trigger word: {word[0]}")
    
    # Retrieve songs
    cursor.execute("SELECT title, artist, spotify_id FROM songs WHERE spotify_id = ?", ("test_spotify_id",))
    song = cursor.fetchone()
    assert song is not None, "Should find inserted song"
    print(f"✓ Retrieved song: {song[0]} by {song[1]} (ID: {song[2]})")
    
    # Close connections
    db.close()
    db2.close()
    
    # Clean up test database
    os.remove(test_db_path)
    print(f"\n✓ Test database {test_db_path} cleaned up")
    
    print("\n" + "=" * 50)
    print("ALL TESTS PASSED! ✅")
    print("Database setup is working correctly.")
    print("=" * 50)


def create_production_database():
    """Create the production database"""
    print("\n" + "=" * 50)
    print("Creating Production Database")
    print("=" * 50)
    
    db = create_database("spotify_ocd_saver.db")
    print(f"\nProduction database created at: {os.path.abspath(db.db_path)}")
    
    # Show table info
    conn = db.connect()
    cursor = conn.cursor()
    
    print("\nDatabase schema:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Table: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
    
    db.close()
    print("\n✅ Production database ready!")


if __name__ == "__main__":
    try:
        # Run tests first
        test_database_creation()
        
        # Create production database
        create_production_database()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
