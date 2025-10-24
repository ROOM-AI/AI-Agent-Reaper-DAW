# Algorithm Refinements Applied - Reference-Based Mixing

## Summary

Applied **enhanced algorithms from Grok AI** to improve reference-based audio matching. The refinements focus on perceptual accuracy, musical safeguards, and smarter convergence strategies.

---

## What Was Refined

### 1. Feature Extraction (lines 937-1095)

**OLD:** Basic librosa features with no perceptual weighting  
**NEW:** Enhanced with perceptual accuracy

**Improvements:**
- ✅ **A-weighted power spectrum** - Uses `librosa.perceptual_weighting()` for human hearing sensitivity
- ✅ **40 mel bands** instead of simple frequency bins - Better frequency resolution
- ✅ **THD calculation** - Total Harmonic Distortion with FFT analysis
- ✅ **Odd/even harmonic ratio** - Distinguishes tube (odd) vs tape (even) saturation
- ✅ **Improved RT60 estimation** - Proper reverb decay time from energy envelope (-60dB point)
- ✅ **Pre-delay detection** - Reverb pre-delay in milliseconds from autocorrelation
- ✅ **Wet/dry ratio** - Estimated from tail energy vs RMS
- ✅ **Reverb type classification** - Hall/Room/Plate based on decay characteristics

**Code highlights:**
```python
# A-weighted spectrum (perceptual)
S_weighted = librosa.perceptual_weighting(S**2, freqs, ref=1.0)
mel_spec = librosa.feature.melspectrogram(S=S_weighted, sr=sr, n_mels=40)

# THD from FFT harmonics
Y = fft(y_mono)
harmonics = [2nd, 3rd, ..., 9th harmonic magnitudes]
thd = sqrt(sum(h^2)) / fundamental_magnitude

# RT60 from energy decay
tail_db = librosa.amplitude_to_db(tail_energy) - max_energy_db
rt60_idx = first index where tail_db <= -60dB
rt60_seconds = rt60_idx * hop_length / sample_rate
```

---

### 2. Similarity Calculation (lines 1097-1159)

**OLD:** Simple distance metrics, all frequencies weighted equally  
**NEW:** Perceptually-weighted with processing penalty

**Improvements:**
- ✅ **Presence region emphasis** (2-5kHz gets 1.5x weight) - Humans most sensitive here
- ✅ **Processing penalty parameter** - Penalizes over-processing to preserve musicality
- ✅ **THD-aware harmonic matching** - Uses actual distortion analysis, not just HP ratio
- ✅ **Better clipping** - Results clamped to 0-100% range properly

**Code highlights:**
```python
# Extra weight for presence (mel bands 10-20 ≈ 2-5kHz)
presence_ref = reference_features['mel_bands'][10:20]
presence_cur = current_features['mel_bands'][10:20]
presence_diff = cosine(presence_ref, presence_cur) * 1.5

spec_diff = 0.7 * mel_diff + 0.3 * (presence_diff / 1.5)

# Apply processing penalty
final_sim = (total_sim - processing_penalty) * 100
return np.clip(final_sim, 0, 100)
```

**Perceptual weighting explained:**
- Spectral: 40% (most important - timbre/tone)
- Dynamics: 20% (compression/punch)
- Spatial: 15% (stereo width)
- Harmonic: 15% (saturation/warmth) - now includes THD
- Temporal: 10% (attack/transients)

---

### 3. Processing Penalty System (lines 1161-1190)

**NEW FEATURE:** Prevents unmusical over-processing

**How it works:**
```python
# Penalties for excessive processing:
- EQ total > 72dB (±12dB per band × 6 bands)
- Compression ratio > 10:1
- Saturation drive > 50% (≈ 20% THD)

# Each over-limit adds 5% penalty to similarity
penalty = 0.05 * (eq_penalty + comp_penalty + sat_penalty)
```

**Why this matters:**
- Prevents "+50dB at 10kHz" nonsense
- Keeps compression ratios reasonable
- Limits saturation to preserve source character
- **The system will prefer "75% similar but musical" over "90% similar but destroyed"**

---

### 4. Saturation Character Analysis (lines 1192-1207)

**NEW FEATURE:** Identifies saturation type from harmonics

