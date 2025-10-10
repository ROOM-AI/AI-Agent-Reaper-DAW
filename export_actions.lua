local file = io.open("C:\\Users\\moosb\\AIAGENT DAW\\reaper_actions_list.txt", "w")

-- Main section actions
local section = 0
local i = 0
repeat
    local retval = reaper.kbd_enumerateActions(section, i)
    if retval then
        local cmd = reaper.ReverseNamedCommandLookup(retval)
        if cmd then
            file:write(cmd .. " | " .. retval .. "\n")
        end
    end
    i = i + 1
until not retval

file:close()
reaper.ShowMessageBox("Actions exported!", "Done", 0)