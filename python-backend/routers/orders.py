"""
routers/orders.py — Razorpay payments + order management — Security Hardened
"""

import os
import hashlib
import hmac
import uuid as uuid_lib
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from db.database import is_connected, get_db, json_db
from middleware.auth import require_auth, optional_auth
from middleware.validators import validate_email

router = APIRouter(prefix="/api/orders", tags=["orders"])
limiter = Limiter(key_func=get_remote_address)

_razorpay = None
_PHONE_RE = re.compile(r"^\+?[\d\s\-]{7,15}$")
_PIN_RE = re.compile(r"^\d{6}$")


def is_real_key(key_id: str, secret: str) -> bool:
    return (
        bool(key_id) and bool(secret)
        and "XXXX" not in key_id and "XXXX" not in secret
        and len(key_id) >= 20 and len(secret) >= 20
        and key_id.startswith("rzp_")
    )


def get_razorpay():
    global _razorpay
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not is_real_key(key_id, secret):
        return None
    if _razorpay is None:
        try:
            import razorpay
            _razorpay = razorpay.Client(auth=(key_id, secret))
        except Exception:
            return None
    return _razorpay


# ── Request models ──────────────────────────────────────────────────────────────
class CreateOrderBody(BaseModel):
    amount: float
    currency: str = "INR"
    receipt: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 1:
            raise ValueError("amount must be greater than 0")
        if v > 10_000_000:   # ₹1 crore limit
            raise ValueError("amount exceeds maximum allowed value")
        return round(v, 2)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        if v not in ("INR", "USD", "EUR"):
            return "INR"
        return v


class AddressModel(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return (v or "")[:100].strip() if v else v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not _PHONE_RE.match(str(v)):
            raise ValueError("Invalid phone number")
        return (v or "")[:20]

    @field_validator("email")
    @classmethod
    def val_email(cls, v):
        if v:
            try:
                return validate_email(v)
            except Exception:
                raise ValueError("Invalid email")
        return v

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v):
        if v and not _PIN_RE.match(str(v)):
            raise ValueError("Invalid PIN code")
        return v

    @field_validator("street", "city", "state")
    @classmethod
    def sanitize_text(cls, v):
        return (v or "")[:200].strip() if v else v


class OrderItem(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    qty: Optional[int] = None
    id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v):
        return (v or "")[:200].strip() if v else v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("price cannot be negative")
        return v

    @field_validator("qty")
    @classmethod
    def validate_qty(cls, v):
        if v is not None and (v < 1 or v > 1000):
            raise ValueError("qty must be between 1 and 1000")
        return v


class VerifyOrderBody(BaseModel):
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    items: List[OrderItem] = []
    address: Optional[AddressModel] = None
    total: float = 0

    @field_validator("razorpay_order_id", "razorpay_payment_id", "razorpay_signature")
    @classmethod
    def sanitize_ids(cls, v):
        if v and len(v) > 200:
            raise ValueError("ID too long")
        return v

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        if len(v) > 100:
            raise ValueError("Too many items (max 100)")
        return v

    @field_validator("total")
    @classmethod
    def validate_total(cls, v):
        if v < 0 or v > 10_000_000:
            raise ValueError("Invalid total amount")
        return round(v, 2)


# ── POST /api/orders/create-order ────────────────────────────────────────────────
@router.post("/create-order")
@limiter.limit("30/minute")
async def create_order(
    request: Request,
    body: CreateOrderBody,
    current_user: Optional[dict] = Depends(optional_auth),
):
    rz = get_razorpay()
    if not rz:
        mock_id = "order_mock_" + uuid_lib.uuid4().hex[:16]
        return {
            "order": {
                "id": mock_id,
                "amount": round(body.amount * 100),
                "currency": body.currency,
                "receipt": body.receipt or str(uuid_lib.uuid4()),
                "status": "created",
                "_mock": True,
            },
            "key": "rzp_test_MOCK",
            "mock": True,
        }
    try:
        order = rz.order.create({
            "amount": round(body.amount * 100),
            "currency": body.currency,
            "receipt": (body.receipt or str(uuid_lib.uuid4()))[:40],
        })
        return {"order": order, "key": os.getenv("RAZORPAY_KEY_ID")}
    except Exception as e:
        raise HTTPException(500, "Failed to create payment order")


# ── POST /api/orders/verify ──────────────────────────────────────────────────────
@router.post("/verify")
@limiter.limit("30/minute")
async def verify_order(
    request: Request,
    body: VerifyOrderBody,
    current_user: Optional[dict] = Depends(optional_auth),
):
    secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    order_id = body.razorpay_order_id or ""
    payment_id = body.razorpay_payment_id or ""
    signature = body.razorpay_signature or ""

    is_mock = not order_id or "mock" in order_id or signature == "mock_sig"

    if not is_mock and secret and is_real_key(os.getenv("RAZORPAY_KEY_ID", ""), secret):
        expected = hmac.new(
            secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(400, "Payment verification failed — invalid signature")

    uid = current_user["id"] if current_user else None
    items = [i.model_dump(exclude_none=True) for i in body.items]
    address = body.address.model_dump(exclude_none=True) if body.address else {}

    if is_connected():
        result = await get_db().orders.insert_one({
            "userId": uid,
            "razorpayOrderId": order_id[:100],
            "razorpayPaymentId": payment_id[:100],
            "items": items, "address": address,
            "total": body.total, "status": "paid",
            "createdAt": datetime.now(timezone.utc),
        })
        order_doc_id = str(result.inserted_id)
    else:
        order_doc = json_db.push("orders", {
            "id": str(uuid_lib.uuid4()), "userId": uid,
            "razorpayOrderId": order_id[:100], "razorpayPaymentId": payment_id[:100],
            "items": items, "address": address,
            "total": body.total, "status": "paid",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
        order_doc_id = order_doc["id"]

    return {"success": True, "message": "🌿 Order placed! Your plants are on the way.", "orderId": order_doc_id}


# ── GET /api/orders ──────────────────────────────────────────────────────────────
@router.get("/")
async def get_orders(current_user: dict = Depends(require_auth)):
    uid = current_user["id"]
    if is_connected():
        cursor = get_db().orders.find({"userId": uid}).sort("createdAt", -1).limit(50)
        orders = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            doc.pop("userId", None)  # Don't expose userId
            orders.append(doc)
    else:
        orders = sorted(
            [o for o in json_db.get("orders") if o.get("userId") == uid],
            key=lambda o: o.get("createdAt", ""), reverse=True,
        )[:50]
    return {"orders": orders}


# ── GET /api/orders/{id} ─────────────────────────────────────────────────────────
@router.get("/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(require_auth)):
    # Validate order_id format
    if not re.match(r"^[a-f0-9]{24}$|^[0-9a-f\-]{36}$", order_id, re.IGNORECASE):
        raise HTTPException(400, "Invalid order ID format")

    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        try:
            doc = await get_db().orders.find_one({"_id": ObjectId(order_id), "userId": uid})
        except Exception:
            raise HTTPException(400, "Invalid order ID")
        if not doc:
            raise HTTPException(404, "Order not found")
        doc["id"] = str(doc.pop("_id"))
        doc.pop("userId", None)
        return {"order": doc}
    else:
        order = json_db.find_one("orders", lambda o: o["id"] == order_id and o.get("userId") == uid)
        if not order:
            raise HTTPException(404, "Order not found")
        return {"order": order}
