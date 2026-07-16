"""
routers/chat.py — EcoBot AI chat powered by Google Gemini
POST /api/chat  { messages: [{role, content}] }
"""

import os
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])

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

Context: You serve Indian plant enthusiasts. Prices are in INR. Be aware of Indian seasons (Summer, Monsoon, Post-Monsoon, Winter) and Indian climate zones (tropical, subtropical, temperate)."""

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


class ChatBody(BaseModel):
    messages: List[Message]


@router.post("/")
async def chat(body: ChatBody):
    if not body.messages:
        raise HTTPException(400, "messages array is required")

    for m in body.messages:
        if m.role not in ("user", "assistant"):
            raise HTTPException(400, "Each message must have role (user|assistant) and content (string)")

    client = get_client()
    if not client:
        return {
            "error": "AI service not configured",
            "reply": "I'm currently offline for maintenance 🌿 Please try again later or browse our plant collection!",
        }

    trimmed = body.messages[-20:]

    try:
        model = client.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        history = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [m.content],
            }
            for m in trimmed[:-1]
        ]
        last = trimmed[-1].content
        chat_session = model.start_chat(history=history)
        result = chat_session.send_message(last)
        return {"reply": result.text}

    except Exception as e:
        msg = str(e)
        if "API key" in msg or "401" in msg:
            raise HTTPException(500, detail={"error": "AI API key invalid", "reply": "AI service temporarily unavailable 🌿"})
        if "429" in msg or "quota" in msg.lower():
            raise HTTPException(429, detail={"error": "Rate limit reached", "reply": "I'm a bit busy right now 🌿 Please try again in a moment!"})
        raise HTTPException(500, detail={"error": msg, "reply": "Something went wrong. Please try again!"})
