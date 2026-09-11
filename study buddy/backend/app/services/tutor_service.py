import logging
from typing import List, Dict, Optional
from google.genai import types
from app.services.gemini_key_manager import key_manager

logger = logging.getLogger("TutorService")

SYSTEM_TUTOR_PROMPT = """You are a senior, encouraging, step-by-step AI Personal Tutor for school students (Classes 1 to 10).
Your goal is to HELP THE STUDENT TRULY UNDERSTAND school concepts, not simply provide direct answers or canned responses.

CORE TUTOR GUIDELINES:
1. BE A TEACHER, NOT A DIRECT ANSWER ENGINE:
   - When a student asks a concept question (e.g., "Explain about the layers of atmosphere", "What is photosynthesis?", "Newton's third law explain cheyyi"):
     a. Give a simple, student-friendly introduction.
     b. Break the topic into clear, logical parts/layers.
     c. Explain each part simply in accessible language.
     d. Provide a relatable real-world example.
     e. Summarize important points to remember.
     f. End with a short question to check understanding.

   - When a student asks a problem-solving question (e.g., "Solve 2x + 5 = 15"):
     a. Understand what is being asked and state the relevant principle.
     b. Guide the student step-by-step through isolating variables or applying formulas.
     c. Ask guiding questions to help them think independently.

2. MULTI-LINGUAL REGIONAL LANGUAGE SUPPORT:
   - Selected Language: {language}
   - Student Class Level: {student_class}
   - Target Subject: {subject}
   - Respond in {language} naturally (or natural mixed regional language e.g. Telugu/Hindi if requested by the student).
   - Recognize mixed queries (e.g., "Photosynthesis ante enti?" or "Newton third law samjhao") and answer naturally.

3. STRUCTURED RESPONSE FORMATTING (Use clean Markdown):
   - 💡 **Simple Explanation**: High-level intuitive summary.
   - 🔍 **Concept Breakdown**: Key components or principles.
   - 📝 **Step-by-Step Explanation**: Sequential logical steps.
   - 🌍 **Real-World Example**: Everyday relatable analogy or real-life application.
   - ❓ **Quick Check**: A friendly follow-up question to check understanding.

4. ACCURACY & ADAPTABILITY:
   - Adapt explanations to the student's selected class grade ({student_class}).
   - Always respond directly to the student's actual question. Never return generic filler content.
"""

def generate_tutor_response(
    prompt: str,
    language: str = "English",
    tutor_mode: str = "Teach Me",
    student_class: str = "10th",
    subject: str = "General Science",
    history: Optional[List[Dict[str, str]]] = None,
    document_context: Optional[str] = None
) -> str:
    """
    Generates educational tutor responses using Gemini API via key load balancer.
    Uses 'gemini-3.6-flash' model for reliable live responses.
    """
    logger.info(f"[AI DEBUG] Chat request received for prompt: '{prompt[:40]}...' | Language: {language} | Mode: {tutor_mode}")

    system_instruction = SYSTEM_TUTOR_PROMPT.format(
        language=language,
        student_class=student_class,
        subject=subject
    )

    if tutor_mode == "Teach Me":
        system_instruction += "\nMODE SPECIFIC INSTRUCTION: Use Socratic step-by-step guidance. Guide the student to think through the steps."
    elif tutor_mode == "Practice Me":
        system_instruction += "\nMODE SPECIFIC INSTRUCTION: Provide a guided practice exercise after a short concept review."

    if document_context:
        system_instruction += f"\n\nSTRICT STUDY MATERIAL CONTEXT:\nThe student uploaded study material. Answer using this content:\n{document_context}"

    # Build prompt context with history
    contents = []
    if history:
        for msg in history[-8:]:
            role = "user" if msg["role"] == "student" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
    
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.7,
        max_output_tokens=1500,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )

    # Candidate models pool in order of preference (fastest/most reliable first)
    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]

    # Attempt request with automatic key rotation across pool
    attempts = len(key_manager.keys) if key_manager.keys else 1
    if attempts == 0:
        logger.warning("[AI DEBUG] Gemini API key loaded: NO")
        return "AI service is currently unavailable. Please check the Gemini configuration in .env or try again."

    logger.info(f"[AI DEBUG] Gemini key loaded: YES | Available keys in pool: {attempts}")

    for attempt_num in range(attempts):
        client, key_idx = key_manager.get_client()
        if not client:
            break

        for model_name in candidate_models:
            try:
                logger.info(f"[AI DEBUG] Calling Gemini API (model: '{model_name}', Key #{key_idx + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                if response and response.text:
                    logger.info(f"[AI DEBUG] Gemini response received! Model: '{model_name}' | Length: {len(response.text)} chars")
                    return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[AI ERROR] Gemini request failed for model '{model_name}' on Key #{key_idx + 1}: {error_msg}")
        
        # If all models failed for this key, mark key for short cooldown
        if key_idx is not None:
            key_manager.mark_key_failed(key_idx, duration=15)

    logger.error("[AI ERROR] All Gemini API attempts failed across configured models and keys.")
    return "AI service is temporarily unavailable. Please check your Gemini configuration or try again in a few moments."

def generate_conversation_title(first_message: str, language: str = "English") -> str:
    """Generates a short, descriptive 3-5 word title for a conversation using gemini-3.6-flash with fast local fallback."""
    fallback_title = " ".join(first_message.split()[:4]).title() if len(first_message.split()) >= 4 else first_message.title()
    
    try:
        client, key_idx = key_manager.get_client()
        if not client:
            return fallback_title

        config = types.GenerateContentConfig(
            max_output_tokens=20,
            temperature=0.3,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        for model_name in ["gemini-3.5-flash-lite", "gemini-3.6-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=f"Generate a short 3-5 word concise conversation title for this school question in {language}: '{first_message}'. Return ONLY the plain title without quotes.",
                    config=config
                )
                if response and response.text:
                    return response.text.strip().replace('"', '')
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"[AI DEBUG] Title generation fallback triggered: {str(e)}")

    return fallback_title
