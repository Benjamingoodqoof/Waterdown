#!/usr/bin/env python3
"""Preview renders of the props on the studio floor (Cycles, CPU).

Usage: python3 props_render.py PROPS_DIR OUT_DIR [--samples 64] [--res 1000x800]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import props_build as PB  # noqa: E402
import render  # noqa: E402

# per shot: blend, camera target, camera offset, lens, door angle (player), tape in the bay, flip the tape over
SHOTS = {
    "tape_top": ("tape", (0, 0, 0.012), (-0.11, -0.15, 0.13), 70, None, False, False),
    "tape_bottom": ("tape", (0, 0, 0.012), (0.12, -0.14, 0.12), 70, None, False, True),
    "camcorder_front": ("camcorder", (0, -0.01, 0.055), (-0.3, -0.36, 0.14), 55, None, False, False),
    "camcorder_back": ("camcorder", (0.03, 0.0, 0.055), (0.34, 0.3, 0.12), 55, None, False, False),
    "player_open": ("tape_player", (0.0, 0.0, 0.11), (0.42, -0.3, 0.08), 55, 100, True, False),
    "player_closed": ("tape_player", (0.0, 0.0, 0.11), (-0.4, -0.32, 0.1), 55, 0, False, False),
}


def objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and "part" in o]


def on_floor(obs, flip=False):
    """Moves (and optionally flips) the prop so it rests on the floor."""
    M = Matrix.Rotation(math.pi, 4, "Y") if flip else Matrix.Identity(4)
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    zmin = min((o.matrix_world @ Vector(c)).z for o in obs for c in o.bound_box)
    for o in obs:
        o.location.z -= zmin
    return -zmin


def open_door(angle):
    """Swings the player's door down and out about its hinge."""
    door = bpy.data.objects["Door"]
    h = Vector(PB.PLAYER_HINGE)
    R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(angle), 4, "Y") @ Matrix.Translation(-h)
    door.matrix_world = R @ door.matrix_world


def insert_tape(props_dir):
    """Loads the tape into the player's bay: its long side along Y, its label facing out (+X)."""
    with bpy.data.libraries.load(os.path.join(props_dir, "tape.blend")) as (src, dst):
        dst.objects = list(src.objects)
    R = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # tape x -> y, y -> z, z -> x
    for o in dst.objects:
        if o is None:
            continue
        o.name = "Tape" + o.name
        del o["part"]
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = Matrix.Translation(Vector((0.004, 0.0, 0.0))) @ R @ o.matrix_basis  # not yet evaluated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("props")
    ap.add_argument("out")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--res", default="1000x800")
    ap.add_argument("--shots", default=",".join(SHOTS))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    w, h = (int(x) for x in a.res.split("x"))
    for shot in a.shots.split(","):
        blend, tgt, off, lens, door, tape, flip = SHOTS[shot]
        bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.abspath(a.props), f"{blend}.blend"))
        if door:
            open_door(door)
        if tape:
            insert_tape(os.path.abspath(a.props))
        obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        lift = on_floor(obs, flip)
        render.setup("studio", a.samples, (w, h))
        bpy.data.objects.remove(bpy.data.objects["Puddle"])
        bpy.context.scene.view_settings.look = "AgX - Punchy"
        bpy.context.scene.cycles.max_bounces = 10
        if tape:  # light into the open bay, so the loaded tape's label reads
            render.add_light("AREA", (0.45, -0.1, 0.16), 6, (1.0, 0.97, 0.92), 0.3, (0.0, 0.0, 0.11))
        render.VIEWS["shot"] = (None, (tgt[0], tgt[1], tgt[2] - 0.0 + 0.0 * lift), off, lens)
        cam = render.camera("Cam", "shot", None)
        cam.data.clip_start = 0.005
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = os.path.join(a.out, f"{shot}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", shot)


if __name__ == "__main__":
    main()
