"""Credential redaction. Used twice: by `land` when copying source bytes, and by
scripts/check_secrets.py before every commit. One pattern list, so the two can't drift — which also means a
shape neither pattern knows is missed by both. That is why CI runs gitleaks as an independent second scanner
(.github/workflows/ci.yml); this list is the first line, not a guarantee.

Each pattern names what it catches; the replacement is `<redacted:NAME>` so a reader of the
landed file can see that something was removed and what kind of thing it was.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Pattern

# (name, compiled regex, replacement-template). Templates may reference groups of the match.
PATTERNS: list[tuple[str, Pattern[str], str]] = [
    ("hf_token",      re.compile(r"hf_[A-Za-z0-9]{20,}"),                       "<redacted:hf_token>"),
    ("runpod_key",    re.compile(r"rpa_[A-Za-z0-9]{20,}"),                      "<redacted:runpod_key>"),
    # covers OpenAI sk-..., OpenRouter sk-or-v1-..., Anthropic sk-ant-...
    ("sk_key",        re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),                    "<redacted:sk_key>"),
    ("github_token",  re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),                "<redacted:github_token>"),
    ("github_pat",    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),              "<redacted:github_pat>"),   # fine-grained PATs
    ("aws_access_key", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),                "<redacted:aws_access_key>"),
    ("slack_token",   re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),             "<redacted:slack_token>"),
    # whole PEM block, header to footer; a truncated block (no footer) is redacted to the end of the text
    ("private_key",   re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "<redacted:private_key>"),
    ("private_key_truncated", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*"), "<redacted:private_key>"),
    ("jwt",           re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "<redacted:jwt>"),
    ("bearer",        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._+/=\-]{20,}"),    "Bearer <redacted:bearer>"),
    # key=value and "key": "value" forms where the key name contains a secret-ish word — including compound names
    # such as AWS_SECRET_ACCESS_KEY or OPENROUTER_API_KEY. Keeps the key, quotes and separator, drops the value.
    # The value class allows base64 (+ / =) and excludes '<' so already-redacted values don't re-match; a purely
    # numeric value is not a secret ("first_token_s": 2073169.405621416 is a timestamp).
    ("kv_secret",
     re.compile(r"(?i)([A-Za-z0-9_\-]*(?:api[_-]?key|secret|token(?!izer)|password|passwd|authorization|credential)[A-Za-z0-9_\-]*)"
                r"(['\"]?\s*[:=]\s*['\"]?)(?![0-9.]{16,}(?![A-Za-z0-9+/=_\-]))([A-Za-z0-9+/=._\-]{16,})"),
     r"\1\2<redacted:kv_secret>"),
]


def redact(text: str) -> tuple[str, Counter]:
    """Return (redacted_text, Counter{pattern_name: hits})."""
    hits: Counter = Counter()
    for name, rx, repl in PATTERNS:
        text, n = rx.subn(repl, text)
        if n:
            hits[name] += n
    return text, hits


def find(text: str) -> list[tuple[str, str]]:
    """Return [(pattern_name, masked_match)] without modifying anything. For the pre-commit scan."""
    out = []
    for name, rx, _ in PATTERNS:
        for m in rx.finditer(text):
            s = m.group(0)
            out.append((name, s[:6] + "…" + s[-3:] if len(s) > 12 else s[:3] + "…"))
    return out
