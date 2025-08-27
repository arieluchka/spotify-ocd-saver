from typing import List, Optional
import logging
import re

from common.models.models import TriggerCategory
from services.ocdify_db.ocdify_db import OCDifyDb

logger = logging.getLogger(__name__)


class TriggerService:
    def __init__(self, db: OCDifyDb):
        self.db = db

    def create_trigger_category(self, name: str, user_id: Optional[int] = None) -> TriggerCategory:
        category = TriggerCategory(
            name=name,
            user_id=user_id,
            is_active=True
        )
        
        category_id = self.db.add_trigger_category(category)
        category.id = category_id
        
        logger.info(f"Created trigger category: {name} (ID: {category_id})")
        return category

    def get_user_categories(self, user_id: Optional[int] = None, include_global: bool = True) -> List[TriggerCategory]:
        return self.db.get_trigger_categories(user_id, include_global)

    def get_category_by_id(self, category_id: int) -> Optional[TriggerCategory]:
        return self.db.get_trigger_category_by_id(category_id)

    def update_category(self, category_id: int, name: str, words: List[str], is_active: bool, user_id: int) -> bool:
        success = self.db.update_trigger_category(category_id, name, words, is_active, user_id)
        if success:
            logger.info(f"Updated trigger category: {name} (ID: {category_id}) with {len(words)} words")
        return success

    def get_category_words(self, category_id: int) -> List[str]:
        category = self.db.get_trigger_category_by_id(category_id)
        return category.words if category else []

    def get_all_active_words(self, user_id: Optional[int] = None) -> List[str]:
        categories = self.get_user_categories(user_id, include_global=True)
        word_list = []
        for category in categories:
            if category.is_active:
                word_list.extend([word.lower() for word in category.words])
        
        # Remove duplicates
        word_list = list(set(word_list))
        logger.debug(f"Retrieved {len(word_list)} trigger words for user {user_id}")
        
        return word_list

    def get_active_words_by_category(self, user_id: Optional[int] = None) -> dict:
        categories = self.get_user_categories(user_id, include_global=True)
        result = {}
        
        for category in categories:
            if category.is_active:
                result[category.id] = {
                    'category': category,
                    'words': [word.lower() for word in category.words]
                }
        
        return result

    def find_triggers_in_text(self, text: str, user_id: Optional[int] = None) -> List[dict]:
        if not text:
            return []

        # Get active words by category
        words_by_category = self.get_active_words_by_category(user_id)
        triggers_found = []
        
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        for category_id, category_data in words_by_category.items():
            words = category_data['words']
            
            for word in words:
                # Use word boundaries for better matching
                pattern = r'\b' + re.escape(word) + r'\b'
                
                for match in re.finditer(pattern, text_lower):
                    triggers_found.append({
                        'word': word,
                        'start': match.start(),
                        'end': match.end(),
                        'category_id': category_id,
                        'category_name': category_data['category'].name
                    })
        
        # Sort by position in text
        triggers_found.sort(key=lambda x: x['start'])
        
        return triggers_found

    def has_triggers(self, text: str, user_id: Optional[int] = None) -> bool:
        if not text:
            return False

        trigger_words = self.get_all_active_words(user_id)
        text_lower = text.lower()
        
        # Quick check using word boundaries
        for word in trigger_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                return True
        
        return False

    def clear_cache(self):
        self._word_cache.clear()
        self._cache_dirty = True
        logger.debug("Cleared trigger words cache")

    def get_category_statistics(self, user_id: Optional[int] = None) -> dict:
        categories = self.get_user_categories(user_id, include_global=True)
        
        stats = {
            'total_categories': len(categories),
            'global_categories': len([c for c in categories if c.user_id is None]),
            'user_categories': len([c for c in categories if c.user_id is not None]),
            'categories': []
        }
        
        for category in categories:
            words = self.get_category_words(category.id)
            category_stats = {
                'id': category.id,
                'name': category.name,
                'word_count': len(words),
                'active_words': len([w for w in words if w.is_active]),
                'is_global': category.user_id is None,
                'is_active': category.is_active
            }
            stats['categories'].append(category_stats)
        
        return stats


def get_trigger_service(db: OCDifyDb) -> TriggerService:
    return TriggerService(db)