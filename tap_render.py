"""Rendering for tap notes.

Also reused directly for a slide's head (see slide_render.py) -- both
behave identically until a slide starts moving along its path: scale in
0 -> 1 at the spawn location, then approach the ring, then stay pinned.
"""

from __future__ import annotations
import pyglet

import config
from render_common import face_center_rotation, draw_order


class TapVisual:
    """A single sprite: scales in at the spawn location, then approaches
    the ring over the following APPROACH_TIME, staying pinned afterward."""

    def __init__(self, note, image, batch: pyglet.graphics.Batch):
        group = pyglet.graphics.Group(order=draw_order(config.TAP_LAYER, note.time))
        self.sprite = pyglet.sprite.Sprite(image, batch=batch, group=group)
        self.base_rotation = face_center_rotation(note.position) 
        self.sprite.rotation = self.base_rotation
        self.sprite.scale = 0.0

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
        # TODO apply a rotation function for star head on top of face_center_rotation
        # maybe like this: Rotation speed = Total length of path / (Total slide time * 15 * pi)
        # length path in pixel, time in mili, unit is degree per frame, max 18
        # use total_length from class slidepathvisual and note.slidetime
        # rotation speed = 1 means 180 degrees per second
        # so deltaRot = (-180 * RotateSpeed)/FPS
        # need a lot more testing so formula should be flexible to changes
        # star should start rotating immediately at spawn_time
        if length is not None and note.slide_time is not None:
            rotation_speed = length / (note.slide_time * 2 * 3.14159)
            degrees_per_sec = -180 * rotation_speed
            elapsed = max(0.0, t - spawn_start)
            self.sprite.rotation = self.base_rotation + degrees_per_sec * elapsed
        else:
            self.sprite.rotation = self.base_rotation

    def delete(self) -> None:
        self.sprite.delete()