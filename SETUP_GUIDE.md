# 🎵 AI Agent for Reaper DAW - Setup Guide

**Control Reaper with natural language using Claude AI**

Voice commands like "add reverb to track 3" or "make it sound like a phone call" are automatically converted to Reaper actions.

---

## ✅ Prerequisites

### Required Software

1. **Reaper DAW** (any recent version)
   - Download: https://www.reaper.fm/download.php
   - Free trial, $60 for personal license

2. **Python 3.9+**
   - **Windows:** https://www.python.org/downloads/
     - ✅ Check "Add Python to PATH" during install
   - **macOS:** `brew install python3` or download from python.org
   - **Linux:** Usually pre-installed, or `sudo apt install python3 python3-pip`

3. **API Keys** (required):
   - **Anthropic Claude API** - Get at: https://console.anthropic.com/
   - **OpenAI API** (optional, for lyrics extraction) - Get at: https://platform.openai.com/api-keys

---

## 🚀 Quick Start (Local Mode)

### Step 1: Install Python Dependencies

Open terminal/command prompt in the project folder:

**Windows:**
```bash
cd "C:\path\to\AI-Agent-Reaper-DAW"
pip install anthropic openai python-dotenv watchdog requests numpy scipy
```

**macOS/Linux:**
```bash
cd ~/path/to/AI-Agent-Reaper-DAW
pip3 install anthropic openai python-dotenv watchdog requests numpy scipy
```

### Step 2: Set Your API Keys (Local Mode Only)

**⚠️ Skip this if using cloud mode - keys are already in the cloud!**

**Option A: Use .env file (recommended)**

Create a file named `.env` in the project folder:

```env
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
```

**Option B: Set in local agent.py**

Edit `local agent.py` lines 111-114 and paste your keys directly.

**Cloud Mode:** API keys are set in Cloud Run environment variables, not locally.

### Step 3: Load Lua Script in Reaper

1. Open Reaper
2. **Actions → Show action list**
3. Click **"New action..."** → **"Load ReaScript..."**
4. Navigate to project folder and select `reaper_agent.lua`
5. Click **"Run"**
6. You should see: "🤖 Reaper AI Agent Started" in Reaper's console

**The Lua script must stay running!** Don't close Reaper's action window.

### Step 4: Start the Bridge (connects Lua to Python)

**Windows:**
```bash
python cloud_bridge.py
```

**macOS/Linux:**
```bash
python3 cloud_bridge.py
```

You should see:
```
CursorDAW Cloud Bridge
Cloud: https://...
Session: demo
✓ Watching reaper_state.txt for changes
✓ Polling cloud for commands
```

### Step 5: Run the Agent

**Open a NEW terminal window** (keep bridge running), then:

**Windows:**
```bash
python "local agent.py"
```

**macOS/Linux:**
```bash
python3 "local agent.py"
```

The agent will prompt you: `🎤 You:`

Type commands like:
- `add reverb to track 3`
- `make it sound like a phone call`
- `create volume dip from 10 to 20 seconds`

---

## ☁️ Cloud Mode (Run Agent in Cloud, Control from Web)

### Why Cloud Mode?

- Access from any device with a browser
- **No Python or API keys needed locally** (only Reaper + Lua + Bridge)
- Multiple users can control different Reaper instances
- Agent runs on the server, you just control it

### Using Existing Cloud Deployment (Easiest)

**If someone already deployed the cloud version:**

1. **Just run Reaper + Lua + Bridge** - that's it!
   - Load `reaper_agent.lua` in Reaper
   - Edit `cloud_bridge.py` line 14: Set `CLOUD_URL` to the deployed URL
   - Run: `python cloud_bridge.py`
   - Open the URL in browser → control Reaper from web!

2. **No API keys needed locally!** Keys are stored in the cloud deployment.

### Setup Your Own Cloud Deployment (Google Cloud Run)

1. **Install Google Cloud SDK**
   - Download: https://cloud.google.com/sdk/docs/install

2. **Login and Set Project**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

4. **Set Environment Variables**
   - Go to Cloud Console → Cloud Run → Your Service
   - Click "Edit & Deploy New Revision"
   - Add environment variables:
     - `ANTHROPIC_API_KEY`: Your Claude API key
     - `OPENAI_API_KEY`: Your OpenAI key

5. **Update cloud_bridge.py**
   - Edit line 14: `CLOUD_URL = "https://your-deployed-url.run.app"`

