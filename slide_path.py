"""Computes the 2D path a slide's slide chain follows, given its parsed shape.

Each shape handler returns a list of (x, y, angle_degrees) triples -- both
position AND facing are decided by the shape itself. Most shapes just want
"face the direction of travel," so they build plain (x, y) points and pass
them through _with_tangent_angles(). A shape that wants different rotation
behavior computes its own angles instead -- no config file involved."""
import math

import config

SAMPLES_PER_SEGMENT = 128
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

def _with_tangent_angles(points, offset_fn=None, pivot_index: int | None = None) -> list[tuple[float, float, float]]:
    """Default rotation: each point faces the next point (last point reuses
    the final segment's direction).
 
    `offset_fn`, if given, is called as offset_fn(progress) for each point
    (progress: 0 at the first point, 1 at the last) and its return value
    (degrees) is added on top of the tangent angle -- so a shape can vary
    rotation along its own path without leaving this function.

    `pivot_index`, if set, keeps the inbound tangent on that corner vertex
    so rotation can ease onto the next leg via `sample_at_distance`."""
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
    if pivot_index is not None and 0 < pivot_index < len(triples):
        x, y, _ = triples[pivot_index]
        _, _, incoming = triples[pivot_index - 1]
        triples[pivot_index] = (x, y, incoming)
    return triples

def _line_points(p0, p1, n):
    """n evenly-spaced points from p0 to p1 (inclusive of both ends)."""
    x0, y0 = p0
    x1, y1 = p1
    return [(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1)) for i in range(n)]

def _circle_points(p0: tuple[float, float], r: float, a: float, b: float, CCW: bool, n: int) -> list[tuple[float, float]]:
    """n points along a circle of radius r centered at p0, from angle a to
    angle b (both radians), going counterclockwise if CCW else clockwise.

    Returns plain (x, y) points like _line_points
    """
    cx, cy = p0
    diff = (b - a) % (2 * math.pi)
    
    if not CCW:
        diff -= 2 * math.pi
    if diff == 0:
        diff = 2 * math.pi
    points = []
    for i in range(n):
        angle = a + diff * i / (n - 1) if n > 1 else a
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    return points

@register_shape("-")
def _straight_slide(start_pos: int, end_pos: int, samples: int) -> list[tuple[float, float]]:
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)
    points = _line_points((sx,sy), (ex,ey), samples)
    return _with_tangent_angles(points)

def _V_slide(start_position: int, middle_position: int, end_position: int, samples: int) -> list[tuple[float, float]]:
    """V slide: exactly three positions -- start, middle, end -- forming
    exactly two straight legs (start->middle, middle->end)."""
    sx, sy = config.lane_xy(start_position, config.RING_RADIUS)
    mx, my = config.lane_xy(middle_position, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_position, config.RING_RADIUS)

    half = samples // 2
    first_leg = _line_points((sx, sy), (mx, my), half + 1)
    second_leg = _line_points((mx, my), (ex, ey), samples - half)[1:]
    
    points = first_leg + second_leg
    return _with_tangent_angles(points, pivot_index=half)

@register_shape("v")
def _v_slide(start_pos: int, end_pos: int, samples: int) -> list[tuple[float, float]]:
    """v slide: start to center and center to end"""
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)
    center = (config.CENTER_X, config.CENTER_Y)
    half = samples // 2
    first_leg = _line_points((sx, sy), center, half + 1)
    second_leg = _line_points(center, (ex, ey), samples - half)[1:]
    points = first_leg + second_leg
    return _with_tangent_angles(points, pivot_index=half)

def _arc(start_pos: int, end_pos: int, samples: int, CCW: bool, shortest: bool) -> list[tuple[float, float]]:
    start_angle = config.lane_angle(start_pos)
    end_angle = config.lane_angle(end_pos)
    diff = (end_angle - start_angle) % (2 * math.pi)

    if not shortest:
        if start_pos not in (3,4,5,6):
            if not CCW:
                diff -= 2 * math.pi
        else:
            if CCW:
                diff -= 2 * math.pi
    else:
        if diff > math.pi:
            diff -= 2 * math.pi
        elif diff == math.pi or diff == 0:
            raise ValueError(f"Invalid ^ endpoint: {end_pos}")

    points = []
    for i in range(samples):
        angle = start_angle + diff * i / (samples - 1)
        x = config.CENTER_X + config.RING_RADIUS * math.cos(angle)
        y = config.CENTER_Y + config.RING_RADIUS * math.sin(angle)
        points.append((x, y))
    return _with_tangent_angles(points)

