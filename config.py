"""Configuration constants for the maimai chart renderer."""
import math

WIDTH = 1080
HEIGHT = 1080
SCREEN_RADIUS = WIDTH / 2
FPS = 60

# Radius of the judgment ring (where notes are hit) in pixels.
RING_RADIUS = SCREEN_RADIUS * 8/9

# Radius at which notes first spawn (edge of the approach path).
SPAWN_RADIUS = SCREEN_RADIUS * 2/9
A_SENSOR_RADIUS = SCREEN_RADIUS * 40/54
B_SENSOR_RADIUS = SCREEN_RADIUS * 22/54
D_SENSOR_RADIUS = SCREEN_RADIUS * 41/54
# E_SENSOR_RADIUS

# How many seconds before a note's hit time it should first appear on screen.
APPROACH_TIME = (RING_RADIUS - SPAWN_RADIUS) / ((107.25 / (71.4184491 * (8 + 0.9975)**-0.985558604))*FPS) # d / v = t
# print(APPROACH_TIME)

CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

# Sprites are loaded via pyglet.resource, which resolves relative to
# whatever pyglet.resource.path is set to (see main.py).
ASSET_DIR = "assets"

# Misc
RING_SIZE = 980
ARROW_SPACING = 0.098017 * RING_RADIUS

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
    "arrow": "arrow.png"
}

_TYPE_NAMES = {0: "tap", 1: "star", 2: "hold"}

def note_variant(note, is_each: bool = False) -> str:
    """Map a Note to the sprite variant key that should render its head."""
    base = _TYPE_NAMES.get(note.type, "tap")
    if note.is_break:
        return f"{base}_break"
    if is_each:
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