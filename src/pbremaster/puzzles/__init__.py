"""The ten puzzle types. Each game draws inside the 650x540 play area at (75, 42)
of the puzzle screen (where every puzzle's background, e.g. FPN/312.PNG, sits on
SCREENS/300.RIM)."""
from __future__ import annotations


def game_for(kind_name):
    from .findfill import FindAndFill
    from .focuspoint import FocusPoint
    from .imagehole import ImageHole
    from .interlock import Interlock
    from .jesse import JessesStrips
    from .lensbender import LensBender
    from .overlap import Overlap
    from .rotascope import Rotascope
    from .slices import Slices
    return {"Focus Point": FocusPoint, "Rotascope": Rotascope, "Image Hole": ImageHole,
            "Jesse's Strips": JessesStrips, "Overlap": Overlap,
            "Interlock": Interlock, "Find and Fill": FindAndFill,
            "Slices": Slices, "Lens Bender": LensBender}.get(kind_name)
