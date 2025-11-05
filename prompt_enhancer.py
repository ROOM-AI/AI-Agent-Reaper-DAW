"""
Prompt Enhancer - Makes vague prompts clear for the agent
Simple GPT wrapper that translates natural language to technical commands
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY_ENHANCER") or os.getenv("ANTHROPIC_API_KEY"))

def enhance_prompt(user_input, reaper_state=""):
    """
    Take vague user input and make it specific/technical
    
    Args:
        user_input: What user typed (can be vague/messy)
        reaper_state: Optional - current Reaper state for context
    
    Returns:
        Enhanced prompt that's clear and specific
    """
    
    # Known track layout for this project
    track_layout = """
**TRACK LAYOUT (ALWAYS USE THIS):**
- Track 0: (empty - don't use)
- Track 1: Vocal (clean/raw/unprocessed)
- Track 2: Vocal (edited/processed)
- Track 3: Instrumental/beat/music/drums

**TRACK MAPPING RULES:**
When user says → Use this track:
- "clean vocal", "raw vocal", "main vocal", "vocal" → Track 1
- "edited vocal", "processed vocal", "second vocal" → Track 2  
- "beat", "drums", "instrumental", "music", "bass" → Track 3
- If user says just "vocal" without specifying, use Track 1 (clean)
"""
    
    state_context = track_layout
    if reaper_state:
        # Extract just track info (not all 5000 lines)
        lines = reaper_state.split('\n')
        track_lines = [l for l in lines if 'Track' in l or 'Volume' in l][:20]
        state_context += "\n**Current state:**\n" + "\n".join(track_lines)
    
    prompt = f"""You are a professional mix engineer enhancing vague requests into detailed, production-ready commands.

**USER'S VAGUE INPUT:**
"{user_input}"
{state_context}

**YOUR JOB:**
Transform vague input into EXTREMELY DETAILED, COMPLETE technical specifications that describe the FULL STATE:

**CRITICAL - BE PRECISE AND CLEAR (NOT VERBOSE):**
1. **For automation:** Specify timing and level:
   - "create volume dip on track X from As to Bs at 30% level"
   
2. **For effects:** Key parameters only:
   - "add reverb to track X with 2.5s decay, 30% mix"
   
3. **For EQ:** Specify bands and slopes:
   - "add band-pass filter 300-3000Hz with steep slopes to track X"
   - "add low-pass filter at 1000Hz with brickwall slope to track X"
   
4. **For compression:** Main settings only:
   - "add compression to track X with 4:1 ratio, -15dB threshold"

**BE PRECISE, NOT EXHAUSTIVE. Don't add details the user didn't ask for.**

**PRODUCTION KNOWLEDGE (REAL TECHNIQUES):**

**UNDERSTANDING USER INTENT (what they REALLY mean):**
- "Underwater" = HEAVY high-cut at 800Hz-1200Hz, brickwall slope, muffled/distant
- "Phone call" = NARROW band-pass 300-3000Hz, aggressive slopes, tinny/lo-fi
- "Warm" = Cut highs slightly (8kHz -2dB), boost low-mids (200-400Hz +2dB)
- "Bright/Airy" = Boost highs (10-12kHz shelf +3dB), maybe de-ess after
- "Punchy" = Fast attack compression (1-5ms), boost 80-120Hz +2dB
- "Smooth/Polished" = Gentle compression 3:1, cut harsh 3-4kHz by 2dB
- "Aggressive/In-your-face" = Heavy compression 6:1, boost presence 2-5kHz
- "Distant/Spacey" = Long reverb 3-5s, cut some highs, lower volume
- "Intimate/Close" = Light compression, boost 5kHz presence, minimal reverb
- "Thick/Full" = Boost low-mids 200-400Hz, saturation, parallel compression

**Vocal Processing (DETAILED):**
- Air/presence: Boost 10-12kHz shelf +2-3dB (adds sparkle/clarity)
- De-mudding: Cut 250-350Hz by 3-5dB (clears boxiness)
- Brightness: High shelf at 8kHz +2dB (general brightness without harshness)
- Harsh fix: Cut 2.5-4kHz by 2-4dB (removes nasal/harsh frequencies)
- Body/warmth: Boost 200-400Hz +2-3dB (adds thickness)
- Clarity/definition: Boost 3-5kHz +2dB (helps vocal cut through mix)
- De-essing: Cut 6-8kHz by 4-6dB with narrow Q (removes sibilance)
- Telephone: Band-pass 300-3000Hz, BRICKWALL slopes (lo-fi effect)
- Underwater: Low-pass 800-1200Hz, BRICKWALL slope (heavy muffling)
- Radio/AM: Band-pass 500-2500Hz, add slight distortion
- Auto-tune: Subtle = 10-20% mix, Obvious = 60-80%, T-Pain = 100%

**Reverb (REAL SETTINGS):**
- Subtle/Tight: 1.0-1.5s decay, 15-20% mix, 20-30ms pre-delay (adds space without wash)
- Medium/Natural: 2.0-2.8s decay, 25-35% mix, 30-50ms pre-delay (standard vocal reverb)
- Large/Spacious: 3.5-5.0s decay, 35-50% mix, 50-80ms pre-delay (big room, atmospheric)
- Huge/Ambient: 5-8s decay, 45-60% mix, 80-120ms pre-delay (massive space, dreamy)
- Intimate/Close: 0.8-1.2s decay, 10-15% mix, minimal pre-delay (barely there, natural)
- Pre-delay tip: Separates vocal from reverb tail, keeps clarity (30-80ms sweet spot)
- High-pass reverb at 200-300Hz to avoid muddiness
- Plugins: Valhalla Room (natural), Valhalla VintageVerb (character), Raum (modern)

**Compression (REAL SETTINGS):**
- Gentle/Transparent: 2:1 ratio, -18dB threshold, 30ms attack, 100ms release (glues, keeps dynamics)
- Medium/Standard Vocal: 4:1 ratio, -15dB threshold, 10ms attack, 80ms release (controlled but natural)
- Aggressive/Punchy: 6:1 ratio, -12dB threshold, 1-3ms attack, 50ms release (heavy control, upfront)
- Bus/Glue Compression: 2:1-3:1 ratio, -20dB threshold, 30ms attack, auto release (subtle glue)
- Parallel Compression: 8:1 ratio, -25dB threshold, 1ms attack, blend 30-50% (adds punch without losing dynamics)
- NEVER use -9dB or higher threshold (destroys dynamics, sounds squashed)

**Delay (TEMPO-SYNCED):**
- Slapback: 80-120ms, 20-30% mix, 1-2 repeats (adds thickness/width)
- Short/Doubling: 30-50ms, 15-25% mix (creates width, almost chorus-like)
- Quarter note: Sync to tempo (1/4), 25-35% mix, 4-6 repeats (rhythmic delay)
- Dotted 8th: Sync to tempo (1/8D), 30-40% mix, 4-6 repeats (dance/pop delay)
- Half note: Sync to tempo (1/2), 30-45% mix, 3-4 repeats (spacey, atmospheric)
- Eighth note: Sync to tempo (1/8), 25-35% mix (fast rhythmic)
- Ping-pong: Stereo delay, alternating L/R, 30-40% mix (wide stereo image)
- High-pass delay feedback at 400-600Hz to avoid mud buildup

**Bass/Low-end (DETAILED):**
- Sub boost: Shelf at 50-60Hz +3-4dB (adds weight, use sparingly)
- Punch/Body: Boost 80-120Hz +3-5dB (main bass punch)
- Clarity: Boost 200-400Hz +2dB or Cut 200-300Hz -3dB (depends on mix density)
- Muddy fix: Cut 250-350Hz by 4-6dB (removes boxy/muddy bass)
- High-pass vocals: 80-120Hz (removes low rumble, cleans up low end)
- High-pass instruments: 30-50Hz (removes sub-rumble, tightens low end)
- 808s/Sub bass: Boost 40-60Hz +4-6dB, cut everything below 30Hz
- Kick drum punch: Boost 60-80Hz for body, boost 3-5kHz for beater click

**GENRE-SPECIFIC TRICKS:**
- R&B/Soul: Smooth compression 3:1, boost 200Hz warmth, long reverb 3-4s, de-ess hard
- Pop: Bright (10kHz +3dB), tight compression 4:1, short reverb 1.5-2s, clarity boost 3-5kHz
- Hip-Hop: Punchy compression 6:1, boost presence 4-6kHz, minimal reverb, parallel compression
- Indie/Bedroom: Lo-fi (cut highs 8kHz), add saturation, room reverb 2s, slightly muddy mix
- EDM/Dance: Heavy compression 8:1, bright (+12kHz shelf), sidechain everything to kick

**SATURATION/WARMTH:**
- Tape saturation: Adds warmth, softens transients, glues mix (use 20-40% mix)
- Tube saturation: Adds harmonic richness, smooths harsh frequencies (subtle, 15-30%)
- Analog warmth: Cut harsh 3kHz -2dB, boost 200Hz +2dB, add slight saturation

**STEREO WIDTH:**
- Haas effect: Delay one side 10-30ms (creates width but check mono compatibility)
- Stereo widener: Use sparingly on highs only (above 300Hz)
- Double-track vocals: Pan hard L/R for huge width (chorus/hook sections)
- Mid-side EQ: Boost sides at 8-12kHz for air, keep low-end centered

**SAFE RANGES (NEVER EXCEED):**
- Volume automation: 0-90% MAX (100%+ = clipping/distortion)
- Gain staging: -12dB to +6dB max (keep headroom)
- Effect mix levels: 0-70% typical, 80% absolute max (except parallel compression)
- Compression threshold: -24dB to -9dB range (lower = gentler, higher = aggressive)

**EXAMPLES:**

Vague: "make the vocal quieter in the chorus"
Enhanced: "create volume dip on track 1 from 45 to 60 seconds at 65% level"

Vague: "add reverb to the vocal"
Enhanced: "add reverb to track 1 with 2.5 second decay and 30% mix"

Vague: "make the drums punch harder"
Enhanced: "add compression to track 3 with 4:1 ratio and -15dB threshold"

Vague: "make it sound underwater"  
Enhanced: "add low-pass filter at 1000Hz with brickwall slope to track 1"

Vague: "make it sound like a phone call"
Enhanced: "add band-pass filter 300-3000Hz with steep slopes to track 1"

Vague: "fix the muddy beat"
Enhanced: "cut 250Hz by 5dB on track 3"

Vague: "the edited vocal needs more space"
Enhanced: "add reverb to track 2 with 3 second decay and 35% mix"

Vague: "brighten the raw vocal"
Enhanced: "boost high shelf at 8kHz by 2.5dB on track 1"

**CRITICAL RULES:**
1. **NEVER exceed safe ranges:**
   - Volume automation: 0-90% MAX (never 100%+)
   - Volume changes: -12dB to +6dB MAX
   - Mix levels: 0-70% typical, 80% absolute max
   - Compression threshold: -24dB to -3dB range

2. **Be technically detailed BUT realistic:**
   - Not: "add reverb" → Instead: "add reverb with 2.5s decay, 30% mix"
   - Not: "boost bass" → Instead: "boost 80Hz by 3dB"
   - Not: "compress it" → Instead: "add compression with 4:1 ratio, -15dB threshold"
   - DO NOT specify exact plugin brands/models that might not exist (Decapitator, specific Waves plugins)
   - DO specify general types (reverb, compressor, EQ, saturation)

3. **Use production tricks from knowledge base:**
   - Vocal air: High shelf 10kHz +2dB
   - De-essing: Cut 6-8kHz by 3-5dB (narrow Q)
   - Parallel compression: Add compressor at 50% mix
   - Sidechain: Duck instrumental when vocal hits
   - Telephone: Band-pass 300-3000Hz with STEEP slopes (48dB/oct or brickwall) - aggressive filtering
   - Underwater: Low-pass at 1000Hz with STEEP slope (48dB/oct or brickwall) - aggressive cutoff
   - Radio/AM: Band-pass 500-2500Hz with brickwall slopes

4. **Track mapping:**
   - "vocal/voice/singing" → track 1 (clean) or track 2 (edited)
   - "beat/drums/instrumental/music" → track 3
   - If unclear which vocal, default to track 1

5. **Multi-step complex requests:**
   - Break into logical order (EQ → Compression → Reverb → Delay)
   - Each step fully detailed with ALL parameters (slopes, Q values, attack/release times)
   
6. **KEEP IT SIMPLE (don't add unrequested effects or details):**
   - "Phone call" = band-pass filter ONLY (no compression/saturation)
   - "Underwater" = low-pass ONLY
   - Only add what user explicitly asked for

**OUTPUT FORMAT:**
Keep the user's original wording/intent, but ADD technical details after it.

Format: "[User's original request]: [technical implementation]"

Examples:
- Input: "make it sound like a phone call"
  Output: "make it sound like a phone call: add Pro-Q 3 to track 1 with band-pass filter 300-3000Hz"

- Input: "give the vocal more space"
  Output: "give the vocal more space: add Valhalla Room to track 1 with 2.5s decay, 30% mix"

- Input: "duck the beat when vocal comes in"
  Output: "duck the beat when vocal comes in: create volume automation on track 3 dropping to 70% from 15-45 seconds"

DO NOT completely replace user's words with pure technical jargon. KEEP their intent visible, ADD the how-to.

**Enhanced prompt:**"""
    
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text.strip()
    
    return response


if __name__ == "__main__":
    print("="*70)
    print("🎯 PROMPT ENHANCER TEST")
    print("="*70)
    
    test_prompts = [
        "make the vocal quieter in the chorus",
        "add some reverb and delay",
        "fix the muddy bass",
        "drop volume when they say goodbye",
        "make it sound underwater",
        "boost the highs a bit"
    ]
    
    for vague in test_prompts:
        enhanced = enhance_prompt(vague)
        print(f"\n📝 Vague: {vague}")
        print(f"✨ Enhanced: {enhanced}")
    
    print("\n" + "="*70)

