from __future__ import annotations

from pathlib import Path

from app.domain.errors import StorageAppError


def validate_storage_segment(segment: str, *, code: str = "unsafe_storage_path") -> str:
    if (
        not segment
        or segment in {".", ".."}
        or "/" in segment
        or "\\" in segment
        or any(ord(character) < 32 or ord(character) == 127 for character in segment)
    ):
        raise StorageAppError(
            "Storage path is outside controlled runtime storage.",
            code=code,
        )
    return segment


def controlled_child_path(
    root: Path,
    *segments: str,
    code: str = "unsafe_storage_path",
) -> Path:
    root_path = root.expanduser().resolve(strict=False)
    candidate = root_path
    for segment in segments:
        candidate = candidate / validate_storage_segment(str(segment), code=code)
    return ensure_path_within(root_path, candidate, code=code)


def ensure_path_within(root: Path, candidate: Path, *, code: str = "unsafe_storage_path") -> Path:
    root_path = root.expanduser().resolve(strict=False)
    candidate_path = candidate.expanduser().resolve(strict=False)
    if not candidate_path.is_relative_to(root_path):
        raise StorageAppError(
            "Storage path is outside controlled runtime storage.",
            code=code,
        )
    return candidate_path


def public_storage_reference(
    path: Path,
    *,
    root: Path,
    public_root: str,
    code: str = "unsafe_media_reference",
) -> str:
    root_path = root.expanduser().resolve(strict=False)
    safe_path = ensure_path_within(root_path, path, code=code)
    relative_path = safe_path.relative_to(root_path).as_posix()
    return f"{public_root.strip('/')}/{relative_path}"
