from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse

from app.domain.errors import AppError

REDACTED_VALUE = "[redacted]"

SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|credential)s?\b"),
    re.compile(r"(?i)\b(?:openai_api_key|gemini_api_key)\b"),
    re.compile(r"(?i)\.env\b"),
    re.compile(r"(?i)traceback \(most recent call last\)"),
    re.compile(r'(?i)\bfile "[^"]+", line \d+'),
    re.compile(r"(?:/Users|/home|/var|/tmp|/private/tmp)/[^\s,;:]+"),
    re.compile(r"[A-Za-z]:\\[^\r\n\t ]+"),
)


def app_error_response(exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": safe_error_message(exc.message, fallback=exc.__class__.message),
                "details": sanitize_error_details(exc.details),
            }
        },
    )


def request_validation_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "request_validation_error",
                "message": "Request validation failed.",
                "details": {},
            }
        },
    )


def internal_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "Internal server error.",
                "details": {},
            }
        },
    )


def safe_error_message(message: str, *, fallback: str) -> str:
    return fallback if _contains_sensitive_text(message) else message


def sanitize_error_details(details: Mapping[str, object] | None) -> dict[str, object]:
    if not details:
        return {}

    sanitized: dict[str, object] = {}
    for key, value in details.items():
        key_text = str(key)
        if _contains_sensitive_text(key_text):
            continue
        sanitized[key_text] = _sanitize_value(value)
    return sanitized


def _sanitize_value(value: object) -> object:
    if isinstance(value, Path):
        return REDACTED_VALUE if _contains_sensitive_text(str(value)) else str(value)
    if isinstance(value, str):
        return REDACTED_VALUE if _contains_sensitive_text(value) else value
    if isinstance(value, Mapping):
        return sanitize_error_details(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _sanitize_value(str(value))


def _contains_sensitive_text(value: Any) -> bool:
    text = str(value)
    return any(pattern.search(text) for pattern in SENSITIVE_TEXT_PATTERNS)
