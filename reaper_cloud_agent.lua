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

-- Poll for commands from cloud
function poll_commands()
    local status, response = http_request(CLOUD_URL .. "/api/reaper/poll")
    
    if status == 200 and response and response ~= "" then
        -- Write command to file
        local file = io.open(COMMAND_FILE, "w")
        if file then
            file:write(response)
            file:close()
            reaper.ShowConsoleMsg("📥 Command received: " .. response:sub(1, 50) .. "...\n")
        end
    end
end

-- Send state to cloud
function send_state()
    local file = io.open(STATE_FILE, "r")
    if file then
        local state = file:read("*all")
        file:close()
        
        if state and state ~= "" then
            local status, response = http_request(CLOUD_URL .. "/api/reaper/state", "POST", state)
            if status == 200 then
                reaper.ShowConsoleMsg("📤 State sent to cloud\n")
            end
        end
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
