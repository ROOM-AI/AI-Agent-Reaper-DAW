-- CursorDAW Cloud Demo - Bidirectional cloud sync with full command support

local COMMAND_FILE = "C:\\Users\\moosb\\AIAGENT DAW\\reaper_commands.txt"
local STATE_FILE = "C:\\Users\\moosb\\AIAGENT DAW\\reaper_state.json"
local state_counter = 0

reaper.ShowConsoleMsg("☁️ CursorDAW Cloud Demo\n")
reaper.ShowConsoleMsg("📁 Commands: " .. COMMAND_FILE .. "\n")
reaper.ShowConsoleMsg("📁 State: " .. STATE_FILE .. "\n")
reaper.ShowConsoleMsg("✅ Bidirectional cloud sync active!\n\n")

function msg(s) reaper.ShowConsoleMsg(tostring(s).."\n") end

-- Parameter conversion helpers
function db_to_normalized(target_db, min_db, max_db)
    min_db = min_db or -30
    max_db = max_db or 30
    return (target_db - min_db) / (max_db - min_db)
end

function execute_command(cmd)
    msg("📥 " .. cmd)
    
    -- Parse command into parts
    local parts = {}
    for word in cmd:gmatch("%S+") do
        table.insert(parts, word)
    end
    
    local command = parts[1]
    
    -- Parse structured commands from cloud AI
    if cmd:match("^ADD_FX:") then
        -- ADD_FX:Track 1:ReaVerb
        local track_str, fx_name = cmd:match("^ADD_FX:(.+):(.+)$")
        if track_str and fx_name then
            local track_num = track_str:match("Track (%d+)")
            if track_num then
                local track = reaper.GetTrack(0, tonumber(track_num) - 1)
                if track then
                    -- Check if FX already exists
                    local numFX = reaper.TrackFX_GetCount(track)
                    local existingIdx = -1
                    for i = 0, numFX - 1 do
                        local _, existingName = reaper.TrackFX_GetFXName(track, i, "")
                        if existingName:lower():find(fx_name:lower(), 1, true) then
                            existingIdx = i
                            break
                        end
                    end
                    
                    if existingIdx >= 0 then
                        reaper.TrackFX_Show(track, existingIdx, 3)
                        msg("✅ Opened existing " .. fx_name)
                    else
                        -- Try adding with variations
                        local namesToTry = {
                            fx_name,
                            "VST3: " .. fx_name,
                            "VST: " .. fx_name,
                            "VST3: " .. fx_name .. " (FabFilter)",
                            "VST: " .. fx_name .. " (FabFilter)"
                        }
                        
                        local fxIdx = -1
                        for _, tryName in ipairs(namesToTry) do
                            fxIdx = reaper.TrackFX_AddByName(track, tryName, false, -1)
                            if fxIdx >= 0 then break end
                        end
                        
                        if fxIdx >= 0 then
                            reaper.TrackFX_Show(track, fxIdx, 3)
                            msg("✅ Added " .. fx_name .. " to Track " .. track_num)
                        else
                            msg("⚠️ Could not find FX: " .. fx_name)
                        end
                    end
                else
                    msg("⚠️ Track " .. track_num .. " not found")
                end
            end
        end
        
    elseif cmd:match("^SET_FX_PARAM:") then
        -- SET_FX_PARAM:Track 1:FX 0:Param 2:0.5
        local parts = {}
        for part in cmd:gmatch("[^:]+") do
            table.insert(parts, part)
        end
        -- parts[1] = "SET_FX_PARAM"
        -- parts[2] = "Track 1"
        -- parts[3] = "FX 0"
        -- parts[4] = "Param 2"
        -- parts[5] = "0.5"
        
        local track_num = parts[2] and parts[2]:match("Track (%d+)")
        local fx_idx = parts[3] and parts[3]:match("FX (%d+)")
        local param_idx = parts[4] and parts[4]:match("Param (%d+)")
        local value = tonumber(parts[5])
        
        if track_num and fx_idx and param_idx and value then
            local track = reaper.GetTrack(0, tonumber(track_num) - 1)
            if track then
                reaper.TrackFX_SetParam(track, tonumber(fx_idx), tonumber(param_idx), value)
                local _, fxName = reaper.TrackFX_GetFXName(track, tonumber(fx_idx), "")
                local _, paramName = reaper.TrackFX_GetParamName(track, tonumber(fx_idx), tonumber(param_idx), "")
                msg(string.format("✅ %s > %s → %.0f%%", fxName, paramName, value*100))
            end
        end
        
    elseif cmd:match("^AI_MESSAGE:") then
        local message = cmd:match("^AI_MESSAGE:(.+)$")
        msg("💬 AI: " .. message)
        
    elseif command == "SELECT_TRACK" then
        local trackIdx = tonumber(parts[2]) or 0
        local numTracks = reaper.CountTracks(0)
        for i = 0, numTracks - 1 do
            reaper.SetTrackSelected(reaper.GetTrack(0, i), false)
        end
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            reaper.SetTrackSelected(track, true)
            msg("✅ Selected track " .. trackIdx)
        end
        
    elseif command == "SET_TRACK_VOL" then
        local trackIdx = tonumber(parts[2]) or 0
        local volDB = tonumber(parts[3]) or 0
        local track = reaper.GetTrack(0, trackIdx)
        if track then
            local volume = 10^(volDB/20)
            reaper.SetMediaTrackInfo_Value(track, "D_VOL", volume)
            msg(string.format("✅ Track %d → %.1fdB", trackIdx, volDB))
        end
        
    else
        -- Fallback: simple keyword detection
        local m = cmd:lower()
        if m:find("play") then
            reaper.Main_OnCommand(1007, 0)
            msg("▶️ Playing")
        elseif m:find("stop") then
            reaper.Main_OnCommand(1016, 0)
            msg("⏹️ Stopped")
        elseif m:find("record") then
            reaper.Main_OnCommand(1013, 0)
            msg("🔴 Recording")
        elseif m:find("add_track") or m:find("add track") then
            reaper.Main_OnCommand(40001, 0)
            msg("➕ Added track")
        else
            msg("⚠️ Unknown command")
        end
    end
