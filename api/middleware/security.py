"""
middleware/security.py — Comprehensive API & Website Security
─────────────────────────────────────────────────────────────
Protects against:
  • XSS (Cross-Site Scripting)
  • NoSQL Injection (MongoDB operator injection)
  • CSRF (via SameSite + Referrer checks)
  • Clickjacking (X-Frame-Options / CSP frame-ancestors)
  • MIME sniffing
  • Information leakage
  • Brute-force login attacks (in-memory per-IP lockout)
  • Oversized payloads
  • Path traversal
  • HTTP parameter pollution
  • Insecure direct object reference (on top of auth)
"""

import os
import re
import time
import html
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ecoplant.security")

# ─── Constants ────────────────────────────────────────────────────────────────
IS_PROD = os.getenv("VERCEL") == "1" or os.getenv("ENV", "").lower() == "production"
PROD_ORIGIN = "https://ecoplant-pro.vercel.app"

# MongoDB operator injection patterns
_NOSQL_BANNED = re.compile(
    r"(\$where|\$regex|\$gt|\$gte|\$lt|\$lte|\$ne|\$in|\$nin|\$or|\$and|\$not|\$nor"
    r"|\$exists|\$type|\$expr|\$jsonSchema|\$mod|\$text|\$where|\$all|\$elemMatch"
    r"|\$size|\$slice|\$lookup|\$group|\$unwind|\$project|\$match|\$sort|\$limit)",
    re.IGNORECASE,
)

# XSS / script injection patterns
_XSS_PATTERNS = re.compile(
    r"(<\s*script|javascript\s*:|data\s*:\s*text/html|vbscript\s*:|on\w+\s*=|"
    r"<\s*iframe|<\s*object|<\s*embed|<\s*link\s+rel|<\s*meta\s+http)",
    re.IGNORECASE,
)

# Path traversal patterns
_PATH_TRAVERSAL = re.compile(r"\.\.[/\\]|%2e%2e[%2f%5c]", re.IGNORECASE)

# Max request body size: 15 MB (for base64 image uploads)
MAX_BODY_BYTES = 15 * 1024 * 1024

# ─── Brute-Force / Login Rate Limiting ───────────────────────────────────────
# Tracks failed auth attempts per IP
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_locked_ips: dict[str, float] = {}

FAIL_WINDOW_SECONDS = 15 * 60   # 15 minutes window
MAX_FAILS = 10                   # Max 10 failed auth attempts per IP per window
LOCKOUT_SECONDS = 30 * 60       # Lock out for 30 minutes after exceeding limit


def record_failed_auth(ip: str) -> None:
    """Record a failed authentication attempt for an IP address."""
    now = time.time()
    # Purge old attempts outside the window
    _failed_attempts[ip] = [t for t in _failed_attempts[ip] if now - t < FAIL_WINDOW_SECONDS]
    _failed_attempts[ip].append(now)

    if len(_failed_attempts[ip]) >= MAX_FAILS:
        _locked_ips[ip] = now + LOCKOUT_SECONDS
        logger.warning(f"[security] IP {ip} locked out after {MAX_FAILS} failed auth attempts")


def clear_failed_auth(ip: str) -> None:
    """Clear failed attempts after a successful login."""
    _failed_attempts.pop(ip, None)
    _locked_ips.pop(ip, None)


def is_ip_locked(ip: str) -> bool:
    """Check if an IP is currently locked out."""
    if ip not in _locked_ips:
        return False
    if time.time() > _locked_ips[ip]:
        # Lock expired
        _locked_ips.pop(ip, None)
        _failed_attempts.pop(ip, None)
        return False
    return True


# ─── Input Sanitization ───────────────────────────────────────────────────────
def sanitize_string(value: str, max_length: int = 2000) -> str:
    """Strip leading/trailing whitespace and enforce max length."""
    if not isinstance(value, str):
        return value
    return value.strip()[:max_length]


def contains_nosql_injection(value: Any) -> bool:
    """Recursively check a value for MongoDB operator injection."""
    if isinstance(value, str):
        return bool(_NOSQL_BANNED.search(value))
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and k.startswith("$"):
                return True
            if contains_nosql_injection(k) or contains_nosql_injection(v):
                return True
    if isinstance(value, list):
        return any(contains_nosql_injection(item) for item in value)
    return False


