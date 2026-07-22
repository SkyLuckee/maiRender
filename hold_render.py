"""Rendering for hold notes: head, body, and tail sprites, sliced from a
single sprite sheet and independently animated (head/tail approach the
ring on their own schedules, body stretches to always connect them)."""

from __future__ import annotations
import pyglet

import config
from render_common import face_center_rotation, draw_order

HOLD_VARIANTS = ("hold", "hold_break", "hold_each")


def slice_hold_regions(img: pyglet.image.AbstractImage):
    """Split a hold sprite sheet into (head, body, tail) sub-images.

    The sheet is HOLD_HEAD_TAIL_SIZE px of head at the top, the same
    amount of tail at the bottom, and a stretchable body strip in between.
    Anchors are set so head's and tail's body-facing edges are each at
    local y matching where the body attaches -- when both are placed at
    the same (x, y), those edges coincide exactly (body length 0).
    """
    w, h = img.width, img.height
    size_px = int(round(config.HOLD_HEAD_TAIL_SIZE))

    tail = img.get_region(0, 0, w, size_px)
    head = img.get_region(0, h - size_px, w, size_px)
    body_height = max(h - 2 * size_px, 1)
    body = img.get_region(0, size_px, w, body_height)

    head.anchor_x = w // 2
    head.anchor_y = 0            # bottom edge of head crop -- attaches to body

    tail.anchor_x = w // 2
    tail.anchor_y = size_px      # top edge of tail crop -- attaches to body

    body.anchor_x = w // 2
    body.anchor_y = 0            # stretches upward (outward) from this edge

    return head, body, tail


class HoldVisual:
    """Head, body, and tail sprites for one hold note.

    Head approaches the ring like a normal note, arriving at note.time and
    staying pinned there. Tail uses the exact same approach formula but
    targets note.end_time instead -- since head_progress/tail_progress are
    both clamped to [0, 1], the tail naturally sits still at SPAWN_RADIUS
    until its own approach window opens, with no separate branch needed.
    The body sprite is repositioned and vertically re-scaled every frame
    to span exactly the current gap between head and tail.
    """
    def __init__(self, note, head_img, body_img, tail_img, batch: pyglet.graphics.Batch):
        rotation = face_center_rotation(note.position)
        group = pyglet.graphics.Group(order=draw_order(config.HOLD_LAYER, note.time))
        self.head = pyglet.sprite.Sprite(head_img, batch=batch, group=group)
        self.body = pyglet.sprite.Sprite(body_img, batch=batch, group=group)
        self.tail = pyglet.sprite.Sprite(tail_img, batch=batch, group=group)
        for sprite in (self.head, self.body, self.tail):
            sprite.rotation = rotation
            sprite.scale = 0.0
        self._body_native_height = body_img.height or 1

    def update(self, t: float, note) -> None:
        spawn_start = note.time - 2 * config.APPROACH_TIME
        move_start = note.time - config.APPROACH_TIME

        scale_progress = (t - spawn_start) / config.APPROACH_TIME
        scale = max(0.0, min(1.0, scale_progress))
        self.head.scale = scale
        self.body.scale = scale
        self.tail.scale = scale

        head_progress = (t - move_start) / config.APPROACH_TIME
        head_progress = max(0.0, min(1.0, head_progress))
        head_radius = config.SPAWN_RADIUS + (config.RING_RADIUS - config.SPAWN_RADIUS) * head_progress

        tail_move_start = note.end_time - config.APPROACH_TIME
        tail_progress = (t - tail_move_start) / config.APPROACH_TIME
        tail_progress = max(0.0, min(1.0, tail_progress))
        tail_radius = config.SPAWN_RADIUS + (config.RING_RADIUS - config.SPAWN_RADIUS) * tail_progress

        hx, hy = config.lane_xy(note.position, head_radius)
        tx, ty = config.lane_xy(note.position, tail_radius)

        self.head.x, self.head.y = hx, hy
        self.tail.x, self.tail.y = tx, ty

        self.body.x, self.body.y = tx, ty
        gap = head_radius - tail_radius
        self.body.scale_y = gap / self._body_native_height

    def delete(self) -> None:
        self.head.delete()
        self.body.delete()
        self.tail.delete()