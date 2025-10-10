# Grok's improved version - paste Grok's complete code here
# This is the one with retry loop + better error handling + loads multiple action files

0|Action: Arm next action
1|Action: Disarm action
2|Action: Modify MIDI CC/mousewheel: +10%
3|Action: Modify MIDI CC/mousewheel: -10%
4|Action: Modify MIDI CC/mousewheel: 0.5x
5|Action: Modify MIDI CC/mousewheel: 2x
6|Action: Modify MIDI CC/mousewheel: Negative
7|Action: Momentarily send next action to next project tab 1
8|Action: Momentarily send next action to next project tab 2
9|Action: Momentarily send next action to next project tab 3
10|Action: Momentarily send next action to next project tab 4
11|Action: Momentarily send next action to next project tab 5
12|Action: Momentarily send next action to previous project tab 1
13|Action: Momentarily send next action to previous project tab 2
14|Action: Momentarily send next action to previous project tab 3
15|Action: Momentarily send next action to previous project tab 4
16|Action: Momentarily send next action to previous project tab 5
17|Action: Momentarily send next action to previously active project tab
18|Action: Momentarily send next action to project tab 1
19|Action: Momentarily send next action to project tab 10
20|Action: Momentarily send next action to project tab 2
21|Action: Momentarily send next action to project tab 3
22|Action: Momentarily send next action to project tab 4
23|Action: Momentarily send next action to project tab 5
24|Action: Momentarily send next action to project tab 6
25|Action: Momentarily send next action to project tab 7
26|Action: Momentarily send next action to project tab 8
27|Action: Momentarily send next action to project tab 9
28|Action: Momentarily send next action to project tab N
29|Action: Momentarily send next action to project tab N-1
30|Action: Momentarily send next action to project tab N-2
31|Action: Momentarily send next action to project tab N-3
32|Action: Momentarily send next action to project tab N-4
33|Action: Momentarily send next action to project tab N-5
34|Action: Momentarily send next action to project tab N-6
35|Action: Momentarily send next action to project tab N-7
36|Action: Momentarily send next action to project tab N-8
37|Action: Momentarily send next action to project tab N-9
38|Action: Prompt to continue (only valid within custom actions)
39|Action: Prompt to go to action loop start (only valid within custom actions)
40|Action: Repeat the action prior to the most recent action
41|Action: Repeat the most recent action
42|Action: Set action loop start (only valid within custom actions)
43|Action: Skip next action if CC parameter !=0/mid
44|Action: Skip next action if CC parameter <0/mid
45|Action: Skip next action if CC parameter <=0/mid
46|Action: Skip next action if CC parameter ==0/mid
47|Action: Skip next action if CC parameter >0/mid
48|Action: Skip next action if CC parameter >=0/mid
49|Action: Skip next action, set CC parameter to relative +1 if action armed, 0 otherwise
50|Action: Skip next action, set CC parameter to relative +1 if action toggle state enabled, -1 if disabled, 0 if toggle state unavailable.
51|Action: Toggle arm of next action
52|Action: Wait 0.1 seconds before next action
53|Action: Wait 0.5 seconds before next action
54|Action: Wait 1 second before next action
55|Action: Wait 10 seconds before next action
56|Action: Wait 5 seconds before next action
57|Activate next MIDI item
58|Activate next MIDI track
59|Activate next visible MIDI item
60|Activate previous MIDI item
61|Activate previous MIDI track
62|Activate previous visible MIDI item
63|Add CC/velocity lane preset...
64|Add next note to selection
65|Add next note with higher pitch to selection
66|Add next note with lower pitch to selection
67|Add note nearest to the edit cursor to selection
68|Add previous note to selection
69|Add user metadata column
70|Adjust entire tempo envelope...
71|Adjust last touched FX parameter (MIDI CC/OSC only)
72|Adjust solo in front dim (MIDI CC/mousewheel only)
73|Adjust track FX parameter 01 (MIDI CC/OSC only)
74|Adjust track FX parameter 02 (MIDI CC/OSC only)
75|Adjust track FX parameter 03 (MIDI CC/OSC only)
76|Adjust track FX parameter 04 (MIDI CC/OSC only)
77|Adjust track FX parameter 05 (MIDI CC/OSC only)
78|Adjust track FX parameter 06 (MIDI CC/OSC only)
79|Adjust track FX parameter 07 (MIDI CC/OSC only)
80|Adjust track FX parameter 08 (MIDI CC/OSC only)
81|Adjust track FX parameter 09 (MIDI CC/OSC only)
82|Adjust track FX parameter 10 (MIDI CC/OSC only)
83|Adjust track FX parameter 11 (MIDI CC/OSC only)
84|Adjust track FX parameter 12 (MIDI CC/OSC only)
85|Adjust track FX parameter 13 (MIDI CC/OSC only)
86|Adjust track FX parameter 14 (MIDI CC/OSC only)
87|Adjust track FX parameter 15 (MIDI CC/OSC only)
88|Adjust track FX parameter 16 (MIDI CC/OSC only)
89|Adjust track send 1 pan (MIDI CC/OSC only)
90|Adjust track send 1 volume (MIDI CC/OSC only)
91|Adjust track send 2 pan (MIDI CC/OSC only)
92|Adjust track send 2 volume (MIDI CC/OSC only)
93|Adjust track send 3 pan (MIDI CC/OSC only)
94|Adjust track send 3 volume (MIDI CC/OSC only)
95|Adjust track send 4 pan (MIDI CC/OSC only)
96|Adjust track send 4 volume (MIDI CC/OSC only)
97|Adjust track send 5 pan (MIDI CC/OSC only)
98|Adjust track send 5 volume (MIDI CC/OSC only)
99|Adjust track send 6 pan (MIDI CC/OSC only)
100|Adjust track send 6 volume (MIDI CC/OSC only)
101|Adjust track send 7 pan (MIDI CC/OSC only)
102|Adjust track send 7 volume (MIDI CC/OSC only)
103|Adjust track send 8 pan (MIDI CC/OSC only)
104|Adjust track send 8 volume (MIDI CC/OSC only)
105|Align lyric events with notes
106|Apply LFO to last touched CC lane...
107|Apply normalized volume to inserted media item
108|Apply preview pitch/rate to inserted media item
109|Apply preview volume to inserted media item
110|Assign MIDI channel 1 when inserting into sampler, incrementing if new track
111|Assign MIDI channel 10 when inserting into sampler, incrementing if new track
112|Assign MIDI channel 11 when inserting into sampler, incrementing if new track
113|Assign MIDI channel 12 when inserting into sampler, incrementing if new track
114|Assign MIDI channel 13 when inserting into sampler, incrementing if new track
115|Assign MIDI channel 14 when inserting into sampler, incrementing if new track
116|Assign MIDI channel 15 when inserting into sampler, incrementing if new track
117|Assign MIDI channel 16 when inserting into sampler, incrementing if new track
118|Assign MIDI channel 2 when inserting into sampler, incrementing if new track
119|Assign MIDI channel 3 when inserting into sampler, incrementing if new track
120|Assign MIDI channel 4 when inserting into sampler, incrementing if new track
121|Assign MIDI channel 5 when inserting into sampler, incrementing if new track
122|Assign MIDI channel 6 when inserting into sampler, incrementing if new track
123|Assign MIDI channel 7 when inserting into sampler, incrementing if new track
124|Assign MIDI channel 8 when inserting into sampler, incrementing if new track
125|Assign MIDI channel 9 when inserting into sampler, incrementing if new track
126|Assign MIDI note when inserting into sampler, starting at note and incrementing if new track...
127|Assign detected pitch when inserting into sampler
128|Audio device configuration...
129|Auto-save default CC lanes on window close
130|Auto-save default configuration when changing options
131|Auto-stop preview when dragging media
132|Auto-stop preview when inserting media
133|Automatically expand shortcuts while browsing file list
134|Automation lane: Decrease active fader a little bit
135|Automation lane: Decrease active fader a tiny bit
136|Automation lane: Increase active fader a little bit
137|Automation lane: Increase active fader a tiny bit
138|Automation lane: Set active fader (MIDI CC/OSC only)
139|Automation: Clear all saved track envelope latches
140|Automation: Clear all track envelope latches
141|Automation: Clear saved track envelope latches
142|Automation: Clear track envelope latches
143|Automation: Restore all saved track envelope latches
144|Automation: Restore saved track envelope latches
145|Automation: Save and clear all track envelope latches
146|Automation: Save and clear all track envelope latches if any, otherwise restore saved latches
147|Automation: Save and clear track envelope latches
148|Automation: Save and clear track envelope latches if any, otherwise restore saved latches
149|Automation: Set all tracks automation mode to latch
150|Automation: Set all tracks automation mode to latch preview
151|Automation: Set all tracks automation mode to read
152|Automation: Set all tracks automation mode to touch
153|Automation: Set all tracks automation mode to trim/read
154|Automation: Set all tracks automation mode to write
155|Automation: Set track automation mode to latch
156|Automation: Set track automation mode to latch preview
157|Automation: Set track automation mode to read
158|Automation: Set track automation mode to touch
159|Automation: Set track automation mode to trim/read
160|Automation: Set track automation mode to write
161|Automation: Toggle track between touch and trim/read modes
162|Automation: Unarm all envelopes
163|Automation: Write current values for actively-writing envelopes from cursor to end of project
164|Automation: Write current values for actively-writing envelopes from cursor to first touch position
165|Automation: Write current values for actively-writing envelopes from cursor to start of project
166|Automation: Write current values for actively-writing envelopes to entire envelope
167|Automation: Write current values for actively-writing envelopes to time selection
168|Automation: Write current values for all writing envelopes from cursor to end of project
169|Automation: Write current values for all writing envelopes from cursor to start of project
170|Automation: Write current values for all writing envelopes to time selection
171|Autoplay: Off
172|Autoplay: On
173|Autoplay: Toggle on/off
174|Big clock plus: Extended display (recording pass, markers, etc)...
175|Browser: Browse selected folder, or insert selected media file
176|Browser: Display all files/supported media only
177|Browser: Go to next folder in history
178|Browser: Go to next shortcut in list
179|Browser: Go to parent folder
180|Browser: Go to previous folder in history
181|Browser: Go to previous shortcut in list
182|Browser: Go to shortcut 1
183|Browser: Go to shortcut 10
184|Browser: Go to shortcut 11
185|Browser: Go to shortcut 12
186|Browser: Go to shortcut 13
187|Browser: Go to shortcut 14
188|Browser: Go to shortcut 15
189|Browser: Go to shortcut 16
190|Browser: Go to shortcut 17
191|Browser: Go to shortcut 18
192|Browser: Go to shortcut 19
193|Browser: Go to shortcut 2
194|Browser: Go to shortcut 20
195|Browser: Go to shortcut 3
196|Browser: Go to shortcut 4
197|Browser: Go to shortcut 5
198|Browser: Go to shortcut 6
199|Browser: Go to shortcut 7
200|Browser: Go to shortcut 8
201|Browser: Go to shortcut 9
202|Browser: Refresh
203|Browser: Search (focuses search field)
204|Browser: Select all media files
205|Browser: Select next file in directory
206|Browser: Select previous file in directory
207|Browser: Show full path in databases and searches
208|Browser: Show leading path in databases and searches
209|CC lane: Reset zoom/scroll
210|CC lane: Scroll down
211|CC lane: Scroll up
212|CC lane: Zoom in
213|CC lane: Zoom out
214|CC: Next CC lane
215|CC: Previous CC lane
216|CC: Set CC lane to 00/32 Bank Select 14-bit
217|CC: Set CC lane to 000 Bank Select MSB
218|CC: Set CC lane to 001 Mod Wheel MSB
219|CC: Set CC lane to 002 Breath MSB
220|CC: Set CC lane to 003
221|CC: Set CC lane to 004 Foot Pedal MSB
222|CC: Set CC lane to 005 Portamento MSB
223|CC: Set CC lane to 006 Data Entry MSB
224|CC: Set CC lane to 007 Volume MSB
225|CC: Set CC lane to 008 Balance MSB
226|CC: Set CC lane to 009
227|CC: Set CC lane to 01/33 Mod Wheel 14-bit
228|CC: Set CC lane to 010 Pan Position MSB
229|CC: Set CC lane to 011 Expression MSB
230|CC: Set CC lane to 012 Control 1 MSB
231|CC: Set CC lane to 013 Control 2 MSB
232|CC: Set CC lane to 014
233|CC: Set CC lane to 015
234|CC: Set CC lane to 016 GP Slider 1
235|CC: Set CC lane to 017 GP Slider 2
236|CC: Set CC lane to 018 GP Slider 3
237|CC: Set CC lane to 019 GP Slider 4
238|CC: Set CC lane to 02/34 Breath 14-bit
239|CC: Set CC lane to 020
240|CC: Set CC lane to 021
241|CC: Set CC lane to 022
242|CC: Set CC lane to 023
243|CC: Set CC lane to 024
244|CC: Set CC lane to 025
245|CC: Set CC lane to 026
246|CC: Set CC lane to 027
247|CC: Set CC lane to 028
248|CC: Set CC lane to 029
249|CC: Set CC lane to 03/35 14-bit
250|CC: Set CC lane to 030
251|CC: Set CC lane to 031
252|CC: Set CC lane to 032 Bank Select LSB
253|CC: Set CC lane to 033 Mod Wheel LSB
254|CC: Set CC lane to 034 Breath LSB
255|CC: Set CC lane to 035
256|CC: Set CC lane to 036 Foot Pedal LSB
257|CC: Set CC lane to 037 Portamento LSB
258|CC: Set CC lane to 038 Data Entry LSB
259|CC: Set CC lane to 039 Volume LSB
260|CC: Set CC lane to 04/36 Foot Pedal 14-bit
261|CC: Set CC lane to 040 Balance LSB
262|CC: Set CC lane to 041
263|CC: Set CC lane to 042 Pan Position LSB
264|CC: Set CC lane to 043 Expression LSB
265|CC: Set CC lane to 044 Control 1 LSB
266|CC: Set CC lane to 045 Control 2 LSB
267|CC: Set CC lane to 046
268|CC: Set CC lane to 047
269|CC: Set CC lane to 048
270|CC: Set CC lane to 049
271|CC: Set CC lane to 05/37 Portamento 14-bit
272|CC: Set CC lane to 050
273|CC: Set CC lane to 051
274|CC: Set CC lane to 052
275|CC: Set CC lane to 053
276|CC: Set CC lane to 054
277|CC: Set CC lane to 055
278|CC: Set CC lane to 056
279|CC: Set CC lane to 057
280|CC: Set CC lane to 058
281|CC: Set CC lane to 059
282|CC: Set CC lane to 06/38 Data Entry 14-bit
283|CC: Set CC lane to 060
284|CC: Set CC lane to 061
285|CC: Set CC lane to 062
286|CC: Set CC lane to 063
287|CC: Set CC lane to 064 Hold Pedal (on/off)
288|CC: Set CC lane to 065 Portamento (on/off)
289|CC: Set CC lane to 066 Sostenuto (on/off)
290|CC: Set CC lane to 067 Soft Pedal (on/off)
291|CC: Set CC lane to 068 Legato Pedal (on/off)
292|CC: Set CC lane to 069 Hold 2 Pedal (on/off)
293|CC: Set CC lane to 07/39 Volume 14-bit
294|CC: Set CC lane to 070 Sound Variation
295|CC: Set CC lane to 071 Timbre/Resonance
296|CC: Set CC lane to 072 Sound Release
297|CC: Set CC lane to 073 Sound Attack
298|CC: Set CC lane to 074 Brightness/Cutoff Freq
299|CC: Set CC lane to 075 Sound Control 6
300|CC: Set CC lane to 076 Sound Control 7
301|CC: Set CC lane to 077 Sound Control 8
302|CC: Set CC lane to 078 Sound Control 9
303|CC: Set CC lane to 079 Sound Control 10
304|CC: Set CC lane to 08/40 Balance 14-bit
305|CC: Set CC lane to 080 GP Button 1 (on/off)
306|CC: Set CC lane to 081 GP Button 2 (on/off)
307|CC: Set CC lane to 082 GP Button 3 (on/off)
308|CC: Set CC lane to 083 GP Button 4 (on/off)
309|CC: Set CC lane to 084
310|CC: Set CC lane to 085
311|CC: Set CC lane to 086
312|CC: Set CC lane to 087
313|CC: Set CC lane to 088
314|CC: Set CC lane to 089
315|CC: Set CC lane to 09/41 14-bit
316|CC: Set CC lane to 090
317|CC: Set CC lane to 091 Effects Level
318|CC: Set CC lane to 092 Tremolo Level
319|CC: Set CC lane to 093 Chorus Level
320|CC: Set CC lane to 094 Celeste Level
321|CC: Set CC lane to 095 Phaser Level
322|CC: Set CC lane to 096 Data Button Inc
323|CC: Set CC lane to 097 Data Button Dec
324|CC: Set CC lane to 098 Non-Reg Parm LSB
325|CC: Set CC lane to 099 Non-Reg Parm MSB
326|CC: Set CC lane to 10/42 Pan Position 14-bit
327|CC: Set CC lane to 100 Reg Parm LSB
328|CC: Set CC lane to 101 Reg Parm MSB
329|CC: Set CC lane to 102
330|CC: Set CC lane to 103
331|CC: Set CC lane to 104
332|CC: Set CC lane to 105
333|CC: Set CC lane to 106
334|CC: Set CC lane to 107
335|CC: Set CC lane to 108
336|CC: Set CC lane to 109
337|CC: Set CC lane to 11/43 Expression 14-bit
338|CC: Set CC lane to 110
339|CC: Set CC lane to 111
340|CC: Set CC lane to 112
341|CC: Set CC lane to 113
342|CC: Set CC lane to 114
343|CC: Set CC lane to 115
344|CC: Set CC lane to 116
345|CC: Set CC lane to 117
346|CC: Set CC lane to 118
347|CC: Set CC lane to 119
348|CC: Set CC lane to 12/44 Control 1 14-bit
349|CC: Set CC lane to 13/45 Control 2 14-bit
350|CC: Set CC lane to 14/46 14-bit
351|CC: Set CC lane to 15/47 14-bit
352|CC: Set CC lane to 16/48 GP Slider 114-bit
353|CC: Set CC lane to 17/49 GP Slider 214-bit
354|CC: Set CC lane to 18/50 GP Slider 314-bit
355|CC: Set CC lane to 19/51 GP Slider 414-bit
356|CC: Set CC lane to 20/52 14-bit
357|CC: Set CC lane to 21/53 14-bit
358|CC: Set CC lane to 22/54 14-bit
359|CC: Set CC lane to 23/55 14-bit
360|CC: Set CC lane to 24/56 14-bit
361|CC: Set CC lane to 25/57 14-bit
362|CC: Set CC lane to 26/58 14-bit
363|CC: Set CC lane to 27/59 14-bit
364|CC: Set CC lane to 28/60 14-bit
365|CC: Set CC lane to 29/61 14-bit
366|CC: Set CC lane to 30/62 14-bit
367|CC: Set CC lane to 31/63 14-bit
368|CC: Set CC lane to Bank/Program Select
369|CC: Set CC lane to Channel Pressure
370|CC: Set CC lane to Pitch
371|CC: Set CC lane to Poly Aftertouch
372|CC: Set CC lane to Program
373|CC: Set CC lane to Sysex
374|CC: Set CC lane to Text Events
375|CC: Set CC lane to Velocity
376|Calculate loudness of master mix via dry run render
377|Calculate loudness of master mix within time selection via dry run render
378|Calculate loudness of selected items source media via dry run render
379|Calculate loudness of selected items, including take and track FX and settings, via dry run render
380|Calculate loudness of selected tracks via dry run render
381|Calculate loudness of selected tracks within time selection via dry run render
382|Calculate loudness statistics for media via dry run render
383|Calculate mono loudness of selected tracks via dry run render
384|Calculate mono loudness of selected tracks within time selection via dry run render
385|Calculate peak volume and loudness (LUFS-I) for media
386|Calculate peak volume and loudness (LUFS-I) for media (force recalculation)
387|Calculate peak volume for all media
388|Calculate peak volume for media
389|Calculate transient guides
390|Calculate transient guides for visible areas in items
391|Channel: Show all channels
392|Channel: Show only channel 01
393|Channel: Show only channel 02
394|Channel: Show only channel 03
395|Channel: Show only channel 04
396|Channel: Show only channel 05
397|Channel: Show only channel 06
398|Channel: Show only channel 07
399|Channel: Show only channel 08
400|Channel: Show only channel 09
401|Channel: Show only channel 10
402|Channel: Show only channel 11
403|Channel: Show only channel 12
404|Channel: Show only channel 13
405|Channel: Show only channel 14
406|Channel: Show only channel 15
407|Channel: Show only channel 16
408|Channel: Show only next channel
409|Channel: Show only previous channel
410|Channel: Toggle channel 01
411|Channel: Toggle channel 02
412|Channel: Toggle channel 03
413|Channel: Toggle channel 04
414|Channel: Toggle channel 05
415|Channel: Toggle channel 06
416|Channel: Toggle channel 07
417|Channel: Toggle channel 08
418|Channel: Toggle channel 09
419|Channel: Toggle channel 10
420|Channel: Toggle channel 11
421|Channel: Toggle channel 12
422|Channel: Toggle channel 13
423|Channel: Toggle channel 14
424|Channel: Toggle channel 15
425|Channel: Toggle channel 16
426|Chase MIDI note-on/CC/PC/pitch in project playback
427|Clear all note/CC names
428|Clear all temporary marks
429|Clear project recording tag ($rectag wildcard)
430|Clear tempo envelope
431|Clear transient guides
432|Close Media Explorer window
433|Close all projects but current
434|Close current project tab
435|Close inline editor
436|Collapse all folders
437|Color by source for default-colored tracks/items when coloring by track or media item
438|Color notes by pitch
439|Color notes by velocity
440|Color notes by voice
441|Color notes/CC by channel
442|Color notes/CC by media item custom color
443|Color notes/CC by source, using colormap
444|Color notes/CC by track custom color
445|Colors: Reset random color generator
446|Command Palette: Reload
447|Command Palette: Show
448|Comp takes: Activate next comp
449|Comp takes: Activate previous comp
450|Comp takes: Choose active comp for item under mouse (and all other items in the comp)
451|Comp takes: Crop list to active comp
452|Comp takes: Move active comp to top lane
453|Comp takes: Remove active comp from list
454|Comp takes: Save/rename active comp...
455|Comp takes: Toggle select last comp (A/B)
456|Contents: Activate next MIDI media item on this track, clearing the editor first
457|Contents: Activate next MIDI media item on this track, preserving existing editor contents
458|Contents: Activate previous MIDI media item on this track, clearing the editor first
459|Contents: Activate previous MIDI media item on this track, preserving existing editor contents
460|Contents: Display all MIDI media items on this track
461|Contents: Display editor contents menu at mouse position
462|Contents: Show/hide media item lane
463|Contents: Show/hide track list
464|Control surface: Refresh all surfaces
465|Convert active take MIDI to .mid file reference
466|Convert active take MIDI to in-project MIDI source data
467|Correct overlapping notes
468|Create measure from time selection (detect tempo, detect number of measures)
469|Create measure from time selection (detect tempo, try to create single measure)
470|Create measure from time selection (new time signature)...
471|Create new folder
472|Cursor: Advance 1
473|Cursor: Advance 1 using current note length division type
474|Cursor: Advance 1/128
475|Cursor: Advance 1/128 using current note length division type
476|Cursor: Advance 1/128.
477|Cursor: Advance 1/16
478|Cursor: Advance 1/16 using current note length division type
479|Cursor: Advance 1/16.
480|Cursor: Advance 1/16T
481|Cursor: Advance 1/2
482|Cursor: Advance 1/2 using current note length division type
483|Cursor: Advance 1/2.
484|Cursor: Advance 1/2T
485|Cursor: Advance 1/32
486|Cursor: Advance 1/32 using current note length division type
487|Cursor: Advance 1/32.
488|Cursor: Advance 1/32T
489|Cursor: Advance 1/4
490|Cursor: Advance 1/4 using current note length division type
491|Cursor: Advance 1/4.
492|Cursor: Advance 1/4T
493|Cursor: Advance 1/64
494|Cursor: Advance 1/64 using current note length division type
495|Cursor: Advance 1/64.
496|Cursor: Advance 1/8
497|Cursor: Advance 1/8 using current note length division type
498|Cursor: Advance 1/8.
499|Cursor: Advance 1/8T
500|Custom: Affichage MIdi Piano
501|Custom: Affichage Midi Drums
502|Custom: Armer en Enregistrement, Monitoring
503|Custom: Chevauchement, Fondus Autmatiques
504|Custom: Color items by group
505|Custom: Create text items from groups and notes from regions
506|Custom: Default poitn shape to suqare
507|Custom: Degrouper / Couper
508|Custom: Définir la fin de l'Objet au Curseur
509|Custom: Déplacer objet au curseur, Déplacer curseur à la fin
510|Custom: Désactiver Solo Toutes Les Pistes
511|Custom: Désélectionner tout, Déplacer Curseur, Piste sous la Souris
512|Custom: Export Objet
513|Custom: Export SRT from =START
514|Custom: Go to next region, play
515|Custom: Go to previous region, play
516|Custom: Grid and notes to 1/16
517|Custom: Insert note at mouse cursor, unselect the others
518|Custom: Layout Button : Ajouter un séparateur TCP & MCP
519|Custom: Layout Button : Black Track Layout
520|Custom: Layout Button : Vertical Meters & Classic Layout
521|Custom: Move notes down one semitone and zoom vertically
522|Custom: Move notes up one semitone and zoom vertically
523|Custom: Move position of item to edit cursor without snap offset
524|Custom: Next item to previous item and ripple
525|Custom: Objet Couleur Défaut, Grouper
526|Custom: Paste item notes and select next item
527|Custom: Play from snap offset
528|Custom: Quantize item edges and Snap MIDI notes to grid
529|Custom: Rassembler en Prises, Dégradé, Eclater, Muet
530|Custom: Record on new track
531|Custom: Redémarrer Reaper
532|Custom: Remove item under mouse restoring fades and scroll view to edit cursor
533|Custom: Render track pre fx
534|Custom: Renumber Marker and Regions ID
535|Custom: Replace selected items by empty
536|Custom: SHow TCP FX and Sends
537|Custom: SWS Global startup actions
538|Custom: Set track/item to black color
539|Custom: Set track/item to white color
540|Custom: Set track/take custom color
541|Custom: Set track/take to 1-16 color gradient
542|Custom: Set track/take to SWS color gradient
543|Custom: Set track/take to custom color 1
544|Custom: Set track/take to custom color 10
545|Custom: Set track/take to custom color 11
546|Custom: Set track/take to custom color 12
547|Custom: Set track/take to custom color 13
548|Custom: Set track/take to custom color 14
549|Custom: Set track/take to custom color 15
550|Custom: Set track/take to custom color 16
551|Custom: Set track/take to custom color 2
552|Custom: Set track/take to custom color 3
553|Custom: Set track/take to custom color 4
554|Custom: Set track/take to custom color 5
555|Custom: Set track/take to custom color 6
556|Custom: Set track/take to custom color 7
557|Custom: Set track/take to custom color 8
558|Custom: Set track/take to custom color 9
559|Custom: Set track/take to default color
560|Custom: Set track/take to one random color
561|Custom: Set track/take to random colors
562|Custom: Split Trim Left (Copy)
563|Custom: Split Trim Righ
564|Custom: Split Trim Righ (Copy)
565|Custom: Split item under mouse and delete left
566|Custom: Split items at mouse creating new groups
567|Custom: Split items group under mouse
568|Custom: Supprimer Prise et Supprimer Prises Vides
569|Custom: Sélectionner Objet, Déplacer Curseur, Désélectionner Piste
570|Custom: Sélectionner Piste par rapport à Objet
571|Custom: Sélectionner sous Curseur, Sélectionner Piste en fonction de Objet
572|Custom: Sélectionner toutes les Pistes, Désactiver Monitoring et Enregistrement
573|Custom: Time selection to selected notes and move cursor
574|Custom: Unselect all and razor area as well
575|Custom: Verouiller Piste et Objets
576|Custom: YOUPI
577|Custom: delete redundant point
578|Custom: group items, create regions and edit it
579|Custom: play snap offset once
580|Custom: unselect all items and last touched track under mouse
581|Customize MIDI editor toolbar
582|Customize menus
583|Display image metadata...
584|Do not assign pitch, note, or channel when inserting into sampler
585|Dock Media Explorer in Docker
586|Dock/undock currently focused dockable window, or attach/unattach focused docker
587|Docker: Activate next tab
588|Docker: Activate previous tab
589|Docker: Show in bottom of main window
590|Docker: Show in left of main window
591|Docker: Show in right of main window
592|Docker: Show in top of main window
593|Dockers: Compact when small and single tab
594|Double length of MIDI (repeating contents)
595|Edit image metadata...
596|Edit metadata tag: Album
597|Edit metadata tag: Artist
598|Edit metadata tag: BPM
599|Edit metadata tag: Comment
600|Edit metadata tag: Custom Tags
601|Edit metadata tag: Date
602|Edit metadata tag: Description
603|Edit metadata tag: Genre
604|Edit metadata tag: Key
605|Edit metadata tag: Offset
606|Edit metadata tag: Title
607|Edit metadata tag: Track Number
608|Edit metadata tag: User-created tag 1
609|Edit metadata tag: User-created tag 10
610|Edit metadata tag: User-created tag 2
611|Edit metadata tag: User-created tag 3
612|Edit metadata tag: User-created tag 4
613|Edit metadata tag: User-created tag 5
614|Edit metadata tag: User-created tag 6
615|Edit metadata tag: User-created tag 7
616|Edit metadata tag: User-created tag 8
617|Edit metadata tag: User-created tag 9
618|Edit: Adjust value for events (mousewheel/MIDI controller only)
619|Edit: Copy
620|Edit: Copy events within time selection
621|Edit: Copy events within time selection, if any (smart copy)
622|Edit: Copy files
623|Edit: Copy items
624|Edit: Copy items/tracks/envelope points (depending on focus) ignoring time selection
625|Edit: Copy items/tracks/envelope points (depending on focus) within time selection, if any (smart copy)
626|Edit: Cut
627|Edit: Cut events within time selection
628|Edit: Cut events within time selection, if any (smart cut)
629|Edit: Cut items
630|Edit: Cut items/tracks/envelope points (depending on focus) ignoring time selection
631|Edit: Cut items/tracks/envelope points (depending on focus) within time selection, if any (smart cut)
632|Edit: Decrease pitch cursor one octave
633|Edit: Decrease pitch cursor one semitone
634|Edit: Decrease value a little bit for CC events
635|Edit: Delete all notes of less than 1/128 note in length
636|Edit: Delete all notes of less than 1/16 note in length
637|Edit: Delete all notes of less than 1/256 note in length
638|Edit: Delete all notes of less than 1/32 note in length
639|Edit: Delete all notes of less than 1/64 note in length
640|Edit: Delete all notes of less than 1/8 note in length
641|Edit: Delete events
642|Edit: Delete notes
643|Edit: Delete notes of less than 1/128 note in length in selected MIDI items
644|Edit: Delete notes of less than 1/16 note in length in selected MIDI items
645|Edit: Delete notes of less than 1/256 note in length in selected MIDI items
646|Edit: Delete notes of less than 1/32 note in length in selected MIDI items
647|Edit: Delete notes of less than 1/64 note in length in selected MIDI items
648|Edit: Delete notes of less than 1/8 note in length in selected MIDI items
649|Edit: Delete trailing notes of less than 1/128 note in length
650|Edit: Delete trailing notes of less than 1/128 note in length in selected MIDI items
651|Edit: Delete trailing notes of less than 1/16 note in length
652|Edit: Delete trailing notes of less than 1/16 note in length in selected MIDI items
653|Edit: Delete trailing notes of less than 1/256 note in length
654|Edit: Delete trailing notes of less than 1/256 note in length in selected MIDI items
655|Edit: Delete trailing notes of less than 1/32 note in length
656|Edit: Delete trailing notes of less than 1/32 note in length in selected MIDI items
657|Edit: Delete trailing notes of less than 1/64 note in length
658|Edit: Delete trailing notes of less than 1/64 note in length in selected MIDI items
659|Edit: Delete trailing notes of less than 1/8 note in length
660|Edit: Delete trailing notes of less than 1/8 note in length in selected MIDI items
661|Edit: Duplicate events
662|Edit: Duplicate events one octave higher
663|Edit: Duplicate events one octave lower
664|Edit: Duplicate events within time selection
665|Edit: Duplicate events within time selection (do not trim notes)
666|Edit: Duplicate events within time selection, if any (smart duplicate)
667|Edit: Duplicate events within time selection, if any (smart duplicate) (do not trim notes)
668|Edit: Dynamic split items using most recent settings
669|Edit: Dynamic split items...
670|Edit: Event properties
671|Edit: Fit notes to time selection
672|Edit: Increase pitch cursor one octave
673|Edit: Increase pitch cursor one semitone
674|Edit: Increase value a little bit for CC events
675|Edit: Insert CC event at edit cursor in current lane
676|Edit: Insert note at edit cursor
677|Edit: Insert note at edit cursor (no advance edit cursor)
678|Edit: Insert note at mouse cursor
679|Edit: Insert note at nearest A
680|Edit: Insert note at nearest A#/Bb
681|Edit: Insert note at nearest B
682|Edit: Insert note at nearest C
683|Edit: Insert note at nearest C#/Db
684|Edit: Insert note at nearest D
685|Edit: Insert note at nearest D#/Eb
686|Edit: Insert note at nearest E
687|Edit: Insert note at nearest F
688|Edit: Insert note at nearest F#/Gb
689|Edit: Insert note at nearest G
690|Edit: Insert note at nearest G#/Ab
691|Edit: Invert (reverse vertically) all note intervals
692|Edit: Invert (reverse vertically) all notes
693|Edit: Invert (reverse vertically) selected note intervals
694|Edit: Invert (reverse vertically) selected notes
695|Edit: Invert voicing downwards for each selected chord
696|Edit: Invert voicing downwards for selected notes
697|Edit: Invert voicing upwards for each selected chord
698|Edit: Invert voicing upwards for selected notes
699|Edit: Join notes
700|Edit: Lengthen notes one grid unit
701|Edit: Lengthen notes one pixel
702|Edit: Make notes legato, preserving note start times
703|Edit: Make notes legato, preserving relative note spacing
704|Edit: Move CC events left 1 pixel
705|Edit: Move CC events left by grid
706|Edit: Move CC events right 1 pixel
707|Edit: Move CC events right by grid
708|Edit: Move edit cursor left one pixel
709|Edit: Move edit cursor right one pixel
710|Edit: Move events left/right (mousewheel/MIDI relative only)
711|Edit: Move left edge of note to edit cursor
712|Edit: Move notes down one octave
713|Edit: Move notes down one semitone
714|Edit: Move notes down one semitone ignoring scale/key
715|Edit: Move notes left one grid unit
716|Edit: Move notes left one pixel
717|Edit: Move notes right one grid unit
718|Edit: Move notes right one pixel
719|Edit: Move notes up one octave
720|Edit: Move notes up one semitone
721|Edit: Move notes up one semitone ignoring scale/key
722|Edit: Move pitch cursor down one octave
723|Edit: Move pitch cursor down one semitone
724|Edit: Move pitch cursor to C60
725|Edit: Move pitch cursor to nearest A
726|Edit: Move pitch cursor to nearest A#/Bb
727|Edit: Move pitch cursor to nearest B
728|Edit: Move pitch cursor to nearest C
729|Edit: Move pitch cursor to nearest C#/Db
730|Edit: Move pitch cursor to nearest D
731|Edit: Move pitch cursor to nearest D#/Eb
732|Edit: Move pitch cursor to nearest E
733|Edit: Move pitch cursor to nearest F
734|Edit: Move pitch cursor to nearest F#/Gb
735|Edit: Move pitch cursor to nearest G
736|Edit: Move pitch cursor to nearest G#/Ab
737|Edit: Move pitch cursor up one octave
738|Edit: Move pitch cursor up one semitone
739|Edit: Move right edge of note to edit cursor
740|Edit: Mute events
741|Edit: Mute events (toggle)
742|Edit: Note velocity +01
743|Edit: Note velocity +10
744|Edit: Note velocity -01
745|Edit: Note velocity -10
746|Edit: Paste
747|Edit: Paste events into the active MIDI media item regardless of source MIDI media item
748|Edit: Paste events preserving position in measure, into the active MIDI media item regardless of source MIDI media item
749|Edit: Paste files
750|Edit: Paste preserving position in measure
751|Edit: Redo
752|Edit: Rename file
753|Edit: Reverse all events
754|Edit: Reverse selected events
755|Edit: Reverse selected events within time selection
756|Edit: Select all CC events in time selection (even if CC lane is hidden)
757|Edit: Select all CC events in time selection (in all visible CC lanes)
758|Edit: Select all CC events in time selection (in last clicked CC lane)
759|Edit: Select all events
760|Edit: Select all events in current time signature
761|Edit: Select all events in lane under mouse
762|Edit: Select all events in measure
763|Edit: Select all events in time selection
764|Edit: Select all events with same active channel
765|Edit: Select all muted events
766|Edit: Select all muted notes
767|Edit: Select all notes
768|Edit: Select all notes in lane under mouse
769|Edit: Select all notes in measure
770|Edit: Select all notes in time selection
771|Edit: Select all notes starting in time selection
772|Edit: Select all notes with same pitch
773|Edit: Select all odd numbered events
774|Edit: Select all unmuted events
775|Edit: Select all unmuted notes
776|Edit: Shorten notes one grid unit
777|Edit: Shorten notes one pixel
778|Edit: Stretch events
779|Edit: Thin out CC events
780|Edit: Transpose notes...
781|Edit: Undo
782|Edit: Unselect all
783|Edit: Unselect all events
784|Edit: Unselect all notes
785|Edit: Unselect events
786|Edit: Unselect notes
787|Edit: Velocity++
788|Edit: Velocity--
789|Edit: Velocity++++
790|Edit: Velocity----
791|Edit: Velocity+01
792|Edit: Velocity-01
793|Edit: Velocity+10
794|Edit: Velocity-10
795|Editor: Close event list
796|Editor: Open event list
797|Editor: Toggle inline editor
798|Editor: Toggle notation/event list view
799|Envelope: Add edge points when moving multiple envelope points
800|Envelope: Add/edit envelope point value at cursor
801|Envelope: Add/edit envelope point value at mouse
802|Envelope: Clear envelope
803|Envelope: Commit take envelopes (apply to underlying track envelope)
804|Envelope: Convert all project automation to bezier curves
805|Envelope: Convert all track automation to bezier curves
806|Envelope: Convert automation to square points
807|Envelope: Convert selected automation to bezier curves
808|Envelope: Convert selected automation to square points
809|Envelope: Convert track automation to bezier curves
810|Envelope: Copy selected points
811|Envelope: Cut selected points
812|Envelope: Delete all points in time selection
813|Envelope: Delete all selected points
814|Envelope: Delete envelope point at cursor
815|Envelope: Delete envelope point near mouse
816|Envelope: Fit selected points to time selection
817|Envelope: Humanize values in lane under mouse...
818|Envelope: Insert 4 envelope points at time selection
819|Envelope: Insert envelope point at cursor (no sort)
820|Envelope: Insert envelope point at cursor, snap to grid
821|Envelope: Insert new envelope point at mouse
822|Envelope: Insert new envelope point at mouse, snap to grid
823|Envelope: Invert all points
824|Envelope: Load point shape preset 1
825|Envelope: Load point shape preset 2
826|Envelope: Load point shape preset 3
827|Envelope: Load point shape preset 4
828|Envelope: Load point shape preset 5
829|Envelope: Load point shape preset 6
830|Envelope: Load point shape preset 7
831|Envelope: Load point shape preset 8
832|Envelope: Load point shape preset 9
833|Envelope: Load point shape preset 10
834|Envelope: Load point shape preset 11
835|Envelope: Load point shape preset 12
836|Envelope: Load point shape preset 13
837|Envelope: Load point shape preset 14
838|Envelope: Load point shape preset 15
839|Envelope: Load point shape preset 16
840|Envelope: Load point shape preset 17
841|Envelope: Load point shape preset 18
842|Envelope: Load point shape preset 19
843|Envelope: Load point shape preset 20
844|Envelope: Nudge point value down a little bit
845|Envelope: Nudge point value down a tiny bit
846|Envelope: Nudge point value up a little bit
847|Envelope: Nudge point value up a tiny bit
848|Envelope: Nudge selected points position left a little bit
849|Envelope: Nudge selected points position left a tiny bit
850|Envelope: Nudge selected points position left by grid
851|Envelope: Nudge selected points position right a little bit
852|Envelope: Nudge selected points position right a tiny bit
853|Envelope: Nudge selected points position right by grid
854|Envelope: Nudge selected points value down a little bit
855|Envelope: Nudge selected points value down a tiny bit
856|Envelope: Nudge selected points value up a little bit
857|Envelope: Nudge selected points value up a tiny bit
858|Envelope: Paste points at cursor
859|Envelope: Reduce number of points by half (decimate)
860|Envelope: Reduce number of points...
861|Envelope: Reset all envelope points to zero/center
862|Envelope: Reset selected envelope points to zero/center
863|Envelope: Reverse points
864|Envelope: Select all points
865|Envelope: Select all points in time selection
866|Envelope: Select shape preset 1
867|Envelope: Select shape preset 2
868|Envelope: Select shape preset 3
869|Envelope: Select shape preset 4
870|Envelope: Select shape preset 5
871|Envelope: Select shape preset 6
872|Envelope: Select shape preset 7
873|Envelope: Select shape preset 8
874|Envelope: Select shape preset 9
875|Envelope: Select shape preset 10
876|Envelope: Select shape preset 11
877|Envelope: Select shape preset 12
878|Envelope: Select shape preset 13
879|Envelope: Select shape preset 14
880|Envelope: Select shape preset 15
881|Envelope: Select shape preset 16
882|Envelope: Select shape preset 17
883|Envelope: Select shape preset 18
884|Envelope: Select shape preset 19
885|Envelope: Select shape preset 20
886|Envelope: Set all selected envelopes visible
887|Envelope: Set default point shape to bezier
888|Envelope: Set default point shape to fast end
889|Envelope: Set default point shape to fast start
890|Envelope: Set default point shape to linear
891|Envelope: Set default point shape to slow start/end
892|Envelope: Set default point shape to square
893|Envelope: Set envelope visible
894|Envelope: Set first selected envelope visible
895|Envelope: Set last selected envelope visible
896|Envelope: Set point shape to bezier
897|Envelope: Set point shape to fast end
898|Envelope: Set point shape to fast start
899|Envelope: Set point shape to linear
900|Envelope: Set point shape to slow start/end
901|Envelope: Set point shape to square
902|Envelope: Set time selection to envelope
903|Envelope: Set time selection to envelope points
904|Envelope: Shift points (mousewheel/MIDI CC only)
905|Envelope: Show all active envelopes for tracks
906|Envelope: Show all envelopes for all tracks
907|Envelope: Show all envelopes for last touched track
908|Envelope: Show all envelopes for tracks
909|Envelope: Show last touched envelope
910|Envelope: Toggle all active envelopes for tracks
911|Envelope: Toggle all envelopes for all tracks
912|Envelope: Toggle all envelopes for tracks
913|Envelope: Toggle show all active envelopes for tracks
914|Envelope: Toggle show all envelopes for all tracks
915|Envelope: Toggle show all envelopes for tracks
916|Envelope: Toggle show last touched envelope
917|Envelope: Toggle track/take envelope
918|Envelope: Toggle visible all active envelopes for tracks
919|Envelope: Toggle visible all envelopes for all tracks
920|Envelope: Toggle visible all envelopes for tracks
921|Envelope: Toggle visible last touched envelope
922|Envelope: Unselect all points
923|Envelope: View I/O for current/last touched track
924|Envelope: View envelopes for current/last touched track
925|Envelope: View faders for current/last touched track
926|Envelopes: Move selected points down by grid
927|Envelopes: Move selected points left by grid
928|Envelopes: Move selected points right by grid
929|Envelopes: Move selected points up by grid
930|Event: Close editor
931|Event: Open secondary editor
932|Export project MIDI...
933|Export: Configuration...
934|Export: MIDI to file...
935|Export: Project to clipboard
936|Export: Project to file...
937|Export: Selected events as MIDI to clipboard
938|Export: Selected events as MIDI to file...
939|Export: Selected notes/CC as MIDI to clipboard
940|Export: Selected notes/CC as MIDI to file...
941|Export: Time selection as MIDI to clipboard
942|Export: Time selection as MIDI to file...
943|FX browser: Activate next FX in browser tree
944|FX browser: Activate previous FX in browser tree
945|FX browser: Add FX to selected tracks
946|FX browser: Add FX to selected tracks (replace existing)
947|FX browser: Add FX to selected tracks and close browser
948|FX browser: Add FX to selected tracks and close browser (replace existing)
949|FX browser: Add selected FX to current track
950|FX browser: Add selected FX to current track (replace existing)
951|FX browser: Add selected FX to current track and close browser
952|FX browser: Add selected FX to current track and close browser (replace existing)
953|FX browser: Delete selected FX from list
954|FX browser: Edit name of selected FX
955|FX browser: Move down
956|FX browser: Move to parent folder
957|FX browser: Move up
958|FX browser: Search (focuses search field)
959|FX browser: Show all FX
960|FX browser: Show only FX containing...
961|FX browser: Show only FX from folder...
962|FX browser: Show only FX matching...
963|FX browser: Show only JS FX
964|FX browser: Show only VST FX
965|FX browser: Show only VSTi FX
966|FX browser: Show only recently used FX
967|FX browser: Show/hide FX browser
968|FX browser: Toggle show all FX
969|FX browser: Toggle show only FX containing...
970|FX browser: Toggle show only FX from folder...
971|FX browser: Toggle show only FX matching...
972|FX browser: Toggle show only JS FX
973|FX browser: Toggle show only VST FX
974|FX browser: Toggle show only VSTi FX
975|FX browser: Toggle show only recently used FX
976|FX: Add FX to selected tracks
977|FX: Add FX to selected tracks (replace existing)
978|FX: Add FX to selected tracks and close browser
979|FX: Add FX to selected tracks and close browser (replace existing)
980|FX: Add selected FX to current track
981|FX: Add selected FX to current track (replace existing)
982|FX: Add selected FX to current track and close browser
983|FX: Add selected FX to current track and close browser (replace existing)
984|FX: Close FX chain for current track
985|FX: Close FX chain for master track
986|FX: Close floating FX window(s) for current track
987|FX: Close floating FX window(s) for master track
988|FX: Close floating FX window(s) for selected tracks
989|FX: Float FX 1 for current track
990|FX: Float FX 1 for master track
991|FX: Float FX 1 for selected tracks
992|FX: Float FX 2 for current track
993|FX: Float FX 2 for master track
994|FX: Float FX 2 for selected tracks
995|FX: Float FX 3 for current track
996|FX: Float FX 3 for master track
997|FX: Float FX 3 for selected tracks
998|FX: Float FX 4 for current track
999|FX: Float FX 4 for master track
1000|FX: Float FX 4 for selected tracks
1001|FX: Float FX 5 for current track
1002|FX: Float FX 5 for master track
1003|FX: Float FX 5 for selected tracks
1004|FX: Float FX 6 for current track
1005|FX: Float FX 6 for master track
1006|FX: Float FX 6 for selected tracks
1007|FX: Float FX 7 for current track
1008|FX: Float FX 7 for master track
1009|FX: Float FX 7 for selected tracks
1010|FX: Float FX 8 for current track
1011|FX: Float FX 8 for master track
1012|FX: Float FX 8 for selected tracks
1013|FX: Float last focused FX for current track
1014|FX: Float last focused FX for master track
1015|FX: Float last focused FX for selected tracks
1016|FX: Float last touched FX for current track
1017|FX: Float last touched FX for master track
1018|FX: Float last touched FX for selected tracks
1019|FX: Show FX chain for current track
1020|FX: Show FX chain for master track
1021|FX: Show FX chain for selected tracks
1022|FX: Show embedded UI for FX 1 for current track
1023|FX: Show embedded UI for FX 1 for master track
1024|FX: Show embedded UI for FX 1 for selected tracks
1025|FX: Show embedded UI for FX 2 for current track
1026|FX: Show embedded UI for FX 2 for master track
1027|FX: Show embedded UI for FX 2 for selected tracks
1028|FX: Show embedded UI for FX 3 for current track
1029|FX: Show embedded UI for FX 3 for master track
1030|FX: Show embedded UI for FX 3 for selected tracks
1031|FX: Show embedded UI for FX 4 for current track
1032|FX: Show embedded UI for FX 4 for master track
1033|FX: Show embedded UI for FX 4 for selected tracks
1034|FX: Show embedded UI for FX 5 for current track
1035|FX: Show embedded UI for FX 5 for master track
1036|FX: Show embedded UI for FX 5 for selected tracks
1037|FX: Show embedded UI for FX 6 for current track
1038|FX: Show embedded UI for FX 6 for master track
1039|FX: Show embedded UI for FX 6 for selected tracks
1040|FX: Show embedded UI for FX 7 for current track
1041|FX: Show embedded UI for FX 7 for master track
1042|FX: Show embedded UI for FX 7 for selected tracks
1043|FX: Show embedded UI for FX 8 for current track
1044|FX: Show embedded UI for FX 8 for master track
1045|FX: Show embedded UI for FX 8 for selected tracks
1046|FX: Show embedded UI for last touched FX for current track
1047|FX: Show embedded UI for last touched FX for master track
1048|FX: Show embedded UI for last touched FX for selected tracks
1049|FX: Show/hide FX browser
1050|FX: Toggle bypass FX 1 for current track
1051|FX: Toggle bypass FX 1 for master track
1052|FX: Toggle bypass FX 1 for selected tracks
1053|FX: Toggle bypass FX 2 for current track
1054|FX: Toggle bypass FX 2 for master track
1055|FX: Toggle bypass FX 2 for selected tracks
1056|FX: Toggle bypass FX 3 for current track
1057|FX: Toggle bypass FX 3 for master track
1058|FX: Toggle bypass FX 3 for selected tracks
1059|FX: Toggle bypass FX 4 for current track
1060|FX: Toggle bypass FX 4 for master track
1061|FX: Toggle bypass FX 4 for selected tracks
1062|FX: Toggle bypass FX 5 for current track
1063|FX: Toggle bypass FX 5 for master track
1064|FX: Toggle bypass FX 5 for selected tracks
1065|FX: Toggle bypass FX 6 for current track
1066|FX: Toggle bypass FX 6 for master track
1067|FX: Toggle bypass FX 6 for selected tracks
1068|FX: Toggle bypass FX 7 for current track
1069|FX: Toggle bypass FX 7 for master track
1070|FX: Toggle bypass FX 7 for selected tracks
1071|FX: Toggle bypass FX 8 for current track
1072|FX: Toggle bypass FX 8 for master track
1073|FX: Toggle bypass FX 8 for selected tracks
1074|FX: Toggle bypass all FX for current track
1075|FX: Toggle bypass all FX for master track
1076|FX: Toggle bypass all FX for selected tracks
1077|FX: Toggle bypass last FX for current track
1078|FX: Toggle bypass last FX for master track
1079|FX: Toggle bypass last FX for selected tracks
1080|FX: Toggle show FX chain for current track
1081|FX: Toggle show FX chain for master track
1082|FX: Toggle show FX chain for selected tracks
1083|FX: Toggle show embedded UI for FX 1 for current track
1084|FX: Toggle show embedded UI for FX 1 for master track
1085|FX: Toggle show embedded UI for FX 1 for selected tracks
1086|FX: Toggle show embedded UI for FX 2 for current track
1087|FX: Toggle show embedded UI for FX 2 for master track
1088|FX: Toggle show embedded UI for FX 2 for selected tracks
1089|FX: Toggle show embedded UI for FX 3 for current track
1090|FX: Toggle show embedded UI for FX 3 for master track
1091|FX: Toggle show embedded UI for FX 3 for selected tracks
1092|FX: Toggle show embedded UI for FX 4 for current track
1093|FX: Toggle show embedded UI for FX 4 for master track
1094|FX: Toggle show embedded UI for FX 4 for selected tracks
1095|FX: Toggle show embedded UI for FX 5 for current track
1096|FX: Toggle show embedded UI for FX 5 for master track
1097|FX: Toggle show embedded UI for FX 5 for selected tracks
1098|FX: Toggle show embedded UI for FX 6 for current track
1099|FX: Toggle show embedded UI for FX 6 for master track
1100|FX: Toggle show embedded UI for FX 6 for selected tracks
1101|FX: Toggle show embedded UI for FX 7 for current track
1102|FX: Toggle show embedded UI for FX 7 for master track
1103|FX: Toggle show embedded UI for FX 7 for selected tracks
1104|FX: Toggle show embedded UI for FX 8 for current track
1105|FX: Toggle show embedded UI for FX 8 for master track
1106|FX: Toggle show embedded UI for FX 8 for selected tracks
1107|FX: Toggle show embedded UI for last touched FX for current track
1108|FX: Toggle show embedded UI for last touched FX for master track
1109|FX: Toggle show embedded UI for last touched FX for selected tracks
1110|Fade-in: Set to default fade-in shape
1111|Fade-in: Set to fade-in shape 1
1112|Fade-in: Set to fade-in shape 2
1113|Fade-in: Set to fade-in shape 3
1114|Fade-in: Set to fade-in shape 4
1115|Fade-in: Set to fade-in shape 5
1116|Fade-in: Set to fade-in shape 6
1117|Fade-in: Set to fade-in shape 7
1118|Fade-out: Set to default fade-out shape
1119|Fade-out: Set to fade-out shape 1
1120|Fade-out: Set to fade-out shape 2
1121|Fade-out: Set to fade-out shape 3
1122|Fade-out: Set to fade-out shape 4
1123|Fade-out: Set to fade-out shape 5
1124|Fade-out: Set to fade-out shape 6
1125|Fade-out: Set to fade-out shape 7
1126|Fade: Set to default crossfade shape
1127|Fade: Set to default fade shape
1128|Fade: Set to fade shape 1
1129|Fade: Set to fade shape 2
1130|Fade: Set to fade shape 3
1131|Fade: Set to fade shape 4
1132|Fade: Set to fade shape 5
1133|Fade: Set to fade shape 6
1134|Fade: Set to fade shape 7
1135|Fades: Adjust absolute fade-in length (mousewheel/MIDI CC only)
1136|Fades: Adjust absolute fade-out length (mousewheel/MIDI CC only)
1137|Fades: Adjust relative fade-in length (mousewheel/MIDI CC only)
1138|Fades: Adjust relative fade-out length (mousewheel/MIDI CC only)
1139|File: Close window
1140|File: Consolidate tracks...
1141|File: Export project MIDI...
1142|File: Import from clipboard...
1143|File: Import from file...
1144|File: Open project
1145|File: Open project directory in explorer/finder
1146|File: Quit REAPER
1147|File: Render project to disk...
1148|File: Render project, using most recent render settings...
1149|File: Save live output to disk (bounce)...
1150|File: Save new version of project (automatically increment project name)...
1151|File: Save project
1152|File: Save project as template...
1153|File: Save project as...
1154|File: Save project with media moved/copied/converted to new folder...
1155|File: Save project, auto-increment project name if unsaved...
1156|File: Save project, auto-increment project name/version...
1157|Filter: Clear filter
1158|Filter: Show/hide filter
1159|Fit item contents
1160|Fit item contents, including leading and trailing silence
1161|Fit item contents, including leading silence
1162|Fit item contents, including trailing silence
1163|Fit item loop
1164|Fit item loop, including leading and trailing silence
1165|Fit item loop, including leading silence
1166|Fit item loop, including trailing silence
1167|Fixed item lanes: Add lane
1168|Fixed item lanes: Collapse all lanes
1169|Fixed item lanes: Collapse all lanes in selected tracks
1170|Fixed item lanes: Collapse empty lanes
1171|Fixed item lanes: Collapse empty lanes in selected tracks
1172|Fixed item lanes: Delete lane
1173|Fixed item lanes: Expand all lanes
1174|Fixed item lanes: Expand all lanes in selected tracks
1175|Fixed item lanes: Hide lane
1176|Fixed item lanes: Play only highest lane
1177|Fixed item lanes: Play only lane 1
1178|Fixed item lanes: Play only lane 2
1179|Fixed item lanes: Play only lane 3
1180|Fixed item lanes: Play only lane 4
1181|Fixed item lanes: Play only lane 5
1182|Fixed item lanes: Play only lane 6
1183|Fixed item lanes: Play only lane 7
1184|Fixed item lanes: Play only lane 8
1185|Fixed item lanes: Play only lane 9
1186|Fixed item lanes: Play only lane 10
1187|Fixed item lanes: Play only lane 11
1188|Fixed item lanes: Play only lane 12
1189|Fixed item lanes: Play only lane 13
1190|Fixed item lanes: Play only lane 14
1191|Fixed item lanes: Play only lane 15
1192|Fixed item lanes: Play only lane 16
1193|Fixed item lanes: Play only lane 17
1194|Fixed item lanes: Play only lane 18
1195|Fixed item lanes: Play only lane 19
1196|Fixed item lanes: Play only lane 20
1197|Fixed item lanes: Play only lane 21
1198|Fixed item lanes: Play only lane 22
1199|Fixed item lanes: Play only lane 23
1200|Fixed item lanes: Play only lane 24
1201|Fixed item lanes: Play only lane 25
1202|Fixed item lanes: Play only lane 26
1203|Fixed item lanes: Play only lane 27
1204|Fixed item lanes: Play only lane 28
1205|Fixed item lanes: Play only lane 29
1206|Fixed item lanes: Play only lane 30
1207|Fixed item lanes: Play only lane 31
1208|Fixed item lanes: Play only lane 32
1209|Fixed item lanes: Play only lane 33
1210|Fixed item lanes: Play only lane 34
1211|Fixed item lanes: Play only lane 35
1212|Fixed item lanes: Play only lane 36
1213|Fixed item lanes: Play only lane 37
1214|Fixed item lanes: Play only lane 38
1215|Fixed item lanes: Play only lane 39
1216|Fixed item lanes: Play only lane 40
1217|Fixed item lanes: Play only lane 41
1218|Fixed item lanes: Play only lane 42
1219|Fixed item lanes: Play only lane 43
1220|Fixed item lanes: Play only lane 44
1221|Fixed item lanes: Play only lane 45
1222|Fixed item lanes: Play only lane 46
1223|Fixed item lanes: Play only lane 47
1224|Fixed item lanes: Play only lane 48
1225|Fixed item lanes: Play only lane 49
1226|Fixed item lanes: Play only lane 50
1227|Fixed item lanes: Play only lane 51
1228|Fixed item lanes: Play only lane 52
1229|Fixed item lanes: Play only lane 53
1230|Fixed item lanes: Play only lane 54
1231|Fixed item lanes: Play only lane 55
1232|Fixed item lanes: Play only lane 56
1233|Fixed item lanes: Play only lane 57
1234|Fixed item lanes: Play only lane 58
1235|Fixed item lanes: Play only lane 59
1236|Fixed item lanes: Play only lane 60
1237|Fixed item lanes: Play only lane 61
1238|Fixed item lanes: Play only lane 62
1239|Fixed item lanes: Play only lane 63
1240|Fixed item lanes: Play only lane 64
1241|Fixed item lanes: Play only lane N
1242|Fixed item lanes: Play only lane N-1
1243|Fixed item lanes: Play only lane N-10
1244|Fixed item lanes: Play only lane N-11
1245|Fixed item lanes: Play only lane N-12
1246|Fixed item lanes: Play only lane N-13
1247|Fixed item lanes: Play only lane N-14
1248|Fixed item lanes: Play only lane N-15
1249|Fixed item lanes: Play only lane N-16
1250|Fixed item lanes: Play only lane N-17
1251|Fixed item lanes: Play only lane N-18
1252|Fixed item lanes: Play only lane N-19
1253|Fixed item lanes: Play only lane N-2
1254|Fixed item lanes: Play only lane N-20
1255|Fixed item lanes: Play only lane N-21
1256|Fixed item lanes: Play only lane N-22
1257|Fixed item lanes: Play only lane N-23
1258|Fixed item lanes: Play only lane N-24
1259|Fixed item lanes: Play only lane N-25
1260|Fixed item lanes: Play only lane N-26
1261|Fixed item lanes: Play only lane N-27
1262|Fixed item lanes: Play only lane N-28
1263|Fixed item lanes: Play only lane N-29
1264|Fixed item lanes: Play only lane N-3
1265|Fixed item lanes: Play only lane N-30
1266|Fixed item lanes: Play only lane N-31
1267|Fixed item lanes: Play only lane N-32
1268|Fixed item lanes: Play only lane N-33
1269|Fixed item lanes: Play only lane N-34
1270|Fixed item lanes: Play only lane N-35
1271|Fixed item lanes: Play only lane N-36
1272|Fixed item lanes: Play only lane N-37
1273|Fixed item lanes: Play only lane N-38
1274|Fixed item lanes: Play only lane N-39
1275|Fixed item lanes: Play only lane N-4
1276|Fixed item lanes: Play only lane N-40
1277|Fixed item lanes: Play only lane N-41
1278|Fixed item lanes: Play only lane N-42
1279|Fixed item lanes: Play only lane N-43
1280|Fixed item lanes: Play only lane N-44
1281|Fixed item lanes: Play only lane N-45
1282|Fixed item lanes: Play only lane N-46
1283|Fixed item lanes: Play only lane N-47
1284|Fixed item lanes: Play only lane N-48
1285|Fixed item lanes: Play only lane N-49
1286|Fixed item lanes: Play only lane N-5
1287|Fixed item lanes: Play only lane N-50
1288|Fixed item lanes: Play only lane N-51
1289|Fixed item lanes: Play only lane N-52
1290|Fixed item lanes: Play only lane N-53
1291|Fixed item lanes: Play only lane N-54
1292|Fixed item lanes: Play only lane N-55
1293|Fixed item lanes: Play only lane N-56
1294|Fixed item lanes: Play only lane N-57
1295|Fixed item lanes: Play only lane N-58
1296|Fixed item lanes: Play only lane N-59
1297|Fixed item lanes: Play only lane N-6
1298|Fixed item lanes: Play only lane N-60
1299|Fixed item lanes: Play only lane N-61
1300|Fixed item lanes: Play only lane N-62
1301|Fixed item lanes: Play only lane N-63
1302|Fixed item lanes: Play only lane N-7
1303|Fixed item lanes: Play only lane N-8
1304|Fixed item lanes: Play only lane N-9
1305|Fixed item lanes: Play only lowest lane
1306|Fixed item lanes: Play only next lane
1307|Fixed item lanes: Play only previous lane
1308|Fixed item lanes: Rename lane
1309|Fixed item lanes: Shuffle lanes down
1310|Fixed item lanes: Shuffle lanes up
1311|Fixed item lanes: Show all lanes
1312|Fixed item lanes: Show only lane 1
1313|Fixed item lanes: Show only lane 2
1314|Fixed item lanes: Show only lane 3
1315|Fixed item lanes: Show only lane 4
1316|Fixed item lanes: Show only lane 5
1317|Fixed item lanes: Show only lane 6
1318|Fixed item lanes: Show only lane 7
1319|Fixed item lanes: Show only lane 8
1320|Fixed item lanes: Show only lane 9
1321|Fixed item lanes: Show only lane 10
1322|Fixed item lanes: Show only lane 11
1323|Fixed item lanes: Show only lane 12
1324|Fixed item lanes: Show only lane 13
1325|Fixed item lanes: Show only lane 14
1326|Fixed item lanes: Show only lane 15
1327|Fixed item lanes: Show only lane 16
1328|Fixed item lanes: Show only lane 17
1329|Fixed item lanes: Show only lane 18
1330|Fixed item lanes: Show only lane 19
1331|Fixed item lanes: Show only lane 20
1332|Fixed item lanes: Show only lane 21
1333|Fixed item lanes: Show only lane 22
1334|Fixed item lanes: Show only lane 23
1335|Fixed item lanes: Show only lane 24
1336|Fixed item lanes: Show only lane 25
1337|Fixed item lanes: Show only lane 26
1338|Fixed item lanes: Show only lane 27
1339|Fixed item lanes: Show only lane 28
1340|Fixed item lanes: Show only lane 29
1341|Fixed item lanes: Show only lane 30
1342|Fixed item lanes: Show only lane 31
1343|Fixed item lanes: Show only lane 32
1344|Fixed item lanes: Show only lane 33
1345|Fixed item lanes: Show only lane 34
1346|Fixed item lanes: Show only lane 35
1347|Fixed item lanes: Show only lane 36
1348|Fixed item lanes: Show only lane 37
1349|Fixed item lanes: Show only lane 38
1350|Fixed item lanes: Show only lane 39
1351|Fixed item lanes: Show only lane 40
1352|Fixed item lanes: Show only lane 41
1353|Fixed item lanes: Show only lane 42
1354|Fixed item lanes: Show only lane 43
1355|Fixed item lanes: Show only lane 44
1356|Fixed item lanes: Show only lane 45
1357|Fixed item lanes: Show only lane 46
1358|Fixed item lanes: Show only lane 47
1359|Fixed item lanes: Show only lane 48
1360|Fixed item lanes: Show only lane 49
1361|Fixed item lanes: Show only lane 50
1362|Fixed item lanes: Show only lane 51
1363|Fixed item lanes: Show only lane 52
1364|Fixed item lanes: Show only lane 53
1365|Fixed item lanes: Show only lane 54
1366|Fixed item lanes: Show only lane 55
1367|Fixed item lanes: Show only lane 56
1368|Fixed item lanes: Show only lane 57
1369|Fixed item lanes: Show only lane 58
1370|Fixed item lanes: Show only lane 59
1371|Fixed item lanes: Show only lane 60
1372|Fixed item lanes: Show only lane 61
1373|Fixed item lanes: Show only lane 62
1374|Fixed item lanes: Show only lane 63
1375|Fixed item lanes: Show only lane 64
1376|Fixed item lanes: Show only lane N
1377|Fixed item lanes: Show only lane N-1
1378|Fixed item lanes: Show only lane N-10
1379|Fixed item lanes: Show only lane N-11
1380|Fixed item lanes: Show only lane N-12
1381|Fixed item lanes: Show only lane N-13
1382|Fixed item lanes: Show only lane N-14
1383|Fixed item lanes: Show only lane N-15
1384|Fixed item lanes: Show only lane N-16
1385|Fixed item lanes: Show only lane N-17
1386|Fixed item lanes: Show only lane N-18
1387|Fixed item lanes: Show only lane N-19
1388|Fixed item lanes: Show only lane N-2
1389|Fixed item lanes: Show only lane N-20
1390|Fixed item lanes: Show only lane N-21
1391|Fixed item lanes: Show only lane N-22
1392|Fixed item lanes: Show only lane N-23
1393|Fixed item lanes: Show only lane N-24
1394|Fixed item lanes: Show only lane N-25
1395|Fixed item lanes: Show only lane N-26
1396|Fixed item lanes: Show only lane N-27
1397|Fixed item lanes: Show only lane N-28
1398|Fixed item lanes: Show only lane N-29
1399|Fixed item lanes: Show only lane N-3
1400|Fixed item lanes: Show only lane N-30
1401|Fixed item lanes: Show only lane N-31
1402|Fixed item lanes: Show only lane N-32
1403|Fixed item lanes: Show only lane N-33
1404|Fixed item lanes: Show only lane N-34
1405|Fixed item lanes: Show only lane N-35
1406|Fixed item lanes: Show only lane N-36
1407|Fixed item lanes: Show only lane N-37
1408|Fixed item lanes: Show only lane N-38
1409|Fixed item lanes: Show only lane N-39
1410|Fixed item lanes: Show only lane N-4
1411|Fixed item lanes: Show only lane N-40
1412|Fixed item lanes: Show only lane N-41
1413|Fixed item lanes: Show only lane N-42
1414|Fixed item lanes: Show only lane N-43
1415|Fixed item lanes: Show only lane N-44
1416|Fixed item lanes: Show only lane N-45
1417|Fixed item lanes: Show only lane N-46
1418|Fixed item lanes: Show only lane N-47
1419|Fixed item lanes: Show only lane N-48
1420|Fixed item lanes: Show only lane N-49
1421|Fixed item lanes: Show only lane N-5
1422|Fixed item lanes: Show only lane N-50
1423|Fixed item lanes: Show only lane N-51
1424|Fixed item lanes: Show only lane N-52
1425|Fixed item lanes: Show only lane N-53
1426|Fixed item lanes: Show only lane N-54
1427|Fixed item lanes: Show only lane N-55
1428|Fixed item lanes: Show only lane N-56
1429|Fixed item lanes: Show only lane N-57
1430|Fixed item lanes: Show only lane N-58
1431|Fixed item lanes: Show only lane N-59
1432|Fixed item lanes: Show only lane N-6
1433|Fixed item lanes: Show only lane N-60
1434|Fixed item lanes: Show only lane N-61
1435|Fixed item lanes: Show only lane N-62
1436|Fixed item lanes: Show only lane N-63
1437|Fixed item lanes: Show only lane N-7
1438|Fixed item lanes: Show only lane N-8
1439|Fixed item lanes: Show only lane N-9
1440|Fixed item lanes: Show only next lane
1441|Fixed item lanes: Show only previous lane
1442|Fixed item lanes: Toggle lane collapsed state
1443|Fixed item lanes: Toggle lane collapsed state in selected tracks
1444|Fixed item lanes: Toggle show all lanes
1445|Fixed item lanes: Toggle show lane 1
1446|Fixed item lanes: Toggle show lane 2
1447|Fixed item lanes: Toggle show lane 3
1448|Fixed item lanes: Toggle show lane 4
1449|Fixed item lanes: Toggle show lane 5
1450|Fixed item lanes: Toggle show lane 6
1451|Fixed item lanes: Toggle show lane 7
1452|Fixed item lanes: Toggle show lane 8
1453|Fixed item lanes: Toggle show lane 9
1454|Fixed item lanes: Toggle show lane 10
1455|Fixed item lanes: Toggle show lane 11
1456|Fixed item lanes: Toggle show lane 12
1457|Fixed item lanes: Toggle show lane 13
1458|Fixed item lanes: Toggle show lane 14
1459|Fixed item lanes: Toggle show lane 15
1460|Fixed item lanes: Toggle show lane 16
1461|Fixed item lanes: Toggle show lane 17
1462|Fixed item lanes: Toggle show lane 18
1463|Fixed item lanes: Toggle show lane 19
1464|Fixed item lanes: Toggle show lane 20
1465|Fixed item lanes: Toggle show lane 21
1466|Fixed item lanes: Toggle show lane 22
1467|Fixed item lanes: Toggle show lane 23
1468|Fixed item lanes: Toggle show lane 24
1469|Fixed item lanes: Toggle show lane 25
1470|Fixed item lanes: Toggle show lane 26
1471|Fixed item lanes: Toggle show lane 27
1472|Fixed item lanes: Toggle show lane 28
1473|Fixed item lanes: Toggle show lane 29
1474|Fixed item lanes: Toggle show lane 30
1475|Fixed item lanes: Toggle show lane 31
1476|Fixed item lanes: Toggle show lane 32
1477|Fixed item lanes: Toggle show lane 33
1478|Fixed item lanes: Toggle show lane 34
1479|Fixed item lanes: Toggle show lane 35
1480|Fixed item lanes: Toggle show lane 36
1481|Fixed item lanes: Toggle show lane 37
1482|Fixed item lanes: Toggle show lane 38
1483|Fixed item lanes: Toggle show lane 39
1484|Fixed item lanes: Toggle show lane 40
1485|Fixed item lanes: Toggle show lane 41
1486|Fixed item lanes: Toggle show lane 42
1487|Fixed item lanes: Toggle show lane 43
1488|Fixed item lanes: Toggle show lane 44
1489|Fixed item lanes: Toggle show lane 45
1490|Fixed item lanes: Toggle show lane 46
1491|Fixed item lanes: Toggle show lane 47
1492|Fixed item lanes: Toggle show lane 48
1493|Fixed item lanes: Toggle show lane 49
1494|Fixed item lanes: Toggle show lane 50
1495|Fixed item lanes: Toggle show lane 51
1496|Fixed item lanes: Toggle show lane 52
1497|Fixed item lanes: Toggle show lane 53
1498|Fixed item lanes: Toggle show lane 54
1499|Fixed item lanes: Toggle show lane 55
1500|Fixed item lanes: Toggle show lane 56
1501|Fixed item lanes: Toggle show lane 57
1502|Fixed item lanes: Toggle show lane 58
1503|Fixed item lanes: Toggle show lane 59
1504|Fixed item lanes: Toggle show lane 60
1505|Fixed item lanes: Toggle show lane 61
1506|Fixed item lanes: Toggle show lane 62
1507|Fixed item lanes: Toggle show lane 63
1508|Fixed item lanes: Toggle show lane 64
1509|Fixed item lanes: Toggle show lane N
1510|Fixed item lanes: Toggle show lane N-1
1511|Fixed item lanes: Toggle show lane N-10
1512|Fixed item lanes: Toggle show lane N-11
1513|Fixed item lanes: Toggle show lane N-12
1514|Fixed item lanes: Toggle show lane N-13
1515|Fixed item lanes: Toggle show lane N-14
1516|Fixed item lanes: Toggle show lane N-15
1517|Fixed item lanes: Toggle show lane N-16
1518|Fixed item lanes: Toggle show lane N-17
1519|Fixed item lanes: Toggle show lane N-18
1520|Fixed item lanes: Toggle show lane N-19
1521|Fixed item lanes: Toggle show lane N-2
1522|Fixed item lanes: Toggle show lane N-20
1523|Fixed item lanes: Toggle show lane N-21
1524|Fixed item lanes: Toggle show lane N-22
1525|Fixed item lanes: Toggle show lane N-23
1526|Fixed item lanes: Toggle show lane N-24
1527|Fixed item lanes: Toggle show lane N-25
1528|Fixed item lanes: Toggle show lane N-26
1529|Fixed item lanes: Toggle show lane N-27
1530|Fixed item lanes: Toggle show lane N-28
1531|Fixed item lanes: Toggle show lane N-29
1532|Fixed item lanes: Toggle show lane N-3
1533|Fixed item lanes: Toggle show lane N-30
1534|Fixed item lanes: Toggle show lane N-31
1535|Fixed item lanes: Toggle show lane N-32
1536|Fixed item lanes: Toggle show lane N-33
1537|Fixed item lanes: Toggle show lane N-34
1538|Fixed item lanes: Toggle show lane N-35
1539|Fixed item lanes: Toggle show lane N-36
1540|Fixed item lanes: Toggle show lane N-37
1541|Fixed item lanes: Toggle show lane N-38
1542|Fixed item lanes: Toggle show lane N-39
1543|Fixed item lanes: Toggle show lane N-4
1544|Fixed item lanes: Toggle show lane N-40
1545|Fixed item lanes: Toggle show lane N-41
1546|Fixed item lanes: Toggle show lane N-42
1547|Fixed item lanes: Toggle show lane N-43
1548|Fixed item lanes: Toggle show lane N-44
1549|Fixed item lanes: Toggle show lane N-45
1550|Fixed item lanes: Toggle show lane N-46
1551|Fixed item lanes: Toggle show lane N-47
1552|Fixed item lanes: Toggle show lane N-48
1553|Fixed item lanes: Toggle show lane N-49
1554|Fixed item lanes: Toggle show lane N-5
1555|Fixed item lanes: Toggle show lane N-50
1556|Fixed item lanes: Toggle show lane N-51
1557|Fixed item lanes: Toggle show lane N-52
1558|Fixed item lanes: Toggle show lane N-53
1559|Fixed item lanes: Toggle show lane N-54
1560|Fixed item lanes: Toggle show lane N-55
1561|Fixed item lanes: Toggle show lane N-56
1562|Fixed item lanes: Toggle show lane N-57
1563|Fixed item lanes: Toggle show lane N-58
1564|Fixed item lanes: Toggle show lane N-59
1565|Fixed item lanes: Toggle show lane N-6
1566|Fixed item lanes: Toggle show lane N-60
1567|Fixed item lanes: Toggle show lane N-61
1568|Fixed item lanes: Toggle show lane N-62
1569|Fixed item lanes: Toggle show lane N-63
1570|Fixed item lanes: Toggle show lane N-7
1571|Fixed item lanes: Toggle show lane N-8
1572|Fixed item lanes: Toggle show lane N-9
1573|Fixed item lanes: Uncollapse all lanes
1574|Fixed item lanes: Uncollapse all lanes in selected tracks
1575|Fixed item lanes: Uncollapse empty lanes
1576|Fixed item lanes: Uncollapse empty lanes in selected tracks
1577|Fixed item lanes: Unhide all lanes
1578|Fixed item lanes: Unhide lane
1579|Folder: Collapse all folders
1580|Folder: Collapse all nested folders
1581|Folder: Collapse selected folder
1582|Folder: Expand all folders
1583|Folder: Expand all nested folders
1584|Folder: Expand selected folder
1585|Folder: Toggle selected folder collapsed state
1586|Force selected tracks to TCP
1587|Force selected tracks to TCP and MCP
1588|Force selected tracks to MCP
1589|Go to end of loop
1590|Go to end of time selection
1591|Go to start of loop
1592|Go to start of time selection
1593|Grid: Adjust MIDI TPPQN
1594|Grid: Adjust by 1.1
1595|Grid: Adjust by 1.2
1596|Grid: Adjust by 1/1.1
1597|Grid: Adjust by 1/1.2
1598|Grid: Adjust by 1/2
1599|Grid: Adjust by 1/3
1600|Grid: Adjust by 2
1601|Grid: Adjust by 3
1602|Grid: Relative decrease
1603|Grid: Relative increase
1604|Grid: Set adaptive eighths (no swing)
1605|Grid: Set adaptive quarters (no swing)
1606|Grid: Set adaptive sixteenths (no swing)
1607|Grid: Set adaptive triplets (no swing)
1608|Grid: Set dotted 1/1
1609|Grid: Set dotted 1/16
1610|Grid: Set dotted 1/2
1611|Grid: Set dotted 1/32
1612|Grid: Set dotted 1/4
1613|Grid: Set dotted 1/64
1614|Grid: Set dotted 1/8
1615|Grid: Set to 1
1616|Grid: Set to 1/128
1617|Grid: Set to 1/16
1618|Grid: Set to 1/16T
1619|Grid: Set to 1/2
1620|Grid: Set to 1/32
1621|Grid: Set to 1/32T
1622|Grid: Set to 1/4
1623|Grid: Set to 1/4T
1624|Grid: Set to 1/64
1625|Grid: Set to 1/64T
1626|Grid: Set to 1/8
1627|Grid: Set to 1/8T
1628|Grid: Set triplet 1/12
1629|Grid: Set triplet 1/24
1630|Grid: Set triplet 1/3
1631|Grid: Set triplet 1/48
1632|Grid: Set triplet 1/6
1633|Grid: Set triplet 1/96
1634|Grid: Toggle dotted
1635|Grid: Toggle framerate grid
1636|Grid: Toggle measure grid
1637|Grid: Toggle swing grid
1638|Grid: Toggle triplet
1639|Group: Clear item group
1640|Group: Create and select item group from selected items
1641|Group: Remove selected items from groups
1642|Group: Select all items in groups
1643|Help: About REAPER
1644|Help: All actions / keyboard shortcuts
1645|Help: API functions list
1646|Help: Command line parameters
1647|Help: Documentation
1648|Help: Keyboard shortcuts
1649|Help: Mouse modifier/action reference
1650|Help: ReaScript documentation
1651|Help: What's new in this version
1652|Hide all rulers
1653|Hide docker
1654|Hide inline editor
1655|Hide track in track view and hide track in mixer
1656|Hide track in track view but show track in mixer
1657|Hide track in track view only
1658|Humanize notes...
1659|Import lyric events...
1660|Import metadata from file...
1661|Import: MIDI from clipboard
1662|Import: MIDI from file...
1663|Import: Metadata from file...
1664|Inline editor: Adjust value for events (mousewheel/MIDI CC relative only)
1665|Inline editor: Decrease value a little bit for events
1666|Inline editor: Edit event properties
1667|Inline editor: Increase value a little bit for events
1668|Inline editor: Insert event at mouse cursor
1669|Inline editor: Insert note at edit cursor
1670|Inline editor: Insert note at mouse cursor
1671|Inline editor: Move edit cursor left by grid
1672|Inline editor: Move edit cursor right by grid
1673|Inline editor: Move notes/CC left by grid
1674|Inline editor: Move notes/CC right by grid
1675|Inline editor: Mute events (toggle)
1676|Inline editor: Quantize events using last quantize dialog settings
1677|Inline editor: Quantize...
1678|Inline editor: Select all events
1679|Inline editor: Unselect all events
1680|Inline editor: Velocity +01
1681|Inline editor: Velocity +10
1682|Inline editor: Velocity -01
1683|Inline editor: Velocity -10
1684|Insert click source
1685|Insert empty item from time selection (razor edit areas if exist)
1686|Insert empty space at time selection (moving later items)
1687|Insert media file 1...
1688|Insert media file 10...
1689|Insert media file 2...
1690|Insert media file 3...
1691|Insert media file 4...
1692|Insert media file 5...
1693|Insert media file 6...
1694|Insert media file 7...
1695|Insert media file 8...
1696|Insert media file 9...
1697|Insert media files...
1698|Insert note at edit cursor
1699|Insert note at mouse cursor
1700|Insert note at nearest C
1701|Insert note at nearest C#/Db
1702|Insert note at nearest D
1703|Insert note at nearest D#/Eb
1704|Insert note at nearest E
1705|Insert note at nearest F
1706|Insert note at nearest F#/Gb
1707|Insert note at nearest G
1708|Insert note at nearest G#/Ab
1709|Insert or extend MIDI item
1710|Insert tempo marker at cursor
1711|Insert time signature marker at edit cursor
1712|Insert track from template
1713|Insert virtual instrument on new track...
1714|Insert: Click source
1715|Insert: Empty item
1716|Insert: Media files...
1717|Insert: New MIDI item...
1718|Insert: Time signature/tempo change marker
1719|Invert selection
1720|Item FX: Add FX to item take
1721|Item FX: Add FX to selected items
1722|Item FX: Add FX to selected take of selected items
1723|Item FX: Close FX chain for selected take
1724|Item FX: Close floating FX window(s) for selected take
1725|Item FX: Float FX for selected take
1726|Item FX: Show FX chain for item take
1727|Item FX: Show embedded UI for FX 1 for selected take
1728|Item FX: Show embedded UI for FX 2 for selected take
1729|Item FX: Show embedded UI for FX 3 for selected take
1730|Item FX: Show embedded UI for FX 4 for selected take
1731|Item FX: Show embedded UI for FX 5 for selected take
1732|Item FX: Show embedded UI for FX 6 for selected take
1733|Item FX: Show embedded UI for FX 7 for selected take
1734|Item FX: Show embedded UI for FX 8 for selected take
1735|Item FX: Show embedded UI for last touched FX for selected take
1736|Item FX: Toggle bypass all FX for selected take
1737|Item FX: Toggle bypass last FX for selected take
1738|Item FX: Toggle show embedded UI for FX 1 for selected take
1739|Item FX: Toggle show embedded UI for FX 2 for selected take
1740|Item FX: Toggle show embedded UI for FX 3 for selected take
1741|Item FX: Toggle show embedded UI for FX 4 for selected take
1742|Item FX: Toggle show embedded UI for FX 5 for selected take
1743|Item FX: Toggle show embedded UI for FX 6 for selected take
1744|Item FX: Toggle show embedded UI for FX 7 for selected take
1745|Item FX: Toggle show embedded UI for FX 8 for selected take
1746|Item FX: Toggle show embedded UI for last touched FX for selected take
1747|Item FX: Toggle show FX chain for selected take
1748|Item MIDI: Add stretch marker at mouse position
1749|Item MIDI: Add stretch marker at mouse position (snap to grid)
1750|Item MIDI: Delete stretch marker at mouse position
1751|Item MIDI: Delete stretch marker at mouse position (snap to grid)
1752|Item MIDI: Edit stretch marker at mouse position
1753|Item MIDI: Edit stretch marker rate at mouse position
1754|Item MIDI: Remove all stretch markers
1755|Item MIDI: Remove stretch markers preserving times and positions
1756|Item MIDI: Reset all MIDI banks/programs for selected items
1757|Item MIDI: Show/hide notation editor for selected items
1758|Item MIDI: Show/hide raw MIDI data
1759|Item MIDI: Transpose notes...
1760|Item colors: Set items to custom color...
1761|Item colors: Set items to default color
1762|Item colors: Set items to one random color per group
1763|Item colors: Set items to one random color per track
1764|Item colors: Set items to random colors
1765|Item edit: Change item group...
1766|Item edit: Change item lane under mouse cursor
1767|Item edit: Change item name...
1768|Item edit: Grow left edge of items
1769|Item edit: Grow right edge of items
1770|Item edit: Move contents of items left
1771|Item edit: Move contents of items left by grid size
1772|Item edit: Move contents of items right
1773|Item edit: Move contents of items right by grid size
1774|Item edit: Move items/envelope points down one track/a bit
1775|Item edit: Move items/envelope points left
1776|Item edit: Move items/envelope points left by grid size
1777|Item edit: Move items/envelope points right
1778|Item edit: Move items/envelope points right by grid size
1779|Item edit: Move items/envelope points up one track/a bit
1780|Item edit: Move position of item to edit cursor
1781|Item edit: Nudge item position left
1782|Item edit: Nudge item position left by grid
1783|Item edit: Nudge item position right
1784|Item edit: Nudge item position right by grid
1785|Item edit: Shrink left edge of items
1786|Item edit: Shrink right edge of items
1787|Item edit: Stretch item left/right (mousewheel/MIDI relative only)
1788|Item edit: Trim left edge of item to edit cursor
1789|Item edit: Trim right edge of item to edit cursor
1790|Item grouping: Create automatic grouping (auto-color/auto-name) for selected items
1791|Item grouping: Group items
1792|Item grouping: Remove items from group
1793|Item grouping: Select all items in groups
1794|Item lanes: Display playrate lane
1795|Item lanes: Hide playrate lane
1796|Item lanes: Toggle display playrate lane
1797|Item lanes: Toggle lane collapsed state
1798|Item lanes: Toggle lane collapsed state in selected tracks
1799|Item lanes: Uncollapse all lanes
1800|Item lanes: Uncollapse all lanes in selected tracks
1801|Item lanes: Uncollapse empty lanes
1802|Item lanes: Uncollapse empty lanes in selected tracks
1803|Item lanes: Unhide all lanes
1804|Item lanes: Unhide lane
1805|Item loudness: Calculate loudness of selected items via dry run render
1806|Item loudness: Normalize loudness of selected items to -23 LUFS
1807|Item loudness: Normalize loudness of selected items/takes...
1808|Item loudness: Show/hide item peak gain
1809|Item loudness: Show/hide item peak loudness
1810|Item loudness: Show/hide item short-term loudness
1811|Item loudness: Show/hide item true peak
1812|Item loudness: Toggle show item peak gain
1813|Item loudness: Toggle show item peak loudness
1814|Item loudness: Toggle show item short-term loudness
1815|Item loudness: Toggle show item true peak
1816|Item notes: Edit item notes
1817|Item notes: Show/hide item notes
1818|Item notes: Toggle show/hide item notes
1819|Item open: Open associated items in secondary project
1820|Item open: Open items in primary external editor
1821|Item open: Open items in secondary external editor
1822|Item open: Open items with built-in MIDI editor
1823|Item open: Open items with built-in MIDI editor, do not activate
1824|Item open: Open items with built-in MIDI editor, preserving existing editor contents
1825|Item open: Open items/associated project in new project tab
1826|Item preview: Preview item (toggle play/stop)
1827|Item preview: Preview selected media item through track (preview existing routing/FX)
1828|Item preview: Preview selected media item through track (preview existing routing/FX), auto-advance to next
1829|Item preview: Preview selected media item/track (toggle play/stop)
1830|Item preview: Preview selected media item/track (toggle play/stop), auto-advance to next
1831|Item properties: Adjust item playrate by semitones and cents (mousewheel/MIDI CC only)
1832|Item properties: Adjust take pan (mousewheel/MIDI CC only)
1833|Item properties: Adjust take pitch by semitones (mousewheel/MIDI CC only)
1834|Item properties: Adjust take volume (mousewheel/MIDI CC only)
1835|Item properties: Adjust take volume by dB (mousewheel/MIDI CC only)
1836|Item properties: Auto-trim/split items...
1837|Item properties: Clear item take name
1838|Item properties: Decrease pitch shift one cent
1839|Item properties: Decrease pitch shift one semitone
1840|Item properties: Increase pitch shift one cent
1841|Item properties: Increase pitch shift one semitone
1842|Item properties: Item play rate from user-supplied BPM...
1843|Item properties: Loop item source
1844|Item properties: Loop item source (toggle)
1845|Item properties: Mute
1846|Item properties: Mute (toggle)
1847|Item properties: Normalize items
1848|Item properties: Normalize multiple items to common gain
1849|Item properties: Normalize multiple items to integrated loudness...
1850|Item properties: Pitch item down one cent
1851|Item properties: Pitch item down one octave
1852|Item properties: Pitch item down one semitone
1853|Item properties: Pitch item up one cent
1854|Item properties: Pitch item up one octave
1855|Item properties: Pitch item up one semitone
1856|Item properties: Position from user-supplied timecode...
1857|Item properties: Preserve pitch when changing rate
1858|Item properties: Preserve pitch when changing rate (toggle)
1859|Item properties: Reset pitch
1860|Item properties: Reverse items as new take
1861|Item properties: Reverse items to new take
1862|Item properties: Set all takes channel mode to mono 1
1863|Item properties: Set all takes channel mode to mono 1+2
1864|Item properties: Set all takes channel mode to mono 2
1865|Item properties: Set all takes channel mode to mono bottom of stereo
1866|Item properties: Set all takes channel mode to mono left
1867|Item properties: Set all takes channel mode to mono mix
1868|Item properties: Set all takes channel mode to mono right
1869|Item properties: Set all takes channel mode to normal
1870|Item properties: Set all takes channel mode to reverse stereo
1871|Item properties: Set all takes channel mode to stereo
1872|Item properties: Set all takes channel mode to top of stereo
1873|Item properties: Set item channel mode to mono 1
1874|Item properties: Set item channel mode to mono 1+2
1875|Item properties: Set item channel mode to mono 2
1876|Item properties: Set item channel mode to mono bottom of stereo
1877|Item properties: Set item channel mode to mono left
1878|Item properties: Set item channel mode to mono mix
1879|Item properties: Set item channel mode to mono right
1880|Item properties: Set item channel mode to normal
1881|Item properties: Set item channel mode to reverse stereo
1882|Item properties: Set item channel mode to stereo
1883|Item properties: Set item channel mode to top of stereo
1884|Item properties: Set item color to custom color...
1885|Item properties: Set item color to default
1886|Item properties: Set item color to random colors
1887|Item properties: Set item play rate to 0.25x (one quarter speed)
1888|Item properties: Set item play rate to 0.5x (half speed)
1889|Item properties: Set item play rate to 1.0 (normal speed)
1890|Item properties: Set item play rate to 2.0x (double speed)
1891|Item properties: Set item play rate to 4.0x (quadruple speed)
1892|Item properties: Set item playback start offset...
1893|Item properties: Set take channel mode to mono 1
1894|Item properties: Set take channel mode to mono 1+2
1895|Item properties: Set take channel mode to mono 2
1896|Item properties: Set take channel mode to mono bottom of stereo
1897|Item properties: Set take channel mode to mono left
1898|Item properties: Set take channel mode to mono mix
1899|Item properties: Set take channel mode to mono right
1900|Item properties: Set take channel mode to normal
1901|Item properties: Set take channel mode to reverse stereo
1902|Item properties: Set take channel mode to stereo
1903|Item properties: Set take channel mode to top of stereo
1904|Item properties: Set take color to custom color...
1905|Item properties: Set take color to default
1906|Item properties: Set take color to random colors
1907|Item properties: Show media item/take properties
1908|Item properties: Take channel mode (mono/stereo)
1909|Item properties: Toggle item in-project MIDI
1910|Item properties: Toggle item mute
1911|Item properties: Toggle item play all takes
1912|Item properties: Toggle item/take preserve pitch when changing rate
1913|Item properties: Toggle loop source
1914|Item properties: Toggle take mute
1915|Item properties: Toggle take preserve pitch
1916|Item properties: Toggle take reverse
1917|Item settings: Copy all media into project directory...
1918|Item settings: Copy selected area of items
1919|Item settings: Crop to active take
1920|Item settings: Duplicate active take
1921|Item settings: Glue items
1922|Item settings: Glue items, ignoring time selection
1923|Item settings: Implode items across tracks into takes
1924|Item settings: Implode items on same track into takes
1925|Item settings: Import item media cues as project markers
1926|Item settings: Import item media cues as project regions
1927|Item settings: Item settings: Loop source
1928|Item settings: Loop source (toggle)
1929|Item settings: Open items in editor
1930|Item settings: Open items in primary external editor
1931|Item settings: Open items in secondary external editor
1932|Item settings: Paste
1933|Item settings: Quantize items using last quantize dialog settings...
1934|Item settings: Quantize items...
1935|Item settings: Remove all takes from items (prompt to save unused takes)
1936|Item settings: Remove content (trim) behind items
1937|Item settings: Reset item pitch
1938|Item settings: Reverse active take
1939|Item settings: Set item end to end of source media
1940|Item settings: Set item end to source media end
1941|Item settings: Set item timebase to beats (position only)
1942|Item settings: Set item timebase to beats (position, length, rate)
1943|Item settings: Set item timebase to default project/item timebase setting
1944|Item settings: Set item timebase to time
1945|Item settings: Shift items contents (moving media without changing start position in source media)
1946|Item settings: Show media item source properties
1947|Item settings: Split items at edit or play cursor
1948|Item settings: Split items at edit or play cursor (ignoring grouping)
1949|Item settings: Split items at time selection
1950|Item settings: Split items at time selection (ignoring grouping)
1951|Item settings: Take lane down (smallest shown)
1952|Item settings: Take lane up (smallest shown)
1953|Item settings: Trim content behind items
1954|Item settings: Trim left edge of item to edit cursor
1955|Item settings: Trim right edge of item to edit cursor
1956|Item: Add stretch markers at project tempo changes
1957|Item: Add stretch markers at time selection edges
1958|Item: Add stretch markers to items
1959|Item: Adjust take pan (mousewheel/MIDI CC only)
1960|Item: Adjust take pitch by semitones (mousewheel/MIDI CC only)
1961|Item: Adjust take volume (mousewheel/MIDI CC only)
1962|Item: Adjust take volume by dB (mousewheel/MIDI CC only)
1963|Item: Apply FX to items (mono output)
1964|Item: Apply track/take FX to items
1965|Item: Apply track/take FX to items (mono output)
1966|Item: Apply track/take FX to items (multichannel output)
1967|Item: Auto trim/split items (remove silence)...
1968|Item: Auto-trim/split items...
1969|Item: Clear take preserve pitch
1970|Item: Close item inline editors
1971|Item: Collapse empty take lanes
1972|Item: Copy items
1973|Item: Copy selected area of items
1974|Item: Cut items
1975|Item: Cut selected area of items
1976|Item: Cycle through take FX
1977|Item: Duplicate items
1978|Item: Duplicate selected area of items
1979|Item: Dynamic split items...
1980|Item: Explode multichannel audio or MIDI to new mono items
1981|Item: Explode multichannel audio or MIDI to new one-channel items
1982|Item: Explode multichannel items in place
1983|Item: Explode multichannel items in place (new items)
1984|Item: Explode multichannel items to new items
1985|Item: Explode takes of items across tracks
1986|Item: Explode takes of items in order
1987|Item: Explode takes of items in place
1988|Item: Fit to active take
1989|Item: Fit to all takes
1990|Item: Fit to item
1991|Item: Force offline
1992|Item: Force online
1993|Item: Glue items
1994|Item: Glue items, ignoring time selection
1995|Item: Glue items, ignoring time selection, including leading fade-in and trailing fade-out
1996|Item: Heal splits in items
1997|Item: Implode items across tracks into items on one track
1998|Item: Implode items across tracks into takes
1999|Item: Implode items on same track into takes
2000|Item: Increase pitch shift one cent
2001|Item: Increase pitch shift one semitone
2002|Item: Insert empty item
2003|Item: Insert empty space at time selection (remove time)
2004|Item: Insert empty space from cursor to start of project (moving later items)
2005|Item: Insert media item from clipboard
2006|Item: Insert note ignoring scale/key
2007|Item: Insert time signature marker
2008|Item: Invert phase
2009|Item: Load take active channels from user-supplied channel count...
2010|Item: Loop section of audio items
2011|Item: Make mono items stereo by copying first channel to second
2012|Item: Mute items
2013|Item: Nudge item pitch down a cent
2014|Item: Nudge item pitch down a semitone
2015|Item: Nudge item pitch up a cent
2016|Item: Nudge item pitch up a semitone
2017|Item: Nudge/set...
2018|Item: Open associated project in new tab
2019|Item: Open in built-in MIDI editor
2020|Item: Open in inline editors
2021|Item: Open in primary external editor
2022|Item: Open in secondary external editor
2023|Item: Open item copies in primary external editor
2024|Item: Open item copies in secondary external editor
2025|Item: Open items in editor
2026|Item: Open items in primary external editor
2027|Item: Open items in secondary external editor
2028|Item: Open source file
2029|Item: Paste items
2030|Item: Pitch down one cent
2031|Item: Pitch down one octave
2032|Item: Pitch down one semitone
2033|Item: Pitch up one cent
2034|Item: Pitch up one octave
2035|Item: Pitch up one semitone
2036|Item: Quantize items positions and rates to nearest tempo marker
2037|Item: Reduce number of playrate envelope points
2038|Item: Reduce overlaps
2039|Item: Remove all stretch markers
2040|Item: Remove content (trim) behind items
2041|Item: Remove items
2042|Item: Remove stretch marker at current position
2043|Item: Remove stretch markers from time selection
2044|Item: Remove time selection
2045|Item: Rename take
2046|Item: Rename take and source file
2047|Item: Reposition stretch markers in items
2048|Item: Reset item pitch
2049|Item: Reset take volume to 0dB (unity)
2050|Item: Restore previous play rate
2051|Item: Reverse active take
2052|Item: Reverse items to new take
2053|Item: Rotate backward through channel modes
2054|Item: Rotate forward through channel modes
2055|Item: Rotate take lanes backward
2056|Item: Rotate take lanes forward
2057|Item: Select all items
2058|Item: Select all items in current time signature
2059|Item: Select all items in track
2060|Item: Select all items on selected tracks in current time selection
2061|Item: Select all items with same source media
2062|Item: Select item under mouse
2063|Item: Set all media offline
2064|Item: Set all media online
2065|Item: Set all takes preserve pitch
2066|Item: Set cursor to end of items
2067|Item: Set cursor to start of items
2068|Item: Set item end to cursor
2069|Item: Set item end to source media end
2070|Item: Set item group 1
2071|Item: Set item group 10
2072|Item: Set item group 11
2073|Item: Set item group 12
2074|Item: Set item group 13
2075|Item: Set item group 14
2076|Item: Set item group 15
2077|Item: Set item group 16
2078|Item: Set item group 17
2079|Item: Set item group 18
2080|Item: Set item group 19
2081|Item: Set item group 2
2082|Item: Set item group 20
2083|Item: Set item group 21
2084|Item: Set item group 22
2085|Item: Set item group 23
2086|Item: Set item group 24
2087|Item: Set item group 25
2088|Item: Set item group 26
2089|Item: Set item group 27
2090|Item: Set item group 28
2091|Item: Set item group 29
2092|Item: Set item group 3
2093|Item: Set item group 30
2094|Item: Set item group 31
2095|Item: Set item group 32
2096|Item: Set item group 33
2097|Item: Set item group 34
2098|Item: Set item group 35
2099|Item: Set item group 36
2100|Item: Set item group 37
2101|Item: Set item group 38
2102|Item: Set item group 39
2103|Item: Set item group 4
2104|Item: Set item group 40
2105|Item: Set item group 41
2106|Item: Set item group 42
2107|Item: Set item group 43
2108|Item: Set item group 44
2109|Item: Set item group 45
2110|Item: Set item group 46
2111|Item: Set item group 47
2112|Item: Set item group 48
2113|Item: Set item group 49
2114|Item: Set item group 5
2115|Item: Set item group 50
2116|Item: Set item group 51
2117|Item: Set item group 52
2118|Item: Set item group 53
2119|Item: Set item group 54
2120|Item: Set item group 55
2121|Item: Set item group 56
2122|Item: Set item group 57
2123|Item: Set item group 58
2124|Item: Set item group 59
2125|Item: Set item group 6
2126|Item: Set item group 60
2127|Item: Set item group 61
2128|Item: Set item group 62
2129|Item: Set item group 63
2130|Item: Set item group 64
2131|Item: Set item group 7
2132|Item: Set item group 8
2133|Item: Set item group 9
2134|Item: Set item play rate to 1.0
2135|Item: Set item timebase to beats (position only)
2136|Item: Set item timebase to beats (position, length, rate)
2137|Item: Set item timebase to default project/item timebase setting
2138|Item: Set item timebase to time
2139|Item: Set new take channel mode to mono 1
2140|Item: Set new take channel mode to mono 1+2
2141|Item: Set new take channel mode to mono 2
2142|Item: Set new take channel mode to mono bottom of stereo
2143|Item: Set new take channel mode to mono left
2144|Item: Set new take channel mode to mono mix
2145|Item: Set new take channel mode to mono right
2146|Item: Set new take channel mode to normal
2147|Item: Set new take channel mode to reverse stereo
2148|Item: Set new take channel mode to stereo
2149|Item: Set new take channel mode to top of stereo
2150|Item: Set preserve pitch
2151|Item: Set selected items play rate to 0.25x (one quarter speed)
2152|Item: Set selected items play rate to 0.5x (half speed)
2153|Item: Set selected items play rate to 1.0 (normal speed)
2154|Item: Set selected items play rate to 2.0x (double speed)
2155|Item: Set selected items play rate to 4.0x (quadruple speed)
2156|Item: Set snap offset to cursor
2157|Item: Set take preserve pitch
2158|Item: Shift items contents left (moving loop section contents)
2159|Item: Shift items contents right (moving loop section contents)
2160|Item: Show media item/take properties
2161|Item: Show notes for items...
2162|Item: Show take envelopes
2163|Item: Solo items
2164|Item: Split items at edit cursor (no change selection)
2165|Item: Split items at edit or play cursor
2166|Item: Split items at edit or play cursor (ignoring grouping)
2167|Item: Split items at project markers
2168|Item: Split items at time selection
2169|Item: Split items at time selection (ignoring grouping)
2170|Item: Split items at transients
2171|Item: Split items under edit or play cursor
2172|Item: Split items under time selection
2173|Item: Toggle item grouping and track media/razor edit grouping
2174|Item: Toggle item solo
2175|Item: Toggle lock
2176|Item: Toggle mute
2177|Item: Toggle solo for item
2178|Item: Toggle take FX bypass
2179|Item: Toggle take envelope
2180|Item: Toggle take mute envelope
2181|Item: Toggle take pan envelope
2182|Item: Toggle take pitch envelope
2183|Item: Toggle take preserve pitch
2184|Item: Toggle take reverse
2185|Item: Toggle take volume envelope
2186|Item: Trim items left of cursor
2187|Item: Trim items right of cursor
2188|Item: Trim items to selected area
2189|Item: Uncollapse empty take lanes
2190|Item: Unmute items
2191|Item: Unsolo items
2192|JS: Adjust last touched FX parameter (MIDI CC/OSC only)
2193|JS: Adjust track send 1 pan (MIDI CC/OSC only)
2194|JS: Adjust track send 1 volume (MIDI CC/OSC only)
2195|JS: Adjust track send 2 pan (MIDI CC/OSC only)
2196|JS: Adjust track send 2 volume (MIDI CC/OSC only)
2197|JS: Adjust track send 3 pan (MIDI CC/OSC only)
2198|JS: Adjust track send 3 volume (MIDI CC/OSC only)
2199|JS: Adjust track send 4 pan (MIDI CC/OSC only)
2200|JS: Adjust track send 4 volume (MIDI CC/OSC only)
2201|JS: Adjust track send 5 pan (MIDI CC/OSC only)
2202|JS: Adjust track send 5 volume (MIDI CC/OSC only)
2203|JS: Adjust track send 6 pan (MIDI CC/OSC only)
2204|JS: Adjust track send 6 volume (MIDI CC/OSC only)
2205|JS: Adjust track send 7 pan (MIDI CC/OSC only)
2206|JS: Adjust track send 7 volume (MIDI CC/OSC only)
2207|JS: Adjust track send 8 pan (MIDI CC/OSC only)
2208|JS: Adjust track send 8 volume (MIDI CC/OSC only)
2209|JS: Toggle FX bypass for last touched FX
2210|JS: Toggle FX bypass for master track
2211|JS: Toggle FX bypass on all tracks
2212|JS: Toggle floating windows
2213|JS: Toggle master track mono/stereo
2214|JS: Toggle master track mute
2215|JS: Toggle master track solo
2216|JS: Toggle mute for last touched track
2217|JS: Toggle mute for master track
2218|JS: Toggle mute for selected tracks
2219|JS: Toggle pan reverse for last touched track
2220|JS: Toggle pan reverse for master track
2221|JS: Toggle pan reverse for selected tracks
2222|JS: Toggle solo for last touched track
2223|JS: Toggle solo for master track
2224|JS: Toggle solo for selected tracks
2225|JS: Toggle solo in front for last touched track
2226|JS: Toggle solo in front for master track
2227|JS: Toggle solo in front for selected tracks
2228|JS: Toggle track FX bypass
2229|JS: Toggle track FX bypass on all tracks
2230|JS: Toggle track mute
2231|JS: Toggle track solo
2232|Key signature: Set project key signature from editor grid
2233|Key signature: Show/hide key signature changes
2234|Key: Delete selected notes if any, otherwise delete lyric events at cursor
2235|Key: Insert note at nearest C
2236|Key: Insert note at nearest C#/Db
2237|Key: Insert note at nearest D
2238|Key: Insert note at nearest D#/Eb
2239|Key: Insert note at nearest E
2240|Key: Insert note at nearest F
2241|Key: Insert note at nearest F#/Gb
2242|Key: Insert note at nearest G
2243|Key: Insert note at nearest G#/Ab
2244|Key: Set project key signature from editor grid
2245|Key: Show/hide key signature changes
2246|Keyboard: Delete all notes in measure at edit cursor
2247|Keyboard: Delete note at edit cursor
2248|Keyboard: Delete notes in measure at edit cursor
2249|Keyboard: Next octave
2250|Keyboard: Previous octave
2251|Lane: Add lane
2252|Lane: Collapse lane
2253|Lane: Delete lane
2254|Lane: Hide lane
2255|Lane: Play only highest lane
2256|Lane: Play only lane 1
2257|Lane: Play only lane 2
2258|Lane: Play only lane 3
2259|Lane: Play only lane 4
2260|Lane: Play only lane 5
2261|Lane: Play only lane 6
2262|Lane: Play only lane 7
2263|Lane: Play only lane 8
2264|Lane: Play only lane 9
2265|Lane: Play only lane 10
2266|Lane: Play only lane 11
2267|Lane: Play only lane 12
2268|Lane: Play only lane 13
2269|Lane: Play only lane 14
2270|Lane: Play only lane 15
2271|Lane: Play only lane 16
2272|Lane: Play only lane 17
2273|Lane: Play only lane 18
2274|Lane: Play only lane 19
2275|Lane: Play only lane 20
2276|Lane: Play only lane 21
2277|Lane: Play only lane 22
2278|Lane: Play only lane 23
2279|Lane: Play only lane 24
2280|Lane: Play only lane 25
2281|Lane: Play only lane 26
2282|Lane: Play only lane 27
2283|Lane: Play only lane 28
2284|Lane: Play only lane 29
2285|Lane: Play only lane 30
2286|Lane: Play only lane 31
2287|Lane: Play only lane 32
2288|Lane: Play only lane 33
2289|Lane: Play only lane 34
2290|Lane: Play only lane 35
2291|Lane: Play only lane 36
2292|Lane: Play only lane 37
2293|Lane: Play only lane 38
2294|Lane: Play only lane 39
2295|Lane: Play only lane 40
2296|Lane: Play only lane 41
2297|Lane: Play only lane 42
2298|Lane: Play only lane 43
2299|Lane: Play only lane 44
2300|Lane: Play only lane 45
2301|Lane: Play only lane 46
2302|Lane: Play only lane 47
2303|Lane: Play only lane 48
2304|Lane: Play only lane 49
2305|Lane: Play only lane 50
2306|Lane: Play only lane 51
2307|Lane: Play only lane 52
2308|Lane: Play only lane 53
2309|Lane: Play only lane 54
2310|Lane: Play only lane 55
2311|Lane: Play only lane 56
2312|Lane: Play only lane 57
2313|Lane: Play only lane 58
2314|Lane: Play only lane 59
2315|Lane: Play only lane 60
2316|Lane: Play only lane 61
2317|Lane: Play only lane 62
2318|Lane: Play only lane 63
2319|Lane: Play only lane 64
2320|Lane: Play only lane N
2321|Lane: Play only lane N-1
2322|Lane: Play only lane N-10
2323|Lane: Play only lane N-11
2324|Lane: Play only lane N-12
2325|Lane: Play only lane N-13
2326|Lane: Play only lane N-14
2327|Lane: Play only lane N-15
2328|Lane: Play only lane N-16
2329|Lane: Play only lane N-17
2330|Lane: Play only lane N-18
2331|Lane: Play only lane N-19
2332|Lane: Play only lane N-2
2333|Lane: Play only lane N-20
2334|Lane: Play only lane N-21
2335|Lane: Play only lane N-22
2336|Lane: Play only lane N-23
2337|Lane: Play only lane N-24
2338|Lane: Play only lane N-25
2339|Lane: Play only lane N-26
2340|Lane: Play only lane N-27
2341|Lane: Play only lane N-28
2342|Lane: Play only lane N-29
2343|Lane: Play only lane N-3
2344|Lane: Play only lane N-30
2345|Lane: Play only lane N-31
2346|Lane: Play only lane N-32
2347|Lane: Play only lane N-33
2348|Lane: Play only lane N-34
2349|Lane: Play only lane N-35
2350|Lane: Play only lane N-36
2351|Lane: Play only lane N-37
2352|Lane: Play only lane N-38
2353|Lane: Play only lane N-39
2354|Lane: Play only lane N-4
2355|Lane: Play only lane N-40
2356|Lane: Play only lane N-41
2357|Lane: Play only lane N-42
2358|Lane: Play only lane N-43
2359|Lane: Play only lane N-44
2360|Lane: Play only lane N-45
2361|Lane: Play only lane N-46
2362|Lane: Play only lane N-47
2363|Lane: Play only lane N-48
2364|Lane: Play only lane N-49
2365|Lane: Play only lane N-5
2366|Lane: Play only lane N-50
2367|Lane: Play only lane N-51
2368|Lane: Play only lane N-52
2369|Lane: Play only lane N-53
2370|Lane: Play only lane N-54
2371|Lane: Play only lane N-55
2372|Lane: Play only lane N-56
2373|Lane: Play only lane N-57
2374|Lane: Play only lane N-58
2375|Lane: Play only lane N-59
2376|Lane: Play only lane N-6
2377|Lane: Play only lane N-60
2378|Lane: Play only lane N-61
2379|Lane: Play only lane N-62
2380|Lane: Play only lane N-63
2381|Lane: Play only lane N-7
2382|Lane: Play only lane N-8
2383|Lane: Play only lane N-9
2384|Lane: Play only lowest lane
2385|Lane: Play only next lane
2386|Lane: Play only previous lane
2387|Lane: Rename lane
2388|Lane: Shuffle lanes down
2389|Lane: Shuffle lanes up
2390|Lane: Show all lanes
2391|Lane: Show only lane 1
2392|Lane: Show only lane 2
2393|Lane: Show only lane 3
2394|Lane: Show only lane 4
2395|Lane: Show only lane 5
2396|Lane: Show only lane 6
2397|Lane: Show only lane 7
2398|Lane: Show only lane 8
2399|Lane: Show only lane 9
2400|Lane: Show only lane 10
2401|Lane: Show only lane 11
2402|Lane: Show only lane 12
2403|Lane: Show only lane 13
2404|Lane: Show only lane 14
2405|Lane: Show only lane 15
2406|Lane: Show only lane 16
2407|Lane: Show only lane 17
2408|Lane: Show only lane 18
2409|Lane: Show only lane 19
2410|Lane: Show only lane 20
2411|Lane: Show only lane 21
2412|Lane: Show only lane 22
2413|Lane: Show only lane 23
2414|Lane: Show only lane 24
2415|Lane: Show only lane 25
2416|Lane: Show only lane 26
2417|Lane: Show only lane 27
2418|Lane: Show only lane 28
2419|Lane: Show only lane 29
2420|Lane: Show only lane 30
2421|Lane: Show only lane 31
2422|Lane: Show only lane 32
2423|Lane: Show only lane 33
2424|Lane: Show only lane 34
2425|Lane: Show only lane 35
2426|Lane: Show only lane 36
2427|Lane: Show only lane 37
2428|Lane: Show only lane 38
2429|Lane: Show only lane 39
2430|Lane: Show only lane 40
2431|Lane: Show only lane 41
2432|Lane: Show only lane 42
2433|Lane: Show only lane 43
2434|Lane: Show only lane 44
2435|Lane: Show only lane 45
2436|Lane: Show only lane 46
2437|Lane: Show only lane 47
2438|Lane: Show only lane 48
2439|Lane: Show only lane 49
2440|Lane: Show only lane 50
2441|Lane: Show only lane 51
2442|Lane: Show only lane 52
2443|Lane: Show only lane 53
2444|Lane: Show only lane 54
2445|Lane: Show only lane 55
2446|Lane: Show only lane 56
2447|Lane: Show only lane 57
2448|Lane: Show only lane 58
2449|Lane: Show only lane 59
2450|Lane: Show only lane 60
2451|Lane: Show only lane 61
2452|Lane: Show only lane 62
2453|Lane: Show only lane 63
2454|Lane: Show only lane 64
2455|Lane: Show only lane N
2456|Lane: Show only lane N-1
2457|Lane: Show only lane N-10
2458|Lane: Show only lane N-11
2459|Lane: Show only lane N-12
2460|Lane: Show only lane N-13
2461|Lane: Show only lane N-14
2462|Lane: Show only lane N-15
2463|Lane: Show only lane N-16
2464|Lane: Show only lane N-17
2465|Lane: Show only lane N-18
2466|Lane: Show only lane N-19
2467|Lane: Show only lane N-2
2468|Lane: Show only lane N-20
2469|Lane: Show only lane N-21
2470|Lane: Show only lane N-22
2471|Lane: Show only lane N-23
2472|Lane: Show only lane N-24
2473|Lane: Show only lane N-25
2474|Lane: Show only lane N-26
2475|Lane: Show only lane N-27
2476|Lane: Show only lane N-28
2477|Lane: Show only lane N-29
2478|Lane: Show only lane N-3
2479|Lane: Show only lane N-30
2480|Lane: Show only lane N-31
2481|Lane: Show only lane N-32
2482|Lane: Show only lane N-33
2483|Lane: Show only lane N-34
2484|Lane: Show only lane N-35
2485|Lane: Show only lane N-36
2486|Lane: Show only lane N-37
2487|Lane: Show only lane N-38
2488|Lane: Show only lane N-39
2489|Lane: Show only lane N-4
2490|Lane: Show only lane N-40
2491|Lane: Show only lane N-41
2492|Lane: Show only lane N-42
2493|Lane: Show only lane N-43
2494|Lane: Show only lane N-44
2495|Lane: Show only lane N-45
2496|Lane: Show only lane N-46
2497|Lane: Show only lane N-47
2498|Lane: Show only lane N-48
2499|Lane: Show only lane N-49
2500|Lane: Show only lane N-5
2501|Lane: Show only lane N-50
2502|Lane: Show only lane N-51
2503|Lane: Show only lane N-52
2504|Lane: Show only lane N-53
2505|Lane: Show only lane N-54
2506|Lane: Show only lane N-55
2507|Lane: Show only lane N-56
2508|Lane: Show only lane N-57
2509|Lane: Show only lane N-58
2510|Lane: Show only lane N-59
2511|Lane: Show only lane N-6
2512|Lane: Show only lane N-60
2513|Lane: Show only lane N-61
2514|Lane: Show only lane N-62
2515|Lane: Show only lane N-63
2516|Lane: Show only lane N-7
2517|Lane: Show only lane N-8
2518|Lane: Show only lane N-9
2519|Lane: Show only next lane
2520|Lane: Show only previous lane
2521|Lane: Toggle lane collapsed state
2522|Lane: Toggle lane collapsed state in selected tracks
2523|Lane: Toggle show all lanes
2524|Lane: Toggle show lane 1
2525|Lane: Toggle show lane 2
2526|Lane: Toggle show lane 3
2527|Lane: Toggle show lane 4
2528|Lane: Toggle show lane 5
2529|Lane: Toggle show lane 6
2530|Lane: Toggle show lane 7
2531|Lane: Toggle show lane 8
2532|Lane: Toggle show lane 9
2533|Lane: Toggle show lane 10
2534|Lane: Toggle show lane 11
2535|Lane: Toggle show lane 12
2536|Lane: Toggle show lane 13
2537|Lane: Toggle show lane 14
2538|Lane: Toggle show lane 15
2539|Lane: Toggle show lane 16
2540|Lane: Toggle show lane 17
2541|Lane: Toggle show lane 18
2542|Lane: Toggle show lane 19
2543|Lane: Toggle show lane 20
2544|Lane: Toggle show lane 21
2545|Lane: Toggle show lane 22
2546|Lane: Toggle show lane 23
2547|Lane: Toggle show lane 24
2548|Lane: Toggle show lane 25
2549|Lane: Toggle show lane 26
2550|Lane: Toggle show lane 27
2551|Lane: Toggle show lane 28
2552|Lane: Toggle show lane 29
2553|Lane: Toggle show lane 30
2554|Lane: Toggle show lane 31
2555|Lane: Toggle show lane 32
2556|Lane: Toggle show lane 33
2557|Lane: Toggle show lane 34
2558|Lane: Toggle show lane 35
2559|Lane: Toggle show lane 36
2560|Lane: Toggle show lane 37
2561|Lane: Toggle show lane 38
2562|Lane: Toggle show lane 39
2563|Lane: Toggle show lane 40
2564|Lane: Toggle show lane 41
2565|Lane: Toggle show lane 42
2566|Lane: Toggle show lane 43
2567|Lane: Toggle show lane 44
2568|Lane: Toggle show lane 45
2569|Lane: Toggle show lane 46
2570|Lane: Toggle show lane 47
2571|Lane: Toggle show lane 48
2572|Lane: Toggle show lane 49
2573|Lane: Toggle show lane 50
2574|Lane: Toggle show lane 51
2575|Lane: Toggle show lane 52
2576|Lane: Toggle show lane 53
2577|Lane: Toggle show lane 54
2578|Lane: Toggle show lane 55
2579|Lane: Toggle show lane 56
2580|Lane: Toggle show lane 57
2581|Lane: Toggle show lane 58
2582|Lane: Toggle show lane 59
2583|Lane: Toggle show lane 60
2584|Lane: Toggle show lane 61
2585|Lane: Toggle show lane 62
2586|Lane: Toggle show lane 63
2587|Lane: Toggle show lane 64
2588|Lane: Toggle show lane N
2589|Lane: Toggle show lane N-1
2590|Lane: Toggle show lane N-10
2591|Lane: Toggle show lane N-11
2592|Lane: Toggle show lane N-12
2593|Lane: Toggle show lane N-13
2594|Lane: Toggle show lane N-14
2595|Lane: Toggle show lane N-15
2596|Lane: Toggle show lane N-16
2597|Lane: Toggle show lane N-17
2598|Lane: Toggle show lane N-18
2599|Lane: Toggle show lane N-19
2600|Lane: Toggle show lane N-2
2601|Lane: Toggle show lane N-20
2602|Lane: Toggle show lane N-21
2603|Lane: Toggle show lane N-22
2604|Lane: Toggle show lane N-23
2605|Lane: Toggle show lane N-24
2606|Lane: Toggle show lane N-25
2607|Lane: Toggle show lane N-26
2608|Lane: Toggle show lane N-27
2609|Lane: Toggle show lane N-28
2610|Lane: Toggle show lane N-29
2611|Lane: Toggle show lane N-3
2612|Lane: Toggle show lane N-30
2613|Lane: Toggle show lane N-31
2614|Lane: Toggle show lane N-32
2615|Lane: Toggle show lane N-33
2616|Lane: Toggle show lane N-34
2617|Lane: Toggle show lane N-35
2618|Lane: Toggle show lane N-36
2619|Lane: Toggle show lane N-37
2620|Lane: Toggle show lane N-38
2621|Lane: Toggle show lane N-39
2622|Lane: Toggle show lane N-4
2623|Lane: Toggle show lane N-40
2624|Lane: Toggle show lane N-41
2625|Lane: Toggle show lane N-42
2626|Lane: Toggle show lane N-43
2627|Lane: Toggle show lane N-44
2628|Lane: Toggle show lane N-45
2629|Lane: Toggle show lane N-46
2630|Lane: Toggle show lane N-47
2631|Lane: Toggle show lane N-48
2632|Lane: Toggle show lane N-49
2633|Lane: Toggle show lane N-5
2634|Lane: Toggle show lane N-50
2635|Lane: Toggle show lane N-51
2636|Lane: Toggle show lane N-52
2637|Lane: Toggle show lane N-53
2638|Lane: Toggle show lane N-54
2639|Lane: Toggle show lane N-55
2640|Lane: Toggle show lane N-56
2641|Lane: Toggle show lane N-57
2642|Lane: Toggle show lane N-58
2643|Lane: Toggle show lane N-59
2644|Lane: Toggle show lane N-6
2645|Lane: Toggle show lane N-60
2646|Lane: Toggle show lane N-61
2647|Lane: Toggle show lane N-62
2648|Lane: Toggle show lane N-63
2649|Lane: Toggle show lane N-7
2650|Lane: Toggle show lane N-8
2651|Lane: Toggle show lane N-9
2652|Lane: Uncollapse all lanes
2653|Lane: Uncollapse all lanes in selected tracks
2654|Lane: Uncollapse empty lanes
2655|Lane: Uncollapse empty lanes in selected tracks
2656|Lane: Unhide all lanes
2657|Lane: Unhide lane
2658|Locking: Clear all lock modes
2659|Locking: Disable locking
2660|Locking: Enable locking
2661|Locking: Full item locking mode
2662|Locking: Set active take locking mode
2663|Locking: Set active take envelope locking mode
2664|Locking: Set all lock modes
2665|Locking: Set envelope locking mode
2666|Locking: Set item edges locking mode
2667|Locking: Set item fades locking mode
2688|Locking: Set item locking mode
2669|Locking: Set item position locking mode
2670|Locking: Set left/right item locking mode
2671|Locking: Set loop points locking mode
2672|Locking: Set razor edits locking mode
2673|Locking: Set region locking mode
2674|Locking: Set stretch marker locking mode
2675|Locking: Set take locking mode
2676|Locking: Set time selection locking mode
2677|Locking: Set time signature marker locking mode
2678|Locking: Set track envelope locking mode
2679|Locking: Set up/down item locking mode
2680|Locking: Toggle active take locking mode
2681|Locking: Toggle active take envelope locking mode
2682|Locking: Toggle all lock modes
2683|Locking: Toggle envelope locking mode
2684|Locking: Toggle full item locking mode
2685|Locking: Toggle item edges locking mode
2686|Locking: Toggle item fades locking mode
2687|Locking: Toggle item locking mode
2688|Locking: Toggle item position locking mode
2689|Locking: Toggle left/right item locking mode
2690|Locking: Toggle loop points locking mode
2691|Locking: Toggle razor edits locking mode
2692|Locking: Toggle region locking mode
2693|Locking: Toggle stretch marker locking mode
2694|Locking: Toggle take locking mode
2695|Locking: Toggle time selection locking mode
2696|Locking: Toggle time signature marker locking mode
2697|Locking: Toggle track envelope locking mode
2698|Locking: Toggle up/down item locking mode
2699|Loop points: Double loop length
2700|Loop points: Halve loop length
2701|Loop points: Move end point to cursor (preserve length)
2702|Loop points: Move start point to cursor (preserve length)
2703|Loop points: Remove (unselect) loop point selection
2704|Loop points: Remove (unselect) loop points, if not linked to time selection, ignoring lock state
2705|Loop points: Remove loop points
2706|Loop points: Set end point
2707|Loop points: Set loop points to items
2708|Loop points: Set start point
2709|Loop: Double loop length
2710|Loop: Halve loop length
2711|MIDI: Clear retroactive MIDI history
2712|MIDI: Insert all available retroactively recorded MIDI for armed and selected tracks
2713|MIDI: Insert all available retroactively recorded MIDI for armed tracks
2714|MIDI: Insert recent retroactively recorded MIDI for armed and selected tracks
2715|MIDI: Insert recent retroactively recorded MIDI for armed tracks
2716|MIDI: Reload track support data (bank/program files, notation, etc) for all MIDI items on selected tracks
2717|Main action section: Clear any override
2718|Main action section: Momentarily set override to alt-1
2719|Main action section: Momentarily set override to alt-10
2720|Main action section: Momentarily set override to alt-11
2721|Main action section: Momentarily set override to alt-12
2722|Main action section: Momentarily set override to alt-13
2723|Main action section: Momentarily set override to alt-14
2724|Main action section: Momentarily set override to alt-15
2725|Main action section: Momentarily set override to alt-16
2726|Main action section: Momentarily set override to alt-2
2727|Main action section: Momentarily set override to alt-3
2728|Main action section: Momentarily set override to alt-4
2729|Main action section: Momentarily set override to alt-5
2730|Main action section: Momentarily set override to alt-6
2731|Main action section: Momentarily set override to alt-7
2732|Main action section: Momentarily set override to alt-8
2733|Main action section: Momentarily set override to alt-9
2734|Main action section: Momentarily set override to default
2735|Main action section: Momentarily set override to recording
2736|Main action section: Set override to default
2737|Main action section: Toggle override to alt-1
2738|Main action section: Toggle override to alt-10
2739|Main action section: Toggle override to alt-11
2740|Main action section: Toggle override to alt-12
2741|Main action section: Toggle override to alt-13
2742|Main action section: Toggle override to alt-14
2743|Main action section: Toggle override to alt-15
2744|Main action section: Toggle override to alt-16
2745|Main action section: Toggle override to alt-2
2746|Main action section: Toggle override to alt-3
2747|Main action section: Toggle override to alt-4
2748|Main action section: Toggle override to alt-5
2749|Main action section: Toggle override to alt-6
2750|Main action section: Toggle override to alt-7
2751|Main action section: Toggle override to alt-8
2752|Main action section: Toggle override to alt-9
2753|Main action section: Toggle override to recording
2754|Markers/Regions: Export markers/regions to file
2755|Markers/Regions: Import markers/regions from file (merge with existing)
2756|Markers/Regions: Import markers/regions from file (replace existing)
2757|Markers: Add/move marker 1 to play/edit cursor
2758|Markers: Add/move marker 10 to play/edit cursor
2759|Markers: Add/move marker 2 to play/edit cursor
2760|Markers: Add/move marker 3 to play/edit cursor
2761|Markers: Add/move marker 4 to play/edit cursor
2762|Markers: Add/move marker 5 to play/edit cursor
2763|Markers: Add/move marker 6 to play/edit cursor
2764|Markers: Add/move marker 7 to play/edit cursor
2765|Markers: Add/move marker 8 to play/edit cursor
2766|Markers: Add/move marker 9 to play/edit cursor
2767|Markers: Change color for marker near cursor...
2768|Markers: Change color for region near cursor...
2769|Markers: Delete marker near cursor
2770|Markers: Delete region near cursor
2771|Markers: Delete time signature marker near cursor
2772|Markers: Edit marker near cursor
2773|Markers: Edit region near cursor
2774|Markers: Edit time signature marker near cursor
2775|Markers: Go to marker 01
2776|Markers: Go to marker 02
2777|Markers: Go to marker 03
2778|Markers: Go to marker 04
2779|Markers: Go to marker 05
2780|Markers: Go to marker 06