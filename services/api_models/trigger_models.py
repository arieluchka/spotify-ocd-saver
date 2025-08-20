"""
Trigger category-related API models for OCDify service
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class TriggerCategoryCreate(BaseModel):
    name: str = Field(..., description="Category name")
    words: List[str] = Field(..., description="List of trigger words")
    is_active: bool = Field(True, description="Whether category is active")


class TriggerCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Category name")
    words: Optional[List[str]] = Field(None, description="List of trigger words")
    is_active: Optional[bool] = Field(None, description="Whether category is active")


class TriggerCategoryResponse(BaseModel):
    id: int
    name: str
    words: List[str]
    user_id: Optional[int]
    is_global: bool
    is_active: bool
    created_at: Optional[str]