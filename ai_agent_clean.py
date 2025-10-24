"""
AI Agent for Reaper DAW - CLEAN VERSION
- Transparent: You see exactly what it's doing
- Self-aware: Learns which commands work/fail
- Minimal: No retry loops, no memory bloat
"""

import json
import time
from pathlib import Path
from anthropic import Anthropic

# Files
COMMAND_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_commands.txt"
STATE_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_state.txt"
FEEDBACK_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_feedback.txt"
ACTIONS_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_actions.txt"
KNOWLEDGE_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_knowledge.json"

client = Anthropic(api_key="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")

# ============================================================================
# KNOWLEDGE BASE - What the agent learns
# ============================================================================

class Knowledge:
    """Self-aware knowledge base - learns what works"""
    
    def __init__(self):
        self.data = {
            "working_commands": {},     # command_name → success_count
            "broken_commands": {},      # command_name → failure_count
            "command_effects": {},      # command_name → what it actually does
            "task_solutions": {}        # task_type → list of working command sequences
        }
        self.load()
    
    def load(self):
        """Load learned knowledge from file"""
        try:
            if Path(KNOWLEDGE_FILE).exists():
                with open(KNOWLEDGE_FILE, 'r') as f:
                    self.data = json.load(f)
                print(f"📚 Loaded knowledge: {len(self.data['working_commands'])} working, {len(self.data['broken_commands'])} broken")
        except:
            pass
    
    def save(self):
        """Save learned knowledge to file"""
        with open(KNOWLEDGE_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def record_success(self, command, effect):
        """Record that a command worked and what it did"""
        if command not in self.data["working_commands"]:
            self.data["working_commands"][command] = 0
        self.data["working_commands"][command] += 1
        self.data["command_effects"][command] = effect
        
        # Remove from broken if it was there
        if command in self.data["broken_commands"]:
            del self.data["broken_commands"][command]
        
        self.save()
        print(f"✅ Learned: {command} works ({self.data['working_commands'][command]} times)")
    
    def record_failure(self, command, reason):
        """Record that a command failed"""
        if command not in self.data["broken_commands"]:
            self.data["broken_commands"][command] = 0
        self.data["broken_commands"][command] += 1
        self.save()
        print(f"❌ Learned: {command} doesn't work ({self.data['broken_commands'][command]} times) - {reason}")
    
    def is_known_broken(self, command):
        """Check if command is known to be broken"""
        return command in self.data["broken_commands"] and self.data["broken_commands"][command] >= 2
    
    def get_working_commands(self):
        """Get list of commands known to work"""
        return list(self.data["working_commands"].keys())
    
    def get_knowledge_summary(self):
        """Get summary for Claude"""
        summary = ""
        if self.data["working_commands"]:
            summary += "\n**KNOWN WORKING COMMANDS:**\n"
            for cmd, count in sorted(self.data["working_commands"].items(), key=lambda x: -x[1])[:10]:
                effect = self.data["command_effects"].get(cmd, "unknown effect")
                summary += f"- {cmd}: {effect} (used {count} times)\n"
        
        if self.data["broken_commands"]:
            summary += "\n**KNOWN BROKEN COMMANDS (DO NOT USE):**\n"
            for cmd, count in sorted(self.data["broken_commands"].items(), key=lambda x: -x[1])[:10]:
                summary += f"- {cmd}: failed {count} times\n"
        
        return summary

# ============================================================================
# REAPER INTERFACE
# ============================================================================

def send_to_reaper(commands):
    """Send commands to Reaper"""
    try:
        with open(COMMAND_FILE, 'w') as f:
            for cmd in commands:
                f.write(cmd + '\n')
        time.sleep(0.3)
        return True
    except:
        return False

def get_state():
    """Get current Reaper state"""
    send_to_reaper(["GET_STATE"])
    time.sleep(0.3)
    try:
        with open(STATE_FILE, 'r') as f:
            return f.read()
    except:
        return ""

def get_feedback():
    """Get feedback from Reaper"""
    try:
        with open(FEEDBACK_FILE, 'r') as f:
            return f.read().strip()
    except:
        return ""

def load_actions():
    """Load action database"""
    actions = {}
    try:
        with open(ACTIONS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("REAPER") or line.startswith("Format"):
                    continue
                parts = line.split(':', 1)
                if len(parts) == 2:
                    actions[parts[0].strip()] = parts[1].strip()
    except:
        pass
    return actions

# ============================================================================
# STATE COMPARISON
# ============================================================================

def diff_states(before, after):
    """Compare two states and return what changed"""
    changes = []
    
    # Simple line-by-line diff
    before_lines = set(before.split('\n'))
    after_lines = set(after.split('\n'))
    
    added = after_lines - before_lines
    removed = before_lines - after_lines
    
    if not added and not removed:
        return None  # No change
    
    # Summarize changes
    for line in added:
        if 'Automation' in line:
            changes.append(f"Added: {line.strip()}")
        elif 'FX' in line:
            changes.append(f"Added: {line.strip()}")
        elif 'Volume:' in line or 'Pan:' in line:
            changes.append(f"Changed: {line.strip()}")
    
    for line in removed:
        if 'Automation' in line:
            changes.append(f"Removed: {line.strip()}")
        elif 'FX' in line:
            changes.append(f"Removed: {line.strip()}")
    
    return changes if changes else ["State changed (details unclear)"]

# ============================================================================
# AGENT LOGIC
# ============================================================================

def plan(user_input, state, knowledge):
    """Ask Claude what to do (one attempt only)"""
    
    actions = load_actions()
    
    # Filter out known broken commands
    for broken in knowledge.data["broken_commands"].keys():
        if broken in actions:
            del actions[broken]
    
    actions_text = "\n".join([f"{aid}: {desc}" for aid, desc in list(actions.items())[:100]])
    knowledge_summary = knowledge.get_knowledge_summary()
    
    prompt = f"""You control Reaper DAW. Plan what to do.

{knowledge_summary}

**USER WANTS:** {user_input}

**CURRENT STATE:**
{state[:2000]}

**AVAILABLE ACTIONS:**
{actions_text}

**CUSTOM COMMANDS:**
- VOL_DIP <track> <start_sec> <end_sec> <value_0-1> - Create volume automation dip
- SELECT_TRACK <track> - Select a track
- CLEAR_AUTOMATION <track> Volume - Delete ALL volume automation points
- SET_TRACK_VOL <track> <dB> - Set track volume
- GOTO <seconds> - Jump to position

**RULES:**
1. Return ONE simple approach - don't overcomplicate
2. If you know a command works (from knowledge above), USE IT
3. If you don't know what works, try ONE thing and we'll learn
4. DO NOT use commands marked as broken

**OUTPUT JSON:**
{{{{
  "reasoning": "Brief explanation",
  "commands": ["SELECT_TRACK 1", "CLEAR_AUTOMATION 1 Volume"]
}}}}"""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text.strip()
    
    # Parse JSON
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()
    
    plan = json.loads(response)
    return plan

def execute(user_input, knowledge):
    """Execute user command - ONE attempt, learn from result"""
    
    print(f"\n{'='*70}")
    print(f"🎤 User: {user_input}")
    print(f"{'='*70}")
    
    # Get current state
    print("\n📊 Getting current state...")
    state_before = get_state()
    
    # Plan
    print("🧠 Planning...")
    try:
        plan_result = plan(user_input, state_before, knowledge)
        reasoning = plan_result.get("reasoning", "")
        commands = plan_result.get("commands", [])
    except Exception as e:
        print(f"❌ Planning failed: {e}")
        return
    
    print(f"💭 Reasoning: {reasoning}")
    print(f"📝 Commands: {commands}")
    
    if not commands:
        print("⚠️ No commands to execute")
        return
    
    # Execute
    print("\n⚡ Executing...")
    send_to_reaper(commands)
    time.sleep(0.5)
    
    # Get feedback
    feedback = get_feedback()
    print(f"📢 Reaper: {feedback if feedback else '(no feedback)'}")
    
    # Get new state
    print("\n🔍 Checking what changed...")
    state_after = get_state()
    changes = diff_states(state_before, state_after)
    
    # Analyze result
    if changes:
        print("\n✅ STATE CHANGED:")
        for change in changes:
            print(f"   {change}")
        
        # Learn: these commands work
        for cmd in commands:
            cmd_name = cmd.split()[0]
            knowledge.record_success(cmd_name, "; ".join(changes))
        
        print("\n🎉 SUCCESS!")
    else:
        print("\n❌ STATE DID NOT CHANGE")
        print("   The commands executed but nothing happened in the project.")
        
        # Learn: these commands don't work for this task
        for cmd in commands:
            cmd_name = cmd.split()[0]
            knowledge.record_failure(cmd_name, "No state change")
        
        print("\n💡 What this means:")
        print("   - The command isn't broken (Reaper executed it)")
        print("   - But it doesn't do what we need for this task")
        print("   - I'll remember this and try something else next time")
    
    print(f"{'='*70}\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🎵 AI AGENT FOR REAPER (CLEAN VERSION) 🎵")
    print("="*70)
    print("\nFeatures:")
    print("  ✅ Transparent - see exactly what it does")
    print("  ✅ Self-aware - learns what works/fails")
    print("  ✅ No retry loops - one attempt, honest result")
    print("  ✅ No bloat - minimal code")
    print("="*70)
    
    knowledge = Knowledge()
    
    print("\n✅ Ready!\n")
    
    while True:
        user_input = input("💬 Command: ")
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break
        
        if user_input.lower() == "show knowledge":
            print("\n" + knowledge.get_knowledge_summary())
            continue
        
        if user_input.strip():
            execute(user_input, knowledge)

