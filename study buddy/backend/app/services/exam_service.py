import json
import logging
from typing import List, Dict, Any, Optional
from google.genai import types

from app.services.gemini_key_manager import key_manager

logger = logging.getLogger("ExamService")

EXAM_GEN_PROMPT = """You are an expert school exam setter. Generate a high quality, non-repetitive mock exam for a school student.

EXAM REQUIREMENTS:
- Subject: {subject}
- Class/Grade: {student_class}
- Target Language: {language}
- Difficulty: {difficulty}
- Total Questions: {total_questions}
- Question Types to Include: {question_types}

INSTRUCTIONS:
1. Provide valid, age-appropriate educational questions in {language}.
2. Ensure high topic diversity across the subject.
3. For MCQs, provide exactly 4 options ("A", "B", "C", "D") with only 1 correct answer.
4. Output strictly valid JSON format matching the schema below. Do not include markdown codeblocks or extra text.

JSON RESPONSE SCHEMA:
{{
  "questions": [
    {{
      "question_number": 1,
      "question_type": "MCQ",
      "question_text": "Question text in {language}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Explanation in {language}",
      "difficulty": "Medium",
      "topic": "Topic Name"
    }}
  ]
}}
"""

def generate_exam_questions(
    subject: str = "Physics",
    student_class: str = "10th",
    language: str = "English",
    difficulty: str = "Medium",
    total_questions: int = 5,
    question_types: str = "MCQ",
    document_context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generates structured exam questions via Gemini load balancer using gemini-3.6-flash.
    """
    prompt = EXAM_GEN_PROMPT.format(
        subject=subject,
        student_class=student_class,
        language=language,
        difficulty=difficulty,
        total_questions=total_questions,
        question_types=question_types
    )

    if document_context:
        prompt += f"\n\nSTRICT STUDY MATERIAL CONTEXT:\nBase questions on this study content:\n{document_context[:3000]}"

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.4,
        max_output_tokens=3000
    )

    attempts = len(key_manager.keys) if key_manager.keys else 1
    for _ in range(max(1, attempts)):
        client, key_idx = key_manager.get_client()
        if not client:
            break

        try:
            logger.info(f"[AI DEBUG] Generating exam questions with model 'gemini-3.6-flash' on Key #{key_idx + 1}")
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=config
            )
            if response and response.text:
                data = json.loads(response.text.strip())
                questions = data.get("questions", [])
                if questions and len(questions) > 0:
                    logger.info(f"[AI DEBUG] Exam questions generated successfully: {len(questions)} items")
                    return questions
        except Exception as e:
            logger.error(f"[AI ERROR] Exam Generation API error on Key #{key_idx + 1 if key_idx is not None else 0}: {str(e)}")
            if key_idx is not None:
                key_manager.mark_key_failed(key_idx)

    # Fallback questions if API fails or keys not set up
    return generate_fallback_questions(subject, language, difficulty, total_questions, question_types)

def generate_fallback_questions(subject: str, language: str, difficulty: str, count: int, q_type: str) -> List[Dict[str, Any]]:
    """Provides valid sample questions when API key is unconfigured."""
    questions = []
    
    sample_pool = {
        "Telugu": [
            {
                "question_number": 1,
                "question_type": "MCQ",
                "question_text": "న్యూటన్ మూడో గమన నియమం ఏమిటి?",
                "options": ["ప్రతి చర్యకూ సమానమైన ప్రతిచర్య ఉంటుంది", "బలము = ద్రవ్యరాశి x త్వరణము", "నిశ్చల స్థితి లో ఉన్న వస్తువు అలానే ఉంటుంది", "ఏదీ కాదు"],
                "correct_answer": "ప్రతి చర్యకూ సమానమైన ప్రతిచర్య ఉంటుంది",
                "explanation": "న్యూటన్ 3వ నియమం ప్రకారం ప్రతి చర్యకూ సమాన మరియు వ్యతిరేక ప్రతిచర్య ఉంటుంది.",
                "difficulty": difficulty,
                "topic": "Motion & Force"
            }
        ],
        "Hindi": [
            {
                "question_number": 1,
                "question_type": "MCQ",
                "question_text": "न्यूटन के तीसरे नियम का सही कथन क्या है?",
                "options": ["प्रत्येक क्रिया की समान तथा विपरीत प्रतिक्रिया होती है", "बल = द्रव्यमान x त्वरण", "वस्तु स्थिर ही रहती है", "इनमें से कोई नहीं"],
                "correct_answer": "प्रत्येक क्रिया की समान तथा विपरीत प्रतिक्रिया होती है",
                "explanation": "न्यूटन का तीसरा नियम क्रिया-प्रतिक्रिया का नियम कहलाता है।",
                "difficulty": difficulty,
                "topic": "Motion & Force"
            }
        ],
        "English": [
            {
                "question_number": 1,
                "question_type": "MCQ",
                "question_text": "What is Newton's Third Law of Motion?",
                "options": [
                    "For every action, there is an equal and opposite reaction",
                    "Force equals mass times acceleration",
                    "An object at rest stays at rest unless acted upon",
                    "Energy can neither be created nor destroyed"
                ],
                "correct_answer": "For every action, there is an equal and opposite reaction",
                "explanation": "Newton's third law states that forces always occur in equal and opposite pairs.",
                "difficulty": difficulty,
                "topic": "Laws of Motion"
            }
        ]
    }

    pool = sample_pool.get(language, sample_pool["English"])
    for idx in range(count):
        base_q = pool[idx % len(pool)].copy()
        base_q["question_number"] = idx + 1
        questions.append(base_q)

    return questions
