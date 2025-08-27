from enum import IntEnum


class LyricsScanStatus(IntEnum):
    """Enum for song lyrics scan status."""
    NOT_SCANNED = 0
    NO_RESULTS = 1
    PLAIN_LYRICS = 2
    SYNC_LYRICS = 3