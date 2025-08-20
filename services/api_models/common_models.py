"""
Common API models for OCDify service
"""

from pydantic import BaseModel
from typing import Optional, Any


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None