"""Reads C2PA (Coalition for Content Provenance and Authenticity) manifest
data embedded in an image, when present. This is the same provenance-metadata
layer Meta itself reads first for its "AI info" labels on Facebook/Instagram,
before falling back to a purely visual/perceptual classifier (which is what
app.providers.ai_detection already does via Sightengine). A manifest here is
a much stronger signal than a perceptual guess - it's a (potentially signed)
declaration made by the tool that created or edited the file - but most
ordinary photos/forwards carry no manifest at all, which is the normal case,
not an error.

Uses the `c2pa-python` package (Rust bindings, Apache-2.0/MIT), an optional
dependency (see pyproject.toml's `real` extra) because it needs Python 3.10+
- on an older interpreter, or when the package simply isn't installed, this
degrades gracefully to "no manifest data available", the same pattern
app.services.video_processing uses for a missing ffmpeg binary."""

import io
from typing import Any, Optional

from pydantic import BaseModel

from app.logging_conf import get_logger

logger = get_logger(__name__)

# IPTC digital-source-type values (https://cv.iptc.org/newscodes/digitalsourcetype/)
# that indicate the asset was produced or substantially composed by a
# generative/trained algorithm, as opposed to e.g. a plain digital camera
# capture or a minor human edit.
_AI_DIGITAL_SOURCE_TYPES = {
    "trainedAlgorithmicMedia",
    "compositeWithTrainedAlgorithmicMedia",
    "algorithmicMedia",
}


class C2PAResult(BaseModel):
    has_manifest: bool
    generator: Optional[str] = None
    digital_source_type: Optional[str] = None
    is_ai_indicated: bool = False
    summary: Optional[str] = None


def _extract_generator(manifest: dict) -> Optional[str]:
    generator_info = manifest.get("claim_generator_info")
    if isinstance(generator_info, list) and generator_info:
        name = generator_info[0].get("name")
        if name:
            return name
    claim_generator = manifest.get("claim_generator")
    if isinstance(claim_generator, str) and claim_generator:
        return claim_generator.split("/")[0].replace("_", " ")
    return None


def _find_digital_source_type(node: Any) -> Optional[str]:
    """Recursively searches the manifest JSON for a `digitalSourceType`
    field. Its exact nesting has shifted across C2PA manifest schema
    versions (typically inside an assertion action, but not guaranteed), so
    this walks the whole structure rather than assuming one fixed path."""
    if isinstance(node, dict):
        value = node.get("digitalSourceType")
        if isinstance(value, str):
            return value
        for child in node.values():
            found = _find_digital_source_type(child)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_digital_source_type(item)
            if found:
                return found
    return None


def _classify_digital_source_type(source_type: Optional[str]) -> bool:
    if not source_type:
        return False
    # Values are URIs (e.g. ".../trainedAlgorithmicMedia") in some manifests
    # and bare terms in others - match on the trailing segment either way.
    term = source_type.rsplit("/", 1)[-1]
    return term in _AI_DIGITAL_SOURCE_TYPES


def _summarize(generator: Optional[str], is_ai_indicated: bool) -> str:
    who = f" by {generator}" if generator else ""
    if is_ai_indicated:
        return f"This file carries a Content Credentials (C2PA) manifest recording it as AI-generated/edited{who}."
    return f"This file carries a Content Credentials (C2PA) manifest{who} with no AI-generation marker."


def check_manifest(media_bytes: bytes, format_hint: str = "image/jpeg") -> C2PAResult:
    """Best-effort: any failure (library not installed, unsupported
    interpreter, no embedded manifest, an unparseable/corrupt one) is
    treated the same as "no manifest found" rather than raised - this must
    never be what breaks a verification."""
    try:
        import c2pa
    except Exception:
        # Not just ImportError: on an interpreter older than the bindings'
        # minimum (they use `match` syntax, Python 3.10+) the import itself
        # raises a SyntaxError rather than failing to be found.
        logger.debug("c2pa_unavailable")
        return C2PAResult(has_manifest=False)

    try:
        reader = c2pa.Reader(format_hint, io.BytesIO(media_bytes))
        manifest = reader.get_active_manifest()
    except Exception:
        return C2PAResult(has_manifest=False)

    if not manifest:
        return C2PAResult(has_manifest=False)

    generator = _extract_generator(manifest)
    source_type = _find_digital_source_type(manifest)
    is_ai_indicated = _classify_digital_source_type(source_type)

    return C2PAResult(
        has_manifest=True,
        generator=generator,
        digital_source_type=source_type,
        is_ai_indicated=is_ai_indicated,
        summary=_summarize(generator, is_ai_indicated),
    )
