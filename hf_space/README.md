---
title: Oyen Purba 3D Rig Studio
emoji: 🐈
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: mit
short_description: Render Oyen Purba with a real Blender armature to MP4 and .blend
---

# Oyen Purba 3D Rig Studio

Gradio interface that turns a story prompt into a Blender-rendered animation of **Oyen Purba**, the permanent main character.

## V0.4 — 3D Rig V1

- Build Oyen Purba from the official brand design and colors.
- Create a real Blender armature with 28 bones.
- Rig the body, head, jaw, eyes, ears, arms, legs, paws, and five-part tail.
- Animate walking/running, body bounce, jumping, reactions, jaw, blinking, and tail motion from prompt keywords.
- Render an MP4 directly inside the Space.
- Download the `.blend` file containing the editable armature.
- Validate both the rig marker and MP4 before GitHub receives a green deployment status.

Rig V1 uses segmented bone parenting for reliable automatic rendering. A unified deformation mesh, retopology, weight painting, IK controls, and facial shape keys are planned for Rig V2.
