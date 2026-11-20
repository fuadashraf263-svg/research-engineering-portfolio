from __future__ import annotations

import math
import shutil
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "vectorone-xr-cs02-prototype"
W, H = 1280, 720
BG = (8, 14, 20)
CYAN = (94, 222, 231)
CYAN_DIM = (62, 153, 169)
STEEL = (105, 133, 145)
PALE = (225, 238, 243)
MUTED = (137, 159, 169)
AMBER = (255, 202, 120)


def font(size, bold=False, mono=False):
    names = ("consola.ttf", "consolab.ttf") if mono else (("segoeuib.ttf", "seguisb.ttf") if bold else ("segoeui.ttf", "seguisb.ttf"))
    for name in names:
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def project(p, center, scale, lift=0, offset=0):
    x, y, z = p
    x += offset
    z += lift
    u = (x - y) * .70710678
    v = (x + y) * .25 - z * .88
    return (round(center[0] + scale * u), round(center[1] + scale * v))


def interpolate(a, b, t):
    t = max(0, min(1, t))
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def root_pt(x, dist, z, side, deploy, lift, offset):
    angle = side * (1 - deploy) * math.pi / 2
    dy = side * dist
    return (x * math.cos(angle) - dy * math.sin(angle) + offset,
            side * 32 + x * math.sin(angle) + dy * math.cos(angle), z + lift)


def outer_pt(x, dist, z, side, deploy, lift, offset):
    a = (1 - deploy) * math.pi / 2
    dy = side * (148 + dist * math.cos(a) + 8 * math.sin(a))
    zz = 44 + dist * math.sin(a) - 8 * math.cos(a) + lift
    angle = side * (1 - deploy) * math.pi / 2
    return (x * math.cos(angle) - dy * math.sin(angle) + offset,
            side * 32 + x * math.sin(angle) + dy * math.cos(angle), zz)


def chord(y):
    q = max(0, min(1, (y - 32) / (325 - 32)))
    return 54 - 20 * q


def line_world(draw, a, b, center, scale, color=CYAN, width=2, lift=0, offset=0):
    draw.line((project(a, center, scale, lift, offset), project(b, center, scale, lift, offset)), fill=color, width=width)


def polygon_world(draw, pts, center, scale, fill, outline=None, lift=0, offset=0):
    coords = [project(p, center, scale, lift, offset) for p in pts]
    draw.polygon(coords, fill=fill)
    if outline:
        draw.line(coords + [coords[0]], fill=outline, width=1, joint="curve")


def draw_ring(draw, center3, r, center, scale, color, fill=None, lift=0, offset=0):
    pts = []
    for i in range(32):
        a = 2 * math.pi * i / 32
        pts.append((center3[0] + r * math.cos(a), center3[1] + r * math.sin(a), center3[2]))
    polygon_world(draw, pts, center, scale, fill or (16, 38, 46), color)


def draw_wing(draw, side, outer, deploy, lift, center, scale, offset):
    start, end = ((180, 325) if outer else (32, 180))
    stations = [start, end] + [i for i in range(math.ceil(start / 36) * 36, end, 36) if start < i < end]
    stations = sorted(set(stations))
    point = outer_pt if outer else root_pt

    def get(f, y):
        if outer:
            return point(chord(y) * f, y - start, 36, side, deploy, lift, offset)
        return point(chord(y) * f, y - 32, 36, side, deploy, lift, offset)

    edge = (120, 225, 231) if not outer else (97, 190, 202)
    for f in (-.5, 0, .5):
        draw.line((project(get(f, start), center, scale), project(get(f, end), center, scale)), fill=edge, width=max(2, round(2.1 * scale)))
    for y in stations:
        if not outer and y == start:
            ribs = ((-.5, -6/chord(y)), (6/chord(y), .5))
        else:
            ribs = ((-.5, 0), (0, .5))
        for f0, f1 in ribs:
            draw.line((project(get(f0, y), center, scale), project(get(f1, y), center, scale)), fill=CYAN_DIM, width=max(1, round(1.3 * scale)))
    if outer:
        h = root_pt(0, 148, 44, side, deploy, lift, offset)
        draw_ring(draw, h, 5.3, center, scale, (180, 242, 241), lift=0)
    else:
        h = root_pt(0, 0, 41, side, deploy, lift, offset)
        draw_ring(draw, h, 6, center, scale, (180, 242, 241))
        m = root_pt(0, 148, 44, side, deploy, lift, offset)
        draw_ring(draw, m, 5.3, center, scale, (180, 242, 241))


