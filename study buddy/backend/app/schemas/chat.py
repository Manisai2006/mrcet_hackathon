from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Student doubt/question")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID if continuing")
    tutor_mode: str = Field("Teach Me", description="'Teach Me', 'Quick Explanation', or 'Practice Me'")
    selected_language: str = Field("English", description="'English', 'Telugu', or 'Hindi'")
    selected_document_id: Optional[int] = Field(None, description="PDF Document ID for RAG context")
    strict_mode: bool = Field(False, description="If True, restrict AI answer strictly to PDF content")

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    selected_language: str
    tutor_mode: str
    selected_document_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationDetail(ConversationResponse):
    messages: List[MessageResponse] = []

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    selected_language: Optional[str] = None
    tutor_mode: Optional[str] = None
