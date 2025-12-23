"""
ElevenLabs Full Song Generation + Stem Separation

EL1 Mode: Generate a complete song with ElevenLabs, then separate into stems.
Returns 6 stems: vocals, drums, bass, guitar, piano, other
"""

import os
import time
import tempfile
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

@dataclass
class FullSongBrief:
    """All info needed to generate a full song with ElevenLabs."""
    lyrics: str
    genre: str = "pop"
    mood: str = "uplifting"
    tempo: int = 120
    key: str = "C"
    vocal_style: str = "male"  # male, female, mixed
    language: str = "english"
    song_length_seconds: float = 120.0  # 2 minutes default
    title: Optional[str] = None
    additional_instructions: str = ""


@dataclass 
class StemResult:
    """Result of stem separation - contains all 6 stem audio bytes."""
    vocals: bytes = b''
    drums: bytes = b''
    bass: bytes = b''
    guitar: bytes = b''
    piano: bytes = b''
    other: bytes = b''
    filenames: Dict[str, str] = field(default_factory=dict)


class ElevenLabsBadPromptError(RuntimeError):
    """Raised when ElevenLabs rejects a prompt as bad_prompt (non-transient)."""

    def __init__(
        self,
        message: str,
        *,
        prompt_suggestion: Optional[str] = None,
        status_code: Optional[int] = None,
        body: Any = None,
    ):
        super().__init__(message)
        self.prompt_suggestion = prompt_suggestion
        self.status_code = status_code
        self.body = body


# Keep these conservative: we only aim to remove the most common ToS triggers (artist/title refs).
_LIKE_PATTERNS = [
    r"\b(sounds?\s+like|in\s+the\s+style\s+of|in\s+style\s+of|make\s+it\s+like|like|similar\s+to|inspired\s+by|channeling)\b\s+[^.\n;:]{1,160}",
]


def sanitize_for_elevenlabs(text: str) -> str:
    """
    Remove/neutralize likely ToS-triggering copycat phrasing and quoted titles.
    This is not a bypass; it's compliance automation.
    """
    if not text:
        return ""
    out = str(text)

    # Remove quoted spans (often song/album titles or artist references).
    out = re.sub(r"[\"“”']([^\"“”']{2,120})[\"“”']", "", out)

    # Remove "in the style of X" / "sounds like X" etc.
    for pat in _LIKE_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)

    # Collapse whitespace
    out = re.sub(r"\s{2,}", " ", out).strip(" ,.-;\n\t")
    return out.strip()


def _parse_bad_prompt_suggestion(err: Exception) -> Optional[str]:
    """
    ElevenLabs may return structured error bodies containing prompt_suggestion.
    We parse defensively to handle variations (detail vs detaill).
    """
    body = getattr(err, "body", None)
    if not isinstance(body, dict):
        return None
    detail = body.get("detail") or body.get("detaill")
    if not isinstance(detail, dict):
        return None
    if detail.get("status") != "bad_prompt":
        return None
    data = detail.get("data") or {}
    if isinstance(data, dict):
        return data.get("prompt_suggestion")
    return None


def _is_bad_prompt(err: Exception) -> bool:
    body = getattr(err, "body", None)
    if not isinstance(body, dict):
        return False
    detail = body.get("detail") or body.get("detaill")
    return isinstance(detail, dict) and detail.get("status") == "bad_prompt"


def _get_client():
    """Get ElevenLabs client with API key from environment. Lazy import."""
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as e:
        raise ImportError(f"elevenlabs package not installed or import failed: {e}. Run: pip install elevenlabs")
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")
    
    # Long timeout - song generation can take 2-5 minutes!
    return ElevenLabs(api_key=api_key, timeout=600.0)


def _format_exception(e: Exception) -> str:
    """Format ElevenLabs exception for better error messages."""
    msg = str(e)
    if hasattr(e, 'status_code'):
        msg = f"status_code: {e.status_code}, "
    if hasattr(e, 'body'):
        msg += f"body: {e.body}"
    elif hasattr(e, 'response'):
        try:
            msg += f"response: {e.response.text[:500]}"
        except:
            pass
    return msg


