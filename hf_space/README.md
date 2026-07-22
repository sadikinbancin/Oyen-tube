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
short_description: Prompt to Blender MP4 preview rendered directly in the Space
---

# Oyen AI Animation Studio

Gradio interface that turns an animation prompt into a Blender-rendered MP4 preview.

## V0.3

- Create an `animation_job.json` from a story prompt.
- Generate a procedural Oyen placeholder, lighting, animation, and camera movement.
- Run Blender headlessly inside the Hugging Face Space.
- Show the completed MP4 in the browser and provide a direct MP4 download.
- Provide optional `.blend`, JSON, and Blender log files for debugging.
- Follow the headless Blender execution pattern used by the main `blender-mcp` codebase.

The free preview is intentionally limited to 3–8 seconds, 12–15 FPS, and a maximum of 480p. The final rigged Oyen character and full prompt-aware scene construction will be connected in later versions.
