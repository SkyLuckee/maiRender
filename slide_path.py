"""Computes the 2D path a slide's slide chain follows, given its parsed shape.

Each shape handler returns a list of (x, y, angle_degrees) triples -- both
position AND facing are decided by the shape itself. Most shapes just want
"face the direction of travel," so they build plain (x, y) points and pass
them through _with_tangent_angles(). A shape that wants different rotation
behavior computes its own angles instead -- no config file involved."""
import math

import config

SAMPLES_PER_SEGMENT = 10
SHAPE_HANDLERS = {}

def register_shape(*chars):
    def decorator(fn):
        for c in chars:
            SHAPE_HANDLERS[c] = fn
        return fn
    return decorator

def _tangent_angle_deg(x0: float, y0: float, x1: float, y1: float) -> float:
    """Degrees, pyglet's clockwise-from-up convention, for the direction x0,y0 -> x1,y1.
    +90 at the end to account for the original direction of the sprite"""
    return math.degrees(math.atan2(x1 - x0, y1 - y0)) + 90

def _with_tangent_angles(points, offset_fn=None) -> list[tuple[float, float, float]]:
    """Default rotation: each point faces the next point (last point reuses
    the final segment's direction).
 
    `offset_fn`, if given, is called as offset_fn(progress) for each point
    (progress: 0 at the first point, 1 at the last) and its return value
    (degrees) is added on top of the tangent angle -- so a shape can vary
    rotation along its own path without leaving this function."""
    n = len(points)
    triples = []
    for i, (x, y) in enumerate(points):
        if i < n - 1:
            x1, y1 = points[i + 1]
            angle = _tangent_angle_deg(x, y, x1, y1)
        else:
            x0, y0 = points[i - 1]
            angle = _tangent_angle_deg(x0, y0, x, y)
        if offset_fn is not None:
            progress = i / (n - 1) if n > 1 else 0.0
            angle += offset_fn(progress)
        triples.append((x, y, angle))
    return triples

def _line_points(p0, p1, n):
    """n evenly-spaced points from p0 to p1 (inclusive of both ends)."""
    x0, y0 = p0
    x1, y1 = p1
    return [(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1)) for i in range(n)]

@register_shape("-","V")
def _straight(start_pos: int, end_pos: int, samples: int) -> list[tuple[float, float]]:
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)
    points = _line_points((sx,sy), (ex,ey), samples)
    return _with_tangent_angles(points)

@register_shape("v")
def _dip_through_center(start_pos: int, end_pos: int, samples: int) -> list[tuple[float, float]]:
    """2 slide: start to center and center to end"""
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)
    center = (config.CENTER_X, config.CENTER_Y)
    half = samples // 2
    first_leg = _line_points((sx, sy), center, half + 1)
    second_leg = _line_points(center, (ex, ey), samples - half)[1:]
    points = first_leg + second_leg
    return _with_tangent_angles(points)

def _arc(start_pos: int, end_pos: int, samples: int, default: bool) -> list[tuple[float, float]]:
    start_angle = config.lane_angle(start_pos)
    end_angle = config.lane_angle(end_pos)
    diff = (end_angle - start_angle) % (2 * math.pi)

    if start_pos not in (3,4,5,6):
        if not default:
            diff -= 2 * math.pi
    else:
        if default:
            diff -= 2 * math.pi

    points = []
    for i in range(samples):
        angle = start_angle + diff * i / (samples - 1)
        x = config.CENTER_X + config.RING_RADIUS * math.cos(angle)
        y = config.CENTER_Y + config.RING_RADIUS * math.sin(angle)
        points.append((x, y))
    return _with_tangent_angles(points)

@register_shape("<")
def _arc_left(start_pos, end_pos, samples: int) -> list[tuple[float, float, float]]:
    return _arc(start_pos, end_pos, samples, default=True)

@register_shape(">")
def _arc_right(start_pos, end_pos, samples: int) -> list[tuple[float, float, float]]:
    return _arc(start_pos, end_pos, samples, default=False)

def _segment(start_pos: int, end_pos: int, shape: str, samples: int) -> list[tuple[float, float, float]]:
    handler = SHAPE_HANDLERS.get(shape, _straight)
    return handler(start_pos, end_pos, samples)

def build_path(start_position: int, waypoints: list[int], shape: str) -> list[tuple[float, float, float]]:
    """Return an ordered list of (x, y, angle_degrees) tracing a slide's full path.
 
    `waypoints` is everything after the start position -- for most shapes
    that's a single endpoint; "V" slides have two legs, so two waypoints.
    """
    stops = [start_position] + waypoints
    points: list[tuple[float, float,float]] = []
    for i in range(len(stops) - 1):
        segment = _segment(stops[i], stops[i + 1], shape, SAMPLES_PER_SEGMENT)
        if points:
            segment = segment[1:]
        points.extend(segment)
    return points

# x0, y0 = config.lane_xy(1, 480)
# x1, y1 = config.lane_xy(5, 480)
# print(_tangent_angle_deg(x0, y0, x1, y1))
# print(_straight(4,8,2))

# a = build_path(1,[4],"-")
# print(a)

# start_angle = config.lane_angle(5)
# end_angle = config.lane_angle(4)
# diff = (end_angle - start_angle) % (2 * math.pi)
# print(diff)