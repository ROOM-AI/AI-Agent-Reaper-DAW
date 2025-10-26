-- CursorDAW Cloud Demo - Simple command watcher

local COMMAND_FILE = os.getenv("USERPROFILE") .. "\\Documents\\reaper_commands.txt"
local last_cmd = ""

reaper.ShowConsoleMsg("CursorDAW Cloud Demo\n")
reaper.ShowConsoleMsg("Watching for commands...\n\n")

function main()
    local f = io.open(COMMAND_FILE, "r")
    if f then
        local cmd = f:read("*all")
        f:close()
        
        if cmd and cmd ~= "" and cmd ~= last_cmd then
            last_cmd = cmd
            reaper.ShowConsoleMsg("Command: " .. cmd:sub(1, 60) .. "\n")
            
            local m = cmd:lower()
            if m:find("play") then
                reaper.Main_OnCommand(1007, 0)
            elseif m:find("stop") then
                reaper.Main_OnCommand(1016, 0)
            elseif m:find("record") then
                reaper.Main_OnCommand(1013, 0)
            elseif m:find("add_track") or m:find("add track") then
                reaper.Main_OnCommand(40001, 0)
            end
            
            local c = io.open(COMMAND_FILE, "w")
            if c then c:close() end
        end
    end
    
    reaper.defer(main)
end

main()

