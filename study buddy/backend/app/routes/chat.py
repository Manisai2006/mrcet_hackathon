import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.chat import Conversation, Message
from app.models.document import Document
from app.schemas.chat import ChatQueryRequest, MessageResponse, ConversationResponse, ConversationDetail, ConversationUpdate
from app.auth.dependencies import get_current_user
from app.services.tutor_service import generate_tutor_response, generate_conversation_title

router = APIRouter(prefix="/api/chat", tags=["AI Tutor & Chat History"])

@router.post("", response_model=MessageResponse)
def ask_tutor(
    request: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Resolve or create conversation
    conversation = None
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or unauthorized")
    
    if not conversation:
        # Generate initial title from student prompt with fallback
        try:
            title = generate_conversation_title(request.prompt, request.selected_language)
        except Exception:
            words = request.prompt.split()
            title = " ".join(words[:4]).title() if len(words) >= 4 else request.prompt.title()

        conversation = Conversation(
            user_id=current_user.id,
            title=title,
            selected_language=request.selected_language,
            tutor_mode=request.tutor_mode,
            selected_document_id=request.selected_document_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Save student message
    student_msg = Message(
        conversation_id=conversation.id,
        role="student",
        content=request.prompt
    )
    db.add(student_msg)
    db.commit()

    # 3. Retrieve conversation message history for context
    history_records = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()

    history = [{"role": msg.role, "content": msg.content} for msg in history_records[:-1]]

    # 4. Vector Search Context for RAG (if document selected or strict mode)
    doc_context = None
    sources_metadata = []

    if conversation.selected_document_id or request.strict_mode:
        doc_query = db.query(Document).filter(Document.user_id == current_user.id)
        if conversation.selected_document_id:
            doc_query = doc_query.filter(Document.id == conversation.selected_document_id)
        
        user_docs = doc_query.all()
        candidate_chunks = []
        for d in user_docs:
            for ch in d.chunks:
                candidate_chunks.append({
                    "id": ch.id,
                    "text": ch.text_content,
                    "page": ch.page_number,
                    "filename": d.filename
                })

        if candidate_chunks:
            from app.rag.vector_store import LocalVectorIndex
            top_results = LocalVectorIndex.search_top_k(request.prompt, candidate_chunks, top_k=3)
            if top_results:
                context_blocks = []
                for res in top_results:
                    context_blocks.append(f"[📄 {res['filename']} - Page {res['page']}]:\n{res['text']}")
                    sources_metadata.append(f"📄 {res['filename']} (Page {res['page']})")
                doc_context = "\n\n".join(context_blocks)
            elif request.strict_mode:
                # Immediate response if strict mode enabled and no chunks found
                assistant_msg = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="I couldn't find that information in your uploaded study material."
                )
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)
                return assistant_msg

    # 5. Generate AI Tutor Response
    student_class = current_user.profile.student_class if current_user.profile else "10th"
    prompt_to_send = request.prompt
    if request.strict_mode:
        prompt_to_send = f"{request.prompt}\n\nSTRICT INSTRUCTION: Answer strictly from provided study material. If answer is not present, reply: 'I couldn't find that information in your uploaded study material.'"

    ai_reply_text = generate_tutor_response(
        prompt=prompt_to_send,
        language=request.selected_language or conversation.selected_language,
        tutor_mode=request.tutor_mode or conversation.tutor_mode,
        student_class=student_class,
        history=history,
        document_context=doc_context
    )

    if sources_metadata and "couldn't find that information" not in ai_reply_text.lower():
        ai_reply_text += "\n\n📌 **Based on**: " + ", ".join(sources_metadata)

    # 6. Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_reply_text
    )
    db.add(assistant_msg)
    
    # Update conversation timestamp & settings
    conversation.updated_at = datetime.datetime.utcnow()
    if request.selected_language:
        conversation.selected_language = request.selected_language
    if request.tutor_mode:
        conversation.tutor_mode = request.tutor_mode

    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg

@router.get("/history", response_model=List[ConversationResponse])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()
    return conversations

@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if update_data.title:
        conversation.title = update_data.title
    if update_data.selected_language:
        conversation.selected_language = update_data.selected_language
    if update_data.tutor_mode:
        conversation.tutor_mode = update_data.tutor_mode

    db.commit()
    db.refresh(conversation)
    return conversation

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted successfully."}
