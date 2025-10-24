# Clean Agent vs Old Agent

## File Comparison

| Feature | Old (`ai_agent_reaper_final.py`) | New (`ai_agent_clean.py`) |
|---------|----------------------------------|---------------------------|
| **Lines of code** | 6,261 | 340 |
| **Retry loops** | Yes (up to 20 attempts) | No (1 attempt, learn result) |
| **Memory system** | Text history + structured JSON | Knowledge base (what works/fails) |
| **Sanity checks** | Yes (API calls) | No (trust the plan) |
| **Conversation history** | Yes | No |
| **Audio analysis** | Yes (librosa, PANNs, etc.) | No |
| **Snapshot/undo** | Yes | No |
| **Reference matching** | Yes | No |

---

## What You Get With Clean Version

### **TRANSPARENCY**
You see EXACTLY what happens:

```
💬 Command: remove automation on track 1

📊 Getting current state...
🧠 Planning...
💭 Reasoning: Will use CLEAR_AUTOMATION to delete all points
📝 Commands: ['SELECT_TRACK 1', 'CLEAR_AUTOMATION 1 Volume']

⚡ Executing...
📢 Reaper: ✓ Selected track 1
           ✓ CLEAR_AUTOMATION: Cleared 5 automation points

🔍 Checking what changed...

✅ STATE CHANGED:
   Removed: Volume Automation: 5 points

🎉 SUCCESS!
✅ Learned: SELECT_TRACK works (1 times)
✅ Learned: CLEAR_AUTOMATION works (1 times)
```

**OR if it fails:**

```
❌ STATE DID NOT CHANGE
   The commands executed but nothing happened in the project.

❌ Learned: CLEAR_AUTOMATION doesn't work (1 times) - No state change

💡 What this means:
   - The command isn't broken (Reaper executed it)
   - But it doesn't do what we need for this task
   - I'll remember this and try something else next time
```

---

### **SELF-AWARENESS**

The agent builds a knowledge base:

```json
{
  "working_commands": {
    "SELECT_TRACK": 5,
    "VOL_DIP": 3,
    "ADD_FX": 2
  },
  "broken_commands": {
    "40205": 3,
    "40406": 2
  },
  "command_effects": {
    "SELECT_TRACK": "Changed: Selected: YES",
    "VOL_DIP": "Added: Volume Automation: 9 points"
  }
}
```

**Next time** you ask to remove automation:
- Agent sees: "40205 failed 3 times - don't use it"
- Agent tries: "CLEAR_AUTOMATION worked before - use that"

---

### **NO RETRY HELL**

**Old agent:**
```
Attempt 1/20: Try action 40205
❌ Failed
Attempt 2/20: Try VOL_DIP
❌ Failed (made it worse)
Attempt 3/20: Try action 40406
❌ Failed
...
Attempt 8/20: Crash (API timeout)
```

**New agent:**
```
Try: CLEAR_AUTOMATION
✅ Worked → Remember this
DONE
```

---

## How It Learns

### **Example: Delete Automation Task**

**First time:**
```
User: remove automation on track 1
Agent: Tries CLEAR_AUTOMATION
Result: ✅ Works! (5 points deleted)
Agent: Saves to knowledge base
```

**Second time:**
```
User: delete automation on track 3
Agent: Sees in knowledge: CLEAR_AUTOMATION worked before
Agent: Uses CLEAR_AUTOMATION again
Result: ✅ Works!
```

**If something fails:**
```
User: remove automation on track 2
Agent: Tries action 40205
Result: ❌ No state change
Agent: Saves to knowledge: 40205 doesn't work

Next time: Won't use 40205 again
```

---

## How To Use

### **Run the clean agent:**
```bash
python ai_agent_clean.py
```

### **Commands:**
```
💬 Command: remove automation on track 1
💬 Command: add reverb to track 2
💬 Command: create volume dip on track 3 from 5 to 10 seconds
💬 Command: show knowledge  (see what it learned)
💬 Command: quit
```

---

## What's Missing (That You Don't Need)

### **Removed from old agent:**
- ❌ 20 retry loops (just try once, learn result)
- ❌ Audio analysis (not needed for commands)
- ❌ Reference matching (separate feature)
- ❌ Sanity checks (caused API timeouts)
- ❌ Conversation memory (not needed for single commands)
- ❌ Snapshot/undo (Reaper has this built-in)
- ❌ 5000+ lines of complexity

### **What you still have:**
- ✅ Planning (Claude decides what to do)
- ✅ Execution (sends to Reaper)
- ✅ Verification (checks if it worked)
- ✅ Learning (remembers what works)
- ✅ Transparency (you see everything)

---

## When To Use Which

### **Use `ai_agent_clean.py` when:**
- Learning what commands work
- Testing new tasks
- Need to see exactly what's happening
- Want fast, honest feedback

### **Use `ai_agent_reaper_final.py` when:**
- Need audio analysis features
- Need reference matching
- Need snapshot/undo system
- Task requires multiple retries to tune parameters

---

## Code Structure (Clean)

```python
# 1. Knowledge Base
class Knowledge:
    def record_success(command, effect)
    def record_failure(command, reason)
    def is_known_broken(command)

# 2. Reaper Interface
def send_to_reaper(commands)
def get_state()
def get_feedback()

# 3. State Comparison
def diff_states(before, after)

# 4. Agent Logic
def plan(user_input, state, knowledge)
def execute(user_input, knowledge)

# 5. Main Loop
while True:
    user_input = input()
    execute(user_input, knowledge)
```

**That's it.** 340 lines total.

---

## Try It

1. **Run clean agent:**
   ```bash
   python ai_agent_clean.py
   ```

2. **Try your failing command:**
   ```
   remove automation on track 1
   ```

3. **See what happens:**
   - If it works → it learned the solution
   - If it fails → it learned what doesn't work
   - Either way, you see EXACTLY what it tried

4. **Check what it learned:**
   ```
   show knowledge
   ```

---

## Next Steps

After the agent learns what works:
1. **You can add those working commands to the old agent** (so it has more tools)
2. **Or just keep using the clean agent** (it's simpler)
3. **Or build a hybrid** (clean core + specific features you need)

The clean agent is a **diagnostic tool** - use it to figure out what works, then decide how to evolve from there.

