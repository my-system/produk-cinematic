import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'fs';

// Polyfill FileReader for Node.js
class FileReaderPolyfill {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((buf) => {
      this.result = buf;
      if (this.onload) this.onload({ target: this });
      if (this.onloadend) this.onloadend({ target: this });
    });
  }
}
globalThis.FileReader = FileReaderPolyfill;

console.log('Generating Authentic Advan Workplus Air GLB (#2f4a57 Matte Teal, Beveled, Concave Keycaps)...');

function prepGeom(geom, tx = 0, ty = 0, tz = 0) {
  const g = geom.index ? geom.toNonIndexed() : geom.clone();
  if (tx !== 0 || ty !== 0 || tz !== 0) {
    g.translate(tx, ty, tz);
  }
  g.computeVertexNormals();
  g.normalizeNormals();
  if (!g.attributes.uv) {
    const count = g.attributes.position.count;
    g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(count * 2), 2));
  }
  for (const key of Object.keys(g.attributes)) {
    if (key !== 'position' && key !== 'normal' && key !== 'uv') {
      g.deleteAttribute(key);
    }
  }
  return g;
}

function mergeParts(geoms) {
  const merged = BufferGeometryUtils.mergeGeometries(geoms, false);
  merged.computeVertexNormals();
  merged.normalizeNormals();
  return merged;
}

function applyPlanarUV(geom, width, depth, flipV = false) {
  const pos = geom.attributes.position;
  const uv = geom.attributes.uv;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const u = Math.max(0, Math.min(1, (x + width / 2) / width));
    let v = Math.max(0, Math.min(1, (z + depth / 2) / depth));
    if (flipV) v = 1.0 - v;
    uv.setXY(i, u, v);
  }
  uv.needsUpdate = true;
  return geom;
}

// Rounded Box with Bevel (0.05 cm, 2-3 segments)
function createRoundedBox(w, h, d, r, bevel = 0.05, curveSegments = 6, bevelSegments = 2) {
  const shape = new THREE.Shape();
  const radius = Math.min(r, w * 0.45, d * 0.45);
  const hw = w / 2 - radius;
  const hd = d / 2 - radius;

  shape.moveTo(-hw, -hd - radius);
  shape.lineTo(hw, -hd - radius);
  shape.absarc(hw, -hd, radius, -Math.PI / 2, 0, false);
  shape.lineTo(hw + radius, hd);
  shape.absarc(hw, hd, radius, 0, Math.PI / 2, false);
  shape.lineTo(-hw, hd + radius);
  shape.absarc(-hw, hd, radius, Math.PI / 2, Math.PI, false);
  shape.lineTo(-hw - radius, -hd);
  shape.absarc(-hw, -hd, radius, Math.PI, Math.PI * 1.5, false);

  const bSize = Math.min(bevel, radius * 0.35, h * 0.35);
  const extrudeSettings = {
    depth: Math.max(0.01, h - bSize * 2),
    bevelEnabled: bSize > 0.002,
    bevelSegments: bevelSegments,
    steps: 1,
    bevelSize: bSize,
    bevelThickness: bSize,
    curveSegments: curveSegments
  };

  const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
  geom.center();
  geom.rotateX(Math.PI / 2);
  return prepGeom(geom);
}

// Concave Keycap Geometry (rounded corners + subtle concave dish on top surface)
function createConcaveKeycap(w, h, d, r = 0.14, dishDepth = 0.016) {
  const geom = createRoundedBox(w, h, d, r, 0.02, 4, 2);
  const pos = geom.attributes.position;
  const hw = Math.max(0.01, w * 0.45);
  const hd = Math.max(0.01, d * 0.45);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    if (y > 0) {
      const nx = Math.min(1, Math.abs(x) / hw);
      const nz = Math.min(1, Math.abs(z) / hd);
      const radial = Math.min(1, nx * nx + nz * nz);
      const dip = (1.0 - radial) * dishDepth;
      pos.setY(i, y - dip);
    }
  }
  geom.computeVertexNormals();
  geom.normalizeNormals();
  return geom;
}

