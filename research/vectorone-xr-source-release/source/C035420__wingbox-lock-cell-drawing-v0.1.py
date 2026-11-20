"""Generate a dimensioned engineering drawing from the 1:5 coupon inputs.

All dimensions are taken from wingbox-lock-cell-1-5.py. Views describe the
current candidate CAD only; they are not aircraft design allowables.
"""
from pathlib import Path
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

OUT = Path(__file__).resolve().parent
SCALE = 5.0
AREA_M2 = 14.0
SPAN_M = 13.0
MOMENT_NM = 40_600.0
CAP_FORCE_N = 178_000.0
BAY_FULL_MM = 200.0
PITCH_FULL_MM = 40.0
CHORD = AREA_M2 / SPAN_M * 1000.0 / SCALE
DEPTH = MOMENT_NM / CAP_FORCE_N * 1000.0 / SCALE
SPAN = BAY_FULL_MM / SCALE
PITCH = PITCH_FULL_MM / SCALE
PIN_Y = CHORD / 4.0
PIN_X = 10.0
WALL = 1.2
WEB = 1.2
STRAP_T = 1.6
STRAP_W = 18.0
PIN_D = 3.0
BORE_D = 3.6

BG = "#071018"
PANEL = "#0b1822"
LINE = "#c4d5df"
MUTED = "#8097a5"
CYAN = "#4bd8ea"
BLUE = "#36a4dc"
AMBER = "#ffbc58"
RED = "#ff6d68"
WHITE = "#f2f7fa"

fig = plt.figure(figsize=(16, 10), facecolor=BG)
fig.text(0.045, 0.94, "VECTORONE XR · CS-02.3", color=WHITE,
         fontsize=24, weight="bold", family="DejaVu Sans")
fig.text(0.045, 0.905,
         "1:5 WING-BOX / LOAD-SPREADING JOINT · DIMENSIONED PROTOTYPE DRAWING",
         color=CYAN, fontsize=11, family="DejaVu Sans")
fig.text(0.955, 0.942, "REV 0.1  |  02 NOV 2026", color=MUTED,
         fontsize=9, ha="right", family="DejaVu Sans Mono")

def add_panel(rect, title):
    ax = fig.add_axes(rect, facecolor=PANEL)
    for sp in ax.spines.values():
        sp.set_color("#39515e")
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.text(0.02, 0.97, title, transform=ax.transAxes, color=WHITE,
            fontsize=10, weight="bold", va="top")
    return ax

def dim_x(ax, x1, x2, y, label, color=CYAN, yext=None, fs=7.4):
    if yext is not None:
        ax.plot([x1, x1], [yext, y], color=color, lw=0.65, alpha=.8)
        ax.plot([x2, x2], [yext, y], color=color, lw=0.65, alpha=.8)
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="<->",
                                 mutation_scale=8, color=color, lw=.8))
    ax.text((x1+x2)/2, y, f" {label} ", color=color, fontsize=fs,
            ha="center", va="bottom", family="DejaVu Sans Mono",
            bbox=dict(facecolor=PANEL, edgecolor="none", pad=1.0))

def dim_y(ax, y1, y2, x, label, color=CYAN, xext=None, fs=7.4):
    if xext is not None:
        ax.plot([xext, x], [y1, y1], color=color, lw=0.65, alpha=.8)
        ax.plot([xext, x], [y2, y2], color=color, lw=0.65, alpha=.8)
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle="<->",
                                 mutation_scale=8, color=color, lw=.8))
    ax.text(x, (y1+y2)/2, f"{label}", color=color, fontsize=fs,
            ha="left", va="center", rotation=90,
            family="DejaVu Sans Mono",
            bbox=dict(facecolor=PANEL, edgecolor="none", pad=1.0))

# Plan view: x is spanwise; y is chordwise.
ax = add_panel([0.045, 0.395, 0.36, 0.47], "A  PLAN VIEW · x = spanwise, y = chordwise")
ax.set_xlim(-58, 61); ax.set_ylim(-132, 132); ax.set_aspect("equal", adjustable="box")
ax.add_patch(Rectangle((-SPAN, -CHORD/2), 2*SPAN, CHORD,
                       facecolor="#193141", edgecolor=CYAN, lw=1.45))
# Three spanwise shear webs, continuous through both segments.
for y in (-PIN_Y, 0, PIN_Y):
    ax.plot([-SPAN, SPAN], [y, y], color=BLUE, lw=1.05)
# Transverse ribs at 8 mm pitch and the reinforced pin stations.
rib_x = sorted(set([-32, -24, -16, -10.6, -8, 8, 9.4, 16, 24, 32]))
for x in rib_x:
    ax.plot([x, x], [-CHORD/2+WALL, CHORD/2-WALL], color=MUTED,
            lw=0.62, alpha=.68)
