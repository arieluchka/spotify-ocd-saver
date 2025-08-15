- document the lrclib id of found lyricses in the db
- add to songs table column for not_sync_lrclib_id and allow to be null (if no sync lyrics found, try to find regular lyrics and search it for trigger words)

- create a dataclass for synced lyrics line (with start_timestamp, line)
- create a dataclass for trigger_timestamp (start_timestamp, end_timestamp, created_at)

- have 2 functions for searching a lyrics
    - 1) will get a synced lyrics array and return an array for trigger_timestamps.
    - 2) will get the entire lyrics and return True/False if it found a trigger word in there.