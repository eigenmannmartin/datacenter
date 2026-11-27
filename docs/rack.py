#!/usr/bin/env python3
"""
rack.py - a procedural 10-inch rack cabinet ("the three-server box") and its studio shots.

    python3 rack.py --shot studio-light --samples 192 --scale 1.0 --out out/studio-light.png
    python3 rack.py --shot front-dark   --samples 48  --scale 0.5 --out previews/front-dark.png

Shots    studio-light, studio-dark   three-quarter view from the front right
         front-light,  front-dark    straight front view
         light = lit for a light page (#eceef0), dark = lit for a near-black page (#0b0c0d)
Output   <out>.png            RGBA, transparent film; the contact shadow is in the alpha channel
         <out>-on-page.jpg    the same image flattened on the page colour (override with --page)
         passes/              next to this script: the two render passes of every image
                              (<name>-beauty.png = the product, <name>-shadow.png = its shadow)
Options  --scale 1.0 is 1600 x 2000 px; --region x0,y0,x1,y1 renders only a crop (fractions of
         the frame, y from the bottom) for looking at details; --reuse-beauty redoes only the
         shadow pass and the finish (for tuning the shadow); --blend saves the scene.

Needs Blender as a Python module (bpy), numpy and Pillow. Cycles on the CPU, at most three
threads. Everything is built from the parameters below: geometry in Python, modifiers, shader
nodes. There are no external assets. No brand names, logos or text anywhere.

Where to change what
    proportions, sheet thickness, gaps ........ the parameters right below
    a part .................................... cabinet(), feet(), door(), rails(), firewall(),
                                                switch(), server(), backup_unit(), ups(), cables()
    surfaces .................................. make_materials() and the mat_*() functions
    lighting .................................. studio_lights(): softbox(), glass_sheen(), world()
    camera, framing, depth of field ........... camera()
    samples, bounces, view transform .......... setup_render()
    the shadow on the page .................... SHADOW_LAMP, SHADOW_SIZE, SHADOW_LEVELS
    lens glare, grain ......................... finish_image()

Units are metres. X = width (left/right seen from the front), Y = depth (the door looks to -Y),
Z = up. The cabinet stands on the floor z = 0, centred on the origin.
"""
import argparse
import math
import os
import random
import sys
import time
from types import SimpleNamespace

try:  # keep to three cores, other work shares the machine
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:3]))
except Exception:
    pass

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

# --------------------------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------------------------
MM = 0.001

W, D, H = 300 * MM, 330 * MM, 480 * MM   # cabinet, outside
FOOT_H = 12 * MM
SHEET = 1.2 * MM                          # sheet steel
BEND_R = 2.6 * MM                         # outer radius of the folded cabinet edges
SIDE_FRAME_T = 10 * MM                    # depth of the body frame around the side panels
SIDE_BORDER = 22 * MM                     # visible width of that frame
PANEL_GAP = 1.4 * MM                      # gap around the removable side panels
DOOR_T = 16 * MM
DOOR_GAP = 2 * MM                         # gap between door and body
STILE = 24 * MM                           # door frame, left and right
DOOR_RAIL = 34 * MM                       # door frame, top and bottom
GLASS_T = 4 * MM
GLASS_INSET = 6 * MM                      # glass sits this far behind the door front

U = 44.45 * MM
N_U = 9
RACK_OPEN = 222.25 * MM                   # clear width between the rails
RACK_W = 254 * MM                         # 10 inch
HOLE_PITCH_X = 236.525 * MM
RAIL_SETBACK = 56 * MM                    # rail front, measured from the body front
EAR_T = 2 * MM

# derived
Z0 = FOOT_H
ZT = Z0 + H
YF = -D / 2                               # door front
YB = D / 2
YBODY = YF + DOOR_T + DOOR_GAP            # body front
ZR = Z0 + (H - N_U * U) / 2               # bottom of the 9U mounting space
YRAIL = YBODY + RAIL_SETBACK              # front face of the rails
YDEV = YRAIL - EAR_T                      # front face of ears and faceplates
XO = RACK_OPEN / 2
XE = RACK_W / 2
XH = HOLE_PITCH_X / 2
GX = W / 2 - STILE                        # half width of the glass opening
GZ0 = Z0 + DOOR_RAIL
GZ1 = ZT - DOOR_RAIL
YGLASS = YF + GLASS_INSET                 # front face of the glass
FAN_Y = 0.025                             # centre of the fan grille on the top

SERVER_SLOT = 3.5 * U / 3                 # three servers share 3.5U
SLOTS = {                                 # bottom of every device slot
    'ups': ZR,
    'backup': ZR + 2 * U,
    'server3': ZR + 3.5 * U,
    'server2': ZR + 3.5 * U + SERVER_SLOT,
    'server1': ZR + 3.5 * U + 2 * SERVER_SLOT,
    'switch': ZR + 7 * U,
    'firewall': ZR + 8 * U,
}

LED_GREEN = (0.035, 0.95, 0.22)           # linear RGB of the status lights

# The contact shadow on the page: one lamp high above the cabinet draws it (plus a little of the
# ambient light). Higher and smaller = tighter and harder; moving it sideways moves the shadow.
SHADOW_LAMP = (0.0, 0.0, 6.0)
SHADOW_SIZE = 0.9
SHADOW_LEVELS = dict(floor=0.05, gain=0.9, gamma=1.0)     # retouch: cut the faint far field, overall density

SHOTS = {
    'studio-light': dict(view='studio', mood='light', page=(0xEC, 0xEE, 0xF0)),
    'studio-dark': dict(view='studio', mood='dark', page=(0x0B, 0x0C, 0x0D)),
    'front-light': dict(view='front', mood='light', page=(0xEC, 0xEE, 0xF0)),
    'front-dark': dict(view='front', mood='dark', page=(0x0B, 0x0C, 0x0D)),
}

RNG = random.Random(11)
LEDS = []                                 # (position, size in metres, kind) of every lit status light, for the lens glare


# --------------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------------
def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def new_mesh_object(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    return link(ob)


def shade(ob, smooth=True):
    me = ob.data
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    me.update()


def finish(ob, bevel=0.4 * MM, segs=2, limit=40.0):
    """Round every hard edge a little and shade smooth with face-weighted normals."""
    if bevel is None:
        return ob
    if bevel <= 0:
        shade(ob, False)
        return ob
    m = ob.modifiers.new('bevel', 'BEVEL')
    m.width = bevel
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(limit)
    shade(ob, True)
    w = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    w.keep_sharp = True
    w.weight = 100
    return ob


def bake(ob):
    """Apply the modifier stack (used right after booleans)."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


_BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def _box_verts(lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    return [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]


def box(name, lo, hi, mat=None, bevel=0.4 * MM, segs=2):
    """Axis-aligned box from corner lo to corner hi."""
    return finish(new_mesh_object(name, _box_verts(lo, hi), _BOX_FACES, mat), bevel, segs)


def boxes(name, lohi, mat=None, bevel=0.0, segs=1):
    """Many boxes in one mesh."""
    verts, faces = [], []
    for lo, hi in lohi:
        n = len(verts)
        verts += _box_verts(lo, hi)
        faces += [tuple(i + n for i in f) for f in _BOX_FACES]
    return finish(new_mesh_object(name, verts, faces, mat), bevel, segs)


def cut(ob, lohi):
    """Boolean-subtract axis-aligned boxes from ob, then apply."""
    verts, faces = [], []
    for lo, hi in lohi:
        n = len(verts)
        verts += _box_verts(lo, hi)
        faces += [tuple(i + n for i in f) for f in _BOX_FACES]
    cutter = new_mesh_object(ob.name + '_cutter', verts, faces)
    m = ob.modifiers.new('cut', 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bake(ob)
    me = cutter.data
    bpy.data.objects.remove(cutter)
    bpy.data.meshes.remove(me)
    return ob


def cylinder(name, p0, p1, r, mat=None, bevel=0.3 * MM, segs=2, n=48, r1=None):
    """Cylinder (or cone) from p0 to p1, radius r at p0 and r1 at p1."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    bm = bmesh.new()
    mtx = Matrix.Translation((p0 + p1) / 2) @ axis.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                          radius2=r if r1 is None else r1, depth=axis.length, matrix=mtx)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    return finish(link(ob), bevel, segs)


# ---- 2D outlines (counter-clockwise lists of (u, v)) ----
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rrect(x0, y0, x1, y1, r, n=3):
    r = min(r, (x1 - x0) / 2 - 1e-6, (y1 - y0) / 2 - 1e-6)
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle(cx, cy, r, n=16):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def slot(cx, cy, length, width, vertical=False, n=5):
    """Obround slot."""
    r = width / 2
    h = max(length / 2 - r, 0.0)
    pts = []
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        pts.append((h + r * math.cos(a), r * math.sin(a)))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n
        pts.append((-h + r * math.cos(a), r * math.sin(a)))
    if vertical:
        pts = [(-y, x) for x, y in pts]
    return [(cx + x, cy + y) for x, y in pts]


def rj45(cx, cy, grow=0.0):
    """Opening of an RJ45 jack, latch notch at the bottom."""
    w, h, nw, nh = 11.7 * MM + 2 * grow, 7.8 * MM + 2 * grow, 6.0 * MM + 2 * grow, 2.2 * MM
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return [(x0, y0), (cx - nw / 2, y0), (cx - nw / 2, y0 - nh), (cx + nw / 2, y0 - nh),
            (cx + nw / 2, y0), (x1, y0), (x1, y1), (x0, y1)]