// Hollow Frame Rounded Box (for display bezel)
function createFrameRoundedBox(outerW, outerD, innerW, innerD, innerOffsetZ, h, r) {
  const shape = new THREE.Shape();
  const hw = outerW / 2 - r;
  const hd = outerD / 2 - r;

  shape.moveTo(-hw, -hd - r);
  shape.lineTo(hw, -hd - r);
  shape.absarc(hw, -hd, r, -Math.PI / 2, 0, false);
  shape.lineTo(hw + r, hd);
  shape.absarc(hw, hd, r, 0, Math.PI / 2, false);
  shape.lineTo(-hw, hd + r);
  shape.absarc(-hw, hd, r, Math.PI / 2, Math.PI, false);
  shape.lineTo(-hw - r, -hd);
  shape.absarc(-hw, -hd, r, Math.PI, Math.PI * 1.5, false);

  const hole = new THREE.Path();
  const ihw = innerW / 2;
  const ihd = innerD / 2;
  const oz = innerOffsetZ;
  hole.moveTo(-ihw, -ihd + oz);
  hole.lineTo(ihw, -ihd + oz);
  hole.lineTo(ihw, ihd + oz);
  hole.lineTo(-ihw, ihd + oz);
  hole.lineTo(-ihw, -ihd + oz);
  shape.holes.push(hole);

  const geom = new THREE.ExtrudeGeometry(shape, {
    depth: h,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 1,
    bevelSize: 0.02,
    bevelThickness: 0.02,
    curveSegments: 6
  });
  geom.center();
  geom.rotateX(Math.PI / 2);
  return prepGeom(geom);
}

// Authentic Materials matching the real Advan Workplus Air (#2f4a57 matte teal, #111214 black keycaps/bezel)
const matTealBody = new THREE.MeshStandardMaterial({
  name: 'mat_aluminum_body',
  color: 0x2f4a57,
  metalness: 0.60,
  roughness: 0.55
});

const matDarkBezel = new THREE.MeshStandardMaterial({
  name: 'mat_dark_bezel',
  color: 0x111214,
  metalness: 0.05,
  roughness: 0.65
});

const matScreenGlass = new THREE.MeshStandardMaterial({
  name: 'mat_screen_glass',
  color: 0x0e1218,
  metalness: 0.05,
  roughness: 0.08
});

const matWebcam = new THREE.MeshStandardMaterial({
  name: 'mat_webcam',
  color: 0x0a0c10,
  metalness: 0.50,
  roughness: 0.20
});

const matKeycaps = new THREE.MeshStandardMaterial({
  name: 'mat_keycaps',
  color: 0x111214,
  metalness: 0.05,
  roughness: 0.60
});

const matTouchpad = new THREE.MeshStandardMaterial({
  name: 'mat_touchpad',
  color: 0x2f4a57,
  metalness: 0.55,
  roughness: 0.52
});

const matCopper = new THREE.MeshStandardMaterial({
  name: 'mat_copper',
  color: 0xc86d3b,
  metalness: 0.90,
  roughness: 0.26
});

const matFan = new THREE.MeshStandardMaterial({
  name: 'mat_fan',
  color: 0x1c1e22,
  metalness: 0.30,
  roughness: 0.45
});

const matMotherboard = new THREE.MeshStandardMaterial({
  name: 'mat_motherboard',
  color: 0x113220,
  metalness: 0.25,
  roughness: 0.42
});

const matSteel = new THREE.MeshStandardMaterial({
  name: 'mat_steel',
  color: 0xb8c0c8,
  metalness: 0.90,
  roughness: 0.25
});

const matRubber = new THREE.MeshStandardMaterial({
  name: 'mat_rubber',
  color: 0x121316,
  metalness: 0.0,
  roughness: 0.92
});

const matBattery = new THREE.MeshStandardMaterial({
  name: 'mat_battery',
  color: 0x23262b,
  metalness: 0.12,
  roughness: 0.55
});

const matSSD = new THREE.MeshStandardMaterial({
  name: 'mat_ssd',
  color: 0x162836,
  metalness: 0.35,
  roughness: 0.35
});

const matRAM = new THREE.MeshStandardMaterial({
  name: 'mat_ram',
  color: 0x163d26,
  metalness: 0.35,
  roughness: 0.35
});