end

function send_state()
    -- Build detailed track list with FX
    local tracks_json = ""
    local track_count = reaper.CountTracks(0)
    
    for i = 0, track_count - 1 do
        local track = reaper.GetTrack(0, i)
        local _, track_name = reaper.GetTrackName(track)
        local volume = reaper.GetMediaTrackInfo_Value(track, "D_VOL")
        local pan = reaper.GetMediaTrackInfo_Value(track, "D_PAN")
        local fx_count = reaper.TrackFX_GetCount(track)
        local selected = reaper.IsTrackSelected(track) and "true" or "false"
        
        -- Get FX list with parameters
        local fx_list = ""
        for j = 0, fx_count - 1 do
            local _, fx_name = reaper.TrackFX_GetFXName(track, j, "")
            local enabled = reaper.TrackFX_GetEnabled(track, j) and "true" or "false"
            
            if j > 0 then fx_list = fx_list .. "," end
            fx_list = fx_list .. string.format('{"name":"%s","enabled":%s}', fx_name, enabled)
        end
        
        if i > 0 then tracks_json = tracks_json .. "," end
        tracks_json = tracks_json .. string.format(
            '{"num":%d,"name":"%s","volume_db":%.1f,"pan":%.2f,"fx_count":%d,"fx":[%s],"selected":%s}',
            i + 1,
            track_name:gsub('"', '\\"'),
            20*math.log(volume, 10),
            pan,
            fx_count,
            fx_list,
            selected
        )
    end
    
    -- Build complete state JSON
    local play_state = reaper.GetPlayState()
    local state = string.format(
        '{"tracks":%d,"position":%.2f,"playing":%s,"timestamp":%d,"track_list":[%s]}',
        track_count,
        reaper.GetCursorPosition(),
        (play_state & 1) == 1 and "true" or "false",
        os.time(),
        tracks_json
    )
    
    -- Write to file for bridge to pick up
    local f = io.open(STATE_FILE, "w")
    if f then
        f:write(state)
        f:close()
    end
end

function main()
    -- Check for incoming commands
    local f = io.open(COMMAND_FILE, "r")
    if f then
        local commands = f:read("*all")
        f:close()
        
        if commands and commands ~= "" then
            -- Clear file after reading
            local c = io.open(COMMAND_FILE, "w")
            if c then c:close() end
            
            -- Process each command line
            for cmd in commands:gmatch("[^\n]+") do
                if cmd and cmd:match("%S") then
                    execute_command(cmd)
                end
            end
        end
    end
    
    -- Send state every ~2 seconds (every 40 defers at ~50ms each)
    state_counter = state_counter + 1
    if state_counter >= 40 then
        send_state()
        state_counter = 0
    end
    
    reaper.defer(main)
end

main()
