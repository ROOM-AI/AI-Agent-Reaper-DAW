-- Dump all plugin parameters from all tracks in current project
-- Outputs to console and saves to file

reaper.ClearConsole()
reaper.ShowConsoleMsg("🔄 Starting plugin parameter dump...\n\n")

function dump_all_plugin_params()
    local output = {}
    table.insert(output, "REAPER PLUGIN PARAMETER DUMP")
    table.insert(output, "========================================\n")
    
    local num_tracks = reaper.CountTracks(0)
    
    if num_tracks == 0 then
        reaper.ShowConsoleMsg("❌ No tracks found in project\n")
        reaper.MB("No tracks found in current project!", "Plugin Parameter Dump", 0)
        return
    end
    
    reaper.ShowConsoleMsg(string.format("Found %d tracks\n", num_tracks))
    
    -- Iterate through all tracks
    for i = 0, num_tracks - 1 do
        local track = reaper.GetTrack(0, i)
        local retval, track_name = reaper.GetTrackName(track)
        
        table.insert(output, string.format("\n=== TRACK %d: %s ===", i + 1, track_name))
        
        local num_fx = reaper.TrackFX_GetCount(track)
        
        if num_fx > 0 then
            -- Iterate through all FX on this track
            for j = 0, num_fx - 1 do
                local retval, fx_name = reaper.TrackFX_GetFXName(track, j, "")
                
                table.insert(output, string.format("\n  FX %d: %s", j, fx_name))
                table.insert(output, "  " .. string.rep("-", 60))
                
                local num_params = reaper.TrackFX_GetNumParams(track, j)
                
                -- Iterate through all parameters for this FX
                for k = 0, num_params - 1 do
                    local retval, param_name = reaper.TrackFX_GetParamName(track, j, k, "")
                    local param_value = reaper.TrackFX_GetParam(track, j, k)
                    local retval, param_formatted = reaper.TrackFX_GetFormattedParamValue(track, j, k, "")
                    
                    table.insert(output, string.format("    [%3d] %-40s = %.4f (%s)", 
                                                       k, param_name, param_value, param_formatted))
                end
            end
        else
            table.insert(output, "  (No FX on this track)")
        end
        
        table.insert(output, "\n")
    end
    
    -- Convert output table to string
    local output_text = table.concat(output, "\n")
    
    -- Show in console
    reaper.ShowConsoleMsg(output_text)
    
    -- Save to file
    local project_path = reaper.GetProjectPath("")
    local file_path = project_path .. "/plugin_parameters_dump.txt"
    
    local file = io.open(file_path, "w")
    if file then
        file:write(output_text)
        file:close()
        reaper.ShowConsoleMsg("\n\n✅ Saved to: " .. file_path .. "\n")
        reaper.MB("Plugin parameters dumped successfully!\n\nSaved to:\n" .. file_path .. "\n\nCheck the console for full output.", "Success", 0)
    else
        reaper.ShowConsoleMsg("\n\n⚠️ Could not save to file\n")
        reaper.MB("Could not save file!\n\nCheck console for output.", "Error", 0)
    end
end

-- Run the dump
reaper.ShowConsoleMsg("Running dump_all_plugin_params()...\n")
dump_all_plugin_params()
reaper.ShowConsoleMsg("\n✅ Script finished\n")

