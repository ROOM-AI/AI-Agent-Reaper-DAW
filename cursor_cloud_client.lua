-- Minimal client for CursorDAW Cloud
-- Edit these 3 lines:
local API_URL  = "https://ai-agent-reaper-daw-production.up.railway.app"
local API_KEY  = "YOUR_LONG_RANDOM_KEY"  -- same as Railway env
local SESSION  = "demo"                   -- or unique per user

local function http_get(path, qs, authed)
  local url = API_URL .. path .. (qs and ("?"..qs) or "")
  local hdr = authed and ('-H "x-api-key: '..API_KEY..'"') or ""
  local cmd = string.format('curl -s %s "%s"', hdr, url)
  local _, out = reaper.ExecProcess(cmd, 10)
  return out or ""
end

local function http_post_json(path, body, authed)
  local tmp = reaper.GetResourcePath().."/cursor_tmp.json"
  local f = io.open(tmp,"w"); f:write(body); f:close()
  local hdr = authed and ('-H "x-api-key: '..API_KEY..'"') or ""
  local cmd = string.format('curl -s -X POST %s -H "Content-Type: application/json" --data-binary "@%s" "%s%s"',
    hdr, tmp, API_URL, path)
  local _, out = reaper.ExecProcess(cmd, 10)
  return out or ""
end

local function report(step_id, ok, meta_json)
  local body = string.format('{"session_id":"%s","step_id":"%s","ok":%s%s}',
    SESSION, step_id, ok and "true" or "false", meta_json and (',"meta":'..meta_json) or "")
  http_post_json("/v1/report", body, true)
end

-- naive JSON field pickup (fine for demo). For production, drop in a tiny JSON lib.
local function parse_field(s, key)
  local pat = '"'..key..'"%s*:%s*"([^"]+)"'
  return s:match(pat)
end

local function ExecuteAction(cmd_json)
  local action = parse_field(cmd_json, "action")
  local step_id = parse_field(cmd_json, "id") or parse_field(cmd_json, "step_id") or "s?"
  if action == "ADD_FX" then
    local plugin = parse_field(cmd_json, "plugin") or "Unknown"
    -- >>> call your existing helpers here <<<
    -- AddFX(target, plugin); SetFXParams(target, plugin, params)
    report(step_id, true, '{"note":"added '..plugin..'"}')
  elseif action == "SET_FX_PARAM" then
    -- SetFXParams(...)
    report(step_id, true, '{"note":"params set"}')
  elseif action == "VERIFY" then
    -- compute metrics if you have them
    report(step_id, true, '{"LUFS":-12.0}')
  else
    report(step_id, false, '{"error":"unknown action"}')
  end
end

local function loop()
  local out = http_get("/v1/next", "session_id="..SESSION, true)
  -- if there's a command, it looks like: {"command":{"step_id":"s1","session_id":"demo","command":{...}}}
  if out:find('{"command":{') and not out:find('"command": null') then
    -- hand the nested "command" object to ExecuteAction. quick slice:
    local cmd = out:match('("command"%s*:%s*{.*})')
    if cmd then
      local inner = cmd:match(':%s*({.*})') or "{}"
      ExecuteAction(inner)
    end
  end
  reaper.defer(loop)
end

reaper.ShowConsoleMsg("Cursor Cloud client running. Session "..SESSION.."\n")
loop()