def draw_tire(draw, x, side, lift, center, scale, offset, spin=0):
    y, z, r = side * 35.5, 15 + lift, 15
    pts = [(x + r * math.cos(i * math.pi * 2 / 36), y, z + r * math.sin(i * math.pi * 2 / 36)) for i in range(36)]
    polygon_world(draw, pts, center, scale, (18, 26, 31), (75, 101, 112), lift=0, offset=offset)
    pts2 = [(x + 7.3 * math.cos(i * math.pi * 2 / 24), y, z + 7.3 * math.sin(i * math.pi * 2 / 24)) for i in range(24)]
    polygon_world(draw, pts2, center, scale, (38, 59, 68), (135, 169, 179), offset=offset)
    for i in range(5):
        a = spin + i * math.pi * 2 / 5
        line_world(draw, (x + 1.5 * math.cos(a), y, z + 1.5 * math.sin(a)),
                   (x + 6 * math.cos(a), y, z + 6 * math.sin(a)), center, scale, (159, 193, 201), 1, offset=offset)


def draw_hull(draw, lift, center, scale, offset):
    sections = [(-130, 3, 1.5, 3), (-126, 5, 6, 6), (-116, 10, 13, 11),
                (-98, 15, 20, 15), (-80, 17, 23, 17), (65, 17, 26, 17),
                (92, 16, 23, 16), (112, 13, 17, 13), (124, 8, 9, 8), (130, 3, 1.5, 3)]
    patches = []
    sides = 32
    for j in range(len(sections) - 1):
        xA, zA, yA, hA = sections[j]
        xB, zB, yB, hB = sections[j + 1]
        for i in range(sides):
            a, b = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides
            def q(x, zc, wy, hz, t):
                return (x + offset, wy * math.cos(t), zc + 2.5 + hz * math.sin(t) + lift)
            pts = [q(xA, zA, yA, hA, a), q(xA, zA, yA, hA, b),
                   q(xB, zB, yB, hB, b), q(xB, zB, yB, hB, a)]
            depth = sum(.62 * p[0] + .62 * p[1] + .35 * p[2] for p in pts) / 4
            light = max(0.0, math.sin((a + b) / 2))
            shade = tuple(min(255, round(c + light * add)) for c, add in zip((27, 45, 53), (20, 34, 41)))
            patches.append((depth, pts, shade))
    for _, pts, shade in sorted(patches, key=lambda item: item[0]):
        polygon_world(draw, pts, center, scale, shade)
    for zoff in (-.76, .76):
        points = [(x + offset, zoff * half_width,
                   zc + 2.5 + math.sqrt(1-zoff*zoff) * half_height + lift)
                  for x, zc, half_width, half_height in sections]
        for a, b in zip(points, points[1:]):
            line_world(draw, a, b, center, scale, (85, 122, 132), 1)
    rings = [(34, 60, 23), (39, 57, 21), (47, 48, 18), (54, 32, 12), (58, 3, 2)]
    cx = 18 + offset
    for k in range(len(rings) - 1):
        zA, rxA, ryA = rings[k]
        zB, rxB, ryB = rings[k + 1]
        for i in range(24):
            a, b = i * math.pi / 12, (i + 1) * math.pi / 12
            q = lambda z, rx, ry, t: (cx + rx * math.cos(t), ry * math.sin(t), z + lift)
            shade = ((44, 91, 106), (45, 113, 128), (44, 125, 139), (39, 99, 116))[k]
            polygon_world(draw, [q(zA, rxA, ryA, a), q(zA, rxA, ryA, b), q(zB, rxB, ryB, b), q(zB, rxB, ryB, a)], center, scale, shade, (95, 160, 170))
    line_world(draw, (-105 + offset, 0, 34 + lift), (113 + offset, 0, 34 + lift), center, scale, (126, 157, 166), 1)
    for side in (-1, 1):
        for x0, x1 in ((-12, -6), (12, 6)):
            line_world(draw, (x0 + offset, side * 18, 24 + lift),
                       (x1 + offset, side * 32, 34.5 + lift), center, scale, (119, 195, 202), 2)


