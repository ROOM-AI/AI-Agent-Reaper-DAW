-- Reaper Cloud Agent - Full command processor for cloud
-- Uses file-based bridge to communicate with cloud
local COMMAND_FILE = [[C:\Users\moosb\AIAGENT DAW\reaper_commands.txt]]
local STATE_FILE = [[C:\Users\moosb\AIAGENT DAW\reaper_state.txt]]
local FEEDBACK_FILE = [[C:\Users\moosb\AIAGENT DAW\reaper_feedback.txt]]
local state_counter = 0

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
    -- Export FULL state (compact version for cloud)
    local stateFile = io.open(STATE_FILE, "w")
    if not stateFile then return end
    
    local numTracks = reaper.CountTracks(0)
    local playState = reaper.GetPlayState()
    local cursorPos = reaper.GetCursorPosition()
    local _, tempo = reaper.GetProjectTimeSignature2(0)
    
    stateFile:write(string.format("Tracks: %d | Playing: %s | Pos: %.2fs | Tempo: %.1f BPM\n",
        numTracks, playState == 1 and "Yes" or "No", cursorPos, tempo))
    
    for i = 0, numTracks - 1 do
        local track = reaper.GetTrack(0, i)
        local _, trackName = reaper.GetTrackName(track)
        local volume = reaper.GetMediaTrackInfo_Value(track, "D_VOL")
        local numFX = reaper.TrackFX_GetCount(track)
        
        stateFile:write(string.format("Track %d (%s): %.1fdB, %d FX\n", 
            i, trackName, 20*math.log(volume, 10), numFX))
        
        for j = 0, numFX - 1 do
            local _, fxName = reaper.TrackFX_GetFXName(track, j, "")
            stateFile:write(string.format("  [%d] %s\n", j, fxName))
        end
    end
    
    stateFile:close()
end

function process_command(line)
    local parts = {}
    for word in line:gmatch("%S+") do
        table.insert(parts, word)
    end
    
    local cmd = parts[1]
    
    -- Export state command
    if cmd == "GET_STATE" then
        export_state()
        msg("📤 State exported")
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
    
    -- FULL COMMAND SET FROM LOCAL AGENT
    if cmd == "VOL_DIP" then
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
            reaper.SetTrackSelected(track, true)
            reaper.Main_OnCommand(40406, 0)
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
            execute_with_feedback("VOL_DIP", false, "Could not create volume envelope")
        end
        
    elseif cmd == "SET_TRACK_PAN" then
        local trackIdx = tonumber(parts[2]) or 0
        local panValue = tonumber(parts[3]) or 0.0
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            reaper.SetOnlyTrackSelected(track)
            reaper.SetMediaTrackInfo_Value(track, "D_PAN", panValue)
            execute_with_feedback("SET_TRACK_PAN", true, string.format("Track %d pan: %.0f%%", trackIdx, panValue*100))
        else
            execute_with_feedback("SET_TRACK_PAN", false, string.format("Track %d not found", trackIdx))
        end
        
    elseif cmd == "ADD_FX" then
        local trackIdx = tonumber(parts[2]) or 0
        local fxName = table.concat(parts, " ", 3)
       
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            -- Check if plugin already exists
            local numFX = reaper.TrackFX_GetCount(track)
            local existingIdx = -1
            for i = 0, numFX - 1 do
                local _, existingName = reaper.TrackFX_GetFXName(track, i, "")
                local searchLower = fxName:lower()
                local existingLower = existingName:lower()
                if existingLower:find(searchLower, 1, true) then
                    existingIdx = i
                    break
                end
            end
            
            if existingIdx >= 0 then
                reaper.TrackFX_Show(track, existingIdx, 3)
                local _, existingName = reaper.TrackFX_GetFXName(track, existingIdx, "")
                msg("✅ Opened existing FX: " .. existingName)
                add_feedback("✅ Opened existing FX: " .. existingName)
            else
                -- Try to add plugin
                local namesToTry = {fxName}
                local vendors = {"FabFilter", "Waves", "Cockos", "iZotope"}
                for _, vendor in ipairs(vendors) do
                    table.insert(namesToTry, "VST3: " .. fxName .. " (" .. vendor .. ")")
                    table.insert(namesToTry, "VST: " .. fxName .. " (" .. vendor .. ")")
                end
                table.insert(namesToTry, "VST3: " .. fxName)
                table.insert(namesToTry, "VST: " .. fxName)
                
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
                    msg("✅ Added FX: " .. fxName)
                    add_feedback("✅ Added FX: " .. fxName)
                else
                    msg("❌ Could not find FX: " .. fxName)
                    add_feedback("❌ Could not find FX: " .. fxName)
                end
            end
        end
        
    elseif cmd == "SET_FX_PARAM" then
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
                msg(string.format("✅ %s > %s → %.0f%%", fxName, paramName, value*100))
                add_feedback(string.format("✅ Set param on %s", fxName))
            else
                msg(string.format("❌ Track %d only has %d FX", trackIdx, numFX))
            end
        end
        
    elseif cmd == "REMOVE_FX" then
        local trackIdx = tonumber(parts[2]) or 0
        local fxIdx = tonumber(parts[3]) or 0
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local numFX = reaper.TrackFX_GetCount(track)
            if fxIdx < numFX then
                local _, fxName = reaper.TrackFX_GetFXName(track, fxIdx, "")
                reaper.TrackFX_Delete(track, fxIdx)
                msg("✅ Removed FX: " .. fxName)
                add_feedback("✅ Removed FX: " .. fxName)
    end
