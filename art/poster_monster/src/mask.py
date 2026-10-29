"""The cracked droplet-mascot mask: shape in mask space, triangulated with real holes for the
eyes and the cut smile, a split-and-lifted crack, rim walls, plus the dark sockets behind it."""
import math

import bpy  # noqa: I001  (bpy must load before bmesh/mathutils)
import bmesh
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

import common as C
from geom import lerp, region_uv
from layout import HEAD_C
from skeleton import V

MASK_TILT = Matrix.Rotation(math.radians(5.0), 3, "Y") @ Matrix.Rotation(math.radians(-4.0), 3, "X")
MASK_ORIGIN = V(0, -0.192, 2.455)
MASK_SCALE = 1.04


def dome(x, y):
    return -4.6 * x * x - (2.0 if y > 0 else 0.7) * y * y


def mask_world(x, y, z_extra=0.0):
    """Mask space (x right, y up, z toward the viewer) to world."""
    z = dome(x, y) + z_extra
    return HEAD_C + MASK_TILT @ (MASK_ORIGIN - HEAD_C + V(x, -z, y) * MASK_SCALE)


def mask_normal(x, y):
    fx = -9.2 * x
    fy = -(4.0 if y > 0 else 1.4) * y
    return (MASK_TILT @ V(-fx, -1.0, -fy)).normalized()


def point_in_poly(p, poly):
    x, y = p
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def dist_to_polyline(p, pts):
    best, best_t = 1e9, 0.0
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        ax, ay = a
        dx, dy = b[0] - ax, b[1] - ay
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        d = math.hypot(ax + dx * t - p[0], ay + dy * t - p[1])
        if d < best:
            best, best_t = d, (acc + t * math.sqrt(L2)) / total
        acc += math.sqrt(L2)
    return best, best_t