def build_fullsong_prompt(brief: FullSongBrief) -> str:
    """
    Build prompt for ElevenLabs full song generation.
    Keep it simple - just lyrics + description. Let ElevenLabs decide the rest.
    """
    parts = []
    
    # If there's a description/context, include it first
    if brief.additional_instructions:
        parts.append(sanitize_for_elevenlabs(brief.additional_instructions))
        parts.append("")
    
    # Only include genre/mood/tempo if explicitly set (non-default)
    if brief.genre and brief.genre != "pop":
        parts.append(f"Genre: {brief.genre}")
    if brief.mood and brief.mood != "uplifting":
        parts.append(f"Mood: {brief.mood}")
    
    # Lyrics are the main content
    parts.append("")
    parts.append("LYRICS:")
    parts.append(sanitize_for_elevenlabs(brief.lyrics.strip()))

    # Compliance guardrail (does not attempt to bypass; clarifies originality requirement)
    parts.append("")
    parts.append(
        "CONSTRAINTS: Do not imitate or reference any real artists, bands, songs, albums, or copyrighted lyrics. Keep everything original."
    )
    
    return "\n".join([p for p in parts if p or p == ""])


def generate_full_song(
    brief: FullSongBrief,
    retries: int = 3,
    timeout: int = 300
) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Generate a full song using ElevenLabs Music API.
    
    Returns:
        (audio_bytes, filename, metadata)
    """
    client = _get_client()
    prompt = build_fullsong_prompt(brief)
    
    # Convert seconds to milliseconds
    length_ms = int(brief.song_length_seconds * 1000)
    # Clamp to reasonable range (30s - 5min)
    length_ms = max(30_000, min(length_ms, 300_000))
    
    print(f"🎵 [EL1] Generating full song ({length_ms/1000:.0f}s)...")
    print(f"   Prompt preview: {prompt[:200]}...")
    print(f"   ⏳ Calling ElevenLabs API... this takes 2-5 MINUTES, please wait!")
    import sys
    sys.stdout.flush()  # Force log output immediately
    
    last_error = None
    tried_suggestion = False
    for attempt in range(retries):
        try:
            start_time = time.time()
            # Use music.compose_detailed for full song (same API as vocals)
            # Returns object with .audio (bytes), .filename, .json (metadata)
            track_details = client.music.compose_detailed(
                prompt=prompt,
                music_length_ms=length_ms
            )
            elapsed = time.time() - start_time
            print(f"   ✅ ElevenLabs returned after {elapsed:.1f}s")
            
            # Extract audio bytes from response
            audio_bytes = getattr(track_details, "audio", None)
            if audio_bytes is None:
                # Try alternative attribute names
                audio_bytes = getattr(track_details, "content", None)
            if audio_bytes is None and hasattr(track_details, 'read'):
                audio_bytes = track_details.read()
            if audio_bytes is None and isinstance(track_details, bytes):
                audio_bytes = track_details
            
            if not audio_bytes or len(audio_bytes) < 1024:
                raise ValueError("Empty or too small audio returned")
            
            filename = getattr(track_details, "filename", None) or f"fullsong_{int(time.time())}.mp3"
            meta_json = getattr(track_details, "json", {})
            if isinstance(meta_json, str):
                import json as json_module
                try:
                    meta_json = json_module.loads(meta_json)
                except:
                    meta_json = {}
            
            metadata = {
                "prompt": prompt[:500],
                "length_ms": length_ms,
                "genre": brief.genre,
                "mood": brief.mood,
                "elevenlabs_meta": meta_json
            }
            
            print(f"✅ [EL1] Full song generated: {len(audio_bytes)/1024:.1f} KB")
            return audio_bytes, filename, metadata
            
        except Exception as e:
            last_error = e

            # bad_prompt is not transient; handle explicitly
            if _is_bad_prompt(e):
                suggestion = _parse_bad_prompt_suggestion(e)
                if suggestion and not tried_suggestion:
                    tried_suggestion = True
                    print("⚠️ [EL1] ElevenLabs rejected prompt (bad_prompt). Retrying once with prompt_suggestion...")
                    # Replace the user-provided description with suggestion, keep lyrics (sanitized).
                    brief2 = FullSongBrief(
                        lyrics=brief.lyrics,
                        genre=brief.genre,
                        mood=brief.mood,
                        tempo=brief.tempo,
                        key=brief.key,
                        vocal_style=brief.vocal_style,
                        language=brief.language,
                        song_length_seconds=brief.song_length_seconds,
                        title=brief.title,
                        additional_instructions=suggestion,
                    )
                    prompt = build_fullsong_prompt(brief2)
                    continue

                # No suggestion (often implies non-retriable) OR suggestion already tried.
                raise ElevenLabsBadPromptError(
                    "ElevenLabs rejected prompt (bad_prompt). Please revise request.",
                    prompt_suggestion=suggestion,
                    status_code=getattr(e, "status_code", None),
                    body=getattr(e, "body", None),
                ) from e

            print(f"⚠️ [EL1] Attempt {attempt+1}/{retries} failed: {_format_exception(e)}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    
    raise RuntimeError(f"Failed to generate full song after {retries} attempts: {_format_exception(last_error)}")


def separate_stems(
    audio_bytes: bytes,
    retries: int = 3
) -> StemResult:
    """
    Separate audio into stems using ElevenLabs Stem Separation API.
    
    Endpoint: POST /v1/music/stem-separation
    Response: ZIP archive containing separated audio stems as MP3 files.
    
    Stem variations:
    - two_stems_v1: vocals + instrumental
    - six_stems_v1: vocals, drums, bass, guitar, piano, other
    
    Returns:
        StemResult with vocals, drums, bass, other as bytes
    """
    import requests
    import zipfile
    import io
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")
    
    print(f"🔀 [EL1] Separating stems ({len(audio_bytes)/1024:.1f} KB audio)...")
    
    last_error = None
    for attempt in range(retries):
        try:
            # Call ElevenLabs stem separation API
            # Uses six_stems_v1 for full separation (vocals, drums, bass, guitar, piano, other)
            url = "https://api.elevenlabs.io/v1/music/stem-separation"
            params = {
                "output_format": "mp3_44100_128",  # MP3 at 44.1kHz, 128kbps
            }
            headers = {
                "xi-api-key": api_key
            }
            files = {
                "file": ("song.mp3", audio_bytes, "audio/mpeg"),
            }
            data = {
                "stem_variation_id": "six_stems_v1"  # Get all 6 stems
            }
            
            print(f"   Calling ElevenLabs stem separation API (6 stems)...")
            response = requests.post(
                url, 
                params=params,
                headers=headers, 
                files=files, 
                data=data,
                timeout=600  # Can take a while for long songs
            )
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "No error details"
                raise RuntimeError(f"Stem separation failed: HTTP {response.status_code} - {error_text}")
            
            # Response is a ZIP file containing the stems
            zip_bytes = response.content
            print(f"   Received ZIP archive: {len(zip_bytes)/1024:.1f} KB")
            
            # Extract stems from ZIP
            stems = StemResult(filenames={})
            
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
                print(f"   ZIP contents: {zf.namelist()}")
                
                for filename in zf.namelist():
                    file_lower = filename.lower()
                    stem_bytes = zf.read(filename)
                    
                    # Map filenames to our 6 stem categories
                    if 'vocal' in file_lower:
                        stems.vocals = stem_bytes
                        stems.filenames['vocals'] = 'vocals.mp3'
                    elif 'drum' in file_lower:
                        stems.drums = stem_bytes
                        stems.filenames['drums'] = 'drums.mp3'
                    elif 'bass' in file_lower:
                        stems.bass = stem_bytes
                        stems.filenames['bass'] = 'bass.mp3'
                    elif 'guitar' in file_lower:
                        stems.guitar = stem_bytes
                        stems.filenames['guitar'] = 'guitar.mp3'
                    elif 'piano' in file_lower or 'keys' in file_lower:
                        stems.piano = stem_bytes
                        stems.filenames['piano'] = 'piano.mp3'
                    elif 'other' in file_lower or 'instrumental' in file_lower:
                        stems.other = stem_bytes
                        stems.filenames['other'] = 'other.mp3'
                    else:
                        # Unknown stem - put in other if empty
                        if not stems.other:
                            stems.other = stem_bytes
                            stems.filenames['other'] = 'other.mp3'
            
            print(f"✅ [EL1] Stems extracted:")
            for name in ['vocals', 'drums', 'bass', 'guitar', 'piano', 'other']:
                data = getattr(stems, name, b'')
                if data:
                    print(f"   - {name}: {len(data)/1024:.1f} KB")
            
            return stems
                    
        except Exception as e:
            last_error = e
            print(f"⚠️ [EL1] Stem separation attempt {attempt+1}/{retries} failed: {_format_exception(e)}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    
    raise RuntimeError(f"Failed to separate stems after {retries} attempts: {_format_exception(last_error)}")


def _extract_bytes(data) -> bytes:
    """Extract bytes from various data types."""
    if isinstance(data, bytes):
        return data
    if hasattr(data, 'read'):
        return data.read()
    if hasattr(data, 'content'):
        return data.content
    if hasattr(data, '__iter__'):
        return b''.join(data)
    return bytes(data) if data else b''


def generate_and_stem_zip(brief: FullSongBrief) -> Tuple[bytes, Dict[str, Any]]:
    """
    Full EL1 pipeline: generate song, then separate into stems.
    
    Returns:
        (zip_bytes, metadata)
        
    Returns the ZIP directly from ElevenLabs (with full song added).
    No re-packaging - just forward the bytes!
    """
    import zipfile
    import io
    
    # Step 1: Generate full song
    full_song_bytes, filename, metadata = generate_full_song(brief)
    
    # Step 2: Get stems ZIP from ElevenLabs
    try:
        stems_zip_bytes = separate_stems_raw(full_song_bytes)
        print(f"✅ [EL1] Got stems ZIP: {len(stems_zip_bytes)/1024:.1f} KB")
        
        # Add full song to the ZIP
        zip_buffer = io.BytesIO(stems_zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_STORED) as zf:
            zf.writestr("fullsong.mp3", full_song_bytes)
        
        final_zip = zip_buffer.getvalue()
        print(f"✅ [EL1] Final ZIP with fullsong: {len(final_zip)/1024:.1f} KB")
        return final_zip, metadata
        
    except Exception as e:
        print(f"⚠️ [EL1] Stem separation failed: {e}")
        print(f"   Returning just full song in ZIP")
        # Fallback: return just full song in a ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zf:
            zf.writestr("fullsong.mp3", full_song_bytes)
        return zip_buffer.getvalue(), metadata


def separate_stems_raw(audio_bytes: bytes, retries: int = 3) -> bytes:
    """
    Get raw ZIP bytes from ElevenLabs stem separation.
    No extraction - just return the ZIP directly.
    """
    import requests
    import sys
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")
    
    print(f"🔀 [EL1] Getting stems ZIP ({len(audio_bytes)/1024:.1f} KB audio)...")
    print(f"   ⏳ Calling stem separation API... this takes 1-2 MINUTES, please wait!")
    sys.stdout.flush()
    
    url = "https://api.elevenlabs.io/v1/music/stem-separation"
    params = {"output_format": "mp3_44100_128"}
    headers = {"xi-api-key": api_key}
    files = {"file": ("song.mp3", audio_bytes, "audio/mpeg")}
    data = {"stem_variation_id": "six_stems_v1"}
    
    last_error = None
    for attempt in range(retries):
        try:
            start_time = time.time()
            response = requests.post(url, params=params, headers=headers, 
                                    files=files, data=data, timeout=600)
            elapsed = time.time() - start_time
            
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
            
            zip_bytes = response.content
            print(f"✅ [EL1] Received stems ZIP: {len(zip_bytes)/1024:.1f} KB (took {elapsed:.1f}s)")
            return zip_bytes
            
        except Exception as e:
            last_error = e
            print(f"⚠️ [EL1] Attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    
    raise RuntimeError(f"Failed after {retries} attempts: {last_error}")


def generate_and_stem(
    brief: FullSongBrief
) -> Tuple[bytes, StemResult, Dict[str, Any]]:
    """
    Legacy function - kept for compatibility.
    Use generate_and_stem_zip for better performance.
    """
    # Step 1: Generate full song
    full_song_bytes, filename, metadata = generate_full_song(brief)
    
    # Step 2: Try to separate into stems
    try:
        stems = separate_stems(full_song_bytes)
        print(f"✅ [EL1] Stem separation successful")
    except Exception as e:
        print(f"⚠️ [EL1] Stem separation failed: {e}")
        print(f"   Returning full song as 'other' stem instead")
        stems = StemResult(
            other=full_song_bytes,
            filenames={'other': filename}
        )
    
    return full_song_bytes, stems, metadata


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Test with a simple brief
    brief = FullSongBrief(
        lyrics="Never give up on your dreams\nKeep pushing through the hard times\nYou're stronger than you know",
        genre="pop rock",
        mood="uplifting, energetic",
        tempo=128,
        key="G major",
        vocal_style="male",
        song_length_seconds=60
    )
    
    try:
        full_song, stems, meta = generate_and_stem(brief)
        print(f"\n🎉 Success!")
        print(f"Full song: {len(full_song)/1024:.1f} KB")
        print(f"Stems: vocals={len(stems.vocals)/1024:.1f}KB, drums={len(stems.drums)/1024:.1f}KB")
    except Exception as e:
        print(f"❌ Error: {e}")

