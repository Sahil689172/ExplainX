"""Safe prompt template formatting — never treat JSON braces as format fields."""

from __future__ import annotations

import json
from typing import Any


def dumps_schema(schema: Any) -> str:
    """Serialize a JSON schema example for embedding in prompts."""
    return json.dumps(schema, ensure_ascii=False, indent=2)


def format_prompt(template: str, **kwargs: Any) -> str:
    """Apply ``str.format`` with a clear error if a field is missing.

    JSON must never appear as literal ``{...}`` in ``template``. Pass schema
    text via ``dumps_schema(...)`` into a ``{schema_json}`` (or similar) field.
    Values substituted into the template are not re-scanned for format fields.
    """
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        raise KeyError(
            f"Prompt template missing field {exc.args[0]!r}; "
            f"provided keys={sorted(kwargs)}"
        ) from exc
    except ValueError as exc:
        raise ValueError(
            "Prompt template has invalid format syntax (unescaped braces?). "
            f"Error: {exc}"
        ) from exc
