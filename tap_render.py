"""Rendering for tap notes.

Also reused directly for a slide's head (see slide_render.py) -- both
behave identically until a slide starts moving along its path: scale in
0 -> 1 at the spawn location, then approach the ring, then stay pinned.
"""

from __future__ import annotations
import math
import pyglet

import config
from render_common import face_center_rotation, draw_order

MAX_ROTATION_PER_FRAME = 18.0

class TapVisual:
    """A single sprite: scales in at the spawn location, then approaches
    the ring over the following APPROACH_TIME, staying pinned afterward."""

    def __init__(self, note, image, batch: pyglet.graphics.Batch):
        group = pyglet.graphics.Group(order=draw_order(config.TAP_LAYER, note.time))
        self.sprite = pyglet.sprite.Sprite(image, batch=batch, group=group)
        self.base_rotation = face_center_rotation(note.position) 
        self.sprite.rotation = self.base_rotation
        self.sprite.scale = 0.0
        # extra spin on top of base_rotation when being a star head
        self._spin_offset = 0.0

    def update(self, t: float, note, length = None) -> None:
        spawn_start = note.time - 2 * config.APPROACH_TIME
        move_start = note.time - config.APPROACH_TIME

        if t < move_start:
            scale_progress = (t - spawn_start) / config.APPROACH_TIME
            self.sprite.scale = max(0.0, min(1.0, scale_progress))
            x, y = config.lane_xy(note.position, config.SPAWN_RADIUS)
        else:
            self.sprite.scale = 1.0
            head_progress = (t - move_start) / config.APPROACH_TIME
            head_progress = max(0.0, min(1.0, head_progress))
            radius = config.SPAWN_RADIUS + (config.RING_RADIUS - config.SPAWN_RADIUS) * head_progress
            x, y = config.lane_xy(note.position, radius)

        self.sprite.x, self.sprite.y = x, y
        # Star head spin: only applies when we're being driven as a slide's
        # head (caller passes the path's total length), and starts right
        # away at spawn_time rather than waiting for move_start.
        if length is not None and note.slide_time:
            rotate_speed = length / (note.slide_time * 15 * 13 * math.pi)
            rotate_speed = max(-MAX_ROTATION_PER_FRAME, min(MAX_ROTATION_PER_FRAME, rotate_speed))
            delta_rot = (-180 * rotate_speed) / config.FPS
            # print(length, note.slide_time, rotate_speed, delta_rot)
            self._spin_offset += delta_rot

        self.sprite.rotation = self.base_rotation + self._spin_offset

    def delete(self) -> None:
        self.sprite.delete()