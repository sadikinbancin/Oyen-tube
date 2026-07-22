# Oyen V0.2 Blender Worker Bridge

V0.2 proves the complete handoff:

```text
Prompt
→ animation_job.json
→ standalone Blender Python
→ Blender headless worker
→ oyen_preview.blend
→ oyen_preview.mp4
```

## Why the worker is separate

The Hugging Face Space uses Gradio and ZeroGPU to prepare AI-side files. Blender rendering needs a Blender executable and is therefore executed on a local machine, self-hosted runner, or later Docker worker.

The runner command follows the same headless pattern used by the forked `sandraschi/blender-mcp` foundation:

```bash
blender --background --factory-startup --enable-autoexec --python oyen_blender_scene.py
```

## Test it

1. Open the Oyen Hugging Face Space.
2. Enter an animation prompt.
3. Select **3D Blender**.
4. Press **Buat Paket Blender**.
5. Download **Worker ZIP**.
6. Extract it on a computer with Blender 4.x.
7. Run `run_blender.bat` or `run_blender.sh`.

The output appears in:

```text
oyen_output/
├── oyen_preview.blend
└── oyen_preview.mp4
```

## Current limitation

The character is still a procedural placeholder made from Blender primitives. The next stage replaces it with the final Oyen model, armature, rig controls, expressions, and lip-sync shapes.
