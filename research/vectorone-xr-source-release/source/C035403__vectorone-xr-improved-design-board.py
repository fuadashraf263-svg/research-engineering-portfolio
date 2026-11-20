"""Render an evidence-labeled VECTORONE XR structural design board.

The airframe drawing is a schematic based only on the user's supplied boards.
The lower-right 3D view is tessellated from the generated 1:5 STEP coupon.
"""
from __future__ import annotations

from pathlib import Path

import cadquery as cq
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parent
STEP = ROOT / "wingbox-lock-cell-1-5-assembly.step"
OUT = ROOT / "vectorone-xr-improved-design-board.png"

BG = "#0b1118"
PANEL = "#101b25"
GRID = "#294050"
TEXT = "#e8f0f5"
MUTED = "#a8bac6"
CYAN = "#41c9e7"
BLUE = "#6b9cf0"
AMBER = "#ffbd5b"
GREEN = "#8ee0bc"
RED = "#ff7878"


def panel(fig, rect, title, subtitle=None):
    ax = fig.add_axes(rect)
    ax.set_facecolor(PANEL)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(GRID)
        spine.set_linewidth(1.0)
    ax.text(0.02, 0.96, title, color=TEXT, fontsize=11, weight="bold",
            ha="left", va="top", transform=ax.transAxes)
    if subtitle:
        ax.text(0.02, 0.88, subtitle, color=MUTED, fontsize=7.5,
                ha="left", va="top", transform=ax.transAxes)
    return ax


def draw_deployed_plan(ax):
    # Put the 13 m span on the horizontal axis, matching the board's plan view.
    ax.set_xlim(-7.35, 7.35)
    ax.set_ylim(-4.0, 3.6)
    ax.set_aspect("equal")
    ax.axis("off")
    # Full wing planform: 13 m span, 14 m² total area are latest-board anchors.
    for s in (-1, 1):
        wing = np.array([[s * 1.0, -0.88], [s * 1.0, 0.88],
                         [s * 6.5, 0.30], [s * 6.5, -0.30]])
        ax.add_patch(Polygon(wing, closed=True, facecolor="#183344",
                             edgecolor=CYAN, linewidth=1.7, alpha=0.72))
        # Closed leading/trailing load paths and the spanwise box core.
        for y0, y1 in [(-0.70, -0.24), (0.24, 0.70)]:
            t = (abs(y0) - 0.88) / (0.30 - 0.88)
            yt = np.sign(y0) * (0.88 + t * (0.30 - 0.88))
            ax.plot([s * 1.0, s * 6.5], [y0, yt], color=BLUE, lw=1.1)
        # Schematic rib stations; spacing is not a complete structural design.
        for x in np.arange(1.45, 6.35, 0.42):
            t = (x - 1.0) / 5.5
            half = 0.88 + t * (0.30 - 0.88)
            ax.plot([s * x, s * x], [-half, half], color=GRID, lw=0.65)
        # Highlight a representative load-spreading joint station.
        ax.scatter([s * 3.1], [0.0], s=30, marker="s", color=AMBER,
                   edgecolors=TEXT, linewidths=0.5, zorder=8)

    # Compact non-car-like hull envelope and paired continuous loops.
    hull = np.array([[0.0, -2.6], [-0.75, -1.95], [-1.12, -0.75],
                     [-1.12, 0.95], [-0.65, 2.15], [0.0, 2.6],
                     [0.65, 2.15], [1.12, 0.95], [1.12, -0.75],
                     [0.75, -1.95]])
    ax.add_patch(Polygon(hull, closed=True, facecolor="#14222d",
                         edgecolor=TEXT, linewidth=1.6, alpha=0.95, zorder=4))
    ax.add_patch(Ellipse((0.0, 0.0), 1.95, 4.75, angle=0,
                         fill=False, edgecolor=CYAN, linewidth=1.45, zorder=6))
    ax.add_patch(Ellipse((0.0, 0.0), 1.45, 4.25, angle=0,
                         fill=False, edgecolor=AMBER, linewidth=1.2, zorder=6))
    ax.plot([0, 0], [-2.35, 2.35], color=BLUE, lw=2.0, zorder=7)
    ax.text(0.06, 0, "CENTRAL KEEL", color=BLUE, fontsize=6.2,
            ha="left", va="center", rotation=90, zorder=9)

    # Occupant support anchors only; human clearances are not represented here.
    seats = [(0.0, -1.18), (-0.36, 0.0), (0.36, 0.0), (0.0, 1.18)]
    for x, y in seats:
        ax.add_patch(Ellipse((x, y), 0.26, 0.55, facecolor="#263743",
                             edgecolor=GREEN, linewidth=1.0, zorder=8))

    ax.annotate("1–2–1 supported-core candidate", xy=(0.0, 0.5), xytext=(-4.65, 1.8),
                color=GREEN, fontsize=7, arrowprops=dict(arrowstyle="-", color=GREEN, lw=0.8))
    ax.annotate("closed wing-box + ribs", xy=(3.1, 0.0), xytext=(4.0, 1.25),
                color=CYAN, fontsize=7, arrowprops=dict(arrowstyle="-", color=CYAN, lw=0.8))
    ax.annotate("representative lock joint", xy=(3.1, 0.0), xytext=(4.0, -0.65),
                color=AMBER, fontsize=7, arrowprops=dict(arrowstyle="-", color=AMBER, lw=0.8))
    ax.annotate("13 m span target", xy=(-6.5, -3.05), xytext=(6.5, -3.05),
                color=MUTED, fontsize=7, ha="center", va="bottom",
                arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.8))
    ax.text(-7.0, -3.8, "SCHEMATIC TOP VIEW · NOT A LIFTING-SURFACE ANALYSIS",
            color=MUTED, fontsize=6.5, ha="left")


