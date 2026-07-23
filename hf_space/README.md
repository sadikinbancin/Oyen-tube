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
short_description: Oyen Purba 2D cutout rig and Motion Director
---

# Oyen Purba 2D Cutout Studio

V0.6 menjalankan pipeline uji **Tahap 1–7** dari brand sheet Oyen Purba:

1. Layer tubuh, wajah, kostum, aksesori, kaki, tangan, dan ekor transparan.
2. Pivot anatomis tetap dari manifest aset.
3. Armature cutout 2D dengan sedikitnya 25 bone/control.
4. Paket PNG transparan committed, dibagi menjadi 12 bagian, dan dilindungi checksum SHA-256.
5. Import, depth/Z-order, material alpha, serta bone parenting otomatis di Blender.
6. Tujuh Action resmi: idle, blink, walk, run, head turn, wave, dan tail wag.
7. AI Motion Director library-only yang menyusun NLA, ekspresi, blink, root motion, kamera, QA, MP4, dan `.blend`.

AI tidak boleh menjalankan Python bebas atau mengarang karakter pengganti. Blender merender lima frame QA sebelum MP4. Runtime menormalisasi keluaran movie Blender lama maupun baru menjadi satu nama MP4 yang stabil. Space mengembalikan MP4, `.blend`, JSON job, log Blender, serta contact sheet untuk pemeriksaan visual.

Ini adalah **uji cutout 2D pertama**, belum puppet studio-quality. Sudut motion dibuat konservatif agar Oyen tetap dikenali dan sambungan layer tidak mudah terbuka.
