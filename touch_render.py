"""Rendering for touch notes.
"""

from __future__ import annotations
import pyglet
import math

import config
from render_common import draw_order
from slide_path import _circle_points

# TODO implement touch note
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
        self.slice_radius = 35

    def update(self, t: float, note) -> None:
        spawn_start = note.time - 2 * config.APPROACH_TIME
        move_start = note.time - 1.2 * config.APPROACH_TIME

        px, py = config.lane_xy(note.position - 0.5 if self.area in ("D","E") else note.position, config.SENSOR_RADIUS[self.area])
        if t < move_start:
            opacity_progress = (t - spawn_start) / config.APPROACH_TIME
            value = int(max(0.0, min(1.0, opacity_progress)) * 255)
            radius = self.slice_radius
        else:
            move_progress = (t - move_start) / config.APPROACH_TIME
            value = 255
            radius = self.slice_radius * (1 - move_progress)

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

# coord = _circle_points((540,540), 0.5, math.pi*1.5, 0, False, 4)
# for i in coord:
#     print(i[0])