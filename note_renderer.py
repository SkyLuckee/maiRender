"""Top-level note renderer: owns the per-note spawn/expiry lifecycle and
dispatches to the per-type visual classes in tap_render / hold_render /
slide_render. All three visual classes share the same tiny interface --
update(t, note) and delete() -- so this loop never branches on note.type
except once, at spawn time, to decide which class to build.
"""

from __future__ import annotations
import pyglet

import config
from chart import Note
from render_common import Visual
from tap_render import TapVisual
from hold_render import HoldVisual, slice_hold_regions, HOLD_VARIANTS
from slide_render import SlideVisual
from touch_render import TouchVisual
from touchhold_render import TouchHoldVisual


def load_note_images() -> dict[str, pyglet.image.AbstractImage]:
    images = {}
    for variant, filename in config.NOTE_IMAGE_FILES.items():
        img = pyglet.resource.image(filename)

        if variant in HOLD_VARIANTS:
            head, body, tail = slice_hold_regions(img)
            images[f"{variant}_head"] = head
            images[f"{variant}_body"] = body
            images[f"{variant}_tail"] = tail
            continue

        if variant in ("slide", "slide_each","slide_break"):
            img.anchor_x = img.width - 36 # 43
        else:
            img.anchor_x = img.width // 2

        if variant in ("slice", "slice_each"):
            img.anchor_y = img.height - 15
        else:
            img.anchor_y = img.height // 2
        images[variant] = img
    return images


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
        self._visuals: dict[int, Visual] = {}

    # Global image lookups
    def _variant_image(self, note: Note, *, is_each: bool, is_break: bool | None = None):
        """Look up the sprite for a note's variant, falling back to the
        tap image if this chart doesn't skin that variant."""
        variant = config.note_variant(note, is_each=is_each, is_break=is_break)
        return self.images.get(variant, self.images["tap"])

    # one builder per note type

    def _build_hold(self, note: Note) -> HoldVisual:
        variant = config.note_variant(note, is_each=note.is_each)
        return HoldVisual(
            note,
            self.images[f"{variant}_head"],
            self.images[f"{variant}_body"],
            self.images[f"{variant}_tail"],
            self.batch,
        )

    def _build_slide(self, note: Note) -> SlideVisual:
        head_image = self._variant_image(note, is_each=note.is_each)

        # Tracer uses slide-specific flags rather than the note's general
        # is_each/is_break, so it can be skinned separately from the head.
        tracer_image = self._variant_image(
            note, is_each=note.is_slide_each, is_break=note.is_slide_break
        )

        if note.is_slide_break:
            path_image = self.images["slide_break"]
        elif note.is_slide_each:
            path_image = self.images["slide_each"]
        else:
            path_image = self.images["slide"]

        return SlideVisual(note, head_image, tracer_image, path_image, self.batch)

    def _build_touch(self, note: Note) -> TouchVisual:
        point_image = self._variant_image(note, is_each=note.is_each)
        slice_image = self.images["slice_each" if note.is_each else "slice"]
        return TouchVisual(note, point_image, slice_image, note.touch_area, self.batch)

    def _build_touchhold(self, note: Note) -> TouchHoldVisual:
        point_image = self._variant_image(note, is_each=note.is_each)
        return TouchHoldVisual(note, point_image, note.touch_area, self.batch)

    def _build_tap(self, note: Note) -> TapVisual:
        image = self._variant_image(note, is_each=note.is_each)
        return TapVisual(note, image, self.batch)

    def _build_visual(self, note: Note):
        """Pick the right builder for this note. The only place note.type
        (and, for slides, the presence of shape/segments) is inspected."""
        if note.type == 2:
            return self._build_hold(note)
        if note.type == 1 and (note.slide_shape is not None or note.slide_segments):
            return self._build_slide(note)
        if note.type == 3:
            return self._build_touch(note)
        if note.type == 4:
            return self._build_touchhold(note)
        return self._build_tap(note)

    def update(self, t: float) -> None:
        while self._next_index < len(self.notes):
            note = self.notes[self._next_index]
            if note.time - 2 * config.APPROACH_TIME > t:
                break

            self._visuals[self._next_index] = self._build_visual(note)
            self._next_index += 1

        expired = []
        for idx, visual in self._visuals.items():
            note = self.notes[idx]
            visual.update(t, note)
            if t > note.end_time + 0.016:
                expired.append(idx)

        for idx in expired:
            self._visuals.pop(idx).delete()