# maiRender

maimai chart-visualizer project using pyglet.
Takes a JSON chart export and animates notes approaching a judgment ring.
Powered using shitcode and AI

## File structure
- `config.py` - window size, timing constants, ring/lane geometry and sprite dict
- `chart.py` - loads a chart JSON, flattens it into a sorted `list[Note]`
- `note_renderer.py` - owns the on-screen shapes, updates positions each frame
- `main.py` - window setup, clock loop, pause control, chart loading, wires everything together ...
- `slide_path.py` - dedicated script for slide generation
- `slide_render.py` - star head, "tracer star", movement, and opacity logic 
- `tap_render.py` - dedicated script for tap generation, reused to also generate star head
- `hold_render.py` - dedicated script for hold note
- `render_common.py` - common function for note generation
- `compound_slide_path.py` - dedicated script to handle compound slide

## How to use
Put your chart.json and track.mp3 into the same folder. Run the script and choose the json.
**TODO:** add a wrapper so the script can read txt directly

## Status
Basic feature
- [x] audio playback / sync and pause control
- [ ] video export
- [ ] sound effects
- [ ] background video

STD Feature
- [x] tap, break, star head
- [x] hold note
- [ ] slide (missing wifi slide rn)

DX Feature
- [x] touch note
- [x] compound slide
- [ ] hanabi

Other?
- [ ] HS, SV