import hashlib
from enum import Enum
from typing import Any, List, Type, Union, get_args, get_origin

from pydantic import BaseModel


def _seed_int(seed: str, salt: str) -> int:
    digest = hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


# Long-form text fields (shown directly to a human in the simulator UI) get a
# readable canned sentence instead of "mock-fieldname-a1b2" - still fully
# deterministic per seed, just legible. This does NOT make the mock's content
# semantically accurate to the actual claim - it's a UI-readability aid only,
# not a substitute for a real LLM key (see NEXT_STEPS.md).
_SENTENCE_BANK = {
    "explanation": [
        "This claim does not appear to be well-supported by the evidence found. "
        "The sources reviewed do not confirm the specific details being circulated.",
        "The available evidence suggests this claim is misleading. Similar claims "
        "have previously been traced back to unreliable or out-of-context sources.",
        "Based on cross-referenced sources, this appears to be an established, "
        "verifiable fact rather than a fabrication.",
        "There isn't enough reliable evidence to confirm or deny this claim right "
        "now - treat it with caution until better sourcing is available.",
        "This looks like a satirical or exaggerated claim rather than a genuine "
        "factual statement - it shouldn't be taken at face value.",
    ],
    "rationale": [
        "The evidence gathered leans toward contradicting the claim, with limited "
        "corroboration from credible sources.",
        "Multiple pieces of evidence were found, but they disagree with each other "
        "on key details, lowering overall certainty.",
        "The strongest available sources directly support the claim as stated.",
        "No strong evidence was found either way, so the claim is treated as "
        "unverifiable rather than confirmed false.",
        "The framing and content pattern match known satire rather than a literal "
        "factual claim.",
    ],
}


def _sentence_for(field_name: str, n: int) -> str:
    bank = _SENTENCE_BANK[field_name]
    return bank[n % len(bank)]


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
        if field_name in _SENTENCE_BANK:
            return _sentence_for(field_name, n)
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
