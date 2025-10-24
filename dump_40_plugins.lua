-- Comprehensive plugin parameter dump
-- Loads 40 key plugins, dumps all params, saves to file

reaper.ClearConsole()
reaper.ShowConsoleMsg("🔄 Starting comprehensive plugin parameter dump...\n\n")

-- List of 40 plugins to dump (organized by category)
local plugins_to_dump = {
    -- EQ (5)
    "VST3: Pro-Q 3 (FabFilter)",
    "CLAP: Pro-Q 3 (FabFilter)",
    "VST: SSL E-Series Channel Strip 2 (x86) (Waves)",
    "VST: PuigTec EQP1A (x86) (Waves)",
    "VST: Q10 Equalizer (x86) (Waves)",
    
    -- Compression (7)
    "VST3: Pro-C 2 (FabFilter)",
    "VST: SSLComp Stereo (x86) (Waves)",
    "VST: CLA-76 Compressor / Limiter (x86) (Waves)",
    "VST: CLA-2A Compressor / Limiter (x86) (Waves)",
    "VST: Renaissance Compressor (x86) (Waves)",
    "VST: C6 Multiband Compressor (x86) (Waves)",
    "VST3: Pro-MB (FabFilter)",
    
    -- Reverb (4)
    "VST3: ValhallaVintageVerb (Valhalla DSP, LLC)",
    "VST3: ValhallaRoom (Valhalla DSP, LLC)",
    "VST: Renaissance Reverb (x86) (Waves)",
    "VST: H-Reverb Hybrid Reverb (x86) (Waves)",
    
    -- Delay (3)
    "VST3: ValhallaDelay (Valhalla DSP, LLC)",
    "VST: H-Delay Hybrid Delay (x86) (Waves)",
    "VST: EchoBoy (x86) (Soundtoys 5)",
    
    -- Saturation/Distortion (4)
    "VST3: Saturn 2 (FabFilter)",
    "VST: Decapitator (x86) (Soundtoys 5)",
    "VST: Abbey Road Saturator (x86) (Waves)",
    "VST: Trash 2 (x86) (iZotope)",
    
    -- Dynamics/Vocal (5)
    "VST: Vocal Rider (x86) (Waves)",
    "VST: Bass Rider (x86) (Waves)",
    "VST: Renaissance DeEsser (x86) (Waves)",
    "VST: DeEsser (x86) (Waves)",
    "VST: MV2 (x86) (Waves)",
    
    -- Pitch Correction (2)
    "VST3: Auto-Tune Pro (Antares)",
    "VST3: Waves Tune Real-Time Stereo (Waves)",
    
    -- Channel Strip/SSL (2)
    "VST: SSLChannel Stereo (x86) (Waves)",
    "VST: CLA MixHub (x86) (Waves)",
    
    -- Limiting/Mastering (2)
    "VST3: Pro-L 2 (FabFilter)",
    "VST: L2 Ultramaximizer (x86) (Waves)",
    
    -- Modulation/Effects (3)
    "VST: PanMan (x86) (Soundtoys 5)",
    "VST: MetaFlanger (x86) (Waves)",
    "VST: MondoMod (x86) (Waves)",
    
    -- Utility/Specialized (3)
    "VST3: Pro-DS (FabFilter)",
    "VST: Vitamin Sonic Enhancer (x86) (Waves)",
    "VST: Renaissance Bass (x86) (Waves)"
}

local output = {}
table.insert(output, "========================================")
table.insert(output, "COMPREHENSIVE PLUGIN PARAMETER DUMP")
table.insert(output, "40 Key Plugins - Organized by Category")
table.insert(output, "========================================")
table.insert(output, "")
table.insert(output, "TABLE OF CONTENTS:")
table.insert(output, "  1. EQ (5 plugins)")
table.insert(output, "  2. COMPRESSION (7 plugins)")
table.insert(output, "  3. REVERB (4 plugins)")
table.insert(output, "  4. DELAY (3 plugins)")
table.insert(output, "  5. SATURATION/DISTORTION (4 plugins)")
table.insert(output, "  6. DYNAMICS/VOCAL (5 plugins)")
table.insert(output, "  7. PITCH CORRECTION (2 plugins)")
table.insert(output, "  8. CHANNEL STRIP/SSL (2 plugins)")
table.insert(output, "  9. LIMITING/MASTERING (2 plugins)")
table.insert(output, " 10. MODULATION/EFFECTS (3 plugins)")
table.insert(output, " 11. UTILITY/SPECIALIZED (3 plugins)")
table.insert(output, "")
table.insert(output, "Use Ctrl+F to search for plugin names")
table.insert(output, "========================================\n")

-- Create a temporary track for loading plugins
local track_idx = reaper.CountTracks(0)
reaper.InsertTrackAtIndex(track_idx, false)
local temp_track = reaper.GetTrack(0, track_idx)
reaper.GetSetMediaTrackInfo_String(temp_track, "P_NAME", "TEMP_PLUGIN_DUMP", true)

