"""Small fail-closed JSON Schema subset for provider-neutral structured output.

Unsupported validation keywords raise rather than silently accepting output.
Workflows can also supply a domain validator to ModelRouter.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


_COMMON = {"type", "enum", "description", "title"}
_BY_TYPE = {
    "object": {"properties", "required", "additionalProperties"},
    "array": {"items", "minItems", "maxItems"},
    "string": {"minLength", "maxLength"},
    "number": {"minimum", "maximum"},
    "integer": {"minimum", "maximum"},
    "boolean": set(),
    "null": set(),
}


def validate_schema(schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ValueError("Structured output schema must have an object root")
    _check_schema(schema)


def _check_schema(schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping):
        raise ValueError("Invalid structured output schema")
    kind = schema.get("type")
    if not isinstance(kind, str) or kind not in _BY_TYPE or set(schema) - (_COMMON | _BY_TYPE[kind]):
        raise ValueError("Unsupported structured output schema keyword")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        raise ValueError("Invalid schema enum")
    if kind == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, Mapping) or any(not isinstance(key, str) for key in properties) or not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            raise ValueError("Invalid object schema")
        if set(required) - set(properties):
            raise ValueError("Required property has no schema")
        if not isinstance(schema.get("additionalProperties", True), bool):
            raise ValueError("Only boolean additionalProperties is supported")
        for child in properties.values():
            _check_schema(child)
    if kind == "array":
        _check_schema(schema.get("items", {}))
    for lower, upper in (("minItems", "maxItems"), ("minLength", "maxLength"), ("minimum", "maximum")):
        if lower in schema and (not isinstance(schema[lower], (int, float)) or isinstance(schema[lower], bool) or schema[lower] < 0 and lower != "minimum"):
            raise ValueError("Invalid schema bound")
        if upper in schema and (not isinstance(schema[upper], (int, float)) or isinstance(schema[upper], bool) or schema[upper] < 0 and upper != "maximum"):
            raise ValueError("Invalid schema bound")
        if lower in schema and upper in schema and schema[lower] > schema[upper]:
            raise ValueError("Invalid schema bound order")
    for key in ("minItems", "maxItems", "minLength", "maxLength"):
        if key in schema and not isinstance(schema[key], int):
            raise ValueError("Length bounds must be integers")


def parse_structured(content: str, schema: Mapping[str, Any]) -> Any:
    validate_schema(schema)

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Model output contains duplicate fields")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("Non-finite JSON value")

    try:
        value = json.loads(content, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Model returned invalid JSON") from exc
    _validate(value, schema)
    return value


def _validate(value: Any, schema: Mapping[str, Any]) -> None:
    kind = schema["type"]
    valid_type = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
        "null": lambda x: x is None,
    }[kind]
    if not valid_type(value) or ("enum" in schema and value not in schema["enum"]):
        raise ValueError("Model output does not match structured schema")
    if kind == "object":
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            raise ValueError("Model output lacks a required field")
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise ValueError("Model output has an unexpected field")
        for key, child in properties.items():
            if key in value:
                _validate(value[key], child)
    elif kind == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            raise ValueError("Model output array length is invalid")
        for item in value:
            _validate(item, schema["items"])
    elif kind == "string":
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
            raise ValueError("Model output string length is invalid")
    elif kind in {"number", "integer"}:
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise ValueError("Model output number is outside its allowed range")
