import pytest

from app.services import video_processing


@pytest.mark.asyncio
async def test_extraction_degrades_gracefully_without_ffmpeg():
    # This test environment has no ffmpeg on PATH - confirms the real
    # graceful-degradation branch (not a mocked stand-in for it): a video
    # message should fall back to just its caption rather than crash.
    frame_bytes, audio_bytes = await video_processing.extract_frame_and_audio(b"not-a-real-video")
    assert frame_bytes is None
    assert audio_bytes is None
