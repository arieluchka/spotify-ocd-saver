from enum import IntEnum


class TriggerScanStatus(IntEnum):
    """Enum for trigger scan status."""
    NOT_SCANNED = 0
    CLEAN = 1
    CONTAMINATED = 2