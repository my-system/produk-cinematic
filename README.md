# 3D Laptop Advan Workplus Air - Exploded View (Blender & Three.js)

Proyek ini menyediakan skrip prosedural Blender Python (`bpy`) untuk menghasilkan model 3D laptop **Advan Workplus Air** dengan 20 komponen terpisah berorientasi efek *exploded view*, pivot di pusat massa, material PBR individu, hierarki *Empty parent*, serta ekspor otomatis ke file glTF/GLB (`laptop_advan_workplus_air.glb`).

---

## 📁 Struktur Berkas

```
PRODUK CINEMATIC/
├── generate_laptop_advan_workplus_air.py  # Skrip Blender Python (bpy) pembuat 3D & auto-export GLB
├── index.html                             # Web Viewer Three.js interaktif (Slider & Auto-Play Explode)
└── README.md                              # Dokumentasi panduan teknis
```

---

## 💻 Spesifikasi Model 3D

- **Dimensi Tertutup**: 312 x 218 x 16 mm (31.2 x 21.8 x 1.6 cm).
- **Layar**: 14.0 inci rasio 16:10 (*active panel* ~29.4 x 18.4 cm).
- **Skala**: 1 unit Blender = 1 cm.
- **Bodi**: Ramping (*ultra-slim*), sudut membulat (*filleted corners*), warna *silver/space grey*, material *brushed aluminum alloy*.
- **Pusat Massa (Origin)**: Setiap objek memiliki titik pivot (*origin*) tepat di pusat geometrinya (`ORIGIN_GEOMETRY`), sehingga dapat berotasi dan bergerak secara alami.
- **Budget Poligon**: ~25.000 – 35.000 segitiga (*well below* target 150k tris), shading smooth dengan auto smooth normals.

---

## 🧩 Daftar 20 Komponen & Hierarki Objek

Model diatur rapi dalam struktur hierarki menggunakan **Empty Objects**:

```
laptop_root (Empty)
├── group_display (Empty)
│   ├── lid_cover        (Punggung layar aluminium brushed + aksen logo Advan)
│   ├── display_bezel    (Bingkai layar tipis rasio 16:10)
│   ├── display_panel    (Kaca panel IPS 14.0 inci glossy)
│   └── webcam_module    (Modul kamera HD, sensor, & dual mic)
│
├── group_top_case (Empty)
│   ├── keyboard_deck    (C-shell aluminium dengan well keyboard & port I/O)
│   ├── keycaps          (Tombol chiclet lengkap 6 baris: F1-F12, QWERTY, Space, Panah)
│   ├── touchpad         (Plat kaca satin presisi 12.0 x 7.6 cm)
│   ├── hinge_left       (Engsel baja kiri)
│   └── hinge_right      (Engsel baja kanan)
│
├── group_internals (Empty)
│   ├── motherboard      (PCB utama hitam/gelap + socket CPU, chipset, chokes, port)
│   ├── cpu_heatsink     (Vapor chamber tembaga + dual heatpipe + sirip radiator)
│   ├── fan              (Rumah kipas blower sentrifugal + 14 bilah sudu turbin)
│   ├── battery          (Baterai 3-sel polimer tipis + BMS connector)
│   ├── ssd_m2           (Modul NVMe M.2 2280 dengan controller & NAND flash)
│   ├── ram_module       (Modul SO-DIMM dengan deretan 8 chip DRAM BGA)
│   ├── speaker_left     (Unit modul speaker akustik kiri)
│   └── speaker_right    (Unit modul speaker akustik kanan)
│
└── group_bottom (Empty)
    ├── bottom_case      (D-shell aluminium dengan kisi-kisi ventilasi kipas)
    ├── rubber_feet      (4 bantalan karet anti-slip)
    └── screws           (10 baut sasis bawah dengan kepala Torx/Phillips)
```

---

## 🎨 Material PBR (Principled BSDF)

Setiap komponen memiliki material sendiri dengan parameter:
- **Aluminium Brushed** (`mat_lid_cover`, `mat_keyboard_deck`, `mat_bottom_case`): Base Color [0.73, 0.74, 0.76], Metallic: 0.90–0.92, Roughness: 0.30–0.34.
- **Display Glass** (`mat_display_panel`): Deep black mirror [0.015, 0.018, 0.022], Metallic: 0.08, Roughness: 0.06.
- **Tembaga Heatsink** (`mat_cpu_heatsink`): Base Color [0.88, 0.48, 0.28], Metallic: 0.96, Roughness: 0.22.
- **Keycaps & Fan** (`mat_keycaps`, `mat_fan`): Matte dark charcoal [0.08–0.12], Metallic: 0.05, Roughness: 0.45–0.55.
- **Baja Engsel & Baut** (`mat_hinge_*`, `mat_screws`): High metallic steel [0.82–0.98], Roughness: 0.18–0.22.

---

## 🚀 Cara Menjalankan Skrip di Blender

### Opsi 1: Lewat GUI Blender (Paling Mudah)
1. Buka aplikasi **Blender** (versi 3.0 ke atas, disarankan 3.6 LTS, 4.1, atau 4.2+).
2. Masuk ke tab **Scripting** pada bagian atas layar.
3. Klik tombol **Open** (Buka), lalu pilih berkas `generate_laptop_advan_workplus_air.py`.
4. Klik tombol **Run Script** (ikon ▶) atau tekan shortcut `Alt + P`.
5. Model 3D akan langsung terbuat di 3D Viewport dan otomatis diekspor menjadi file:
   `laptop_advan_workplus_air.glb`.

### Opsi 2: Lewat Command Line (Headless / Background Mode)
Jika Anda memiliki executable Blender di terminal / command prompt:
```bash
blender -b -P generate_laptop_advan_workplus_air.py
```

---

## 🌐 Integrasi ke Three.js (Exploded View)

Skrip Blender menyisipkan custom property ke dalam `node.extras` file GLTF/GLB:
- `explode_dir`: Vektor arah `[x, y, z]` (sudah dinormalisasi).
- `explode_dist`: Jarak pemisahan komponen saat posisi terbuka penuh (*progress* = 1.0).

### Logika Tiga Baris di Three.js:
```javascript
// 1. Simpan posisi awal saat model dimuat
gltf.scene.traverse((child) => {
  if (child.isMesh && child.userData.explode_dir) {
    child.userData.initialPos = child.position.clone();
    child.userData.dir = new THREE.Vector3(...child.userData.explode_dir);
    child.userData.dist = child.userData.explode_dist || 5.0;
  }
});

// 2. Animasikan posisi saat slider/scroll berubah (progress: 0.0 s/d 1.0)
function setExplodeProgress(progress) {
  gltf.scene.traverse((child) => {
    if (child.isMesh && child.userData.initialPos) {
      const offset = child.userData.dir.clone().multiplyScalar(child.userData.dist * progress);
      child.position.copy(child.userData.initialPos).add(offset);
    }
  });
}
```

---

## 🖥 Menjalankan Web Viewer

Buka direktori proyek dan jalankan web server sederhana (agar GLTFLoader dapat memuat berkas GLB):
```bash
# Menggunakan npx serve
npx serve .

# ATAU menggunakan Python
python -m http.server 8000
```
Buka browser di `http://localhost:8000` (atau port yang ditampilkan) untuk menikmati animasi interaktif *exploded view* 3D Advan Workplus Air!
