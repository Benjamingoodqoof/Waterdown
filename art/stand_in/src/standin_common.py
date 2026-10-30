"""Shared layout for the Stand-in: texture atlas regions, joint positions and the R15 rig.

Blender units are meters, Z is up, she faces -Y, so her left side is +X. Height is
2.53 m (8.3 ft). Bones point straight up with no roll, the way Roblox's own R15 rigs do,
so standard Roblox animations rotate her joints about the same axes as a player's.
"""
import bpy  # noqa: F401  (loads mathutils when running as a module)
from mathutils import Vector


def V(*a):
    return Vector(a)


HEIGHT = 2.53

# ---------------------------------------------------------------- atlas (2048 px, x right, y down)
ATLAS = 2048
REGIONS = {
    "skin": (0, 0, 1024, 512),
    "sole": (1024, 0, 1280, 256),
    "shoe": (1280, 0, 1536, 256),
    "metal": (1536, 0, 1792, 256),
    "button": (1792, 0, 2048, 256),
    "belt": (1024, 256, 2048, 512),
    "skirt": (0, 512, 1024, 1024),
    "bodice": (1024, 512, 1536, 1024),
    "sleeve": (1536, 512, 2048, 768),
    "collar": (1536, 768, 2048, 1024),
    "apron": (0, 1024, 768, 1536),
    "pocket": (768, 1024, 1024, 1280),
    "hair_under": (768, 1280, 1024, 1536),
    "hair": (1024, 1024, 1536, 1536),
    "scalp": (1536, 1024, 2048, 1536),
    "badge": (1024, 1536, 1344, 1728),
    "lining": (0, 1536, 256, 1792),
}


def region_uv(name, inset=4):
    x0, y0, x1, y1 = REGIONS[name]
    return (x0 + inset) / ATLAS, 1 - (y1 - inset) / ATLAS, (x1 - inset) / ATLAS, 1 - (y0 + inset) / ATLAS


def in_region(name, u, v):
    """Map (u, v) in 0..1 into a region's UV rect."""
    u0, v0, u1, v1 = region_uv(name)
    return u0 + (u1 - u0) * min(1.0, max(0.0, u)), v0 + (v1 - v0) * min(1.0, max(0.0, v))


# ---------------------------------------------------------------- joints
J = {
    "root": V(0, 0, 1.55),
    "waist": V(0, 0, 1.72),
    "neck": V(0, 0.0, 2.20),
    "head_c": V(0, 0.004, 2.345),
}
SIDES = (("Left", 1.0), ("Right", -1.0))
for _s, _x in SIDES:
    J[f"shoulder_{_s}"] = V(0.205 * _x, 0.0, 2.095)
    J[f"elbow_{_s}"] = V(0.23 * _x, 0.01, 1.60)
    J[f"wrist_{_s}"] = V(0.245 * _x, -0.005, 1.245)
    J[f"hip_{_s}"] = V(0.092 * _x, 0.0, 1.43)
    J[f"knee_{_s}"] = V(0.086 * _x, -0.01, 0.765)
    J[f"ankle_{_s}"] = V(0.072 * _x, 0.015, 0.105)

# R15 bones: name -> (joint the bone sits on, parent)
BONES = {
    "Root": ("root", None),
    "HumanoidRootNode": ("root", "Root"),
    "LowerTorso": ("root", "HumanoidRootNode"),
    "UpperTorso": ("waist", "LowerTorso"),
    "Head": ("neck", "UpperTorso"),
}
for _s, _x in SIDES:
    BONES[f"{_s}UpperArm"] = (f"shoulder_{_s}", "UpperTorso")
    BONES[f"{_s}LowerArm"] = (f"elbow_{_s}", f"{_s}UpperArm")
    BONES[f"{_s}Hand"] = (f"wrist_{_s}", f"{_s}LowerArm")
    BONES[f"{_s}UpperLeg"] = (f"hip_{_s}", "LowerTorso")
    BONES[f"{_s}LowerLeg"] = (f"knee_{_s}", f"{_s}UpperLeg")
    BONES[f"{_s}Foot"] = (f"ankle_{_s}", f"{_s}LowerLeg")

# the 15 R15 body parts (one mesh each); Hair and BadgePhoto are extra meshes on the same rig
PARTS = ["Head", "UpperTorso", "LowerTorso"] + [f"{s}{p}" for s, _ in SIDES for p in
                                                 ("UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot")]
