"""Builds the WhatsApp-facing verdict report text, in SatyaScan's own
voice: a short badge line, then a shape that depends on what kind of
message this was (see SourceMediaType) - a plain text claim is led with
"Claim:", a photo leads with the image findings themselves (there's often
no caption to "verify"), and a video splits what came from the extracted
frame (visual authenticity) from what came from the audio track (the
actual spoken claim) rather than presenting a video the same way as a
plain photo. For images, C2PA manifest data (when present) is shown ahead
of the perceptual AI-detector line, mirroring the order Meta's own
AI-content labels use (read embedded provenance metadata first, fall back
to visual-artifact classification second).

Kept separate from app.routers.webhook_whatsapp so the formatting itself is
testable without a DB session or a fake Verification/Image ORM instance."""

from typing import Optional

from app.models.enums import ConfidenceLabel, Language, SourceMediaType, Verdict

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
    # Hindi/Tamil labels below are a first-pass machine translation, not
    # native-reviewed (flagged explicitly when added) - reasonable to ship,
    # but worth a native speaker's pass before leaning on it heavily.
    Language.hi: {
        (Verdict.true, True): "सही",
        (Verdict.true, False): "संभवतः सही",
        (Verdict.false, True): "गलत",
        (Verdict.false, False): "संभवतः गलत",
        (Verdict.misleading, True): "भ्रामक",
        (Verdict.misleading, False): "भ्रामक",
        (Verdict.unverifiable, True): "पुष्टि नहीं हो सकी",
        (Verdict.unverifiable, False): "पुष्टि नहीं हो सकी",
        (Verdict.satire, True): "व्यंग्य",
        (Verdict.satire, False): "व्यंग्य",
    },
    Language.ta: {
        (Verdict.true, True): "உண்மை",
        (Verdict.true, False): "பெரும்பாலும் உண்மை",
        (Verdict.false, True): "தவறு",
        (Verdict.false, False): "பெரும்பாலும் தவறு",
        (Verdict.misleading, True): "தவறாக வழிநடத்தும்",
        (Verdict.misleading, False): "தவறாக வழிநடத்தும்",
        (Verdict.unverifiable, True): "சரிபார்க்க முடியவில்லை",
        (Verdict.unverifiable, False): "சரிபார்க்க முடியவில்லை",
        (Verdict.satire, True): "நையாண்டி",
        (Verdict.satire, False): "நையாண்டி",
    },
}

