from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
