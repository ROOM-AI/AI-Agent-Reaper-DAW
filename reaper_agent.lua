-- Reaper AI Agent - Background Command Processor
-- Load once: Actions → Show action list → New action → Load ReaScript → select this file → Run
-- Keep running in background

-- Portable base dir using REAPER_AGENT_DIR or ~/AIAGENT DAW (match bridge)
local sep = package.config:sub(1,1)
local base = os.getenv("REAPER_AGENT_DIR")
if not base or base == "" then
  local home = os.getenv(sep == "\\" and "USERPROFILE" or "HOME") or "."
  base = home .. sep .. "AIAGENT DAW"
end
local COMMAND_FILE = base .. sep .. "reaper_commands.txt"
local STATE_FILE   = base .. sep .. "reaper_state.txt"
local FEEDBACK_FILE= base .. sep .. "reaper_feedback.txt"
local last_check = reaper.time_precise()
local last_state_export = reaper.time_precise()
local state_export_counter = 0

function msg(s) reaper.ShowConsoleMsg(tostring(s).."\n") end

-- Parameter conversion helpers
function db_to_normalized(target_db, min_db, max_db)
    min_db = min_db or -30
    max_db = max_db or 30
    return (target_db - min_db) / (max_db - min_db)
end

function normalized_to_db(normalized, min_db, max_db)
    min_db = min_db or -30
    max_db = max_db or 30
    return min_db + (normalized * (max_db - min_db))
end

-- Feedback buffer to report back to Python
local feedback_buffer = {}

function add_feedback(message)
    table.insert(feedback_buffer, message)
end

function write_feedback()
    if #feedback_buffer > 0 then
        local file = io.open(FEEDBACK_FILE, "w")
        if file then
            for _, msg in ipairs(feedback_buffer) do
                file:write(msg .. "\n")
            end
            file:close()
        end
        feedback_buffer = {}
    end
end

-- Generalized command execution wrapper
-- Automatically logs success/failure for ANY command
function execute_with_feedback(command_name, success, message)
    if success then
        local feedback_msg = string.format("✓ %s: %s", command_name, message or "success")
        msg(feedback_msg)
        add_feedback(feedback_msg)
        return true
    else
        local feedback_msg = string.format("✗ %s: %s", command_name, message or "failed")
        msg(feedback_msg)
        add_feedback(feedback_msg)
        return false
    end
end

