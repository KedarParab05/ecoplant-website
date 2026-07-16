"""
routers/orders.py — Razorpay payments + order management
"""

import os
import hashlib
import hmac
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db.database import is_connected, get_db, json_db
from middleware.auth import require_auth, optional_auth

router = APIRouter(prefix="/api/orders", tags=["orders"])

_razorpay = None


def is_real_key(key_id: str, secret: str) -> bool:
    if not key_id or not secret:
        return False
    if "XXXX" in key_id or "XXXX" in secret:
        return False
    if len(key_id) < 20 or len(secret) < 20:
        return False
    if not key_id.startswith("rzp_"):
        return False
    return True


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


class AddressModel(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None


class OrderItem(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    qty: Optional[int] = None
    id: Optional[int] = None


class VerifyOrderBody(BaseModel):
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    items: List[OrderItem] = []
    address: Optional[AddressModel] = None
    total: float = 0


# ── POST /api/orders/create-order ───────────────────────────────────────────────
@router.post("/create-order")
async def create_order(body: CreateOrderBody, current_user: Optional[dict] = Depends(optional_auth)):
    if body.amount < 1:
        raise HTTPException(400, "amount > 0 is required")

    rz = get_razorpay()
    if not rz:
        mock_id = "order_mock_" + uuid_lib.uuid4().hex[:16]
        mock_order = {
            "id": mock_id,
            "amount": round(body.amount * 100),
            "currency": body.currency,
            "receipt": body.receipt or str(uuid_lib.uuid4()),
            "status": "created",
            "_mock": True,
        }
        return {"order": mock_order, "key": "rzp_test_MOCK", "mock": True}

    try:
        order = rz.order.create({
            "amount": round(body.amount * 100),
            "currency": body.currency,
            "receipt": body.receipt or str(uuid_lib.uuid4()),
        })
        return {"order": order, "key": os.getenv("RAZORPAY_KEY_ID")}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── POST /api/orders/verify ──────────────────────────────────────────────────────
@router.post("/verify")
async def verify_order(body: VerifyOrderBody, current_user: Optional[dict] = Depends(optional_auth)):
    secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    order_id = body.razorpay_order_id or ""
    payment_id = body.razorpay_payment_id or ""
    signature = body.razorpay_signature or ""

    is_mock = not order_id or "mock" in order_id or signature == "mock_sig"

    if not is_mock and secret and is_real_key(os.getenv("RAZORPAY_KEY_ID", ""), secret):
        mac = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256)
        expected = mac.hexdigest()
        if expected != signature:
            raise HTTPException(400, "Payment verification failed — invalid signature")

    uid = current_user["id"] if current_user else None
    items = [i.model_dump() for i in body.items]
    address = body.address.model_dump() if body.address else {}

    if is_connected():
        result = await get_db().orders.insert_one({
            "userId": uid,
            "razorpayOrderId": order_id,
            "razorpayPaymentId": payment_id,
            "items": items, "address": address,
            "total": body.total, "status": "paid",
            "createdAt": datetime.now(timezone.utc),
        })
        order_doc_id = str(result.inserted_id)
    else:
        order_doc = json_db.push("orders", {
            "id": str(uuid_lib.uuid4()), "userId": uid,
            "razorpayOrderId": order_id, "razorpayPaymentId": payment_id,
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
        cursor = get_db().orders.find({"userId": uid}).sort("createdAt", -1)
        orders = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            orders.append(doc)
    else:
        orders = sorted(
            [o for o in json_db.get("orders") if o.get("userId") == uid],
            key=lambda o: o.get("createdAt", ""), reverse=True,
        )
    return {"orders": orders}


# ── GET /api/orders/{id} ─────────────────────────────────────────────────────────
@router.get("/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(require_auth)):
    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        doc = await get_db().orders.find_one({"_id": ObjectId(order_id), "userId": uid})
        if not doc:
            raise HTTPException(404, "Order not found")
        doc["id"] = str(doc.pop("_id"))
        return {"order": doc}
    else:
        order = json_db.find_one("orders", lambda o: o["id"] == order_id and o.get("userId") == uid)
        if not order:
            raise HTTPException(404, "Order not found")
        return {"order": order}