const matSpeaker = new THREE.MeshStandardMaterial({
  name: 'mat_speaker',
  color: 0x1e2026,
  metalness: 0.35,
  roughness: 0.45
});

// Root & Hierarchy Groups
const laptop_root = new THREE.Group();
laptop_root.name = 'laptop_root';

const group_display = new THREE.Group();
group_display.name = 'group_display';

const group_top_case = new THREE.Group();
group_top_case.name = 'group_top_case';

const group_internals = new THREE.Group();
group_internals.name = 'group_internals';

const group_bottom = new THREE.Group();
group_bottom.name = 'group_bottom';

laptop_root.add(group_display, group_top_case, group_internals, group_bottom);

function makeMesh(name, geom, mat, explodeDir, explodeDist, parentGroup, pos = [0, 0, 0]) {
  const mesh = new THREE.Mesh(geom, mat.clone());
  mesh.name = name;
  mesh.position.set(pos[0], pos[1], pos[2]);
  mesh.userData.explode_dir = explodeDir; // Blender Z-up coordinates
  mesh.userData.explode_dist = explodeDist;
  parentGroup.add(mesh);
  return mesh;
}

// =============================================================
// 1. GROUP DISPLAY (Evenly spaced vertical explode layers)
// =============================================================
// 1.1 lid_cover (Plain matte teal lid, subtle small ADVAN badge at top-right corner)
{
  const parts = [
    createRoundedBox(31.2, 0.24, 21.8, 0.60, 0.05, 6, 2),
    // Subtle top-right corner ADVAN emblem plate (x: +10.2, z: -4.8)
    createRoundedBox(3.8, 0.02, 0.55, 0.08, 0.005, 3, 1).translate(10.2, 0.125, -4.8)
  ];
  const lidGeom = mergeParts(parts);
  lidGeom.center();
  applyPlanarUV(lidGeom, 31.2, 21.8, false);
  makeMesh('lid_cover', lidGeom, matTealBody, [0.0, 0.15, 1.0], 11.0, group_display, [0, 1.38, 0]);
}

// 1.2 display_bezel (Matte black frame #111214)
{
  const bezelGeom = createFrameRoundedBox(31.1, 21.7, 29.6, 18.5, 0.45, 0.08, 0.55);
  applyPlanarUV(bezelGeom, 31.1, 21.7, false);
  makeMesh('display_bezel', bezelGeom, matDarkBezel, [0.0, 0.15, 1.0], 9.2, group_display, [0, 1.24, 0]);
}

// 1.3 display_panel (14" 16:10 dark glass panel)
{
  const w = 29.6, h = 0.06, d = 18.5;
  const panelGeom = prepGeom(new THREE.BoxGeometry(w, h, d));
  applyPlanarUV(panelGeom, w, d, false);
  makeMesh('display_panel', panelGeom, matScreenGlass, [0.0, 0.15, 1.0], 7.4, group_display, [0, 1.24, 0.45]);
}

// 1.4 webcam_module
{
  const parts = [
    createRoundedBox(3.2, 0.06, 0.45, 0.08, 0.01, 3, 1),
    prepGeom(new THREE.CylinderGeometry(0.14, 0.14, 0.10, 14), 0, -0.03, 0),
    prepGeom(new THREE.CylinderGeometry(0.05, 0.05, 0.10, 10), 0.45, -0.03, 0),
    prepGeom(new THREE.CylinderGeometry(0.04, 0.04, 0.10, 10), -1.1, -0.03, 0),
    prepGeom(new THREE.CylinderGeometry(0.04, 0.04, 0.10, 10), 1.1, -0.03, 0)
  ];
  makeMesh('webcam_module', mergeParts(parts), matWebcam, [0.0, 0.2, 1.0], 10.1, group_display, [0, 1.25, -10.25]);
}

