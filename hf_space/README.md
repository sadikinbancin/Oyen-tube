---
title: Oyen Purba 3D Rig Studio
emoji: 🐈
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.49.1
app_file: app_v04.py
pinned: false
license: mit
short_description: Oyen Purba Blender rig with MP4 and blend output
---

# Oyen Purba 3D Rig Studio

This Space renders **Oyen Purba**, the permanent main character, with a real Blender armature.

## V0.4 — Rig V1

- Official orange-tabby Oyen Purba design, fang necklace and prehistoric loincloth.
- A 34-bone armature with body, head, jaw, ears, arms, legs and five tail bones.
- IK hand and foot controls with elbow and knee pole targets.
- Animated gait, body bounce, head acting, jaw, ear twitch, tail follow-through and hand wave.
- Direct MP4 preview in the browser.
- Downloadable `.blend` containing the editable rig.
- Runtime validation rejects the result unless the armature, `.blend` and MP4 all exist.

Rig V1 uses segmented bone parenting for reliable procedural rendering. Rig V2 will focus on a unified retopologized mesh, deformation weight painting, IK/FK controls and facial shape keys.
