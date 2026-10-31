#!/usr/bin/env python3
"""Builds the three Rewind props at real size and bakes their textures:

- tape.blend: a compact camcorder cassette (the size of a VHS-C tape) with a window onto its
  reel, a gear and screws underneath, and a paper label the game can swap.
- camcorder.blend: a 2000s handheld camcorder: silver body, black lens, hand strap, viewfinder,
  and its flip-out screen opened, showing playback.
- tape_player.blend: a black pistol grip with a small video camera on top and a cassette bay
  under the camera, closed by a door hinged along its bottom edge.

Parts that get their own SurfaceAppearance are baked (color, roughness, normal, metalness);
glass, lights, the label and the screen are kept separate so the game can change them.

Usage: python3 props_build.py OUT_DIR [--only tape|camcorder|player]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import props_lib as L  # noqa: E402
from props_lib import V, cut, cyl, join, rbox  # noqa: E402

TAPE = (0.092, 0.059, 0.023)  # the cassette: length, depth, thickness
# the tape player's door: hinged along its bottom edge, at this point, about the Y axis
PLAYER_HINGE = (0.0205, 0.0, -0.033)


# ================================================================ the tape
def build_tape():
    black = L.plastic("Shell", (0.018, 0.018, 0.02), 0.32, scuff=0.15)
    white = L.plastic("Hub", (0.8, 0.8, 0.78), 0.4, scuff=0.05)
    brown = L.plastic("MagTape", (0.09, 0.055, 0.03), 0.18, scuff=0.0, grain=0.05)
    metal = L.plastic("Screw", (0.6, 0.6, 0.62), 0.25, metal=1.0, scuff=0.05)
    Lx, Dy, Hz = TAPE
    top, bot = Hz / 2, -Hz / 2
    shell = rbox("shell", TAPE, (0, 0, 0), 0.0016, black)
    cut(shell, rbox("c", (0.053, 0.0285, 0.002), (0.014, 0.0, top + 0.0005), 0, black))  # label recess
    cut(shell, rbox("c", (0.03, 0.03, 0.012), (-0.028, 0.002, top), 0.001, black))  # window onto the reel
    cut(shell, rbox("c", (0.087, 0.0012, 0.0008), (0, -Dy / 2, 0.004), 0, black))  # the lid's outline
    for x in (-0.0435, 0.0435):
        cut(shell, rbox("c", (0.0008, 0.0012, 0.017), (x, -Dy / 2, -0.0045), 0, black))
    cut(shell, cyl("c", 0.0095, 0.012, (0.022, 0.006, bot), black))  # the reel's gear, underneath
    screws = [(-0.04, -0.024), (0.04, -0.024), (-0.04, 0.024), (0.04, 0.024), (0.0, 0.022)]
    for x, y in screws:
        cut(shell, cyl("c", 0.0021, 0.0016, (x, y, bot), black, segs=16))
    cut(shell, rbox("c", (0.008, 0.007, 0.007), (-0.0425, 0.027, bot + 0.0025), 0, black))  # record-protect notch
    parts = [shell]
    parts.append(cyl("pack", 0.0125, 0.004, (-0.028, 0.002, top - 0.0045), brown, segs=40))  # wound tape
    hub = cyl("hub", 0.0055, 0.0045, (-0.028, 0.002, top - 0.0035), white, segs=24)
    cut(hub, cyl("c", 0.0034, 0.004, (-0.028, 0.002, top - 0.0016), white, segs=24))  # the hub's socket
    parts.append(hub)
    for k in range(3):  # its drive teeth
        parts.append(rbox("tooth", (0.0011, 0.0016, 0.0022), (-0.028 + 0.0028 * math.cos(math.radians(120 * k)),
                                                             0.002 + 0.0028 * math.sin(math.radians(120 * k)),
                                                             top - 0.0024), 0, white,
                          rot=Matrix.Rotation(math.radians(120 * k), 4, "Z")))
    g = L.gear("gear", 0.0086, 0.0076, 18, 0.005, (0.022, 0.006, bot + 0.0035), white)
    cut(g, cyl("c", 0.0028, 0.01, (0.022, 0.006, bot + 0.0035), white, segs=16))
    parts.append(g)
    for x, y in screws:
        s = cyl("screw", 0.0017, 0.0008, (x, y, bot + 0.0012), metal, segs=16)
        cut(s, rbox("c", (0.0026, 0.0005, 0.001), (x, y, bot + 0.0008), 0, metal))
        cut(s, rbox("c", (0.0005, 0.0026, 0.001), (x, y, bot + 0.0008), 0, metal))
        parts.append(s)
    for k in range(6):  # grip ridges on both ends
        for x in (-Lx / 2, Lx / 2):
            parts.append(rbox("rib", (0.0012, 0.0016, 0.014), (x, -0.012 + 0.0055 * k, 0.0), 0.0003, black))
    parts.append(L.plane("print", 0.016, 0.0055, (0.03, -Dy / 2 - 0.0001, -0.0045), (0, -1, 0), (0, 0, 1),
                         L.printed("TapePrint", (0.018, 0.018, 0.02), "print_tape.png")))
    handle = join(parts, "Handle")
    window = rbox("Window", (0.0296, 0.0296, 0.0008), (-0.028, 0.002, top - 0.0007), 0.0003,
                  L.glass("M_Window", (0.4, 0.42, 0.45), 0.08))
    label = L.plane("Label", 0.051, 0.0265, (0.014, 0.0, top - 0.0005 + 0.00015), (0, 0, 1), (0, 1, 0),
                    L.textured("M_Label", "label_stairwell.png", 0.7))
    return {"Handle": handle, "Window": window, "Label": label}, {"Handle": 1024}


# ================================================================ the camcorder
def build_camcorder():
    silver = L.plastic("Silver", (0.62, 0.64, 0.68), 0.28, metal=0.55, scuff=0.08)
    gloss = L.plastic("GlossBlack", (0.012, 0.012, 0.014), 0.12, scuff=0.08)
    grey = L.plastic("DarkGrey", (0.06, 0.062, 0.066), 0.5, scuff=0.1)
    rubber = L.plastic("Rubber", (0.02, 0.02, 0.022), 0.8, texture="knurl", tex_scale=500, tex_strength=0.2)
    fabric = L.plastic("Strap", (0.04, 0.042, 0.046), 0.85, texture="weave", tex_scale=180, tex_strength=0.25)
    grille = L.plastic("Grille", (0.08, 0.08, 0.085), 0.5, texture="grille", tex_scale=900, tex_strength=0.4)
    blue = L.plastic("AccentBlue", (0.08, 0.32, 0.75), 0.25, metal=0.7, scuff=0.03)
    coating = L.plastic("LensCoating", (0.03, 0.02, 0.08), 0.05, metal=0.6, scuff=0.0)
    red = L.plastic("RecRed", (0.7, 0.04, 0.03), 0.3, scuff=0.03)
    knurl = L.plastic("Dial", (0.05, 0.05, 0.055), 0.45, texture="ridges", tex_scale=1400, tex_strength=0.5)
    lx = 0.034  # half width of the body
    body = rbox("main", (0.068, 0.15, 0.088), (0, 0.012, 0), 0.014, silver, segs=4)
    # the screen panel's pocket on his left side (+X), with buttons inside
    cut(body, rbox("c", (0.008, 0.088, 0.066), (lx + 0.0012, 0.0, 0.0), 0.003, silver))
    # the tape door's outline on the right side (-X)
    for z in (-0.031, 0.031):
        cut(body, rbox("c", (0.0024, 0.11, 0.0012), (-lx, 0.012, z), 0, silver))
    for y in (-0.043, 0.067):
        cut(body, rbox("c", (0.0024, 0.0012, 0.062), (-lx, y, 0.0), 0, silver))
    cut(body, cyl("c", 0.003, 0.01, (0.0, 0.02, -0.044), silver, segs=16))  # tripod socket
    parts = [body]
    parts.append(rbox("front", (0.062, 0.03, 0.074), (0, -0.07, 0.006), 0.01, gloss, segs=4))
    parts.append(cyl("barrel", 0.031, 0.042, (0, -0.1, 0.008), gloss, axis="Y", segs=48, bevel=0.002))
    parts.append(cyl("accent", 0.0322, 0.004, (0, -0.0835, 0.008), blue, axis="Y", segs=48))
    hood = cyl("hood", 0.034, 0.009, (0, -0.124, 0.008), gloss, axis="Y", segs=48, bevel=0.0015)
    cut(hood, cyl("c", 0.026, 0.02, (0, -0.124, 0.008), gloss, axis="Y", segs=48))
    parts.append(hood)
    parts.append(cyl("rim", 0.0275, 0.004, (0, -0.1215, 0.008), gloss, axis="Y", segs=48))
    parts.append(cyl("element", 0.021, 0.002, (0, -0.1225, 0.008), coating, axis="Y", segs=40))
    parts.append(L.plane("zoomprint", 0.034, 0.0045, (0, -0.074, 0.0432), (0, 0, 1), (0, 1, 0),
                         L.printed("ZoomPrint", (0.012, 0.012, 0.014), "print_zoom.png", 0.12)))
    parts.append(cyl("sensor", 0.0045, 0.003, (-0.02, -0.0852, 0.035), gloss, axis="Y", segs=20))
    parts.append(cyl("mic", 0.011, 0.04, (0, -0.056, 0.047), grille, axis="X", segs=32, bevel=0.002))
    # top controls
    parts.append(rbox("zoom", (0.014, 0.022, 0.007), (-0.014, 0.04, 0.0455), 0.0028, grey))
    parts.append(cyl("photo", 0.0055, 0.005, (-0.014, 0.012, 0.045), silver, segs=20, bevel=0.001))
    parts.append(rbox("shoe", (0.02, 0.03, 0.004), (0.012, -0.004, 0.045), 0.0015, gloss))
    parts.append(rbox("eject", (0.008, 0.016, 0.0045), (-0.022, 0.072, 0.0445), 0.0015, grey))
    # the viewfinder on the back, with a rubber eyecup
    parts.append(rbox("finder", (0.032, 0.05, 0.026), (0.008, 0.058, 0.054), 0.008, silver))
    parts.append(cyl("eyepiece", 0.0135, 0.022, (0.008, 0.094, 0.056), gloss, axis="Y", segs=32, bevel=0.0015))
    cup = cyl("eyecup", 0.016, 0.01, (0.008, 0.109, 0.056), rubber, axis="Y", segs=32, bevel=0.003)
    cut(cup, cyl("c", 0.009, 0.03, (0.008, 0.109, 0.056), rubber, axis="Y", segs=32))
    parts.append(cup)
    parts.append(cyl("finderglass", 0.0092, 0.002, (0.008, 0.106, 0.056), coating, axis="Y", segs=24))
    # battery, REC button and mode dial at the back
    parts.append(rbox("battery", (0.052, 0.024, 0.044), (0, 0.098, -0.012), 0.005, grey))
    parts.append(cyl("recring", 0.0105, 0.003, (-0.022, 0.0876, 0.022), gloss, axis="Y", segs=32))
    parts.append(cyl("rec", 0.0078, 0.006, (-0.022, 0.0895, 0.022), red, axis="Y", segs=32, bevel=0.0015))
    parts.append(L.plane("recprint", 0.012, 0.004, (-0.022, 0.0868, 0.0365), (0, 1, 0), (0, 0, 1),
                         L.printed("RecPrint", (0.62, 0.64, 0.68), "print_rec.png", 0.28, 0.55)))
    parts.append(cyl("mode", 0.012, 0.006, (-0.036, 0.075, 0.028), knurl, axis="X", segs=40, bevel=0.001))
    # inside the screen pocket: buttons and a speaker
    for k in range(4):
        parts.append(cyl("btn", 0.003, 0.003, (lx - 0.0018, -0.03 + 0.016 * k, 0.02), grey, axis="X", segs=16))
    parts.append(rbox("speaker", (0.0012, 0.03, 0.014), (lx - 0.0022, 0.02, -0.018), 0.0005, grille))
    # strap anchors
    for y in (-0.046, 0.074):
        parts.append(rbox("anchor", (0.008, 0.012, 0.03), (-lx - 0.003, y, 0.0), 0.002, gloss))
    body = join(parts, "Body")
    # the hand strap on his right (-X): this is where the hand goes, so it's the Handle
    path = [V(-lx - 0.004, -0.046, 0.0), V(-0.05, -0.032, 0.0), V(-0.058, 0.006, 0.0), V(-0.056, 0.044, 0.0),
            V(-0.047, 0.066, 0.0), V(-lx - 0.004, 0.074, 0.0)]
    from props_lib import superellipse  # noqa: E402
    smooth_path = []
    for a, b in zip(path, path[1:]):
        for k in range(6):
            smooth_path.append(a.lerp(b, k / 6))
    smooth_path.append(path[-1])

    def section(t):
        thick = 0.0035 + 0.0025 * math.sin(math.pi * t)  # padded in the middle
        return superellipse(thick, 0.018, 20, 5.0)

    strap = L.sweep("Handle", smooth_path, section, fabric)
    # the flip-out screen, opened: hinged at the front of his left side, facing back at the user
    px0, px1 = lx + 0.004, lx + 0.086
    panel = rbox("panel", (px1 - px0, 0.009, 0.062), ((px0 + px1) / 2, -0.036, 0.0), 0.003, silver)
    cut(panel, rbox("c", (0.068, 0.004, 0.051), ((px0 + px1) / 2, -0.0315, 0.0), 0.001, silver))
    hinge = cyl("hinge", 0.005, 0.064, (lx + 0.002, -0.036, 0.0), grey, segs=20, bevel=0.001)
    print_ = L.plane("panelprint", 0.06, 0.0075, ((px0 + px1) / 2, -0.0406, -0.02), (0, -1, 0), (0, 0, 1),
                     L.printed("PanelPrint", (0.62, 0.64, 0.68), "print_camcorder.png", 0.28, 0.55))
    panel = join([panel, hinge, print_], "Panel")
    screen = L.plane("Screen", 0.064, 0.048, ((px0 + px1) / 2, -0.0332, 0.0), (0, 1, 0), (0, 0, 1),
                     L.textured("M_Screen", "screen_playback.png", 0.15, emit=1.5))
    lens = cyl("Lens", 0.0262, 0.003, (0, -0.1195, 0.008), L.glass("M_Lens", (0.55, 0.6, 0.7)), axis="Y", segs=40)
    rec = L.sphere("RecLight", 0.0028, (0.022, -0.0852, 0.035), L.light("M_RecLight", (1.0, 0.05, 0.03), 3.0))
    return ({"Body": body, "Handle": strap, "Panel": panel, "Screen": screen, "Lens": lens, "RecLight": rec},
            {"Body": 1024, "Handle": 512, "Panel": 512})


# ================================================================ the tape player
def build_player():
    matte = L.plastic("Matte", (0.016, 0.016, 0.018), 0.55, scuff=0.12)
    gloss = L.plastic("GlossBlack", (0.01, 0.01, 0.012), 0.14, scuff=0.08)
    rubber = L.plastic("Rubber", (0.022, 0.022, 0.024), 0.85, texture="knurl", tex_scale=450, tex_strength=0.25)
    white = L.plastic("Spindle", (0.78, 0.78, 0.76), 0.4, scuff=0.04)
    metal = L.plastic("Metal", (0.62, 0.63, 0.65), 0.22, metal=1.0, scuff=0.05)
    coating = L.plastic("LensCoating", (0.03, 0.02, 0.08), 0.05, metal=0.6, scuff=0.0)
    bay = L.plastic("Bay", (0.008, 0.008, 0.009), 0.7, scuff=0.05)
    hx, hy, hz = 0.038, 0.112, 0.074  # the cassette housing
    housing = rbox("housing", (hx, hy, hz), (0, 0, 0), 0.006, matte, segs=3)
    cut(housing, rbox("c", (0.043, 0.098, 0.064), (0.0085, 0.0, 0.0), 0.002, bay))  # the bay, open on his left
    parts = [housing]
    for y in (-0.025, 0.025):  # reel spindles and a capstan inside
        parts.append(cyl("spindle", 0.0045, 0.006, (-0.0105, y, -0.004), white, axis="X", segs=24, bevel=0.0008))
    parts.append(cyl("capstan", 0.003, 0.06, (0.0, -0.045, 0.0), metal, segs=16))
    for y in (-0.04, 0.04):  # hinge knuckles for the door
        parts.append(cyl("knuckle", 0.003, 0.012, (PLAYER_HINGE[0], y, PLAYER_HINGE[2]), metal, axis="Y", segs=16))
    for y in (-0.045, 0.045):
        for z in (-0.028, 0.028):
            parts.append(cyl("screw", 0.0022, 0.001, (-hx / 2 - 0.0002, y, z), metal, axis="X", segs=16))
    parts.append(L.plane("playprint", 0.028, 0.0075, (-hx / 2 - 0.0002, 0.0, 0.0), (-1, 0, 0), (0, 0, 1),
                         L.printed("PlayPrint", (0.016, 0.016, 0.018), "print_play.png", 0.55)))
    # the video camera on top
    cz = hz / 2 + 0.026
    cam = rbox("camera", (0.046, 0.12, 0.052), (0, -0.004, cz), 0.009, gloss, segs=3)
    for k in range(4):
        cut(cam, rbox("c", (0.03, 0.0016, 0.002), (0, 0.02 + 0.007 * k, cz + 0.026), 0, gloss))  # vents
    parts.append(cam)
    parts.append(cyl("barrel", 0.023, 0.03, (0, -0.077, cz + 0.002), gloss, axis="Y", segs=40, bevel=0.0015))
    parts.append(cyl("chrome", 0.0238, 0.003, (0, -0.069, cz + 0.002), metal, axis="Y", segs=40))
    hood = cyl("hood", 0.025, 0.007, (0, -0.095, cz + 0.002), gloss, axis="Y", segs=40, bevel=0.001)
    cut(hood, cyl("c", 0.019, 0.02, (0, -0.095, cz + 0.002), gloss, axis="Y", segs=40))
    parts.append(hood)
    parts.append(cyl("element", 0.016, 0.002, (0, -0.0935, cz + 0.002), coating, axis="Y", segs=32))
    # the play button where your finger rests, under the front of the housing
    parts.append(rbox("trigger", (0.012, 0.009, 0.016), (0, -0.026, -hz / 2 - 0.008), 0.003, rubber))
    body = join(parts, "Body")
    # the grip: a rubber pistol grip with finger grooves, angled back
    path = [V(0, 0.034, -0.15), V(0, 0.026, -0.11), V(0, 0.018, -0.07), V(0, 0.014, -0.03)]
    from props_lib import superellipse  # noqa: E402
    pts = []
    for a, b in zip(path, path[1:]):
        for k in range(8):
            pts.append(a.lerp(b, k / 8))
    pts.append(path[-1])

    def section(t):
        flare = 1.0 + 0.18 * max(0.0, 0.18 - t) / 0.18
        out = []
        for u, v in superellipse(0.021, 0.016, 28, 3.2):  # u: front-back, v: side to side
            groove = -0.0035 * max(0.0, math.cos(3 * math.pi * (t - 0.2) / 0.6)) if (u < 0 and 0.2 < t < 0.8) else 0.0
            out.append(((u + (groove if u < 0 else 0.0)) * flare, v * flare))
        return [(v, u) for u, v in out]

    grip = L.sweep("Handle", pts, section, rubber)
    # the door, closed (the game opens it)
    door = rbox("door", (0.003, 0.1, 0.066), (0.0205, 0.0, 0.0), 0.0012, matte)
    for k in range(3):
        door_r = rbox("ridge", (0.0012, 0.03, 0.0012), (0.0225, 0.0, 0.022 + 0.0035 * k), 0.0003, matte)
        door = join([door, door_r], "door")
    tab = rbox("tab", (0.004, 0.016, 0.004), (0.0215, 0.0, 0.0315), 0.0012, gloss)
    knuckle = cyl("doorknuckle", 0.0028, 0.06, PLAYER_HINGE, metal, axis="Y", segs=16)
    door = join([door, tab, knuckle], "Door")
    lens = cyl("Lens", 0.0192, 0.002, (0, -0.0955, cz + 0.002), L.glass("M_Lens", (0.55, 0.6, 0.7)), axis="Y", segs=32)
    led = L.sphere("Light", 0.003, (0.014, 0.0565, cz + 0.012), L.light("M_Light", (0.2, 1.0, 0.35), 3.0))
    return ({"Body": body, "Handle": grip, "Door": door, "Lens": lens, "Light": led},
            {"Body": 1024, "Handle": 512, "Door": 512})


BUILDERS = {"tape": build_tape, "camcorder": build_camcorder, "player": build_player}
FILES = {"tape": "tape", "camcorder": "camcorder", "player": "tape_player"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    for key in ([a.only] if a.only else BUILDERS):
        L.reset()
        parts, bakes = BUILDERS[key]()
        for name, ob in parts.items():
            L.finish(ob, 25 if name in ("Handle", "Body") else 32)
            ob["part"] = name
        for name, size in bakes.items():
            L.bake(parts[name], size, f"{FILES[key]}_{name.lower()}", os.path.join(a.out, "textures", "baked"))
        print(key, {n: L.tris(o) for n, o in parts.items()}, "total", sum(L.tris(o) for o in parts.values()))
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), f"{FILES[key]}.blend"))


if __name__ == "__main__":
    main()
