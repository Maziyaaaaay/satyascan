from typing import Any, Dict, Type

from pydantic import BaseModel

# Gemini's response_schema (a protobuf Schema) only understands a narrow
# OpenAPI-3.0-like subset: type, format, description, nullable, enum, items,
# properties, required. Passing a pydantic class directly to the SDK and
# letting it auto-convert breaks on fields with defaults (confirmed against a
# live key: "ValueError: Unknown field for Schema: default"), and pydantic's
# own model_json_schema() emits $ref/$defs and JSON-Schema-only keys (title,
# default, additionalProperties) Gemini's Schema proto rejects. This module
# converts a pydantic model to the sanitized dict shape Gemini actually
# accepts, resolving $ref/$defs and allOf-wrapping (pydantic v2 wraps a $ref
# in allOf whenever the field also carries a default/description) inline.

_DROP_KEYS = {"title", "default", "additionalProperties", "examples"}


def _resolve(node: Any, defs: Dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_resolve(item, defs) for item in node]

    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        ref_name = node["$ref"].rsplit("/", 1)[-1]
        return _resolve(defs.get(ref_name, {}), defs)

    if "allOf" in node:
        merged: Dict[str, Any] = {}
        for sub in node["allOf"]:
            resolved_sub = _resolve(sub, defs)
            if isinstance(resolved_sub, dict):
                merged.update(resolved_sub)
        for k, v in node.items():
            if k not in ("allOf",) and k not in _DROP_KEYS:
                merged[k] = v
        return merged

    if "anyOf" in node:
        # Optional[X] -> anyOf: [X, null]. Gemini has no null type - use the
        # first non-null variant and drop the nullability distinction.
        for variant in node["anyOf"]:
            resolved_variant = _resolve(variant, defs)
            if isinstance(resolved_variant, dict) and resolved_variant.get("type") != "null":
                return resolved_variant
        return {"type": "string"}

    result: Dict[str, Any] = {}
    for key, value in node.items():
        if key in _DROP_KEYS or key == "$defs":
            continue
        if key == "properties":
            result[key] = {prop_name: _resolve(prop_val, defs) for prop_name, prop_val in value.items()}
        elif key == "items":
            result[key] = _resolve(value, defs)
        else:
            result[key] = value
    return result


def to_gemini_schema(model_cls: Type[BaseModel]) -> Dict[str, Any]:
    schema = model_cls.model_json_schema()
    defs = schema.get("$defs", {})
    return _resolve(schema, defs)
