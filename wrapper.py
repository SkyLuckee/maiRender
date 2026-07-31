from pythonnet import load
load("coreclr")

import clr
import sys
import os
import json
import tkinter as tk
from tkinter import filedialog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DLL_DIR = SCRIPT_DIR  # DLL sits next to the script

sys.path.append(DLL_DIR)
clr.AddReference("MajSimai")

from MajSimai import SimaiParser # type: ignore
from System.IO import FileStream, FileMode, FileAccess # type: ignore
from System.Reflection import BindingFlags # type: ignore

DIFFICULTY_NAMES = ["EASY", "BASIC", "ADVANCED", "EXPERT", "MASTER", "Re_MASTER", "UTAGE"]

# ---- Parser ----
def get_note_timings(chart):
    field = chart.GetType().GetField("_noteTimings", BindingFlags.NonPublic | BindingFlags.Instance)
    return list(field.GetValue(chart))

def note_to_dict(n):
    d = {
        "Type": int(getattr(n, "Type")),
        "StartPosition": getattr(n, "StartPosition"),
        "HoldTime": getattr(n, "HoldTime"),
        "IsBreak": getattr(n, "IsBreak"),
        "IsEx": getattr(n, "IsEx"),
        "IsFakeRotate": getattr(n, "IsFakeRotate"),
        "IsForceStar": getattr(n, "IsForceStar"),
        "IsHanabi": getattr(n, "IsHanabi"),
        "IsSlideBreak": getattr(n, "IsSlideBreak"),
        "IsSlideNoHead": getattr(n, "IsSlideNoHead"),
        "IsMine": getattr(n, "IsMine"),
        "IsMineSlide": getattr(n, "IsMineSlide"),
        "RawContent": getattr(n, "RawContent"),
        "SlideStartTime": getattr(n, "SlideStartTime"),
        "SlideTime": getattr(n, "SlideTime"),
        "TouchArea": getattr(n, "TouchArea"),
    }

    for key in ["IsBreak", "IsEx", "IsFakeRotate", "IsForceStar", "IsHanabi",
                "IsSlideBreak", "IsSlideNoHead", "IsMine", "IsMineSlide"]:
        if d[key] is False:
            del d[key]

    if d["Type"] != 1:
        del d["SlideStartTime"]
        del d["SlideTime"]

    if d["Type"] not in (2, 4):
        del d["HoldTime"]

    if d["Type"] not in (3, 4):
        del d["TouchArea"]

    return d

def timing_point_to_dict(tp):
    d = {
        "Timing": tp.Timing,
        "Bpm": tp.Bpm,
        "RawContent": tp.RawContent,
        "Notes": [note_to_dict(n) for n in tp.Notes],
        "IsEmpty": tp.IsEmpty,
    }
    if d["IsEmpty"] == False:
        del d["IsEmpty"]
    return d

def chart_to_dict(simai_file, chart, diff_index):
    return {
        "title": simai_file.Title,
        "artist": simai_file.Artist,
        "designer": chart.Designer,
        "difficulty": DIFFICULTY_NAMES[diff_index],
        "diffNum": diff_index,
        "level": chart.Level,
        "timingList": [timing_point_to_dict(tp) for tp in get_note_timings(chart)],
    }

def metadata_to_dict(simai_file, chart_results):
    """File-level metadata, independent of any single chart/difficulty."""
    return {
        "title": simai_file.Title,
        "artist": simai_file.Artist,
        "finalDesigner": simai_file.FinalDesigner,
        "offset": simai_file.Offset,
        "hash": simai_file.Hash,
        "charts": [
            {
                "difficulty": r["difficulty"],
                "diffNum": r["diffNum"],
                "level": r["level"],
                "designer": r["designer"],
            }
            for r in chart_results
        ],
    }

def parse_maidata(maidata_path):
    """Parses a maidata.txt and returns (chart_results, metadata).
    chart_results is a list of chart dicts (one per non-empty difficulty).
    metadata is a single dict of file-level info."""
    stream = FileStream(maidata_path, FileMode.Open, FileAccess.Read)
    try:
        simai_file = SimaiParser.Parse(stream)
    finally:
        stream.Close()

    results = []
    for i, chart in enumerate(simai_file.Charts):
        if chart is None or not chart.Level:
            continue
        if i > 3:
            results.append(chart_to_dict(simai_file, chart, i))

    metadata = metadata_to_dict(simai_file, results)

    return results, metadata

# ---- tk ----
def prompt_for_file():
    """Opens a file picker dialog and returns the selected path, or '' if cancelled."""
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select maidata.txt",
        initialdir=SCRIPT_DIR,
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    root.destroy()
    return path

# ---- Write Json ---- (Debug only)
def write_results(results, output_dir):
    """Writes one JSON file per chart into output_dir"""
    written = []
    for result in results:
        diff_name = result["difficulty"]
        output_path = os.path.join(output_dir, f"maigraph_{diff_name}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=True, separators=(",", ":"), indent = 2)
        written.append(output_path)
    return written

def write_metadata(metadata, output_dir):
    """Writes the file-level metadata dict to metadata.json"""
    output_path = os.path.join(output_dir, "metadata.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=True, separators=(",", ":"), indent=2)
    return output_path

# ---- Main ----
def wrapper(DEBUG = False):
    """Prompts for a maidata.txt file and returns (results, metadata, source_dir), or None if cancelled/empty."""
    maidata_path = prompt_for_file()

    if not maidata_path:
        print("No file selected.")
        return None

    results, metadata = parse_maidata(maidata_path)
    if not results:
        print("No charts found.")
        return None

    if DEBUG:
        for path in write_results(results,  os.path.join(SCRIPT_DIR, "testing")):
            print(f"Wrote {path}")
        print(f"Wrote {write_metadata(metadata,  os.path.join(SCRIPT_DIR, "testing"))}")

    return {
        "results": results[1] if len(results) > 1 else results[0], 
        "metadata": metadata, 
        "source_dir": os.path.dirname(maidata_path)
        }

if __name__ == "__main__": # debug
    chart = wrapper(False)
    print(chart["source_dir"])