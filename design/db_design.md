# Database Design Documentation

## Overview

The OCDify database is an SQLite database designed to support a Spotify monitoring service that helps users avoid songs containing triggering words. The system scans song lyrics for user-defined trigger words and provides detailed information about where these triggers occur within songs.

## Database Schema

### Core Entities

The database consists of 4 main tables that work together to provide comprehensive trigger word detection and user management:

1. **users** - User authentication and Spotify integration
2. **songs** - Song metadata and general lyrics availability status
3. **trigger_categories** - User-defined categories of trigger words
4. **trigger_timestamps** - Specific occurrences of trigger words in songs

---

## Table Specifications

### 1. `users` Table

**Purpose**: Manages user accounts and Spotify API authentication tokens.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique user identifier |
| `spotify_user_id` | TEXT | UNIQUE NOT NULL | Spotify's unique user ID |
| `display_name` | TEXT | NOT NULL | User's display name from Spotify |
| `access_token` | TEXT | NULL | Spotify API access token (encrypted) |
| `refresh_token` | TEXT | NULL | Spotify API refresh token (encrypted) |
| `token_expires_at` | TIMESTAMP | NULL | When the access token expires |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last account update timestamp |

**Role**: 
- Stores Spotify authentication credentials for API access
- Enables user-specific trigger categories and personalized scanning
- Supports multi-user functionality with isolated data per user

**Key Features**:
- Automatic token management for Spotify API integration
- Secure token storage (encrypted in application layer)
- User isolation for privacy and data separation

---

### 2. `songs` Table

**Purpose**: Stores song metadata and tracks lyrics availability (user-agnostic).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique song identifier |
| `title` | TEXT | NOT NULL | Song title |
| `artist` | TEXT | NOT NULL | Primary artist name |
| `album` | TEXT | NOT NULL | Album name |
| `duration_ms` | INTEGER | NOT NULL | Song duration in milliseconds |
| `status` | INTEGER | NOT NULL DEFAULT 0 | Lyrics status (see SongStatus enum) |
| `spotify_id` | TEXT | UNIQUE | Spotify's unique track ID |
| `isrc` | TEXT | NULL | International Standard Recording Code |
| `lrclib_id` | TEXT | NULL | LRCLib ID for synced lyrics |
| `not_sync_lrclib_id` | TEXT | NULL | LRCLib ID for non-synced lyrics |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When song was added to database |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last song update timestamp |

**Status Values** (SongStatus enum):
- `0` - NOT_SCANNED: Lyrics have not been attempted
- `1` - NO_RESULTS: No lyrics were found
- `2` - PLAIN_LYRICS: Plain (unsynced) lyrics available
- `3` - SYNC_LYRICS: Synced (timestamped) lyrics available

**Role**:
- Central repository for all song information
- Tracks scanning progress to avoid duplicate processing
- Links songs to multiple lyrics sources (LRCLib synced/unsynced)
- Provides metadata for trigger reporting and user interface

**Key Features**:
- Dual lyrics support (synced timestamps vs. plain text)
- Status tracking prevents redundant scanning
- Spotify integration via spotify_id
- ISRC support for cross-platform song identification

---

### 3. `trigger_categories` Table

**Purpose**: Manages user-defined categories of trigger words that can be activated/deactivated independently.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique category identifier |
| `name` | TEXT | NOT NULL | Category name (e.g., "Violence", "Explicit Language") |
| `words` | TEXT | DEFAULT '[]' | JSON array of trigger words |
| `user_id` | INTEGER | NULL, FK to users(id) | Owner user (NULL = global category) |
| `is_active` | BOOLEAN | DEFAULT 1 | Whether category is currently enabled |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Category creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last category modification timestamp |

**Constraints**:
- `FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE`
- `UNIQUE(name, user_id)` - Prevents duplicate category names per user

**Role**:
- Flexible trigger word organization by theme/category
- Support for both global (system-wide) and user-specific categories
- Dynamic word list management via JSON storage
- Granular control over which trigger types are active

**Key Features**:
- Hierarchical trigger management (global vs. personal)
- JSON word storage allows dynamic list sizes
- Toggle activation without deleting categories
- User isolation with cascade deletion

---

### 4. `trigger_timestamps` Table

**Purpose**: Records specific instances where trigger words were found in songs, including precise timing information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique trigger instance identifier |
| `category_id` | INTEGER | NOT NULL, FK to trigger_categories(id) | Which category triggered |
| `song_id` | INTEGER | NOT NULL, FK to songs(id) | Which song contains the trigger |
| `user_id` | INTEGER | NULL, FK to users(id) | Which user's scan detected this |
| `start_time_ms` | INTEGER | NOT NULL | When trigger word starts (milliseconds) |
| `end_time_ms` | INTEGER | NOT NULL | When trigger word ends (milliseconds) |
| `trigger_word` | TEXT | NULL | The specific word that triggered |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When trigger was detected |

