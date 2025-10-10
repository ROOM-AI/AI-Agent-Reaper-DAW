-- Safe batch export of Reaper actions with descriptions
-- Processes in chunks to avoid crash
-- Run this in Reaper: Actions → Load ReaScript → select this file

local OUTPUT_FILE = [[C:\Users\moosb\AIAGENT DAW\reaper_actions_with_descriptions.txt]]
local CHUNK_SIZE = 100  -- Process 100 actions at a time
local DELAY = 0.05      -- 50ms delay between chunks

-- State tracking
local section = 0
local current_index = 0
local total_exported = 0
local start_time = reaper.time_precise()

-- Open file for writing
local file = io.open(OUTPUT_FILE, "w")
if not file then
    reaper.ShowMessageBox("Could not open output file for writing!", "Error", 0)
    return
end

file:write("REAPER ACTIONS WITH DESCRIPTIONS\n")
file:write("Format: ActionID|Description\n")
file:write("Generated: " .. os.date("%Y-%m-%d %H:%M:%S") .. "\n\n")
file:close()

function process_chunk()
    local file = io.open(OUTPUT_FILE, "a")  -- Append mode
    if not file then
        reaper.ShowConsoleMsg("ERROR: Could not open file for appending\n")
        return false
    end
    
    local chunk_count = 0
    
    -- Process CHUNK_SIZE actions
    while chunk_count < CHUNK_SIZE do
        local commandID = reaper.kbd_enumerateActions(section, current_index)
        
        if not commandID then
            -- No more actions
            file:close()
            local elapsed = reaper.time_precise() - start_time
            reaper.ShowConsoleMsg(string.format("\n✅ COMPLETE! Exported %d actions in %.1f seconds\n", total_exported, elapsed))
            reaper.ShowMessageBox(
                string.format("Successfully exported %d actions!\n\nFile: %s", total_exported, OUTPUT_FILE),
                "Export Complete",
                0
            )
            return false  -- Stop processing
        end
        
        -- Get description using NamedCommandLookup
        local desc = reaper.CF_GetCommandText(section, commandID)
        
        -- If no description, try reverse lookup for command name
        if not desc or desc == "" then
            desc = reaper.ReverseNamedCommandLookup(commandID) or "No description"
        end
        
        -- Write to file
        file:write(commandID .. "|" .. desc .. "\n")
        
        current_index = current_index + 1
        chunk_count = chunk_count + 1
        total_exported = total_exported + 1
        
        -- Safety: don't go infinite
        if current_index > 150000 then
            break
        end
    end
    
    file:close()
    
    -- Show progress
    if total_exported % 500 == 0 then
        reaper.ShowConsoleMsg(string.format("Progress: %d actions exported...\n", total_exported))
    end
    
    -- Continue processing
    reaper.defer(process_chunk)
    return true
end

-- Check if SWS/CF extension is available (for better descriptions)
if not reaper.CF_GetCommandText then
    reaper.ShowConsoleMsg("⚠️ WARNING: SWS extension not found\n")
    reaper.ShowConsoleMsg("Descriptions will be limited to command names only\n")
    reaper.ShowConsoleMsg("Install SWS for full descriptions: https://www.sws-extension.org/\n\n")
end

reaper.ShowConsoleMsg("🚀 Starting safe batch export...\n")
reaper.ShowConsoleMsg("Processing " .. CHUNK_SIZE .. " actions every 50ms\n")
reaper.ShowConsoleMsg("You can continue working in Reaper while this runs\n\n")

-- Start processing
process_chunk()

