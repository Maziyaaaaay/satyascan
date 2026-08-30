from app.models.enums import ConfidenceLabel, Language, SourceMediaType, Verdict
from app.services import report_formatting


def test_build_verdict_report_includes_claim_verdict_and_confidence():
    report = report_formatting.build_verdict_report(
        language=Language.en,
        verdict=Verdict.false,
        confidence_score=0.92,
        confidence_label=ConfidenceLabel.high,
        claim_text="Vijay is Tamil Nadu's new Chief Minister",
        explanation_text="No credible source reports this.",
        image_lines=None,
    )
    assert "SatyaScan Verdict" in report
    assert "Vijay is Tamil Nadu's new Chief Minister" in report
    assert "❌" in report and "FALSE" in report
    assert "92%" in report
    assert "No credible source reports this." in report


def test_build_verdict_report_omits_claim_line_when_no_claim_text():
    report = report_formatting.build_verdict_report(
        language=Language.en,
        verdict=Verdict.true,
        confidence_score=0.5,
        confidence_label=ConfidenceLabel.medium,
        claim_text=None,
        explanation_text="Confirmed.",
        image_lines=None,
    )
    assert "Claim:" not in report


def test_build_verdict_report_includes_image_lines_when_present():
    report = report_formatting.build_verdict_report(
        language=Language.en,
        verdict=Verdict.misleading,
        confidence_score=0.6,
        confidence_label=ConfidenceLabel.medium,
        claim_text="A photo claim",
        explanation_text="Partly accurate.",
        image_lines=["This image appears to be a real, unedited photo."],
    )
    assert "Image check" in report
    assert "This image appears to be a real, unedited photo." in report


def test_build_verdict_report_malayalam_uses_malayalam_labels():
    report = report_formatting.build_verdict_report(
        language=Language.ml,
        verdict=Verdict.true,
        confidence_score=0.8,
        confidence_label=ConfidenceLabel.high,
        claim_text="ഒരു അവകാശവാദം",
        explanation_text="സ്ഥിരീകരിച്ചു.",
        image_lines=None,
    )
    assert "സത്യസ്‌കാൻ" in report
    assert "ശരി" in report


def test_verdict_label_defaults_to_unverifiable_when_verdict_is_none():
    assert report_formatting.verdict_label(None, None, Language.en) == "UNVERIFIABLE"


def test_perceptual_image_line_thresholds():
    assert "AI-generated" in report_formatting.perceptual_image_line(0.9, Language.en)
    assert "real" in report_formatting.perceptual_image_line(0.1, Language.en)
    assert "Could not confidently" in report_formatting.perceptual_image_line(0.45, Language.en)
    assert "Could not confidently" in report_formatting.perceptual_image_line(None, Language.en)


def test_hindi_and_tamil_use_their_own_labels():
    hi = report_formatting.build_verdict_report(
        language=Language.hi,
        verdict=Verdict.true,
        confidence_score=0.8,
        confidence_label=ConfidenceLabel.high,
        claim_text="एक दावा",
        explanation_text="पुष्टि हो गई।",
        image_lines=None,
    )
    assert "सत्यस्कैन" in hi and "सही" in hi

    ta = report_formatting.build_verdict_report(
        language=Language.ta,
        verdict=Verdict.true,
        confidence_score=0.8,
        confidence_label=ConfidenceLabel.high,
        claim_text="ஒரு கூற்று",
        explanation_text="உறுதிப்படுத்தப்பட்டது.",
        image_lines=None,
    )
    assert "சத்யஸ்கேன்" in ta and "உண்மை" in ta


def test_photo_report_leads_with_image_findings_before_claim():
    report = report_formatting.build_verdict_report(
        language=Language.en,
        verdict=Verdict.unverifiable,
        confidence_score=0.7,
        confidence_label=ConfidenceLabel.medium,
        claim_text=None,
        explanation_text="No caption or claim to check.",
        image_lines=["This image appears to be a real, unedited photo."],
        source_media_type=SourceMediaType.photo,
    )
    assert report.index("Image check") < report.index("What we found")
    # A photo with no caption must not claim to have found a "Claim:" line.
    assert "Claim:" not in report


def test_video_report_splits_frame_and_spoken_claim():
    report = report_formatting.build_verdict_report(
        language=Language.en,
        verdict=Verdict.false,
        confidence_score=0.88,
        confidence_label=ConfidenceLabel.high,
        claim_text="This footage shows today's flood",
        explanation_text="This clip is from a different event.",
        image_lines=["Likely AI-generated (81%)."],
        source_media_type=SourceMediaType.video,
    )
    assert "From the video frame" in report
    assert "What was said" in report
    assert "This footage shows today's flood" in report
    assert "Likely AI-generated (81%)." in report
    # A video must never be presented as if it were a plain photo.
    assert "Image check" not in report


def test_audio_report_has_no_image_section_and_leads_with_transcript():
    report = report_formatting.build_verdict_report(
        language=Language.en,
        verdict=Verdict.false,
        confidence_score=0.9,
        confidence_label=ConfidenceLabel.high,
        claim_text="I heard that the minister has died",
        explanation_text="No credible source reports this.",
        image_lines=None,
        source_media_type=SourceMediaType.audio,
    )
    assert "What we heard" in report
    assert "I heard that the minister has died" in report
    assert "Image check" not in report
    assert "Claim:" not in report