function export_state()
    -- Export FULL Reaper project state to file (like Cursor reading entire codebase)
    local stateFile = io.open(STATE_FILE, "w")
    if not stateFile then return end
    
    state_export_counter = state_export_counter + 1
    local precise_time = reaper.time_precise()
    
    local numTracks = reaper.CountTracks(0)
    local playState = reaper.GetPlayState()
    local cursorPos = reaper.GetCursorPosition()
    local _, tempo = reaper.GetProjectTimeSignature2(0)
    
    -- Project-level info
    stateFile:write("=== PROJECT STATE ===\n")
    stateFile:write(string.format("Timestamp: %d\n", os.time()))
    stateFile:write(string.format("Export Counter: %d\n", state_export_counter))
    stateFile:write(string.format("Precise Time: %.6f\n", precise_time))
    stateFile:write(string.format("Playing: %s\n", ((playState & 1) ~= 0) and "Yes" or "No"))
    stateFile:write(string.format("Cursor Position: %.2fs\n", cursorPos))
    stateFile:write(string.format("Tempo: %.1f BPM\n", tempo))
    stateFile:write(string.format("Total Tracks: %d\n", numTracks))
    
    -- Time selection
    local timeStart, timeEnd = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    if timeStart ~= timeEnd then
        stateFile:write(string.format("Time Selection: %.2fs to %.2fs (%.2fs duration)\n", timeStart, timeEnd, timeEnd-timeStart))
    end
    
    -- Loop points
    local loopStart, loopEnd = reaper.GetSet_LoopTimeRange(false, true, 0, 0, false)
    if loopStart ~= loopEnd then
        stateFile:write(string.format("Loop: %.2fs to %.2fs\n", loopStart, loopEnd))
    end
    
    stateFile:write("\n=== TRACKS ===\n")
    
    -- Detailed track info
    for i = 0, numTracks - 1 do
        local track = reaper.GetTrack(0, i)
        local _, trackName = reaper.GetTrackName(track)
        local volume = reaper.GetMediaTrackInfo_Value(track, "D_VOL")
        local pan = reaper.GetMediaTrackInfo_Value(track, "D_PAN")
        local mute = reaper.GetMediaTrackInfo_Value(track, "B_MUTE")
        local solo = reaper.GetMediaTrackInfo_Value(track, "I_SOLO")
        local selected = reaper.IsTrackSelected(track)
        local numFX = reaper.TrackFX_GetCount(track)
        local numItems = reaper.CountTrackMediaItems(track)
        
        local displayIndex = i + 1  -- Use 1-based numbering for consistency with commands/UI
        stateFile:write(string.format("\n--- Track %d: %s ---\n", displayIndex, trackName))
        stateFile:write(string.format("  Volume: %.1f dB (%.0f%%)\n", 20*math.log(volume, 10), volume*100))
        stateFile:write(string.format("  Pan: %.0f%%\n", pan*100))
        stateFile:write(string.format("  Mute: %s | Solo: %s | Selected: %s\n", 
            mute == 1 and "YES" or "no", 
            solo > 0 and "YES" or "no",
            selected and "YES" or "no"))
        stateFile:write(string.format("  Media Items: %d\n", numItems))
        
        -- FX chain with parameters
        if numFX > 0 then
            stateFile:write(string.format("  FX Chain (%d plugins):\n", numFX))
            for j = 0, numFX - 1 do
                local _, fxName = reaper.TrackFX_GetFXName(track, j, "")
                local enabled = reaper.TrackFX_GetEnabled(track, j)
                stateFile:write(string.format("    [%d] %s %s\n", j, fxName, enabled and "" or "(BYPASSED)"))
                
                -- All parameters grouped by category
                local numParams = reaper.TrackFX_GetNumParams(track, j)
                if numParams > 0 then
                    local currentSection = ""
                    local maxShow = numParams  -- Show ALL params (no limit)
                    
                    for p = 0, maxShow - 1 do
                        local value = reaper.TrackFX_GetParam(track, j, p)
                        local _, paramName = reaper.TrackFX_GetParamName(track, j, p, "")
                        local _, displayValue = reaper.TrackFX_GetFormattedParamValue(track, j, p, "")
                        local nameLower = paramName:lower()
                        
                        -- Detect section changes
                        local newSection = ""
                        if nameLower:find("band %d+") or nameLower:find("eq") then
                            newSection = "EQ BANDS"
                        elseif nameLower:find("tap %d+") or nameLower:find("delay tap") then
                            newSection = "DELAY TAPS"
                        elseif nameLower:find("filter") then
                            newSection = "FILTERS"
                        elseif nameLower:find("lfo") or nameLower:find("modulation") then
                            newSection = "MODULATION"
                        elseif nameLower:find("dynamics") or nameLower:find("compress") or nameLower:find("threshold") then
                            newSection = "DYNAMICS"
                        elseif nameLower:find("output") or nameLower:find("mix") or nameLower:find("gain") and p > numParams - 10 then
                            newSection = "OUTPUT"
                        elseif p < 20 and currentSection == "" then
                            newSection = "MAIN CONTROLS"
                        end
                        
                        -- Print section header if changed
                        if newSection ~= "" and newSection ~= currentSection then
                            stateFile:write(string.format("\n        === %s ===\n", newSection))
                            currentSection = newSection
                        end
                        
                        stateFile:write(string.format("        p%d %s: %.0f%% [%s]\n", p, paramName, value*100, displayValue))
                    end
                    
                    -- All params shown, no truncation message needed
                end
                
                -- Check for FX parameter automation envelopes
                local hasAutomation = false
                for p = 0, numParams - 1 do
                    local env = reaper.GetFXEnvelope(track, j, p, false)
                    if env then
                        local numPoints = reaper.CountEnvelopePoints(env)
                        if numPoints > 0 then
                            if not hasAutomation then
                                stateFile:write("\n        === AUTOMATED PARAMETERS ===\n")
                                hasAutomation = true
                            end
                            local _, paramName = reaper.TrackFX_GetParamName(track, j, p, "")
                            stateFile:write(string.format("        p%d %s: %d automation points\n", p, paramName, numPoints))
                            -- Show first few points
                            local maxShow = math.min(numPoints, 3)
                            for pt = 0, maxShow - 1 do
                                local _, time, value = reaper.GetEnvelopePoint(env, pt)
                                stateFile:write(string.format("          %.2fs: %.0f%%\n", time, value*100))
                            end
                            if numPoints > 3 then
                                stateFile:write(string.format("          ... (%d more points)\n", numPoints - 3))
                            end
                        end
                    end
                end
            end
        else
            stateFile:write("  FX Chain: (empty)\n")
        end
        
        -- Volume envelope automation
        local volEnv = reaper.GetTrackEnvelopeByName(track, "Volume")
        if volEnv then
            local numPoints = reaper.CountEnvelopePoints(volEnv)
            if numPoints > 0 then
                stateFile:write(string.format("  Volume Automation: %d points\n", numPoints))
                -- Show first few points
                local maxShow = math.min(numPoints, 5)
                for p = 0, maxShow - 1 do
                    local _, time, value = reaper.GetEnvelopePoint(volEnv, p)
                    stateFile:write(string.format("    %.2fs: %.1fdB\n", time, 20*math.log(value, 10)))
                end
                if numPoints > 5 then
                    stateFile:write(string.format("    ... (%d more points)\n", numPoints - 5))
                end
            end
        end
    end
    
    stateFile:write("\n=== END STATE ===\n")
    stateFile:close()
