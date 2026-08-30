"""Builds the WhatsApp-facing verdict report text, in SatyaScan's own
voice: a short badge line, the claim as understood, the verdict with an
emoji + confidence, a plain-language "what we found", and (for images) a
provenance-first image-check section - C2PA manifest data (when present) is
shown ahead of the perceptual AI-detector line, mirroring the order Meta's
own AI-content labels use (read embedded provenance metadata first, fall
back to visual-artifact classification second).

Kept separate from app.routers.webhook_whatsapp so the formatting itself is
testable without a DB session or a fake Verification/Image ORM instance."""

from typing import Optional

from app.models.enums import ConfidenceLabel, Language, Verdict

_VERDICT_EMOJI = {
    Verdict.true: "✅",
    Verdict.false: "❌",
    Verdict.misleading: "⚠️",
    Verdict.unverifiable: "❓",
    Verdict.satire: "🎭",
}

_VERDICT_LABELS = {
    Language.en: {
        (Verdict.true, True): "TRUE",
        (Verdict.true, False): "LIKELY TRUE",
        (Verdict.false, True): "FALSE",
        (Verdict.false, False): "LIKELY FALSE",
        (Verdict.misleading, True): "MISLEADING",
        (Verdict.misleading, False): "MISLEADING",
        (Verdict.unverifiable, True): "UNVERIFIABLE",
        (Verdict.unverifiable, False): "UNVERIFIABLE",
        (Verdict.satire, True): "SATIRE",
        (Verdict.satire, False): "SATIRE",
    },
    Language.ml: {
        (Verdict.true, True): "ശരി",
        (Verdict.true, False): "മിക്കവാറും ശരി",
        (Verdict.false, True): "തെറ്റ്",
        (Verdict.false, False): "മിക്കവാറും തെറ്റ്",
        (Verdict.misleading, True): "തെറ്റിദ്ധരിപ്പിക്കുന്നത്",
        (Verdict.misleading, False): "തെറ്റിദ്ധരിപ്പിക്കുന്നത്",
        (Verdict.unverifiable, True): "സ്ഥിരീകരിക്കാൻ കഴിയില്ല",
        (Verdict.unverifiable, False): "സ്ഥിരീകരിക്കാൻ കഴിയില്ല",
        (Verdict.satire, True): "ആക്ഷേപഹാസ്യം",
        (Verdict.satire, False): "ആക്ഷേപഹാസ്യം",
    },
}

_SECTION_LABELS = {
    Language.en: {
        "badge": "🛡️ *SatyaScan Verdict*",
        "claim": "🔎 *Claim:*",
        "confidence_suffix": "confidence",
        "found": "📋 *What we found:*",
        "image": "🖼️ *Image check:*",
        "footer": "📎 _Forward another claim, image, or video anytime._",
    },
    Language.ml: {
        "badge": "🛡️ *സത്യസ്‌കാൻ വിധി*",
        "claim": "🔎 *അവകാശവാദം:*",
        "confidence_suffix": "വിശ്വാസ്യത",
        "found": "📋 *ഞങ്ങൾ കണ്ടെത്തിയത്:*",
        "image": "🖼️ *ചിത്ര പരിശോധന:*",
        "footer": "📎 _എപ്പോൾ വേണമെങ്കിലും മറ്റൊരു അവകാശവാദം, ചിത്രം, വീഡിയോ ഫോർവേഡ് ചെയ്യൂ._",
    },
}

_IMAGE_VERDICT_TEXT = {
    Language.en: {
        "ai": "This image appears to be AI-generated or fabricated.",
        "real": "This image appears to be a real, unedited photo.",
        "unsure": "Could not confidently determine if this image is AI-generated.",
    },
    Language.ml: {
        "ai": "ഈ ചിത്രം AI ഉപയോഗിച്ച് നിർമ്മിച്ചതോ കൃത്രിമമായി ഉണ്ടാക്കിയതോ ആകാം.",
        "real": "ഈ ചിത്രം യഥാർത്ഥവും തിരുത്തപ്പെടാത്തതുമായ ഫോട്ടോ ആണെന്ന് തോന്നുന്നു.",
        "unsure": "ഈ ചിത്രം AI നിർമ്മിതമാണോ എന്ന് ഉറപ്പിച്ച് പറയാൻ കഴിയില്ല.",
    },
}


def verdict_label(verdict: Optional[Verdict], confidence_label: Optional[ConfidenceLabel], language: Language) -> str:
    if verdict is None:
        return _VERDICT_LABELS[language][(Verdict.unverifiable, True)]
    is_high_confidence = confidence_label == ConfidenceLabel.high
    return _VERDICT_LABELS[language][(verdict, is_high_confidence)]


def perceptual_image_line(ai_generated_probability: Optional[float], language: Language) -> str:
    texts = _IMAGE_VERDICT_TEXT[language]
    if ai_generated_probability is None:
        return texts["unsure"]
    if ai_generated_probability >= 0.6:
        return texts["ai"]
    if ai_generated_probability <= 0.3:
        return texts["real"]
    return texts["unsure"]


def build_verdict_report(
    *,
    language: Language,
    verdict: Optional[Verdict],
    confidence_score: Optional[float],
    confidence_label: Optional[ConfidenceLabel],
    claim_text: Optional[str],
    explanation_text: Optional[str],
    image_lines: Optional[list] = None,
) -> str:
    """Pure formatter: every value comes in as a primitive so this needs no
    DB session and no ORM instance - see app.routers.webhook_whatsapp for
    the thin wrapper that pulls those values off a Verification/Image row."""
    labels = _SECTION_LABELS[language]
    emoji = _VERDICT_EMOJI.get(verdict, "❓")
    confidence_pct = round((confidence_score or 0.0) * 100)
    label = verdict_label(verdict, confidence_label, language)

    lines = [labels["badge"], ""]
    if claim_text:
        lines += [f"{labels['claim']} {claim_text}", ""]
    lines += [f"{emoji} *{label}* — {confidence_pct}% {labels['confidence_suffix']}", ""]
    if explanation_text:
        lines += [labels["found"], explanation_text, ""]
    if image_lines:
        lines += [labels["image"]]
        lines += list(image_lines)
        lines += [""]
    lines.append(labels["footer"])

    return "\n".join(lines).strip()