**Algorithm:**
```python
if THD < 1%:
    → No saturation
elif odd_harmonics/even_harmonics > 2:
    → Tube (if THD < 10%) or Distortion (if THD > 10%)
else:
    → Tape saturation (even harmonics dominant)
```

**Output:**
```json
{
    "type": "tube",  // or "tape", "distortion", "none"
    "amount": 0.08   // 8% THD
}
```

**Why this matters:**
- Recommends correct saturation plugin character
- "Add tube saturation" vs "Add tape warmth" - different sonic results
- Based on actual harmonic content, not guesswork

---

### 5. Action Generation with Priority Queue (lines 1209-1304)

**OLD:** All actions returned in arbitrary order  
**NEW:** Priority queue with constraints

**Improvements:**
- ✅ **Priority queue** - Fixes biggest differences first
- ✅ **Hard constraints:**
  - EQ: ±6dB max per band (was unlimited)
  - Compression: 10:1 max ratio (was unlimited)
  - Saturation: 50% max drive / 20% THD (was unlimited)
- ✅ **Step size parameter** - Enables learning rate decay
- ✅ **Softer thresholds:**
  - EQ: triggers at 0.5dB diff (was 3dB)
  - Compression: triggers at 2dB DR diff (was 5dB)
  - Saturation: triggers at 2% THD diff (new)
  - Reverb: triggers at 300ms diff (was 500ms)
- ✅ **Character-aware recommendations:**
  - "Add hall reverb (RT60: 3.2s)" vs "Add plate reverb"
  - "Add tube saturation (THD: 0.08)" vs "Add tape saturation"

**Code highlights:**
```python
from queue import PriorityQueue
priorities = PriorityQueue()

# Add actions with priority (negative for max-heap)
for i, diff in enumerate(band_diffs):
    if abs(diff) > 0.5:
        gain = np.clip(step_size * diff / 2, -6, 6)  # CONSTRAINED
        priority = abs(diff)
        priorities.put((-priority, action_dict))

# Extract in priority order
actions = []
while not priorities.empty():
    _, action = priorities.get()
    actions.append(action)
```

**Priority example:**
1. Compression (10dB DR diff - huge priority)
2. EQ band 15 (6dB diff at 3kHz)
3. EQ band 5 (4dB diff at 200Hz)
4. Saturation (3% THD diff)
5. Reverb (0.8s decay diff)
6. Stereo width (0.2 correlation diff)

---

## Comparison: Before vs After

### Feature Extraction
| Feature | Before | After |
|---------|--------|-------|
| Frequency bands | 6 basic | 40 perceptually-weighted mel bands |
| Harmonic analysis | HP ratio only | THD + odd/even ratio |
| Reverb estimation | Autocorrelation lag | RT60 (-60dB decay) + pre-delay + wet/dry |
| Reverb type | None | Hall/Room/Plate classification |
| Perceptual weighting | None | A-weighting for human sensitivity |

### Similarity Scoring
| Aspect | Before | After |
|--------|--------|-------|
| Presence region | Equal weight | 1.5x emphasis (2-5kHz) |
| Over-processing | Ignored | Penalized (5% per limit exceeded) |
| THD matching | Not included | Included in harmonic similarity |
| Range | Sometimes >100% or <0% | Properly clamped 0-100% |

### Action Generation
| Aspect | Before | After |
|--------|--------|-------|
| Priority | Random order | Priority queue (biggest issues first) |
| EQ limits | None | ±6dB per band, 72dB total |
| Compression limits | None | 10:1 max ratio |
| Saturation limits | None | 50% max drive (20% THD) |
| Thresholds | Hard (3dB) | Soft (0.5dB) - more sensitive |
| Character | Generic | Type-aware (tube/tape, hall/room) |
| Step size | Fixed | Variable (enables decay) |

---

## What This Enables

### 1. Better Perceptual Matching
- Reference and target might be "60% similar" mathematically but "90% similar" perceptually
- A-weighting accounts for human hearing (less sensitive to sub-bass, more to presence)
- Presence boost has bigger impact on similarity than sub-bass boost

### 2. Musicality Preservation
- Won't apply +20dB at 10kHz just because math says so
- Processing penalty keeps results sounding natural
- Constraints prevent over-compression, over-EQ, over-saturation

