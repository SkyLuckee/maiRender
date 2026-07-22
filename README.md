# maiRender

maimai chart-visualizer project.
Takes a JSON chart export (flattened `timingList`) and animates notes approaching a judgment ring.
Powered using shitcode and AI

## Layout

- `config.py` - window size, timing constants, ring/lane geometry
- `chart.py` - loads a chart JSON, flattens it into a sorted `list[Note]`
- `renderer.py` - owns the on-screen shapes, updates positions each frame
- `main.py` - window setup, clock loop, wires everything together
- `slide_path.py` - dedicated script for slide generation

## Sprites

Notes render as `pyglet.sprite.Sprite` objects loaded from `assets/`.
Images are loaded once via `pyglet.resource` (see `load_note_images()` in `renderer.py`) and reused for the life of each note.

## Status

**TODO**
- [ ] audio playback / sync
- [ ] ppqq , w slide
- [ ] video export
- [ ] touch note
- [ ] compound slide
- [ ] hanabi