6. **Run Bridge + Lua (local), Access UI (cloud)**
   - Start `reaper_agent.lua` in Reaper (same as local mode)
   - Start `cloud_bridge.py` (connects your Reaper to cloud)
   - Open `https://your-deployed-url.run.app` in browser
   - Control Reaper from the web interface!

---

## 🎛️ Available Commands

### FX/Plugins
- `add reverb to track 3`
- `add Pro-Q 3 to track 2`
- `remove first effect from track 1`

### Automation
- `create volume dip from 10 to 20 seconds on track 3`
- `automate reverb mix from 30% to 80% from 5 to 10 seconds`

### Effects Presets
- `make it sound like a phone call` (bandpass 300-3000Hz)
- `make it sound underwater` (lowpass at 1000Hz)
- `brighten the vocal` (high shelf boost)

### Track Control
- `select track 2`
- `set track 3 volume to -6dB`
- `pan track 1 to the left`

### Analysis
- `analyze track 2` (audio analysis with recommendations)
- `get lyrics from track 1` (uses Whisper AI to transcribe)

---

## 📁 Project Structure

```
AI-Agent-Reaper-DAW/
├── local agent.py          # Main AI agent (local mode)
├── reaper_agent.lua        # Reaper script (load this in Reaper)
├── cloud_bridge.py         # Connects Reaper ↔ Cloud
├── main.py                 # Cloud server (FastAPI)
├── prompt_enhancer.py      # Makes vague prompts specific
├── reaper_actions.txt      # Available Reaper actions
├── reaper_plugins_list.txt # Available plugins
├── sound_knowledge_base.json # Audio production knowledge
└── requirements.txt        # Python dependencies
```

---

## 🐛 Troubleshooting

### "Command file not found"
- Make sure paths in `local agent.py` lines 96-100 match where you want files
- Default: `C:\Users\YOUR_NAME\AIAGENT DAW\`

### "API key not valid"
- Check your `.env` file or hardcoded keys
- Verify keys at https://console.anthropic.com/ and https://platform.openai.com/

### "Lua script not running"
- In Reaper: Actions → Show action list
- Look for "reaper_agent.lua" in the list
- Select it and click "Run" again

### "Bridge can't connect to cloud"
- Check `CLOUD_URL` in `cloud_bridge.py` line 14
- Make sure your cloud service is deployed and running
- Test URL in browser - should show the web interface

### "State not updating"
- The Lua script exports state automatically
- Check Reaper console (View → Show console) for errors
- Bridge should show "→ Sent state to cloud" messages

---

## 💡 Tips

1. **Use the Enhance button** (cloud mode) to improve vague prompts before sending

2. **Track numbers are 0-indexed in commands but 1-indexed in Reaper UI:**
   - Reaper shows "Track 1" → Use `trackIdx=0` in commands
   - The agent handles this automatically

3. **Check logs** if something fails:
   - Reaper console: View → Show console
   - Bridge terminal: Shows all commands sent
   - Agent output: Shows reasoning and verification

4. **Audio analysis requires extra packages:**
   ```bash
   pip install librosa soundfile
   ```

---

## 🎓 Examples

### Basic Workflow

```
🎤 You: add reverb to track 3 and make it sound distant

Agent thinks:
- Track 3 = index 2
- "distant" = long decay time, higher mix
- Command: ADD_FX 2 VST3: ValhallaRoom
- Set decay to 4.5s, mix to 45%

✅ Success: Reverb added with distant sound
```

### Complex Multi-Step

```
🎤 You: make the vocal sound like it's coming through a phone, 
        but only from 30 to 45 seconds

Agent thinks:
- "Phone call" = bandpass 300-3000Hz with steep slopes
- "Only from 30-45s" = automation
- Steps:
  1. Add Pro-Q 3 to track (vocal = track 1 = index 0)
  2. Configure bandpass filter
  3. Automate bypass: off at 30s, on at 45s

✅ Success: Phone effect appears 30-45s only
```

---

## 🔒 Security Notes

- **Never commit `.env` file** with real API keys to public repos
- Use environment variables in cloud deployments
- API keys give access to your accounts - keep them secret!

---

## 📝 License

MIT License - Use freely, modify, distribute. See LICENSE file.

---

## 🤝 Contributing

PRs welcome! Areas for improvement:
- More effect presets
- Better audio analysis
- Support for other DAWs
- Mobile app version

---

## 🆘 Support

- Issues: https://github.com/YOUR_REPO/issues
- Discussions: https://github.com/YOUR_REPO/discussions

---

**Enjoy controlling your DAW with AI! 🎵✨**