def render_coupon(ax):
    if not STEP.exists():
        ax.text2D(0.5, 0.5, "STEP file not found", color=RED, ha="center")
        return
    compound = cq.importers.importStep(str(STEP)).val()
    vertices, faces = compound.tessellate(0.35)
    xyz = np.array([v.toTuple() for v in vertices])
    triangles = [[xyz[i] for i in tri] for tri in faces]
    mesh = Poly3DCollection(triangles, facecolors="#63c7df", edgecolors="#163440",
                            linewidths=0.10, alpha=0.98)
    ax.add_collection3d(mesh)
    ax.set_xlim(-45, 45)
    ax.set_ylim(-120, 120)
    ax.set_zlim(-31, 31)
    ax.set_box_aspect((80, 215.4, 62))
    ax.view_init(elev=20, azim=-47)
    ax.set_axis_off()
    ax.text2D(0.02, 0.04, "80 × 215 × 52 mm envelope · 14 printable solids",
              transform=ax.transAxes, color=MUTED, fontsize=7)


def mini_vehicle(ax, mode: str, title: str, status: str, status_color):
    ax.set_xlim(-3.0, 3.0)
    ax.set_ylim(-3.0, 3.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(0.5, 1.06, title, transform=ax.transAxes, color=TEXT,
            fontsize=8.5, weight="bold", ha="center")
    ax.text(0.5, 0.98, status, transform=ax.transAxes, color=status_color,
            fontsize=6.5, ha="center")
    body = np.array([[-2.4, 0], [-1.5, -0.65], [1.5, -0.65],
                     [2.4, 0], [1.5, 0.65], [-1.5, 0.65]])
    ax.add_patch(Polygon(body, closed=True, facecolor="#1c2b36",
                         edgecolor=TEXT, linewidth=1.2))
    ax.plot([-1.95, 1.95], [0, 0], color=BLUE, lw=1.2)
    if mode in ("road", "hover"):
        # Stowed wing-box segments along the hull; exact clearances are open.
        ax.plot([-1.4, 1.4], [0.47, 0.47], color=CYAN, lw=2.1)
        ax.plot([-1.4, 1.4], [-0.47, -0.47], color=CYAN, lw=2.1)
        for x in (-1.75, 1.75):
            for y in (-0.82, 0.82):
                ax.add_patch(Circle((x, y), 0.13, facecolor=AMBER,
                                    edgecolor=TEXT, linewidth=0.5))
        if mode == "hover":
            for x in (-1.7, -0.55, 0.55, 1.7):
                ax.add_patch(FancyArrowPatch((x, -1.05), (x, -2.0),
                               arrowstyle="-|>", mutation_scale=8,
                               linestyle="--", color=AMBER, linewidth=0.9))
            ax.text(0, -2.25, "arrows are placeholders; no lift source shown",
                    color=AMBER, fontsize=5.8, ha="center")
    else:
        for s in (-1, 1):
            wing = np.array([[-0.7, s * 0.6], [0.7, s * 0.6],
                             [0.18, s * 2.7], [-0.18, s * 2.7]])
            ax.add_patch(Polygon(wing, closed=True, facecolor="#183344",
                                 edgecolor=CYAN, linewidth=1.1, alpha=0.8))
            ax.plot([0, 0], [s * 0.6, s * 2.65], color=BLUE, lw=0.9)
            ax.scatter([0], [s * 1.7], color=AMBER, marker="s", s=12)
        ax.text(0, -2.45, "wing lift / forward thrust not validated",
                color=AMBER, fontsize=5.8, ha="center")


def main():
    fig = plt.figure(figsize=(16.5, 10.2), dpi=150, facecolor=BG)
    fig.text(0.045, 0.965, "VECTORONE XR  /  CONTINUUM SPINE",
             color=TEXT, fontsize=21, weight="bold", va="top")
    fig.text(0.047, 0.925, "CS-02.3 STRUCTURAL INTEGRATION CANDIDATE  ·  SOURCE-BOUND GEOMETRY  ·  NOT FLIGHT VALIDATED",
             color=CYAN, fontsize=9.5, va="top")
    fig.text(0.955, 0.955, "REV 0.1", color=AMBER, fontsize=10,
             weight="bold", ha="right", va="top")

    plan = panel(fig, [0.045, 0.505, 0.60, 0.385],
                 "01  /  DEPLOYED STRUCTURAL PLAN",
                 "Latest-board anchors: 13 m span · 14 m² area · 5.2 m folded body · all targets, not verified dimensions")
    draw_deployed_plan(plan)

    ax3d = fig.add_axes([0.68, 0.515, 0.275, 0.365], projection="3d")
    ax3d.set_facecolor(PANEL)
    render_coupon(ax3d)
    fig.text(0.685, 0.875, "02  /  PRINTABLE WING-BOX JOINT COUPON",
             color=TEXT, fontsize=10, weight="bold", ha="left")
    fig.text(0.685, 0.845, "1:5 candidate · cap bridges + removable pins · untested",
             color=MUTED, fontsize=7.5, ha="left")

    modes = panel(fig, [0.045, 0.08, 0.60, 0.36],
                  "03  /  TRANSFORMATION STATES",
                  "Structural sequence from the supplied animation; no propulsion or aerodynamic performance is implied")
    modes.axis("off")
    p1 = fig.add_axes([0.07, 0.115, 0.16, 0.24], facecolor=PANEL)
    p2 = fig.add_axes([0.265, 0.115, 0.16, 0.24], facecolor=PANEL)
    p3 = fig.add_axes([0.46, 0.115, 0.16, 0.24], facecolor=PANEL)
    mini_vehicle(p1, "road", "ROAD", "5.2 m envelope target", MUTED)
    mini_vehicle(p2, "hover", "FOLDED HOVER", "UNRESOLVED HYPOTHESIS", AMBER)
    mini_vehicle(p3, "wing", "WINGBORNE", "NOT VALIDATED", AMBER)
    for x in (0.24, 0.435):
        ax = fig.add_axes([x, 0.205, 0.02, 0.05])
        ax.axis("off")
        ax.text(0.5, 0.5, "→", color=CYAN, fontsize=18, ha="center", va="center")

    facts = panel(fig, [0.68, 0.08, 0.275, 0.36],
                  "04  /  DERIVED TEST-CELL SIZING",
                  "Calculated from unverified values printed on the supplied boards")
    facts.axis("off")
    rows = [
        ("Mean chord", "14 m² / 13 m = 1.077 m", "215.4 mm @ 1:5"),
        ("Cap separation", "40.6 kN·m / 178 kN = 0.228 m", "45.6 mm @ 1:5"),
        ("Support bay", "200 mm / 5", "40 mm"),
        ("Rib pitch", "40 mm / 5", "8 mm"),
        ("Assembly", "2 box halves + 4 bridges + 8 pins", "14 solids"),
    ]
    y = 0.75
    for label, equation, result in rows:
        facts.text(0.06, y, label, transform=facts.transAxes, color=TEXT, fontsize=7.2, weight="bold")
        facts.text(0.06, y - 0.055, equation, transform=facts.transAxes, color=MUTED, fontsize=6.3)
        facts.text(0.94, y - 0.055, result, transform=facts.transAxes, color=CYAN, fontsize=6.6, ha="right")
        y -= 0.13
    facts.text(0.06, 0.08,
               "NOT A LOAD RATING · 2+2 vs 1–2–1 cabin, 1,200 vs 1,250–1,350 kg, and 9–14 m / 10–18 m² wing values remain in conflict.",
               transform=facts.transAxes, color=AMBER, fontsize=6.1, wrap=True)

    fig.text(0.047, 0.035,
             "HOVER SOURCE UNRESOLVED  ·  LOCKS UNTESTED  ·  PRINTED POLYMER IS NOT CORRELATED TO FULL-SCALE STRUCTURE",
             color=RED, fontsize=8.2, weight="bold", va="bottom")
    fig.savefig(OUT, dpi=150, facecolor=BG, bbox_inches="tight", pad_inches=0.12)
    print(OUT)


if __name__ == "__main__":
    main()
