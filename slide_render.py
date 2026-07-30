"""Rendering for slide notes: a head (reuses tap_render.TapVisual as-is)
plus a separately-tracked path of arrow sprites, created once the head
lands on the ring and consumed as the star travels along it."""

from __future__ import annotations
import pyglet

import config
from render_common import draw_order, face_center_rotation, cumulative_lengths, sample_at_distance
from slide_path import build_path, SAMPLES_PER_SEGMENT
from compound_slide_path import build_compound_path
from tap_render import TapVisual


def _leg_boundaries(lengths: list[float], num_legs: int) -> list[float]:
    """Cumulative arc-length at the end of each leg of a (possibly
    compound) slide path.

    Every leg contributes exactly SAMPLES_PER_SEGMENT points to the path
    (whichever handler built it), and every leg after the first drops its
    shared first point when concatenated onto the previous one -- so
    leg k's last point always sits at path index
    (k + 1) * (SAMPLES_PER_SEGMENT - 1), regardless of that leg's shape.
    """
    S = SAMPLES_PER_SEGMENT
    last_index = len(lengths) - 1
    return [lengths[min((k + 1) * (S - 1), last_index)] for k in range(num_legs)]


def _slide_placements(path, lengths, spacing: float, leg_boundaries: list[float]):
    """Place arrows at `spacing` intervals, restarting at each leg
    boundary so skipping the arrow right at the start (covered by the head/previous leg's
    endpoint) and never placing one too close to the end

    Returns (placements, distances) as parallel lists, where `distances`
    is each placement's actual arc-length distance from the path start
    (not assumed to be a uniform multiple of `spacing` any more, since a
    leg's own length need not be an exact multiple of it)."""
    placements = []
    distances = []
    leg_start = 0.0
    for boundary in leg_boundaries:
        leg_length = boundary - leg_start
        dist = spacing  # skip this leg's own first arrow (its own start / shared waypoint)
        while leg_length - dist >= spacing / 2:
            placements.append(sample_at_distance(path, lengths, leg_start + dist))
            distances.append(leg_start + dist)
            dist += spacing
        leg_start = boundary
    return placements, distances

"""Offset between consecutive arrows' draw order, layered on top of the
slide's own base order"""
ARROW_ORDER_EPSILON = 1e-6

class SlidePathVisual:
    """A chain of arrow sprites tracing one slide's path, consumed in order
    as the star travels along it."""
    def __init__(self, note, image, batch: pyglet.graphics.Batch):
        if note.slide_segments:
            # Compound slide's built once here and treated identically to
            # a simple slide's path - only the arrow placement below still
            # needs to know the individual segment boundaries.
            self.path = build_compound_path(note.position, note.slide_segments)
            num_legs = len(note.slide_segments)
        else:
            self.path = build_path(note.position, note.slide_waypoints or [], note.slide_shape or "-")
            num_legs = 1
        self.lengths = cumulative_lengths(self.path)
        self.total_length = self.lengths[-1]
        leg_boundaries = _leg_boundaries(self.lengths, num_legs)
        placements, distances = _slide_placements(self.path, self.lengths, config.SLIDE_SPACING, leg_boundaries)
        self.distances = distances
        self.sprites = []
        base_order = draw_order(config.SLIDE_LAYER, note.time)
        for i, (x, y, angle) in enumerate(placements):
            group = pyglet.graphics.Group(order=base_order - i * ARROW_ORDER_EPSILON)
            sprite = pyglet.sprite.Sprite(image, x=x, y=y, batch=batch, group=group)
            sprite.rotation = angle
            self.sprites.append(sprite)
        self._consumed = 0

    def head_position(self, progress: float) -> tuple[float, float, float]:
        """Same tangent-angle model the arrows use (_with_tangent_angles in
        slide_path.py), so the tracer star can rotate the same way they do."""
        dist = max(0.0, min(1.0, progress)) * self.total_length
        x, y, angle = sample_at_distance(self.path, self.lengths, dist)
        return x, y, angle

    def set_opacity(self, fraction: float) -> None:
        """Set every still-existing arrow's opacity uniformly (0.0-1.0)."""
        value = int(max(0.0, min(1.0, fraction)) * 255)
        for sprite in self.sprites:
            if sprite is not None:
                sprite.opacity = value

    def consume(self, progress: float) -> None:
        covered = progress * self.total_length + config.SLIDE_SPACING
        while self._consumed < len(self.sprites) and self.distances[self._consumed] <= covered:
            self.sprites[self._consumed].delete()
            self.sprites[self._consumed] = None
            self._consumed += 1

    def delete(self) -> None:
        for sprite in self.sprites:
            if sprite is not None:
                sprite.delete()


