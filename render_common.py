"""Shared math/utility helpers used across the per-note-type renderer modules."""
from __future__ import annotations
import math
from typing import Protocol

import config


class Visual(Protocol):
    """The interface every per-note visual (TapVisual, HoldVisual,
    SlideVisual, TouchVisual, TouchHoldVisual, ...) implements. NoteRenderer
    only ever calls these two methods, regardless of note type -- this
    documents that contract in the type system instead of only in prose,
    so a new visual class or a typo'd method name is caught by a type
    checker rather than only surfacing at runtime.
    """

    def update(self, t: float, note) -> None: ...
    def delete(self) -> None: ...

def face_center_rotation(position: int) -> float:
    """Sprite rotation (degrees, clockwise) facing inward."""
    return 90 - math.degrees(config.lane_angle(position))

def clamped_progress(t: float, start: float, duration: float) -> float:
    """Linear progress of `t` through the window [start, start + duration],
    clamped to [0, 1].
    """
    if duration <= 0:
        return 1.0
    return max(0.0, min(1.0, (t - start) / duration))


def draw_order(tier: int, note_time: float) -> float:
    """Group order for a note's sprite(s): lower draws first (behind).

    Tiers are separated by config.LAYER_GAP so they never overlap. Within
    a tier, later notes get a LOWER order (drawn first/behind) so earlier
    notes end up rendered on top of later ones.
    """
    return tier * config.LAYER_GAP - note_time


def cumulative_lengths(path) -> list[float]:
    """Calculate line length between point on a path cumulatively"""
    lengths = [0.0]
    for i in range(1, len(path)):
        x0, y0, _ = path[i - 1]
        x1, y1, _ = path[i]
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    return lengths


def sample_at_distance(path, lengths, dist: float) -> tuple[float, float, float]:
    """Return (x, y, angle_degrees) at arc-length `dist` along `path`."""
    i = next((i for i in range(1, len(lengths)) if lengths[i] >= dist), len(lengths) - 1)
    x0, y0, angle = path[i - 1]
    x1, y1, _ = path[i]
    seg_len = lengths[i] - lengths[i - 1]
    frac = 0.0 if seg_len == 0 else max(0.0, min(1.0, (dist - lengths[i - 1]) / seg_len))
    x = x0 + (x1 - x0) * frac
    y = y0 + (y1 - y0) * frac
    return x, y, angle