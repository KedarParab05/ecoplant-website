"""
routers/chat.py — EcoBot AI chat (Gemini) — Security Hardened with Fallback
POST /api/chat  { messages: [{role, content}] }
"""

import os
from typing import List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)

SYSTEM_PROMPT = """You are EcoBot, a friendly and knowledgeable AI plant care assistant for EcoPlant — a premium Indian plant shop.

Your expertise covers:
• Plant identification and species information
• Plant health diagnosis and treatment recommendations
• Watering, fertilising, and soil advice
• Light requirements and placement guidance
• Pest and disease management
• Seasonal care tips specific to Indian climates
• Recommendations for plants based on space, experience level, and light conditions

Tone: Warm, encouraging, and practical. Use relevant plant emojis. Keep answers concise (2–4 short paragraphs max). Always end with an actionable tip.

Context: You serve Indian plant enthusiasts. Prices are in INR. Be aware of Indian seasons (Summer, Monsoon, Post-Monsoon, Winter) and Indian climate zones (tropical, subtropical, temperate).

IMPORTANT: You are strictly a plant care assistant. Politely decline to answer anything unrelated to plants, gardening, or nature."""

_gen_ai = None


def get_client():
    global _gen_ai
    if _gen_ai is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            _gen_ai = genai
    return _gen_ai


class Message(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not isinstance(v, str):
            raise ValueError("content must be a string")
        if len(v) > 4000:
            raise ValueError("Message too long (max 4000 characters)")
        return v.strip()


class ChatBody(BaseModel):
    messages: List[Message]

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v):
        if not v:
            raise ValueError("messages array is required")
        if len(v) > 50:
            raise ValueError("Too many messages (max 50)")
        return v


def get_fallback_answer(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["beginner", "easy", "starter", "new"]):
        return (
            "🌿 **Top Recommendations for Beginners:**\n\n"
            "1. **Snake Plant (Sansevieria):** Virtually indestructible, thrives in low light, and only needs water every 2–3 weeks.\n"
            "2. **ZZ Plant (Zamioculcas):** Handles neglect beautifully and tolerates dry indoor air.\n"
            "3. **Golden Pothos:** Fast-growing trailing vine that tells you when it needs water by slightly wilting.\n\n"
            "💡 *Pro-Tip:* More houseplants die from overwatering than underwatering. When in doubt, wait a couple more days!"
        )
    elif any(w in q for w in ["water", "watering", "dry"]):
        return (
            "💧 **Houseplant Watering Guide:**\n\n"
            "• Use the **finger test**: Insert your index finger 2 inches into the soil. Water only if dry.\n"
            "• Always ensure the pot has drainage holes so roots don't sit in stagnant water.\n"
            "• In Indian summers, water more frequently; during monsoons and winter, reduce watering.\n\n"
            "💡 *Pro-Tip:* Morning is the best time to water your plants so excess moisture evaporates during the day."
        )
    elif any(w in q for w in ["yellow", "leaf", "leaves", "dying"]):
        return (
            "🍃 **Why Plant Leaves Turn Yellow:**\n\n"
            "1. **Overwatering:** The #1 cause. Check if the lower soil is soggy or smells sour.\n"
            "2. **Poor Drainage:** Water sitting in the saucer chokes roots.\n"
            "3. **Low Light or Age:** Natural shedding of older bottom leaves is normal.\n\n"
            "💡 *Pro-Tip:* Inspect root health. If roots are firm and white/tan, prune the yellow leaf and adjust moisture."
        )
    elif any(w in q for w in ["sun", "light", "indoor"]):
        return (
            "☀️ **Light Requirements Guide:**\n\n"
            "• **Bright Indirect Light:** Perfect for Monstera, Fiddle Leaf Fig, and Calatheas (near an east or north window).\n"
            "• **Low Light:** Ideal for Snake Plant, ZZ Plant, and Aglaonema (can sit farther into rooms).\n"
            "• **Direct Sun:** Needed for succulents, cacti, and flowering plants like Bougainvillea.\n\n"
            "💡 *Pro-Tip:* Avoid harsh midday sun on indoor tropicals to prevent leaf scorch!"
        )
    return (
        "🌱 Hello! I'm **EcoBot**, your plant care expert. I can help you with watering schedules, choosing the right plant for your light conditions, troubleshooting yellow leaves, or recommending low-maintenance houseplants.\n\n"
        "How can I assist your garden today?"
    )


@router.post("/")
@limiter.limit("15/minute")
async def chat(request: Request, body: ChatBody):
    client = get_client()

    # Keep last 20 messages (token budget)
    trimmed = body.messages[-20:]

    # Last message must be from user
    if trimmed[-1].role != "user":
        raise HTTPException(400, "Last message must be from the user")

    user_query = trimmed[-1].content

    if not client:
        return {"reply": get_fallback_answer(user_query)}

    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    for m_name in models_to_try:
        try:
            model = client.GenerativeModel(
                model_name=m_name,
                system_instruction=SYSTEM_PROMPT,
            )
            history = [
                {"role": "model" if m.role == "assistant" else "user", "parts": [m.content]}
                for m in trimmed[:-1]
            ]
            chat_session = model.start_chat(history=history)
            result = chat_session.send_message(user_query)
            if result and result.text:
                return {"reply": result.text}
        except Exception as e:
            continue

    # Fallback if Gemini quota or models are unavailable
    return {"reply": get_fallback_answer(user_query)}