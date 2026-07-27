"""Configuration constants for the maimai chart renderer."""
import math
import os

# Setting
WIDTH = 1080
HEIGHT = 1080
SCREEN_RADIUS = HEIGHT / 2
FPS = 60
TAP_SPEED = 8
TRACK_VOLUME = 0.5

# For positioning
# Radius of the judgment ring (where notes are hit) in pixels.
RING_RADIUS = SCREEN_RADIUS * 8/9

# Radius at which notes first spawn (edge of the approach path).
SPAWN_RADIUS = SCREEN_RADIUS * 2/9
# Radius for touch note
SENSOR_RADIUS = {
    "A": SCREEN_RADIUS * 40/54,
    "B": SCREEN_RADIUS * 22/54,
    "C": 0,
    "D": SCREEN_RADIUS * 41/54,
    "E": SCREEN_RADIUS * 31/54,
}

PQ_RADIUS = 183.6870475 #SCREEN_RADIUS * 8/9 * math.sin(math.pi/8)
PPQQ_RADIUS = 223.3084370661     #0.413534142715 * SCREEN_RADIUS | magic number, doesnt matter anyway
PPQQ_HYP = 220.1537394 # distance from ppqq center point to the origin

# How many seconds before a note's hit time it should first appear on screen.
APPROACH_TIME = 2.4 / TAP_SPEED # 300ms for speed 8
# print(APPROACH_TIME)

CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2


# Asset
# Sprites are loaded via pyglet.resource, which resolves relative to
# whatever pyglet.resource.path is set to (see main.py).
ASSET_DIR = "assets"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(SCRIPT_DIR, "testing")

# Misc
RING_SIZE = RING_RADIUS * 2 + 20 # 20 for sprite offset
SLIDE_SPACING = 0.098017 * RING_RADIUS # side length of a 32 gon
HOLD_HEAD_TAIL_SIZE = 70.4367  # px height of the head/tail crop

NOTE_IMAGE_FILES = {
    "tap": "tap.png",
    "tap_break": "tap_break.png",
    "tap_each": "tap_each.png",
    "hold": "hold.png",
    "hold_break": "hold_break.png",
    "hold_each": "hold_each.png",
    "star": "star.png",
    "star_break": "star_break.png",
    "star_each": "star_each.png",
    "slide": "slide.png",
    "slide_each": "slide_each.png",
    "slide_break": "slide_break.png",
    "touch": "touch_point.png",
    "touch_each": "touch_point_each.png",
    "slice": "touch.png",
    "slice_each": "touch_each.png"
}

_TYPE_NAMES = {0: "tap", 1: "star", 2: "hold", 3: "touch", 4: "touch"}

# Draw-order tiers, lowest = drawn first = appears behind.
SLIDE_LAYER = 1   # the whole slide path (all its arrows), not per-arrow
TAP_LAYER = 2     # tap AND star/slide-head, all variants including break
HOLD_LAYER = 3
TOUCH_LAYER = 4
LAYER_GAP = 1_000_000  # keeps tiers from ever overlapping regardless of chart length

def note_variant(note, is_each: bool = False, is_break: bool | None = None) -> str:
    """Map a Note to the sprite variant key that should render its head."""
    base = _TYPE_NAMES.get(note.type, "tap")
    if is_break is None: # fallback
        is_break = note.is_break
    if is_break:
        return f"{base}_break"
    elif is_each:
        return f"{base}_each"
    return base


def lane_angle(position: int) -> float:
    """Return the angle (degree) for ring position 1-8, position 1 = top, clockwise."""
    degrees = 67.5 - (position - 1) * 45
    return math.radians(degrees)
# pos 1: 67.5
# pos 2: 22.5
# pos 3: -22.5
# pos 4: -67.5
# pos 5: -112.5
# pos 6: -157.5
# pos 7: -202.5
# pos 8: -247.5

def lane_xy(position: int, radius: float) -> tuple[float, float]:
    """Return (x, y) on the circle of given radius for a lane position."""
    angle = lane_angle(position)
    x = CENTER_X + radius * math.cos(angle)
    y = CENTER_Y + radius * math.sin(angle)
    return x, y