// =============================================================
// 2. GROUP TOP CASE (Keyboard Deck, Concave Keycaps, Touchpad, Hinges)
// =============================================================
// 2.1 keyboard_deck (With recessed keyboard well, recessed touchpad border, and side USB-C/USB-A/HDMI/Audio ports)
{
  const audioCyl = new THREE.CylinderGeometry(0.15, 0.15, 0.24, 12);
  audioCyl.rotateZ(Math.PI / 2);

  const parts = [
    // Main base floor of C-shell
    createRoundedBox(31.2, 0.42, 21.8, 0.60, 0.05, 6, 2).translate(0, -0.08, 0),
    // Palmrest left and right of touchpad
    createRoundedBox(9.5, 0.18, 10.6, 0.45, 0.03, 4, 2).translate(-10.8, 0.18, 5.55),
    createRoundedBox(9.5, 0.18, 10.6, 0.45, 0.03, 4, 2).translate(10.8, 0.18, 5.55),
    // Strip above and below touchpad to form recessed touchpad well
    prepGeom(new THREE.BoxGeometry(12.2, 0.18, 1.5), 0, 0.18, 1.0),
    prepGeom(new THREE.BoxGeometry(12.2, 0.18, 1.4), 0, 0.18, 10.15),
    // Rear strip above keyboard
    createRoundedBox(31.1, 0.18, 1.5, 0.4, 0.03, 4, 2).translate(0, 0.18, -10.1),
    // Left & right border strips beside keyboard
    prepGeom(new THREE.BoxGeometry(1.6, 0.18, 9.6), -14.75, 0.18, -4.55),
    prepGeom(new THREE.BoxGeometry(1.6, 0.18, 9.6), 14.75, 0.18, -4.55),
    // Left Side Ports: HDMI + 2x USB-C 3.2
    prepGeom(new THREE.BoxGeometry(0.24, 0.16, 1.35), -15.52, -0.04, -7.2),
    prepGeom(new THREE.BoxGeometry(0.24, 0.11, 0.80), -15.52, -0.04, -5.2),
    prepGeom(new THREE.BoxGeometry(0.24, 0.11, 0.80), -15.52, -0.04, -3.5),
    // Right Side Ports: USB-A 3.2 + 3.5mm Audio Jack + USB-C 2.0
    prepGeom(new THREE.BoxGeometry(0.24, 0.18, 1.30), 15.52, -0.04, -6.8),
    prepGeom(audioCyl, 15.52, -0.04, -4.8),
    prepGeom(new THREE.BoxGeometry(0.24, 0.11, 0.80), 15.52, -0.04, -3.3)
  ];
  const deckGeom = mergeParts(parts);
  deckGeom.center();
  applyPlanarUV(deckGeom, 31.2, 21.8, false);
  makeMesh('keyboard_deck', deckGeom, matTealBody, [0.0, 0.0, 1.0], 2.0, group_top_case, [0, 0.82, 0]);
}