# Segment seam and four projected cap-bridge plates (top and bottom coincide in plan).
ax.plot([0, 0], [-CHORD/2, CHORD/2], color=AMBER, lw=1.35, ls=(0, (4, 2)))
for y in (-PIN_Y, PIN_Y):
    ax.add_patch(Rectangle((-20, y-STRAP_W/2), 40, STRAP_W,
                           facecolor="#ffbc5820", edgecolor=AMBER,
                           lw=1.05, zorder=4))
    for x in (-PIN_X, PIN_X):
        ax.add_patch(Circle((x, y), BORE_D/2, facecolor=BG,
                            edgecolor=WHITE, lw=.85, zorder=5))
ax.text(41, 0, "3 shear webs", color=BLUE, fontsize=7, va="center", rotation=90)
ax.text(-48, 0, "4 closed cells", color=WHITE, fontsize=7, va="center", rotation=90)
ax.text(-20, 101, "LEFT SEGMENT", color=MUTED, fontsize=6.2, ha="center")
ax.text(20, -101, "RIGHT SEGMENT", color=MUTED, fontsize=6.2, ha="center")
dim_x(ax, -40, 40, -124, "80.0 overall", yext=-CHORD/2, fs=7)
dim_y(ax, -CHORD/2, CHORD/2, 52, "215.4 mean-chord envelope", xext=40, fs=6.6)
ax.axis("off")

# Chord-side elevation: look along +y through a cap bridge line.
ax = add_panel([0.43, 0.68, 0.31, 0.185], "B  SIDE ELEVATION · view along chord")
ax.set_xlim(-50, 50); ax.set_ylim(-34, 36); ax.set_aspect("equal", adjustable="box")
ax.add_patch(Rectangle((-40, -DEPTH/2), 80, DEPTH, facecolor="#183142",
                       edgecolor=CYAN, lw=1.3))
ax.plot([0, 0], [-DEPTH/2, DEPTH/2], color=AMBER, lw=1.2, ls="--")
ax.add_patch(Rectangle((-20, DEPTH/2), 40, STRAP_T, facecolor="#ffbc5840",
                       edgecolor=AMBER, lw=.9))
ax.add_patch(Rectangle((-20, -DEPTH/2-STRAP_T), 40, STRAP_T,
                       facecolor="#ffbc5840", edgecolor=AMBER, lw=.9))
for x in (-10, 10):
    ax.plot([x, x], [DEPTH/2-8.6, DEPTH/2+STRAP_T], color=WHITE, lw=1.0)
    ax.plot([x, x], [-DEPTH/2-STRAP_T, -DEPTH/2+8.6], color=WHITE, lw=1.0)
    ax.add_patch(Rectangle((x-2.5, DEPTH/2+STRAP_T), 5, 1.6,
                           facecolor=WHITE, edgecolor=WHITE, lw=.6))
    ax.add_patch(Rectangle((x-2.5, -DEPTH/2-STRAP_T-1.6), 5, 1.6,
                           facecolor=WHITE, edgecolor=WHITE, lw=.6))
dim_x(ax, -40, 0, -30, "40 mm", yext=-DEPTH/2, fs=6.5)
dim_x(ax, 0, 40, -30, "40 mm", yext=-DEPTH/2, fs=6.5)
dim_y(ax, -DEPTH/2, DEPTH/2, 47, "45.62 box depth", xext=40, fs=6.4)
ax.axis("off")

# Section between ribs, looking spanwise.
ax = add_panel([0.43, 0.395, 0.31, 0.235], "C  SECTION BETWEEN RIBS · candidate four-cell box")
ax.set_xlim(-126, 126); ax.set_ylim(-34, 38); ax.set_aspect("equal", adjustable="box")
ax.add_patch(Rectangle((-CHORD/2, -DEPTH/2), CHORD, DEPTH,
                       facecolor="#102734", edgecolor=CYAN, lw=1.35))
for y in (-CHORD/2+WALL/2, CHORD/2-WALL/2):
    ax.add_patch(Rectangle((y-WALL/2, -DEPTH/2), WALL, DEPTH,
                           facecolor=CYAN, edgecolor="none"))
for z in (-DEPTH/2+WALL/2, DEPTH/2-WALL/2):
    ax.add_patch(Rectangle((-CHORD/2, z-WALL/2), CHORD, WALL,
                           facecolor=CYAN, edgecolor="none"))
for y in (-PIN_Y, 0, PIN_Y):
    ax.add_patch(Rectangle((y-WEB/2, -DEPTH/2+WALL), WEB,
                           DEPTH-2*WALL, facecolor=BLUE, edgecolor="none"))
dim_x(ax, -CHORD/2, CHORD/2, -31, "215.4 mm (conditional mean chord)",
      yext=-DEPTH/2, fs=6.7)