def round_poly(pts, r, n=3):
    """Fillet every corner of a polygon."""
    out = []
    N = len(pts)
    for i in range(N):
        A, P, B = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % N])
        d1, d2 = P - A, B - P
        l1, l2 = d1.length, d2.length
        d1, d2 = d1 / l1, d2 / l2
        cr = d1.x * d2.y - d1.y * d2.x
        th = math.acos(max(-1.0, min(1.0, d1.dot(d2))))
        if abs(cr) < 1e-9 or r <= 0:
            out.append((P.x, P.y))
            continue
        t = min(r * math.tan(th / 2), 0.45 * l1, 0.45 * l2)
        rr = t / math.tan(th / 2)
        s = 1.0 if cr > 0 else -1.0
        n1 = Vector((-d1.y, d1.x)) * s
        C = P - d1 * t + n1 * rr
        a0 = math.atan2(-n1.y, -n1.x)
        for k in range(n + 1):
            a = a0 + s * th * k / n
            out.append((C.x + rr * math.cos(a), C.y + rr * math.sin(a)))
    return out


def hex_grid(x0, y0, x1, y1, pitch, inside=None):
    """Centres of a hexagonal hole pattern inside a rectangle (or inside a predicate)."""
    pts = []
    dy = pitch * math.sqrt(3) / 2
    rows = int((y1 - y0) / dy) + 1
    yoff = ((y1 - y0) - (rows - 1) * dy) / 2
    for j in range(rows):
        y = y0 + yoff + j * dy
        cols = int((x1 - x0 - (pitch / 2 if j % 2 else 0)) / pitch) + 1
        xoff = ((x1 - x0) - (cols - 1) * pitch) / 2
        for i in range(cols):
            p = (x0 + xoff + i * pitch, y)
            if inside is None or inside(*p):
                pts.append(p)
    return pts


def _area(poly):
    return 0.5 * sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))


def sheet(name, outline, holes, thick, mat=None, plane='XZ', at=0.0, bevel=0.25 * MM, segs=1, flip=False):
    """Sheet-metal part with real holes and real thickness.

    outline, holes: 2D polygons (u, v).
    plane 'XZ': u = x, v = z; the face lies at y = at and looks to -y, the body goes to +y.
    plane 'YZ': u = y, v = z; the face lies at x = at and looks to +x, the body goes to -x.
    plane 'XY': u = x, v = y; the face lies at z = at and looks up, the body goes down.
    flip: the face looks the other way (and the body goes the other way).
    """
    pts = [Vector(p) for p in (outline if _area(outline) > 0 else outline[::-1])]
    faces = [list(range(len(pts)))]
    for h in holes:
        h = h if _area(h) < 0 else h[::-1]
        faces.append(list(range(len(pts), len(pts) + len(h))))
        pts += [Vector(p) for p in h]
    vc, _e, fc, *_ = delaunay_2d_cdt(pts, [], faces, 3, 1e-7)
    if plane == 'XZ':
        verts, want = [(p.x, at, p.y) for p in vc], Vector((0, -1, 0))
    elif plane == 'YZ':
        verts, want = [(at, p.x, p.y) for p in vc], Vector((1, 0, 0))
    else:
        verts, want = [(p.x, p.y, at) for p in vc], Vector((0, 0, 1))
    if flip:
        want = -want
    ob = new_mesh_object(name, verts, fc, mat)
    if ob.data.polygons[0].normal.dot(want) < 0:
        ob.data.flip_normals()
        ob.data.update()
    s = ob.modifiers.new('solid', 'SOLIDIFY')
    s.thickness = thick
    s.offset = -1.0
    return finish(ob, bevel, segs)