// 2.2 keycaps (82 black keys with slightly concave top surface, rounded corners, clear gaps)
{
  const keyParts = [];
  const kh = 0.14;
  const totalW = 27.6;
  const totalD = 9.4;

  // Row 0: Function keys (16 keys)
  const r0Z = -4.15;
  for (let i = 0; i < 16; i++) {
    const x = -13.0 + i * 1.733;
    keyParts.push(createConcaveKeycap(1.48, kh, 0.82, 0.12, 0.012).translate(x, 0, r0Z));
  }

  // Row 1: Numbers + Backspace
  const r1Z = -2.75;
  for (let i = 0; i < 13; i++) {
    const x = -12.95 + i * 1.88;
    keyParts.push(createConcaveKeycap(1.60, kh, 1.34, 0.14, 0.016).translate(x, 0, r1Z));
  }
  keyParts.push(createConcaveKeycap(2.76, kh, 1.34, 0.14, 0.016).translate(12.35, 0, r1Z));

  // Row 2: Tab + QWERTY
  const r2Z = -1.12;
  keyParts.push(createConcaveKeycap(2.42, kh, 1.34, 0.14, 0.016).translate(-12.55, 0, r2Z));
  for (let i = 0; i < 12; i++) {
    const x = -10.35 + i * 1.88;
    keyParts.push(createConcaveKeycap(1.60, kh, 1.34, 0.14, 0.016).translate(x, 0, r2Z));
  }
  keyParts.push(createConcaveKeycap(2.12, kh, 1.34, 0.14, 0.016).translate(12.68, 0, r2Z));

  // Row 3: CapsLock + ASDF + Enter
  const r3Z = 0.51;
  keyParts.push(createConcaveKeycap(2.86, kh, 1.34, 0.14, 0.016).translate(-12.32, 0, r3Z));
  for (let i = 0; i < 11; i++) {
    const x = -9.9 + i * 1.88;
    keyParts.push(createConcaveKeycap(1.60, kh, 1.34, 0.14, 0.016).translate(x, 0, r3Z));
  }
  keyParts.push(createConcaveKeycap(3.56, kh, 1.34, 0.14, 0.016).translate(11.95, 0, r3Z));

  // Row 4: Shift + ZXCV + Shift
  const r4Z = 2.14;
  keyParts.push(createConcaveKeycap(3.76, kh, 1.34, 0.14, 0.016).translate(-11.87, 0, r4Z));
  for (let i = 0; i < 10; i++) {
    const x = -8.98 + i * 1.88;
    keyParts.push(createConcaveKeycap(1.60, kh, 1.34, 0.14, 0.016).translate(x, 0, r4Z));
  }
  keyParts.push(createConcaveKeycap(4.50, kh, 1.34, 0.14, 0.016).translate(11.48, 0, r4Z));

  // Row 5: Modifiers, Spacebar, Arrow Cluster
  const r5Z = 3.82;
  keyParts.push(createConcaveKeycap(2.06, kh, 1.44, 0.14, 0.015).translate(-12.72, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.66, kh, 1.44, 0.14, 0.015).translate(-10.55, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.66, kh, 1.44, 0.14, 0.015).translate(-8.58, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.66, kh, 1.44, 0.14, 0.015).translate(-6.60, 0, r5Z));
  keyParts.push(createConcaveKeycap(9.22, kh, 1.44, 0.16, 0.010).translate(-0.82, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.66, kh, 1.44, 0.14, 0.015).translate(4.95, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.66, kh, 1.44, 0.14, 0.015).translate(6.92, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.64, kh, 1.44, 0.14, 0.015).translate(8.92, 0, r5Z));
  keyParts.push(createConcaveKeycap(1.64, kh, 0.66, 0.10, 0.010).translate(10.88, 0, r5Z - 0.39));
  keyParts.push(createConcaveKeycap(1.64, kh, 0.66, 0.10, 0.010).translate(10.88, 0, r5Z + 0.39));
  keyParts.push(createConcaveKeycap(1.64, kh, 1.44, 0.14, 0.015).translate(12.84, 0, r5Z));

  const mergedKeys = mergeParts(keyParts);
  mergedKeys.center();
  applyPlanarUV(mergedKeys, totalW, totalD, false);
  makeMesh('keycaps', mergedKeys, matKeycaps, [0.0, 0.0, 1.0], 4.8, group_top_case, [0, 1.06, -4.55]);
}

// 2.3 touchpad (Same matte dark teal #2f4a57 as body, subtle recessed border)
{
  const parts = [
    createRoundedBox(11.6, 0.05, 7.3, 0.26, 0.015, 5, 2),
    createRoundedBox(11.82, 0.03, 7.52, 0.30, 0.01, 5, 1).translate(0, -0.015, 0)
  ];
  const padGeom = mergeParts(parts);
  padGeom.center();
  applyPlanarUV(padGeom, 11.8, 7.5, false);
  makeMesh('touchpad', padGeom, matTouchpad, [0.0, -0.15, 1.0], 3.5, group_top_case, [0, 1.07, 5.55]);
}

// 2.4 hinge_left & hinge_right
{
  const cyl = new THREE.CylinderGeometry(0.24, 0.24, 3.4, 14);
  cyl.rotateZ(Math.PI / 2);
  const hParts = [
    prepGeom(cyl, 0, 0, 0),
    createRoundedBox(3.0, 0.12, 0.9, 0.1, 0.02, 3, 1).translate(0, -0.08, 0.35),
    createRoundedBox(2.6, 0.26, 0.4, 0.08, 0.02, 3, 1).translate(0, 0.10, -0.05)
  ];
  const hGeom = mergeParts(hParts);
  makeMesh('hinge_left', hGeom.clone(), matSteel, [-0.5, 0.0, 0.8], 3.8, group_top_case, [-8.2, 1.08, -10.55]);
  makeMesh('hinge_right', hGeom.clone(), matSteel, [0.5, 0.0, 0.8], 3.8, group_top_case, [8.2, 1.08, -10.55]);
}

