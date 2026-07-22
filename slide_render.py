"""Rendering for slide notes: a head (reuses tap_render.TapVisual as-is)
plus a separately-tracked path of arrow sprites, created once the head
lands on the ring and consumed as the star travels along it."""

from __future__ import annotations
import pyglet

import config
from render_common import draw_order, cumulative_lengths, sample_at_distance
from slide_path import build_path
from tap_render import TapVisual


def _slide_placements(path, lengths, spacing: float):
    total = lengths[-1]
    placements = []
    dist = 0.0
    while total - dist >= spacing / 2:
        placements.append(sample_at_distance(path, lengths, dist))
        dist += spacing
    return placements

"""Offset between consecutive arrows' draw order, layered on top of the
slide's own base order"""
ARROW_ORDER_EPSILON = 1e-6

class SlidePathVisual:
    """A chain of arrow sprites tracing one slide's path, consumed in order
    as the star travels along it."""
    def __init__(self, note, image, batch: pyglet.graphics.Batch):
        self.path = build_path(note.position, note.slide_waypoints or [], note.slide_shape or "-")
        self.lengths = cumulative_lengths(self.path)
        self.total_length = self.lengths[-1]
        placements = _slide_placements(self.path, self.lengths, config.SLIDE_SPACING)
        self.sprites = []
        self.distances = [i * config.SLIDE_SPACING for i in range(len(placements))]
        base_order = draw_order(config.SLIDE_LAYER, note.time)
        for i, (x, y, angle) in enumerate(placements):
            group = pyglet.graphics.Group(order=base_order - i * ARROW_ORDER_EPSILON)
            sprite = pyglet.sprite.Sprite(image, x=x, y=y, batch=batch, group=group)
            sprite.rotation = angle
            self.sprites.append(sprite)
        self._consumed = 0

    def head_position(self, progress: float) -> tuple[float, float]:
        dist = max(0.0, min(1.0, progress)) * self.total_length
        x, y, _ = sample_at_distance(self.path, self.lengths, dist)
        return x, y

    def consume(self, progress: float) -> None:
        covered = progress * self.total_length
        while self._consumed < len(self.sprites) and self.distances[self._consumed] <= covered:
            self.sprites[self._consumed].delete()
            self.sprites[self._consumed] = None
            self._consumed += 1

    def delete(self) -> None:
        for sprite in self.sprites:
            if sprite is not None:
                sprite.delete()


class SlideVisual:
    """A slide note: a head (TapVisual, reused unchanged for the spawn +
    approach phase) plus a path (SlidePathVisual, created once the head
    lands on the ring at note.time). Once the slide starts moving
    (note.slide_start_time), the head is driven by the path's
    head_position() instead of TapVisual's own approach formula.
    """
    def __init__(self, note, head_image, path_image, batch: pyglet.graphics.Batch):
        self.head = TapVisual(note, head_image, batch)
        self.path_image = path_image
        self.batch = batch
        self.path: SlidePathVisual | None = None

    def update(self, t: float, note) -> None:
        if self.path is None and t >= note.time:
            self.path = SlidePathVisual(note, self.path_image, self.batch)

        is_moving = (
            note.slide_time
            and t >= note.slide_start_time
            and self.path is not None
        )

        if is_moving:
            self.head.sprite.scale = 1.0
            progress = max(0.0, min(1.0, (t - note.slide_start_time) / note.slide_time))
            x, y = self.path.head_position(progress)
            self.head.sprite.x, self.head.sprite.y = x, y
            self.path.consume(progress)
        else:
            self.head.update(t, note)

    def delete(self) -> None:
        self.head.delete()
        if self.path is not None:
            self.path.delete()