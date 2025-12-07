-- insert_audio_item.lua
-- Places an audio file as an item on a track at specified position

local track_num = tonumber(reaper.GetExtState("ai_agent", "audio_track"))
local file_path = reaper.GetExtState("ai_agent", "audio_file")
local start_pos = tonumber(reaper.GetExtState("ai_agent", "audio_start"))
local item_length = tonumber(reaper.GetExtState("ai_agent", "audio_length")) or 0  -- 0 = use file length

if not track_num or not file_path or not start_pos then
    reaper.ShowConsoleMsg("Missing audio insert parameters\n")
    reaper.SetExtState("ai_agent", "result", "error: missing params", false)
    return
end

-- Check if file exists
local f = io.open(file_path, "r")
if not f then
    reaper.ShowConsoleMsg("Audio file not found: " .. file_path .. "\n")
    reaper.SetExtState("ai_agent", "result", "error: file not found", false)
    return
end
f:close()

-- Get or create track
local track = reaper.GetTrack(0, track_num)
if not track then
    -- Create tracks up to the needed number
    local current_count = reaper.CountTracks(0)
    for i = current_count, track_num do
        reaper.InsertTrackAtIndex(i, true)
    end
    track = reaper.GetTrack(0, track_num)
end

if not track then
    reaper.SetExtState("ai_agent", "result", "error: could not create track", false)
    return
end

-- Insert media item
reaper.SetOnlyTrackSelected(track)
reaper.SetEditCurPos(start_pos, false, false)

-- Insert the audio file
local item_count_before = reaper.CountMediaItems(0)
reaper.InsertMedia(file_path, 0)  -- 0 = insert at edit cursor
local item_count_after = reaper.CountMediaItems(0)

if item_count_after > item_count_before then
    -- Get the newly created item
    local new_item = reaper.GetMediaItem(0, item_count_after - 1)
    
    if new_item then
        -- Move item to correct position (InsertMedia might place it elsewhere)
        reaper.SetMediaItemPosition(new_item, start_pos, false)
        
        -- If specific length requested, set it
        if item_length > 0 then
            reaper.SetMediaItemLength(new_item, item_length, false)
        end
        
        -- Get actual item length for return
        local actual_length = reaper.GetMediaItemInfo_Value(new_item, "D_LENGTH")
        
        reaper.SetExtState("ai_agent", "result", "ok:" .. tostring(actual_length), false)
        reaper.ShowConsoleMsg("Inserted audio: " .. file_path .. " at " .. start_pos .. "s\n")
    end
else
    reaper.SetExtState("ai_agent", "result", "error: insert failed", false)
end

reaper.UpdateArrange()

