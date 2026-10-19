"""
=============================================================================
3D PROCEDURAL GENERATOR: ADVAN WORKPLUS AIR (AUTHENTIC REALISM EDITION)
=============================================================================
Deskripsi:
  Skrip Blender Python (bpy) untuk membuat model 3D laptop Advan Workplus Air
  yang sesuai dengan laptop asli:
  1. Warna bodi: Aluminium Teal Gelap Matte (#2f4a57), roughness 0.55, metallic 0.60
     Keycaps: Hitam (#111214), roughness 0.60
     Bezel: Hitam (#111214), roughness 0.65
  2. Semua objek diberi Bevel Modifier kecil (0.05 cm, segments 2) dan di-apply
     sebelum ekspor.
  3. Keycaps: Setiap tombol memiliki permukaan atas sedikit cekung (concave dish),
     sudut membulat, dan celah (gap) antar tombol yang jelas.
  4. Lid Cover: Polos, logo ADVAN kecil di pojok kanan atas (bukan di tengah).
  5. Touchpad: Sewarna bodi (#2f4a57) dengan tepi menjorok tipis (recessed border).
  6. Detail Tambahan:
     - Kisi ventilasi & lubang sekrup cekung di bottom_case
     - Port USB-C, USB-A, HDMI, dan Audio Jack di sisi keyboard_deck
     - Kabel flat kecil (FPC ribbon cable) di dalam
     - Chip IC, VRM, kapasitor & konektor emas di motherboard
     - Plat label spesifikasi pada battery
  7. Pembagian UV otomatis (Smart/Box Planar UV) & tekstur Roughness Noise
     prosedural untuk bodi aluminium matte.
  8. Total poligon optimal di bawah 150.000 segitiga (< 150k tris).

Hierarki Objek (Tetap Dipertahankan):
  laptop_root (Empty)
    ├── group_display (Empty)
    │     ├── lid_cover
    │     ├── display_bezel
    │     ├── display_panel
    │     └── webcam_module
    ├── group_top_case (Empty)
    │     ├── keyboard_deck
    │     ├── keycaps
    │     ├── touchpad
    │     ├── hinge_left
    │     └── hinge_right
    ├── group_internals (Empty)
    │     ├── motherboard
    │     ├── cpu_heatsink
    │     ├── fan
    │     ├── battery
    │     ├── ssd_m2
    │     ├── ram_module
    │     ├── speaker_left
    │     └── speaker_right
    └── group_bottom (Empty)
          ├── bottom_case
          ├── rubber_feet
          └── screws
=============================================================================
"""

import bpy
import bmesh
from mathutils import Vector
import math
import os
import random

# =============================================================================
# KONFIGURASI PENGATURAN & EKSPOR
# =============================================================================
OUTPUT_FILENAME = "laptop_advan_workplus_air.glb"
CLEAR_EXISTING_SCENE = True
ENABLE_DRACO_COMPRESSION = False

# Dimensi Utama Laptop (1 Blender Unit = 1 cm)
CHASSIS_WIDTH = 31.2
CHASSIS_DEPTH = 21.8
CHASSIS_CORNER_RADIUS = 0.65
CORNER_SEGMENTS = 5


def hex_to_linear_rgba(hex_str, alpha=1.0):
    """Konversi warna hex sRGB (#2f4a57) ke Linear RGBA untuk Blender BSDF."""
    h = hex_str.lstrip('#')
    sr = int(h[0:2], 16) / 255.0
    sg = int(h[2:4], 16) / 255.0
    sb = int(h[4:6], 16) / 255.0

    def to_lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return [to_lin(sr), to_lin(sg), to_lin(sb), alpha]


