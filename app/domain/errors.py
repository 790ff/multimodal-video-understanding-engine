from __future__ import annotations

from typing import Optional


class AppError(Exception):
    status_code = 500
    code = "application_error"
    message = "An application error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, object]] = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}


class ValidationAppError(AppError):
    status_code = 400
    code = "validation_error"
    message = "Request validation failed."


class FileTooLargeAppError(AppError):
    status_code = 413
    code = "file_too_large"
    message = "Uploaded file is too large."


class NotFoundAppError(AppError):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictAppError(AppError):
    status_code = 409
    code = "conflict"
    message = "The requested operation conflicts with the current state."


class ProcessingAppError(AppError):
    status_code = 500
    code = "processing_error"
    message = "Video processing failed."


class StorageAppError(AppError):
    status_code = 500
    code = "storage_error"
    message = "Video storage failed."
