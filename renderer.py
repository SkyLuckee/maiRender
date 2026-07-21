"""Drawing logic for the chart renderer: turns Note objects + elapsed time into on-screen sprites."""
import math
import pyglet

import config
from chart import Note
from slide_path import build_path

def _face_center_rotation(position: int) -> float:
    """Sprite rotation (degrees, clockwise) facing inward."""
    return 90 - math.degrees(config.lane_angle(position))

def _cumulative_lengths(path) -> list[float]:
    """Running arc-length total up to each point in `path`."""
    lengths = [0.0]
    for i in range(1, len(path)):
        x0, y0, _ = path[i - 1]
        x1, y1, _ = path[i]
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    return lengths

def _sample_at_distance(path, lengths, dist: float) -> tuple[float, float, float]:
    """Return (x, y, tangent_angle_degrees) at arc-length `dist` along `path`."""
    i = next((i for i in range(1, len(lengths)) if lengths[i] >= dist), len(lengths) - 1)
    x0, y0, angle = path[i - 1]
    x1, y1, _ = path[i]
    seg_len = lengths[i] - lengths[i - 1]
    frac = 0.0 if seg_len == 0 else max(0.0, min(1.0, (dist - lengths[i - 1]) / seg_len))
    x = x0 + (x1 - x0) * frac
    y = y0 + (y1 - y0) * frac
    return x, y, angle

def _slide_placements(path, lengths, spacing: float):
    """Evenly-spaced (x, y, angle) triples along `path`, `spacing` pixels apart.

    Stops before placing one that would land closer than half a spacing to
    the endpoint, so the last slide never crowds the slide's end.
    """
    total = lengths[-1]
    placements = []
    dist = 0.0
    while total - dist >= spacing / 2:
        placements.append(_sample_at_distance(path, lengths, dist))
        dist += spacing
    # print(placements)
    return placements

class _SlideBody:
    """A chain of slide sprites tracing one slide's path, revealed progressively."""
    def __init__(self, note, image, batch):
        self.path = build_path(note.position, note.slide_waypoints or [], note.slide_shape or "-")
        self.lengths = _cumulative_lengths(self.path)
        self.total_length = self.lengths[-1]
        placements = _slide_placements(self.path, self.lengths, config.SLIDE_SPACING)
        self.sprites = []
        self.distances = [i * config.SLIDE_SPACING for i in range(len(placements))]
        group = pyglet.graphics.Group(order=_draw_order(config.SLIDE_LAYER, note.time))
        for x, y, angle in placements:
            sprite = pyglet.sprite.Sprite(image, x=x, y=y, batch=batch, group=group)
            sprite.rotation = angle
            self.sprites.append(sprite)
        self._consumed = 0
    
    def head_position(self, progress: float) -> tuple[float, float]:
        """Uses the same arc-length model (self.lengths / self.total_length)
        as consume() and the arrow placements, so the star and the arrows
        can never disagree about how far "progress" has gotten."""
        dist = max(0.0, min(1.0, progress)) * self.total_length
        x, y, _ = _sample_at_distance(self.path, self.lengths, dist)
        return x, y
    
    def consume(self, progress: float) -> None:
        """Destroy slides the star has already passed, in order."""
        covered = progress * self.total_length
        while self._consumed < len(self.sprites) and self.distances[self._consumed] <= covered:
            self.sprites[self._consumed].delete()
            self.sprites[self._consumed] = None
            self._consumed += 1

    def delete(self) -> None:
        for sprite in self.sprites:
            if sprite is not None:
                sprite.delete()

class _HoldVisual:
    """Head, body, and tail sprites for one hold note.

    Head approaches the ring like a normal note, arriving at note.time and
    staying pinned there. Tail uses the exact same approach formula but
    targets note.end_time instead -- since head_progress/tail_progress are
    both clamped to [0, 1], the tail naturally sits still at SPAWN_RADIUS
    until its own approach window opens, with no separate branch needed.
    The body sprite is repositioned and vertically re-scaled every frame
    to span exactly the current gap between head and tail.
    """
    def __init__(self, note: Note, head_img, body_img, tail_img,
                 batch: pyglet.graphics.Batch, group: pyglet.graphics.Group):
        rotation = _face_center_rotation(note.position)
        self.head = pyglet.sprite.Sprite(head_img, batch=batch, group=group)
        self.body = pyglet.sprite.Sprite(body_img, batch=batch, group=group)
        self.tail = pyglet.sprite.Sprite(tail_img, batch=batch, group=group)
        for sprite in (self.head, self.body, self.tail):
            sprite.rotation = rotation
        self._body_native_height = body_img.height or 1

    def update(self, t: float, note: Note) -> None:
        head_progress = (t - (note.time - config.APPROACH_TIME)) / config.APPROACH_TIME
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

        # head_radius >= tail_radius always (head reaches the ring first and
        # stays there; tail can never overtake it), so this gap is never negative.
        self.body.x, self.body.y = tx, ty
        gap = head_radius - tail_radius
        self.body.scale_y = gap / self._body_native_height

    def delete(self) -> None:
        self.head.delete()
        self.body.delete()
        self.tail.delete()

_HOLD_VARIANTS = ("hold", "hold_break", "hold_each")

def _slice_hold_regions(img: pyglet.image.AbstractImage):
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

