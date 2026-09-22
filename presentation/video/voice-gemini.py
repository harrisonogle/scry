"""Speak one line with the Gemini text-to-speech model and write it as a WAV.

    uv run --extra outline python presentation/video/voice-gemini.py out.wav "The text to speak"

The key is GEMINI_API_KEY from the environment or the repository's .env (scry.env.load_dotenv); it is never printed.
The model returns 24 kHz 16-bit mono PCM; it is written with the wave module. Set GEMINI_TTS_MODEL or GEMINI_TTS_VOICE
to change the model id or the voice (default gemini-2.5-flash-preview-tts, Kore).
"""

from __future__ import annotations

import os
import subprocess
import sys
import wave
from pathlib import Path


def _load_key() -> str:
    from scry.env import load_dotenv

    load_dotenv()  # ./.env of the current directory, if any
    if "GEMINI_API_KEY" not in os.environ:
        # a worktree has no .env of its own: try the main checkout's
        try:
            common = subprocess.run(
                ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            load_dotenv(Path(common).parent / ".env")
        except (subprocess.CalledProcessError, OSError):
            pass
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("voice-gemini: GEMINI_API_KEY is not set (environment or .env)")
    return key


def speak(text: str, out: Path, model: str, voice: str) -> int:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_load_key())
    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)),
            ),
        ),
    )
    part = response.candidates[0].content.parts[0]
    data = part.inline_data.data
    mime = part.inline_data.mime_type or ""
    rate = 24000
    for field in mime.split(";"):
        if field.strip().startswith("rate="):
            rate = int(field.strip()[5:])
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)
    return len(data) // 2


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(argv[1])
    text = argv[2]
    model = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    voice = os.environ.get("GEMINI_TTS_VOICE", "Kore")
    samples = speak(text, out, model, voice)
    print(f"{out}: {samples / 24000:.2f} s, {model}, voice {voice}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
