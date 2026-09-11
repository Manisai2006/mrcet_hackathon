from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    page_number: int
    text_content: str

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_size_bytes: int
    page_count: int
    subject: str
    status: str
    extraction_method: Optional[str] = "text"
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    chunks: List[DocumentChunkResponse] = []
