"""Zoom from a CPU on a motherboard down to a single FinFET transistor.
World units: the hero transistor sits at the origin; one unit ~ 1 fin pitch-ish.
Run: ~/.bpy-venv/bin/python build.py <project_dir>  ->  writes <project_dir>/scene.blend
Example scene for the ipad_code skill (24 fps, 240 frames, 1080x1920, Cycles CPU).
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, Matrix

HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
os.makedirs(HERE, exist_ok=True)
FPS, FRAMES = 24, 240
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------------------------------------------------------- helpers
def mat(name, color, metallic=0.0, rough=0.4, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        p.inputs[k].default_value = v
    return m

def box(bm, x0, x1, y0, y1, z0, z1):
    vs = [bm.verts.new((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])

def diamond_x(bm, x0, x1, yc, hw, zb, zt):
    """Prism along X with a diamond cross-section (SiGe epi look)."""
    zc = (zb + zt) / 2
    prof = [(yc, zb), (yc + hw, zc), (yc, zt), (yc - hw, zc)]
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((a[i], a[j], b[j], b[i]))

def obj_from(bm, name, material, smooth=False, bevel=0.0):
    me = bpy.data.meshes.new(name)
    bm.normal_update(); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    me.materials.append(material)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel; mod.segments = 2; mod.limit_method = "ANGLE"
        mod.harden_normals = False
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return ob

def hole(z):  # radius of the cut-away canyon around the hero transistor
    return 2.6 + 0.75 * z

# ---------------------------------------------------------------- materials
copper  = mat("copper", (0.955, 0.56, 0.42), 1.0, 0.22)
tungst  = mat("tungsten", (0.55, 0.56, 0.6), 1.0, 0.3)
silicon = mat("silicon", (0.32, 0.36, 0.44), 0.55, 0.28)
gate_m  = mat("gate_TiN", (0.85, 0.66, 0.30), 1.0, 0.25)
epi_m   = mat("epi", (0.42, 0.40, 0.52), 0.4, 0.35)
oxide   = mat("oxide", (0.02, 0.035, 0.09), 0.0, 0.12, **{"Coat Weight": 0.6})
hero_g  = mat("hero_gate", (0.85, 0.66, 0.30), 1.0, 0.22,
              **{"Emission Color": (0.15, 0.75, 1.0, 1)})
hero_f  = mat("hero_fin", (0.32, 0.36, 0.44), 0.55, 0.28,
              **{"Emission Color": (0.2, 0.6, 1.0, 1)})
elec_m  = mat("electron", (0.1, 0.5, 1.0), 0.0, 0.5,
              **{"Emission Color": (0.25, 0.65, 1.0, 1), "Emission Strength": 40.0})
die_side= mat("die_side", (0.12, 0.13, 0.16), 1.0, 0.15)
substr  = mat("substrate", (0.03, 0.09, 0.06), 0.0, 0.35, **{"Coat Weight": 0.5})
cap_m   = mat("cap_body", (0.45, 0.33, 0.2), 0.0, 0.5)
cap_end = mat("cap_end", (0.85, 0.85, 0.82), 1.0, 0.25)
socket  = mat("socket", (0.025, 0.025, 0.03), 0.0, 0.55)
cap_alu = mat("cap_alu", (0.6, 0.62, 0.66), 1.0, 0.55)
choke   = mat("choke", (0.08, 0.08, 0.09), 0.3, 0.45)

# ---- die top: multi-scale procedural "die shot" with thin-film iridescence + fade
def die_top_material():
    m = bpy.data.materials.new("die_top"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    p = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    prev_col = None; mortar_acc = None
    palette = [(0.06, 0.07, 0.12), (0.30, 0.18, 0.40), (0.12, 0.22, 0.38),
               (0.55, 0.36, 0.18), (0.08, 0.30, 0.30)]
    scales = [1 / 260, 1 / 60, 1 / 14, 1 / 3.2, 1 / 0.8]
    for i, sc in enumerate(scales):
        br = N.new("ShaderNodeTexBrick")
        br.offset = 0.0 if i % 2 else 0.5
        br.inputs["Scale"].default_value = sc
        br.inputs["Mortar Size"].default_value = 0.035 if i < 2 else 0.06
        br.inputs["Brick Width"].default_value = 1.0 + 0.3 * i % 1
        br.inputs["Row Height"].default_value = 0.6 + 0.15 * (i % 3)
        br.inputs["Color1"].default_value = (0, 0, 0, 1)
        br.inputs["Color2"].default_value = (1, 1, 1, 1)
        br.inputs["Mortar"].default_value = (0, 0, 0, 1)
        L.new(tc.outputs["Object"], br.inputs["Vector"])
        ramp = N.new("ShaderNodeValToRGB")
        cr = ramp.color_ramp; cr.interpolation = "CONSTANT"
        cols = palette[i:] + palette[:i]
        while len(cr.elements) < len(cols): cr.elements.new(0)
        for k, c in enumerate(cols):
            cr.elements[k].position = k / len(cols); cr.elements[k].color = (*c, 1)
        L.new(br.outputs["Color"], ramp.inputs["Fac"])
        if prev_col is None:
            prev_col = ramp.outputs["Color"]
        else:
            mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "OVERLAY"
            mix.inputs["Factor"].default_value = 0.55
            L.new(prev_col, mix.inputs["A"]); L.new(ramp.outputs["Color"], mix.inputs["B"])
            prev_col = mix.outputs["Result"]
        if mortar_acc is None:
            mortar_acc = br.outputs["Fac"]
        else:
            mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
            L.new(mortar_acc, mx.inputs[0]); L.new(br.outputs["Fac"], mx.inputs[1])
            mortar_acc = mx.outputs[0]
    # mortar lines = metal traces (gold/copper), blocks = coloured silicon
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    L.new(mortar_acc, mix.inputs["Factor"])
    L.new(prev_col, mix.inputs["A"])
    mix.inputs["B"].default_value = (0.95, 0.68, 0.38, 1)
    L.new(mix.outputs["Result"], p.inputs["Base Color"])
    met = N.new("ShaderNodeMapRange")
    met.inputs["To Min"].default_value = 0.65; met.inputs["To Max"].default_value = 1.0
    L.new(mortar_acc, met.inputs["Value"]); L.new(met.outputs["Result"], p.inputs["Metallic"])
    rgh = N.new("ShaderNodeMapRange")
    rgh.inputs["To Min"].default_value = 0.18; rgh.inputs["To Max"].default_value = 0.3
    L.new(mortar_acc, rgh.inputs["Value"]); L.new(rgh.outputs["Result"], p.inputs["Roughness"])
    p.inputs["Thin Film Thickness"].default_value = 520.0
    p.inputs["Thin Film IOR"].default_value = 1.46
    p.inputs["Alpha"].default_value = 1.0
    return m

die_top_m = die_top_material()

# ---- motherboard: solder mask with copper traces
def pcb_material():
    m = bpy.data.materials.new("pcb"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    p = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    wave = N.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 0.0009; wave.inputs["Distortion"].default_value = 0.0
    br = N.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1 / 1800; br.inputs["Mortar Size"].default_value = 0.02
    L.new(tc.outputs["Object"], wave.inputs["Vector"]); L.new(tc.outputs["Object"], br.inputs["Vector"])
    thr = N.new("ShaderNodeMath"); thr.operation = "GREATER_THAN"; thr.inputs[1].default_value = 0.93
    L.new(wave.outputs["Fac"], thr.inputs[0])
    mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    L.new(thr.outputs[0], mx.inputs[0]); L.new(br.outputs["Fac"], mx.inputs[1])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.012, 0.035, 0.022, 1)
    mix.inputs["B"].default_value = (0.05, 0.16, 0.07, 1)
    L.new(mx.outputs[0], mix.inputs["Factor"])
    L.new(mix.outputs["Result"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.3
    p.inputs["Coat Weight"].default_value = 0.7
    return m

pcb_m = pcb_material()

# gold pads on substrate (brick mask)
def substrate_top_material():
    m = bpy.data.materials.new("substrate_top"); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; p = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    br = N.new("ShaderNodeTexBrick"); br.offset = 0.0
    br.inputs["Scale"].default_value = 1 / 70; br.inputs["Mortar Size"].default_value = 0.45
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    L.new(tc.outputs["Object"], br.inputs["Vector"])
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
    L.new(br.outputs["Fac"], inv.inputs[1])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.02, 0.07, 0.05, 1)
    mix.inputs["B"].default_value = (1.0, 0.72, 0.32, 1)
    L.new(inv.outputs[0], mix.inputs["Factor"]); L.new(mix.outputs["Result"], p.inputs["Base Color"])
    L.new(inv.outputs[0], p.inputs["Metallic"])
    p.inputs["Roughness"].default_value = 0.28
    return m

subtop_m = substrate_top_material()

# ---------------------------------------------------------------- geometry
# Transistor level -----------------------------------------------------
RT = 30.0
FIN_P, FIN_W, FIN_H = 0.3, 0.07, 0.35
GATE_P, GATE_L, GATE_H = 0.6, 0.14, 0.65

# oxide floor
bm = bmesh.new(); box(bm, -700, 700, -700, 700, -0.6, 0.0); obj_from(bm, "oxide_floor", oxide)

bm_fin = bmesh.new(); bm_gate = bmesh.new(); bm_epi = bmesh.new(); bm_ct = bmesh.new()
nf = int(RT / FIN_P); ng = int(RT / GATE_P)
for k in range(-nf, nf + 1):
    y = k * FIN_P
    # cut fins into segments of random gate counts (hero fin continuous)
    x = -RT
    while x < RT:
        seg = random.randint(4, 12) * GATE_P
        x1 = min(RT, x + seg)
        if k == 0 and x < 0 < x1 + 3:
            pass
        if k != 0 or not (x - 0.01 < 0 < x1):
            box(bm_fin, x + 0.05, x1 - 0.05, y - FIN_W / 2, y + FIN_W / 2, -0.3, FIN_H)
        else:
            # hero fin segment: split off the hero part (separate material)
            box(bm_fin, x + 0.05, -1.5, y - FIN_W / 2, y + FIN_W / 2, -0.3, FIN_H)
            box(bm_fin, 1.5, x1 - 0.05, y - FIN_W / 2, y + FIN_W / 2, -0.3, FIN_H)
        x = x1
for j in range(-ng, ng + 1):
    x = j * GATE_P
    y = -RT
    while y < RT:
        seg = random.randint(6, 20) * FIN_P
        y1 = min(RT, y + seg)
        if j == 0 and y < 0 < y1:
            box(bm_gate, x - GATE_L / 2, x + GATE_L / 2, y + 0.04, -0.2, 0.0, GATE_H)
            box(bm_gate, x - GATE_L / 2, x + GATE_L / 2, 0.2, y1 - 0.04, 0.0, GATE_H)
        else:
            box(bm_gate, x - GATE_L / 2, x + GATE_L / 2, y + 0.04, y1 - 0.04, 0.0, GATE_H)
        y = y1
# epi + contacts between gates on fins
for k in range(-nf, nf + 1):
    y = k * FIN_P
    for j in range(-ng, ng):
        xc = (j + 0.5) * GATE_P
        if k == 0 and abs(xc) < 0.5:
            continue  # hero S/D made separately
        diamond_x(bm_epi, xc - 0.17, xc + 0.17, y, 0.085, 0.14, 0.46)
        r = math.hypot(xc, y)
        if r > 3.2 and random.random() < 0.35:
            box(bm_ct, xc - 0.06, xc + 0.06, y - 0.06, y + 0.06, 0.4, 1.0)
obj_from(bm_fin, "fins", silicon)
obj_from(bm_gate, "gates", gate_m)
obj_from(bm_epi, "epi", epi_m)
obj_from(bm_ct, "contacts", tungst)

# hero transistor: fin, gate, source & drain
bm = bmesh.new(); box(bm, -1.5, 1.5, -FIN_W / 2, FIN_W / 2, -0.3, FIN_H); hero_fin = obj_from(bm, "hero_fin", hero_f)
bm = bmesh.new(); box(bm, -GATE_L / 2, GATE_L / 2, -0.2, 0.2, 0.0, GATE_H); hero_gate = obj_from(bm, "hero_gate", hero_g)
bm = bmesh.new()
for xc in (-0.3, 0.3):
    diamond_x(bm, xc - 0.17, xc + 0.17, 0.0, 0.085, 0.14, 0.46)
obj_from(bm, "hero_sd", epi_m)

# Interconnect stack ----------------------------------------------------
LAYERS = [  # z0, thickness, pitch, width, direction
    (1.00, 0.35, 0.6, 0.28, "Y"),
    (1.80, 0.45, 0.8, 0.38, "X"),
    (2.80, 0.60, 1.2, 0.55, "Y"),
    (4.30, 0.90, 2.0, 0.90, "X"),
    (6.50, 1.40, 3.2, 1.40, "Y"),
    (9.80, 2.20, 5.0, 2.20, "X"),
    (14.5, 3.00, 8.0, 3.40, "Y"),
]
RW = 75.0
bm_cu = bmesh.new(); bm_via = bmesh.new()

def wire(bm, axis, c, w, z0, t, a0, a1):
    if a1 - a0 < 0.05: return
    if axis == "X": box(bm, a0, a1, c - w / 2, c + w / 2, z0, z0 + t)
    else:           box(bm, c - w / 2, c + w / 2, a0, a1, z0, z0 + t)

for z0, t, pitch, w, ax in LAYERS:
    hr = hole(z0)
    n = int(RW / pitch)
    for i in range(-n, n):
        c = (i + 0.5) * pitch
        a = -RW
        while a < RW:   # broken lines like real routing
            seg = random.uniform(4, 14) * pitch
            a1 = min(RW, a + seg)
            gap = random.uniform(0.3, 1.2) * pitch
            # cut the canyon
            if abs(c) < hr:
                h = math.sqrt(hr * hr - c * c)
                wire(bm_cu, ax, c, w, z0, t, a, min(a1, -h))
                wire(bm_cu, ax, c, w, z0, t, max(a, h), a1)
            else:
                wire(bm_cu, ax, c, w, z0, t, a, a1)
            a = a1 + gap
# vias between consecutive layers at random crossings
for (za, ta, pa, wa, axa), (zb, tb, pb, wb, axb) in zip(LAYERS, LAYERS[1:]):
    s = min(wa, wb) * 0.7
    n = int(RW / max(pa, pb))
    cnt = int((2 * RW / pa) * (2 * RW / pb) * 0.04)
    for _ in range(cnt):
        u = (random.randint(-int(RW / pa), int(RW / pa) - 1) + 0.5) * pa
        v = (random.randint(-int(RW / pb), int(RW / pb) - 1) + 0.5) * pb
        x, y = (v, u) if axa == "Y" else (u, v)
        if math.hypot(x, y) < hole(zb) + 1: continue
        box(bm_via, x - s / 2, x + s / 2, y - s / 2, y + s / 2, za + ta, zb)
obj_from(bm_cu, "copper", copper, bevel=0.02)
obj_from(bm_via, "vias", tungst)

# Die + package + board ------------------------------------------------
DIE = 700.0
bm = bmesh.new()
for x0, x1, y0, y1 in ((-DIE, DIE, -DIE - 8, -DIE), (-DIE, DIE, DIE, DIE + 8),
                       (-DIE - 8, -DIE, -DIE, DIE), (DIE, DIE + 8, -DIE, DIE)):
    box(bm, x0, x1, y0, y1, -20, 20)
obj_from(bm, "die_sides", die_side)
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=DIE + 8)
for v in bm.verts: v.co.z = 20.0
die_top = obj_from(bm, "die_top", die_top_m)

bm = bmesh.new(); box(bm, -1800, 1800, -1800, 1800, -60, -20.5); obj_from(bm, "substrate", substr)
bm = bmesh.new(); box(bm, -1780, 1780, -1780, 1780, -20.5, -20); obj_from(bm, "substrate_top", subtop_m)
# SMD capacitors on the substrate around the die
bm_c = bmesh.new(); bm_e = bmesh.new()
for side in range(4):
    for i in range(14):
        a = -1000 + i * 150
        b = DIE + 260 + (i % 2) * 120
        x, y = [(a, b), (a, -b), (b, a), (-b, a)][side]
        L_, W_ = (60, 30) if side < 2 else (30, 60)
        box(bm_c, x - L_ / 2 * 0.6, x + L_ / 2 * 0.6, y - W_ / 2 * 0.6 if side < 2 else y - W_ / 2, y + W_ / 2 * 0.6 if side < 2 else y + W_ / 2, -20, 6)
        if side < 2:
            for s in (-1, 1): box(bm_e, x + s * L_ / 2 * 0.6 - (s > 0) * 12, x + s * L_ / 2 * 0.6 + (s < 0) * 12, y - W_ / 2 * 0.65, y + W_ / 2 * 0.65, -20, 7)
        else:
            for s in (-1, 1): box(bm_e, x - L_ / 2 * 0.65, x + L_ / 2 * 0.65, y + s * W_ / 2 * 0.6 - (s > 0) * 12, y + s * W_ / 2 * 0.6 + (s < 0) * 12, -20, 7)
obj_from(bm_c, "caps", cap_m, bevel=2); obj_from(bm_e, "cap_ends", cap_end, bevel=2)

# board, socket frame, chokes, caps
bm = bmesh.new(); box(bm, -40000, 40000, -40000, 40000, -110, -90); obj_from(bm, "pcb", pcb_m)
bm = bmesh.new()
for x0, x1, y0, y1 in ((-2600, 2600, -2600, -2000), (-2600, 2600, 2000, 2600),
                       (-2600, -2000, -2000, 2000), (2000, 2600, -2000, 2000)):
    box(bm, x0, x1, y0, y1, -90, -45)
box(bm, -2000, 2000, -2000, 2000, -90, -60)
obj_from(bm, "socket", socket, bevel=20)
bm_ch = bmesh.new(); bm_cap = bmesh.new()
for i in range(12):
    x = -4800 + i * 870
    box(bm_ch, x - 380, x + 380, 3300, 4060, -90, 380)
    box(bm_ch, -3700, -2940, -4800 + i * 870 - 380, -4800 + i * 870 + 380, -90, 380)
for i in range(40):
    r = random.uniform(4200, 9000); a = random.uniform(0, 2 * math.pi)
    x, y = r * math.cos(a), r * math.sin(a)
    box(bm_cap, x - 120, x + 120, y - 60, y + 60, -90, 0)
obj_from(bm_ch, "chokes", choke, bevel=30)
obj_from(bm_cap, "board_caps", cap_m, bevel=15)
# electrolytic caps (cylinders)
for i in range(9):
    bpy.ops.mesh.primitive_cylinder_add(radius=420, depth=1500, location=(4200 + (i % 3) * 1000, -2500 + (i // 3) * 1000, 660))
    c = bpy.context.active_object; c.data.materials.append(cap_alu)
    for p in c.data.polygons: p.use_smooth = True

# ---------------------------------------------------------------- electrons
electrons = []
for i in range(9):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.028, location=(0, 0, 0.4), segments=16, ring_count=8)
    e = bpy.context.active_object; e.name = f"electron{i}"
    e.data.materials.append(elec_m); e.cycles.use_motion_blur = False
    for p in e.data.polygons: p.use_smooth = True
    electrons.append(e)

# ---------------------------------------------------------------- lights & world
def sun(name, color, strength, elev, azim, angle):
    l = bpy.data.lights.new(name, "SUN"); l.color = color; l.energy = strength; l.angle = math.radians(angle)
    o = bpy.data.objects.new(name, l); scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    return o
sun("key", (1.0, 0.93, 0.85), 3.2, 52, -35, 4)
sun("rim", (0.35, 0.7, 1.0), 1.6, 18, 150, 6)

def point(name, loc, color, power, radius):
    l = bpy.data.lights.new(name, "POINT"); l.color = color; l.energy = power; l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l); o.location = loc; scene.collection.objects.link(o)
point("canyon_cyan", (2.2, -2.0, 2.4), (0.3, 0.75, 1.0), 60, 0.4)
point("canyon_warm", (-2.6, 1.6, 1.6), (1.0, 0.55, 0.3), 35, 0.4)
point("canyon_top", (0.0, 0.0, 9.0), (0.9, 0.9, 1.0), 400, 1.5)

world = bpy.data.worlds.new("world"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.012, 0.018, 0.03, 1); bg.inputs["Strength"].default_value = 1.0

# ---------------------------------------------------------------- camera path
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d)
scene.collection.objects.link(cam); scene.camera = cam
cam_d.lens = 28; cam_d.sensor_fit = "AUTO"; cam_d.sensor_width = 36
cam_d.dof.use_dof = True

KEYS = [  # t, distance, tilt-from-vertical, azimuth
    (0.00, 5600, 56, -120),
    (0.18, 2600, 46, -98),
    (0.38, 420, 24, -74),
    (0.50, 105, 9, -58),
    (0.60, 40, 3, -46),
    (0.74, 11, 5, -32),
    (0.87, 4.6, 30, -12),
    (1.00, 2.9, 50, 18),
]

def pchip(xs, ys):
    n = len(xs); h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0: m[i] = 0
        else:
            w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    def f(x):
        i = max(0, min(n - 2, next((k for k in range(n - 1) if x <= xs[k + 1]), n - 2)))
        t = (x - xs[i]) / h[i]
        h00 = 2 * t**3 - 3 * t**2 + 1; h10 = t**3 - 2 * t**2 + t
        h01 = -2 * t**3 + 3 * t**2; h11 = t**3 - t**2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f

ts = [k[0] for k in KEYS]
f_logd = pchip(ts, [math.log(k[1]) for k in KEYS])
f_tilt = pchip(ts, [k[2] for k in KEYS])
f_az = pchip(ts, [k[3] for k in KEYS])

def smooth(a, b, x):
    x = max(0.0, min(1.0, (x - a) / (b - a))); return x * x * (3 - 2 * x)

TARGET = Vector((0, 0, 0.3))
die_alpha = die_top_m.node_tree.nodes["Principled BSDF"].inputs["Alpha"]
gate_em = hero_g.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
fin_em = hero_f.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]

scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = FPS
for fr in range(1, FRAMES + 1):
    t = (fr - 1) / (FRAMES - 1)
    d = math.exp(f_logd(t)); th = math.radians(f_tilt(t)); ph = math.radians(f_az(t))
    dirv = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
    pos = TARGET + d * dirv
    fwd = -dirv
    up = Vector((-math.cos(th) * math.cos(ph), -math.cos(th) * math.sin(ph), math.sin(th)))
    right = fwd.cross(up)
    R = Matrix((right, up, -fwd)).transposed()
    cam.matrix_world = Matrix.Translation(pos) @ R.to_4x4()
    cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_euler", frame=fr)
    cam_d.clip_start = max(0.002, d * 0.004); cam_d.clip_end = d * 60 + 2000
    cam_d.keyframe_insert("clip_start", frame=fr); cam_d.keyframe_insert("clip_end", frame=fr)
    # die top fades as we dive through it
    a = smooth(38, 85, d)
    die_alpha.default_value = a; die_alpha.id_data.keyframe_insert(die_alpha.path_from_id("default_value"), frame=fr)
    # focus: die surface while it's opaque, transistor afterwards
    f_die = max(0.01, (pos.z - 20.0) / max(0.05, math.cos(th)))
    cam_d.dof.focus_distance = a * f_die + (1 - a) * d
    cam_d.dof.aperture_fstop = 2.8 if t < 0.8 else 2.8 - 1.2 * smooth(0.8, 1.0, t)
    cam_d.keyframe_insert("dof.focus_distance", frame=fr); cam_d.keyframe_insert("dof.aperture_fstop", frame=fr)
    # transistor switches on
    on = smooth(0.82, 0.9, t)
    gate_em.default_value = 0.6 * on; fin_em.default_value = 0.6 * on
    gate_em.id_data.keyframe_insert(gate_em.path_from_id("default_value"), frame=fr)
    fin_em.id_data.keyframe_insert(fin_em.path_from_id("default_value"), frame=fr)
    for i, e in enumerate(electrons):
        ph_e = ((t - 0.84) * 1.6 + i / len(electrons)) % 1.0
        x = -0.55 + 1.1 * ph_e
        vis = on > 0.05 and t > 0.84
        e.location = (x, 0.022 * math.sin(i * 2.1), 0.5 + 0.02 * math.cos(i * 1.7))
        s = (0.0 if not vis else 1.0) * min(1.0, smooth(0.0, 0.12, ph_e) * (1 - smooth(0.88, 1.0, ph_e)) * 1.6)
        e.scale = (s, s, s)
        e.keyframe_insert("location", frame=fr); e.keyframe_insert("scale", frame=fr)

for ob in [cam] + electrons:
    if ob.animation_data and ob.animation_data.action:
        act = ob.animation_data.action
        fcs = getattr(act, "fcurves", None)
        if fcs is None:
            try: fcs = act.layers[0].strips[0].channelbags[0].fcurves
            except Exception: fcs = []
        for fc in fcs:
            for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

# ---------------------------------------------------------------- render settings
r = scene.render
r.engine = "CYCLES"; r.resolution_x, r.resolution_y = 1080, 1920; r.resolution_percentage = 100
c = scene.cycles
c.device = "CPU"; c.samples = 96; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02
c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"
c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 5; c.transmission_bounces = 2
c.transparent_max_bounces = 8; c.caustics_reflective = False; c.caustics_refractive = False
c.blur_glossy = 0.6
r.use_motion_blur = True; r.motion_blur_shutter = 0.35
r.use_persistent_data = True
scene.view_settings.view_transform = "AgX"
try: scene.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass
r.image_settings.file_format = "PNG"; r.image_settings.color_depth = "8"
r.filepath = os.path.join(HERE, "frames", "f_")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "scene.blend"))
print("saved", len(bpy.data.objects), "objects")
