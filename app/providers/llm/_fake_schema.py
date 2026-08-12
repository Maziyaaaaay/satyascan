import hashlib
from enum import Enum
from typing import Any, List, Type, Union, get_args, get_origin

from pydantic import BaseModel


def _seed_int(seed: str, salt: str) -> int:
    digest = hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _fake_value(annotation: Any, seed: str, field_name: str) -> Any:
    n = _seed_int(seed, field_name)
    origin = get_origin(annotation)

    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if not args:
            return None
        return _fake_value(args[0], seed, field_name)

    if origin in (list, List):
        args = get_args(annotation)
        item_type = args[0] if args else str
        count = 1 + (n % 2)
        return [_fake_value(item_type, seed, f"{field_name}[{i}]") for i in range(count)]

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        members = list(annotation)
        return members[n % len(members)]

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return fake_instance(annotation, seed=f"{seed}:{field_name}")

    if annotation is bool:
        return n % 2 == 0
    if annotation is int:
        return n % 100
    if annotation is float:
        return round((n % 1000) / 1000, 4)
    if annotation is str:
        return f"mock-{field_name}-{n % 0xFFFF:04x}"
    return None


def fake_instance(model_cls: Type[BaseModel], seed: str) -> BaseModel:
    """Deterministically synthesize a valid instance of a pydantic model from
    a seed string, so MockLLMProvider.generate() can satisfy an arbitrary
    response_schema without knowing anything about the caller's domain."""
    values = {}
    for name, field in model_cls.model_fields.items():
        values[name] = _fake_value(field.annotation, seed, name)
    return model_cls(**values)
