"""Entry point: opens a window, loads a chart, and plays back the note animation."""
import os
import tkinter as tk
from tkinter import filedialog

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

# a label to show elapsed time
elapsed_label = pyglet.text.Label(
    text="0.00",
    font_name="Times New Roman",
    font_size=24,
    x=50,
    y=50,
    anchor_x="left",
    anchor_y="center",
    color=(255, 255, 255, 255),
    batch=batch
)

# shown only while paused
paused_label = pyglet.text.Label(
    text="PAUSED",
    font_name="Times New Roman",
    font_size=24,
    x=50,
    y=85,
    anchor_x="left",
    anchor_y="center",
    color=(255, 80, 80, 255),
    batch=batch,
)
paused_label.visible = False
paused = False

player: pyglet.media.Player | None = None
def update(dt: float) -> None:
    global renderer, player

    if player is None or paused:
        return
    current_time = player.time

    renderer.update(current_time)
    elapsed_label.text = f"{current_time:.3f}"

def toggle_pause() -> None:
    """pauses the audio player itself (not just the render loop),
    since renderer.update() reads player.time directly as its clock ..."""
    global paused
    if player is None:
        return
    paused = not paused
    if paused:
        player.pause()
    else:
        player.play()
    paused_label.visible = paused

@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.SPACE:
        toggle_pause()


@window.event
def on_draw():
    window.clear()
    batch.draw()

def prompt_for_file():
    """Opens a file picker dialog and returns the selected path, or '' if cancelled."""
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select maidata.txt",
        initialdir=config.TEST_DIR,
        filetypes=[("Json files", "*.json"), ("All files", "*.*")],
    )
    root.destroy()
    return path


def main(chart_path: str) -> None:
    global renderer, player
    chart = load_chart(chart_path)
    print(f"Loaded {chart.title} [{chart.difficulty} {chart.level}] - {len(chart.notes)} notes")
    images = load_note_images()

    # auto find the track.mp3 in the json directory
    folder = os.path.dirname(chart_path)
    track_path = os.path.join(folder, "track.mp3")

    if not os.path.exists(track_path):
        print(f"Warning: No track.mp3 found in {folder}")
        return

    # Load and play the music
    music = pyglet.media.load(track_path, streaming=True)
    player = pyglet.media.Player()
    player.queue(music)
    player.loop = False
    player.volume = config.TRACK_VOLUME
    player.play()

    renderer = NoteRenderer(chart.notes, batch, images)
    pyglet.clock.schedule_interval(update, 1 / config.FPS)
    pyglet.app.run()


if __name__ == "__main__":
    chart_path = prompt_for_file()
    main(chart_path)
