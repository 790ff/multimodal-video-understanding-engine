from __future__ import annotations

from pathlib import Path

from app.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def _active_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_env_example_documents_every_runtime_setting() -> None:
    env_keys = {line.split("=", maxsplit=1)[0] for line in _active_lines(ROOT / ".env.example")}
    setting_aliases = {field.alias for field in Settings.model_fields.values()}

    assert env_keys == setting_aliases


def test_env_example_keeps_provider_keys_blank() -> None:
    sensitive_keys = {"OPENAI_API_KEY", "GEMINI_API_KEY"}
    values = {}
    for line in _active_lines(ROOT / ".env.example"):
        key, value = line.split("=", maxsplit=1)
        values[key] = value.strip().strip('"')

    assert {key: values[key] for key in sensitive_keys} == {
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "",
    }


def test_gitignore_excludes_local_runtime_files() -> None:
    ignored_patterns = set(_active_lines(ROOT / ".gitignore"))

    assert ".env" in ignored_patterns
    assert "data/*.sqlite3" in ignored_patterns
    assert "data/*.sqlite3-*" in ignored_patterns
    assert "data/uploads/*" in ignored_patterns
    assert "data/audio/*" in ignored_patterns
    assert "data/frames/*" in ignored_patterns
