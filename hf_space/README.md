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
short_description: Prompt to Blender worker package for Oyen animation
---

# Oyen AI Animation Studio

Gradio interface for turning an animation prompt into a Blender-ready worker package.

## V0.2

- Create `animation_job.json` from a story prompt.
- Generate a standalone `oyen_blender_scene.py`.
- Download a ZIP with Windows and Linux/macOS launchers.
- Build a procedural Oyen placeholder, animated camera, lighting, `.blend`, and MP4 preview.
- Follow the headless Blender execution pattern used by the main `blender-mcp` codebase.

The Hugging Face ZeroGPU Space prepares the package. Blender itself runs on a local computer or remote worker where Blender is installed.
