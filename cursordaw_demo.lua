-- CursorDAW Cloud Demo
-- Just watches for commands from cloud

local COMMAND_FILE = os.getenv("USERPROFILE") .. "\\Documents\\reaper_commands.txt"
local last_command = ""

reaper.ShowConsoleMsg("CursorDAW Cloud Demo Started!\n")
reaper.ShowConsoleMsg("Watching for commands...\n\n")

function check_commands()
    local file = io.open(COMMAND_FILE, "r")
    if file then
        local cmd = file:read("*all")
        file:close()
        
        if cmd and cmd ~= "" and cmd ~= last_command then
            reaper.ShowConsoleMsg("Command: " .. cmd:sub(1,50) .. "\n")
            last_command = cmd
            
            local m = cmd:lower()
            if m:find("add_track") or m:find("add track") then
                reaper.Main_OnCommand(40001, 0)
            elseif m:find("record") then
                reaper.Main_OnCommand(1013, 0)
            elseif m:find("play") then
                reaper.Main_OnCommand(1007, 0)
            elseif m:find("stop") then
                reaper.Main_OnCommand(1016, 0)
            end
            
            os.remove(COMMAND_FILE)
        end
    end
    reaper.defer(check_commands)
end

check_commands()