class SlideVisual:
    """slide note: a head (TapVisual, unchanged spawn + approach phase)
    and a separately-controlled tracer star that takes over once the
    slide starts moving, plus the path (SlidePathVisual, created once the
    head lands on the ring at note.time).

    Head and tracer are separated sprite objects, each built from
    whatever image was passed in for it -- so their variants (is_each,
    is_slide_each, eventually is_slide_break) can be chosen independently
    by the caller, rather than one sprite being repurposed for both roles.
    """
    def __init__(self, note, head_image, tracer_image, path_image, batch: pyglet.graphics.Batch):
        self.head: TapVisual | None = TapVisual(note, head_image, batch)
        self.tracer_image = tracer_image
        self.path_image = path_image
        self.batch = batch
        self.path: SlidePathVisual | None = None
        self.tracer: pyglet.sprite.Sprite | None = None
        if note.slide_segments:
            raw_path = build_compound_path(note.position, note.slide_segments)
        else:
            raw_path = build_path(note.position, note.slide_waypoints or [], note.slide_shape or "-")
        self.total_length = cumulative_lengths(raw_path)[-1]

    def update(self, t: float, note) -> None:
        move_start = note.time - config.APPROACH_TIME
        if self.path is None and t >= move_start:
            self.path = SlidePathVisual(note, self.path_image, self.batch)

        if self.path is not None:
            path_progress = (t - move_start) / config.APPROACH_TIME
            self.path.set_opacity(path_progress)

        if t < note.time:
            self.head.update(t, note, self.total_length)
            return

        if self.head is not None:
            self.head.delete()
            self.head = None

        if self.tracer is None:
            group = pyglet.graphics.Group(order=draw_order(config.TAP_LAYER, note.time))
            self.tracer = pyglet.sprite.Sprite(self.tracer_image, batch=self.batch, group=group)
            self.tracer.opacity = 0

        is_moving = note.slide_time and t >= note.slide_start_time and self.path is not None
        slide_progress = 0.0
        if is_moving:
            slide_progress = max(0.0, min(1.0, (t - note.slide_start_time) / note.slide_time))

        if self.path is not None:
            path_x, path_y, path_angle = self.path.head_position(slide_progress)
            self.tracer.rotation = path_angle - 90
        else:
            self.tracer.rotation = face_center_rotation(note.position)

        if is_moving:
            self.tracer.opacity = 255
            self.tracer.x, self.tracer.y = path_x, path_y
            self.tracer.scale = 1.5
            self.path.consume(slide_progress)
        else:
            fade_duration = note.slide_start_time - note.time
            tracer_progress = ((t - note.time) / fade_duration) if fade_duration > 0 else 1.0
            tracer_progress = max(0.0, min(1.0, tracer_progress))
            self.tracer.opacity = int(tracer_progress * 255)
            x, y = config.lane_xy(note.position, config.RING_RADIUS)
            self.tracer.x, self.tracer.y = x, y
            self.tracer.scale = 1.5 * tracer_progress

    def delete(self) -> None:
        if self.head is not None:
            self.head.delete()
        if self.tracer is not None:
            self.tracer.delete()
        if self.path is not None:
            self.path.delete()