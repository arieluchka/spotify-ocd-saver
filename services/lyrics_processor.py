import re
from typing import List, Tuple, Optional
from config.models import SyncedLyricsLine, TriggerTimestamp
from services.trigger_service.trigger_service import TriggerService


def parse_lrc_timestamp(timestamp_str: str) -> int:
    # Remove brackets and split
    timestamp_str = timestamp_str.strip('[]')
    parts = timestamp_str.split(':')
    minutes = int(parts[0])
    
    # Handle seconds and centiseconds
    seconds_part = parts[1].split('.')
    seconds = int(seconds_part[0])
    centiseconds = int(seconds_part[1]) if len(seconds_part) > 1 else 0
    
    # Convert to milliseconds
    total_ms = (minutes * 60 + seconds) * 1000 + centiseconds * 10
    return total_ms


def parse_synced_lyrics_to_lines(synced_lyrics: str) -> List[SyncedLyricsLine]:
    lyrics_lines = []
    
    if not synced_lyrics:
        return lyrics_lines
    
    # Split lyrics into lines
    lines = synced_lyrics.strip().split('\n')
    
    for line in lines:
        if not line.strip() or not line.startswith('['):
            continue
            
        try:
            # Extract timestamp and lyrics text
            timestamp_match = re.match(r'\[([^\]]+)\](.*)$', line)
            if not timestamp_match:
                continue
                
            timestamp_str = timestamp_match.group(1)
            lyrics_text = timestamp_match.group(2).strip()
            
            if not lyrics_text:  # Skip empty lines
                continue
            
            start_timestamp = parse_lrc_timestamp(timestamp_str)
            lyrics_lines.append(SyncedLyricsLine(
                start_timestamp=start_timestamp,
                line=lyrics_text
            ))
            
        except Exception as e:
            # Skip problematic lines
            continue
    
    # Sort by timestamp to ensure proper order
    lyrics_lines.sort(key=lambda x: x.start_timestamp)
    return lyrics_lines


def search_synced_lyrics_for_triggers(
    synced_lyrics_lines: List[SyncedLyricsLine],
    trigger_service: TriggerService,
    user_id: Optional[int] = None,
    buffer_ms: int = 5000
) -> List[Tuple[int, int, int, str]]:  # Returns (start_time, end_time, category_id, trigger_word)
    trigger_timestamps = []
    
    for i, lyrics_line in enumerate(synced_lyrics_lines):
        # Find all triggers in this line
        triggers_found = trigger_service.find_triggers_in_text(lyrics_line.line, user_id)
        
        if triggers_found:
            start_time_ms = lyrics_line.start_timestamp
            
            # Find end time by looking at next line's timestamp
            end_time_ms = start_time_ms + buffer_ms  # Default buffer
            
            # Try to find the next line's timestamp
            if i + 1 < len(synced_lyrics_lines):
                end_time_ms = synced_lyrics_lines[i + 1].start_timestamp
            
            # Group triggers by category for this line, keeping track of trigger words
            categories_found = {}
            for trigger in triggers_found:
                category_id = trigger['category_id']
                if category_id not in categories_found:
                    categories_found[category_id] = set()
                categories_found[category_id].add(trigger['word'])
            
            for category_id, words in categories_found.items():
                # Join multiple words found in the same line
                trigger_word = ', '.join(sorted(words))
                trigger_timestamps.append((start_time_ms, end_time_ms, category_id, trigger_word))
    
    # Combine nearby trigger timestamps for each category (less than 5 seconds apart)
    if trigger_timestamps:
        # Group by category and trigger word combination
        triggers_by_category = {}
        for start_time, end_time, category_id, trigger_word in trigger_timestamps:
            key = (category_id, trigger_word)
            if key not in triggers_by_category:
                triggers_by_category[key] = []
            triggers_by_category[key].append((start_time, end_time))
        
        # Combine nearby triggers for each category/word combination
        combined_timestamps = []
        for (category_id, trigger_word), timestamps in triggers_by_category.items():
            # Sort timestamps by start time
            timestamps.sort(key=lambda x: x[0])
            
            # Combine nearby triggers
            category_combined = []
            current_start, current_end = timestamps[0]
            
            for i in range(1, len(timestamps)):
                next_start, next_end = timestamps[i]
                
                # If less than 5 seconds between end of current and start of next
                if next_start - current_end < 5000:
                    # Extend current trigger to include the next one
                    current_end = max(current_end, next_end)
                else:
                    # Gap is too large, save current trigger and start new one
                    category_combined.append((current_start, current_end, category_id, trigger_word))
                    current_start, current_end = next_start, next_end
            
            # Don't forget the last trigger
            category_combined.append((current_start, current_end, category_id, trigger_word))
            combined_timestamps.extend(category_combined)
        
        trigger_timestamps = combined_timestamps
    
    return trigger_timestamps


def search_plain_lyrics_for_triggers(
    lyrics_text: str,
    trigger_service: TriggerService,
    user_id: Optional[int] = None
) -> bool:
    if not lyrics_text:
        return False
    
    return trigger_service.has_triggers(lyrics_text, user_id)


def create_trigger_timestamps_from_synced_lyrics(
    synced_lyrics: str,
    song_id: int,
    trigger_service: TriggerService,
    user_id: Optional[int] = None
) -> List[TriggerTimestamp]:
    # Parse synced lyrics
    lyrics_lines = parse_synced_lyrics_to_lines(synced_lyrics)
    
    # Find trigger timestamps
    trigger_ranges = search_synced_lyrics_for_triggers(lyrics_lines, trigger_service, user_id)
    
    # Create TriggerTimestamp objects
    trigger_timestamps = []
    for start_time_ms, end_time_ms, category_id, trigger_word in trigger_ranges:
        trigger_timestamps.append(TriggerTimestamp(
            user_id=user_id,
            song_id=song_id,
            category_id=category_id,  # Use category_id to match database schema
            trigger_word=trigger_word,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms
        ))
    
    return trigger_timestamps