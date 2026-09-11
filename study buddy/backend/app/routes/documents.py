import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.auth.dependencies import get_current_user
from app.rag.pdf_processor import validate_and_extract_pdf, PDFValidationError

router = APIRouter(prefix="/api/documents", tags=["Study Material PDF Documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf_document(
    file: UploadFile = File(...),
    subject: Optional[str] = Form("General Science"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Server-side MIME & Extension Check
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF (.pdf) documents are accepted."
        )

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'. Uploaded file must be a valid PDF."
        )

    # 2. Save file temporarily for processing
    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file to server storage: {str(e)}")

    # 3. Validate & Extract Text Pages
    try:
        total_pages, extracted_pages, overall_method = validate_and_extract_pdf(file_path, settings.MAX_UPLOAD_SIZE_MB)
    except PDFValidationError as ve:
        # Clean up invalid file from disk
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    # 4. Save Document Metadata to Database
    file_size = os.path.getsize(file_path)
    document = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
        page_count=total_pages,
        subject=subject or "General Science",
        status="Ready",
        extraction_method=overall_method
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # 5. Create Document Chunks for page contents
    chunks_to_create = []
    chunk_index = 0
    for page_data in extracted_pages:
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=chunk_index,
            page_number=page_data["page"],
            text_content=page_data["text"]
        )
        chunks_to_create.append(chunk)
        chunk_index += 1

    db.add_all(chunks_to_create)
    db.commit()
    db.refresh(document)

    return document

@router.get("", response_model=List[DocumentResponse])
def list_student_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    documents = db.query(Document).filter(
        Document.user_id == current_user.id
    ).order_by(Document.created_at.desc()).all()
    return documents

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_detail(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found or unauthorized")

    return document

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found or unauthorized")

    # Remove physical file if exists
    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception:
            pass

    db.delete(document)
    db.commit()
    return {"message": f"Document '{document.filename}' deleted successfully."}
