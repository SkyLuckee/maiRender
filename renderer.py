"""Drawing logic for the chart renderer: turns Note objects + elapsed time into on-screen sprites."""
import math
import pyglet

import config
from chart import Note
from slide_path import build_path

def _face_center_rotation(position: int) -> float:
    """Sprite rotation (degrees, clockwise) facing inward."""
    return 90 - math.degrees(config.lane_angle(position))

def _point_along_path(path, progress: float) -> tuple[float, float]:
    """Interpolate a point along `path` at fraction `progress` (0-1)."""
    progress = max(0.0, min(1.0, progress))
    scaled = progress * (len(path) - 1)
    i = int(scaled)
    if i >= len(path) - 1:
        x, y, _ = path[-1]
        return x, y
    frac = scaled - i
    x0, y0, _ = path[i]
    x1, y1, _ = path[i + 1]
    return x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac

def _cumulative_lengths(path) -> list[float]:
    """Running arc-length total up to each point in `path`."""
    lengths = [0.0]
    for i in range(1, len(path)):
        x0, y0, _ = path[i - 1]
        x1, y1, _ = path[i]
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    return lengths

def _sample_at_distance(path, lengths, dist: float) -> tuple[float, float, float]:
    """Return (x, y, tangent_angle_degrees) at arc-length `dist` along `path`."""
    i = next((i for i in range(1, len(lengths)) if lengths[i] >= dist), len(lengths) - 1)
    x0, y0, angle = path[i - 1]
    x1, y1, _ = path[i]
    seg_len = lengths[i] - lengths[i - 1]
    frac = 0.0 if seg_len == 0 else max(0.0, min(1.0, (dist - lengths[i - 1]) / seg_len))
    x = x0 + (x1 - x0) * frac
    y = y0 + (y1 - y0) * frac
    return x, y, angle

def _arrow_placements(path, spacing: float):
    """Evenly-spaced (x, y, angle) triples along `path`, `spacing` pixels apart.

    Stops before placing one that would land closer than half a spacing to
    the endpoint, so the last arrow never crowds the slide's end.
    """
    lengths = _cumulative_lengths(path)
    total = lengths[-1]
    placements = []
    dist = 0.0
    while total - dist >= spacing / 2:
        placements.append(_sample_at_distance(path, lengths, dist))
        dist += spacing
    # print(placements)
    return placements, total

class _SlideBody:
    """A chain of arrow sprites tracing one slide's path, revealed progressively."""
    def __init__(self, note, image, batch):
        self.path = build_path(note.position, note.slide_waypoints or [], note.slide_shape or "-")
        placements, self.total_length = _arrow_placements(self.path, config.ARROW_SPACING)
        self.sprites = []
        self.distances = [i * config.ARROW_SPACING for i in range(len(placements))]
        for x, y, angle in placements:
            sprite = pyglet.sprite.Sprite(image, x=x, y=y, batch=batch)
            # sprite.scale = config.ARROW_SIZE / image.width
            sprite.rotation = angle
            self.sprites.append(sprite)
        self._consumed = 0
    
    def head_position(self, progress: float) -> tuple[float, float]:
        """Where the star should sit along the path at slide-progress `progress`."""
        return _point_along_path(self.path, progress)

    def consume(self, progress: float) -> None:
        """Destroy arrows the star has already passed, in order."""
        covered = progress * self.total_length
        while self._consumed < len(self.sprites) and self.distances[self._consumed] <= covered:
            self.sprites[self._consumed].delete()
            self.sprites[self._consumed] = None
            self._consumed += 1

    def delete(self) -> None:
        for sprite in self.sprites:
            if sprite is not None:
                sprite.delete()

def load_note_images() -> dict[str, pyglet.image.AbstractImage]:
    images = {}
    for variant, filename in config.NOTE_IMAGE_FILES.items():
        img = pyglet.resource.image(filename)
        img.anchor_x = img.width // 2
        if filename == "hold.png":
            img.anchor_y = 150
        else:
            img.anchor_y = img.height // 2
        images[variant] = img
    return images

class NoteRenderer:
    def __init__(
        self,
        notes: list[Note],
        batch: pyglet.graphics.Batch,
        images: dict[str, pyglet.image.AbstractImage],
    ):
        self.notes = notes
        self.batch = batch
        self.images = images
        self._next_index = 0
        self._active: dict[int, tuple[Note, pyglet.sprite.Sprite]] = {}
        self._slide_bodies: dict[int, _SlideBody] = {}

    def update(self, t: float) -> None:
        while self._next_index < len(self.notes):
            note = self.notes[self._next_index]
            if note.time - config.APPROACH_TIME > t:
                break

            variant = config.note_variant(note, is_each=note.is_each)
            image = self.images.get(variant, self.images["tap"])

            sprite = pyglet.sprite.Sprite(image, batch=self.batch)
            sprite.rotation = _face_center_rotation(note.position)
            # sprite.scale = config.NOTE_SIZE / image.width
            self._active[self._next_index] = (note, sprite)
            self._next_index += 1

        expired = []
        for idx, (note, sprite) in self._active.items():
            is_moving_slide = (
                note.type == 1
                and note.slide_shape is not None
                and note.slide_time
                and t >= note.slide_start_time
            )

            if note.type == 1 and note.slide_shape is not None:
                if idx not in self._slide_bodies and t >= note.time:
                    self._slide_bodies[idx] = _SlideBody(note, self.images["arrow"], self.batch)
            
            if is_moving_slide:
                body = self._slide_bodies[idx]
                slide_progress = max(0.0, min(1.0, (t - note.slide_start_time) / note.slide_time))
                x, y = body.head_position(slide_progress)
                body.consume(slide_progress)
            else:
                head_progress = (t - (note.time - config.APPROACH_TIME)) / config.APPROACH_TIME
                head_progress = max(0.0, min(1.0, head_progress))
                radius = config.SPAWN_RADIUS + (config.RING_RADIUS - config.SPAWN_RADIUS) * head_progress
                x, y = config.lane_xy(note.position, radius)

            sprite.x, sprite.y = x, y

            if t > note.end_time + 0.05: # 50 mili kill time
                expired.append(idx)

        for idx in expired:
            sprite = self._active[idx][1]
            sprite.delete()
            self._active.pop(idx)
            body = self._slide_bodies.pop(idx, None)
            if body is not None:
                body.delete()