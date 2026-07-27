"""Rendering for touch notes.
"""

from __future__ import annotations
import pyglet
import math

import config
from render_common import draw_order
from slide_path import _circle_points

# TODO implement touch hold note
class TouchHoldVisual:
    """1 touch point sprite and a group of 4 different sprites of touch hold slices.
    All slices behave indentically apart from their rotation, position and sprite.
    Slices are positioned in the 4 ordinal direction at a distance away from touch point, rotated appropriately.
    Between move_start and note.time, the slices approach the point at a fix rate before reaching the touch point and expire.
    the point and slices then stay until expire at note.end_time"""

    def __init__(self, note, point_image, area, batch: pyglet.graphics.Batch):
        base_order = draw_order(config.TOUCH_LAYER, note.time)
        point_group = pyglet.graphics.Group(base_order)
        slice_group = pyglet.graphics.Group(base_order - 1)
        border_group = pyglet.graphics.Group(base_order - 2)

        self.point = pyglet.sprite.Sprite(point_image, batch=batch, group=point_group)

        slices_image = [pyglet.resource.image(f"touchhold_{i}.png") for i in range(4)]
        for i in slices_image:
            i.anchor_x = i.width // 2
            i.anchor_y = i.height - 17
        self.slices = [pyglet.sprite.Sprite(i, batch=batch, group=slice_group) for i in slices_image]
        for i, s in enumerate(self.slices):
            s.rotation = i * (360 / 4) - 135

        border_image = pyglet.resource.image("touchhold_border.png")
        border_image.anchor_x = border_image.width // 2
        border_image.anchor_y = border_image.height // 2
        self.border = pyglet.sprite.Sprite(border_image, batch=batch, group=border_group)

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
            move_progress = max(0.0, min(1.0, move_progress))
            value = 255
            radius = self.slice_radius * (1 - move_progress)

        border_start = note.time
        border_progress = (t - border_start) / (note.end_time - border_start)
        border_progress = max(0.0, min(1.0, border_progress))
        self.border.x, self.border.y = px, py
        self.border.opacity = int(value * border_progress)

        self.point.opacity = value
        for s in self.slices:
            s.opacity = value
        
        slice_coords = _circle_points((px, py), radius, math.pi*0.25, math.pi*0.75, False, 4)
        self.point.x, self.point.y = px, py
        for s, (x, y) in zip(self.slices, slice_coords):
            s.x, s.y = x, y

    def delete(self) -> None:
        self.point.delete()
        self.border.delete()
        for s in self.slices:
            s.delete()