## ✅ COMPLETED TASKS

- ✅ document the lrclib id of found lyricses in the db
- ✅ add to songs table column for not_sync_lrclib_id and allow to be null (if no sync lyrics found, try to find regular lyrics and search it for trigger words)

- ✅ create a dataclass for synced lyrics line (with start_timestamp, line)
- ✅ create a dataclass for trigger_timestamp (start_timestamp, end_timestamp, created_at)

- ✅ have 2 functions for searching a lyrics
    - 1) will get a synced lyrics array and return an array for trigger_timestamps.
    - 2) will get the entire lyrics and return True/False if it found a trigger word in there.

- ✅ dont merge timestamps that are close to each other in the db, but calculate it when fetching it from the db

- ✅ dockerize the application so it can be deployed on a headless machine

- ✅ **NEW:** add background queue scanning thread that runs every 300 seconds to analyze unscanned songs in the Spotify queue

## Implementation Summary

### 1. Database Schema Updates
- Added `not_sync_lrclib_id` column to songs table
- Implemented automatic database migration for existing databases
- Added database method to update non-synced lyrics ID

### 2. New Data Models
- Created `SyncedLyricsLine` dataclass with `start_timestamp` and `line` properties
- Verified `TriggerTimestamp` dataclass has correct structure (start_time_ms, end_time_ms, created_at)

### 3. Lyrics Processing Module
- Created `services/lyrics_processor.py` with comprehensive lyrics analysis functions
- `search_synced_lyrics_for_triggers()`: Processes synced lyrics and returns trigger timestamps
- `search_plain_lyrics_for_triggers()`: Analyzes plain text lyrics for trigger words
- `create_trigger_timestamps_from_synced_lyrics()`: Creates TriggerTimestamp objects from synced lyrics
- Timestamp merging is handled during analysis (not stored merged in DB)

### 4. Docker Containerization
- Created `Dockerfile` with Python 3.10 base image
- Added `docker-compose.yml` for easy deployment
- Created `.dockerignore` for optimized builds
- Added comprehensive `DOCKER_README.md` with deployment instructions
- Container runs as non-root user for security
- Includes health checks and proper volume mounting

### 5. Queue Scanning Feature
- Added `queue_scanning_thread()` that runs every 300 seconds (5 minutes)
- Automatically scans Spotify queue for new songs and adds them to database
- Triggers background analysis for unscanned songs found in queue
- Uses `user-read-currently-playing` scope for queue access
- Prevents duplicate scanning and handles error cases gracefully

### 6. Code Refactoring
- Updated main.py to use new lyrics processor module
- Removed duplicate lyrics processing code
- Enhanced scanning logic to handle both synced and plain lyrics
- Added proper error handling and logging
- Fixed sqlite3.Row compatibility issue for new database columns

All tasks have been successfully implemented and tested!