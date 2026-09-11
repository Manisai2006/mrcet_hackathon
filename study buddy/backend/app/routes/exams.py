import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.exam import Exam, Question
from app.schemas.exam import ExamGenerateRequest, ExamResponse, ExamDetailPublicResponse, ExamSubmitRequest, ExamResultResponse
from app.auth.dependencies import get_current_user
from app.services.exam_service import generate_exam_questions

router = APIRouter(prefix="/api/exams", tags=["AI Exam Generator"])

@router.post("/generate", response_model=ExamDetailPublicResponse, status_code=status.HTTP_201_CREATED)
def generate_ai_exam(
    request: ExamGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Resolve Document Context if grounded exam requested
    doc_context = None
    doc_title = ""
    if request.document_id:
        doc = db.query(Document).filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        ).first()
        if doc and doc.chunks:
            doc_title = f" ({doc.filename})"
            doc_context = "\n---\n".join([chunk.text_content for chunk in doc.chunks[:6]])

    # 2. Call Exam Generator Service
    student_class = current_user.profile.student_class if current_user.profile else "10th"
    raw_questions = generate_exam_questions(
        subject=request.subject,
        student_class=student_class,
        language=request.language,
        difficulty=request.difficulty,
        total_questions=request.total_questions,
        question_types=request.question_types,
        document_context=doc_context
    )

    if not raw_questions:
        raise HTTPException(status_code=500, detail="Failed to generate exam questions. Please try again.")

    # 3. Create Exam Header in Database
    exam_title = f"{request.subject} Mock Test{doc_title}"
    exam = Exam(
        user_id=current_user.id,
        title=exam_title,
        subject=request.subject,
        document_id=request.document_id,
        difficulty=request.difficulty,
        language=request.language,
        total_questions=len(raw_questions),
        time_limit_minutes=request.time_limit_minutes
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # 4. Save Questions with secure backend answer key
    question_records = []
    for idx, q_data in enumerate(raw_questions):
        options_json = json.dumps(q_data.get("options", [])) if q_data.get("options") else None
        q_record = Question(
            exam_id=exam.id,
            question_number=idx + 1,
            question_type=q_data.get("question_type", request.question_types),
            question_text=q_data.get("question_text", f"Question {idx + 1}"),
            options=options_json,
            correct_answer=str(q_data.get("correct_answer", "")),
            explanation=str(q_data.get("explanation", "")),
            difficulty=q_data.get("difficulty", request.difficulty),
            topic=q_data.get("topic", request.subject)
        )
        question_records.append(q_record)

    db.add_all(question_records)
    db.commit()
    db.refresh(exam)

    return exam

@router.get("", response_model=List[ExamResponse])
def list_student_exams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exams = db.query(Exam).filter(
        Exam.user_id == current_user.id
    ).order_by(Exam.created_at.desc()).all()
    return exams

@router.get("/{exam_id}", response_model=ExamDetailPublicResponse)
def get_exam_for_taking(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(Exam).filter(
        Exam.id == exam_id,
        Exam.user_id == current_user.id
    ).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found or unauthorized")

    return exam

@router.post("/{exam_id}/submit", response_model=ExamResultResponse)
def submit_and_evaluate_exam(
    exam_id: int,
    submission: ExamSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(Exam).filter(
        Exam.id == exam_id,
        Exam.user_id == current_user.id
    ).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found or unauthorized")

    # Map student answers by question ID
    submitted_answers_map = {ans.question_id: (ans.student_answer_text or "").strip() for ans in submission.answers}

    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.question_number).all()

    total_score = 0.0
    max_score = float(len(questions))
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    topic_performance = {}  # {topic: {'correct': X, 'total': Y}}
    student_answer_records = []
    detailed_answer_results = []

    from app.services.exam_evaluator import evaluate_subjective_answer, generate_personalized_exam_feedback
    from app.models.exam import ExamAttempt, StudentAnswer
    from app.models.analytics import StudentPerformance

    attempt = ExamAttempt(
        exam_id=exam.id,
        user_id=current_user.id,
        score=0.0,
        max_score=max_score,
        percentage=0.0
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    for q in questions:
        stud_text = submitted_answers_map.get(q.id, "")
        topic = q.topic or exam.subject
        if topic not in topic_performance:
            topic_performance[topic] = {"correct": 0, "total": 0}
        topic_performance[topic]["total"] += 1

        is_correct = False
        score_obtained = 0.0
        feedback = ""

        if not stud_text:
            unanswered_count += 1
            feedback = "Not answered."
        elif q.question_type in ["MCQ", "True/False"]:
            # Strict string comparison for objective MCQs
            if stud_text.lower().strip() == q.correct_answer.lower().strip():
                is_correct = True
                score_obtained = 1.0
                correct_count += 1
                topic_performance[topic]["correct"] += 1
                feedback = "Correct answer!"
            else:
                incorrect_count += 1
                feedback = f"Incorrect. Correct answer is: {q.correct_answer}"
        else:
            # Controlled AI subjective evaluation
            is_correct, score_obtained, feedback = evaluate_subjective_answer(
                question_text=q.question_text,
                expected_answer=q.correct_answer,
                student_answer=stud_text,
                language=exam.language
            )
            if is_correct:
                correct_count += 1
                topic_performance[topic]["correct"] += 1
            else:
                incorrect_count += 1

        total_score += score_obtained

        # Save student answer record
        sa = StudentAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            student_answer_text=stud_text,
            is_correct=is_correct,
            score_obtained=score_obtained,
            evaluation_feedback=feedback
        )
        student_answer_records.append(sa)

        detailed_answer_results.append({
            "question_id": q.id,
            "question_number": q.question_number,
            "question_text": q.question_text,
            "student_answer_text": stud_text,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
            "score_obtained": score_obtained,
            "evaluation_feedback": feedback,
            "explanation": q.explanation,
            "topic": topic
        })

    db.add_all(student_answer_records)

    percentage = round((total_score / max_score) * 100.0, 1) if max_score > 0 else 0.0

    # Categorize Strong vs Weak Topics
    strong_topics = []
    weak_topics = []
    for top_name, stats in topic_performance.items():
        prof = (stats["correct"] / stats["total"]) * 100.0 if stats["total"] > 0 else 0.0
        if prof >= 70.0:
            strong_topics.append(top_name)
        else:
            weak_topics.append(top_name)

        # Update or insert StudentPerformance DB analytics record
        perf_rec = db.query(StudentPerformance).filter(
            StudentPerformance.user_id == current_user.id,
            StudentPerformance.subject == exam.subject,
            StudentPerformance.topic == top_name
        ).first()

        if not perf_rec:
            perf_rec = StudentPerformance(
                user_id=current_user.id,
                subject=exam.subject,
                topic=top_name,
                total_questions_attempted=stats["total"],
                correct_count=stats["correct"],
                proficiency_percentage=prof,
                status="Strong" if prof >= 70.0 else "Needs Practice"
            )
            db.add(perf_rec)
        else:
            perf_rec.total_questions_attempted += stats["total"]
            perf_rec.correct_count += stats["correct"]
            perf_rec.proficiency_percentage = (perf_rec.correct_count / perf_rec.total_questions_attempted) * 100.0
            perf_rec.status = "Strong" if perf_rec.proficiency_percentage >= 70.0 else "Needs Practice"

    # Generate Personalized AI Feedback
    ai_feedback = generate_personalized_exam_feedback(
        subject=exam.subject,
        percentage=percentage,
        strong_topics=strong_topics,
        weak_topics=weak_topics,
        language=exam.language
    )

    attempt.score = total_score
    attempt.percentage = percentage
    attempt.feedback = ai_feedback
    db.commit()
    db.refresh(attempt)

    return ExamResultResponse(
        attempt_id=attempt.id,
        exam_id=exam.id,
        title=exam.title,
        score=total_score,
        max_score=max_score,
        percentage=percentage,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        feedback=ai_feedback,
        strong_topics=strong_topics,
        weak_topics=weak_topics,
        completed_at=attempt.completed_at,
        detailed_answers=detailed_answer_results
    )

@router.get("/{exam_id}/results", response_model=ExamResultResponse)
def get_exam_latest_results(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.exam import ExamAttempt, StudentAnswer
    attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.user_id == current_user.id
    ).order_by(ExamAttempt.completed_at.desc()).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="No evaluation attempt found for this exam")

    exam = attempt.exam
    answers = db.query(StudentAnswer).filter(StudentAnswer.attempt_id == attempt.id).all()

    detailed_answers = []
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    strong_topics = set()
    weak_topics = set()

    for ans in answers:
        q = ans.question
        if ans.is_correct:
            correct_count += 1
            strong_topics.add(q.topic or exam.subject)
        elif not ans.student_answer_text:
            unanswered_count += 1
            weak_topics.add(q.topic or exam.subject)
        else:
            incorrect_count += 1
            weak_topics.add(q.topic or exam.subject)

        detailed_answers.append({
            "question_id": q.id,
            "question_number": q.question_number,
            "question_text": q.question_text,
            "student_answer_text": ans.student_answer_text,
            "correct_answer": q.correct_answer,
            "is_correct": ans.is_correct,
            "score_obtained": ans.score_obtained,
            "evaluation_feedback": ans.evaluation_feedback,
            "explanation": q.explanation,
            "topic": q.topic or exam.subject
        })

    return ExamResultResponse(
        attempt_id=attempt.id,
        exam_id=exam.id,
        title=exam.title,
        score=attempt.score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        feedback=attempt.feedback or "Exam evaluated successfully.",
        strong_topics=list(strong_topics),
        weak_topics=list(weak_topics),
        completed_at=attempt.completed_at,
        detailed_answers=detailed_answers
    )

