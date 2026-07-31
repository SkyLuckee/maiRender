"""Compound slides are several ordinary slides chained together through
shared waypoints, e.g. "1-3-5-7[8:1]" is three "-" legs (1->3, 3->5, 5->7)
back to back, each leg possibly using its own shape token
(e.g. "1-3<5[8:1]" is a "-" leg then a "<" leg). Unlike a normal slide's
multi-waypoint form (e.g. "1-37", one shape reused for every leg),
a compound slide repeats a shape token before every leg's digit(s).

Most shapes need only one digit per leg (just an end position), but "V"
needs two (a middle waypoint then an end position) to describe a single
V-shaped leg -- e.g. "1V35V71[8:1]" is two V legs, "1V35" (start 1,
middle 3, end 5) then "5V71" (start 5, middle 7, end 1). _MULTI_WAYPOINT_
SHAPES records how many digits each such shape consumes; everything else
defaults to one digit per leg, and a shape token followed by several
digits (e.g. "-37") is split into one leg per digit, all reusing that
shape.

slide_time is applied to the whole chain, not to any individual leg --
there is exactly one head and one tracer star, built once and driven
along the concatenated path -- so this module only has to produce the
same (x, y, angle) triple list that slide_path.build_path() returns.
Everything downstream (SlidePathVisual, SlideVisual) then treats a
compound path exactly like a simple one.
"""
from __future__ import annotations

import re

from slide_path import _segment, _V_slide, SAMPLES_PER_SEGMENT

# Captures each (shape, digit-run) pair, e.g. "-3-5-7" -> [("-","3"),("-","5"),("-","7")]
# and "V35V71" -> [("V","35"),("V","71")] -- the digit run is greedy, so it
# naturally grabs however many digits belong to that shape token before the
# next non-digit shape character interrupts it.
_TOKEN_PATTERN = re.compile(r"([^\d\[]+)(\d+)")

# Whole-string check: start digit, then one-or-more (shape, digit-run) pairs, then "[...]"
_COMPOUND_SLIDE_PATTERN = re.compile(r"^\d((?:[^\d\[]+\d+)+)\[[^\]]*\]$")

# Shapes whose leg is described by more than one digit, and how many.
# "V" is a single leg through a middle waypoint to an end waypoint.
_MULTI_WAYPOINT_SHAPES = {"V": 2}

Segment = tuple[str, tuple[int, ...]]


def parse_compound_slide(raw_content: str) -> list[Segment] | None:
    """Parse a slide's RawContent into a list of (shape, waypoints) legs
    if it's a compound slide (a shape token immediately precedes every
    leg's digit(s)), or return None if it isn't shaped like one.

    `waypoints` is a 1-tuple (just the end position) for ordinary shapes,
    or a 2-tuple (middle, end) for "V" legs.

    A single-leg RawContent (e.g. "1-3[8:1]") technically also matches
    this pattern, but that's just an ordinary slide -- callers should try
    the ordinary slide_shape parse first and only fall back to this for
    RawContent the ordinary parse rejected.
    """
    m = _COMPOUND_SLIDE_PATTERN.match(raw_content)
    if not m:
        return None

    segments: list[Segment] = []
    for shape, digits in _TOKEN_PATTERN.findall(m.group(1)):
        needed = _MULTI_WAYPOINT_SHAPES.get(shape)
        if needed is not None:
            if len(digits) != needed:
                return None  # malformed, e.g. "V" without exactly 2 digits
            segments.append((shape, tuple(int(d) for d in digits)))
        else:
            # A shape reused across consecutive single-digit waypoints,
            # e.g. "-37" -- one leg per digit, all using this shape.
            segments.extend((shape, (int(d),)) for d in digits)

    if len(segments) < 2:
        return None  # not actually compound -- just one ordinary leg
    return segments


def build_compound_path(
    start_position: int, segments: list[Segment]
) -> tuple[list[tuple[float, float, float]], list[int]]:
    """Build the full (x, y, angle_degrees) path for a compound slide by
    building each leg with the ordinary per-shape handlers (or _V_slide
    for "V" legs, which needs its middle waypoint and isn't a registered
    shape handler) and concatenating them, dropping each leg's first
    point (the shared waypoint) so it isn't duplicated.

    Also returns `leg_boundary_indices`: the index into the returned path
    of each leg's last point (its shared waypoint with the next leg, or
    the slide's final endpoint for the last leg). Callers need this to
    know where one leg ends and the next begins"""
    if not segments:
        raise ValueError("Compound slide needs at least one segment")

    points: list[tuple[float, float, float]] = []
    leg_boundary_indices: list[int] = []
    current = start_position
    for shape, waypoints in segments:
        end = waypoints[-1]
        if shape == "V":
            middle = waypoints[0]
            leg_points = _V_slide(current, middle, end, SAMPLES_PER_SEGMENT)
        else:
            leg_points = _segment(current, end, shape, SAMPLES_PER_SEGMENT)
        if points:
            shared_x, shared_y, _ = points[-1]
            _, _, outgoing_angle = leg_points[0]
            points[-1] = (shared_x, shared_y, outgoing_angle)
            leg_points = leg_points[1:]
        points.extend(leg_points)
        leg_boundary_indices.append(len(points) - 1)
        current = end
    return points, leg_boundary_indices