**Foreign Key Constraints**:
- `FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE`
- `FOREIGN KEY (category_id) REFERENCES trigger_categories (id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE`

**Role**:
- Detailed logging of every trigger word occurrence
- Precise timing for skip/mute functionality
- User-specific trigger tracking
- Historical record of all detections

**Key Features**:
- Millisecond precision for audio timing
- Multi-user trigger isolation
- Cascading deletion maintains data integrity
- Links triggers to both songs and categories

---

## Database Relationships

### Entity Relationship Diagram (Conceptual)

```
users (1) ──── (0..n) trigger_categories
  │                      │
  │                      │
  │                      │ (1)
  │                      │
  │                      ▼ (0..n)
  │ (0..n)        trigger_timestamps
  │                      ▲ (0..n)
  │                      │
  │                      │ (1)
  │                      │
  └────── songs (1) ──────┘
```

### Relationship Details

1. **users → trigger_categories** (1:N)
   - Users can create multiple personal trigger categories
   - Global categories exist without user ownership (user_id = NULL)

2. **users → trigger_timestamps** (1:N) 
   - Each trigger detection is associated with the user who owns the category
   - Enables user-specific scanning results

3. **songs → trigger_timestamps** (1:N)
   - One song can have multiple trigger occurrences
   - Each trigger points to exact timing within the song

4. **trigger_categories → trigger_timestamps** (1:N)
   - Each trigger occurrence belongs to exactly one category
   - Category deletion removes all associated triggers

---

## Indexes and Performance

### Implemented Indexes

The database includes several indexes for optimal query performance:

```sql
-- User lookups
CREATE INDEX idx_users_spotify_id ON users(spotify_user_id)

-- Trigger category queries
CREATE INDEX idx_trigger_categories_user_id ON trigger_categories(user_id)
CREATE INDEX idx_trigger_categories_active ON trigger_categories(is_active)

-- Song searches
CREATE INDEX idx_songs_spotify_id ON songs(spotify_id)
CREATE INDEX idx_songs_status ON songs(status)

-- Trigger timestamp lookups
CREATE INDEX idx_trigger_timestamps_song_id ON trigger_timestamps(song_id)
CREATE INDEX idx_trigger_timestamps_category_id ON trigger_timestamps(category_id)
CREATE INDEX idx_trigger_timestamps_user_id ON trigger_timestamps(user_id)
```

### Performance Considerations

- **Spotify ID lookups**: Fast user authentication and song identification
- **Status filtering**: Quick access to unscanned songs for batch processing
- **User isolation**: Efficient filtering of user-specific data
- **Trigger analysis**: Fast aggregation of triggers by song or category

---

## Data Flow and Usage Patterns

### 1. User Registration Flow
1. User authenticates with Spotify OAuth
2. User record created in `users` table with Spotify tokens
3. User can create personal `trigger_categories`
4. Global categories are automatically available

### 2. Song Scanning Flow
1. New song detected → added to `songs` table with status `NOT_SCANNED`
2. Lyrics fetched from LRCLib or other sources
3. Song scanned against active `trigger_categories` per-user
4. `trigger_timestamps` created for each detection
5. Per-user status updated to `SCANNED_CLEAN` or `SCANNED_CONTAMINATED` with `sync` flag

### 3. Playback Monitoring Flow
1. Current song identified by `spotify_id`
2. Query `trigger_timestamps` for active user categories
3. Real-time trigger warnings based on `start_time_ms`/`end_time_ms`
4. Skip/mute actions triggered as needed

### 4. User Management Flow
1. Users can activate/deactivate categories via `is_active` flag
2. Category word updates trigger deletion of old `trigger_timestamps`
3. New scanning required for songs with updated categories
4. User deletion cascades to remove all personal data

---

## Migration and Schema Evolution

### Current Migration Support
- Automatic detection of missing columns
- Graceful addition of `not_sync_lrclib_id` column
- New table creation for existing databases
- Index creation for performance optimization

### Future Schema Considerations
- Support for multiple lyrics sources
- Audio fingerprinting integration
- Enhanced user preferences and settings
- Performance metrics and analytics tables

---

## Security and Privacy

### Data Protection
- Spotify tokens encrypted at application layer
- User data isolation through foreign key constraints
- Cascade deletion ensures complete data removal
- No storage of actual lyrics (only timing references)

### Privacy Features
- User-specific trigger categories
- Personal scanning history
- Option for global vs. personal categories
- Complete data deletion on user account removal

---

## Summary

The OCDify database design provides a robust foundation for trigger word detection in music streaming. The schema balances performance, flexibility, and user privacy while supporting real-time monitoring and detailed trigger analysis. The modular design allows for future expansion while maintaining data integrity and user isolation.