// =============================================================
// 3. GROUP INTERNALS (Distinct realistic colors, chips, flat cables, battery label)
// =============================================================
// 3.1 motherboard (Dark green PCB + SoC die + VRM chokes + SMD capacitors + flat FPC ribbon cables)
{
  const parts = [
    createRoundedBox(26.2, 0.12, 10.4, 0.3, 0.02, 4, 1),
    // CPU package & silicon die
    createRoundedBox(3.8, 0.16, 3.8, 0.15, 0.02, 3, 1).translate(0.5, 0.10, -0.8),
    createRoundedBox(2.0, 0.08, 1.4, 0.08, 0.01, 2, 1).translate(0.5, 0.20, -0.8),
    // Chipset & controller ICs
    createRoundedBox(2.0, 0.12, 2.0, 0.1, 0.015, 3, 1).translate(4.8, 0.08, 1.8),
    createRoundedBox(1.5, 0.10, 1.5, 0.1, 0.015, 3, 1).translate(-5.8, 0.08, 2.2),
    // VRM Power Chokes
    ...Array.from({ length: 6 }, (_, i) =>
      createRoundedBox(0.65, 0.22, 0.65, 0.06, 0.015, 2, 1).translate(-2.2, 0.14, -2.5 + i * 0.9)
    ),
    // Flat FPC Ribbon Cables inside chassis
    createRoundedBox(2.2, 0.04, 3.2, 0.08, 0.008, 2, 1).translate(0.0, 0.08, 5.4),
    createRoundedBox(4.4, 0.04, 1.1, 0.08, 0.008, 2, 1).translate(-10.2, 0.08, 3.2),
    // Internal I/O shield housings
    prepGeom(new THREE.BoxGeometry(1.2, 0.26, 1.2), -12.5, 0.14, -2.5),
    prepGeom(new THREE.BoxGeometry(1.0, 0.20, 0.8), -12.5, 0.12, -0.6),
    prepGeom(new THREE.BoxGeometry(1.0, 0.20, 0.8), -12.5, 0.12, 1.1),
    prepGeom(new THREE.BoxGeometry(1.3, 0.26, 1.2), 12.5, 0.14, -2.1)
  ];
  const moboGeom = mergeParts(parts);
  moboGeom.center();
  applyPlanarUV(moboGeom, 26.2, 10.4, false);
  makeMesh('motherboard', moboGeom, matMotherboard, [0.0, 0.0, -1.0], 2.0, group_internals, [0, 0.58, -4.6]);
}

// 3.2 cpu_heatsink (Copper coldplate, dual heatpipes, radiator fins)
{
  const parts = [
    createRoundedBox(4.2, 0.14, 4.2, 0.2, 0.02, 3, 1).translate(3.2, 0, 1.0),
    createRoundedBox(9.8, 0.12, 0.75, 0.15, 0.02, 3, 1).translate(-1.2, 0.04, 0.4),
    createRoundedBox(9.8, 0.12, 0.75, 0.15, 0.02, 3, 1).translate(-1.2, 0.04, 1.6),
    ...Array.from({ length: 24 }, (_, i) =>
      prepGeom(new THREE.BoxGeometry(0.1, 0.34, 1.6), -6.8 + i * 0.26, 0.02, -2.2)
    )
  ];
  const hsGeom = mergeParts(parts);
  hsGeom.center();
  makeMesh('cpu_heatsink', hsGeom, matCopper, [0.0, 0.1, 1.0], 0.8, group_internals, [-3.2, 0.76, -6.2]);
}

// 3.3 fan
{
  const parts = [
    createRoundedBox(6.8, 0.38, 6.8, 1.4, 0.03, 5, 2),
    prepGeom(new THREE.CylinderGeometry(1.15, 1.15, 0.44, 18), 0, 0, 0),
    ...Array.from({ length: 16 }, (_, i) => {
      const ang = (i / 16) * Math.PI * 2;
      const g = new THREE.BoxGeometry(0.12, 0.40, 1.3);
      g.rotateY(ang + 0.35);
      return prepGeom(g, Math.cos(ang) * 1.8, 0, Math.sin(ang) * 1.8);
    })
  ];
  const fanGeom = mergeParts(parts);
  fanGeom.center();
  makeMesh('fan', fanGeom, matFan, [-0.2, 0.1, 1.0], 0.2, group_internals, [-9.8, 0.72, -5.6]);
}

