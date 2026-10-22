"""
theme.py - all colors and fonts live here so they are easy to change.
Colors are hex strings like "#rrggbb".
"""

# ---- Backgrounds -------------------------------------------------------
BG        = "#0b0f1a"   # window background
PANEL     = "#121828"   # side panels
CARD      = "#19223a"   # cards inside panels
CARD_SEL  = "#22305a"   # selected scenario card
BORDER    = "#26324f"
CANVAS_BG = "#0e1424"
GRID      = "#141c30"

# ---- Text --------------------------------------------------------------
TEXT   = "#e6ebf5"
MUTED  = "#8b97b5"

# ---- Accent colors -----------------------------------------------------
BLUE    = "#4f8cff"
GREEN   = "#34d399"
ORANGE  = "#fbbf24"
RED     = "#ff4d6d"
TEAL    = "#2dd4bf"
PURPLE  = "#a78bfa"

# ---- Node colors -------------------------------------------------------
PROCESS_FILL    = "#1b2a4a"
RESOURCE_FILL   = "#143338"
DEADLOCK_FILL   = "#3a1624"
FINISHED_FILL   = "#1a2030"
FINISHED_LINE   = "#4b556f"

# ---- Buttons -----------------------------------------------------------
DISABLED_BG = "#1a2133"
DISABLED_FG = "#566080"

FAMILY = "Segoe UI"   # Windows font; other systems fall back automatically


def font(size=10, weight="normal"):
    """Return a Tk font tuple, e.g. font(12, 'bold')."""
    return (FAMILY, size, weight)
