"""
Monitoring-related API models for OCDify service
"""

from pydantic import BaseModel
from typing import Dict


class MonitoringStatusResponse(BaseModel):
    is_running: bool
    threads_active: Dict[str, bool]