### 3. Smarter Convergence
- Fixes biggest differences first (priority queue)
- Takes smaller steps (step_size parameter → learning rate decay)
- More sensitive thresholds catch subtle differences

### 4. Character-Aware Processing
- "Your track needs tube saturation" vs generic "add drive"
- "Reference has hall reverb" vs generic "add reverb"
- Recommends specific plugin characteristics based on analysis

---

## Next Steps for Full Implementation

### 1. Iterative Convergence with Backtracking
**Still TODO:** The match_to_reference() function needs:
```python
def match_with_convergence(ref, current, max_iter=15):
    step_size = 1.0
    prev_similarity = calculate_similarity(ref, current)
    
    for iteration in range(max_iter):
        actions = calculate_mixing_actions(ref, current, step_size)
        
        # Apply top priority action
        apply_action(actions[0])
        
        # Re-analyze
        new_sim = calculate_similarity(ref, current, 
                                      calculate_processing_penalty(actions))
        
        if new_sim < prev_similarity:
            # BACKTRACK - undo last action
            undo_action(actions[0])
            step_size *= 0.5  # Reduce step size
        else:
            prev_similarity = new_sim
        
        step_size *= 0.9  # Learning rate decay
        
        if prev_similarity >= 85:
            break
    
    return prev_similarity
```

### 2. Action-to-Command Translation
**Still TODO:** Convert action dicts to actual Reaper commands:
```python
def action_to_reaper_commands(action, track_idx):
    if action['type'] == 'eq':
        commands = [f"ADD_FX {track_idx} FabFilter Pro-Q 3"]
        # Map mel band to Pro-Q frequency
        freq_hz = mel_to_hz(action['band'])
        # Find Pro-Q param index for that frequency
        # Generate SET_FX_PARAM commands
    elif action['type'] == 'compression':
        # Map ratio to ReaComp params
    # ... etc
```

### 3. User Command Integration
Add to main agent:
```python
if "sound like" in user_input:
    # "make track 2 sound like reference.wav"
    result = match_to_reference(track_idx=2, 
                                reference_audio_path="reference.wav")
```

---

## Dependencies

All refinements use existing dependencies:
```python
import numpy as np
import librosa
import soundfile as sf
from scipy.spatial.distance import cosine, euclidean
from scipy.fft import fft
from queue import PriorityQueue
```

No new packages required!

---

## Testing the Refinements

```python
# Test feature extraction
from ai_agent_reaper_final import extract_detailed_features

features = extract_detailed_features("my_track.wav")
print(f"THD: {features['thd']:.3f}")
print(f"Odd/Even ratio: {features['odd_even_ratio']:.2f}")
print(f"RT60: {features['rt60']:.2f}s")
print(f"Reverb type: {features['reverb_type']}")

# Test similarity with penalty
from ai_agent_reaper_final import (extract_detailed_features, 
                                    calculate_similarity,
                                    calculate_mixing_actions,
                                    calculate_processing_penalty)

ref = extract_detailed_features("reference.wav")
target = extract_detailed_features("my_track.wav")

actions = calculate_mixing_actions(ref, target, step_size=1.0)
penalty = calculate_processing_penalty(actions)
similarity = calculate_similarity(ref, target, processing_penalty=penalty)

print(f"Similarity: {similarity:.1f}%")
print(f"Processing penalty: {penalty:.3f}")
print(f"Actions ({len(actions)}):")
for action in actions:
    print(f"  - {action['type']}: {action['reason']}")
```

---

## Summary of Changes

**Files modified:** `ai_agent_reaper_final.py`

**Lines changed:**
- Lines 937-1095: Enhanced feature extraction (+158 lines)
- Lines 1097-1159: Perceptual similarity (+7 lines modified)
- Lines 1161-1190: Processing penalty system (+30 lines NEW)
- Lines 1192-1207: Saturation character analysis (+16 lines NEW)
- Lines 1209-1304: Priority queue action generation (+95 lines modified)

**Total:** ~300 lines refined/added

**Impact:**
- More accurate perceptual matching
- Musical safeguards prevent over-processing
- Smarter action prioritization
- Character-aware recommendations
- Better convergence potential

---

🎉 **Algorithm refinement complete!** The reference matching system is now significantly more sophisticated and musically intelligent.

