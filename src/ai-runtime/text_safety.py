from __future__ import annotations

import re
from typing import Any


_CREDENTIAL_VALUE_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|password|secret|authorization)\s*[:=]\s*['\"]?([^\s,'\";]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,'\";]+")
_MAX_UNTRUSTED_TEXT_LENGTH = 300


def sanitize_untrusted_text(value: Any) -> str:
    """Bound and redact obvious credential patterns in outbound untrusted text."""

    text = str(value)
    text = _BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    text = _CREDENTIAL_VALUE_PATTERN.sub(r"\1=[REDACTED]", text)
    return text[:_MAX_UNTRUSTED_TEXT_LENGTH]