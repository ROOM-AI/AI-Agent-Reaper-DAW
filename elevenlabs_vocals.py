"""
ElevenLabs vocals-only (a cappella) generation helper.

Uses ElevenLabs Eleven Music API via the official Python SDK.
Docs: https://elevenlabs.io/docs/developers/guides/cookbooks/music/quickstart

This module is designed to run in the CLOUD service.
Local bridge should only ever download / save the returned bytes.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List


class ElevenLabsVocalError(RuntimeError):
    """Raised when ElevenLabs generation fails in a way we want to surface."""


@dataclass
class VocalBrief:
    lyrics: str
    bpm: Optional[int] = None
    key: Optional[str] = None
    style: Optional[str] = None
    melody_midi: Optional[List[int]] = None
    voice_tags: Optional[List[str]] = None  # e.g. ["male vocals", "dark r&b"]


# Claude can see artist-name vibes, but ElevenLabs should not receive artist names.
# Keep this list short and add more only if you see bad_prompt failures.
_BANNED_NAME_PATTERNS = [
    r"\bthe\s+weeknd\b",
    r"\bweeknd\b",
]

_LIKE_PATTERNS = [
    r"\b(sounds?\s+like|in\s+the\s+style\s+of|like)\s+([A-Z][\w'’\-]+(?:\s+[A-Z][\w'’\-]+){0,5})",
]


def sanitize_for_elevenlabs(text: str) -> str:
    """
    Remove/neutralize artist-name references before sending prompts to ElevenLabs.
    Conservative: strip names, keep descriptive adjectives.
    """
    if not text:
        return ""
    out = str(text)

    # Remove quoted references: "The Weeknd", 'Taylor Swift', etc.
    out = re.sub(r"['\"]{1}[^'\"]{1,80}['\"]{1}", "", out)

    # Remove "like X" / "style of X" patterns
    for pat in _LIKE_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)

    # Remove explicit banned tokens
    for pat in _BANNED_NAME_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)

    # Collapse whitespace
    out = re.sub(r"\s{2,}", " ", out).strip(" ,.-;\n\t")
    return out.strip()


def build_vocals_prompt(brief: VocalBrief) -> str:
    """
    Build a short, strict prompt for vocals-only generation.
    We enforce vocals-only via prompt constraints because the public quickstart
    does not show a dedicated API flag for that UI mode.
    """
    style_bits: List[str] = []
    if brief.style:
        style_bits.append(sanitize_for_elevenlabs(brief.style.strip()))
    if brief.voice_tags:
        style_bits.extend([sanitize_for_elevenlabs(t.strip()) for t in brief.voice_tags if t and t.strip()])

    meta_bits: List[str] = []
    if brief.bpm:
        meta_bits.append(f"Tempo: {brief.bpm} BPM")
    if brief.key:
        meta_bits.append(f"Key: {brief.key}")

    melody_hint = ""
    if brief.melody_midi:
        # Keep it short; this is a hint, not a full spec.
        midi_str = ", ".join(str(int(x)) for x in brief.melody_midi[:256])
        melody_hint = (
            "\nMelody hint (MIDI note numbers, optional): "
            f"{midi_str}"
            + (" ..." if len(brief.melody_midi) > 256 else "")
        )

    style_line = ""
    if style_bits:
        style_line = "Style tags: " + "; ".join(style_bits)

    meta_line = ""
    if meta_bits:
        meta_line = " | ".join(meta_bits)

    # The critical constraints that mimic your UI “Custom vocals only”
    constraints = (
        "Vocals-only a cappella. No instruments. No beat. No pads. No bass. "
        "Dry lead vocal (minimal reverb). No backing vocals unless requested."
    )

    prompt_parts = [
        constraints,
        meta_line,
        style_line,
        "Sing these lyrics exactly (do not add new lines unless needed for phrasing):",
        sanitize_for_elevenlabs(brief.lyrics.strip()),
    ]
    prompt = "\n".join([p for p in prompt_parts if p])
    if melody_hint:
        prompt += melody_hint
    return prompt


def _parse_bad_prompt_suggestion(err: Exception) -> Optional[str]:
    """
    ElevenLabs may return a structured error containing a prompt suggestion.
    We try to extract it without tightly coupling to SDK internals.
    """
    body = getattr(err, "body", None)
    if not isinstance(body, dict):
        return None
    detail = body.get("detail")
    if not isinstance(detail, dict):
        return None
    if detail.get("status") != "bad_prompt":
        return None
    data = detail.get("data") or {}
    if isinstance(data, dict):
        return data.get("prompt_suggestion")
    return None


def compose_vocals_mp3(
    prompt: str,
    length_ms: int,
    *,
    api_key: Optional[str] = None,
    retries: int = 3,
    retry_backoff_s: float = 1.5,
) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Generate vocals-only audio and return (audio_bytes, filename, meta_json).

    Uses ElevenLabs SDK: music.compose_detailed(...)
    See: https://elevenlabs.io/docs/developers/guides/cookbooks/music/quickstart
    """
    # Lazy import so local environments without the SDK don't break import-time.
    try:
        from elevenlabs.client import ElevenLabs
    except Exception as e:
        raise ElevenLabsVocalError(
            "Missing ElevenLabs SDK. Add `elevenlabs` to requirements and install it."
        ) from e

    key = api_key or os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise ElevenLabsVocalError("ELEVENLABS_API_KEY is not set in environment.")

    last_err: Optional[Exception] = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            elevenlabs = ElevenLabs(api_key=key)

            # compose_detailed returns an object with:
            # - .audio (bytes)
            # - .filename (string)
            # - .json (dict / json string) containing composition plan + metadata
            track_details = elevenlabs.music.compose_detailed(
                prompt=prompt,
                music_length_ms=int(length_ms),
            )

            audio = getattr(track_details, "audio", None)
            filename = getattr(track_details, "filename", None) or "vocals.mp3"
            meta_json = getattr(track_details, "json", None)
            if meta_json is None:
                meta_json = {}
            if isinstance(meta_json, str):
                # Some SDK versions may provide a JSON string
                try:
                    import json as _json

                    meta_json = _json.loads(meta_json)
                except Exception:
                    meta_json = {"raw": meta_json}

            if not isinstance(audio, (bytes, bytearray)) or len(audio) < 1024:
                raise ElevenLabsVocalError(
                    "ElevenLabs returned empty/invalid audio bytes."
                )

            return bytes(audio), str(filename), meta_json if isinstance(meta_json, dict) else {"meta": meta_json}
        except Exception as e:
            last_err = e
            suggestion = _parse_bad_prompt_suggestion(e)
            if suggestion:
                raise ElevenLabsVocalError(
                    f"ElevenLabs rejected prompt (bad_prompt). Suggested prompt: {suggestion}"
                ) from e
            if attempt >= retries:
                break
            time.sleep(retry_backoff_s * attempt)

    raise ElevenLabsVocalError(f"ElevenLabs vocals generation failed: {last_err}") from last_err


