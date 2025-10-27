"""
Prompt Enhancer - Makes vague prompts clear for the agent
Simple GPT wrapper that translates natural language to technical commands
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY_ENHANCER"))

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

**PRODUCTION KNOWLEDGE (use these techniques):**

**Vocal Processing:**
- Air/presence: Boost 8-12kHz shelf +2dB
- De-mudding: Cut 200-400Hz by 3-6dB  
- Brightness: High shelf at 6kHz +2dB
- Telephone effect: Band-pass 300-3000Hz
- Underwater: Low-pass at 800-1200Hz with steep slope
- Auto-tune: Add Antares or Waves Tune, set to 0-50% (0=off, 50=noticeable, 100=T-Pain)

**Reverb (space/depth):**
- Subtle: 1.2s decay, 15-25% mix
- Medium: 2.5s decay, 30-40% mix  
- Huge: 4-7s decay, 40-60% mix
- Specific plugins: Valhalla Room, Valhalla VintageVerb

**Compression (punch/control):**
- Gentle: 2:1 ratio, -18dB threshold (starts working on louder parts)
- Medium: 4:1 ratio, -15dB threshold (standard vocal/bus comp)
- Aggressive: 6:1 ratio, -12dB threshold (heavy limiting)
- DO NOT use -9dB or higher threshold (too aggressive, kills dynamics)

**Delay:**
- Slapback: 80-120ms, 20% mix
- Quarter note: 375ms (at 120BPM), 30% mix
- Half note: 750ms, 40% mix

**Bass/Low-end:**
- Sub boost: Shelf at 60Hz +3dB
- Punch: Boost 80-100Hz +2-4dB
- Muddy fix: Cut 200-300Hz by 4-6dB
- High-pass: 30-50Hz (remove rumble)

**SAFE RANGES (never exceed):**
- Volume: 0-90% (never 100%+, causes clipping)
- Gain: -12dB to +6dB max
- Mix: 0-80% (rarely go above)

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