@register_shape("<")
def _arc_left(start_pos, end_pos, samples: int) -> list[tuple[float, float, float]]:
    return _arc(start_pos, end_pos, samples, CCW=True, shortest = False)

@register_shape(">")
def _arc_right(start_pos, end_pos, samples: int) -> list[tuple[float, float, float]]:
    return _arc(start_pos, end_pos, samples, CCW=False, shortest = False)

@register_shape("^")
def _arc_shortest(start_pos, end_pos, samples: int) -> list[tuple[float, float, float]]:
    return _arc(start_pos, end_pos, samples, CCW=False, shortest = True)

def _sz_slide(start_pos: int, end_pos: int, samples: int, z: bool) -> list[tuple[float, float]]:
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)
    if not z:
        fwx, fwy = config.lane_xy(((start_pos - 2 - 1) % 8) + 1, 200) # 200 is a side length of a right triangle create
        swx, swy = config.lane_xy(((end_pos - 2 - 1) % 8) + 1, 200) # by the first half of sz slide and radius
    else:
        fwx, fwy = config.lane_xy(((start_pos + 2 - 1) % 8) + 1, 200)
        swx, swy = config.lane_xy(((end_pos + 2 - 1) % 8) + 1, 200)
    base = (samples - 1) // 3
    remainder = (samples - 1) - base * 3

    first_leg = _line_points((sx, sy), (fwx, fwy), base + remainder + 1)
    second_leg = _line_points((fwx, fwy), (swx, swy), base + 1)[1:]
    third_leg = _line_points((swx, swy), (ex, ey), base + 1)[1:]

    points = first_leg + second_leg + third_leg
    return _with_tangent_angles(points)

@register_shape("s")
def _s_slide(start_pos, end_pos, samples) -> list[tuple[float, float, float]]:
    return _sz_slide(start_pos, end_pos, samples, z=False)

@register_shape("z")
def _s_slide(start_pos, end_pos, samples) -> list[tuple[float, float, float]]:
    return _sz_slide(start_pos, end_pos, samples, z=True)

def _pq_slide(start_pos: int, end_pos: int, samples: int, CCW: bool) -> list[tuple[float, float]]:
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)

    if not CCW:
        a = config.lane_angle(start_pos + 1.5)
        b = config.lane_angle(end_pos - 1.5)
    else:
        a = config.lane_angle(start_pos - 1.5)
        b = config.lane_angle(end_pos + 1.5)

    lsx = config.CENTER_X + config.PQ_RADIUS * math.cos(a)
    lsy = config.CENTER_Y + config.PQ_RADIUS * math.sin(a)

    lex = config.CENTER_X + config.PQ_RADIUS * math.cos(b)
    ley = config.CENTER_Y + config.PQ_RADIUS * math.sin(b)

    first_leg = _line_points((sx,sy), (lsx,lsy), 2)
    loop = _circle_points((config.CENTER_X,config.CENTER_Y), config.PQ_RADIUS, a,b, CCW, samples - 4)[1:]
    second_leg = _line_points((lex,ley), (ex,ey), 2)[1:]

    points = first_leg + loop + second_leg
    return _with_tangent_angles(points)

@register_shape("q")
def _q_slide(start_pos, end_pos, samples) -> list[tuple[float, float, float]]:
    return _pq_slide(start_pos, end_pos, samples, CCW=False)

@register_shape("p")
def _p_slide(start_pos, end_pos, samples) -> list[tuple[float, float, float]]:
    return _pq_slide(start_pos, end_pos, samples, CCW=True)

