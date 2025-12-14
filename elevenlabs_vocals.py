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
    # NEW: Full chord progression and song structure for better sync
    chord_progression: Optional[List[Dict[str, Any]]] = None  # [{"bar": 1, "beat": 1, "chord": "Am"}, ...]
    song_structure: Optional[List[Dict[str, Any]]] = None  # [{"section": "Verse", "start_bar": 1, "end_bar": 16, "chords": "Am-G-F-E"}, ...]
    song_length_seconds: Optional[float] = None
    # NEW: Instruments playing in the track (helps match vocal vibe)
    instruments: Optional[List[str]] = None  # e.g. ["Piano", "808 Bass", "Hi-hats", "Synth Pad"]


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
    Build a detailed prompt for vocals-only generation with full musical context.
    Includes chord progression and song structure so vocals match the instrumental.
    """
    style_bits: List[str] = []
    if brief.style:
        style_bits.append(sanitize_for_elevenlabs(brief.style.strip()))
    if brief.voice_tags:
        style_bits.extend([sanitize_for_elevenlabs(t.strip()) for t in brief.voice_tags if t and t.strip()])

    # Build comprehensive musical context
    meta_bits: List[str] = []
    if brief.bpm:
        meta_bits.append(f"Tempo: {brief.bpm} BPM")
    if brief.key:
        meta_bits.append(f"Key: {brief.key}")
    if brief.song_length_seconds:
        meta_bits.append(f"Duration: {brief.song_length_seconds:.1f} seconds")

    # Build instruments section
    instruments_section = ""
    if brief.instruments:
        instruments_section = "\nINSTRUMENTS IN THE TRACK:\n- " + "\n- ".join(brief.instruments)
        instruments_section += "\n(Match your vocal energy and tone to these instruments)"

    # Build song structure section
    structure_section = ""
    if brief.song_structure:
        structure_lines = ["", "SONG STRUCTURE (sing in sync with these sections):"]
        for section in brief.song_structure:
            section_name = section.get("section", "Section")
            start_bar = section.get("start_bar", "?")
            end_bar = section.get("end_bar", "?")
            chords = section.get("chords", "")
            timing = section.get("timing", "")
            line = f"- {section_name}: bars {start_bar}-{end_bar}"
            if chords:
                line += f" ({chords})"
            if timing:
                line += f" [{timing}]"
            structure_lines.append(line)
        structure_section = "\n".join(structure_lines)

    # Build chord progression section
    chord_section = ""
    if brief.chord_progression:
        chord_lines = ["", "CHORD PROGRESSION (sing notes that fit these chords):"]
        # Group chords by bar for cleaner output
        bar_chords: Dict[int, List[str]] = {}
        for chord_info in brief.chord_progression:
            bar = chord_info.get("bar", 0)
            chord = chord_info.get("chord", "")
            if chord:
                if bar not in bar_chords:
                    bar_chords[bar] = []
                bar_chords[bar].append(chord)
        
        # Format as readable progression
        if bar_chords:
            sorted_bars = sorted(bar_chords.keys())
            progression_str = ""
            for bar in sorted_bars:
                chords = bar_chords[bar]
                progression_str += f"Bar {bar}: {', '.join(chords)} | "
            chord_lines.append(progression_str.rstrip(" | "))
        chord_section = "\n".join(chord_lines)

    # Melody MIDI hint (keep it concise)
    melody_hint = ""
    if brief.melody_midi:
        midi_str = ", ".join(str(int(x)) for x in brief.melody_midi[:128])
        melody_hint = (
            "\n\nMelody contour hint (MIDI pitches): "
            f"{midi_str}"
            + (" ..." if len(brief.melody_midi) > 128 else "")
        )

    style_line = ""
    if style_bits:
        style_line = "Style: " + "; ".join(style_bits)

    meta_line = ""
    if meta_bits:
        meta_line = " | ".join(meta_bits)

    # The critical constraints that mimic your UI "Custom vocals only"
    constraints = (
        "Vocals-only a cappella. No instruments. No beat. No pads. No bass. "
        "Dry lead vocal (minimal reverb). No backing vocals unless requested."
    )
    
    # Build key guidance using ACTUAL chord data from the beat
    key_guidance = ""
    if brief.key:
        key_guidance = f"\nKEY: {brief.key} - sing in this key!"
    
    # If we have actual chord progression, list the SPECIFIC chords to sing over
    if brief.chord_progression and len(brief.chord_progression) > 0:
        # Extract unique chords in order
        seen_chords = []
        for c in brief.chord_progression:
            chord = c.get("chord", "")
            if chord and chord not in seen_chords:
                seen_chords.append(chord)
        if seen_chords:
            key_guidance += f"\nCHORDS IN THIS SONG: {' - '.join(seen_chords)}"
            key_guidance += "\nSing notes that FIT these specific chords. Land on chord tones!"

    # Build the full prompt with all context
    prompt_parts = [
        constraints,
        meta_line,
        style_line,
        key_guidance,
        instruments_section,
        structure_section,
        chord_section,
        "",
        "CRITICAL: Your vocal melody MUST be in the same key as the instrumental.",
        "Land on chord tones (root, 3rd, 5th) on strong beats (1 and 3).",
        "Use passing tones only on weak beats. Match the energy and vibe of the instruments.",
        "",
        "LYRICS TO SING:",
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


def _format_elevenlabs_exception(err: Exception) -> str:
    """
    ElevenLabs SDK exceptions often include structured fields (status_code, body, headers).
    Stringifying the exception sometimes only shows headers, so we surface the useful parts.
    """
    parts: List[str] = []
    status_code = getattr(err, "status_code", None)
    if status_code is not None:
        parts.append(f"status_code={status_code}")
    body = getattr(err, "body", None)
    if body is not None:
        try:
            parts.append(f"body={body}")
        except Exception:
            pass
    headers = getattr(err, "headers", None)
    if headers is not None:
        try:
            # keep short
            parts.append(f"headers={dict(headers)}")
        except Exception:
            parts.append(f"headers={headers}")
    message = str(err) or repr(err)
    if parts:
        return message + " | " + " | ".join(parts)
    return message


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

    # Never hardcode keys. Read from env var ELEVENLABS_API_KEY (Cloud Run).
    key = (api_key or os.getenv("ELEVENLABS_API_KEY") or "").strip()
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

    raise ElevenLabsVocalError(f"ElevenLabs vocals generation failed: {_format_elevenlabs_exception(last_err)}") from last_err