def draw_model(draw, *, deploy, lift, center, scale, offset=0, spin=0, grid=True):
    if grid:
        for y in range(-250, 251, 50):
            line_world(draw, (-340, y, 0), (340, y, 0), center, scale, (25, 39, 47), 1)
        for x in range(-300, 301, 50):
            line_world(draw, (x, -270, 0), (x, 270, 0), center, scale, (25, 39, 47), 1)
    for side in (-1, 1):
        draw_wing(draw, side, False, deploy, lift, center, scale, offset)
        draw_wing(draw, side, True, deploy, lift, center, scale, offset)
    draw_hull(draw, lift, center, scale, offset)
    for x in (-82, 82):
        for side in (-1, 1):
            draw_tire(draw, x, side, lift, center, scale, offset, spin)


def draw_video_frame(t, duration=13.0):
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    for x in range(0, W, 64):
        d.line((x, 0, x, H), fill=(15, 26, 34), width=1)
    for y in range(0, H, 64):
        d.line((0, y, W, y), fill=(15, 26, 34), width=1)
    if t < 2:
        deploy, lift = 0, 0
        label, sub = "ROAD ROLL", "Wheel spin illustrates  v = ωr  ·  steering / braking not modeled"
        drive = 32 * math.sin(t * 1.8)
        spin = -drive / 15
    elif t < 5.4:
        p = (t - 2) / 3.4
        deploy, lift, drive, spin = interpolate(0, 1, p), 0, 0, 0
        label, sub = "TWO-AXIS WING DEPLOYMENT", "Root pivot swings aft  ·  outer panel folds through its chordwise pin"
    elif t < 6.7:
        deploy, lift, drive, spin = 1, 0, 0, 0
        label, sub = "OPEN SPAN CONFIGURATION", "650 mm model span  ·  open spars have no aerodynamic skin"
    elif t < 8.3:
        deploy, lift, drive, spin = 1, 82 * min(1, (t - 6.7) * 2), 0, 0
        label, sub = "HOVER POSE · VISUAL PLACEHOLDER", "No thrust model, lift hardware, mass, or control system is included"
    elif t < 9.8:
        deploy, lift, drive, spin = 1, 82 * (1 - min(1, (t - 8.3) * 2)), 0, 0
        label, sub = "FLIGHT STUDY", "The open loop frame cannot substantiate wingborne flight in this revision"
    elif t < 11.5:
        deploy, lift, drive, spin = 1 - min(1, (t - 9.8) / 1.7), 0, 0, 0
        label, sub = "LAND / FOLD SEQUENCE", "Returning to the road packaging pose"
    else:
        deploy, lift, drive, spin = 0, 0, 24 * math.sin((t - 11.5) * 1.5), 0
        label, sub = "ROAD / FOLDED", "260 mm spine · estimated folded geometry width 118 mm"

    # top identification rail
    d.text((44, 32), "VECTORONE XR", font=font(15, True), fill=PALE)
    d.text((44, 57), "CONTINUUM SPINE  /  CS—02.2", font=font(10, mono=True), fill=CYAN)
    d.text((W - 290, 40), "FIRST-PRINCIPLES MECHANISM STUDY", font=font(10, mono=True), fill=MUTED)
    center = (W * .52, 388)
    scale = 1.02
    draw_model(d, deploy=deploy, lift=lift, center=center, scale=scale, offset=drive, spin=spin)
    # phase and scale callouts
    d.rounded_rectangle((42, 566, 518, 651), radius=4, fill=(12, 24, 31), outline=(43, 72, 83), width=1)
    d.rectangle((42, 566, 46, 651), fill=CYAN)
    d.text((62, 578), label, font=font(13, True), fill=AMBER if "PLACEHOLDER" in label else PALE)
    d.text((62, 605), sub, font=font(9, mono=True), fill=MUTED)
    d.text((42, 673), "SCALE  1:20   |   BODY  260 mm   |   SPAN  650 mm   |   21 PRINT FILES", font=font(9, mono=True), fill=(147, 171, 180))
    d.text((W - 493, 673), "GEOMETRY ONLY · NO FLIGHT / ROAD QUALIFICATION", font=font(9, mono=True), fill=(194, 156, 103))
    # subtle animated deployment strip
    d.rounded_rectangle((W - 305, 583, W - 43, 592), radius=4, fill=(25, 42, 50))
    if deploy > 0:
        d.rounded_rectangle((W - 305, 583, W - 305 + 262 * deploy, 592), radius=4, fill=CYAN)
    d.text((W - 305, 558), "FOLD / DEPLOY", font=font(9, mono=True), fill=MUTED)
    d.text((W - 55, 558), f"{deploy * 100:0.0f}%", font=font(9, mono=True), fill=CYAN, anchor="ra")
    return image


