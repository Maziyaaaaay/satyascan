from app.models.enums import ConfidenceLabel, Language, Verdict
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
