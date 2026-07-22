---
title: Oyen Purba Motion AI Studio
emoji: 🐈
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.49.1
app_file: app_v04.py
pinned: false
license: mit
short_description: AI motion plans for Oyen Blender animations
---

# Oyen Purba Motion AI Studio

V0.5 converts an Indonesian animation prompt into a validated motion plan, then makes the **Oyen Purba** Blender armature execute that plan.

## Motion AI V0.5

- Gemini structured-output API is used when the Space secret `GEMINI_API_KEY` exists.
- Groq structured-output API is the second provider when `GROQ_API_KEY` exists.
- A local Indonesian prompt parser remains available when neither secret is configured or an API request fails.
- AI output is validated and limited to safe motion clips: idle, walk, run, jump, turn, look, wave, tail wag, surprised, angry, and stop.
- The AI never sends arbitrary Python into Blender.
- Oyen's forward axis is fixed to world **-Y**; X is only left/right, so forward locomotion no longer slides sideways.
- Camera keyframes follow the character's actual path.
- The generated `.blend` includes `Oyen_AI_Motion_Plan.json` and `Oyen_Animation_Job.json` in Blender's Text Editor.

## Character and rig improvements

- 34-bone armature with body, head, jaw, ears, arms, legs and five tail bones.
- IK hand and foot controls with elbow and knee pole targets.
- Flatter eyes, smaller muzzle and fangs, slimmer limbs and a more continuous overlapping tail.
- Prompt-specific anticipation, action, follow-through and settle poses.

## Add an AI provider safely

Open the Hugging Face Space **Settings → Variables and secrets → New secret** and add one of:

```text
GEMINI_API_KEY
```

or:

```text
GROQ_API_KEY
```

Do not place an API key in this repository, the prompt, JSON output, or `.blend` file. Adding a Space secret restarts the app automatically.

Optional non-secret model overrides:

```text
GEMINI_MODEL=gemini-3.6-flash
GROQ_MODEL=openai/gpt-oss-20b
```

Rig V1.1 remains a procedural segmented model. A later Rig V2 will require a unified retopologized mesh, deformation weight painting, IK/FK production controls and facial shape keys for truly polished character animation.
