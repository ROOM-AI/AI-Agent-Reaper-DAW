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
    Return a concise, execution-ready version of user_input.
    Output is ONE line, no headings, no bullets, no explanations.
    """
    # Minimal rules passed to the model to avoid verbose sections
    minimal_rules = f"""
You rewrite the user's messy DAW request into ONE precise line the agent can execute.
Rules:
- Fix typos, keep original intent and order.
- Keep explicit track numbers exactly (e.g., "track 2"). If no track is given:
  "vocal"/"main vocal" → track 1; "edited/processed vocal" → track 2; "beat/drums/instrumental" → track 3.
- Use numeric units: Hz, kHz, dB, %, s, ms. Use ranges like "300–3000 Hz" as "300-3000Hz".
- Effects: specify only essential params (e.g., reverb decay and mix; EQ band type, freq, gain).
- Automation: specify start→end times and target levels.
- DO NOT add plugin brands/models. DO NOT add extra effects not requested.
- DO NOT add headings, bullets, quotes, labels, or any extra lines.
- Output ONLY the enhanced line, nothing else.

User input (verbatim):
{user_input}
"""
    prompt = minimal_rules.strip()

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text.strip()

    # Ensure single-line result
    return " ".join(response.splitlines()).strip()


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

