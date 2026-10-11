"""
A simple campus map: known places, the block they belong to, and x/y
coordinates in metres from the main gate. Used to turn a free-text
location ("near B block hostel") into a point for hotspot clustering.
Edit PLACES to match the real campus.
"""
import re

# name: (block, x_metres, y_metres, [aliases people actually write])
PLACES = {
    "A Block Hostel": ("A Block", 100, 400, ["a block", "a-block", "hostel a"]),
    "B Block Hostel": ("B Block", 160, 400, ["b block", "b-block", "hostel b"]),
    "C Block Hostel": ("C Block", 220, 400, ["c block", "c-block", "hostel c"]),
    "Girls Hostel": ("Girls Hostel", 420, 430, ["girls hostel", "ladies hostel", "g block"]),
    "Main Mess": ("Mess Hall", 250, 300, ["mess", "dining hall", "canteen"]),
    "Library": ("Library", 300, 200, ["library", "reading room"]),
    "CSE Lab": ("Academic Block 1", 350, 150, ["cse lab", "computer lab", "programming lab"]),
    "Physics Lab": ("Academic Block 2", 420, 150, ["physics lab", "chemistry lab", "science lab"]),
    "Main Gate": ("Main Gate", 0, 0, ["main gate", "gate", "security post"]),
    "Bus Bay": ("Transport Yard", 50, 60, ["bus bay", "bus stop", "parking", "bus stand"]),
    "Auditorium": ("Admin Block", 300, 90, ["auditorium", "admin block", "office"]),
    "Sports Ground": ("Ground", 520, 300, ["ground", "sports", "playground", "gym"]),
}

# Block names (used for per-block statistics).
BLOCKS = sorted({block for block, *_ in PLACES.values()})


def _normalise(text):
    return re.sub(r"\s+", " ", (text or "").lower())


def locate(*texts):
    """
    Find the first known place mentioned in the given texts.
    Returns (place_name, block, x, y) or None.
    Longer aliases are checked first so "girls hostel" wins over "hostel".
    """
    haystack = " ".join(_normalise(t) for t in texts if t)
    candidates = []
    for name, (block, x, y, aliases) in PLACES.items():
        for alias in [name.lower(), block.lower(), *aliases]:
            candidates.append((alias, name, block, x, y))
    for alias, name, block, x, y in sorted(candidates, key=lambda c: -len(c[0])):
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", haystack):
            return name, block, x, y
    return None
