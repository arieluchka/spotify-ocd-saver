from typing import List, Optional
import logging
import re
from dataclasses import dataclass

from common.models.models import SyncedLyricsLine
from services.trigger_service.trigger_service import TriggerService

logger = logging.getLogger(__name__)


@dataclass
class TriggerResult:
    """Result of trigger scanning"""
    found: bool
    trigger_word: str
    category_id: int
    line_number: Optional[int] = None  # For unsynced lyrics
    timestamp_ms: Optional[int] = None  # For synced lyrics


class TriggerScannerService:
    """Service for scanning lyrics for trigger words"""
    
    def __init__(self, trigger_service: TriggerService):
        self.trigger_service = trigger_service
    
    def scan_synced_lyrics(
        self, 
        synced_lyrics_lines: List[SyncedLyricsLine], 
        user_id: Optional[int] = None
    ) -> List[TriggerResult]:
        """
        Scan synced lyrics for trigger words and return timestamp information.
        
        Args:
            synced_lyrics_lines: List of synced lyrics lines with timestamps
            user_id: User ID for personalized trigger words
            
        Returns:
            List of TriggerResult objects with timestamp information
        """
        trigger_results = []
        
        # Get active words by category for efficient lookup
        words_by_category = self.trigger_service.get_active_words_by_category(user_id)
        
        for line_idx, lyrics_line in enumerate(synced_lyrics_lines):
            line_text = lyrics_line.line.lower().strip()
            
            if not line_text:
                continue
                
            # Check each category's words
            for category_id, category_data in words_by_category.items():
                words = category_data['words']
                
                for word in words:
                    # Use word boundary regex for accurate matching
                    pattern = r'\b' + re.escape(word.lower()) + r'\b'
                    
                    if re.search(pattern, line_text):
                        trigger_result = TriggerResult(
                            found=True,
                            trigger_word=word,
                            category_id=category_id,
                            timestamp_ms=lyrics_line.start_timestamp
                        )
                        trigger_results.append(trigger_result)
                        
                        logger.info(
                            f"Found trigger word '{word}' in synced lyrics at {lyrics_line.start_timestamp}ms: "
                            f"'{lyrics_line.line.strip()}'"
                        )
        
        logger.info(f"Synced lyrics scan completed. Found {len(trigger_results)} triggers.")
        return trigger_results
    
    def scan_unsynced_lyrics(
        self, 
        lyrics_text: str, 
        user_id: Optional[int] = None
    ) -> List[TriggerResult]:
        """
        Scan unsynced lyrics for trigger words and return line information.
        
        Args:
            lyrics_text: Plain text lyrics
            user_id: User ID for personalized trigger words
            
        Returns:
            List of TriggerResult objects with line number information
        """
        trigger_results = []
        
        if not lyrics_text.strip():
            logger.info("No lyrics text provided for scanning")
            return trigger_results
        
        # Get active words by category for efficient lookup
        words_by_category = self.trigger_service.get_active_words_by_category(user_id)
        
        # Split lyrics into lines
        lines = lyrics_text.split('\n')
        
        for line_idx, line in enumerate(lines, 1):
            line_text = line.lower().strip()
            
            if not line_text:
                continue
                
            # Check each category's words
            for category_id, category_data in words_by_category.items():
                words = category_data['words']
                
                for word in words:
                    # Use word boundary regex for accurate matching
                    pattern = r'\b' + re.escape(word.lower()) + r'\b'
                    
                    if re.search(pattern, line_text):
                        trigger_result = TriggerResult(
                            found=True,
                            trigger_word=word,
                            category_id=category_id,
                            line_number=line_idx
                        )
                        trigger_results.append(trigger_result)
                        
                        logger.info(
                            f"Found trigger word '{word}' in unsynced lyrics at line {line_idx}: "
                            f"'{line.strip()}'"
                        )
        
        found_words = set(result.trigger_word for result in trigger_results)
        logger.info(f"Unsynced lyrics scan completed. Found {len(trigger_results)} triggers. Words: {', '.join(found_words)}")
        
        return trigger_results
    
    def has_triggers(self, lyrics_text: str, user_id: Optional[int] = None) -> bool:
        """
        Quick check if lyrics contain any trigger words.
        
        Args:
            lyrics_text: Plain text lyrics
            user_id: User ID for personalized trigger words
            
        Returns:
            True if any trigger words are found, False otherwise
        """
        results = self.scan_unsynced_lyrics(lyrics_text, user_id)
        return len(results) > 0