# Reaper AI Agent - Available Commands

## Discovery Commands

### LIST_PLUGINS
Lists all Reaper stock plugins (ReaComp, ReaEQ, ReaVerb, etc.).
```
LIST_PLUGINS
```
Results written to `reaper_state.txt`

**Note**: Only shows Reaper/Cockos/JS plugins for reliable demos.

### SEARCH_PLUGIN <search_term>
Search for Reaper stock plugins by name.
```
SEARCH_PLUGIN Comp
SEARCH_PLUGIN EQ
SEARCH_PLUGIN Reverb
```
Results written to `reaper_state.txt`

**Common Reaper Plugins:**
- ReaComp (Compressor)
- ReaEQ (Equalizer)
- ReaVerb (Reverb)
- ReaGate (Gate)
- ReaDelay (Delay)
- ReaPitch (Pitch shifter)

### GET_STATE
Export full project state (tracks, FX, parameters, automation).
```
GET_STATE
```
Results written to `reaper_state.txt`

## Transport Commands (Action IDs)

```
40044  - Play/Pause
40073  - Stop
1007   - Record
1013   - Rewind
1008   - Fast Forward
```

## Track Commands

### SELECT_TRACK <track_number>
Select a track (1-based numbering).
```
SELECT_TRACK 1
SELECT_TRACK 3
```

### SET_TRACK_VOL <track_index> <volume_dB>
Set track volume in dB (track_index is 0-based).
```
SET_TRACK_VOL 0 -6.0
SET_TRACK_VOL 1 0.0
SET_TRACK_VOL 2 -12.0
```

### SET_TRACK_PAN <track_index> <pan_value>
Set track pan (-1.0 = full left, 0.0 = center, 1.0 = full right).
```
SET_TRACK_PAN 0 -0.5
SET_TRACK_PAN 1 0.0
SET_TRACK_PAN 2 1.0
```

## FX Commands

### ADD_FX <track_index> <fx_name>
Add an FX plugin to a track. The script will search for exact name, then try VST/VST3 wrappers.
```
ADD_FX 0 Pro-Q 3
ADD_FX 1 ReaComp
ADD_FX 2 ReaEQ
```

**Tip**: Use `SEARCH_PLUGIN` first to find the exact plugin name!

### SET_FX_PARAM <track_index> <fx_index> <param_index> <value_0-1>
Set an FX parameter value (0.0 to 1.0 range).
```
SET_FX_PARAM 0 0 5 0.75
SET_FX_PARAM 1 0 10 0.5
```

**Tip**: Use `GET_STATE` to see all FX parameters and their indices!

### REMOVE_FX <track_index> <fx_index>
Remove an FX from a track.
```
REMOVE_FX 0 0
REMOVE_FX 1 2
```

## Automation Commands

### VOL_DIP <track_index> <start_time> <end_time> <value_0-1>
Create volume automation dip (for ducking/sidechain effects).
```
VOL_DIP 0 16.0 32.0 0.5
VOL_DIP 1 8.0 12.0 0.25
```

### FX_PARAM_AUTO <track_index> <fx_index> <param_index> <start_time> <end_time> <start_value> <end_value>
Automate an FX parameter over time.
```
FX_PARAM_AUTO 0 0 5 0.0 16.0 0.0 1.0
FX_PARAM_AUTO 1 0 10 8.0 24.0 0.5 0.2
```

### CLEAR_AUTOMATION <track_index> <envelope_name>
Clear automation from an envelope.
```
CLEAR_AUTOMATION 0 Volume
CLEAR_AUTOMATION 1 Pan
```

## Playback Commands

### GOTO <seconds>
Jump to a specific time position.
```
GOTO 0.0
GOTO 32.5
GOTO 120.0
```

## Example Workflow

1. **Discover what's available:**
```
GET_STATE
SEARCH_PLUGIN Pro-Q
```

2. **Add and configure FX:**
```
SELECT_TRACK 1
ADD_FX 0 Pro-Q 3
GET_STATE
SET_FX_PARAM 0 0 10 0.75
```

3. **Create automation:**
```
FX_PARAM_AUTO 0 0 10 0.0 16.0 0.0 1.0
GET_STATE
```

## Tips for AI Agents

1. **Always use SEARCH_PLUGIN before ADD_FX** to find exact plugin names
2. **Use GET_STATE frequently** to see current parameters and track info
3. **Track indices are 0-based** (Track 1 = index 0)
4. **FX indices are 0-based** (First FX = index 0)
5. **Check feedback** - every command reports success/failure
6. **Parameter values are 0.0-1.0** - use GET_STATE to see formatted values

