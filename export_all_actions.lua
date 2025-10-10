-- Export ALL Reaper action IDs to a file
-- Run this once in Reaper to get the complete action list
-- This version works without SWS extension

local file = io.open("C:\\Users\\moosb\\AIAGENT DAW\\reaper_all_actions.txt", "w")

-- Main section (0)
local section = 0
local i = 0
local count = 0

file:write("REAPER ACTION IDS - Main Section\n")
file:write("(To see description: right-click action in Actions window)\n\n")

-- Enumerate all actions
while true do
    local commandID = reaper.kbd_enumerateActions(section, i)
    if not commandID then break end
    
    -- Try to get command name string
    local cmdName = reaper.ReverseNamedCommandLookup(commandID)
    
    if cmdName and cmdName ~= "" then
        file:write(commandID .. "|" .. cmdName .. "\n")
        count = count + 1
    end
    
    i = i + 1
    if i > 100000 then break end
end

file:close()
reaper.ShowConsoleMsg("Exported " .. count .. " action IDs to reaper_all_actions.txt\n")

