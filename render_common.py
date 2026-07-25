"""Shared math/utility helpers used across the per-note-type renderer modules."""
import math

import config


def face_center_rotation(position: int) -> float:
    """Sprite rotation (degrees, clockwise) facing inward."""
    return 90 - math.degrees(config.lane_angle(position))


def draw_order(tier: int, note_time: float) -> float:
    """Group order for a note's sprite(s): lower draws first (behind).

    Tiers are separated by config.LAYER_GAP so they never overlap. Within
    a tier, later notes get a LOWER order (drawn first/behind) so earlier
    notes end up rendered on top of later ones.
    """
    return tier * config.LAYER_GAP - note_time


def cumulative_lengths(path) -> list[float]:
    """Running arc-length total up to each point in `path`."""
    lengths = [0.0]
    for i in range(1, len(path)):
        x0, y0, _ = path[i - 1]
        x1, y1, _ = path[i]
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    return lengths


def sample_at_distance(path, lengths, dist: float) -> tuple[float, float, float]:
    """Return (x, y, angle_degrees) at arc-length `dist` along `path`."""
    i = next((i for i in range(1, len(lengths)) if lengths[i] >= dist), len(lengths) - 1)
    x0, y0, angle0 = path[i - 1]
    x1, y1, angle1 = path[i]
    seg_len = lengths[i] - lengths[i - 1]
    frac = 0.0 if seg_len == 0 else max(0.0, min(1.0, (dist - lengths[i - 1]) / seg_len))
    x = x0 + (x1 - x0) * frac
    y = y0 + (y1 - y0) * frac
    angle = angle0 + ((angle1 - angle0 + 180) % 360 - 180) * frac
    return x, y, angle