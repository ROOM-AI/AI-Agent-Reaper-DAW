"""
End-to-end test for ElevenLabs vocals-only -> Reaper import (track 1).

How it works:
1) Sends a command to the cloud queue: ELEVEN_VOCALS 1 0.0 {json payload}
2) Your local cloud_bridge.py polls /api/reaper/poll, sees ELEVEN_VOCALS, calls /api/vocals/elevenlabs,
   saves MP3 to temp_audio, and rewrites it to INSERT_AUDIO for Lua.
3) Reaper Lua (reaper_cloud_agent.lua / reaper_agent.lua) imports the MP3 on track 1.

Prereqs:
- Cloud service running (CLOUD_URL)
- ELEVENLABS_API_KEY configured on the cloud service
- cloud_bridge.py running locally
- Reaper + Lua agent running locally
"""

import json
import os
import time
import requests


def main():
    cloud_url = os.getenv("CLOUD_URL", "").rstrip("/")
    if not cloud_url:
        # Default to the repo's cloud_bridge.py constant URL if user didn't set env.
        cloud_url = "https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app"

    session_id = os.getenv("SESSION_ID", "demo")

    # Short, non-copyright lyrics for testing
    payload = {
        "session_id": session_id,
        "lyrics": "City lights, quiet nights, I breathe and let it go",
        "tempo": 140,
        "key": "C",
        "mood": "reflective, atmospheric, male vocals",
        "music_length_ms": 15000,
    }

    cmd = f"ELEVEN_VOCALS 1 0.0 {json.dumps(payload, ensure_ascii=False)}"

    print("=" * 60)
    print("E2E ElevenLabs vocals -> Reaper (track 1)")
    print("=" * 60)
    print(f"Cloud: {cloud_url}")
    print(f"Session: {session_id}")
    print(f"Command: {cmd[:120]}{'...' if len(cmd) > 120 else ''}")

    # Optional: set tempo first (keeps grid consistent)
    set_tempo_cmd = {"session_id": session_id, "command": "SET_TEMPO 140"}
    r1 = requests.post(f"{cloud_url}/api/reaper/execute", json=set_tempo_cmd, timeout=10)
    r1.raise_for_status()

    # Queue the ELEVEN_VOCALS command
    r2 = requests.post(f"{cloud_url}/api/reaper/execute", json={"session_id": session_id, "command": cmd}, timeout=10)
    r2.raise_for_status()

    print("✅ Queued ELEVEN_VOCALS command to cloud.")
    print("Now watch your local cloud_bridge.py logs:")
    print("- It should fetch /api/vocals/elevenlabs, save an MP3, and rewrite to INSERT_AUDIO.")
    print("- Reaper should import the MP3 on track 1 at time 0.0.")

    # Give a small delay so the user sees it happening.
    time.sleep(1.0)


if __name__ == "__main__":
    main()