# =============================================================================
# HELPER: TEKSTUR ROUGHNESS NOISE SEDERHANA UNTUK BODI ALUMINIUM MATTE
# =============================================================================
def create_body_roughness_image(name="tex_body_roughness_noise", size=256):
    """Membuat tekstur grayscale noise halus untuk variasi roughness ~0.52 - 0.58."""
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)

    img = bpy.data.images.new(name=name, width=size, height=size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'

    rng = random.Random(42)
    pixels = [0.0] * (size * size * 4)
    for i in range(size * size):
        val = 0.55 + (rng.random() - 0.5) * 0.08
        idx = i * 4
        pixels[idx] = val
        pixels[idx + 1] = val
        pixels[idx + 2] = val
        pixels[idx + 3] = 1.0

    img.pixels = pixels
    img.pack()
    return img


# =============================================================================
# HELPER: MATERIAL BUILDER (PBR PRINCIPLED BSDF + ROUGHNESS NOISE)
# =============================================================================
def create_pbr_material(name, base_color, metallic=0.0, roughness=0.55, ior=1.5, roughness_img=None):
    """Membuat material PBR Principled BSDF kompatibel Blender 3.x & 4.x."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.location = (0, 0)

    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location = (320, 0)
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])

    if 'Base Color' in node_bsdf.inputs:
        node_bsdf.inputs['Base Color'].default_value = base_color
    if 'Metallic' in node_bsdf.inputs:
        node_bsdf.inputs['Metallic'].default_value = metallic
    if 'Roughness' in node_bsdf.inputs:
        node_bsdf.inputs['Roughness'].default_value = roughness
    if 'IOR' in node_bsdf.inputs:
        node_bsdf.inputs['IOR'].default_value = ior

    # Pasang tekstur roughness noise untuk sasis aluminium matte
    if roughness_img is not None:
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        tex_coord.location = (-720, -120)

        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.location = (-520, -120)
        if 'Scale' in mapping.inputs:
            mapping.inputs['Scale'].default_value = (6.0, 6.0, 6.0)

        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.location = (-280, -120)
        tex_node.image = roughness_img

        links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])
        links.new(tex_node.outputs['Color'], node_bsdf.inputs['Roughness'])

    return mat


# =============================================================================
# HELPER FUNCTIONS: BMESH GEOMETRY GENERATORS
# =============================================================================
def add_box(bm, x0, x1, y0, y1, z0, z1):
    """Menambahkan balok 6 sisi ke bmesh."""
    v000 = bm.verts.new((x0, y0, z0))
    v100 = bm.verts.new((x1, y0, z0))
    v110 = bm.verts.new((x1, y1, z0))
    v010 = bm.verts.new((x0, y1, z0))

    v001 = bm.verts.new((x0, y0, z1))
    v101 = bm.verts.new((x1, y0, z1))
    v111 = bm.verts.new((x1, y1, z1))
    v011 = bm.verts.new((x0, y1, z1))

    bm.faces.new((v000, v010, v110, v100))
    bm.faces.new((v001, v101, v111, v011))
    bm.faces.new((v000, v100, v101, v001))
    bm.faces.new((v110, v010, v011, v111))
    bm.faces.new((v010, v000, v001, v011))
    bm.faces.new((v100, v110, v111, v101))


def get_rounded_rect_points(cx, cy, w, d, radius, segments=4):
    """Menghasilkan titik 2D persegi sudut membulat."""
    r = max(0.001, min(radius, w * 0.48, d * 0.48))
    hx = w * 0.5 - r
    hy = d * 0.5 - r

    centers = [
        (cx + hx, cy + hy, 0.0, math.pi * 0.5),
        (cx - hx, cy + hy, math.pi * 0.5, math.pi),
        (cx - hx, cy - hy, math.pi, math.pi * 1.5),
        (cx + hx, cy - hy, math.pi * 1.5, math.pi * 2.0)
    ]

    points = []
    for corner_cx, corner_cy, start_ang, end_ang in centers:
        for i in range(segments):
            angle = start_ang + (end_ang - start_ang) * (i / float(segments))
            px = corner_cx + r * math.cos(angle)
            py = corner_cy + r * math.sin(angle)
            points.append((px, py))
    return points


def add_rounded_box(bm, cx, cy, w, d, z0, z1, radius=0.65, segments=4):
    """Menambahkan prisma persegi sudut membulat ke bmesh."""
    ring = get_rounded_rect_points(cx, cy, w, d, radius, segments)
    n = len(ring)

    v_bot = [bm.verts.new((px, py, z0)) for px, py in ring]
    v_top = [bm.verts.new((px, py, z1)) for px, py in ring]

    v_bot_center = bm.verts.new((cx, cy, z0))
    v_top_center = bm.verts.new((cx, cy, z1))

    for i in range(n):
        nxt = (i + 1) % n
        bm.faces.new((v_bot_center, v_bot[nxt], v_bot[i]))
        bm.faces.new((v_top_center, v_top[i], v_top[nxt]))
        bm.faces.new((v_bot[i], v_bot[nxt], v_top[nxt], v_top[i]))


def add_concave_keycap(bm, cx, cy, w, d, z0, z1, radius=0.16, segments=3, dish_depth=0.018):
    """
    Membuat tombol keyboard dengan sudut membulat dan permukaan atas sedikit cekung (concave dish).
    """
    outer_ring = get_rounded_rect_points(cx, cy, w, d, radius, segments)
    inner_ring = get_rounded_rect_points(cx, cy, w * 0.76, d * 0.74, radius * 0.65, segments)
    n = len(outer_ring)

    v_bot = [bm.verts.new((px, py, z0)) for px, py in outer_ring]
    v_top_rim = [bm.verts.new((px, py, z1)) for px, py in outer_ring]
    v_top_dish = [bm.verts.new((px, py, z1 - dish_depth * 0.6)) for px, py in inner_ring]

    v_bot_center = bm.verts.new((cx, cy, z0))
    v_dish_center = bm.verts.new((cx, cy, z1 - dish_depth))

    for i in range(n):
        nxt = (i + 1) % n
        # Sisi bawah
        bm.faces.new((v_bot_center, v_bot[nxt], v_bot[i]))
        # Dinding samping luar
        bm.faces.new((v_bot[i], v_bot[nxt], v_top_rim[nxt], v_top_rim[i]))
        # Lereng transisi dari tepi atas ke cekungan tombol
        bm.faces.new((v_top_rim[i], v_top_rim[nxt], v_top_dish[nxt], v_top_dish[i]))
        # Dasar cekungan tengah tombol
        bm.faces.new((v_dish_center, v_top_dish[i], v_top_dish[nxt]))


def add_cylinder(bm, cx, cy, cz0, cz1, radius, segments=14, axis='Z'):
    """Menambahkan silinder ke bmesh sepanjang sumbu X, Y, atau Z."""
    r = max(0.001, radius)
    circle_pts = [
        (math.cos((math.pi * 2.0 * i) / segments) * r,
         math.sin((math.pi * 2.0 * i) / segments) * r)
        for i in range(segments)
    ]

    n = segments
    if axis == 'Z':
        v_bot = [bm.verts.new((cx + px, cy + py, cz0)) for px, py in circle_pts]
        v_top = [bm.verts.new((cx + px, cy + py, cz1)) for px, py in circle_pts]
        c_bot = bm.verts.new((cx, cy, cz0))
        c_top = bm.verts.new((cx, cy, cz1))
    elif axis == 'X':
        v_bot = [bm.verts.new((cz0, cy + px, cx + py)) for px, py in circle_pts]
        v_top = [bm.verts.new((cz1, cy + px, cx + py)) for px, py in circle_pts]
        c_bot = bm.verts.new((cz0, cy, cx))
        c_top = bm.verts.new((cz1, cy, cx))
    else:
        v_bot = [bm.verts.new((cx + px, cz0, cy + py)) for px, py in circle_pts]
        v_top = [bm.verts.new((cx + px, cz1, cy + py)) for px, py in circle_pts]
        c_bot = bm.verts.new((cx, cz0, cy))
        c_top = bm.verts.new((cx, cz1, cy))

    for i in range(n):
        nxt = (i + 1) % n
        bm.faces.new((c_bot, v_bot[nxt], v_bot[i]))
        bm.faces.new((c_top, v_top[i], v_top[nxt]))
        bm.faces.new((v_bot[i], v_bot[nxt], v_top[nxt], v_top[i]))


def assign_planar_uv(bm, width, depth):
    """Membagi UV secara planar (X-Y di Blender) agar tekstur terpetakan rapi [0..1]."""
    uv_layer = bm.loops.layers.uv.verify()
    hw = max(0.001, width * 0.5)
    hd = max(0.001, depth * 0.5)
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            u = (co.x + hw) / width
            v = (co.y + hd) / depth
            loop[uv_layer].uv = (max(0.0, min(1.0, u)), max(0.0, min(1.0, v)))


# =============================================================================
# OBJECT FACTORY: UV, BEVEL MODIFIER (0.05 cm, 2 SEGMENTS) + APPLY & EXTRAS
# =============================================================================
def build_and_finalize_mesh_object(
    name, bm, material, explode_dir, explode_dist, parent_empty, collection,
    uv_size=(CHASSIS_WIDTH, CHASSIS_DEPTH), bevel_width=0.05, bevel_segments=2
):
    """
    1. Membuat UV planar pada bmesh
    2. Memusatkan pivot di pusat massa objek
    3. Menambahkan Bevel Modifier (0.05 cm, segments 2-3) dan melakukan APPLY
    4. Menyimpan custom property 'explode_dir' & 'explode_dist'
    """
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_planar_uv(bm, uv_size[0], uv_size[1])

    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    verts = mesh.vertices
    if len(verts) > 0:
        center = sum((v.co for v in verts), Vector((0.0, 0.0, 0.0))) / len(verts)
        for v in verts:
            v.co -= center
        obj.location = center

    # Tambahkan Bevel Modifier kecil (0.05 cm, segments 2) lalu Apply sebelum ekspor
    if bevel_width > 0.001:
        bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
        bevel_mod.width = bevel_width
        bevel_mod.segments = bevel_segments
        bevel_mod.limit_method = 'ANGLE'
        bevel_mod.angle_limit = math.radians(32.0)
        if hasattr(bevel_mod, "use_clamp_overlap"):
            bevel_mod.use_clamp_overlap = True

        try:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_apply(modifier=bevel_mod.name)
            obj.select_set(False)
        except Exception:
            pass

    for poly in obj.data.polygons:
        poly.use_smooth = True
    if hasattr(obj.data, "use_auto_smooth"):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(35.0)

    if material:
        obj.data.materials.append(material)

    dir_vec = Vector(explode_dir)
    if dir_vec.length > 0.0001:
        dir_vec.normalize()

    obj["explode_dir"] = [round(dir_vec.x, 4), round(dir_vec.y, 4), round(dir_vec.z, 4)]
    obj["explode_dist"] = float(explode_dist)

    if parent_empty:
        obj.parent = parent_empty
        obj.matrix_parent_inverse = parent_empty.matrix_world.inverted()

    return obj


# =============================================================================
# BUILDERS UNTUK 20 KOMPONEN SPESIFIK LAPTOP ADVAN WORKPLUS AIR
# =============================================================================

# --- 1. GROUP DISPLAY --------------------------------------------------------
def build_lid_cover(mat, parent, col):
    """
    Lid cover (A-Shell): Polos, warna teal gelap matte (#2f4a57),
    dengan emblem logo ADVAN kecil di pojok kanan atas (bukan di tengah).
    """
    bm = bmesh.new()
    add_rounded_box(bm, cx=0.0, cy=0.0, w=CHASSIS_WIDTH, d=CHASSIS_DEPTH,
                    z0=1.36, z1=1.60, radius=CHASSIS_CORNER_RADIUS, segments=CORNER_SEGMENTS)

    # Logo ADVAN kecil di pojok/sisi kanan atas lid (x: +8.2 s/d +12.6, y: +4.5 s/d +5.3)
    logo_y = 4.8
    for i in range(5):
        lx = 8.4 + i * 0.85
        add_box(bm, lx, lx + 0.62, logo_y - 0.32, logo_y + 0.32, 1.60, 1.612)

    return build_and_finalize_mesh_object("lid_cover", bm, mat, [0.0, 0.15, 1.0], 14.0, parent, col)


def build_display_bezel(mat, parent, col):
    """Display bezel: Bingkai layar hitam tipis 16:10."""
    bm = bmesh.new()
    z0, z1 = 1.26, 1.35
    # Sisi kiri & kanan
    add_box(bm, -15.55, -14.75, -10.85, 10.85, z0, z1)
    add_box(bm, 14.75, 15.55, -10.85, 10.85, z0, z1)
    # Bezel atas
    add_box(bm, -14.75, 14.75, 9.95, 10.85, z0, z1)
    # Bezel dagu bawah (chin)
    add_box(bm, -14.75, 14.75, -10.85, -8.55, z0, z1)
    return build_and_finalize_mesh_object("display_bezel", bm, mat, [0.0, 0.15, 1.0], 11.5, parent, col)


def build_display_panel(mat, parent, col):
    """Display panel: Layar kaca gelap 14 inci 16:10."""
    bm = bmesh.new()
    add_box(bm, -14.75, 14.75, -8.55, 9.95, 1.28, 1.34)
    return build_and_finalize_mesh_object("display_panel", bm, mat, [0.0, 0.15, 1.0], 9.5, parent, col,
                                          uv_size=(29.5, 18.5))


def build_webcam_module(mat, parent, col):
    """Webcam module: Kamera HD, LED indikator, dan mikrofon ganda di bezel atas."""
    bm = bmesh.new()
    add_box(bm, -1.5, 1.5, 10.2, 10.65, 1.29, 1.34)
    add_cylinder(bm, cx=0.0, cy=10.42, cz0=1.34, cz1=1.37, radius=0.13, segments=12, axis='Z')
    add_cylinder(bm, cx=0.45, cy=10.42, cz0=1.34, cz1=1.36, radius=0.04, segments=8, axis='Z')
    add_cylinder(bm, cx=-1.05, cy=10.42, cz0=1.34, cz1=1.36, radius=0.04, segments=8, axis='Z')
    add_cylinder(bm, cx=1.05, cy=10.42, cz0=1.34, cz1=1.36, radius=0.04, segments=8, axis='Z')
    return build_and_finalize_mesh_object("webcam_module", bm, mat, [0.0, 0.2, 1.0], 12.8, parent, col)


# --- 2. GROUP TOP CASE -------------------------------------------------------
def build_keyboard_deck(mat, parent, col):
    """
    Keyboard deck (C-Shell): Bodi atas teal gelap matte (#2f4a57) dengan cekungan
    keyboard, bingkai touchpad menjorok tipis, serta detail port USB-C, USB-A, HDMI & Audio Jack.
    """
    bm = bmesh.new()
    # Pelat dasar C-shell
    add_rounded_box(bm, cx=0.0, cy=0.0, w=CHASSIS_WIDTH, d=CHASSIS_DEPTH,
                    z0=0.58, z1=1.02, radius=CHASSIS_CORNER_RADIUS, segments=CORNER_SEGMENTS)
    # Area Palmrest depan (di kiri & kanan touchpad)
    add_box(bm, -15.5, -6.0, -10.8, -0.3, 1.02, 1.14)
    add_box(bm, 6.0, 15.5, -10.8, -0.3, 1.02, 1.14)
    add_box(bm, -6.0, 6.0, -10.8, -9.5, 1.02, 1.14)
    add_box(bm, -6.0, 6.0, -1.8, -0.3, 1.02, 1.14)
    # Strip belakang di atas keyboard & strip samping kiri-kanan keyboard
    add_box(bm, -15.5, 15.5, 9.6, 10.8, 1.02, 1.14)
    add_box(bm, -15.5, -13.9, -0.3, 9.6, 1.02, 1.14)
    add_box(bm, 13.9, 15.5, -0.3, 9.6, 1.02, 1.14)

    # Detail Port Sisi Kiri: 1x HDMI, 2x USB Type-C 3.2
    add_box(bm, -15.62, -15.35, 6.5, 7.9, 0.72, 0.94)   # Port HDMI
    add_box(bm, -15.62, -15.35, 4.6, 5.45, 0.74, 0.90)  # Port USB-C 1 (PD/Display)
    add_box(bm, -15.62, -15.35, 2.9, 3.75, 0.74, 0.90)  # Port USB-C 2

    # Detail Port Sisi Kanan: 1x USB-A 3.2, 1x Audio Combo Jack 3.5mm, 1x USB-C 2.0
    add_box(bm, 15.35, 15.62, 6.1, 7.45, 0.70, 0.94)    # Port USB-A 3.2
    add_cylinder(bm, cx=4.5, cy=0.82, cz0=15.32, cz1=15.62, radius=0.16, segments=10, axis='X')  # Audio Jack
    add_box(bm, 15.35, 15.62, 2.7, 3.55, 0.74, 0.90)    # Port USB-C

    return build_and_finalize_mesh_object("keyboard_deck", bm, mat, [0.0, 0.0, 1.0], 2.5, parent, col)


def build_keycaps(mat, parent, col):
    """
    Keycaps: 6 baris tombol hitam (#111214) dengan permukaan atas cekung (concave),
    sudut membulat, dan celah antar tombol yang jelas.
    """
    bm = bmesh.new()
    z0, z1 = 1.04, 1.18
    kh = 1.32

    # Baris 0: Esc, F1-F12, PrtSc, Ins, Del/Power (16 tombol)
    y0 = 8.95
    for i in range(16):
        x = -13.0 + i * 1.733
        add_concave_keycap(bm, cx=x, cy=y0, w=1.48, d=0.82, z0=z0, z1=z1, radius=0.12, segments=2)

    # Baris 1: Angka 1-0 & Backspace
    y1 = 7.55
    for i in range(13):
        x = -12.95 + i * 1.88
        add_concave_keycap(bm, cx=x, cy=y1, w=1.60, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=12.35, cy=y1, w=2.75, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)

    # Baris 2: Tab + QWERTY
    y2 = 5.92
    add_concave_keycap(bm, cx=-12.55, cy=y2, w=2.40, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    for i in range(12):
        x = -10.35 + i * 1.88
        add_concave_keycap(bm, cx=x, cy=y2, w=1.60, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=12.68, cy=y2, w=2.10, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)

    # Baris 3: CapsLock + ASDF + Enter
    y3 = 4.29
    add_concave_keycap(bm, cx=-12.32, cy=y3, w=2.85, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    for i in range(11):
        x = -9.90 + i * 1.88
        add_concave_keycap(bm, cx=x, cy=y3, w=1.60, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=11.95, cy=y3, w=3.55, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)

    # Baris 4: Shift + ZXCV + Shift
    y4 = 2.66
    add_concave_keycap(bm, cx=-11.87, cy=y4, w=3.75, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    for i in range(10):
        x = -8.98 + i * 1.88
        add_concave_keycap(bm, cx=x, cy=y4, w=1.60, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=11.48, cy=y4, w=4.50, d=kh, z0=z0, z1=z1, radius=0.15, segments=2)

    # Baris 5: Ctrl, Fn, Win, Alt, Spacebar, Alt, Ctrl, Arrow Cluster
    y5 = 0.98
    add_concave_keycap(bm, cx=-12.72, cy=y5, w=2.05, d=1.42, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=-10.55, cy=y5, w=1.65, d=1.42, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=-8.58, cy=y5, w=1.65, d=1.42, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=-6.60, cy=y5, w=1.65, d=1.42, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=-0.82, cy=y5, w=9.20, d=1.42, z0=z0, z1=z1, radius=0.16, segments=2, dish_depth=0.01)
    add_concave_keycap(bm, cx=4.95, cy=y5, w=1.65, d=1.42, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=6.92, cy=y5, w=1.65, d=1.42, z0=z0, z1=z1, radius=0.15, segments=2)
    add_concave_keycap(bm, cx=8.92, cy=y5, w=1.62, d=1.42, z0=z0, z1=z1, radius=0.14, segments=2)
    add_concave_keycap(bm, cx=10.88, cy=y5 + 0.38, w=1.62, d=0.66, z0=z0, z1=z1, radius=0.10, segments=2)
    add_concave_keycap(bm, cx=10.88, cy=y5 - 0.38, w=1.62, d=0.66, z0=z0, z1=z1, radius=0.10, segments=2)
    add_concave_keycap(bm, cx=12.84, cy=y5, w=1.62, d=1.42, z0=z0, z1=z1, radius=0.14, segments=2)

    return build_and_finalize_mesh_object("keycaps", bm, mat, [0.0, 0.0, 1.0], 5.2, parent, col,
                                          uv_size=(27.6, 9.4), bevel_width=0.02, bevel_segments=2)


def build_touchpad(mat, parent, col):
    """Touchpad: Sewarna bodi (#2f4a57) dengan tepi menjorok tipis (recessed border)."""
    bm = bmesh.new()
    # Permukaan sentuh utama sedikit di bawah bibir palmrest
    add_rounded_box(bm, cx=0.0, cy=-5.65, w=11.6, d=7.3, z0=1.06, z1=1.115, radius=0.28, segments=4)
    # Tepi chamfer tipis di sekeliling touchpad
    add_rounded_box(bm, cx=0.0, cy=-5.65, w=11.85, d=7.55, z0=1.04, z1=1.08, radius=0.32, segments=4)
    return build_and_finalize_mesh_object("touchpad", bm, mat, [0.0, -0.15, 1.0], 4.0, parent, col,
                                          uv_size=(11.8, 7.5))


def build_hinge_left(mat, parent, col):
    """Hinge Left: Engsel torsi baja sisi kiri."""
    bm = bmesh.new()
    add_cylinder(bm, cx=1.08, cy=10.55, cz0=-9.8, cz1=-6.6, radius=0.22, segments=12, axis='X')
    add_box(bm, -9.6, -6.8, 9.8, 10.6, 0.94, 1.10)
    return build_and_finalize_mesh_object("hinge_left", bm, mat, [-0.5, 0.0, 0.8], 4.2, parent, col)


def build_hinge_right(mat, parent, col):
    """Hinge Right: Engsel torsi baja sisi kanan."""
    bm = bmesh.new()
    add_cylinder(bm, cx=1.08, cy=10.55, cz0=6.6, cz1=9.8, radius=0.22, segments=12, axis='X')
    add_box(bm, 6.8, 9.6, 9.8, 10.6, 0.94, 1.10)
    return build_and_finalize_mesh_object("hinge_right", bm, mat, [0.5, 0.0, 0.8], 4.2, parent, col)


# --- 3. GROUP INTERNALS ------------------------------------------------------
def build_motherboard(mat, parent, col):
    """
    Motherboard: Papan sirkuit utama dengan chip CPU/SoC, VRM inductors,
    kapasitor SMD, konektor I/O, dan kabel flat kecil (FPC ribbon cable).
    """
    bm = bmesh.new()
    # Papan PCB Utama
    add_box(bm, -13.2, 13.2, -0.2, 9.8, 0.56, 0.68)
    # Soket & Silicon Die AMD Ryzen
    add_box(bm, -1.8, 2.2, 3.8, 7.4, 0.68, 0.80)
    add_box(bm, -0.8, 1.2, 4.6, 6.6, 0.80, 0.85)
    # Chipset Controller & Audio IC
    add_box(bm, 3.8, 5.6, 1.8, 3.6, 0.68, 0.78)
    add_box(bm, -6.5, -5.1, 1.5, 2.9, 0.68, 0.77)
    # Deretan Choke VRM & Kapasitor
    for i in range(6):
        add_box(bm, -3.2, -2.4, 3.6 + i * 0.85, 4.25 + i * 0.85, 0.68, 0.86)
    # Kabel Flat Kecil (FPC Ribbon Cable) penghubung trackpad/keyboard & I/O
    add_box(bm, -1.1, 1.1, -2.4, 0.4, 0.66, 0.71)
    add_box(bm, -12.8, -8.5, 1.2, 2.1, 0.68, 0.72)
    return build_and_finalize_mesh_object("motherboard", bm, mat, [0.0, 0.0, -1.0], 2.2, parent, col,
                                          uv_size=(26.4, 10.2))


def build_cpu_heatsink(mat, parent, col):
    """CPU heatsink: Plat tembaga, dual heatpipe, dan sirip radiator exhaust."""
    bm = bmesh.new()
    add_box(bm, -2.0, 2.4, 3.7, 7.5, 0.82, 0.92)
    add_box(bm, -8.6, -2.0, 6.2, 6.95, 0.84, 0.94)
    add_box(bm, -8.6, -2.0, 4.7, 5.45, 0.84, 0.94)
    for i in range(22):
        x = -12.6 + i * 0.24
        add_box(bm, x, x + 0.11, 8.6, 10.1, 0.64, 1.00)
    return build_and_finalize_mesh_object("cpu_heatsink", bm, mat, [0.0, 0.1, 1.0], 1.2, parent, col)


def build_fan(mat, parent, col):
    """Cooling fan: Kipas sentrifugal dengan rumah blower dan 16 bilah turbin."""
    bm = bmesh.new()
    add_rounded_box(bm, cx=-9.8, cy=5.6, w=6.6, d=6.6, z0=0.56, z1=0.96, radius=1.2, segments=4)
    add_cylinder(bm, cx=-9.8, cy=5.6, cz0=0.58, cz1=0.98, radius=1.1, segments=14, axis='Z')
    for i in range(16):
        ang = (math.pi * 2.0 * i) / 16
        bx = -9.8 + math.cos(ang) * 1.75
        by = 5.6 + math.sin(ang) * 1.75
        add_box(bm, bx - 0.08, bx + 0.08, by - 0.65, by + 0.65, 0.62, 0.94)
    return build_and_finalize_mesh_object("fan", bm, mat, [-0.2, 0.1, 1.0], 0.5, parent, col)


def build_battery(mat, parent, col):
    """
    Battery pack: Baterai Li-Polymer 3-sel abu gelap dilengkapi plat label
    spesifikasi dan konektor kabel flat ke motherboard.
    """
    bm = bmesh.new()
    z0, z1 = 0.54, 0.88
    add_rounded_box(bm, cx=-8.6, cy=-5.2, w=8.2, d=8.6, z0=z0, z1=z1, radius=0.35, segments=4)
    add_rounded_box(bm, cx=0.0, cy=-5.2, w=8.2, d=8.6, z0=z0, z1=z1, radius=0.35, segments=4)
    add_rounded_box(bm, cx=8.6, cy=-5.2, w=8.2, d=8.6, z0=z0, z1=z1, radius=0.35, segments=4)
    # Plat Label Informasi Baterai di atas sel tengah & kiri
    add_box(bm, -11.5, 4.5, -8.2, -2.2, 0.88, 0.905)
    # Papan BMS & Kabel Flat Konektor Baterai
    add_box(bm, -12.8, 12.8, -0.8, -0.2, 0.58, 0.82)
    add_box(bm, -0.9, 0.9, -0.2, 0.4, 0.66, 0.80)
    return build_and_finalize_mesh_object("battery", bm, mat, [0.0, -0.2, -1.0], 4.2, parent, col,
                                          uv_size=(26.0, 9.2))


def build_ssd_m2(mat, parent, col):
    """SSD M.2 2280 NVMe dengan controller, chip NAND, dan konektor M-Key."""
    bm = bmesh.new()
    add_box(bm, 7.1, 9.3, 1.2, 9.0, 0.70, 0.80)
    add_box(bm, 7.4, 9.0, 7.0, 8.4, 0.80, 0.90)
    add_box(bm, 7.3, 9.1, 4.6, 6.4, 0.80, 0.89)
    add_box(bm, 7.3, 9.1, 2.2, 4.0, 0.80, 0.89)
    return build_and_finalize_mesh_object("ssd_m2", bm, mat, [0.3, 0.1, -1.0], 1.2, parent, col)


def build_ram_module(mat, parent, col):
    """RAM Module: SO-DIMM PCB hijau tua dengan 8 chip DRAM hitam."""
    bm = bmesh.new()
    add_box(bm, -2.2, 4.6, 1.2, 4.2, 0.70, 0.80)
    for i in range(4):
        x = -1.6 + i * 1.45
        add_box(bm, x, x + 1.05, 1.5, 2.4, 0.80, 0.89)
        add_box(bm, x, x + 1.05, 2.9, 3.8, 0.80, 0.89)
    return build_and_finalize_mesh_object("ram_module", bm, mat, [0.0, 0.2, -1.0], 0.8, parent, col)


def build_speaker_left(mat, parent, col):
    """Speaker Left: Modul speaker stereo kiri."""
    bm = bmesh.new()
    add_rounded_box(bm, cx=-14.0, cy=-5.2, w=2.1, d=6.2, z0=0.56, z1=0.86, radius=0.3, segments=3)
    add_cylinder(bm, cx=-14.0, cy=-4.0, cz0=0.82, cz1=0.90, radius=0.62, segments=12, axis='Z')
    add_cylinder(bm, cx=-14.0, cy=-6.4, cz0=0.82, cz1=0.90, radius=0.62, segments=12, axis='Z')
    return build_and_finalize_mesh_object("speaker_left", bm, mat, [-0.8, -0.1, -1.0], 3.2, parent, col)


def build_speaker_right(mat, parent, col):
    """Speaker Right: Modul speaker stereo kanan."""
    bm = bmesh.new()
    add_rounded_box(bm, cx=14.0, cy=-5.2, w=2.1, d=6.2, z0=0.56, z1=0.86, radius=0.3, segments=3)
    add_cylinder(bm, cx=14.0, cy=-4.0, cz0=0.82, cz1=0.90, radius=0.62, segments=12, axis='Z')
    add_cylinder(bm, cx=14.0, cy=-6.4, cz0=0.82, cz1=0.90, radius=0.62, segments=12, axis='Z')
    return build_and_finalize_mesh_object("speaker_right", bm, mat, [0.8, -0.1, -1.0], 3.2, parent, col)


# --- 4. GROUP BOTTOM ---------------------------------------------------------
def build_bottom_case(mat, parent, col):
    """
    Bottom case (D-Shell): Penutup bawah teal gelap matte (#2f4a57) dengan
    kisi ventilasi udara lebar dan 10 lubang dudukan sekrup (screw wells).
    """
    bm = bmesh.new()
    add_rounded_box(bm, cx=0.0, cy=0.0, w=CHASSIS_WIDTH, d=CHASSIS_DEPTH,
                    z0=0.14, z1=0.50, radius=CHASSIS_CORNER_RADIUS, segments=CORNER_SEGMENTS)

    # Kisi-kisi ventilasi intake udara di bagian tengah-atas
    for i in range(22):
        y = 2.6 + i * 0.24
        add_box(bm, -8.2, 8.2, y, y + 0.11, 0.10, 0.52)

    # 10 Cincin Lubang Sekrup (Screw Wells) pada tepian bawah sasis
    screw_coords = [
        (-14.0, 9.8), (-5.0, 9.8), (5.0, 9.8), (14.0, 9.8),
        (-14.6, 0.0), (14.6, 0.0),
        (-14.0, -9.8), (-5.0, -9.8), (5.0, -9.8), (14.0, -9.8)
    ]
    for sx, sy in screw_coords:
        add_cylinder(bm, cx=sx, cy=sy, cz0=0.11, cz1=0.22, radius=0.28, segments=10, axis='Z')

    return build_and_finalize_mesh_object("bottom_case", bm, mat, [0.0, 0.0, -1.0], 6.8, parent, col)


def build_rubber_feet(mat, parent, col):
    """Rubber feet: Strip karet belakang panjang & 2 bantalan karet depan."""
    bm = bmesh.new()
    add_rounded_box(bm, cx=0.0, cy=9.2, w=24.5, d=0.75, z0=0.02, z1=0.14, radius=0.3, segments=4)
    add_rounded_box(bm, cx=-11.4, cy=-9.0, w=3.6, d=0.75, z0=0.02, z1=0.14, radius=0.3, segments=4)
    add_rounded_box(bm, cx=11.4, cy=-9.0, w=3.6, d=0.75, z0=0.02, z1=0.14, radius=0.3, segments=4)
    return build_and_finalize_mesh_object("rubber_feet", bm, mat, [0.0, 0.0, -1.0], 8.8, parent, col)


def build_screws(mat, parent, col):
    """Screws: 10 sekrup baja presisi di bagian bawah laptop."""
    bm = bmesh.new()
    screw_coords = [
        (-14.0, 9.8), (-5.0, 9.8), (5.0, 9.8), (14.0, 9.8),
        (-14.6, 0.0), (14.6, 0.0),
        (-14.0, -9.8), (-5.0, -9.8), (5.0, -9.8), (14.0, -9.8)
    ]
    for sx, sy in screw_coords:
        add_cylinder(bm, cx=sx, cy=sy, cz0=0.05, cz1=0.13, radius=0.20, segments=10, axis='Z')
        add_cylinder(bm, cx=sx, cy=sy, cz0=0.13, cz1=0.45, radius=0.09, segments=8, axis='Z')
    return build_and_finalize_mesh_object("screws", bm, mat, [0.0, 0.0, -1.0], 10.6, parent, col,
                                          bevel_width=0.015, bevel_segments=2)


# =============================================================================
# MAIN ORCHESTRATOR FUNCTION
# =============================================================================
def generate_advan_workplus_air(export_path=None):
    print("\n" + "=" * 70)
    print("▶ MEMBANGUN MODEL 3D REALISTIS ADVAN WORKPLUS AIR (#2f4a57)...")
    print("=" * 70)

    if CLEAR_EXISTING_SCENE:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        for m in list(bpy.data.meshes):
            bpy.data.meshes.remove(m)
        for mat in list(bpy.data.materials):
            bpy.data.materials.remove(mat)

    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.length_unit = 'CENTIMETERS'
    bpy.context.scene.unit_settings.scale_length = 0.01

    collection = bpy.context.scene.collection

    laptop_root = bpy.data.objects.new("laptop_root", None)
    laptop_root.empty_display_type = 'PLAIN_AXES'
    laptop_root.empty_display_size = 15.0
    collection.objects.link(laptop_root)

    group_names = ["group_display", "group_top_case", "group_internals", "group_bottom"]
    group_empties = {}
    for gname in group_names:
        g_obj = bpy.data.objects.new(gname, None)
        g_obj.empty_display_type = 'ARROWS'
        g_obj.empty_display_size = 10.0
        g_obj.parent = laptop_root
        collection.objects.link(g_obj)
        group_empties[gname] = g_obj

    # Tekstur Roughness Noise untuk Bodi Aluminium Matte
    roughness_noise_img = create_body_roughness_image()

    # Warna Sesuai Laptop Asli
    teal_body_rgba = hex_to_linear_rgba("#2f4a57")
    black_key_rgba = hex_to_linear_rgba("#111214")
    black_bezel_rgba = hex_to_linear_rgba("#111214")

    materials = {
        "lid_cover":     create_pbr_material("mat_lid_cover", teal_body_rgba, metallic=0.60, roughness=0.55, roughness_img=roughness_noise_img),
        "display_bezel": create_pbr_material("mat_display_bezel", black_bezel_rgba, metallic=0.05, roughness=0.65),
        "display_panel": create_pbr_material("mat_display_panel", hex_to_linear_rgba("#0c0f14"), metallic=0.05, roughness=0.08),
        "webcam_module": create_pbr_material("mat_webcam_module", hex_to_linear_rgba("#0a0c10"), metallic=0.50, roughness=0.20),
        "keyboard_deck": create_pbr_material("mat_keyboard_deck", teal_body_rgba, metallic=0.60, roughness=0.55, roughness_img=roughness_noise_img),
        "keycaps":       create_pbr_material("mat_keycaps", black_key_rgba, metallic=0.05, roughness=0.60),
        "touchpad":      create_pbr_material("mat_touchpad", teal_body_rgba, metallic=0.55, roughness=0.50, roughness_img=roughness_noise_img),
        "hinge_left":    create_pbr_material("mat_hinge_left", hex_to_linear_rgba("#9aa3ad"), metallic=0.90, roughness=0.28),
        "hinge_right":   create_pbr_material("mat_hinge_right", hex_to_linear_rgba("#9aa3ad"), metallic=0.90, roughness=0.28),
        "motherboard":   create_pbr_material("mat_motherboard", hex_to_linear_rgba("#123522"), metallic=0.25, roughness=0.42),
        "cpu_heatsink":  create_pbr_material("mat_cpu_heatsink", hex_to_linear_rgba("#c86d3b"), metallic=0.90, roughness=0.26),
        "fan":           create_pbr_material("mat_fan", hex_to_linear_rgba("#1c1e22"), metallic=0.30, roughness=0.45),
        "battery":       create_pbr_material("mat_battery", hex_to_linear_rgba("#23262b"), metallic=0.12, roughness=0.55),
        "ssd_m2":        create_pbr_material("mat_ssd_m2", hex_to_linear_rgba("#162836"), metallic=0.35, roughness=0.35),
        "ram_module":    create_pbr_material("mat_ram_module", hex_to_linear_rgba("#163d26"), metallic=0.35, roughness=0.35),
        "speaker_left":  create_pbr_material("mat_speaker_left", hex_to_linear_rgba("#1e2026"), metallic=0.35, roughness=0.45),
        "speaker_right": create_pbr_material("mat_speaker_right", hex_to_linear_rgba("#1e2026"), metallic=0.35, roughness=0.45),
        "bottom_case":   create_pbr_material("mat_bottom_case", teal_body_rgba, metallic=0.60, roughness=0.55, roughness_img=roughness_noise_img),
        "rubber_feet":   create_pbr_material("mat_rubber_feet", hex_to_linear_rgba("#121316"), metallic=0.00, roughness=0.92),
        "screws":        create_pbr_material("mat_screws", hex_to_linear_rgba("#c8d0d8"), metallic=0.92, roughness=0.22),
    }

    created_objects = []
    g_disp = group_empties["group_display"]
    created_objects.append(build_lid_cover(materials["lid_cover"], g_disp, collection))
    created_objects.append(build_display_bezel(materials["display_bezel"], g_disp, collection))
    created_objects.append(build_display_panel(materials["display_panel"], g_disp, collection))
    created_objects.append(build_webcam_module(materials["webcam_module"], g_disp, collection))

    g_top = group_empties["group_top_case"]
    created_objects.append(build_keyboard_deck(materials["keyboard_deck"], g_top, collection))
    created_objects.append(build_keycaps(materials["keycaps"], g_top, collection))
    created_objects.append(build_touchpad(materials["touchpad"], g_top, collection))
    created_objects.append(build_hinge_left(materials["hinge_left"], g_top, collection))
    created_objects.append(build_hinge_right(materials["hinge_right"], g_top, collection))

    g_int = group_empties["group_internals"]
    created_objects.append(build_motherboard(materials["motherboard"], g_int, collection))
    created_objects.append(build_cpu_heatsink(materials["cpu_heatsink"], g_int, collection))
    created_objects.append(build_fan(materials["fan"], g_int, collection))
    created_objects.append(build_battery(materials["battery"], g_int, collection))
    created_objects.append(build_ssd_m2(materials["ssd_m2"], g_int, collection))
    created_objects.append(build_ram_module(materials["ram_module"], g_int, collection))
    created_objects.append(build_speaker_left(materials["speaker_left"], g_int, collection))
    created_objects.append(build_speaker_right(materials["speaker_right"], g_int, collection))

    g_bot = group_empties["group_bottom"]
    created_objects.append(build_bottom_case(materials["bottom_case"], g_bot, collection))
    created_objects.append(build_rubber_feet(materials["rubber_feet"], g_bot, collection))
    created_objects.append(build_screws(materials["screws"], g_bot, collection))

    total_triangles = 0
    total_verts = 0
    print("\n✓ BERHASIL MEMBUAT 20 KOMPONEN:")
    for obj in created_objects:
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        verts = len(obj.data.vertices)
        total_triangles += tris
        total_verts += verts
        print(f"  • {obj.name:<16} | Tris: {tris:>6} | Dir: {obj['explode_dir']} | Dist: {obj['explode_dist']}")

    print("-" * 70)
    print(f"Total Komponen : {len(created_objects)} objek")
    print(f"Total Vertex   : {total_verts:,}")
    print(f"Total Segitiga : {total_triangles:,} tris (Target < 150,000 tris)")
    print("-" * 70)

    if export_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
        export_path = os.path.join(script_dir, OUTPUT_FILENAME)

    export_kwargs = {
        'filepath': export_path,
        'export_format': 'GLB',
        'export_yup': True,
        'export_materials': 'EXPORT',
        'export_extras': True,
        'export_apply': True,
    }
    if ENABLE_DRACO_COMPRESSION:
        export_kwargs['export_draco_mesh_compression_enable'] = True

    bpy.ops.export_scene.gltf(**export_kwargs)
    print(f"✓ File GLB tersimpan di: {export_path}")


if __name__ == "__main__":
    generate_advan_workplus_air()
