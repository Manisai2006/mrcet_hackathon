from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.auth.dependencies import get_current_user
from app.rag.vector_store import LocalVectorIndex
from app.services.tutor_service import generate_tutor_response

router = APIRouter(prefix="/api/rag", tags=["RAG Retrieval & Strict Document Search"])

class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Student question")
    document_id: Optional[int] = Field(None, description="Specific document ID")
    strict_mode: bool = Field(False, description="If True, answer only from PDF context")
    language: str = Field("English", description="Response language")

class CitationSource(BaseModel):
    filename: str
    page: int
    score: float

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[CitationSource] = []
    strict_mode: bool

@router.post("/query", response_model=RAGQueryResponse)
def query_rag_documents(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch user's documents & chunks
    doc_query = db.query(Document).filter(Document.user_id == current_user.id)
    if request.document_id:
        doc_query = doc_query.filter(Document.id == request.document_id)

    user_docs = doc_query.all()
    if not user_docs:
        if request.strict_mode:
            return RAGQueryResponse(
                answer="I couldn't find that information in your uploaded study material.",
                sources=[],
                strict_mode=True
            )
        raise HTTPException(status_code=404, detail="No study materials found for search.")

    # 2. Gather candidate chunks from documents
    candidate_chunks = []
    for doc in user_docs:
        for chunk in doc.chunks:
            candidate_chunks.append({
                "id": chunk.id,
                "text": chunk.text_content,
                "page": chunk.page_number,
                "filename": doc.filename
            })

    # 3. Vector similarity search
    top_results = LocalVectorIndex.search_top_k(request.query, candidate_chunks, top_k=3)

    if not top_results and request.strict_mode:
        return RAGQueryResponse(
            answer="I couldn't find that information in your uploaded study material.",
            sources=[],
            strict_mode=True
        )

    # 4. Construct RAG Context string with page tracking
    context_blocks = []
    sources = []
    for res in top_results:
        context_blocks.append(f"[📄 {res['filename']} - Page {res['page']}]:\n{res['text']}")
        sources.append(CitationSource(
            filename=res['filename'],
            page=res['page'],
            score=res['score']
        ))

    doc_context_str = "\n\n".join(context_blocks)

    # 5. Invoke Tutor Service with Strict RAG Mode rules if enabled
    mode = "Teach Me"
    if request.strict_mode:
        prompt_with_strict_instructions = f"""{request.query}

STRICT DOCUMENT INSTRUCTION:
Answer STRICTLY using the provided study material context above.
If the answer cannot be determined from the provided context, respond EXACTLY with:
"I couldn't find that information in your uploaded study material."
Do NOT invent or use outside knowledge when answering in strict mode."""
    else:
        prompt_with_strict_instructions = request.query

    student_class = current_user.profile.student_class if current_user.profile else "10th"
    answer = generate_tutor_response(
        prompt=prompt_with_strict_instructions,
        language=request.language,
        tutor_mode=mode,
        student_class=student_class,
        document_context=doc_context_str
    )

    # Attach citation footer to answer text if sources present
    if sources and "couldn't find that information" not in answer.lower():
        citation_footer = "\n\n📌 **Sources Used**:\n" + "\n".join([f"- 📄 *{s.filename}* (Page {s.page})" for s in sources])
        answer += citation_footer

    return RAGQueryResponse(
        answer=answer,
        sources=sources,
        strict_mode=request.strict_mode
    )
