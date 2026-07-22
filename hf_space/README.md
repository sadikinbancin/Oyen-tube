---
title: Oyen AI Animation Studio
emoji: 🐈
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: mit
short_description: Prompt to animation plan for the Oyen Blender pipeline
---

# Oyen AI Animation Studio

Gradio interface for planning Oyen animations before they are executed by the Blender automation pipeline.

## V0.1

- Create an `animation_job.json` from a story prompt.
- Choose 2D Grease Pencil or 3D Blender mode.
- Configure duration, FPS, aspect ratio, resolution, visual style, and audio preparation.
- Download the generated production plan.

The Blender renderer is not executed inside this Space yet. ZeroGPU will be used later for PyTorch-based AI tasks, while Blender rendering will run through a separate worker.
