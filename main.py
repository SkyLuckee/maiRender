"""Entry point: opens a window, loads a chart, and plays back the note animation."""
import sys

import pyglet

import config
from chart import load_chart
from note_renderer import NoteRenderer, load_note_images

# Sprite filenames in config.py are resolved relative to this path.
pyglet.resource.path = [config.ASSET_DIR]
pyglet.resource.reindex()

window = pyglet.window.Window(config.WIDTH, config.HEIGHT, caption="maimai renderer")
win_x, win_y = window.get_location()
window.set_location(win_x - 60, win_y - 60)

batch = pyglet.graphics.Batch()

# Judgment ring sprite, created once and reused (not recreated every frame).
ring_image = pyglet.resource.image("outline.png")
ring_image.anchor_x = ring_image.width // 2
ring_image.anchor_y = ring_image.height // 2
ring_sprite = pyglet.sprite.Sprite(ring_image, x=config.CENTER_X, y=config.CENTER_Y, batch=batch)

elapsed = 0.0
renderer: NoteRenderer | None = None

def update(dt: float) -> None:
    global elapsed
    elapsed += dt
    renderer.update(elapsed)


@window.event
def on_draw():
    window.clear()
    batch.draw()


def main(chart_path: str) -> None:
    global renderer
    chart = load_chart(chart_path)
    print(f"Loaded {chart.title} [{chart.difficulty} {chart.level}] - {len(chart.notes)} notes")
    images = load_note_images()
    renderer = NoteRenderer(chart.notes, batch, images)
    pyglet.clock.schedule_interval(update, 1 / config.FPS)
    pyglet.app.run()


if __name__ == "__main__":
    chart_path = sys.argv[1] if len(sys.argv) > 1 else "maigraph_MASTER.json"
    main(chart_path)