# --------------------------------------------------------------------------------------------
# Materials (all procedural)
# --------------------------------------------------------------------------------------------
class Nodes:
    """Tiny helper around a node tree."""

    def __init__(self, tree):
        self.t = tree

    def new(self, kind, **props):
        n = self.t.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.t.links.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        n = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                self.link(x, n.inputs[i])
        return n.outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5, stretch=None, rot=None):
        if rot is not None:                       # turn the pattern first, then stretch it
            m = self.new('ShaderNodeMapping')
            m.inputs['Rotation'].default_value = rot
            self.link(vec, m.inputs['Vector'])
            vec = m.outputs[0]
        if stretch is not None:
            m = self.new('ShaderNodeMapping')
            m.inputs['Scale'].default_value = stretch
            self.link(vec, m.inputs['Vector'])
            vec = m.outputs[0]
        n = self.new('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        self.link(vec, n.inputs['Vector'])
        return n.outputs[0]

    def bump(self, height, distance, normal=None, strength=1.0):
        b = self.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = strength
        b.inputs['Distance'].default_value = distance
        self.link(height, b.inputs['Height'])
        if normal is not None:
            self.link(normal, b.inputs['Normal'])
        return b.outputs[0]

    def remap(self, x, lo, hi, a=0.0, b=1.0):
        n = self.new('ShaderNodeMapRange')
        n.inputs['From Min'].default_value = a
        n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = lo
        n.inputs['To Max'].default_value = hi
        self.link(x, n.inputs[0])
        return n.outputs[0]

    def position(self):
        return self.new('ShaderNodeNewGeometry').outputs['Position']


def _material(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    nt.nodes.clear()
    N = Nodes(nt)
    out = N.new('ShaderNodeOutputMaterial')
    return m, N, out


def _principled(name, color, rough, metallic=0.0):
    m, N, out = _material(name)
    b = N.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic
    N.link(b.outputs[0], out.inputs['Surface'])
    return m, N, b


def mat_powder(name, color, rough=0.48, peel=1.0, grain=1.0, tone=0.03, flat=1.0):
    """Powder coat or fine-texture paint: satin, orange peel, fine grain, uneven film."""
    m, N, b = _principled(name, color, rough)
    pos = N.position()
    big = N.noise(pos, 7.0, 3.0)
    mid = N.noise(pos, 650.0, 2.0)            # about 1.5 mm orange peel
    fine = N.noise(pos, 3800.0, 1.0)          # fine structure
    wave = N.noise(pos, 11.0, 1.0)            # sheet metal is never perfectly flat
    n0 = N.bump(wave, 1.0e-3 * flat)
    n1 = N.bump(mid, 4.0e-5 * peel, n0)
    n2 = N.bump(fine, 1.2e-5 * grain, n1)
    N.link(n2, b.inputs['Normal'])
    N.link(N.remap(big, rough - 0.05, rough + 0.05), b.inputs['Roughness'])
    mix = N.new('ShaderNodeMix', data_type='RGBA')
    mix.inputs['A'].default_value = (*[c * (1 - tone) for c in color], 1)
    mix.inputs['B'].default_value = (*[min(1, c * (1 + tone)) for c in color], 1)
    N.link(big, mix.inputs['Factor'])
    N.link(mix.outputs['Result'], b.inputs['Base Color'])
    return m


def mat_metal(name, color, rough=0.38, brush=1.0, axis='X', blotch=0.0):
    """Anodised or plated metal with a brushed grain along one axis."""
    m, N, b = _principled(name, color, rough, 1.0)
    pos = N.position()
    stretch = {'X': (6, 2600, 2600), 'Y': (2600, 6, 2600), 'Z': (2600, 2600, 6)}[axis]
    streak = N.noise(pos, 1.0, 3.0, 0.6, stretch=stretch)
    big = N.noise(pos, 11.0, 3.0)
    r = N.math('ADD', N.remap(streak, rough - 0.10 * brush, rough + 0.10 * brush), N.remap(big, -0.04 - blotch, 0.04 + blotch))
    N.link(r, b.inputs['Roughness'])
    N.link(N.bump(streak, 3.0e-6 * brush), b.inputs['Normal'])
    mix = N.new('ShaderNodeMix', data_type='RGBA')
    mix.inputs['A'].default_value = (*[c * 0.86 for c in color], 1)
    mix.inputs['B'].default_value = (*[min(1, c * 1.14) for c in color], 1)
    N.link(streak, mix.inputs['Factor'])
    N.link(mix.outputs['Result'], b.inputs['Base Color'])
    return m


def mat_plastic(name, color, rough=0.4):
    m, N, b = _principled(name, color, rough)
    pos = N.position()
    N.link(N.remap(N.noise(pos, 40.0, 3.0), rough - 0.06, rough + 0.06), b.inputs['Roughness'])
    N.link(N.bump(N.noise(pos, 2500.0, 1.0), 6.0e-6), b.inputs['Normal'])
    return m


def mat_glass(name, tint=(0.898, 0.912, 0.914), smudge=1.0):
    """Door glass: real refraction for the camera, plain tinted transparency for shadow rays
    (so the softboxes light the inside without caustic noise), plus a trace of wiping marks:
    a faint, slightly rough extra reflection in sparse streaks. It only shows where a light
    source is mirrored in the pane."""
    m, N, out = _material(name)
    g = N.new('ShaderNodeBsdfGlass')
    g.inputs['Color'].default_value = (*tint, 1)
    g.inputs['Roughness'].default_value = 0.0
    g.inputs['IOR'].default_value = 1.52
    pos = N.position()
    streak = N.noise(pos, 1.0, 3.0, 0.55, stretch=(5, 5, 90), rot=(0, math.radians(-24), 0))
    blot = N.noise(pos, 9.0, 3.0, 0.55)
    sm = N.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    sm.inputs['From Min'].default_value = 0.52
    sm.inputs['From Max'].default_value = 0.85
    N.link(streak, sm.inputs[0])
    mask = N.math('MULTIPLY', sm.outputs[0], N.remap(blot, 0.0, 1.0, 0.42, 0.62))
    haze = N.new('ShaderNodeBsdfGlossy')
    haze.inputs['Roughness'].default_value = 0.14
    rgb = N.new('ShaderNodeCombineColor')
    v = N.math('MULTIPLY', mask, 0.016 * smudge, clamp=True)
    for i in range(3):
        N.link(v, rgb.inputs[i])
    N.link(rgb.outputs[0], haze.inputs['Color'])
    add = N.new('ShaderNodeAddShader')
    N.link(g.outputs[0], add.inputs[0])
    N.link(haze.outputs[0], add.inputs[1])
    tr = N.new('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = (*tint, 1)
    lp = N.new('ShaderNodeLightPath')
    mix2 = N.new('ShaderNodeMixShader')
    N.link(lp.outputs['Is Shadow Ray'], mix2.inputs[0])
    N.link(add.outputs[0], mix2.inputs[1])
    N.link(tr.outputs[0], mix2.inputs[2])
    N.link(mix2.outputs[0], out.inputs['Surface'])
    return m


def mat_emit(name, color, strength):
    m, N, out = _material(name)
    e = N.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*color, 1)
    e.inputs['Strength'].default_value = strength
    N.link(e.outputs[0], out.inputs['Surface'])
    return m


def make_materials(mood):
    led = 1.0 if mood == 'light' else 0.5
    M = SimpleNamespace()
    M.powder = mat_powder('powder_light_grey', (0.52, 0.54, 0.555), 0.47)
    M.paint = mat_powder('paint_anthracite', (0.024, 0.026, 0.028), 0.44, peel=0.7, grain=0.8, tone=0.06)
    M.bracket = mat_powder('paint_black', (0.016, 0.017, 0.018), 0.50, peel=0.6, tone=0.06)
    M.backup = mat_powder('paint_graphite', (0.036, 0.038, 0.041), 0.56, peel=0.5, tone=0.05)
    M.alu = mat_metal('alu_anthracite', (0.060, 0.063, 0.068), 0.42, brush=1.0)
    M.alu_fw = mat_metal('alu_firewall', (0.085, 0.088, 0.093), 0.48, brush=0.5, blotch=0.03)
    M.zinc = mat_metal('zinc', (0.60, 0.62, 0.64), 0.40, brush=0.35, axis='Z', blotch=0.06)
    M.steel = mat_metal('steel_screw', (0.50, 0.50, 0.49), 0.30, brush=0.2, axis='Z')
    M.chrome = mat_metal('nickel', (0.70, 0.69, 0.67), 0.20, brush=0.25, axis='X')
    M.plastic = mat_plastic('plastic_black', (0.010, 0.010, 0.011), 0.38)
    M.liner = mat_plastic('liner_black', (0.004, 0.004, 0.004), 0.7)
    M.rubber = mat_plastic('rubber', (0.012, 0.012, 0.012), 0.72)
    M.cable = mat_plastic('cable_grey', (0.56, 0.57, 0.58), 0.30)
    M.foot = mat_plastic('foot_rubber', (0.030, 0.030, 0.032), 0.62)
    M.plug = mat_plastic('plug_clear', (0.42, 0.43, 0.44), 0.22)
    M.usb = mat_plastic('usb_tongue', (0.06, 0.06, 0.065), 0.35)
    M.display = _principled('display', (0.006, 0.007, 0.008), 0.06)[0]
    M.glass = mat_glass('glass')
    M.led = mat_emit('led_green', LED_GREEN, 55.0 * led)
    M.led_ring = mat_emit('led_ring', LED_GREEN, 16.0 * led)
    M.led_port = mat_emit('led_port', LED_GREEN, 26.0 * led)
    M.led_off = mat_plastic('led_off', (0.020, 0.030, 0.024), 0.25)
    return M


# --------------------------------------------------------------------------------------------
# The cabinet
# --------------------------------------------------------------------------------------------
def rack_hole_zs():
    return [ZR + u * U + off * MM for u in range(N_U) for off in (6.35, 22.225, 38.1)]


def cabinet(M):
    """Welded body: outer skin with folded edges, front flange, frame around the side panels,
    removable side panels with vent slots, fan grille on top."""
    xi = W / 2 - SIDE_FRAME_T
    body = new_mesh_object('body', _box_verts((-W / 2, YBODY, Z0), (W / 2, YB, ZT)), _BOX_FACES, M.powder)
    b = body.modifiers.new('bend', 'BEVEL')
    b.width, b.segments, b.limit_method = BEND_R, 4, 'ANGLE'
    cut(body, [((-xi, YBODY + SHEET, Z0 + SHEET), (xi, YB - SHEET, ZT - SHEET))])                 # the inside
    cut(body, [((-GX - 6 * MM, YBODY - 0.01, GZ0 - 6 * MM), (GX + 6 * MM, YBODY + SHEET + 0.001, GZ1 + 6 * MM))])  # front opening
    sy0, sy1, sz0, sz1 = YBODY + SIDE_BORDER, YB - SIDE_BORDER, Z0 + SIDE_BORDER, ZT - SIDE_BORDER
    cut(body, [((-W / 2 - 0.01, sy0, sz0), (-xi + 0.001, sy1, sz1)),
               ((xi - 0.001, sy0, sz0), (W / 2 + 0.01, sy1, sz1))])                               # side windows
    cut(body, [((-0.047, FAN_Y - 0.047, ZT - SHEET - 0.001), (0.047, FAN_Y + 0.047, ZT + 0.01))])  # fan opening
    finish(body, 0.3 * MM, 1)

    # side panels: flush, with a shadow gap all round and two bands of vent slots
    g = PANEL_GAP
    yc = (sy0 + sy1) / 2
    for s in (-1, 1):
        holes = []
        for zrow in (sz1 - 34 * MM, sz1 - 64 * MM, sz0 + 64 * MM, sz0 + 34 * MM):
            for i in range(24):
                holes.append(slot(yc + (i - 11.5) * 9.0 * MM, zrow, 22 * MM, 3.4 * MM, vertical=True))
        sheet('side_panel', rrect(sy0 + g, sz0 + g, sy1 - g, sz1 - g, 2 * MM), holes, SHEET, M.powder,
              'YZ', at=s * (W / 2 - 0.5 * MM), flip=(s < 0))

    # fan grille on the top: a perforated plate screwed over the opening
    r_perf = 43 * MM
    centres = hex_grid(-0.05, FAN_Y - 0.05, 0.05, FAN_Y + 0.05, 6.2 * MM,
                       inside=lambda x, y: math.hypot(x, y - FAN_Y) < r_perf)
    holes = [circle(x, y, 2.2 * MM, 12) for x, y in centres]
    sheet('fan_grille', rrect(-0.058, FAN_Y - 0.058, 0.058, FAN_Y + 0.058, 5 * MM, 4), holes, SHEET, M.powder,
          'XY', at=ZT + SHEET)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cylinder('fan_screw', (sx * 0.050, FAN_Y + sy * 0.050, ZT + SHEET),
                     (sx * 0.050, FAN_Y + sy * 0.050, ZT + SHEET + 1.2 * MM), 2.6 * MM, M.steel, 0.5 * MM, 2, n=24)


def feet(M):
    for sx in (-1, 1):
        for y in (YBODY + 0.024, YB - 0.024):
            x = sx * (W / 2 - 0.026)
            cylinder('foot', (x, y, -0.0004), (x, y, Z0 + 0.0002), 0.0130, M.foot, 1.2 * MM, 3, r1=0.0150)


def door(M):
    """Steel frame, tinted glass with a rubber gasket, round lock on the right, hinges on the left."""
    sheet('door_frame', rrect(-W / 2, Z0, W / 2, ZT, 3 * MM, 4), [rrect(-GX, GZ0, GX, GZ1, 2 * MM, 3)],
          DOOR_T, M.powder, 'XZ', at=YF, bevel=1.4 * MM, segs=3)
    box('door_glass', (-GX - 1 * MM, YGLASS, GZ0 - 1 * MM), (GX + 1 * MM, YGLASS + GLASS_T, GZ1 + 1 * MM), M.glass, 0)
    sheet('door_gasket', rrect(-GX, GZ0, GX, GZ1, 2 * MM, 3),
          [rrect(-GX + 2.6 * MM, GZ0 + 2.6 * MM, GX - 2.6 * MM, GZ1 - 2.6 * MM, 1 * MM, 3)],
          1.9 * MM, M.rubber, 'XZ', at=YGLASS - 2.0 * MM, bevel=0.5 * MM, segs=2)
    # lock
    lx, lz = W / 2 - STILE / 2, Z0 + H / 2
    cylinder('lock_bezel', (lx, YF + 0.5 * MM, lz), (lx, YF - 2.0 * MM, lz), 7.6 * MM, M.chrome, 0.8 * MM, 3)
    plug = cylinder('lock_plug', (lx, YF, lz), (lx, YF - 3.0 * MM, lz), 4.6 * MM, M.chrome, None)
    cut(plug, [((lx - 0.45 * MM, YF - 3.2 * MM, lz - 2.9 * MM), (lx + 0.45 * MM, YF - 1.2 * MM, lz + 2.9 * MM))])
    finish(plug, 0.3 * MM, 2)
    # hinges
    hx, hy = -W / 2 - 1.2 * MM, YBODY - DOOR_GAP / 2
    for hz in (Z0 + 0.078, ZT - 0.078):
        for k in (-1, 0, 1):
            cylinder('hinge', (hx, hy, hz + k * 0.0102 - 0.0049), (hx, hy, hz + k * 0.0102 + 0.0049), 3.0 * MM,
                     M.powder, 0.5 * MM, 2, n=32)


def rails(M):
    """Front 10-inch rails: zinc-plated angle with square holes, three per U."""
    z0, z1 = ZR - 10 * MM, ZR + N_U * U + 10 * MM
    for s in (-1, 1):
        xa, xb = sorted((s * XO, s * XE))
        holes = [rrect(s * XH - 4.75 * MM, z - 4.75 * MM, s * XH + 4.75 * MM, z + 4.75 * MM, 0.7 * MM, 2)
                 for z in rack_hole_zs()]
        sheet('rail', rect(xa, z0, xb, z1), holes, 2 * MM, M.zinc, 'XZ', at=YRAIL)
        box('rail_web', (s * XE, YRAIL, z0), (s * (XE - 2 * MM), YRAIL + 0.030, z1), M.zinc, 0.4 * MM)
        for zz in (z0 + 4 * MM, z1 - 8 * MM):
            box('rail_strut', (s * (XE - 1 * MM), YRAIL + 0.008, zz), (s * (W / 2 - SIDE_FRAME_T + 1 * MM), YRAIL + 0.026, zz + 4 * MM),
                M.zinc, 0.4 * MM)


_SCREW = {}


def screw(M, x, y, z, r=4.6 * MM):
    """Pan-head screw with a cross recess; the head sits on the plane y, pointing to -y."""
    if 'mesh' not in _SCREW:
        ob = cylinder('screw_src', (0, 0, 0), (0, -2.4 * MM, 0), r, M.steel, None, n=32)
        cut(ob, [((-0.5 * MM, -3 * MM, -2.6 * MM), (0.5 * MM, -1.3 * MM, 2.6 * MM))])
        cut(ob, [((-2.6 * MM, -3 * MM, -0.5 * MM), (2.6 * MM, -1.3 * MM, 0.5 * MM))])
        finish(ob, 0.7 * MM, 3)
        bake(ob)
        shade(ob, True)
        _SCREW['mesh'] = ob.data
        bpy.data.objects.remove(ob)
    ob = bpy.data.objects.new('screw', _SCREW['mesh'])
    ob.location = (x, y, z)
    ob.rotation_euler = (0, RNG.uniform(0, math.pi), 0)
    return link(ob)


def ear(M, name, s, x_in, z0, z1, hole_zs, mat):
    """Rack ear: a flat tab on the rail with slotted holes and its screws."""
    xa, xb = sorted((s * x_in, s * XE))
    holes = [slot(s * XH, z, 10 * MM, 6.6 * MM) for z in hole_zs]
    sheet(name, rrect(xa, z0, xb, z1, 1.2 * MM, 2), holes, EAR_T, mat, 'XZ', at=YDEV)
    for z in hole_zs:
        screw(M, s * XH, YDEV, z)


def jack_block(M, name, region, holes, y, depth=13 * MM, mat=None):
    """Plastic block with real cavities behind a front panel."""
    x0, z0, x1, z1 = region
    sheet(name, rect(x0, z0, x1, z1), holes, depth, mat or M.plastic, 'XZ', at=y, bevel=0.15 * MM)
    box(name + '_back', (x0, y + depth, z0), (x1, y + depth + 0.6 * MM, z1), M.liner, 0)


LED_WELL = 1.65 * MM                      # radius of the hole a status light sits in


def led_dot(name, x, y, z, mat, r=1.15 * MM):
    """Status light: a small light pipe, set back in a round hole of the panel whose front is at y.
    The wall of the hole catches the light, which is the glow one sees around a real LED."""
    LEDS.append((Vector((x, y, z)), 2 * r, 'dot'))
    return cylinder(name, (x, y + 1.6 * MM, z), (x, y + 0.45 * MM, z), r, mat, 0.2 * MM, 2, n=20)


# --------------------------------------------------------------------------------------------
# The devices (top to bottom)
# --------------------------------------------------------------------------------------------
def firewall(M, z0):
    """1U fanless firewall: finned aluminium box between two rack ears, network ports in front."""
    xb = 84 * MM
    zb0, zb1, ztop = z0 + 5 * MM, z0 + 31 * MM, z0 + 40 * MM
    yf = YDEV - 6 * MM                      # the box stands proud of the ears
    pz = z0 + 18.5 * MM
    ports = [(-37 + 14.2 * i) * MM for i in range(4)]
    console = -62 * MM
    rj = [rj45(x, pz) for x in ports + [console]]
    usb = [rrect(34 * MM, pz + 0.6 * MM, 47.2 * MM, pz + 6.2 * MM, 0.6 * MM, 2),
           rrect(34 * MM, pz - 6.6 * MM, 47.2 * MM, pz - 1.0 * MM, 0.6 * MM, 2)]
    sheet('fw_front', rrect(-xb, zb0, xb, zb1, 1.5 * MM, 3),
          rj + usb + [circle(66 * MM, pz - 5 * MM, 0.7 * MM, 12), circle(66 * MM, pz + 4 * MM, LED_WELL, 16)],
          1.5 * MM, M.alu_fw, 'XZ', at=yf)
    # finned body with pockets for the jacks
    pts = [(-xb, zb0), (xb, zb0), (xb, zb1)]
    fin_w, pitch = 1.6 * MM, 4.4 * MM
    n = int((2 * xb - 1 * MM - fin_w) / pitch) + 1
    start = ((n - 1) * pitch + fin_w) / 2
    for i in range(n):
        xr = start - i * pitch
        pts += [(xr, zb1), (xr, ztop), (xr - fin_w, ztop), (xr - fin_w, zb1)]
    pts.append((-xb, zb1))
    body = sheet('fw_body', pts, [], 0.120, M.alu_fw, 'XZ', at=yf + 1.5 * MM, bevel=None)
    reg_rj = (console - 7.4 * MM, pz - 7.6 * MM, ports[-1] + 7.4 * MM, pz + 5.6 * MM)
    reg_usb = (33 * MM, pz - 7.6 * MM, 48.2 * MM, pz + 7.2 * MM)
    cut(body, [((reg_rj[0] - 0.1 * MM, yf, reg_rj[1] - 0.1 * MM), (reg_rj[2] + 0.1 * MM, yf + 16 * MM, reg_rj[3] + 0.1 * MM)),
               ((reg_usb[0] - 0.1 * MM, yf, reg_usb[1] - 0.1 * MM), (reg_usb[2] + 0.1 * MM, yf + 16 * MM, reg_usb[3] + 0.1 * MM)),
               ((64 * MM, yf, pz + 2 * MM), (68 * MM, yf + 4 * MM, pz + 6 * MM))])
    finish(body, 0.35 * MM, 2)
    jack_block(M, 'fw_jacks', reg_rj, rj, yf + 1.5 * MM)
    jack_block(M, 'fw_usb', reg_usb, usb, yf + 1.5 * MM, mat=M.zinc)
    for u in usb:
        zc = (u[0][1] + u[len(u) // 2][1]) / 2
        box('fw_usb_tongue', (35 * MM, yf + 2.5 * MM, zc - 0.2 * MM), (46.2 * MM, yf + 12 * MM, zc + 1.7 * MM), M.usb, 0.2 * MM, 1)
    led_dot('fw_led', 66 * MM, yf, pz + 4 * MM, M.led)
    for s in (-1, 1):
        ear(M, 'fw_ear', s, xb + 0.4 * MM, z0 + 0.4 * MM, z0 + U - 0.4 * MM, [z0 + 6.35 * MM, z0 + 38.1 * MM], M.alu_fw)
        box('fw_ear_side', (s * (xb + 0.4 * MM), YDEV, z0 + 3 * MM), (s * (xb + 2.4 * MM), YDEV + 0.05, z0 + U - 3 * MM), M.alu_fw, 0.4 * MM)
    return dict(port=lambda i: (ports[i], yf, pz))


def switch(M, z0):
    """1U network switch: eight RJ45, two SFP cages, tiny port lights, one status light."""
    p0, p1 = z0 + 0.4 * MM, z0 + U - 0.4 * MM
    xb = 108.3 * MM
    pz = z0 + 22.0 * MM
    ports = [(-99.5 + 13.9 * i) * MM for i in range(8)]
    sfps = [21 * MM, 36.8 * MM]
    rj = [rj45(x, pz) for x in ports]
    sf = [rrect(x - 6.9 * MM, pz - 4.9 * MM, x + 6.9 * MM, pz + 4.1 * MM, 0.5 * MM, 2) for x in sfps]
    sheet('sw_front', rrect(-xb, p0, xb, p1, 0.8 * MM, 2), rj + sf + [circle(58 * MM, pz, LED_WELL, 16)], 1.2 * MM, M.paint, 'XZ', at=YDEV)
    reg_rj = (ports[0] - 7.4 * MM, pz - 7.6 * MM, ports[-1] + 7.4 * MM, pz + 5.6 * MM)
    reg_sf = (sfps[0] - 7.7 * MM, pz - 5.7 * MM, sfps[1] + 7.7 * MM, pz + 4.9 * MM)
    body = new_mesh_object('sw_body', _box_verts((-xb, YDEV + 1.2 * MM, p0), (xb, YDEV + 0.135, p1)), _BOX_FACES, M.paint)
    cut(body, [((r[0] - 0.1 * MM, YDEV, r[1] - 0.1 * MM), (r[2] + 0.1 * MM, YDEV + 15.5 * MM, r[3] + 0.1 * MM)) for r in (reg_rj, reg_sf)]
        + [((56 * MM, YDEV, pz - 2 * MM), (60 * MM, YDEV + 4 * MM, pz + 2 * MM))])
    finish(body, 0.5 * MM, 2)
    jack_block(M, 'sw_jacks', reg_rj, rj, YDEV + 1.2 * MM)
    sf_in = [rrect(x - 6.5 * MM, pz - 4.5 * MM, x + 6.5 * MM, pz + 3.7 * MM, 0.3 * MM, 2) for x in sfps]
    jack_block(M, 'sw_sfp', reg_sf, sf_in, YDEV + 1.2 * MM, mat=M.zinc)
    # port lights: two light pipes above every port, a few of them lit
    lit = {0, 1, 2, 5}
    on, off = [], []
    for i, x in enumerate(ports):
        for k, dx in enumerate((-3.6 * MM, 3.6 * MM)):
            b = ((x + dx - 0.9 * MM, YDEV - 0.2 * MM, pz + 6.2 * MM), (x + dx + 0.9 * MM, YDEV + 0.4 * MM, pz + 7.3 * MM))
            (on if (i in lit and k == 0) else off).append(b)
    boxes('sw_port_led_on', on, M.led_port)
    for i in sorted(lit):
        LEDS.append((Vector((ports[i] - 3.6 * MM, YDEV, pz + 6.75 * MM)), 1.4 * MM, 'port'))
    boxes('sw_port_led_off', off, M.led_off)
    led_dot('sw_led', 58 * MM, YDEV, pz, M.led)
    for s in (-1, 1):
        ear(M, 'sw_ear', s, xb + 0.4 * MM, p0, p1, [z0 + 6.35 * MM, z0 + 38.1 * MM], M.paint)
    return dict(port=lambda i: (ports[i], YDEV, pz))


def server(M, z0, tag):
    """Compact server (mini PC, 196 x 189 x 48 mm) in its own rack bracket.

    The bracket carries the mini PC on a tray; on the left it has a small panel with a keystone
    jack that brings the network port to the front."""
    zc = z0 + SERVER_SLOT / 2
    sx0, sx1 = -87.5 * MM, 108.5 * MM
    sz0, sz1 = zc - 24 * MM, zc + 24 * MM
    yf = YDEV - 4 * MM
    fd = 7 * MM
    bx = sx0 + 30 * MM                      # power button
    usb_x = [bx + 22 * MM, bx + 40 * MM]
    holes = [circle(bx, zc, 5.9 * MM, 28)]
    usb = [rrect(x - 6.6 * MM, zc - 2.9 * MM, x + 6.6 * MM, zc + 2.9 * MM, 0.6 * MM, 2) for x in usb_x]
    usbc = [slot(bx + 56 * MM, zc, 8.6 * MM, 2.9 * MM)]
    vx0, vx1 = bx + 70 * MM, sx1 - 9 * MM
    vents = [circle(x, y, 1.15 * MM, 12) for x, y in hex_grid(vx0, zc - 4.6 * MM, vx1, zc + 4.6 * MM, 3.5 * MM)]
    sheet(tag + '_fascia', rrect(sx0, sz0, sx1, sz1, 2.6 * MM, 4), holes + usb + usbc + vents, fd, M.alu, 'XZ', at=yf,
          bevel=0.35 * MM, segs=2)
    box(tag + '_liner', (sx0 + 1 * MM, yf + fd - 0.6 * MM, sz0 + 1 * MM), (sx1 - 1 * MM, yf + fd + 0.2 * MM, sz1 - 1 * MM), M.liner, 0)
    box(tag + '_body', (sx0, yf + fd + 0.1 * MM, sz0), (sx1, yf + 0.189, sz1), M.alu, 2.6 * MM, 4)
    # USB shells and tongues
    for x in usb_x:
        sheet(tag + '_usb_shell', rrect(x - 6.6 * MM, zc - 2.9 * MM, x + 6.6 * MM, zc + 2.9 * MM, 0.6 * MM, 2),
              [rrect(x - 6.2 * MM, zc - 2.5 * MM, x + 6.2 * MM, zc + 2.5 * MM, 0.4 * MM, 2)], 5.5 * MM, M.zinc, 'XZ',
              at=yf + 0.5 * MM, bevel=0.0)
        box(tag + '_usb_tongue', (x - 5.6 * MM, yf + 1.2 * MM, zc - 0.1 * MM), (x + 5.6 * MM, yf + 6 * MM, zc + 1.9 * MM), M.usb, 0.2 * MM, 1)
    # power button with a thin light ring
    cylinder(tag + '_button', (bx, yf + 4 * MM, zc), (bx, yf + 0.25 * MM, zc), 4.95 * MM, M.alu, 0.5 * MM, 3)
    sheet(tag + '_ring', circle(bx, zc, 5.9 * MM, 28), [circle(bx, zc, 5.0 * MM, 28)], 0.4 * MM, M.led_ring, 'XZ', at=yf + 1.1 * MM, bevel=0.0)
    LEDS.append((Vector((bx, yf, zc)), 10.9 * MM, 'ring'))
    # bracket: left panel with keystone, ear tabs, tray
    zlo, zhi = z0 + 0.5 * MM, z0 + SERVER_SLOT - 0.5 * MM
    tlo, thi = zc - 17 * MM, zc + 17 * MM
    xa, xb_, xc = -XE, -XO + 0.3 * MM, sx0 - 0.7 * MM
    kx = (xb_ + xc) / 2
    outline = round_poly([(xa, tlo), (xb_, tlo), (xb_, zlo), (xc, zlo), (xc, zhi), (xb_, zhi), (xb_, thi), (xa, thi)], 1.8 * MM, 3)
    ks = rrect(kx - 7.3 * MM, zc - 8.2 * MM, kx + 7.3 * MM, zc + 8.2 * MM, 0.5 * MM, 2)
    sheet(tag + '_bracket', outline, [ks, slot(-XH, zc, 25 * MM, 6.6 * MM, vertical=True)], EAR_T, M.bracket, 'XZ', at=YDEV)
    sheet(tag + '_ear_r', rrect(XO - 0.3 * MM, tlo, XE, thi, 1.8 * MM, 3), [slot(XH, zc, 25 * MM, 6.6 * MM, vertical=True)],
          EAR_T, M.bracket, 'XZ', at=YDEV)
    box(tag + '_ear_r_side', (XO - 2.4 * MM, YDEV, tlo), (XO - 0.4 * MM, YDEV + 0.06, thi), M.bracket, 0.4 * MM)
    box(tag + '_tray', (-XO + 0.5 * MM, YDEV + 2.2 * MM, z0 + 0.4 * MM), (XO - 0.5 * MM, YDEV + 0.186, sz0 - 0.05 * MM), M.bracket, 0.3 * MM)
    for s in (-1, 1):
        for dz in (-7.94 * MM, 7.94 * MM):
            screw(M, s * XH, YDEV, zc + dz)
    # keystone jack
    kz = zc + 0.6 * MM
    jack_block(M, tag + '_keystone', (kx - 7.1 * MM, zc - 8.0 * MM, kx + 7.1 * MM, zc + 8.0 * MM), [rj45(kx, kz)], YDEV - 0.6 * MM, depth=12 * MM)
    return dict(port=(kx, YDEV - 0.6 * MM, kz))


def backup_unit(M, z0):
    """About 1.5U: a two-bay backup box standing on a 1U rack shelf."""
    # shelf: plate, low front lip, 1U ears
    lip = z0 + 13 * MM
    e1 = z0 + U - 0.4 * MM
    zb = z0 + 0.4 * MM
    xo = XO - 0.3 * MM
    outline = round_poly([(-XE, zb), (XE, zb), (XE, e1), (xo, e1), (xo, lip), (-xo, lip), (-xo, e1), (-XE, e1)], 1.5 * MM, 3)
    hz = [z0 + 6.35 * MM, z0 + 38.1 * MM]
    holes = [slot(s * XH, z, 10 * MM, 6.6 * MM) for s in (-1, 1) for z in hz]
    sheet('shelf_front', outline, holes, EAR_T, M.bracket, 'XZ', at=YDEV)
    box('shelf_plate', (-xo, YDEV + EAR_T, zb), (xo, YDEV + 0.185, zb + 1.5 * MM), M.bracket, 0.3 * MM)
    for s in (-1, 1):
        for z in hz:
            screw(M, s * XH, YDEV, z)
    # the box
    x0, x1 = -98 * MM, 98 * MM
    b0, b1 = zb + 1.6 * MM, zb + 1.6 * MM + 58 * MM
    yf = YDEV + 5 * MM
    box('bk_body', (x0, yf, b0), (x1, yf + 0.165, b1), M.backup, 3.0 * MM, 4)
    # two drive trays with perforated fronts
    tz0, tz1 = b0 + 6 * MM, b1 - 6 * MM
    for k, (tx0, tx1) in enumerate(((-72 * MM, 9 * MM), (13 * MM, 94 * MM))):
        vents = [circle(x, y, 1.1 * MM, 12) for x, y in hex_grid(tx0 + 6 * MM, tz0 + 13 * MM, tx1 - 6 * MM, tz1 - 5 * MM, 3.6 * MM)]
        sheet('bk_tray', rrect(tx0, tz0, tx1, tz1, 1.6 * MM, 3), vents, 1.6 * MM, M.backup, 'XZ', at=yf - 1.6 * MM)
        box('bk_tray_liner', (tx0 + 1 * MM, yf - 0.05 * MM, tz0 + 1 * MM), (tx1 - 1 * MM, yf + 0.3 * MM, tz1 - 1 * MM), M.liner, 0)
        box('bk_tray_latch', (tx0 + 6 * MM, yf - 2.6 * MM, tz0 + 3.2 * MM), (tx0 + 30 * MM, yf - 1.5 * MM, tz0 + 8.2 * MM), M.plastic, 0.5 * MM, 2)
    # control strip on the left: button and status light
    cx_ = -86 * MM
    sheet('bk_strip', rrect(cx_ - 6 * MM, tz0, cx_ + 6 * MM, tz1, 2.5 * MM, 3),
          [circle(cx_, b0 + 22 * MM, 3.9 * MM, 24), circle(cx_, b0 + 40 * MM, LED_WELL, 16)], 1.6 * MM, M.plastic, 'XZ', at=yf - 1.6 * MM)
    cylinder('bk_button', (cx_, yf + 1 * MM, b0 + 22 * MM), (cx_, yf - 1.3 * MM, b0 + 22 * MM), 3.6 * MM, M.plastic, 0.5 * MM, 2, n=32)
    led_dot('bk_led', cx_, yf - 1.6 * MM, b0 + 40 * MM, M.led)


def ups(M, z0):
    """2U UPS: faceplate with a vent grille, a small dark display, one button and one light."""
    f0, f1 = z0 + 0.4 * MM, z0 + 2 * U - 0.4 * MM
    hz = [z0 + 6.35 * MM, z0 + U + 38.1 * MM]
    holes = [slot(s * XH, z, 10 * MM, 6.6 * MM) for s in (-1, 1) for z in hz]
    for col in range(2):
        cx = (-74 + col * 60) * MM
        for r in range(13):
            holes.append(slot(cx, z0 + 14 * MM + r * 5.1 * MM, 52 * MM, 2.6 * MM))
    dx0, dx1, dz0, dz1 = 28 * MM, 76 * MM, z0 + 42 * MM, z0 + 70 * MM
    holes.append(rrect(dx0, dz0, dx1, dz1, 1.5 * MM, 3))
    bx, bz = 40 * MM, z0 + 23 * MM
    holes.append(circle(bx, bz, 5.0 * MM, 24))
    holes.append(circle(bx + 17 * MM, bz, LED_WELL, 16))
    sheet('ups_front', rrect(-XE, f0, XE, f1, 1.5 * MM, 3), holes, 2.5 * MM, M.paint, 'XZ', at=YDEV - 0.5 * MM)
    box('ups_body', (-108 * MM, YDEV + 9 * MM, f0 + 1 * MM), (108 * MM, YDEV + 0.215, f1 - 1 * MM), M.liner, 0.5 * MM)
    box('ups_skirt_t', (-108 * MM, YDEV + 2 * MM, f1 - 2.2 * MM), (108 * MM, YDEV + 9.2 * MM, f1 - 1 * MM), M.paint, 0.3 * MM)
    box('ups_skirt_b', (-108 * MM, YDEV + 2 * MM, f0 + 1 * MM), (108 * MM, YDEV + 9.2 * MM, f0 + 2.2 * MM), M.paint, 0.3 * MM)
    # display: a dark glossy window in a raised bezel
    box('ups_display', (dx0 - 1 * MM, YDEV + 0.9 * MM, dz0 - 1 * MM), (dx1 + 1 * MM, YDEV + 2.6 * MM, dz1 + 1 * MM), M.display, 0)
    sheet('ups_display_bezel', rrect(dx0 - 2.2 * MM, dz0 - 2.2 * MM, dx1 + 2.2 * MM, dz1 + 2.2 * MM, 2.2 * MM, 3),
          [rrect(dx0 + 0.3 * MM, dz0 + 0.3 * MM, dx1 - 0.3 * MM, dz1 - 0.3 * MM, 1.2 * MM, 3)], 1.0 * MM, M.plastic, 'XZ',
          at=YDEV - 1.3 * MM, bevel=0.35 * MM, segs=2)
    cylinder('ups_button', (bx, YDEV + 3 * MM, bz), (bx, YDEV - 0.9 * MM, bz), 4.6 * MM, M.plastic, 0.6 * MM, 3)
    led_dot('ups_led', bx + 17 * MM, YDEV - 0.5 * MM, bz, M.led)
    for s in (-1, 1):
        for z in hz:
            screw(M, s * XH, YDEV - 0.5 * MM, z)


# --------------------------------------------------------------------------------------------
# Patch cables
# --------------------------------------------------------------------------------------------
def plug(M, x, y, z):
    """RJ45 plug with a strain-relief boot, pushed into a jack whose face is at y. Returns the
    point where the cable leaves the boot."""
    box('plug', (x - 5.7 * MM, y - 7.5 * MM, z - 3.8 * MM), (x + 5.7 * MM, y + 6 * MM, z + 3.8 * MM), M.plug, 0.6 * MM, 2)
    box('plug_latch', (x - 2.2 * MM, y - 9 * MM, z - 5.6 * MM), (x + 2.2 * MM, y + 2 * MM, z - 3.9 * MM), M.plug, 0.4 * MM, 2)
    bm = bmesh.new()
    mtx = Matrix.Translation((x, y - 14 * MM, z)) @ Matrix.Rotation(math.pi / 2, 4, 'X') @ Matrix.Diagonal((1.12, 0.84, 1.0, 1.0))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=5.4 * MM, radius2=2.7 * MM, depth=13.5 * MM, matrix=mtx)
    me = bpy.data.meshes.new('boot')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M.cable)
    finish(link(bpy.data.objects.new('boot', me)), 0.7 * MM, 3)
    return Vector((x, y - 19 * MM, z))


def cable(M, name, a, b, ha, hb, sag=0.12, radius=2.0 * MM):
    """Patch cable between two front ports a and b (jack faces look to -y): one Bezier span that
    bows out towards the door and droops a little."""
    A, B = plug(M, *a), plug(M, *b)
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 48
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(1)
    p0, p1 = sp.bezier_points
    va = Vector((0, -ha, -sag * ha))
    vb = Vector((0, -hb, -sag * hb * 1.6))
    p0.handle_left_type = p0.handle_right_type = 'FREE'
    p1.handle_left_type = p1.handle_right_type = 'FREE'
    p0.co, p0.handle_right, p0.handle_left = A + Vector((0, 0.004, 0)), A + va, A - va
    p1.co, p1.handle_left, p1.handle_right = B + Vector((0, 0.004, 0)), B + vb, B - vb
    ob = bpy.data.objects.new(name, cu)
    cu.materials.append(M.cable)
    return link(ob)


def cables(M, sw, fw, servers):
    """Three patch cables from the switch to the servers and a short uplink to the firewall."""
    cable(M, 'patch1', sw['port'](0), servers[0]['port'], 0.036, 0.034)
    cable(M, 'patch2', sw['port'](1), servers[1]['port'], 0.044, 0.042)
    cable(M, 'patch3', sw['port'](2), servers[2]['port'], 0.052, 0.050)
    cable(M, 'uplink', fw['port'](1), sw['port'](5), 0.026, 0.028, sag=0.05)


def build_product(M):
    scene = bpy.context.scene
    cabinet(M)
    feet(M)
    door(M)
    housing = set(scene.objects)
    rails(M)
    fw = firewall(M, SLOTS['firewall'])
    sw = switch(M, SLOTS['switch'])
    srv = [server(M, SLOTS['server%d' % i], 'srv%d' % i) for i in (1, 2, 3)]
    backup_unit(M, SLOTS['backup'])
    ups(M, SLOTS['ups'])
    devices = set(scene.objects) - housing
    cables(M, sw, fw, srv)
    # collections for light linking: everything / only what is mounted in the rack (without the cables)
    lock = [ob for ob in scene.objects if ob.name.startswith('lock')]
    for name, obs in (('product', scene.objects), ('devices', devices), ('glass', [scene.objects['door_glass']]), ('lock', lock)):
        coll = bpy.data.collections.new(name)
        for ob in obs:
            coll.objects.link(ob)


# --------------------------------------------------------------------------------------------
# Studio
# --------------------------------------------------------------------------------------------
def floor(mood):
    """The table the cabinet stands on. It is never seen itself: in the beauty pass it only
    bounces light up onto the product, in the shadow pass it is the shadow catcher. It is hidden
    from glossy rays, so the glass and the metal reflect the studio and not the table."""
    ob = new_mesh_object('floor', [(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [(0, 1, 2, 3)])
    c = 0.16 if mood == 'light' else 0.012      # how much light the table bounces back
    m, N, b = _principled('floor', (c, c, c), 1.0)
    b.inputs['Specular IOR Level'].default_value = 0.0
    ob.data.materials.append(m)
    ob.visible_glossy = False
    ob.visible_camera = False
    bpy.data.collections.new('floor').objects.link(ob)     # for the shadow lamp
    return ob


def _emitter_nodes(N, surface_in, uv, strength, color, feather, grad=None, grad_base=0.0):
    """Emission with feathered edges (a softbox is brighter in the middle). grad=(du, dv) adds a
    fall-off across the card, from grad_base on the dim side to 1 on the bright side."""
    sep = N.new('ShaderNodeSeparateXYZ')
    N.link(uv, sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]

    def smooth(x, hi):
        n = N.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        n.inputs['From Min'].default_value = 0.0
        n.inputs['From Max'].default_value = max(hi, 1e-4)
        N.link(x, n.inputs[0])
        return n.outputs[0]

    def edge(x):
        return smooth(N.math('MINIMUM', x, N.math('SUBTRACT', 1.0, x)), feather)

    mask = N.math('MULTIPLY', edge(u), edge(v))
    if grad is not None:
        du, dv = grad
        t = N.math('ADD', N.math('MULTIPLY', u, du), N.math('MULTIPLY', v, dv))
        t = N.math('ADD', t, (0.0 if du >= 0 else -du) + (0.0 if dv >= 0 else -dv))
        ramp = N.math('ADD', N.math('MULTIPLY', smooth(t, abs(du) + abs(dv)), 1.0 - grad_base), grad_base)
        mask = N.math('MULTIPLY', mask, ramp)
    e = N.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*color, 1)
    N.link(N.math('MULTIPLY', mask, strength), e.inputs['Strength'])
    N.link(e.outputs[0], surface_in)


WARM = (1.0, 0.975, 0.945)                 # slightly warm and slightly cool white: two softboxes are never the same
COOL = (0.955, 0.98, 1.0)


def softbox(name, loc, target, size, strength, color=(1.0, 1.0, 1.0), feather=0.25, grad=None, lights='product'):
    """A softbox: a rectangular area lamp at loc that faces target, brighter in the middle and
    feathered towards its edges, so its reflections in glass and metal look like a real softbox.
    strength is the radiance of the bright middle (the same unit as an emission shader).
    lights='product': the lamp is linked to the product only. It neither lights the floor nor
    throws a shadow on it, so the shadow on the page is drawn by the one lamp meant to draw it.
    lights='devices': only what is mounted in the rack (a snooted light through the glass).
    lights='lock': only the door lock (a catchlight for the chrome).
    lights='floor': the lamp lights only the floor (the product still blocks it): the shadow lamp.
    lights='all': no light linking.
    (Lamps, not emissive meshes: the shadow catcher only understands lamps and the world.)"""
    w, h = size
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape, ld.size, ld.size_y = 'RECTANGLE', w, h
    ld.energy = w * h * math.pi          # radiance 1 where the node strength is 1
    try:
        ld.use_nodes = True
    except Exception:
        pass
    nt = ld.node_tree
    nt.nodes.clear()
    N = Nodes(nt)
    out = N.new('ShaderNodeOutputLight')
    _emitter_nodes(N, out.inputs['Surface'], N.new('ShaderNodeNewGeometry').outputs['Parametric'], strength, color, feather, grad)
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if lights in ('product', 'devices', 'floor', 'lock'):
        ob.light_linking.receiver_collection = bpy.data.collections[lights]
    if lights == 'floor':
        ob.visible_glossy = False
    return ob


def glass_sheen(name, cam_loc, rect, strength, color=(1.0, 1.0, 1.0), feather=0.1, grad=(1.0, 0.0), grad_base=0.35, dist=1.5):
    """The reflection of a softbox in the door glass, placed by where it should appear.

    rect = (cx, cz, w, h, angle): a rectangle on the pane as the camera sees it; centre in
    metres from the lower left corner of the glass, size, and its turn in degrees. The lamp is
    put where a real softbox would have to stand to be mirrored exactly there. It is linked to
    the glass alone, so it draws the reflection and lights nothing else.
    grad: the reflection gets brighter towards +x / +y of the rectangle, from grad_base to 1."""
    cx, cz, w, h, angle = rect
    cm = Vector((cam_loc.x, 2 * YGLASS - cam_loc.y, cam_loc.z))        # the camera, mirrored in the glass
    k = (cm.y - YGLASS + dist) / (cm.y - YGLASS)
    centre = cm + (Vector((-GX + cx, YGLASS, GZ0 + cz)) - cm) * k
    a = math.radians(angle)
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape, ld.size, ld.size_y = 'RECTANGLE', w * k, h * k
    ld.energy = w * k * h * k * math.pi
    try:
        ld.use_nodes = True
    except Exception:
        pass
    nt = ld.node_tree
    nt.nodes.clear()
    N = Nodes(nt)
    out = N.new('ShaderNodeOutputLight')
    _emitter_nodes(N, out.inputs['Surface'], N.new('ShaderNodeNewGeometry').outputs['Parametric'], strength, color, feather, grad, grad_base)
    ob = link(bpy.data.objects.new(name, ld))
    X, Y = Vector((math.cos(a), 0.0, math.sin(a))), Vector((-math.sin(a), 0.0, math.cos(a)))
    Z = X.cross(Y)                                                   # = -y: the lamp shines towards the door
    ob.matrix_world = Matrix.Translation(centre) @ Matrix((X, Y, Z)).transposed().to_4x4()
    ob.light_linking.receiver_collection = bpy.data.collections['glass']
    ob.visible_diffuse = False            # a reflection only: nothing behind the glass is lit by it
    ob.visible_transmission = False
    return ob


def world(zenith, horizon, nadir, strength=1.0):
    w = bpy.data.worlds.new('studio')
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    nt.nodes.clear()
    N = Nodes(nt)
    out = N.new('ShaderNodeOutputWorld')
    bg = N.new('ShaderNodeBackground')
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    N.link(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'EASE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (nadir, nadir, nadir, 1)
    e[1].position, e[1].color = 1.0, (zenith, zenith, zenith, 1)
    mid = e.new(0.5)
    mid.color = (horizon, horizon, horizon, 1)
    N.link(N.remap(sep.outputs[2], 0.0, 1.0, -1.0, 1.0), ramp.inputs[0])
    N.link(ramp.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    N.link(bg.outputs[0], out.inputs['Surface'])
    return w


def studio_lights(view, mood, cam_loc):
    """Lighting for the two moods and the two views. Positions are in metres around the cabinet,
    which stands at the origin with its door towards -y.

    Who lights what: the softboxes light the product and nothing else; 'interior' is a snooted
    light for the devices behind the glass; 'catch' is a catchlight for the lock; 'sheen' is
    the softbox mirrored in the glass; the 'shadow' lamp (with a little of the world) lights
    only the table and so draws the shadow on the page, see SHADOW_LAMP."""
    aim = (0.0, -0.10, 0.28)
    inside = (0.0, YDEV, 0.26)
    sheen = (0.349, 0.381, 0.40, 0.60, 30.0)       # its edge runs from the top of the pane (at 40 %) down to the right side
    softbox('shadow', SHADOW_LAMP, (0.0, 0.0, 0.0), (SHADOW_SIZE, SHADOW_SIZE), 490.0 * (0.6 / SHADOW_SIZE) ** 2, feather=0.1, lights='floor')
    if mood == 'light':
        world(0.30, 0.20, 0.03, 1.0)
        if view == 'studio':
            softbox('top', (0.0, -0.05, 1.5), (0.0, 0.0, 0.49), (1.1, 1.1), 11.0)
            softbox('key', (-1.0, -1.1, 1.25), aim, (0.9, 1.1), 21.0, WARM)
            softbox('fill', (1.25, -0.85, 0.75), (0.15, 0.0, 0.27), (1.0, 1.2), 4.2, COOL)
            softbox('front', (-0.75, -1.9, 0.55), inside, (0.9, 0.7), 4.0)
            softbox('interior', (0.25, -1.7, 1.0), inside, (0.9, 0.9), 14.0, lights='devices')
        else:
            softbox('top', (0.0, -0.75, 1.55), (0.0, -0.165, 0.35), (1.2, 0.9), 12.0)
            softbox('key', (-1.15, -1.25, 0.95), aim, (0.9, 1.2), 15.0, WARM)
            softbox('fill', (1.2, -1.3, 0.6), aim, (0.9, 1.1), 4.0, COOL)
            softbox('interior', (0.0, -1.7, 1.05), inside, (1.0, 0.8), 15.0, lights='devices')
        glass_sheen('sheen', cam_loc, sheen, 9.0, feather=0.06)
        catch = 1.1
    else:
        world(0.003, 0.003, 0.003, 1.0)
        if view == 'studio':
            softbox('key', (-0.75, -0.75, 1.15), (-0.15, -0.165, 0.45), (0.6, 0.6), 9.5, WARM)
            softbox('rim_right', (0.38, 0.85, 0.4), (0.15, 0.05, 0.27), (0.25, 1.2), 16.0, COOL)
            softbox('rim_left', (-1.2, 0.9, 0.6), (-0.15, -0.16, 0.26), (0.3, 1.5), 14.0, COOL)
            softbox('top_back', (0.0, 0.8, 1.5), (0.0, 0.0, 0.49), (1.2, 0.5), 5.5)
            softbox('interior', (0.25, -1.7, 1.0), inside, (0.9, 0.9), 18.0, lights='devices')
        else:
            softbox('side_left', (-0.6, -0.28, 0.7), (-0.15, -0.165, 0.35), (0.2, 0.8), 17.5, WARM)      # grazing: steep fall-off
            softbox('side_right', (0.6, -0.28, 0.5), (0.15, -0.165, 0.25), (0.2, 0.8), 5.0, COOL)
            softbox('top', (0.0, -0.4, 1.1), (0.0, -0.165, 0.49), (0.9, 0.25), 4.0)
            softbox('interior', (0.0, -1.7, 1.05), inside, (1.0, 0.8), 19.0, lights='devices')
        glass_sheen('sheen', cam_loc, sheen, 4.5, feather=0.06)
        catch = 0.35
    # catchlight for the lock: it stands where the chrome face mirrors the camera
    lock = Vector((W / 2 - STILE / 2, YF, Z0 + H / 2))
    d = lock - cam_loc
    softbox('catch', lock + Vector((d.x, -d.y, d.z)).normalized() * 1.2, lock, (0.45, 0.45), catch, feather=0.45, lights='lock')


def camera(view):
    """A level camera with lens shift (verticals stay vertical), 85 mm on a 36 mm frame, f/8,
    focused on the door. The framing is solved from the cabinet's bounding box."""
    scene = bpy.context.scene
    cd = bpy.data.cameras.new('camera')
    cam = link(bpy.data.objects.new('camera', cd))
    scene.camera = cam
    cd.lens = 85.0
    cd.sensor_width = 36.0
    cd.sensor_fit = 'AUTO'
    cd.clip_start, cd.clip_end = 0.1, 50.0
    if view == 'studio':
        az, height, pitch = math.radians(33.0), 0.60, math.radians(3.0)
        margins = dict(left=0.085, right=0.085, top=0.085, bottom=0.115)
    else:
        az, height, pitch = 0.0, 0.27, 0.0
        margins = dict(left=0.1, right=0.1, top=0.085, bottom=0.105)
    target = Vector((0.0, 0.0, 0.25))
    direction = Vector((-math.sin(az), math.cos(az), -math.tan(pitch)))
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    pts = [Vector((x, y, z)) for x in (-W / 2 - 0.004, W / 2) for y in (YF - 0.003, YB) for z in (0.0, ZT + SHEET)]
    from bpy_extras.object_utils import world_to_camera_view
    aspect = scene.render.resolution_x / scene.render.resolution_y
    d = 1.7
    for _ in range(12):
        cam.location = (target.x + d * math.sin(az), target.y - d * math.cos(az), height)
        bpy.context.view_layer.update()
        v = [world_to_camera_view(scene, cam, p) for p in pts]
        x0, x1 = min(p.x for p in v), max(p.x for p in v)
        y0, y1 = min(p.y for p in v), max(p.y for p in v)
        s = max((x1 - x0) / (1 - margins['left'] - margins['right']), (y1 - y0) / (1 - margins['top'] - margins['bottom']))
        d *= s
        tx = (margins['left'] + (1 - margins['right'])) / 2
        ty = (margins['bottom'] + (1 - margins['top'])) / 2
        cd.shift_x += ((x0 + x1) / 2 - tx) * (aspect if aspect < 1 else 1.0)
        cd.shift_y += ((y0 + y1) / 2 - ty) * (1.0 if aspect < 1 else 1.0 / aspect)
    bpy.context.view_layer.update()
    focus = Vector((0.03 if view == 'studio' else 0.0, YF, 0.25))
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 8.0
    cd.dof.focus_distance = (focus - cam.location).dot(direction.normalized())
    cd.dof.aperture_blades = 9
    return cam


# --------------------------------------------------------------------------------------------
# Render and finish
# --------------------------------------------------------------------------------------------
def setup_render(samples, scale, threads):
    scene = bpy.context.scene
    r = scene.render
    r.engine = 'CYCLES'
    r.resolution_x, r.resolution_y = 1600, 2000
    r.resolution_percentage = int(round(100 * scale))
    r.film_transparent = True
    r.threads_mode = 'FIXED'
    r.threads = max(1, min(3, threads))
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.color_depth = '8'
    r.image_settings.compression = 30
    r.dither_intensity = 1.0
    c = scene.cycles
    c.device = 'CPU'
    c.samples = samples
    c.use_adaptive_sampling = False
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    try:
        c.denoising_prefilter = 'ACCURATE'
    except Exception:
        pass
    c.max_bounces = 8
    c.diffuse_bounces = 3
    c.glossy_bounces = 4
    c.transmission_bounces = 8
    c.transparent_max_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 20.0
    c.blur_glossy = 0.4
    c.pixel_filter_type = 'BLACKMAN_HARRIS'
    c.filter_width = 1.5
    vs = scene.view_settings
    vs.view_transform = 'AgX'
    vs.look = 'AgX - Medium High Contrast'
    vs.exposure = 0.0
    vs.gamma = 1.0
    scene.display_settings.display_device = 'sRGB'
    return scene


def render_to(path, region=None):
    scene = bpy.context.scene
    r = scene.render
    if region:
        r.use_border, r.use_crop_to_border = True, True
        r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = region
    r.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t0


def render_beauty(path, region=None):
    """Pass 1, the product alone: the table bounces light but the camera does not see it, so the
    alpha channel is exactly the product."""
    fl = bpy.data.objects['floor']
    fl.is_shadow_catcher, fl.visible_camera = False, False
    return render_to(path, region)


def render_shadow(path, samples):
    """Pass 2, the shadow alone: the product is hidden from the camera but still blocks the
    light, the table is a shadow catcher. The alpha channel of this pass is the shadow.
    A soft shadow needs no detail: it is rendered at half size and scaled up in the finish."""
    scene = bpy.context.scene
    c = scene.cycles
    keep = (c.samples, c.max_bounces, scene.render.resolution_percentage)
    scene.render.resolution_percentage = max(1, keep[2] // 2)
    fl = bpy.data.objects['floor']
    product = list(bpy.data.collections['product'].objects)
    glass = bpy.data.objects['door_glass']
    for ob in product:
        ob.visible_camera = False
    glass.visible_shadow = False                 # the pane throws no shadow worth its render time
    fl.is_shadow_catcher, fl.visible_camera = True, True
    c.samples, c.max_bounces = samples, 0
    secs = render_to(path)
    for ob in product:
        ob.visible_camera = True
    glass.visible_shadow = True
    fl.is_shadow_catcher, fl.visible_camera = False, False
    c.samples, c.max_bounces, scene.render.resolution_percentage = keep
    return secs


def led_pixels(scene, cam):
    """Image position (x, y from the top left), size in pixels and kind of every status light."""
    from bpy_extras.object_utils import world_to_camera_view
    r = scene.render
    w, h = r.resolution_x * r.resolution_percentage / 100.0, r.resolution_y * r.resolution_percentage / 100.0
    out = []
    for pos, size, kind in LEDS:
        v = world_to_camera_view(scene, cam, pos)
        v2 = world_to_camera_view(scene, cam, pos + Vector((0, 0, 0.01)))
        out.append((v.x * w, (1.0 - v.y) * h, size * abs(v2.y - v.y) * h / 0.01, kind))
    return out


def lens_glare(pre, leds, strength):
    """A faint halo around every visible status light, as a lens (and the door glass) would add.
    pre = premultiplied display RGB. A light that is hidden in the render gets no halo."""
    h, w = pre.shape[:2]
    k = h / 2000.0
    s1, s2, s3 = 3.5 * k, 10.0 * k, 28.0 * k
    acc = np.zeros((h, w))
    for x, y, size, kind in leds:
        R = 0.5 * size if kind == 'ring' else 0.0
        weight = {'dot': 1.0, 'port': 0.45, 'ring': 0.5}[kind]
        rad = int(4 * s3 + R) + 2
        x0, x1, y0, y1 = max(0, int(x) - rad), min(w, int(x) + rad + 1), max(0, int(y) - rad), min(h, int(y) + rad + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        c = int(max(2, 0.5 * size + 1))
        win = pre[max(0, int(y) - c):int(y) + c + 1, max(0, int(x) - c):int(x) + c + 1]
        if win.size == 0:
            continue
        seen = float(np.clip((win[..., 1] - win[..., 0]).max() / 0.3, 0.0, 1.0))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.abs(np.hypot(xx - x, yy - y) - R)
        acc[y0:y1, x0:x1] += weight * seen * (0.50 * np.exp(-d * d / (2 * s1 * s1)) + 0.22 * np.exp(-d * d / (2 * s2 * s2))
                                              + 0.07 * np.exp(-d * d / (2 * s3 * s3)))
    halo = np.clip(acc * strength, 0.0, 1.0)[..., None] * np.array([0.30, 1.0, 0.48])
    return 1.0 - (1.0 - pre) * (1.0 - halo)


def finish_image(beauty_png, shadow_png, out_png, page, jpg, leds=(), glare=0.0, levels=SHADOW_LEVELS, fade=0.05, grain=0.004):
    """Put the two passes together like a retoucher would:
    (1) a faint lens glare around the status lights,
    (2) the shadow pass goes under the product, in the alpha channel only, after a levels
        correction (and a safety fade at the very edge of the frame, which should have nothing to do),
    (3) a little grain on the product, (4) the flattened preview on the page colour.
    Returns the largest shadow alpha on the frame edge and 4 % inside it (both should be 0)."""
    from PIL import Image
    b = np.asarray(Image.open(beauty_png).convert('RGBA')).astype(np.float64) / 255.0
    ap = b[..., 3]                                   # the product
    pre = b[..., :3] * ap[..., None]
    h, w = ap.shape
    sh = np.asarray(Image.open(shadow_png).convert('RGBA').resize((w, h), Image.BICUBIC)).astype(np.float64)[..., 3] / 255.0
    yy, xx = np.mgrid[0:h, 0:w]
    if glare > 0 and leds:
        pre = np.where(ap[..., None] > 0.5, lens_glare(pre, leds, glare), pre)
    sh = np.clip((sh - levels['floor']) / (1.0 - levels['floor']), 0.0, 1.0) ** levels['gamma']
    sh = np.clip(sh * levels['gain'], 0.0, 1.0)
    d = int(0.04 * min(w, h))
    inside = float(max(sh[d, :].max(), sh[h - 1 - d, :].max(), sh[:, d].max(), sh[:, w - 1 - d].max()))
    dist = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / float(min(w, h))
    t = np.clip(dist / fade, 0.0, 1.0)
    sh *= t * t * (3 - 2 * t)
    a = ap + (1.0 - ap) * sh
    rgb = np.clip(pre / np.maximum(a, 1e-4)[..., None], 0.0, 1.0)
    if grain > 0:                             # a little sensor grain on the product, none on the page
        rgb = np.clip(rgb + np.random.default_rng(5).normal(0.0, grain, (h, w, 1)) * (ap[..., None] > 0.5), 0.0, 1.0)
    out = np.dstack([rgb, a])
    Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), 'RGBA').save(out_png, optimize=True)
    pg = np.array(page, dtype=np.float64) / 255.0
    flat = rgb * a[..., None] + pg * (1.0 - a[..., None])
    Image.fromarray((flat * 255.0 + 0.5).astype(np.uint8), 'RGB').save(jpg, quality=93)
    return float(max(a[0].max(), a[-1].max(), a[:, 0].max(), a[:, -1].max())), inside


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shot', required=True, choices=sorted(SHOTS))
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--scale', type=float, default=0.5, help='1.0 = 1600 x 2000 px')
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=3, help='render threads (capped at 3)')
    ap.add_argument('--region', default=None, help='x0,y0,x1,y1 as fractions of the frame: render only this crop (no shadow finish)')
    ap.add_argument('--page', default=None, help="page colour for the flattened JPEG, e.g. '#eceef0' (default: the colour of the mood)")
    ap.add_argument('--reuse-beauty', action='store_true', help='keep the beauty pass in passes/ if it exists; only redo the shadow and the finish')
    ap.add_argument('--blend', default=None, help='also save the scene as a .blend file')
    args = ap.parse_args()

    shot = dict(SHOTS[args.shot])
    if args.page:
        shot['page'] = tuple(int(args.page.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_render(args.samples, args.scale, args.threads)
    M = make_materials(shot['mood'])
    build_product(M)
    floor(shot['mood'])
    cam = camera(shot['view'])
    studio_lights(shot['view'], shot['mood'], cam.location.copy())
    t_build = time.time() - t0
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if args.region:
        secs = render_beauty(out, tuple(float(v) for v in args.region.split(',')))
        print('BUILD_SECONDS %.1f  RENDER_SECONDS %.1f  (crop of the beauty pass)' % (t_build, secs))
        return
    passes = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'passes')
    os.makedirs(passes, exist_ok=True)
    stem = os.path.splitext(os.path.basename(out))[0]
    beauty, shadow = os.path.join(passes, stem + '-beauty.png'), os.path.join(passes, stem + '-shadow.png')
    t_beauty = 0.0
    if not (args.reuse_beauty and os.path.exists(beauty)):
        t_beauty = render_beauty(beauty)
    t_shadow = render_shadow(shadow, max(32, args.samples // 3))
    edge, inside = finish_image(beauty, shadow, out, shot['page'], out[:-4] + '-on-page.jpg', leds=led_pixels(bpy.context.scene, cam),
                                glare=0.10 if shot['mood'] == 'light' else 0.45)
    print('BUILD_SECONDS %.1f  BEAUTY_SECONDS %.1f  SHADOW_SECONDS %.1f  TOTAL_SECONDS %.1f' % (t_build, t_beauty, t_shadow, time.time() - t0))
    print('SHADOW_ALPHA on the frame edge %.3f, 4 %% inside the frame %.3f' % (edge, inside))


if __name__ == '__main__':
    main()