_SECTION_LABELS = {
    Language.en: {
        "badge": "🛡️ *SatyaScan Verdict*",
        "claim": "🔎 *Claim:*",
        "confidence_suffix": "confidence",
        "found": "📋 *What we found:*",
        "image": "🖼️ *Image check:*",
        "video_frame": "🎬 *From the video frame:*",
        "said": "🗣️ *What was said:*",
        "heard": "🗣️ *What we heard:*",
        "freshness_caveat": (
            "📚 _This wasn't matched against a live web result - it's based on published "
            "fact-checks and general knowledge, which can be out of date. For anything "
            "about a current officeholder, election, or breaking event, please double-check "
            "with a fresh source._"
        ),
        "footer": "📎 _Forward another claim, image, or video anytime._",
    },
    Language.ml: {
        "badge": "🛡️ *സത്യസ്‌കാൻ വിധി*",
        "claim": "🔎 *അവകാശവാദം:*",
        "confidence_suffix": "വിശ്വാസ്യത",
        "found": "📋 *ഞങ്ങൾ കണ്ടെത്തിയത്:*",
        "image": "🖼️ *ചിത്ര പരിശോധന:*",
        "video_frame": "🎬 *വീഡിയോ ഫ്രെയിമിൽ നിന്ന്:*",
        "said": "🗣️ *പറഞ്ഞത്:*",
        "heard": "🗣️ *ഞങ്ങൾ കേട്ടത്:*",
        "freshness_caveat": (
            "📚 _ഇത് തത്സമയ വെബ് ഫലവുമായി പൊരുത്തപ്പെടുത്തിയതല്ല - പ്രസിദ്ധീകരിച്ച "
            "ഫാക്ട്-ചെക്കുകളെയും പൊതുവിവരത്തെയും അടിസ്ഥാനമാക്കിയാണ്, ഇത് കാലഹരണപ്പെട്ടതാകാം. "
            "നിലവിലെ ഒരു ഉദ്യോഗസ്ഥനെയോ തിരഞ്ഞെടുപ്പിനെയോ പുതിയ സംഭവത്തെയോ കുറിച്ചാണെങ്കിൽ, "
            "ദയവായി പുതിയ ഉറവിടം ഉപയോഗിച്ച് ഒന്നുകൂടി പരിശോധിക്കൂ._"
        ),
        "footer": "📎 _എപ്പോൾ വേണമെങ്കിലും മറ്റൊരു അവകാശവാദം, ചിത്രം, വീഡിയോ ഫോർവേഡ് ചെയ്യൂ._",
    },
    Language.hi: {
        "badge": "🛡️ *सत्यस्कैन फैसला*",
        "claim": "🔎 *दावा:*",
        "confidence_suffix": "विश्वास",
        "found": "📋 *हमने क्या पाया:*",
        "image": "🖼️ *छवि जांच:*",
        "video_frame": "🎬 *वीडियो फ्रेम से:*",
        "said": "🗣️ *क्या कहा गया:*",
        "heard": "🗣️ *हमने क्या सुना:*",
        "freshness_caveat": (
            "📚 _यह किसी लाइव वेब नतीजे से मेल नहीं खाया - यह प्रकाशित फैक्ट-चेक और सामान्य "
            "जानकारी पर आधारित है, जो पुरानी हो सकती है। किसी मौजूदा पदाधिकारी, चुनाव, या ताज़ा "
            "घटना के बारे में हो तो कृपया किसी नए स्रोत से दोबारा जांच लें।_"
        ),
        "footer": "📎 _कभी भी कोई और दावा, तस्वीर या वीडियो भेजें।_",
    },
    Language.ta: {
        "badge": "🛡️ *சத்யஸ்கேன் தீர்ப்பு*",
        "claim": "🔎 *கூற்று:*",
        "confidence_suffix": "நம்பகத்தன்மை",
        "found": "📋 *நாங்கள் கண்டறிந்தது:*",
        "image": "🖼️ *படச் சரிபார்ப்பு:*",
        "video_frame": "🎬 *வீடியோ பிரேமிலிருந்து:*",
        "said": "🗣️ *என்ன சொல்லப்பட்டது:*",
        "heard": "🗣️ *நாங்கள் கேட்டது:*",
        "freshness_caveat": (
            "📚 _இது நேரடி வலைத் தேடல் முடிவுடன் பொருத்தப்படவில்லை - இது வெளியிடப்பட்ட "
            "உண்மைச் சரிபார்ப்புகள் மற்றும் பொதுவான தகவலை அடிப்படையாகக் கொண்டது, இது "
            "காலாவதியானதாக இருக்கலாம். தற்போதைய பதவி வகிப்பவர், தேர்தல் அல்லது சமீபத்திய "
            "நிகழ்வு பற்றியதாக இருந்தால், புதிய மூலத்துடன் மீண்டும் சரிபார்க்கவும்._"
        ),
        "footer": "📎 _எப்போது வேண்டுமானாலும் மற்றொரு கூற்று, படம் அல்லது வீடியோவை அனுப்பவும்._",
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
    Language.hi: {
        "ai": "यह छवि AI-जनित या मनगढ़ंत लगती है।",
        "real": "यह छवि एक असली, बिना संपादित तस्वीर लगती है।",
        "unsure": "यह तय नहीं किया जा सका कि यह छवि AI-जनित है या नहीं।",
    },
    Language.ta: {
        "ai": "இந்தப் படம் AI மூலம் உருவாக்கப்பட்டதாகவோ கட்டமைக்கப்பட்டதாகவோ தோன்றுகிறது.",
        "real": "இந்தப் படம் ஒரு உண்மையான, திருத்தப்படாத புகைப்படமாகத் தோன்றுகிறது.",
        "unsure": "இந்தப் படம் AI உருவாக்கியதா என்று உறுதியாகக் கூற முடியவில்லை.",
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
    source_media_type: SourceMediaType = SourceMediaType.text,
    is_live_search_confirmed: bool = False,
) -> str:
    """Pure formatter: every value comes in as a primitive so this needs no
    DB session and no ORM instance - see app.routers.webhook_whatsapp for
    the thin wrapper that pulls those values off a Verification/Image row.

    The section order/labeling below is the only thing that varies by
    source_media_type - the underlying data (claim_text, image_lines) is
    the same either way, just presented so it's clear what came from
    where, instead of every message type getting an identical shape."""
    labels = _SECTION_LABELS[language]
    emoji = _VERDICT_EMOJI.get(verdict, "❓")
    confidence_pct = round((confidence_score or 0.0) * 100)
    label = verdict_label(verdict, confidence_label, language)
    verdict_line = f"{emoji} *{label}* — {confidence_pct}% {labels['confidence_suffix']}"

    lines = [labels["badge"], ""]

    if source_media_type == SourceMediaType.photo:
        # Image findings lead - there's often no caption to "verify", so
        # the image analysis itself is usually the headline, not a footnote.
        if image_lines:
            lines += [labels["image"]]
            lines += list(image_lines)
            lines += [""]
        if claim_text:
            lines += [f"{labels['claim']} {claim_text}", ""]
        lines += [verdict_line, ""]

    elif source_media_type == SourceMediaType.video:
        # Split visual authenticity (the extracted frame) from the spoken
        # claim (the audio transcript) - a video crashing both into one
        # generic "image check" line loses which part each finding is about.
        if image_lines:
            lines += [labels["video_frame"]]
            lines += list(image_lines)
            lines += [""]
        if claim_text:
            lines += [f"{labels['said']} {claim_text}", ""]
        lines += [verdict_line, ""]

    elif source_media_type == SourceMediaType.audio:
        # No visual component - lead with the transcript itself so a
        # non-technical sender can confirm SatyaScan understood them
        # correctly before trusting the verdict that follows.
        if claim_text:
            lines += [f"{labels['heard']} {claim_text}", ""]
        lines += [verdict_line, ""]

    else:
        # Plain text message - unchanged from the original shape.
        if claim_text:
            lines += [f"{labels['claim']} {claim_text}", ""]
        lines += [verdict_line, ""]
        if image_lines:
            lines += [labels["image"]]
            lines += list(image_lines)
            lines += [""]

    if explanation_text:
        lines += [labels["found"], explanation_text, ""]

    # A confident TRUE/FALSE/MISLEADING verdict that leans only on the
    # reasoning LLM's own (frozen-at-training-time) knowledge or older
    # fact-check articles - not a live web search - can quietly go stale on
    # exactly the claims where that matters most (who currently holds an
    # office, an ongoing election, breaking news). UNVERIFIABLE/SATIRE
    # already communicate their own uncertainty, so this is scoped to the
    # verdicts that read as a confident assertion of fact. Added after a
    # real case of the bot stating a "who is currently X" claim this way.
    if verdict in (Verdict.true, Verdict.false, Verdict.misleading) and not is_live_search_confirmed:
        lines += [labels["freshness_caveat"], ""]

    lines.append(labels["footer"])

    return "\n".join(lines).strip()
