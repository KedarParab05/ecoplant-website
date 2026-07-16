"""
routers/chat.py — EcoBot AI chat (Gemini) — Security Hardened
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
        # Limit individual message length
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


@router.post("/")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatBody):
    client = get_client()
    if not client:
        return {
            "error": "AI service not configured",
            "reply": "I'm currently offline for maintenance 🌿 Please try again later!",
        }

    # Keep last 20 messages (token budget)
    trimmed = body.messages[-20:]

    # Last message must be from user
    if trimmed[-1].role != "user":
        raise HTTPException(400, "Last message must be from the user")

    try:
        model = client.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
            }
        )
        history = [
            {"role": "model" if m.role == "assistant" else "user", "parts": [m.content]}
            for m in trimmed[:-1]
        ]
        chat_session = model.start_chat(history=history)
        result = chat_session.send_message(trimmed[-1].content)
        return {"reply": result.text}

    except Exception as e:
        msg = str(e)
        if "API key" in msg or "401" in msg:
            raise HTTPException(503, "AI service temporarily unavailable 🌿")
        if "429" in msg or "quota" in msg.lower():
            raise HTTPException(429, "I'm a bit busy right now 🌿 Please try again in a moment!")
        raise HTTPException(500, "Something went wrong. Please try again!")