end

function process_command(line)
    local parts = {}
    for word in line:gmatch("%S+") do
        table.insert(parts, word)
    end
    
    local cmd = parts[1]
    
    -- Special command to export state
    if cmd == "GET_STATE" then
        export_state()
        msg("📊 State exported")
        return
    end
    
    -- Check if cmd is a numeric action ID
    local actionID = tonumber(cmd)
    if actionID then
        reaper.Main_OnCommand(actionID, 0)
        msg("✓ Executed action: " .. actionID)
        add_feedback("✓ Action " .. actionID .. " executed")
        return
    end
    
    -- Custom parametric commands below
    if cmd == "VOL_DIP" then
        -- VOL_DIP <trackIdx> <tStart> <tEnd> <value>
        local trackIdx = tonumber(parts[2]) or 0
        local tStart = tonumber(parts[3]) or 16
        local tEnd = tonumber(parts[4]) or 32
        local value = tonumber(parts[5]) or 0.5
        
        local track = reaper.GetTrack(0, trackIdx)
        if not track then
            execute_with_feedback("VOL_DIP", false, string.format("Track %d not found", trackIdx))
            return
        end
        
        local env = reaper.GetTrackEnvelopeByName(track, "Volume")
        if not env then
            -- Show volume envelope
            reaper.SetTrackSelected(track, true)
            reaper.Main_OnCommand(40406, 0) -- Track: Toggle volume envelope visible
            env = reaper.GetTrackEnvelopeByName(track, "Volume")
        end
        
        if env then
            local _, val_before = reaper.Envelope_Evaluate(env, tStart - 0.001, 0, 0)
            local _, val_after = reaper.Envelope_Evaluate(env, tEnd + 0.001, 0, 0)
            
            reaper.InsertEnvelopePoint(env, tStart-0.0005, val_before, 0, 0.0, true, false)
            reaper.InsertEnvelopePoint(env, tStart, value, 0, 0.0, true, false)
            reaper.InsertEnvelopePoint(env, tEnd, value, 0, 0.0, true, false)
            reaper.InsertEnvelopePoint(env, tEnd+0.0005, val_after, 0, 0.0, true, false)
            
            reaper.Envelope_SortPoints(env)
            execute_with_feedback("VOL_DIP", true, string.format("Track %d: %.1fs→%.1fs at %.0f%%", trackIdx, tStart, tEnd, value*100))
        else
            execute_with_feedback("VOL_DIP", false, string.format("Could not create volume envelope for track %d", trackIdx))
        end
        
    elseif cmd == "SET_TRACK_PAN" then
        -- SET_TRACK_PAN <trackIdx> <panValue>
        local trackIdx = tonumber(parts[2]) or 0
        local panValue = tonumber(parts[3]) or 0.0  -- -1.0 (left) to 1.0 (right)
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            -- Select track first (required for some operations)
            reaper.SetOnlyTrackSelected(track)
            reaper.SetMediaTrackInfo_Value(track, "D_PAN", panValue)
            execute_with_feedback("SET_TRACK_PAN", true, string.format("Track %d pan: %.0f%%", trackIdx, panValue*100))
        else
            execute_with_feedback("SET_TRACK_PAN", false, string.format("Track %d not found", trackIdx))
        end
        
    elseif cmd == "ADD_FX" then
        -- ADD_FX <trackIdx> <fxName>
        local trackIdx = tonumber(parts[2]) or 0
        local fxName = table.concat(parts, " ", 3)
       
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            -- First check if plugin already exists on track
            local numFX = reaper.TrackFX_GetCount(track)
            local existingIdx = -1
            for i = 0, numFX - 1 do
                local _, existingName = reaper.TrackFX_GetFXName(track, i, "")
                -- Check if name contains our search term (case insensitive fuzzy match)
                local searchLower = fxName:lower()
                local existingLower = existingName:lower()
                if existingLower:find(searchLower, 1, true) then
                    existingIdx = i
                    break
                end
            end
            
            if existingIdx >= 0 then
                -- Plugin already exists, just show it
                reaper.TrackFX_Show(track, existingIdx, 3)
                local _, existingName = reaper.TrackFX_GetFXName(track, existingIdx, "")
                local successMsg = string.format("🎛️ Opened existing FX '%s' on track %d", existingName, trackIdx)
                msg(successMsg)
                add_feedback(successMsg)
            else
                -- Plugin not found, try to add it
                -- Build list of variations to try
                local namesToTry = {fxName}  -- Exact match first
                
                -- Try with common vendor wrappers
                local vendors = {"FabFilter", "Waves", "Cockos", "iZotope"}
                for _, vendor in ipairs(vendors) do
                    table.insert(namesToTry, "VST3: " .. fxName .. " (" .. vendor .. ")")
                    table.insert(namesToTry, "VST: " .. fxName .. " (" .. vendor .. ")")
                end
                
                -- Try without wrappers
                table.insert(namesToTry, "VST3: " .. fxName)
                table.insert(namesToTry, "VST: " .. fxName)
                
                -- If name starts with vendor prefix, strip it and try again
                local strippedName = fxName:gsub("^FabFilter ", ""):gsub("^Waves ", ""):gsub("^iZotope ", "")
                if strippedName ~= fxName then
                    table.insert(namesToTry, strippedName)
                    for _, vendor in ipairs(vendors) do
                        table.insert(namesToTry, "VST3: " .. strippedName .. " (" .. vendor .. ")")
                        table.insert(namesToTry, "VST: " .. strippedName .. " (" .. vendor .. ")")
                    end
                end
                
                local matchedName = nil
                local fxIdx = -1
                for _, tryName in ipairs(namesToTry) do
                    fxIdx = reaper.TrackFX_AddByName(track, tryName, false, -1)
                    if fxIdx >= 0 then
                        matchedName = tryName
                        break
                    end
                end
                
                if fxIdx >= 0 then
                    reaper.TrackFX_Show(track, fxIdx, 3)
                    -- Wait for plugin to fully load
                    reaper.defer(function() end)
                    local successMsg = string.format("🎛️ Added FX '%s' (matched as '%s') to track %d", fxName, matchedName, trackIdx)
                    msg(successMsg)
                    add_feedback(successMsg)
                else
                    local failMsg = string.format("❌ Could not find FX: %s", fxName)
                    msg(failMsg)
                    add_feedback(failMsg)
                end
            end
        end
        
    elseif cmd == "SET_FX_PARAM" then
        -- SET_FX_PARAM <trackIdx> <fxIdx> <paramIdx> <value0-1>
        local trackIdx = tonumber(parts[2]) or 0
        local fxIdx = tonumber(parts[3]) or 0
        local paramIdx = tonumber(parts[4]) or 0
        local value = tonumber(parts[5]) or 0.5
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local numFX = reaper.TrackFX_GetCount(track)
            if fxIdx < numFX then
                reaper.TrackFX_SetParam(track, fxIdx, paramIdx, value)
                local _, fxName = reaper.TrackFX_GetFXName(track, fxIdx, "")
                local _, paramName = reaper.TrackFX_GetParamName(track, fxIdx, paramIdx, "")
                local _, displayValue = reaper.TrackFX_GetFormattedParamValue(track, fxIdx, paramIdx, "")
                local successMsg = string.format("🎚️ Track %d FX#%d '%s' - %s → %.0f%% [%s]", trackIdx, fxIdx, fxName, paramName, value*100, displayValue)
                msg(successMsg)
                add_feedback(successMsg)
            else
                local failMsg = string.format("❌ Track %d only has %d FX (tried to access FX#%d)", trackIdx, numFX, fxIdx)
                msg(failMsg)
                add_feedback(failMsg)
            end
        end
        
    elseif cmd == "REMOVE_FX" then
        -- REMOVE_FX <trackIdx> <fxIdx>
        local trackIdx = tonumber(parts[2]) or 0
        local fxIdx = tonumber(parts[3]) or 0
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local numFX = reaper.TrackFX_GetCount(track)
            if fxIdx < numFX then
                local fxName = reaper.TrackFX_GetFXName(track, fxIdx, "")
                reaper.TrackFX_Delete(track, fxIdx)
                local successMsg = string.format("🗑️ Removed FX#%d '%s' from track %d", fxIdx, fxName, trackIdx)
                msg(successMsg)
                add_feedback(successMsg)
            else
                local failMsg = string.format("❌ Track %d only has %d FX (tried to remove FX#%d)", trackIdx, numFX, fxIdx)
                msg(failMsg)
                add_feedback(failMsg)
            end
        end
        
    elseif cmd == "SELECT_TRACK" then
        -- SELECT_TRACK <trackNumber>  (treat input as 1-based; REAPER API is 0-based)
        local trackNumber = tonumber(parts[2]) or 1
        local idx0 = math.max(trackNumber - 1, 0)
        
        -- Deselect all tracks first
        local numTracks = reaper.CountTracks(0)
        for i = 0, numTracks - 1 do
            local track = reaper.GetTrack(0, i)
            reaper.SetTrackSelected(track, false)
        end
        
        -- Select the target track
        local track = reaper.GetTrack(0, idx0)
        if track then
            reaper.SetTrackSelected(track, true)
            -- ALSO "touch" the track by setting volume to current volume (makes it "last touched")
            local currentVol = reaper.GetMediaTrackInfo_Value(track, "D_VOL")
            reaper.SetMediaTrackInfo_Value(track, "D_VOL", currentVol)
            execute_with_feedback("SELECT_TRACK", true, string.format("Selected track %d", trackNumber))
        else
            execute_with_feedback("SELECT_TRACK", false, string.format("Track %d not found", trackNumber))
        end
        
    elseif cmd == "SET_TRACK_VOL" then
        -- SET_TRACK_VOL <trackIdx> <volumeDB>
        local trackIdx = tonumber(parts[2]) or 0
        local volDB = tonumber(parts[3]) or 0
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local volume = 10^(volDB/20)  -- Convert dB to linear
            reaper.SetMediaTrackInfo_Value(track, "D_VOL", volume)
            execute_with_feedback("SET_TRACK_VOL", true, string.format("Track %d → %.1fdB", trackIdx, volDB))
        else
            execute_with_feedback("SET_TRACK_VOL", false, string.format("Track %d not found", trackIdx))
        end
        
    elseif cmd == "CLEAR_AUTOMATION" then
        -- CLEAR_AUTOMATION <trackIdx> <envelopeName>
        local trackIdx = tonumber(parts[2]) or 0
        local envName = parts[3] or "Volume"
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local env = reaper.GetTrackEnvelopeByName(track, envName)
            if env then
                -- Delete all automation points using DeleteEnvelopePointRange
                local numPoints = reaper.CountEnvelopePoints(env)
                if numPoints > 0 then
                    -- Delete entire range of points
                    reaper.DeleteEnvelopePointRange(env, 0, 999999)
                    local successMsg = string.format("🗑️ Cleared %d automation points from %s on track %d", numPoints, envName, trackIdx)
                    msg(successMsg)
                    add_feedback(successMsg)
                else
                    local infoMsg = string.format("ℹ️ No automation points on %s envelope of track %d", envName, trackIdx)
                    msg(infoMsg)
                    add_feedback(infoMsg)
                end
            else
                local failMsg = string.format("❌ No %s envelope on track %d", envName, trackIdx)
                msg(failMsg)
                add_feedback(failMsg)
            end
        else
            local failMsg = string.format("❌ Track %d not found", trackIdx)
            msg(failMsg)
            add_feedback(failMsg)
        end
        
    elseif cmd == "FX_PARAM_AUTO" then
        -- FX_PARAM_AUTO <trackIdx> <fxIdx> <paramIdx> <tStart> <tEnd> <startValue> <endValue>
        local trackIdx = tonumber(parts[2]) or 0
        local fxIdx = tonumber(parts[3]) or 0
        local paramIdx = tonumber(parts[4]) or 0
        local tStart = tonumber(parts[5]) or 0
        local tEnd = tonumber(parts[6]) or 0
        local startValue = tonumber(parts[7]) or 0
        local endValue = tonumber(parts[8]) or 1
        
        local track = reaper.GetTrack(0, trackIdx)
        if not track then
            local failMsg = string.format("❌ Track %d not found", trackIdx)
            msg(failMsg)
            add_feedback(failMsg)
            return
        end
        
        local numFX = reaper.TrackFX_GetCount(track)
        if fxIdx >= numFX then
            local failMsg = string.format("❌ Track %d only has %d FX (tried to access FX#%d)", trackIdx, numFX, fxIdx)
            msg(failMsg)
            add_feedback(failMsg)
            return
        end
        
        -- Get FX and parameter info
        local _, fxName = reaper.TrackFX_GetFXName(track, fxIdx, "")
        local _, paramName = reaper.TrackFX_GetParamName(track, fxIdx, paramIdx, "")
        
        -- Get the parameter envelope (create if doesn't exist)
        local env = reaper.GetFXEnvelope(track, fxIdx, paramIdx, true)
        if not env then
            local failMsg = string.format("❌ Could not get envelope for param %d on FX#%d", paramIdx, fxIdx)
            msg(failMsg)
            add_feedback(failMsg)
            return
        end
        
        -- Get values before and after to preserve existing automation
        local _, val_before = reaper.Envelope_Evaluate(env, tStart - 0.001, 0, 0)
        local _, val_after = reaper.Envelope_Evaluate(env, tEnd + 0.001, 0, 0)
        
        -- Add automation points
        -- Add edge point before automation starts (preserve existing)
        reaper.InsertEnvelopePoint(env, tStart - 0.0005, val_before, 0, 0.0, true, false)
        -- Add start point
        reaper.InsertEnvelopePoint(env, tStart, startValue, 0, 0.0, true, false)
        -- Add end point
        reaper.InsertEnvelopePoint(env, tEnd, endValue, 0, 0.0, true, false)
        -- Add edge point after automation ends (preserve existing)
        reaper.InsertEnvelopePoint(env, tEnd + 0.0005, val_after, 0, 0.0, true, false)
        
        -- Sort points to ensure proper order
        reaper.Envelope_SortPoints(env)
        
        local successMsg = string.format("🎛️ Automated %s > %s: %.2fs→%.2fs (%.0f%%→%.0f%%)", 
            fxName, paramName, tStart, tEnd, startValue*100, endValue*100)
        msg(successMsg)
        add_feedback(successMsg)
        
    elseif cmd == "GOTO" then
        -- GOTO <seconds>
        local pos = tonumber(parts[2]) or 0
        reaper.SetEditCurPos(pos, true, true)
        execute_with_feedback("GOTO", true, string.format("Jump to %.1fs", pos))
        
    elseif cmd == "EXPORT_AUDIO" then
        -- EXPORT_AUDIO <trackIdx> <outputPath>
        local trackIdx = tonumber(parts[2]) or 0
        local outputPath = table.concat(parts, " ", 3)
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            -- Get project length
            local projEnd = reaper.GetProjectLength(0)
            
            -- Solo this track
            reaper.SetMediaTrackInfo_Value(track, "I_SOLO", 2)  -- Solo in place
            
            -- Render to file
            reaper.GetSetProjectInfo_String(0, "RENDER_FILE", outputPath, true)
            reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "", true)
            reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)  -- WAV format
            reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
            reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)  -- Stereo
            
            -- Render
            reaper.Main_OnCommand(41824, 0)  -- Render project using last settings
            
            -- Wait for render (simplified - may need improvement)
            local start_time = reaper.time_precise()
            while reaper.time_precise() - start_time < 0.5 do
                -- Brief wait
            end
            
            -- Unsolo track
            reaper.SetMediaTrackInfo_Value(track, "I_SOLO", 0)
            
            msg(string.format("🎵 Exported track %d to %s", trackIdx, outputPath))
            add_feedback(string.format("✓ Exported track %d to %s", trackIdx, outputPath))
        else
            msg(string.format("❌ Track %d not found", trackIdx))
            add_feedback(string.format("✗ Track %d not found", trackIdx))
        end
        
    else
        msg("❓ Unknown command: "..tostring(cmd))
    end
end

function check_for_commands()
    local now = reaper.time_precise()
    if now - last_check < 0.1 then return end -- Check every 100ms
    last_check = now
    
    local file = io.open(COMMAND_FILE, "r")
    if not file then return end
    
    local content = file:read("*all")
    file:close()
    
    -- Delete file immediately
    os.remove(COMMAND_FILE)
    
    -- Process each line
    for line in content:gmatch("[^\r\n]+") do
        if line:match("%S") then
            process_command(line)
        end
    end
    
    -- Write feedback after all commands processed
    write_feedback()
    -- Export state so the bridge immediately sees changes
    export_state()
end

function loop()
    check_for_commands()
    -- Periodically export state so the bridge can send live updates
    local now = reaper.time_precise()
    if now - last_state_export >= 5.0 then
        export_state()
        last_state_export = now
    end
    reaper.defer(loop)
end

msg("🤖 Reaper AI Agent Started")
msg("Watching: "..COMMAND_FILE)
loop()

