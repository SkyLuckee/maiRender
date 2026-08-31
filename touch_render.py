"""Rendering for touch notes.
"""

from __future__ import annotations
import pyglet
import math

import config
from render_common import draw_order, clamped_progress
from slide_path import _circle_points

class TouchVisual:
    """1 touch point sprite and a group of 4 sprites of touch slices.
    All slices behave indentically apart from their rotation and position.
    Slices are positioned in the 4 cardinal direction at a distance away from touch point, rotated appropriately.
    Between move_start and note.time, the slices approach the point at a fix rate before reaching touch point and expire"""

    def __init__(self, note, point_image, slice_image, area, batch: pyglet.graphics.Batch):
        base_order = draw_order(config.TOUCH_LAYER, note.time)
        point_group = pyglet.graphics.Group(base_order)
        slice_group = pyglet.graphics.Group(base_order - 1)

        self.point = pyglet.sprite.Sprite(point_image, batch=batch, group=point_group)

        self.slices = [pyglet.sprite.Sprite(slice_image, batch=batch, group=slice_group) for _ in range(4)]
        for i, s in enumerate(self.slices):
            s.rotation = i * (360 / 4)

        self.area = area
        self.slice_radius = 40

    def update(self, t: float, note) -> None:
        spawn_start = note.time - config.TOUCH_APPROACH_TIME
        move_start = note.time - 0.8 * config.TOUCH_APPROACH_TIME

        px, py = config.lane_xy(note.position - 0.5 if self.area in ("D","E") else note.position, config.SENSOR_RADIUS[self.area])
        if t < move_start:
            opacity_progress = clamped_progress(t, spawn_start, config.TOUCH_APPROACH_TIME * 0.2)
            value = int(opacity_progress * 255)
            radius = self.slice_radius
        else:
            timing = t - move_start
            pow = -math.exp(8 * ((-timing + 0.067) * 0.43 / (config.TOUCH_APPROACH_TIME*0.8)) - 0.85) + 0.42
            distance = max(0.0, min(0.4, pow))

            value = 255
            radius = self.slice_radius - distance*100

        self.point.opacity = value
        for s in self.slices:
            s.opacity = value
        
        slice_coords = _circle_points((px, py), radius, math.pi * 1.5, 0, False, 4)
        self.point.x, self.point.y = px, py
        for s, (x, y) in zip(self.slices, slice_coords):
            s.x, s.y = x, y

    def delete(self) -> None:
        self.point.delete()
        for s in self.slices:
            s.delete()
