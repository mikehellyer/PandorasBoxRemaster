"""The ten puzzle types. Each game draws inside the 650x540 play area at (75, 42)
of the puzzle screen (where every puzzle's background, e.g. FPN/312.PNG, sits on
SCREENS/300.RIM)."""
from __future__ import annotations


def game_for(kind_name):
    from .focuspoint import FocusPoint
    from .imagehole import ImageHole
    from .rotascope import Rotascope
    return {"Focus Point": FocusPoint, "Rotascope": Rotascope, "Image Hole": ImageHole}.get(kind_name)