def build_mask_object(material):
    outline = C.mask_outline(150)
    eyes = [C.eye_outline(0), C.eye_outline(1)]
    slit = C.smile_slit()
    crack, _ = C.crack_path()
    verts2, faces_in = [], []
    for poly in [outline] + eyes + [slit]:
        faces_in.append(list(range(len(verts2), len(verts2) + len(poly))))
        verts2.extend(Vector(p) for p in poly)
    crack_idx = []
    for p in crack:
        hit = next((i for i, q in enumerate(verts2) if (q - Vector(p)).length < 1e-9), None)
        if hit is None:
            hit = len(verts2)
            verts2.append(Vector(p))
        crack_idx.append(hit)
    edges_in = list(zip(crack_idx, crack_idx[1:]))
    boundary = [q for q in verts2]
    step = 0.016
    gy = -0.23
    while gy < 0.27:
        gx = -0.19 + (0.5 * step if int(round(gy / step)) % 2 else 0.0)
        while gx < 0.19:
            p = (gx, gy)
            if point_in_poly(p, outline) and not any(point_in_poly(p, h) for h in eyes + [slit]):
                if min((Vector(p) - q).length for q in boundary) > 0.0075:
                    verts2.append(Vector(p))
            gx += step
        gy += step * 0.866
    res = delaunay_2d_cdt(verts2, edges_in, faces_in, 2, 1e-7, True)
    out_v, out_f = res[0], res[2]

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    bv = [bm.verts.new(mask_world(v.x, v.y)) for v in out_v]
    for f in out_f:
        a, b, c = (out_v[i] for i in f[:3])
        area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
        idx = list(f) if area > 0 else list(f)[::-1]
        face = bm.faces.new([bv[i] for i in idx])
        for loop, i in zip(face.loops, idx):
            loop[uvl].uv = C.mask_uv(out_v[i].x, out_v[i].y)
    bm.verts.ensure_lookup_table()

    def v2d(v):
        u, w = v.link_loops[0][uvl].uv
        return (u - 0.5) * C.MASK_UV_SCALE, (w - 0.5) * C.MASK_UV_SCALE + C.MASK_YC

    # split the crack open and lift its outer side: a broken, bent piece of plastic
    crack_edges = []
    for e in bm.edges:
        a, b = v2d(e.verts[0]), v2d(e.verts[1])
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if all(dist_to_polyline(q, crack)[0] < 1e-6 for q in (a, b, m)):
            crack_edges.append(e)
    bmesh.ops.split_edges(bm, edges=crack_edges)
    (cx0, cy0), (cx1, cy1) = crack[0], crack[-1]
    for v in bm.verts:
        if not v.link_faces:
            continue
        fc = [sum(v2d(x)[k] for x in f.verts) / len(f.verts) for f in v.link_faces for k in (0, 1)]
        px = sum(fc[0::2]) / len(v.link_faces)
        py = sum(fc[1::2]) / len(v.link_faces)
        d, t = dist_to_polyline((px, py), crack)
        side = (cx1 - cx0) * (py - cy0) - (cy1 - cy0) * (px - cx0)
        if side < 0 and d < 0.05:
            x, y = v2d(v)
            v.co += mask_normal(x, y) * 0.0042 * lerp(1.0, 0.25, t) * (1 - d / 0.05)

    # rim walls
    edge_verts = {}
    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    for e in bnd:
        e.smooth = False
    src = {v: v2d(v) for e in bnd for v in e.verts}
    ret = bmesh.ops.extrude_edge_only(bm, edges=bnd)
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    new_faces = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
    new_face_set = set(new_faces)
    by_pos = {tuple(round(c, 7) for c in v.co): v for v in src}
    for v in new_verts:
        o = by_pos.get(tuple(round(c, 7) for c in v.co))
        x, y = src[o] if o else (0.0, 0.0)
        edge_verts[v] = (x, y)
        v.co -= mask_normal(x, y) * 0.0045
    bm.normal_update()
    for f in new_faces:
        f.smooth = False
        for loop in f.loops:
            xy = edge_verts.get(loop.vert) or src.get(loop.vert) or (0.0, 0.0)
            loop[uvl].uv = C.mask_uv(*xy)
        orig = [v for v in f.verts if v not in edge_verts]
        if len(orig) == 2:
            shared = [g for g in orig[0].link_faces if g in orig[1].link_faces and g is not f]
            if shared:
                want = f.calc_center_median() - shared[0].calc_center_median()
                if f.normal.dot(want) < 0:
                    f.normal_flip()
    for f in bm.faces:
        if f not in new_face_set:
            f.smooth = True
    bm.normal_update()
    me = bpy.data.meshes.new("Mask")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    ob = bpy.data.objects.new("Mask", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def add_cup(mb, cx, cy, rx, ry, depth, nphi=14, nalpha=4, curve=None):
    """Dark socket behind a hole in the mask, open toward the viewer. curve(x) bends it along a smile."""
    uv = region_uv("void")
    rings = []
    for ia in range(nalpha + 1):
        al = (math.pi / 2) * (1 - ia / nalpha)
        ring = []
        for ip in range(nphi + 1):
            ph = 2 * math.pi * ip / nphi
            x = cx + rx * math.sin(al) * math.cos(ph)
            y = (curve(x) if curve else cy) + ry * math.sin(al) * math.sin(ph)
            p = mask_world(x, y, -0.004 - depth * math.cos(al))
            ring.append((mb.add_vert(p, None, {"Head": 1.0}),
                         (uv[0] + (uv[2] - uv[0]) * ip / nphi, uv[1] + (uv[3] - uv[1]) * ia / nalpha)))
        rings.append(ring)
    front = mask_world(cx, cy, 0.08)
    for k in range(nalpha):
        for ip in range(nphi):
            quad = [rings[k][ip], rings[k][ip + 1], rings[k + 1][ip + 1], rings[k + 1][ip]]
            ctr = sum((mb.co[i] for i, _ in quad), Vector()) / 4
            mb.add_oriented(quad, front - ctr)
