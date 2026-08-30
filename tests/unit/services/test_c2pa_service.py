import sys
import types

import pytest

from app.services import c2pa_service


def test_check_manifest_degrades_gracefully_when_c2pa_unavailable():
    # This test environment's c2pa-python either isn't installed, or (on
    # Python <3.10) fails to import with a SyntaxError - both are the real,
    # unmocked "unavailable" path, not a stand-in for it.
    result = c2pa_service.check_manifest(b"not-a-real-image")
    assert result.has_manifest is False
    assert result.is_ai_indicated is False


def test_classify_digital_source_type_flags_known_ai_terms():
    assert c2pa_service._classify_digital_source_type(
        "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
    )
    assert c2pa_service._classify_digital_source_type("compositeWithTrainedAlgorithmicMedia")
    assert not c2pa_service._classify_digital_source_type(
        "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"
    )
    assert not c2pa_service._classify_digital_source_type(None)


def test_find_digital_source_type_walks_nested_assertions():
    manifest = {
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {"action": "c2pa.created", "digitalSourceType": "trainedAlgorithmicMedia"},
                    ]
                },
            }
        ]
    }
    assert c2pa_service._find_digital_source_type(manifest) == "trainedAlgorithmicMedia"
    assert c2pa_service._find_digital_source_type({}) is None


def test_extract_generator_prefers_claim_generator_info():
    manifest = {
        "claim_generator": "Some_Tool/1.0",
        "claim_generator_info": [{"name": "Adobe Firefly", "version": "2.0"}],
    }
    assert c2pa_service._extract_generator(manifest) == "Adobe Firefly"


def test_extract_generator_falls_back_to_claim_generator_string():
    manifest = {"claim_generator": "Some_Tool/1.0"}
    assert c2pa_service._extract_generator(manifest) == "Some Tool"


def test_extract_generator_none_when_absent():
    assert c2pa_service._extract_generator({}) is None


@pytest.fixture
def fake_c2pa_module(monkeypatch):
    """Installs a fake `c2pa` module into sys.modules so check_manifest's
    `import c2pa` succeeds regardless of whether the real package is
    installed/importable on this interpreter, letting the "manifest found"
    branch be tested without the real Rust-backed library."""

    class FakeReader:
        def __init__(self, format_hint, stream):
            pass

        def get_active_manifest(self):
            return {
                "claim_generator_info": [{"name": "Test Generator"}],
                "assertions": [
                    {
                        "label": "c2pa.actions",
                        "data": {"actions": [{"digitalSourceType": "trainedAlgorithmicMedia"}]},
                    }
                ],
            }

    fake_module = types.ModuleType("c2pa")
    fake_module.Reader = FakeReader
    monkeypatch.setitem(sys.modules, "c2pa", fake_module)
    yield


def test_check_manifest_reports_ai_indicated_when_manifest_present(fake_c2pa_module):
    result = c2pa_service.check_manifest(b"fake-bytes")
    assert result.has_manifest is True
    assert result.generator == "Test Generator"
    assert result.is_ai_indicated is True
    assert "Test Generator" in result.summary


@pytest.fixture
def fake_c2pa_module_no_ai_marker(monkeypatch):
    class FakeReader:
        def __init__(self, format_hint, stream):
            pass

        def get_active_manifest(self):
            return {"claim_generator_info": [{"name": "Some Camera App"}], "assertions": []}

    fake_module = types.ModuleType("c2pa")
    fake_module.Reader = FakeReader
    monkeypatch.setitem(sys.modules, "c2pa", fake_module)
    yield


def test_check_manifest_no_ai_marker_when_source_type_absent(fake_c2pa_module_no_ai_marker):
    result = c2pa_service.check_manifest(b"fake-bytes")
    assert result.has_manifest is True
    assert result.is_ai_indicated is False
