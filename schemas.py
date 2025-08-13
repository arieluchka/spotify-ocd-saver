"""
SQL schemas and queries for Spotify OCD Saver database
Contains all table creation statements and common queries
"""

# Table creation statements
CREATE_TRIGGER_WORD_CATEGORIES_TABLE = """
    CREATE TABLE IF NOT EXISTS trigger_word_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_TRIGGER_WORDS_TABLE = """
    CREATE TABLE IF NOT EXISTS trigger_words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES trigger_word_categories(id) ON DELETE CASCADE,
        UNIQUE(word, category_id)
    )
"""

CREATE_STREAMING_SERVICES_TABLE = """
    CREATE TABLE IF NOT EXISTS streaming_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        api_endpoint TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_LYRICS_SERVICES_TABLE = """
    CREATE TABLE IF NOT EXISTS lyrics_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        api_endpoint TEXT,
        is_active BOOLEAN DEFAULT 1,
        priority INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_SONGS_TABLE = """
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        album TEXT,
        duration_ms INTEGER,
        spotify_id TEXT UNIQUE,
        isrc TEXT,
        lrclib_id TEXT,
        lyrics_service_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lyrics_service_id) REFERENCES lyrics_services(id),
        UNIQUE(title, artist, album)
    )
"""

CREATE_TRIGGER_TIMESTAMPS_TABLE = """
    CREATE TABLE IF NOT EXISTS trigger_timestamps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        song_id INTEGER NOT NULL,
        trigger_word_id INTEGER NOT NULL,
        start_time_ms INTEGER NOT NULL,
        end_time_ms INTEGER NOT NULL,
        line_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
        FOREIGN KEY (trigger_word_id) REFERENCES trigger_words(id) ON DELETE CASCADE,
        UNIQUE(song_id, trigger_word_id, start_time_ms)
    )
"""

# Index creation statements
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_songs_spotify_id ON songs(spotify_id)",
    "CREATE INDEX IF NOT EXISTS idx_trigger_words_category ON trigger_words(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_song ON trigger_timestamps(song_id)",
    "CREATE INDEX IF NOT EXISTS idx_trigger_timestamps_word ON trigger_timestamps(trigger_word_id)"
]

# All table creation statements in order
TABLE_CREATION_STATEMENTS = [
    CREATE_TRIGGER_WORD_CATEGORIES_TABLE,
    CREATE_TRIGGER_WORDS_TABLE,
    CREATE_STREAMING_SERVICES_TABLE,
    CREATE_LYRICS_SERVICES_TABLE,
    CREATE_SONGS_TABLE,
    CREATE_TRIGGER_TIMESTAMPS_TABLE
]

# Default data insertion queries
INSERT_DEFAULT_STREAMING_SERVICES = """
    INSERT OR IGNORE INTO streaming_services (name, api_endpoint)
    VALUES (?, ?)
"""

INSERT_DEFAULT_LYRICS_SERVICES = """
    INSERT OR IGNORE INTO lyrics_services (name, api_endpoint, priority)
    VALUES (?, ?, ?)
"""

INSERT_DEFAULT_TRIGGER_CATEGORY = """
    INSERT OR IGNORE INTO trigger_word_categories (name, description)
    VALUES (?, ?)
"""

# Default data
DEFAULT_STREAMING_SERVICES = [
    ("Spotify", "https://api.spotify.com"),
    ("YouTube Music", "https://music.youtube.com"),
]

DEFAULT_LYRICS_SERVICES = [
    ("LRCLib", "https://lrclib.net/api", 1),
    ("Musixmatch", "https://api.musixmatch.com", 2),
    ("Spotify Lyrics API", "https://github.com/akashrchandran/spotify-lyrics-api", 3),
]

DEFAULT_TRIGGER_CATEGORIES = [
    ("General", "General trigger words"),
    ("Profanity", "Profanity and offensive language"),
    ("Violence", "Violence-related content"),
    ("Substance", "Drug and alcohol references"),
]

# Common query patterns
FIND_SONG_BY_SPOTIFY_ID = """
    SELECT * FROM songs WHERE spotify_id = ?
"""

FIND_TRIGGER_WORDS_BY_CATEGORY = """
    SELECT tw.* FROM trigger_words tw
    JOIN trigger_word_categories twc ON tw.category_id = twc.id
    WHERE twc.name = ? AND tw.is_active = 1
"""

FIND_TRIGGER_TIMESTAMPS_FOR_SONG = """
    SELECT tt.*, tw.word, twc.name as category_name
    FROM trigger_timestamps tt
    JOIN trigger_words tw ON tt.trigger_word_id = tw.id
    JOIN trigger_word_categories twc ON tw.category_id = twc.id
    WHERE tt.song_id = ?
    ORDER BY tt.start_time_ms
"""

INSERT_SONG = """
    INSERT OR IGNORE INTO songs 
    (title, artist, album, duration_ms, spotify_id, isrc, lrclib_id, lyrics_service_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

INSERT_TRIGGER_WORD = """
    INSERT OR IGNORE INTO trigger_words (word, category_id)
    VALUES (?, ?)
"""

INSERT_TRIGGER_TIMESTAMP = """
    INSERT OR IGNORE INTO trigger_timestamps 
    (song_id, trigger_word_id, start_time_ms, end_time_ms, line_text)
    VALUES (?, ?, ?, ?, ?)
"""