dim_y(ax, -DEPTH/2, DEPTH/2, 120, "45.62 mm", xext=CHORD/2, fs=6.3)
ax.text(-111, 27, "1.2 mm nominal skin", color=CYAN, fontsize=6.3, va="top")
ax.text(-8, 26, "3 × 1.2 mm webs", color=BLUE, fontsize=6.3, ha="center", va="top")
ax.text(0, 2, "4 cell spaces", color=WHITE, fontsize=7, ha="center", va="center")
ax.axis("off")

# Single bridge plate, exact top-view dimensions.
ax = add_panel([0.765, 0.59, 0.19, 0.275], "D  TOP BRIDGE · 4 required")
ax.set_xlim(-25, 25); ax.set_ylim(-29, 31); ax.set_aspect("equal", adjustable="box")
ax.add_patch(Rectangle((-20, -9), 40, 18, facecolor="#ffbc5820",
                       edgecolor=AMBER, lw=1.35))
for x in (-10, 10):
    ax.add_patch(Circle((x, 0), BORE_D/2, facecolor=BG,
                        edgecolor=WHITE, lw=1.0))
dim_x(ax, -20, 20, 24, "40.0", yext=9, fs=7)
dim_y(ax, -9, 9, 23, "18.0", xext=20, fs=6.7)
dim_x(ax, -10, 10, -18, "20.0 pin pitch", yext=-9, fs=6.6)
ax.text(0, -25, "2 × Ø3.6 bores   |   t = 1.6 mm",
        color=WHITE, ha="center", fontsize=6.1)
ax.axis("off")

ax = add_panel([0.765, 0.395, 0.19, 0.175], "E  LOCK PIN · 8 required")
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
ax.plot([50, 50], [18, 80], color=WHITE, lw=5, solid_capstyle="butt")
ax.add_patch(Rectangle((41, 80), 18, 9, facecolor=WHITE, edgecolor=WHITE))
ax.text(63, 69, "Ø3.0 shaft", color=CYAN, fontsize=7, va="center")
ax.text(63, 83, "Ø5.0 × 1.6 head", color=CYAN, fontsize=6.6, va="center")
ax.text(50, 10, "8.6 mm shaft reach", color=WHITE, fontsize=6.8,
        ha="center")

# Traceability and test-gate panel.
ax = add_panel([0.045, 0.055, 0.91, 0.285], "DESIGN BASIS / PRINT SET / EVIDENCE LIMITS")
ax.axis("off")
left = (
    "GEOMETRY DERIVATION\n"
    f"• 14 m² ÷ 13 m → {AREA_M2/SPAN_M:.4f} m rectangular-equivalent mean chord\n"
    f"• {MOMENT_NM/1000:.1f} kN·m ÷ {CAP_FORCE_N/1000:.0f} kN → {DEPTH:.2f} mm at 1:5\n"
    f"• {BAY_FULL_MM:.0f} mm bay → {SPAN:.1f} mm segment; {PITCH_FULL_MM:.0f} mm pitch → {PITCH:.1f} mm\n"
    "• Geometry-derived numbers are conditional on the user-board inputs."
)
middle = (
    "PRINT SET / ASSEMBLY\n"
    "2 box halves · 40 × 215.4 × 45.6 mm each\n"
    "4 bridge plates · 40 × 18 × 1.6 mm · Ø3.6 mm candidate holes\n"
    "8 pins · Ø3.0 mm candidate shafts / Ø5.0 mm heads\n"
    "Existing fit coupon: Ø3.2 / 3.4 / 3.6 / 3.8 mm holes\n"
    "Measure printed pin and bore before selecting fit."
)
right = (
    "PHYSICS / OPEN GATES\n"
    "Board mass 1,250–1,350 kg → static hover force floor T ≥ 12.26–13.24 kN\n"
    "No force source, power, controls, or measured lift is established.\n"
    "Board root moment / cap force are unverified; not coupon load settings.\n"
    "Next: fit coupon → fold cycles → instrumented load / displacement record.\n"
    "PRINT CANDIDATE ONLY · NOT A FLIGHT PART · NOT IMPACT TESTED"
)
for x, txt, c in ((0.025, left, CYAN), (0.36, middle, AMBER), (0.68, right, RED)):
    ax.text(x, .82, txt, transform=ax.transAxes, va="top", color=WHITE,
            fontsize=7.15, linespacing=1.52, family="DejaVu Sans Mono")

fig.text(0.955, 0.025,
         "Dimensions in mm · CAD source: wingbox-lock-cell-1-5.py · Views independently scaled",
         color=MUTED, fontsize=7, ha="right", family="DejaVu Sans Mono")
fig.savefig(OUT / "wingbox-lock-cell-drawing-v0.1.png", dpi=220,
            facecolor=BG, bbox_inches="tight")
fig.savefig(OUT / "wingbox-lock-cell-drawing-v0.1.svg",
            facecolor=BG, bbox_inches="tight")