local successful = 0
local failed = 0
local failed_list = {}

-- Category boundaries for section headers
local category_starts = {1, 6, 13, 17, 20, 24, 29, 31, 33, 35, 38}
local category_names = {
    "=== CATEGORY: EQ ===",
    "=== CATEGORY: COMPRESSION ===",
    "=== CATEGORY: REVERB ===",
    "=== CATEGORY: DELAY ===",
    "=== CATEGORY: SATURATION/DISTORTION ===",
    "=== CATEGORY: DYNAMICS/VOCAL ===",
    "=== CATEGORY: PITCH CORRECTION ===",
    "=== CATEGORY: CHANNEL STRIP/SSL ===",
    "=== CATEGORY: LIMITING/MASTERING ===",
    "=== CATEGORY: MODULATION/EFFECTS ===",
    "=== CATEGORY: UTILITY/SPECIALIZED ==="
}

-- Iterate through plugin list
for i, plugin_name in ipairs(plugins_to_dump) do
    -- Check if we're starting a new category
    for cat_idx, start_idx in ipairs(category_starts) do
        if i == start_idx then
            table.insert(output, "\n\n" .. string.rep("=", 80))
            table.insert(output, category_names[cat_idx])
            table.insert(output, string.rep("=", 80) .. "\n")
            break
        end
    end
    
    reaper.ShowConsoleMsg(string.format("[%d/%d] Loading: %s\n", i, #plugins_to_dump, plugin_name))
    
    -- Try to add the plugin
    local fx_idx = reaper.TrackFX_AddByName(temp_track, plugin_name, false, -1)
    
    if fx_idx >= 0 then
        -- Plugin loaded successfully (format matches existing dump style)
        table.insert(output, string.format("\nPLUGIN [%d]: %s", i, plugin_name))
        table.insert(output, "  " .. string.rep("-", 78))
        
        local num_params = reaper.TrackFX_GetNumParams(temp_track, fx_idx)
        table.insert(output, string.format("  Total Parameters: %d", num_params))
        
        -- Dump all parameters
        for param_idx = 0, num_params - 1 do
            local retval, param_name = reaper.TrackFX_GetParamName(temp_track, fx_idx, param_idx, "")
            local param_value = reaper.TrackFX_GetParam(temp_track, fx_idx, param_idx)
            local retval, param_formatted = reaper.TrackFX_GetFormattedParamValue(temp_track, fx_idx, param_idx, "")
            
            table.insert(output, string.format("  [%4d] %-50s = %.6f  (%s)", 
                                               param_idx, param_name, param_value, param_formatted))
        end
        
        table.insert(output, "")
        successful = successful + 1
        
        -- Remove plugin for next iteration
        reaper.TrackFX_Delete(temp_track, fx_idx)
        reaper.ShowConsoleMsg(string.format("  ✓ Dumped %d parameters\n", num_params))
    else
        -- Plugin failed to load
        table.insert(output, string.format("\n❌ FAILED TO LOAD: %s", plugin_name))
        table.insert(failed_list, plugin_name)
        failed = failed + 1
        reaper.ShowConsoleMsg(string.format("  ✗ Failed to load\n"))
    end
    
    -- Brief pause to ensure clean load/unload
    reaper.time_precise() -- timestamp marker
end

-- Remove temporary track
reaper.DeleteTrack(temp_track)

-- Add summary
table.insert(output, "\n" .. string.rep("=", 80))
table.insert(output, "SUMMARY")
table.insert(output, string.rep("=", 80))
table.insert(output, string.format("Successfully dumped: %d plugins", successful))
table.insert(output, string.format("Failed to load: %d plugins", failed))

if #failed_list > 0 then
    table.insert(output, "\nFailed plugins (not installed or wrong name):")
    for _, name in ipairs(failed_list) do
        table.insert(output, "  - " .. name)
    end
end

table.insert(output, "\n" .. string.rep("=", 80))

-- Convert to string
local output_text = table.concat(output, "\n")

-- Show in console
reaper.ShowConsoleMsg("\n" .. output_text)

-- Save to file in project directory
local project_path = reaper.GetProjectPath("")
local file_path = project_path .. "/plugin_params_40_comprehensive.txt"

local file = io.open(file_path, "w")
if file then
    file:write(output_text)
    file:close()
    reaper.ShowConsoleMsg(string.format("\n\n✅ Saved to: %s\n", file_path))
    reaper.MB(string.format("Plugin parameter dump complete!\n\nSuccessful: %d\nFailed: %d\n\nSaved to:\n%s", 
                            successful, failed, file_path), "Dump Complete", 0)
else
    reaper.ShowConsoleMsg("\n\n⚠️ Could not save to file\n")
    reaper.MB("Dump complete but could not save file!\n\nCheck console for output.", "Warning", 0)
end

