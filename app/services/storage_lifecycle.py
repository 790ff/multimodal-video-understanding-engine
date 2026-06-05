from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from app.domain.errors import StorageAppError
from app.services.storage_paths import ensure_path_within

if TYPE_CHECKING:
    from app.repositories.video_repository import VideoRepository


RUNTIME_KEEP_FILE = ".gitkeep"


@dataclass(frozen=True)
class StorageCleanupReport:
    removed_paths: tuple[Path, ...] = ()
    kept_paths: tuple[Path, ...] = ()


class RuntimeStorageLifecycle:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def runtime_roots(self) -> tuple[Path, Path, Path]:
        return (
            self.settings.upload_dir,
            self.settings.audio_dir,
            self.settings.frame_dir,
        )

    def ensure_runtime_dirs(self) -> None:
        for root in self.runtime_roots:
            root_path = self._root_path(root)
            root_path.mkdir(parents=True, exist_ok=True)
            self._ensure_keep_file(root_path)

    def reset_runtime_dirs(self) -> StorageCleanupReport:
        removed_paths: list[Path] = []
        kept_paths: list[Path] = []
        for root in self.runtime_roots:
            root_path = self._root_path(root)
            root_path.mkdir(parents=True, exist_ok=True)
            for child in list(root_path.iterdir()):
                if child.name == RUNTIME_KEEP_FILE:
                    kept_paths.append(child)
                    continue
                self.remove_runtime_path(child, root=root_path)
                removed_paths.append(child)
            kept_paths.append(self._ensure_keep_file(root_path))

        return StorageCleanupReport(
            removed_paths=tuple(removed_paths),
            kept_paths=tuple(dict.fromkeys(kept_paths)),
        )

    def reset_local_data(
        self,
        *,
        repository: VideoRepository | None = None,
    ) -> StorageCleanupReport:
        if repository is not None:
            repository.clear_all_metadata()
        return self.reset_runtime_dirs()

    def cleanup_orphan_runtime_files(
        self,
        *,
        repository: VideoRepository,
    ) -> StorageCleanupReport:
        known_video_ids = set(repository.list_video_ids())
        removed_paths: list[Path] = []
        kept_paths: list[Path] = []

        for root in self.runtime_roots:
            root_path = self._root_path(root)
            root_path.mkdir(parents=True, exist_ok=True)
            for child in list(root_path.iterdir()):
                if child.name == RUNTIME_KEEP_FILE or child.name in known_video_ids:
                    kept_paths.append(child)
                    continue
                self.remove_runtime_path(child, root=root_path)
                removed_paths.append(child)
            kept_paths.append(self._ensure_keep_file(root_path))

        return StorageCleanupReport(
            removed_paths=tuple(removed_paths),
            kept_paths=tuple(dict.fromkeys(kept_paths)),
        )

    def prepare_clean_directory(
        self,
        path: Path,
        *,
        root: Path,
        code: str,
    ) -> Path:
        self.remove_runtime_path(path, root=root, code=code)
        safe_path = ensure_path_within(root, path, code=code)
        safe_path.mkdir(parents=True, exist_ok=True)
        return safe_path

    def ensure_parent_directory(
        self,
        path: Path,
        *,
        root: Path,
        code: str,
    ) -> Path:
        safe_path = ensure_path_within(root, path, code=code)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        return safe_path

    def is_nonempty_file(
        self,
        path: Path,
        *,
        root: Path,
        code: str,
    ) -> bool:
        safe_path = ensure_path_within(root, path, code=code)
        return safe_path.is_file() and safe_path.stat().st_size > 0

    def remove_runtime_path(
        self,
        path: Path,
        *,
        root: Path,
        code: str = "unsafe_storage_path",
    ) -> None:
        root_path = self._root_path(root)
        safe_path = ensure_path_within(root_path, path, code=code)
        if safe_path == root_path:
            raise StorageAppError(
                "Storage path is outside controlled runtime storage.",
                code=code,
            )
        if not safe_path.exists() and not safe_path.is_symlink():
            return
        if safe_path.is_symlink() or safe_path.is_file():
            safe_path.unlink()
            return
        shutil.rmtree(safe_path)

    def _root_path(self, root: Path) -> Path:
        return root.expanduser().resolve(strict=False)

    def _ensure_keep_file(self, root: Path) -> Path:
        keep_file = ensure_path_within(root, root / RUNTIME_KEEP_FILE)
        if not keep_file.exists():
            keep_file.write_text("", encoding="utf-8")
        return keep_file