// 3.4 battery (3 polymer cells + raised specification label plate + flat cable connector)
{
  const parts = [
    createRoundedBox(8.4, 0.34, 8.8, 0.35, 0.03, 4, 2).translate(-8.8, 0, 0),
    createRoundedBox(8.4, 0.34, 8.8, 0.35, 0.03, 4, 2).translate(0, 0, 0),
    createRoundedBox(8.4, 0.34, 8.8, 0.35, 0.03, 4, 2).translate(8.8, 0, 0),
    // Raised Battery Specification Label Plate
    createRoundedBox(15.5, 0.03, 5.8, 0.18, 0.008, 3, 1).translate(-3.8, 0.18, 0.2),
    // BMS Strip & Flat Connector
    createRoundedBox(26.0, 0.22, 0.7, 0.12, 0.02, 3, 1).translate(0, 0, -4.6),
    createRoundedBox(1.8, 0.08, 0.9, 0.08, 0.01, 2, 1).translate(0, 0.06, -5.1)
  ];
  const batGeom = mergeParts(parts);
  batGeom.center();
  applyPlanarUV(batGeom, 26.0, 9.2, false);
  makeMesh('battery', batGeom, matBattery, [0.0, -0.2, -1.0], 3.8, group_internals, [0, 0.56, 5.2]);
}

// 3.5 ssd_m2
{
  const parts = [
    createRoundedBox(2.2, 0.10, 8.0, 0.12, 0.015, 3, 1),
    createRoundedBox(1.4, 0.12, 1.4, 0.08, 0.015, 2, 1).translate(0, 0.09, -2.4),
    createRoundedBox(1.6, 0.12, 2.0, 0.08, 0.015, 2, 1).translate(0, 0.09, 0.0),
    createRoundedBox(1.6, 0.12, 2.0, 0.08, 0.015, 2, 1).translate(0, 0.09, 2.3)
  ];
  const ssdGeom = mergeParts(parts);
  ssdGeom.center();
  applyPlanarUV(ssdGeom, 2.2, 8.0, false);
  makeMesh('ssd_m2', ssdGeom, matSSD, [0.3, 0.1, -1.0], 1.1, group_internals, [8.2, 0.72, -5.0]);
}

// 3.6 ram_module
{
  const parts = [
    createRoundedBox(6.8, 0.10, 3.0, 0.12, 0.015, 3, 1),
    ...Array.from({ length: 4 }, (_, i) =>
      createRoundedBox(1.1, 0.12, 0.9, 0.06, 0.01, 2, 1).translate(-2.25 + i * 1.5, 0.09, -0.55)
    ),
    ...Array.from({ length: 4 }, (_, i) =>
      createRoundedBox(1.1, 0.12, 0.9, 0.06, 0.01, 2, 1).translate(-2.25 + i * 1.5, 0.09, 0.55)
    )
  ];
  const ramGeom = mergeParts(parts);
  ramGeom.center();
  applyPlanarUV(ramGeom, 6.8, 3.0, false);
  makeMesh('ram_module', ramGeom, matRAM, [0.0, 0.2, -1.0], 0.9, group_internals, [1.2, 0.72, -2.8]);
}

// 3.7 speaker_left & speaker_right
{
  const spkParts = [
    createRoundedBox(2.1, 0.30, 6.4, 0.35, 0.03, 4, 2),
    prepGeom(new THREE.CylinderGeometry(0.65, 0.65, 0.34, 14), 0, 0.02, -1.2),
    prepGeom(new THREE.CylinderGeometry(0.65, 0.65, 0.34, 14), 0, 0.02, 1.2)
  ];
  const spkGeom = mergeParts(spkParts);
  spkGeom.center();
  makeMesh('speaker_left', spkGeom.clone(), matSpeaker, [-0.8, -0.1, -1.0], 2.8, group_internals, [-14.0, 0.58, 5.2]);
  makeMesh('speaker_right', spkGeom.clone(), matSpeaker, [0.8, -0.1, -1.0], 2.8, group_internals, [14.0, 0.58, 5.2]);
}

