import sqlite3
import os
from typing import List, Optional
from contextlib import contextmanager
from datetime import datetime

from config.models import Song, TriggerTimestamp, SongStatus


class DatabaseManager:
    """SQLite database manager for Spotify OCD Saver"""
    
    def __init__(self, db_path: str = "spotify_ocd_saver.db"):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        if not os.path.exists(self.db_path):
            print(f"Creating new database: {self.db_path}")
            self.create_tables()
        else:
            print(f"Using existing database: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()
    
    def create_tables(self):
        """Create the songs and trigger_timestamps tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create songs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    album TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    status INTEGER NOT NULL DEFAULT 0,
                    spotify_id TEXT UNIQUE,
                    isrc TEXT,
                    lrclib_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create trigger_timestamps table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trigger_timestamps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_id INTEGER NOT NULL,
                    song_id INTEGER NOT NULL,
                    start_time_ms INTEGER NOT NULL,
                    end_time_ms INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_spotify_id ON songs(spotify_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_status ON songs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_song_id ON trigger_timestamps(song_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_trigger_id ON trigger_timestamps(trigger_id)')
            
            conn.commit()
            print("Database tables created successfully")
    
    def add_new_song(self, song: Song) -> int:
        """Add a new song to the database and return its ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO songs (title, artist, album, duration_ms, status, spotify_id, isrc, lrclib_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                song.title, song.artist, song.album, song.duration_ms,
                song.status.value, song.spotify_id, song.isrc, song.lrclib_id
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_song(self, song_id: int) -> Optional[Song]:
        """Get a song by its ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM songs WHERE id = ?', (song_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_song(row)
            return None
    
    def get_song_by_spotify_id(self, spotify_id: str) -> Optional[Song]:
        """Get a song by its Spotify ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM songs WHERE spotify_id = ?', (spotify_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_song(row)
            return None
    
    def update_song_status(self, song_id: int, status: SongStatus) -> bool:
        """Update the status of a song"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE songs SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (status.value, song_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_trigger_of_song(self, trigger: TriggerTimestamp) -> int:
        """Add a trigger timestamp for a song and return its ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trigger_timestamps 
                (trigger_id, song_id, start_time_ms, end_time_ms)
                VALUES (?, ?, ?, ?)
            ''', (
                trigger.trigger_id, trigger.song_id, trigger.start_time_ms,
                trigger.end_time_ms
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_triggers_of_song(self, song_id: int) -> List[TriggerTimestamp]:
        """Get all trigger timestamps for a specific song"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM trigger_timestamps 
                WHERE song_id = ? 
                ORDER BY start_time_ms
            ''', (song_id,))
            rows = cursor.fetchall()
            return [self._row_to_trigger(row) for row in rows]
    
    def get_triggers_by_category(self, trigger_id: int) -> List[TriggerTimestamp]:
        """Get all trigger timestamps for a specific trigger category"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tt.*, s.title, s.artist, s.album
                FROM trigger_timestamps tt
                JOIN songs s ON tt.song_id = s.id
                WHERE tt.trigger_id = ?
                ORDER BY s.title, tt.start_time_ms
            ''', (trigger_id,))
            rows = cursor.fetchall()
            return [self._row_to_trigger(row) for row in rows]
    
    def delete_triggers_by_category(self, trigger_id: int) -> int:
        """Delete all trigger timestamps for a specific trigger category"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM trigger_timestamps WHERE trigger_id = ?', (trigger_id,))
            conn.commit()
            return cursor.rowcount
    
    def get_contaminated_songs(self) -> List[Song]:
        """Get all songs that have been scanned and found to contain triggers"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM songs 
                WHERE status = ? 
                ORDER BY title, artist
            ''', (SongStatus.SCANNED_CONTAMINATED.value,))
            rows = cursor.fetchall()
            return [self._row_to_song(row) for row in rows]
    
    def get_unscanned_songs(self) -> List[Song]:
        """Get all songs that haven't been scanned yet"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM songs 
                WHERE status = ? 
                ORDER BY created_at
            ''', (SongStatus.NOT_SCANNED.value,))
            rows = cursor.fetchall()
            return [self._row_to_song(row) for row in rows]
    
    def search_songs(self, query: str) -> List[Song]:
        """Search songs by title, artist, or album"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            like_query = f"%{query}%"
            cursor.execute('''
                SELECT * FROM songs 
                WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
                ORDER BY title, artist
            ''', (like_query, like_query, like_query))
            rows = cursor.fetchall()
            return [self._row_to_song(row) for row in rows]
    
    def get_song_count(self) -> int:
        """Get total number of songs in database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM songs')
            return cursor.fetchone()[0]
    
    def get_trigger_count(self) -> int:
        """Get total number of trigger timestamps in database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM trigger_timestamps')
            return cursor.fetchone()[0]
    
    def _row_to_song(self, row) -> Song:
        """Convert database row to Song dataclass"""
        return Song(
            id=row['id'],
            title=row['title'],
            artist=row['artist'],
            album=row['album'],
            duration_ms=row['duration_ms'],
            status=SongStatus(row['status']),
            spotify_id=row['spotify_id'],
            isrc=row['isrc'],
            lrclib_id=row['lrclib_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
    
    def _row_to_trigger(self, row) -> TriggerTimestamp:
        """Convert database row to TriggerTimestamp dataclass"""
        return TriggerTimestamp(
            id=row['id'],
            trigger_id=row['trigger_id'],
            song_id=row['song_id'],
            start_time_ms=row['start_time_ms'],
            end_time_ms=row['end_time_ms'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )


# Convenience function to get a database instance
def get_database() -> DatabaseManager:
    """Get a database manager instance"""
    return DatabaseManager()


if __name__ == "__main__":
    # Test the database creation
    print("Testing database creation...")
    db = get_database()
    
    # Test adding a song
    test_song = Song(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration_ms=180000,
        spotify_id="test_spotify_id_123"
    )
    
    song_id = db.add_new_song(test_song)
    print(f"Added test song with ID: {song_id}")
    
    # Test retrieving the song
    retrieved_song = db.get_song(song_id)
    print(f"Retrieved song: {retrieved_song.title} by {retrieved_song.artist}")
    
    # Test adding a trigger
    test_trigger = TriggerTimestamp(
        trigger_id=1,
        song_id=song_id,
        start_time_ms=60000,
        end_time_ms=65000
    )
    
    trigger_id = db.add_trigger_of_song(test_trigger)
    print(f"Added test trigger with ID: {trigger_id}")
    
    # Test retrieving triggers
    triggers = db.get_triggers_of_song(song_id)
    print(f"Found {len(triggers)} triggers for song")
    
    print("Database test completed successfully!")