def board():
    image = Image.new("RGB", (1600, 1000), BG)
    d = ImageDraw.Draw(image)
    for x in range(0, 1600, 64):
        d.line((x, 0, x, 1000), fill=(14, 23, 30), width=1)
    for y in range(0, 1000, 64):
        d.line((0, y, 1600, y), fill=(14, 23, 30), width=1)
    d.text((68, 50), "VECTORONE XR", font=font(16, True), fill=PALE)
    d.text((68, 78), "CONTINUUM SPINE  /  ENGINEERING STUDY", font=font(11, mono=True), fill=CYAN)
    d.text((1530, 62), "CS—02.2  ·  REV 0.2  ·  1:20", font=font(11, mono=True), fill=MUTED, anchor="ra")
    d.line((68, 118, 1532, 118), fill=(40, 60, 69), width=1)
    d.text((68, 143), "PRINTABLE FOLDING MECHANISM", font=font(27, True), fill=PALE)
    d.text((68, 186), "A geometry-first prototype from the existing VECTORONE concept. Motion is illustrated; flight performance is not established.", font=font(12), fill=MUTED)
    # two detail panes
    pane_left=(56,230,786,795); pane_right=(814,230,1544,795)
    for pane in (pane_left,pane_right):
        d.rounded_rectangle(pane, radius=7, fill=(10,18,24), outline=(42,61,71), width=1)
    d.text((83,252), "01  /  WINGS OPEN", font=font(11, mono=True), fill=CYAN)
    d.text((83,277), "Twin-loop cells · two hinge axes per side", font=font(10), fill=MUTED)
    draw_model(d, deploy=1, lift=0, center=(421, 514), scale=.98, grid=False)
    d.text((82,742), "TIP-TO-TIP  650 mm", font=font(12, mono=True), fill=PALE)
    d.text((82,766), "Open frame shown without a lifting skin.", font=font(9), fill=MUTED)
    d.text((840,252), "02  /  ROAD FOLD", font=font(11, mono=True), fill=CYAN)
    d.text((840,277), "Outer panel folds up · inner panel swings aft", font=font(10), fill=MUTED)
    draw_model(d, deploy=0, lift=0, center=(1190, 538), scale=1.08, grid=False)
    d.text((840,742), "ENVELOPE  ≈118 W × 286 L × 191 H mm", font=font(11, mono=True), fill=PALE)
    d.text((840,766), "Calculated from current geometry; no tolerance added.", font=font(9), fill=MUTED)
    # calculation ribbon
    d.rounded_rectangle((56,823,1544,952), radius=6, fill=(14,24,31), outline=(42,62,72))
    d.text((83,846), "SCALE ANCHORS  /  PROVISIONAL", font=font(9, mono=True), fill=MUTED)
    d.text((83,873), "5,200 ÷ 20  =  260 mm body", font=font(19, True), fill=PALE)
    d.text((598,873), "13,000 ÷ 20  =  650 mm span", font=font(19, True), fill=PALE)
    d.text((83,916), "21 printable items incl. fit coupon   ·   3 mm hinge pins / 4.6 mm wheel axles", font=font(10, mono=True), fill=CYAN)
    d.text((1531,916), "GEOMETRY ONLY · NO LIFT / FLIGHT / ROAD QUALIFICATION", font=font(9, mono=True), fill=AMBER, anchor="ra")
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    poster = board()
    poster.save(OUT / "vectorone-cs02-2-prototype-board.png", optimize=True)
    fps, seconds = 24, 13
    video = OUT / "vectorone-cs02-2-mechanism-study.mp4"
    with imageio.get_writer(video, fps=fps, codec="libx264", quality=8, macro_block_size=16,
                            ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"]) as w:
        for i in range(fps * seconds):
            im = draw_video_frame(i / fps, seconds)
            w.append_data(__import__("numpy").asarray(im))
    shutil.copy2(ROOT / "work" / "vectorone_first_principles_model.py", OUT / "vectorone-cs02-2-parametric-source.py")
    print(f"Created {OUT / 'vectorone-cs02-2-prototype-board.png'}")
    print(f"Created {video}")


if __name__ == "__main__":
    main()
