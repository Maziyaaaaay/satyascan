import enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.providers.llm._gemini_schema import to_gemini_schema

_FORBIDDEN_KEYS = {"$ref", "$defs", "allOf", "anyOf", "title", "default", "additionalProperties"}


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in _FORBIDDEN_KEYS, f"forbidden key {key!r} leaked into Gemini schema: {node}"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


class _Verdict(str, enum.Enum):
    true = "true"
    false = "false"


class _WithDefaults(BaseModel):
    """Mirrors the real shape that broke against a live Gemini key: an enum
    field plus several fields with plain defaults."""

    verdict: _Verdict
    confidence: float = 0.5
    flag: bool = False


class _WithList(BaseModel):
    items: List[str] = Field(default_factory=list)


class _WithOptional(BaseModel):
    note: Optional[str] = None
    label: str


def test_strips_defaults_and_titles():
    schema = to_gemini_schema(_WithDefaults)
    _assert_no_forbidden_keys(schema)
    assert schema["properties"]["confidence"]["type"] == "number"
    assert schema["properties"]["flag"]["type"] == "boolean"


def test_inlines_enum_refs():
    schema = to_gemini_schema(_WithDefaults)
    verdict_schema = schema["properties"]["verdict"]
    assert "$ref" not in verdict_schema
    assert set(verdict_schema.get("enum", [])) == {"true", "false"}


def test_handles_list_fields():
    schema = to_gemini_schema(_WithList)
    _assert_no_forbidden_keys(schema)
    assert schema["properties"]["items"]["type"] == "array"
    assert schema["properties"]["items"]["items"]["type"] == "string"


def test_handles_optional_fields_without_null_type():
    schema = to_gemini_schema(_WithOptional)
    _assert_no_forbidden_keys(schema)
    note_schema = schema["properties"]["note"]
    assert note_schema.get("type") != "null"
