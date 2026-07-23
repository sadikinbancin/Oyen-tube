---
title: Oyen Purba 2D Cutout Studio
emoji: 🐈
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.49.1
app_file: app_v04.py
pinned: false
license: mit
short_description: Oyen Purba 2D cutout rig, Action library and AI Motion Director
---

# Oyen Purba 2D Cutout Studio

V0.6 menjalankan pipeline uji **Tahap 1–7** dari brand sheet Oyen Purba:

1. Layer tubuh dan wajah transparan.
2. Pivot anatomis tetap.
3. Armature cutout 2D dengan 26 bone/control.
4. Paket PNG transparan committed dan checksum-protected.
5. Import, depth/Z-order, dan bone parenting otomatis di Blender.
6. Tujuh Action resmi: idle, blink, walk, run, head turn, wave, dan tail wag.
7. AI Motion Director library-only yang menyusun NLA, ekspresi, blink, root motion, kamera, QA, MP4, dan `.blend`.

AI tidak boleh menjalankan Python bebas atau mengarang karakter pengganti. Blender merender lima frame QA sebelum MP4. Space mengembalikan MP4, `.blend`, JSON job, log, serta contact sheet untuk pemeriksaan visual.

Ini adalah **uji cutout 2D pertama**, belum puppet studio-quality. Sudut motion dibuat konservatif agar Oyen tetap dikenali dan sambungan layer tidak mudah terbuka.
