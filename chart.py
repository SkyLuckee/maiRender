"""Load a maimai chart JSON export and flatten it into a time-sorted list of Note objects."""
from dataclasses import dataclass
from typing import Optional
import json
from compound_slide_path import parse_slide


@dataclass
class Note:
    time: float
    position: int
    type: int 
    raw_content: str
    is_break: bool = False
    is_each: bool = False
    hold_time: Optional[float] = None
    slide_start_time: Optional[float] = None
    slide_time: Optional[float] = None
    slide_shape: Optional[str] = None
    slide_waypoints: Optional[list[int]] = None
    slide_segments: Optional[list[tuple[str, int]]] = None
    is_slide_each: bool = False
    is_slide_break: bool = False
    touch_area: Optional[str] = None

    @property
    def end_time(self) -> float:
        """Time at which this note is fully resolved (for holds/slides)."""
        if (self.type == 2 or self.type == 4)and self.hold_time is not None:
            return self.time + self.hold_time
        if self.type == 1 and self.slide_start_time is not None and self.slide_time is not None:
            return self.slide_start_time + self.slide_time
        return self.time


@dataclass
class Chart:
    title: str
    artist: str
    designer: str
    difficulty: str
    diff_num: int
    level: str
    notes: list[Note]


def load_chart(path: str) -> Chart:
    """Load a chart directly and flatten timingList into a sorted Note list."""
    data = path

    notes: list[Note] = []
    for entry in data["timingList"]:
        time = entry["Timing"]
        is_each = len(entry["Notes"]) > 1
        is_slide_each = sum(1 for n in entry["Notes"] if n["Type"] == 1) > 1

        for n in entry["Notes"]:
            if n["Type"] == 1:
                slide_shape, slide_waypoints, slide_segments = parse_slide(n["RawContent"])
            else:
                slide_shape = slide_waypoints = slide_segments = None
            notes.append(
                Note(
                    time=time,
                    position=n["StartPosition"],
                    type=n["Type"],
                    raw_content=n.get("RawContent", ""),
                    is_break=n.get("IsBreak", False),
                    is_each=is_each,
                    hold_time=n.get("HoldTime"),
                    slide_start_time=n.get("SlideStartTime"),
                    slide_time=n.get("SlideTime"),
                    slide_shape=slide_shape,
                    slide_waypoints=slide_waypoints,
                    slide_segments=slide_segments,
                    is_slide_each = is_slide_each,
                    is_slide_break = n.get("IsSlideBreak", False),
                    touch_area=n.get("TouchArea")
                )
            )

    notes.sort(key=lambda note: note.time)

    return Chart(
        title=data.get("title", ""),
        artist=data.get("artist", ""),
        designer=data.get("designer", ""),
        difficulty=data.get("difficulty", ""),
        diff_num=data.get("diffNum", 0),
        level=data.get("level", ""),
        notes=notes,
    )
