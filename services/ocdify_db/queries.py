"""
Centralized SQL queries for the OCDify database.
All SQL statements are organized here for better maintainability.
"""

# Table creation queries
CREATE_USERS_TABLE = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spotify_user_id TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        access_token TEXT,
        refresh_token TEXT,
        token_expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''

CREATE_TRIGGER_CATEGORIES_TABLE = '''
    CREATE TABLE IF NOT EXISTS trigger_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        words TEXT DEFAULT '[]',
        user_id INTEGER,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE(name, user_id)
    )
'''

CREATE_SONGS_TABLE = '''
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
        not_sync_lrclib_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''

CREATE_TRIGGER_TIMESTAMPS_TABLE = '''
    CREATE TABLE IF NOT EXISTS trigger_timestamps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        song_id INTEGER NOT NULL,
        user_id INTEGER,
        start_time_ms INTEGER NOT NULL,
        end_time_ms INTEGER NOT NULL,
        trigger_word TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES trigger_categories (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
'''

# Index creation queries
INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_users_spotify_id ON users(spotify_user_id)',
    'CREATE INDEX IF NOT EXISTS idx_trigger_categories_user_id ON trigger_categories(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_trigger_categories_active ON trigger_categories(is_active)',
    'CREATE INDEX IF NOT EXISTS idx_songs_spotify_id ON songs(spotify_id)',
    'CREATE INDEX IF NOT EXISTS idx_songs_status ON songs(status)',
    'CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_song_id ON trigger_timestamps(song_id)',
    'CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_category_id ON trigger_timestamps(category_id)',
    'CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_user_id ON trigger_timestamps(user_id)',
]

# User queries
INSERT_USER = '''
    INSERT INTO users (spotify_user_id, display_name, access_token, refresh_token, token_expires_at)
    VALUES (?, ?, ?, ?, ?)
'''

SELECT_USER_BY_SPOTIFY_ID = 'SELECT * FROM users WHERE spotify_user_id = ?'

UPDATE_USER_TOKENS = '''
    UPDATE users SET access_token = ?, refresh_token = ?, token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
'''

# Song queries
INSERT_SONG = '''
    INSERT INTO songs (title, artist, album, duration_ms, status, spotify_id, isrc, lrclib_id, not_sync_lrclib_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

SELECT_SONG_BY_ID = 'SELECT * FROM songs WHERE id = ?'
SELECT_SONG_BY_SPOTIFY_ID = 'SELECT * FROM songs WHERE spotify_id = ?'

UPDATE_SONG_STATUS = '''
    UPDATE songs SET status = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE id = ?
'''

UPDATE_SONG_NOT_SYNC_LRCLIB_ID = '''
    UPDATE songs SET not_sync_lrclib_id = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE id = ?
'''

SELECT_CONTAMINATED_SONGS = '''
    SELECT * FROM songs 
    WHERE status = ? 
    ORDER BY title, artist
'''

SELECT_UNSCANNED_SONGS = '''
    SELECT * FROM songs 
    WHERE status = ? 
    ORDER BY created_at
'''

SEARCH_SONGS = '''
    SELECT * FROM songs 
    WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
    ORDER BY title, artist
'''

COUNT_SONGS = 'SELECT COUNT(*) FROM songs'

# Trigger category queries
INSERT_TRIGGER_CATEGORY = '''
    INSERT INTO trigger_categories (name, words, user_id, is_active)
    VALUES (?, ?, ?, ?)
'''

SELECT_TRIGGER_CATEGORIES_GLOBAL = '''
    SELECT * FROM trigger_categories 
    WHERE user_id IS NULL AND is_active = 1
    ORDER BY name
'''

SELECT_TRIGGER_CATEGORIES_USER_AND_GLOBAL = '''
    SELECT * FROM trigger_categories 
    WHERE (user_id = ? OR user_id IS NULL) AND is_active = 1
    ORDER BY user_id IS NULL, name
'''

SELECT_TRIGGER_CATEGORIES_USER_ONLY = '''
    SELECT * FROM trigger_categories 
    WHERE user_id = ? AND is_active = 1
    ORDER BY name
'''

SELECT_TRIGGER_CATEGORY_BY_ID = 'SELECT * FROM trigger_categories WHERE id = ?'

UPDATE_TRIGGER_CATEGORY = '''
    UPDATE trigger_categories 
    SET name = ?, words = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ? AND user_id = ?
'''

# Trigger timestamp queries
INSERT_TRIGGER_TIMESTAMP = '''
    INSERT INTO trigger_timestamps (user_id, song_id, category_id, trigger_word, timestamp_ms)
    VALUES (?, ?, ?, ?, ?)
'''

SELECT_TRIGGER_TIMESTAMPS_BY_USER = '''
    SELECT * FROM trigger_timestamps 
    WHERE user_id = ?
    ORDER BY created_at DESC
'''

SELECT_TRIGGER_TIMESTAMPS_BY_SONG = '''
    SELECT * FROM trigger_timestamps 
    WHERE song_id = ? AND user_id = ?
    ORDER BY timestamp_ms
'''

SELECT_TRIGGERS_BY_CATEGORY = '''
    SELECT tt.*, s.title, s.artist, s.album
    FROM trigger_timestamps tt
    JOIN songs s ON tt.song_id = s.id
    WHERE tt.category_id = ? AND tt.user_id = ?
    ORDER BY s.title, tt.timestamp_ms
'''

DELETE_TRIGGERS_BY_CATEGORY = 'DELETE FROM trigger_timestamps WHERE category_id = ? AND user_id = ?'

COUNT_TRIGGER_TIMESTAMPS = 'SELECT COUNT(*) FROM trigger_timestamps'

# Migration queries
CHECK_TABLE_INFO = "PRAGMA table_info(?)"
CHECK_EXISTING_TABLES = "SELECT name FROM sqlite_master WHERE type='table'"

ADD_NOT_SYNC_LRCLIB_ID_COLUMN = 'ALTER TABLE songs ADD COLUMN not_sync_lrclib_id TEXT'

COUNT_TRIGGER_CATEGORIES = 'SELECT COUNT(*) FROM trigger_categories'