def load_note_images() -> dict[str, pyglet.image.AbstractImage]:
    images = {}
    for variant, filename in config.NOTE_IMAGE_FILES.items():
        img = pyglet.resource.image(filename)

        if variant in _HOLD_VARIANTS:
            head, body, tail = _slice_hold_regions(img)
            images[f"{variant}_head"] = head
            images[f"{variant}_body"] = body
            images[f"{variant}_tail"] = tail
            continue

        if variant in ("slide", "slide_each"):
            img.anchor_x = img.width // 2 - 9
        else:
            img.anchor_x = img.width // 2

        img.anchor_y = img.height // 2
        images[variant] = img
    return images

def _draw_order(tier: int, note_time: float) -> float:
    """Group order for a note's sprite(s): lower draws first (behind).
    Tiers are separated by LAYER_GAP so they never overlap. Within a tier,
    later notes get a LOWER order (drawn first/behind) so earlier notes
    end up rendered on top of later ones.
    """
    return tier * config.LAYER_GAP - note_time

class NoteRenderer:
    def __init__(
        self,
        notes: list[Note],
        batch: pyglet.graphics.Batch,
        images: dict[str, pyglet.image.AbstractImage],
    ):
        self.notes = notes
        self.batch = batch
        self.images = images
        self._next_index = 0
        self._active: dict[int, tuple[Note, pyglet.sprite.Sprite | None]] = {}
        self._slide_bodies: dict[int, _SlideBody] = {}
        self._hold_visuals: dict[int, _HoldVisual] = {}

    def update(self, t: float) -> None:
        while self._next_index < len(self.notes):
            note = self.notes[self._next_index]
            if note.time - 2 * config.APPROACH_TIME > t:
                break
            
            if note.type == 2:
                # No single spawn sprite for holds -- head/body/tail are
                # created lazily below, once the hold's own approach window
                # opens (note.time - APPROACH_TIME), not before.
                self._active[self._next_index] = (note, None)
                self._next_index += 1
                continue

            variant = config.note_variant(note, is_each=note.is_each)
            image = self.images.get(variant, self.images["tap"])

            group = pyglet.graphics.Group(order=_draw_order(config.TAP_LAYER, note.time))
            sprite = pyglet.sprite.Sprite(image, batch=self.batch, group=group)
            sprite.rotation = _face_center_rotation(note.position)
            sprite.scale = 0.0
            self._active[self._next_index] = (note, sprite)
            self._next_index += 1

        expired = []
        for idx, (note, sprite) in self._active.items():
            if note.type == 2:
                move_start = note.time - config.APPROACH_TIME
                if idx not in self._hold_visuals and t >= move_start:
                    variant = config.note_variant(note, is_each=note.is_each)
                    group = pyglet.graphics.Group(order=_draw_order(config.HOLD_LAYER, note.time))
                    self._hold_visuals[idx] = _HoldVisual(
                        note,
                        self.images[f"{variant}_head"],
                        self.images[f"{variant}_body"],
                        self.images[f"{variant}_tail"],
                        self.batch,
                        group,
                    )
                visual = self._hold_visuals.get(idx)
                if visual is not None:
                    visual.update(t, note)

                if t > note.end_time + 0.05:
                    expired.append(idx)
                continue
            is_moving_slide = (
                note.type == 1
                and note.slide_shape is not None
                and note.slide_time
                and t >= note.slide_start_time
            )

            if note.type == 1 and note.slide_shape is not None:
                if idx not in self._slide_bodies and t >= note.time:
                    self._slide_bodies[idx] = _SlideBody(note,  self.images["slide_each"] if (note.is_slide_each) else self.images["slide"], self.batch)
            
            if is_moving_slide:
                sprite.scale = 1
                body = self._slide_bodies[idx]
                slide_progress = max(0.0, min(1.0, (t - note.slide_start_time) / note.slide_time))
                x, y = body.head_position(slide_progress)
                body.consume(slide_progress)
            else:
                move_start = note.time - config.APPROACH_TIME
                if t < move_start:
                    # Phase 1: scale up 0 -> 1 at the spawn location, not moving yet.
                    spawn_start = note.time - 2 * config.APPROACH_TIME
                    scale_progress = (t - spawn_start) / config.APPROACH_TIME
                    sprite.scale = max(0.0, min(1.0, scale_progress))
                    x, y = config.lane_xy(note.position, config.SPAWN_RADIUS)
                else:
                    # Phase 2: full scale, existing approach-to-ring movement.
                    sprite.scale = 1.0
                    head_progress = (t - move_start) / config.APPROACH_TIME
                    head_progress = max(0.0, min(1.0, head_progress))
                    radius = config.SPAWN_RADIUS + (config.RING_RADIUS - config.SPAWN_RADIUS) * head_progress
                    x, y = config.lane_xy(note.position, radius)

            sprite.x, sprite.y = x, y

            if t > note.end_time + 0.05: # 50 mili kill time
                expired.append(idx)

        for idx in expired:
            note, sprite = self._active[idx]
            if sprite is not None:
                sprite.delete()
            self._active.pop(idx)
            body = self._slide_bodies.pop(idx, None)
            if body is not None:
                body.delete()
            visual = self._hold_visuals.pop(idx, None)
            if visual is not None:
                visual.delete()