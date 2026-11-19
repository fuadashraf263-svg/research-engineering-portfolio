"""Canonical AXG serialization for the ASCII-only semantic subset in v0.1."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _validate(value: Any) -> None:
    if isinstance(value, str):
        value.encode("ascii")
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        return
    if isinstance(value, list):
        for item in value:
            _validate(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical AXG object keys must be strings")
            key.encode("ascii")
            _validate(item)
        return
    raise TypeError(f"unsupported canonical AXG type: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Stable JCS-compatible serialization for AXG v0.1's ASCII subset.

    Decimal engineering quantities are represented as strings before this point,
    avoiding binary floating-point ambiguity. Full Unicode JCS support is a
    required future conformance upgrade before non-ASCII identifiers are allowed.
    """
    _validate(value)
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def hashed_record(record: dict[str, Any], field: str = "revision") -> dict[str, Any]:
    if field in record:
        raise ValueError(f"record already has {field}")
    result = dict(record)
    result[field] = "sha256:" + sha256_digest(record)
    return result
