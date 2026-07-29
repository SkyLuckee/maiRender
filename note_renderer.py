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
            img.anchor_x = img.width // 2 - 9
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
        self._visuals: dict[int, TapVisual | HoldVisual | SlideVisual | TouchVisual | TouchHoldVisual] = {}

    def update(self, t: float) -> None:
        while self._next_index < len(self.notes):
            note = self.notes[self._next_index]
            if note.time - 2 * config.APPROACH_TIME > t:
                break

            if note.type == 2:
                variant = config.note_variant(note, is_each=note.is_each)
                visual = HoldVisual(
                    note,
                    self.images[f"{variant}_head"],
                    self.images[f"{variant}_body"],
                    self.images[f"{variant}_tail"],
                    self.batch,
                )
            elif note.type == 1 and (note.slide_shape is not None or note.slide_segments):
                head_variant = config.note_variant(note, is_each=note.is_each)
                head_image = self.images.get(head_variant, self.images["tap"])

                # Tracer uses slide-specific flags rather than the note's
                # general is_each/is_break, so it can be skinned separately
                # from the head.
                tracer_variant = config.note_variant(
                    note,
                    is_each=note.is_slide_each,
                    is_break=note.is_slide_break
                )
                tracer_image = self.images.get(tracer_variant, self.images["tap"])

                if note.is_slide_break:
                    path_image = self.images["slide_break"]
                elif note.is_slide_each:
                    path_image = self.images["slide_each"]
                else:
                    path_image = self.images["slide"]
                visual = SlideVisual(note, head_image, tracer_image, path_image, self.batch)

            elif note.type == 3:
                point_variant = config.note_variant(note, is_each = note.is_each)
                point_image = self.images.get(point_variant, self.images["tap"])

                if note.is_each:
                    slice_image = self.images["slice_each"]
                else:
                    slice_image = self.images["slice"]

                visual = TouchVisual(note, point_image, slice_image, note.touch_area, self.batch)

            elif note.type == 4:
                point_variant = config.note_variant(note, is_each = note.is_each)
                point_image = self.images.get(point_variant, self.images["tap"])

                visual = TouchHoldVisual(note, point_image, note.touch_area, self.batch)
                
            else:
                variant = config.note_variant(note, is_each=note.is_each)
                image = self.images.get(variant, self.images["tap"])
                visual = TapVisual(note, image, self.batch)

            self._visuals[self._next_index] = visual
            self._next_index += 1

        expired = []
        for idx, visual in self._visuals.items():
            note = self.notes[idx]
            visual.update(t, note)
            if t > note.end_time + 0.016:
                expired.append(idx)

        for idx in expired:
            self._visuals.pop(idx).delete()