end

    elseif cmd == "SELECT_TRACK" then
        local trackIdx = tonumber(parts[2]) or 0
        
        local numTracks = reaper.CountTracks(0)
        for i = 0, numTracks - 1 do
            reaper.SetTrackSelected(reaper.GetTrack(0, i), false)
        end
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            reaper.SetTrackSelected(track, true)
            local currentVol = reaper.GetMediaTrackInfo_Value(track, "D_VOL")
            reaper.SetMediaTrackInfo_Value(track, "D_VOL", currentVol)
            execute_with_feedback("SELECT_TRACK", true, string.format("Selected track %d", trackIdx))
        else
            execute_with_feedback("SELECT_TRACK", false, string.format("Track %d not found", trackIdx))
        end
        
    elseif cmd == "SET_TRACK_VOL" then
        local trackIdx = tonumber(parts[2]) or 0
        local volDB = tonumber(parts[3]) or 0
        
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local volume = 10^(volDB/20)
            reaper.SetMediaTrackInfo_Value(track, "D_VOL", volume)
            execute_with_feedback("SET_TRACK_VOL", true, string.format("Track %d → %.1fdB", trackIdx, volDB))
        else
            execute_with_feedback("SET_TRACK_VOL", false, string.format("Track %d not found", trackIdx))
        end
        
    elseif cmd == "CLEAR_AUTOMATION" then
        local trackIdx = tonumber(parts[2]) or 0
        local envName = parts[3] or "Volume"
        
        local track = reaper.GetTrack(0, trackIdx)
                if track then
            local env = reaper.GetTrackEnvelopeByName(track, envName)
            if env then
                local numPoints = reaper.CountEnvelopePoints(env)
                if numPoints > 0 then
                    reaper.DeleteEnvelopePointRange(env, 0, 999999)
                    msg(string.format("✅ Cleared %d points from %s", numPoints, envName))
                end
            end
        end
        
    elseif cmd == "FX_PARAM_AUTO" then
        local trackIdx = tonumber(parts[2]) or 0
        local fxIdx = tonumber(parts[3]) or 0
        local paramIdx = tonumber(parts[4]) or 0
        local tStart = tonumber(parts[5]) or 0
        local tEnd = tonumber(parts[6]) or 0
        local startValue = tonumber(parts[7]) or 0
        local endValue = tonumber(parts[8]) or 1
        
        local track = reaper.GetTrack(0, trackIdx)
        if not track then
            msg("❌ Track not found")
            return
        end
        
        local env = reaper.GetFXEnvelope(track, fxIdx, paramIdx, true)
        if not env then
            msg("❌ Could not get envelope")
            return
        end
        
        local _, val_before = reaper.Envelope_Evaluate(env, tStart - 0.001, 0, 0)
        local _, val_after = reaper.Envelope_Evaluate(env, tEnd + 0.001, 0, 0)
        
        reaper.InsertEnvelopePoint(env, tStart - 0.0005, val_before, 0, 0.0, true, false)
        reaper.InsertEnvelopePoint(env, tStart, startValue, 0, 0.0, true, false)
        reaper.InsertEnvelopePoint(env, tEnd, endValue, 0, 0.0, true, false)
        reaper.InsertEnvelopePoint(env, tEnd + 0.0005, val_after, 0, 0.0, true, false)
        
        reaper.Envelope_SortPoints(env)
        msg(string.format("✅ Automated param: %.2fs→%.2fs", tStart, tEnd))
        
    elseif cmd == "GOTO" then
        local pos = tonumber(parts[2]) or 0
        reaper.SetEditCurPos(pos, true, true)
        execute_with_feedback("GOTO", true, string.format("Jump to %.1fs", pos))
        
    else
        msg("❓ Unknown command: "..tostring(cmd))
    end
end

function check_for_commands()
    local file = io.open(COMMAND_FILE, "r")
    if not file then return end
    
    local content = file:read("*all")
        file:close()
    
    if not content or content == "" then return end
    
    -- Delete file immediately
    os.remove(COMMAND_FILE)
    
    -- Process each line
    for line in content:gmatch("[^\r\n]+") do
        if line:match("%S") then
            msg("📥 " .. line)
            process_command(line)
        end
    end
    
    -- Write feedback
    write_feedback()
end

function main()
    check_for_commands()
    
    -- Export state every ~2 seconds (40 defers)
    state_counter = state_counter + 1
    if state_counter >= 40 then
        export_state()
        state_counter = 0
    end
    
    reaper.defer(main)
end

msg("☁️ Reaper Cloud Agent Started")
msg("📁 Commands: "..COMMAND_FILE)
msg("📁 State: "..STATE_FILE)
msg("✅ Watching for cloud commands...")
main()
