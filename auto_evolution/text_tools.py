from __future__ import annotations


def extract_tail(text: str, max_length: int = 1200) -> str:
    raw = str(text or "")
    if len(raw) <= max_length:
        return raw.strip()
    return f"...{raw[-max_length:].strip()}"


def sanitize_commit_message(message: str) -> str:
    return " ".join(str(message or "").split()).strip()[:180]
