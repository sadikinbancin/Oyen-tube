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
short_description: Prompt to Blender MP4 rendered directly in the Space
---

# Oyen AI Animation Studio

Gradio interface that turns an animation prompt into a Blender-rendered MP4 preview.

## V0.3

- Create an `animation_job.json` from a story prompt.
- Generate a procedural Oyen placeholder, lighting, animation, and camera movement.
- Run Blender headlessly inside the Hugging Face Space.
- Show the completed `.mp4` in the browser and provide a direct download.
- Provide the generated `.blend`, JSON, Blender script, worker ZIP, and render log.
- Follow the headless execution pattern used by the main `blender-mcp` codebase.

The direct free-tier preview is capped at 15 seconds, 12 FPS, and 35% of the selected project resolution. The Worker ZIP preserves the full project settings up to 60 seconds. The final rigged Oyen model and richer prompt-aware scene construction will be connected in later versions.
