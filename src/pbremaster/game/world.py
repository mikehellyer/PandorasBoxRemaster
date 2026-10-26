"""Fixed facts about the campaign that live in PANDORA.EUL code rather than data files."""
from __future__ import annotations

TRICKSTERS = ["Maui", "Puck", "Eris", "Coyote", "Monkey", "Anansi", "Raven"]   # levels 1-7

# Videos before each level (table at 0x5ba490, indexed by level at 0x419399).
LEVEL_VIDEOS = ["OPEN.AVI", "INT01.AVI", "INT02.AVI", "INT03.AVI",
                "INT04.AVI", "INT05.AVI", "INT06.AVI", "INT07.AVI"]

# Music region of every city id (table at 0x5a9dd0: id 500+city, name, region).
REGIONS = {
    1: "Germany", 2: "Greece", 3: "MiddleEast", 4: "Asia", 5: "Germany", 6: "MiddleEast",
    7: "India", 8: "UK", 9: "Italy", 10: "Australia", 11: "MiddleEast", 12: "Asia",
    13: "UK", 14: "Africa", 15: "SouthAmerica", 16: "Spain", 17: "SouthAmerica",
    18: "Italy", 19: "Russia", 20: "Africa", 21: "USA", 22: "France", 23: "France",
    24: "USA", 25: "SouthAmerica", 26: "Italy", 27: "Russia", 28: "USA", 29: "USA",
    30: "Asia", 31: "Australia", 32: "Australia", 33: "Asia", 34: "USA", 35: "Germany",
}

# Region -> file stem in DATA/MUSIC (PANDORA.MGD, LocationColl).
REGION_MUSIC = {
    "UK": "UK", "Spain": "SPAIN", "Australia": "AUSSP", "USA": "USA", "MiddleEast": "MIDE",
    "Italy": "ITALY", "India": "INDIA", "Greece": "GREECE", "Germany": "GERNL",
    "France": "FRANCE", "Russia": "RUSSIA", "SouthAmerica": "SAMER", "Asia": "ASIA",
    "Africa": "AFRICA",
}

# Puzzle kind -> (puzzle screen id in SCREEN.DAT, slot tile strip 510+i, type index).
# The order is the Puzzles Only buttons 150-161 (155 and 157 are cut types).
KIND_INDEX = {"Image Hole": 0, "Focus Point": 1, "Rotascope": 2, "Overlap": 3,
              "Outer Layer": 4, "Jesse's Strips": 6, "Slices": 8, "Lens Bender": 9,
              "Interlock": 10, "Find and Fill": 11}
KIND_SCREEN = {"Image Hole": 2000, "Focus Point": 3000, "Rotascope": 4000, "Overlap": 5000,
               "Outer Layer": 6000, "Jesse's Strips": 8000, "Slices": 10000,
               "Lens Bender": 11000, "Interlock": 12000, "Find and Fill": 13000}

# World map markers. SCREEN.DAT's markers 401-434 are laid out for an older city
# list (STATENU 461-494: 1 Acapulco, 6 Budapest, 8 Cairo ...), so cities are
# matched to them by name. Cities missing from that list are placed here, by the
# map's own scale (about 2.23 px per degree of longitude, 3.25 per degree of
# latitude around the Americas/Pacific; the Europe inset for European cities).
EXTRA_MARKERS = {
    "Amsterdam": (625, 88), "Honolulu": (17, 290), "Mexico City": (148, 296),
    "Milan": (648, 138), "Moscow": (466, 170), "Philadelphia": (196, 234),
    "San Francisco": (96, 236), "Tokyo": (748, 240), "Vienna": (695, 120),
}

# Story voice-overs (PANDORA.MGD StoryVOColl): DATA/VO/SX_<stem><piece>.WAV
VO_STEMS = ["MAUI", "PUCK", "ERIS", "COYO", "MONK", "ANAN", "RAVE"]
