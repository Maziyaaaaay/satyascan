import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from app.logging_conf import get_logger

logger = get_logger(__name__)


async def extract_frame_and_audio(video_bytes: bytes) -> Tuple[Optional[bytes], Optional[bytes]]:
    """Best-effort extraction via ffmpeg: a representative JPEG frame (fed
    into the existing image-analysis pipeline as input_image_bytes) and the
    audio track as MP3 (fed into the existing speech-to-text pipeline, same
    as a voice note). Returns (None, None) if ffmpeg isn't on PATH or the
    video can't be decoded - the caller falls back to the message caption
    alone rather than dropping the whole message."""
    with tempfile.TemporaryDirectory() as tmp:
        video_path = Path(tmp) / "input.mp4"
        frame_path = Path(tmp) / "frame.jpg"
        audio_path = Path(tmp) / "audio.mp3"
        video_path.write_bytes(video_bytes)

        frame_bytes = await _run_ffmpeg(
            ["ffmpeg", "-y", "-ss", "00:00:00.5", "-i", str(video_path), "-vframes", "1", str(frame_path)],
            frame_path,
        )
        audio_bytes = await _run_ffmpeg(
            ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "libmp3lame", str(audio_path)],
            audio_path,
        )
        return frame_bytes, audio_bytes


async def _run_ffmpeg(command: list, output_path: Path) -> Optional[bytes]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
    except FileNotFoundError:
        logger.warning("ffmpeg_not_available")
        return None
    if not output_path.exists() or output_path.stat().st_size == 0:
        return None
    return output_path.read_bytes()
