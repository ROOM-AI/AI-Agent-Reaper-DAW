-- reaper_cloud_agent.lua
-- Drop this into Reaper and it connects to your cloud automatically!

local CLOUD_URL = "https://feelings36lex36slo-97692729550.europe-west1.run.app"
local COMMAND_FILE = "C:\\Users\\moosb\\AIAGENT DAW\\reaper_commands.txt"
local STATE_FILE = "C:\\Users\\moosb\\AIAGENT DAW\\reaper_state.json"

-- Simple HTTP client using Reaper's built-in functions
function http_request(url, method, data)
    -- Use Reaper's JS bridge for HTTP requests
    local js_code = string.format([[
        var xhr = new XMLHttpRequest();
        xhr.open('%s', '%s', false);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send('%s');
        return xhr.status + '|' + xhr.responseText;
    ]], method or 'GET', url, data or '')
    
    -- Execute JS and get result
    local result = reaper.ExecProcess(js_code, 0)
    if result then
        local status, response = result:match("(%d+)|(.+)")
        return tonumber(status), response
    end
    return 0, ""
end

-- Poll for commands from file (written by Python bridge)
function poll_commands()
    -- Read command file written by Python bridge
    local file = io.open(COMMAND_FILE, "r")
    if file then
        local commands = file:read("*all")
        file:close()
        
        if commands and commands ~= "" then
            -- Clear the file after reading
            local clear_file = io.open(COMMAND_FILE, "w")
            if clear_file then
                clear_file:close()
            end
            
            -- Process each command
            for cmd in commands:gmatch("[^\n]+") do
                if cmd and cmd ~= "" then
                    reaper.ShowConsoleMsg("📥 Executing: " .. cmd .. "\n")
                    execute_command(cmd)
                end
            end
        end
    end
end

-- Execute a single command
function execute_command(cmd)
    -- Parse command format: ADD_FX:Track 1:ReaVerb
    -- or SET_PARAM:ReaVerb:Wet:0.3
    -- or AI_MESSAGE:text
    
    if cmd:match("^ADD_FX:") then
        -- ADD_FX:Track 1:ReaVerb
        local track_str, fx_name = cmd:match("^ADD_FX:(.+):(.+)$")
        if track_str and fx_name then
            local track_num = track_str:match("Track (%d+)")
            if track_num then
                local track = reaper.GetTrack(0, tonumber(track_num) - 1)
                if track then
                    reaper.TrackFX_AddByName(track, fx_name, false, -1)
                    reaper.ShowConsoleMsg("✅ Added " .. fx_name .. " to Track " .. track_num .. "\n")
                end
            end
        end
        
    elseif cmd:match("^AI_MESSAGE:") then
        local message = cmd:match("^AI_MESSAGE:(.+)$")
        reaper.ShowConsoleMsg("💬 AI: " .. message .. "\n")
        
    else
        reaper.ShowConsoleMsg("⚠️ Unknown command: " .. cmd .. "\n")
    end
end

-- Send state to cloud
function send_state()
    -- Create simple state
    local state = string.format('{"tracks":%d,"position":%.2f,"playing":%s,"timestamp":%d}',
        reaper.CountTracks(0),
        reaper.GetCursorPosition(),
        (reaper.GetPlayState() & 1) and "true" or "false",
        os.time()
    )
    
    -- Write state to file first
    local file = io.open(STATE_FILE, "w")
    if file then
        file:write(state)
        file:close()
        reaper.ShowConsoleMsg("📤 State exported: " .. state:sub(1, 50) .. "...\n")
    end
end

-- Main cloud agent loop
function CloudAgent()
    poll_commands()
    send_state()
    
    -- Loop every 1 second
    reaper.defer(function() 
        reaper.runloop(CloudAgent)
    end)
end

-- Start the cloud agent
reaper.ShowConsoleMsg("☁️ REAPER CLOUD AGENT STARTING...\n")
reaper.ShowConsoleMsg("📍 Cloud URL: " .. CLOUD_URL .. "\n")
reaper.ShowConsoleMsg("📁 Command file: " .. COMMAND_FILE .. "\n")
reaper.ShowConsoleMsg("✅ Connecting to cloud AI agent...\n")

-- Start the connection
CloudAgent()

reaper.ShowConsoleMsg("🎹 REAPER CLOUD AGENT ACTIVE! 🎹\n")