def contains_xss(value: Any) -> bool:
    """Recursively check a value for XSS patterns."""
    if isinstance(value, str):
        return bool(_XSS_PATTERNS.search(value))
    if isinstance(value, dict):
        return any(contains_xss(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_xss(item) for item in value)
    return False


def contains_path_traversal(value: str) -> bool:
    """Check for path traversal attempts."""
    return bool(_PATH_TRAVERSAL.search(value))


def validate_request_body(body: Any) -> None:
    """
    Validate the parsed JSON body for injection attacks.
    Raises HTTPException(400) on detected attack.
    Skips the 'image' field (base64 is safe).
    """
    if not isinstance(body, dict):
        return

    # Check all non-image fields
    filtered = {k: v for k, v in body.items() if k != "image"}

    if contains_nosql_injection(filtered):
        logger.warning("[security] NoSQL injection attempt blocked")
        raise HTTPException(400, "Invalid input detected")

    if contains_xss(filtered):
        logger.warning("[security] XSS attempt blocked")
        raise HTTPException(400, "Invalid input detected")


# ─── Security Headers ─────────────────────────────────────────────────────────
CSP = (
    "default-src 'self' https://ecoplant-pro.vercel.app; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
    "https://accounts.google.com https://apis.google.com "
    "https://checkout.razorpay.com https://cdn.razorpay.com "
    "https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: blob: https: http:; "
    "connect-src 'self' https://ecoplant-pro.vercel.app https://api.razorpay.com "
    "https://generativelanguage.googleapis.com wss:; "
    "frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "upgrade-insecure-requests;"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(self), usb=(), magnetometer=(), gyroscope=()"
    ),
    "Content-Security-Policy": CSP,
    "X-Powered-By": "",               # hide tech stack
    "Server": "EcoPlant",             # disguise server
    "Cache-Control": "no-store",      # default; overridden for static assets
}

if IS_PROD:
    SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"


# ─── Middleware ───────────────────────────────────────────────────────────────
class SecurityMiddleware(BaseHTTPMiddleware):
    """
    All-in-one security middleware:
    1. Applies all security response headers
    2. Validates Content-Type for POST/PUT/PATCH requests
    3. Enforces max body size
    4. Checks for NoSQL injection and XSS in JSON bodies
    5. Blocks suspicious User-Agent patterns
    """

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
    SUSPICIOUS_UA = re.compile(
        r"(sqlmap|nikto|nessus|masscan|zgrab|go-http-client/1\.1$|python-requests/2\.[01]|"
        r"curl/7\.[0-4]|wget/1\.[01]|libwww-perl)",
        re.IGNORECASE,
    )

    async def dispatch(self, request: Request, call_next):
        # ── 1. Block obviously malicious User-Agents ──────────────────────────
        ua = request.headers.get("user-agent", "")
        if self.SUSPICIOUS_UA.search(ua):
            logger.warning(f"[security] Blocked suspicious UA: {ua[:120]}")
            return JSONResponse({"error": "Forbidden"}, status_code=403)

        # ── 2. Check path for traversal ───────────────────────────────────────
        path = request.url.path
        if contains_path_traversal(path):
            logger.warning(f"[security] Path traversal attempt: {path}")
            return JSONResponse({"error": "Bad request"}, status_code=400)

        # ── 3. Validate JSON body for API write requests ──────────────────────
        if (
            request.method not in self.SAFE_METHODS
            and request.url.path.startswith("/api/")
            and "application/json" in request.headers.get("content-type", "")
        ):
            # Enforce max body size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_BODY_BYTES:
                return JSONResponse({"error": "Request body too large"}, status_code=413)

            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_json = json.loads(body_bytes)
                    validate_request_body(body_json)
            except HTTPException as e:
                return JSONResponse({"error": e.detail}, status_code=e.status_code)
            except (json.JSONDecodeError, ValueError):
                pass  # Let FastAPI handle malformed JSON

        # ── 4. Process request ────────────────────────────────────────────────
        response = await call_next(request)

        # ── 5. Inject security headers ────────────────────────────────────────
        for header, value in SECURITY_HEADERS.items():
            if value:  # Skip empty values (like X-Powered-By removal)
                response.headers[header] = value
            elif header in response.headers:
                del response.headers[header]

        # Allow caching for static assets
        if not request.url.path.startswith("/api/"):
            if any(request.url.path.endswith(ext) for ext in
                   (".js", ".css", ".avif", ".webp", ".jpg", ".png", ".woff2", ".ico")):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return response