// =============================================================
// 4. GROUP BOTTOM (Ventilation grille + recessed screw holes)
// =============================================================
// 4.1 bottom_case
{
  const screwCoords = [
    [-14.0, -9.8], [-5.0, -9.8], [5.0, -9.8], [14.0, -9.8],
    [-14.6, 0.0],  [14.6, 0.0],
    [-14.0, 9.8],  [-5.0, 9.8],  [5.0, 9.8],  [14.0, 9.8]
  ];
  const parts = [
    createRoundedBox(31.2, 0.32, 21.8, 0.60, 0.05, 6, 2),
    // Ventilation intake grille slots
    ...Array.from({ length: 22 }, (_, i) =>
      prepGeom(new THREE.BoxGeometry(16.5, 0.35, 0.11), 0, -0.02, -7.8 + i * 0.24)
    ),
    // 10 Screw hole wells on bottom_case
    ...screwCoords.map(([sx, sz]) =>
      prepGeom(new THREE.CylinderGeometry(0.28, 0.28, 0.08, 12), sx, -0.14, sz)
    )
  ];
  const botGeom = mergeParts(parts);
  botGeom.center();
  applyPlanarUV(botGeom, 31.2, 21.8, false);
  makeMesh('bottom_case', botGeom, matTealBody, [0.0, 0.0, -1.0], 6.0, group_bottom, [0, 0.28, 0]);
}

// 4.2 rubber_feet
{
  const feetParts = [
    createRoundedBox(24.5, 0.12, 0.75, 0.32, 0.025, 4, 2).translate(0, 0, -9.2),
    createRoundedBox(3.6, 0.12, 0.75, 0.32, 0.025, 4, 2).translate(-11.4, 0, 9.0),
    createRoundedBox(3.6, 0.12, 0.75, 0.32, 0.025, 4, 2).translate(11.4, 0, 9.0)
  ];
  const feetGeom = mergeParts(feetParts);
  feetGeom.center();
  makeMesh('rubber_feet', feetGeom, matRubber, [0.0, 0.0, -1.0], 7.8, group_bottom, [0, 0.08, 0]);
}

// 4.3 screws
{
  const screwCoords = [
    [-14.0, -9.8], [-5.0, -9.8], [5.0, -9.8], [14.0, -9.8],
    [-14.6, 0.0],  [14.6, 0.0],
    [-14.0, 9.8],  [-5.0, 9.8],  [5.0, 9.8],  [14.0, 9.8]
  ];
  const screwParts = [];
  for (const [sx, sz] of screwCoords) {
    screwParts.push(prepGeom(new THREE.CylinderGeometry(0.20, 0.20, 0.08, 12), sx, -0.14, sz));
    screwParts.push(prepGeom(new THREE.CylinderGeometry(0.09, 0.09, 0.34, 10), sx, 0.06, sz));
  }
  const screwsGeom = mergeParts(screwParts);
  screwsGeom.center();
  makeMesh('screws', screwsGeom, matSteel, [0.0, 0.0, -1.0], 9.4, group_bottom, [0, 0.04, 0]);
}

// Count total triangles
let totalTris = 0;
laptop_root.traverse((c) => {
  if (c.isMesh && c.geometry) {
    totalTris += c.geometry.attributes.position.count / 3;
  }
});
console.log(`Total Triangles: ${Math.round(totalTris).toLocaleString()} tris (< 150k target)`);

const exporter = new GLTFExporter();
exporter.parse(
  laptop_root,
  (gltf) => {
    fs.writeFileSync('laptop_advan_workplus_air.glb', Buffer.from(gltf));
    const stats = fs.statSync('laptop_advan_workplus_air.glb');
    console.log(`✓ SUCCESS! Exported laptop_advan_workplus_air.glb (${(stats.size / 1024).toFixed(1)} KB)`);
  },
  (err) => {
    console.error('Export error:', err);
  },
  { binary: true }
);