def _ppqq_slide(start_pos: int, end_pos: int, samples: int, CCW: bool) -> list[tuple[float, float]]:
    sx, sy = config.lane_xy(start_pos, config.RING_RADIUS)
    ex, ey = config.lane_xy(end_pos, config.RING_RADIUS)

    start_angle = config.lane_angle(start_pos)
    end_angle = config.lane_angle(end_pos)
    diff = (end_angle - start_angle) % (2 * math.pi)
    diff = round(diff/ math.pi,2)

    PPQQ_ANGLE = [240,264,288,324,0,408,120,204] # list of escape angle for the loop 
    index = int(diff*4)

    if CCW:
        a = config.lane_angle(start_pos - 3.5) - 1.09 # magic number
        centerx, centery = config.lane_xy(start_pos+1.5, config.PPQQ_HYP)
        b = a + math.radians(PPQQ_ANGLE[index])
    else:
        a = config.lane_angle(start_pos + 3.5) + 1.09
        centerx, centery = config.lane_xy(start_pos-1.5, config.PPQQ_HYP)
        b = a - math.radians(PPQQ_ANGLE[-index])

    lsx = centerx + config.PPQQ_RADIUS * math.cos(a)
    lsy = centery + config.PPQQ_RADIUS * math.sin(a)

    lex = centerx + config.PPQQ_RADIUS * math.cos(b)
    ley = centery + config.PPQQ_RADIUS * math.sin(b)

    first_leg = _line_points((sx,sy), (lsx,lsy), 2)
    if CCW and index == 5:
        loop = _circle_points((centerx,centery), config.PPQQ_RADIUS, a,a, CCW, (samples - 4)//2)[1:]
        extra = _circle_points((centerx,centery), config.PPQQ_RADIUS, a, a + math.radians(48), CCW, (samples - 4)//2)[1:]
    elif not CCW and index == 3:
        loop = _circle_points((centerx,centery), config.PPQQ_RADIUS, a,a, CCW, (samples - 4)//2)[1:]
        extra = _circle_points((centerx,centery), config.PPQQ_RADIUS, a, a - math.radians(48), CCW, (samples - 4)//2)[1:]
    else:
        loop = _circle_points((centerx,centery), config.PPQQ_RADIUS, a,b, CCW, samples - 4)[1:]
        extra = []
    second_leg = _line_points((lex,ley), (ex,ey), 2)[1:]

    points = first_leg + loop + extra+ second_leg
    return _with_tangent_angles(points)

@register_shape("pp")
def _pp_slide(start_pos, end_pos, samples) -> list[tuple[float, float, float]]:
    return _ppqq_slide(start_pos, end_pos, samples, CCW=True)

@register_shape("qq")
def _qq_slide(start_pos, end_pos, samples) -> list[tuple[float, float, float]]:
    return _ppqq_slide(start_pos, end_pos, samples, CCW=False)

def _segment(start_pos: int, end_pos: int, shape: str, samples: int) -> list[tuple[float, float, float]]:
    handler = SHAPE_HANDLERS.get(shape, _v_slide)
    return handler(start_pos, end_pos, samples)

def build_path(start_position: int, waypoints: list[int], shape: str) -> list[tuple[float, float, float]]:
    """Return an ordered list of (x, y, angle_degrees) tracing a slide's full path.
 
    `waypoints` is everything after the start position -- for most shapes
    that's a single endpoint; "V" slides have two legs, so two waypoints.
    """
    if shape == "V":
        if len(waypoints) != 2:
            raise ValueError(
                f"'V' slide needs exactly 2 waypoints (middle, end), got {waypoints!r}"
            )
        middle_position, end_position = waypoints
        return _V_slide(start_position, middle_position, end_position, SAMPLES_PER_SEGMENT)
    
    stops = [start_position] + waypoints
    points: list[tuple[float, float,float]] = []
    for i in range(len(stops) - 1):
        segment = _segment(stops[i], stops[i + 1], shape, SAMPLES_PER_SEGMENT)
        if points:
            segment = segment[1:]
        points.extend(segment)
    return points

# x0, y0 = config.lane_xy(3, config.RING_RADIUS)
# print(x0-340.3,y0+161.2)
# x1, y1 = config.lane_xy(5, 480)
# print(_tangent_angle_deg(x0, y0, x1, y1))
# print(_straight(4,8,2))

# a = build_path(1,[4],"-")
# print(a)
