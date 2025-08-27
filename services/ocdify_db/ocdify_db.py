import sqlite3
import os
from typing import List, Optional
from contextlib import contextmanager
from datetime import datetime

from common.models.models import Song, TriggerTimestamp, SongStatus, User, TriggerCategory
from .queries import *


class OCDifyDb:
    def __init__(self, db_path: str = "spotify_ocd_saver.db"):
        self.db_path = db_path
        self.ensure_database_exists()

    def ensure_database_exists(self):
        if not os.path.exists(self.db_path):
            print(f"Creating new database: {self.db_path}")
            self.create_tables()
        else:
            print(f"Using existing database: {self.db_path}")
            self.migrate_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create all tables
            cursor.execute(CREATE_USERS_TABLE)
            cursor.execute(CREATE_TRIGGER_CATEGORIES_TABLE)
            cursor.execute(CREATE_SONGS_TABLE)
            cursor.execute(CREATE_TRIGGER_TIMESTAMPS_TABLE)

            # Create indexes
            for index_query in INDEXES:
                cursor.execute(index_query)

            conn.commit()
            print("Database tables created successfully")

    def migrate_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if not_sync_lrclib_id column exists in songs table
            cursor.execute("PRAGMA table_info(songs)")
            songs_columns = [column[1] for column in cursor.fetchall()]

            if 'not_sync_lrclib_id' not in songs_columns:
                print("Adding not_sync_lrclib_id column to songs table...")
                cursor.execute(ADD_NOT_SYNC_LRCLIB_ID_COLUMN)
                conn.commit()
                print("Migration completed: Added not_sync_lrclib_id column")

            # Check if new tables exist
            cursor.execute(CHECK_EXISTING_TABLES)
            existing_tables = [table[0] for table in cursor.fetchall()]

            # Create new tables if they don't exist
            if 'users' not in existing_tables:
                print("Creating users table...")
                cursor.execute(CREATE_USERS_TABLE)
            if 'trigger_categories' not in existing_tables:
                print("Creating trigger_categories table...")
                cursor.execute(CREATE_TRIGGER_CATEGORIES_TABLE)

            # Ensure all tables and indexes exist (for partial migrations)
            self.create_tables()
            
            conn.commit()
            print("Database migration completed")

    def add_new_song(self, song: Song) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(INSERT_SONG, (
                song.title, song.artist, song.album, song.duration_ms,
                song.status.value, song.spotify_id, song.isrc, song.lrclib_id, song.not_sync_lrclib_id
            ))
            conn.commit()
            return cursor.lastrowid

    def get_song(self, song_id: int) -> Optional[Song]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_SONG_BY_ID, (song_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_song(row)
            return None

    def get_song_by_spotify_id(self, spotify_id: str) -> Optional[Song]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_SONG_BY_SPOTIFY_ID, (spotify_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_song(row)
            return None

    def update_song_status(self, song_id: int, status: SongStatus) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(UPDATE_SONG_STATUS, (status.value, song_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_song_not_sync_lrclib_id(self, song_id: int, not_sync_lrclib_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(UPDATE_SONG_NOT_SYNC_LRCLIB_ID, (not_sync_lrclib_id, song_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_song_lrclib_id(self, song_id: int, lrclib_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(UPDATE_SONG_LRCLIB_ID, (lrclib_id, song_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_song_isrc(self, song_id: int, isrc: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(UPDATE_SONG_ISRC, (isrc, song_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_trigger_of_song(self, trigger: TriggerTimestamp) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(INSERT_TRIGGER_TIMESTAMP, (
                trigger.user_id, trigger.song_id, trigger.category_id,
                trigger.trigger_word, trigger.start_time_ms, trigger.end_time_ms
            ))
            conn.commit()
            return cursor.lastrowid

    def get_triggers_of_song(self, song_id: int, user_id: int) -> List[TriggerTimestamp]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_TRIGGER_TIMESTAMPS_BY_SONG, (song_id, user_id))
            rows = cursor.fetchall()
            return [self._row_to_trigger(row) for row in rows]

    def get_triggers_by_category(self, category_id: int, user_id: int) -> List[TriggerTimestamp]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_TRIGGERS_BY_CATEGORY, (category_id, user_id))
            rows = cursor.fetchall()
            return [self._row_to_trigger(row) for row in rows]

    def delete_triggers_by_category(self, category_id: int, user_id: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(DELETE_TRIGGERS_BY_CATEGORY, (category_id, user_id))
            conn.commit()
            return cursor.rowcount

    def get_contaminated_songs(self) -> List[Song]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_CONTAMINATED_SONGS, (SongStatus.SCANNED_CONTAMINATED.value,))
            rows = cursor.fetchall()
            return [self._row_to_song(row) for row in rows]

    def get_unscanned_songs(self) -> List[Song]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_UNSCANNED_SONGS, (SongStatus.NOT_SCANNED.value,))
            rows = cursor.fetchall()
            return [self._row_to_song(row) for row in rows]

    def search_songs(self, query: str) -> List[Song]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            like_query = f"%{query}%"
            cursor.execute(SEARCH_SONGS, (like_query, like_query, like_query))
            rows = cursor.fetchall()
            return [self._row_to_song(row) for row in rows]

    def get_song_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(COUNT_SONGS)
            return cursor.fetchone()[0]

    def get_trigger_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(COUNT_TRIGGER_TIMESTAMPS)
            return cursor.fetchone()[0]

    # User management methods
    def add_user(self, user: User) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(INSERT_USER, (user.spotify_user_id, user.display_name, user.access_token, user.refresh_token, user.token_expires_at))
            conn.commit()
            return cursor.lastrowid

    def get_user_by_spotify_id(self, spotify_user_id: str) -> Optional[User]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_USER_BY_SPOTIFY_ID, (spotify_user_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_user(row)
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_USER_BY_ID, (user_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_user(row)
            return None

    def update_user_tokens(self, user_id: int, access_token: str, refresh_token: str, expires_at: datetime) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(UPDATE_USER_TOKENS, (access_token, refresh_token, expires_at, user_id))
            conn.commit()
            return cursor.rowcount > 0

    # Trigger category management methods
    def add_trigger_category(self, category: TriggerCategory) -> int:
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            words_json = json.dumps(category.words)
            cursor.execute(INSERT_TRIGGER_CATEGORY, (category.name, words_json, category.user_id, category.is_active))
            conn.commit()
            return cursor.lastrowid

    def get_trigger_categories(self, user_id: Optional[int] = None, include_global: bool = True) -> List[TriggerCategory]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id is None:
                cursor.execute(SELECT_TRIGGER_CATEGORIES_GLOBAL)
            elif include_global:
                cursor.execute(SELECT_TRIGGER_CATEGORIES_USER_AND_GLOBAL, (user_id,))
            else:
                cursor.execute(SELECT_TRIGGER_CATEGORIES_USER_ONLY, (user_id,))
            
            rows = cursor.fetchall()
            return [self._row_to_trigger_category(row) for row in rows]

    def get_trigger_category_by_id(self, category_id: int) -> Optional[TriggerCategory]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_TRIGGER_CATEGORY_BY_ID, (category_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_trigger_category(row)
            return None

    def update_trigger_category(self, category_id: int, name: str, words: List[str], is_active: bool, user_id: int) -> bool:
        import json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            words_json = json.dumps(words)
            cursor.execute(UPDATE_TRIGGER_CATEGORY, (name, words_json, is_active, category_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_song(self, row) -> Song:
        # Handle the case where not_sync_lrclib_id might not exist in older DB schemas
        try:
            not_sync_lrclib_id = row['not_sync_lrclib_id']
        except (IndexError, KeyError):
            not_sync_lrclib_id = None

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
            not_sync_lrclib_id=not_sync_lrclib_id,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

    def _row_to_trigger(self, row) -> TriggerTimestamp:
        # Handle optional columns that might not exist in all queries
        try:
            user_id = row['user_id']
        except (IndexError, KeyError):
            user_id = None
        
        try:
            trigger_word = row['trigger_word']
        except (IndexError, KeyError):
            trigger_word = None
            
        return TriggerTimestamp(
            id=row['id'],
            category_id=row['category_id'],  # Use category_id directly from database
            song_id=row['song_id'],
            user_id=user_id,
            start_time_ms=row['start_time_ms'],
            end_time_ms=row['end_time_ms'],
            trigger_word=trigger_word,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

    def _row_to_user(self, row) -> User:
        return User(
            id=row['id'],
            spotify_user_id=row['spotify_user_id'],
            display_name=row['display_name'],
            access_token=row['access_token'],
            refresh_token=row['refresh_token'],
            token_expires_at=datetime.fromisoformat(row['token_expires_at']) if row['token_expires_at'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

    def _row_to_trigger_category(self, row) -> TriggerCategory:
        import json
        words = json.loads(row['words']) if row['words'] else []
        return TriggerCategory(
            id=row['id'],
            name=row['name'],
            words=words,
            user_id=row['user_id'],
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )


def get_database() -> OCDifyDb:
    return OCDifyDb()


