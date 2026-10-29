"""Where the body's surfaces are: torso profile, neck, head, limb tubes and the torn chest."""
import math

from mathutils import noise

import skeleton as SK
from geom import Blob, Torso, Tube
from skeleton import J, V

TORSO = Torso()
NECK = Tube(V(0, 0.014, 1.98), V(0, 0.0, 2.37), [(0, 0.038, 0.036), (1, 0.032, 0.030)])
HEAD_C = V(0, 0.02, 2.47)
HEAD = Blob(HEAD_C, (0.18, 0.175, 0.23))


def limb_tubes(side):
    return {
        "uarm": Tube(J[f"elbow_{side}"], J[f"shoulder_{side}"], [(0, 0.043, 0.040), (0.55, 0.050, 0.047), (1, 0.056, 0.052)]),
        "farm": Tube(J[f"wrist_{side}"], J[f"elbow_{side}"], [(0, 0.030, 0.026), (0.65, 0.042, 0.038), (1, 0.042, 0.039)]),
        "thigh": Tube(J[f"knee_{side}"], J[f"hip_{side}"], [(0, 0.050, 0.048), (0.6, 0.068, 0.066), (1, 0.078, 0.074)]),
        "shin": Tube(J[f"ankle_{side}"], J[f"knee_{side}"], [(0, 0.036, 0.034), (0.72, 0.054, 0.052), (1, 0.050, 0.048)]),
    }


LIMBS = {side: limb_tubes(side) for side, _ in SK.SIDES}

# torn-open chest: a hole on the front-left showing rolled-poster ribs
CAV = dict(th=-0.80, z=1.65, dth=0.42, dz=0.11)


def cavity_e(p):
    th, b = TORSO.theta_b(p)
    z = TORSO.z0 + b
    dth = math.atan2(math.sin(th - CAV["th"]), math.cos(th - CAV["th"]))
    return (dth / CAV["dth"]) ** 2 + ((z - CAV["z"]) / CAV["dz"]) ** 2 + 0.25 * noise.noise(V(th * 4, z * 20, 0.5))


def head_weights(p):
    return {"Head": 1.0} if p.z > 2.38 else {"Head": 0.7, "Neck": 0.3}


def torso_part(p):
    return "pelvis" if p.z < 1.36 else "torso"
