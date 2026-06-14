from __future__ import annotations

import json
import re
from typing import Any


_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Extract the first JSON object/array from an LLM response."""

    text = text.strip()
    fence = _CODE_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    first_obj = text.find("{")
    first_arr = text.find("[")
    candidates = [i for i in [first_obj, first_arr] if i != -1]
    if not candidates:
        raise ValueError(f"No JSON object or array found in response: {text[:300]}")

    start = min(candidates)
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    end = text.rfind(closing)
    if end == -1 or end <= start:
        raise ValueError(f"Could not locate end of JSON in response: {text[:300]}")

    return json.loads(text[start : end + 1])
