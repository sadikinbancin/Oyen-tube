# Oyen Motion AI V0.5 deployment diagnostics

- Source commit: `22ff726bc68550f4270ae12188563da39717721c`
- Deploy: `success`
- Health: `success`
- Prompt-specific MP4 smoke test: `success`

## oyen-deploy.log
```text
Updated Git hooks.
Git LFS initialized.
Cloning into '/tmp/oyen-hf-space'...
sending incremental file list
./
.gitattributes
README.md
app.py
app_v04.py
oyen_2d_director.py
oyen_2d_motion_library.json
oyen_bridge.py
oyen_motion_ai.py
oyen_rig_v1.py
oyen_runtime.py
packages.txt
requirements.txt
rig_parts/
rig_parts/oyen_rig_v1_01.txt
rig_parts/oyen_rig_v1_02.txt
rig_parts/oyen_rig_v1_03.txt
rig_parts/oyen_rig_v1_04.txt
rig_parts/oyen_rig_v1_04b.txt
rig_parts/oyen_rig_v1_05.txt

sent 117,664 bytes  received 380 bytes  236,088.00 bytes/sec
total size is 116,348  speedup is 0.99
?? oyen_2d_director.py
?? oyen_2d_motion_library.json
[main 528bee7] Deploy Oyen Motion AI V0.5 from GitHub 22ff726
 2 files changed, 594 insertions(+)
 create mode 100644 oyen_2d_director.py
 create mode 100644 oyen_2d_motion_library.json
To https://huggingface.co/spaces/lako123/Belajarh-ani
   5283a75..528bee7  HEAD -> main

```
## oyen-health.log
```text
Oyen Motion AI V0.5 /render_mp4 API is ready.

```
## oyen-smoke.log
```text
Loaded as API: https://lako123-belajarh-ani.hf.space/ ✔
SMOKE_RESULT: ('✅ **Oyen Motion AI V0.5 selesai** — `oyen-20260723-041428-7bf370`  \n🧠 Sutradara gerak: **Local fallback** • klip: `run, look, angry`  \n🦴 Armature: **34 tulang** • arah depan: **−Y** • 5 detik • 12 FPS • 360×640  \nRender 12.4 detik • MP4 0.07 MB • `.blend` berisi motion plan JSON', {'video': '/tmp/gradio/7615439dbe4af6cc14586bae405b5eb104d03f5aecb6792a181b9837234ac175/oyen_preview.mp4', 'subtitles': None}, '/tmp/gradio/7615439dbe4af6cc14586bae405b5eb104d03f5aecb6792a181b9837234ac175/oyen_preview.mp4', '{\n  "schema_version": "oyen.animation-job.v5",\n  "app_version": "0.5.0",\n  "job_id": "oyen-20260723-041428-7bf370",\n  "created_at": "2026-07-23T04:14:28.838419+00:00",\n  "project": {\n    "name": "Oyen Purba AI Motion Studio",\n    "prompt": "Oyen berlari cepat mengejar ayam ke depan, berhenti mendadak, lalu menoleh ke kamera dengan wajah kesal.",\n    "mode": "3D Blender",\n    "style": "Oyen Purba Official",\n    "visual_direction": "short chubby orange tabby hero, large flat amber eyes, Sun Cream muzzle and belly, small friendly fangs, fang necklace, prehistoric loincloth, continuous striped tail",\n    "lighting": "warm cinematic cartoon studio lighting",\n    "main_character": {\n      "name": "Oyen Purba",\n      "rig_version": "Oyen Purba 3D Rig V1.1",\n      "armature": "Oyen_Purba_Rig",\n      "bone_count": 34,\n      "character_forward_axis": "-Y",\n      "controls": [\n        "root/pelvis/spine/chest/neck/head/jaw",\n        "arms, elbows, hands, thighs, knees and feet",\n        "IK hands and feet with elbow/knee pole targets",\n        "five-bone articulated tail"\n      ]\n    }\n  },\n  "ai_motion_director": {\n    "provider": "Local fallback",\n    "note": "Local prompt parser",\n    "plan_embedded_in_blend": true\n  },\n  "motion_plan": {\n    "summary": "Local motion planner fallback",\n    "coordinate_system": {\n      "character_forward": "-Y",\n      "right": "+X",\n      "up": "+Z"\n    },\n    "clips": [\n      {\n        "type": "run",\n        "start": 0.0,\n        "end": 3.6,\n        "direction": "forward",\n        "distance": 3.75,\n        "intensity": 0.9,\n        "target": "ayam"\n      },\n      {\n        "type": "look",\n        "start": 3.6,\n        "end": 4.4,\n        "direction": "none",\n        "distance": 0.0,\n        "intensity": 0.7,\n        "target": "camera"\n      },\n      {\n        "type": "angry",\n        "start": 4.4,\n        "end": 5.0,\n        "direction": "none",\n        "distance": 0.0,\n        "intensity": 0.8,\n        "target": ""\n      }\n    ],\n    "camera": [\n      {\n        "start": 0.0,\n        "end": 5.0,\n        "shot": "medium",\n        "angle": "three_quarter",\n        "follow": true\n      }\n    ]\n  },\n  "timeline": {\n    "duration_seconds": 5,\n    "fps": 12,\n    "total_frames": 60\n  },\n  "render": {\n    "engine": "BLENDER_WORKBENCH",\n    "width": 360,\n    "height": 640,\n    "aspect_ratio": "9:16",\n    "output_format": "FFMPEG_MPEG4",\n    "audio_enabled": false,\n    "preview_resolution_percentage": 100\n  },\n  "worker": {\n    "mode": "huggingface_blender_headless_cpu",\n    "expected_outputs": [\n      "oyen_preview.blend",\n      "oyen_preview.mp4"\n    ]\n  },\n  "pipeline": [\n    "prompt_to_ai_motion_plan",\n    "validate_motion_json",\n    "build_oyen_purba_character",\n    "create_34_bone_armature_and_ik_controls",\n    "execute_prompt_specific_motion_clips",\n    "follow_character_camera",\n    "embed_motion_plan_inside_blend",\n    "save_rigged_blend",\n    "render_mp4",\n    "validate_armature_blend_and_video"\n  ],\n  "status": "ready_to_render_ai_directed_motion",\n  "notes": [\n    "Forward locomotion uses world -Y; X is reserved for left/right movement.",\n    "The AI does not generate unsafe arbitrary Blender Python. It selects validated motion clips.",\n    "Without an API key, a local Indonesian prompt parser remains available.",\n    "Rig V2 will add unified retopology, deformation weights and facial shape keys."\n  ]\n}', '/tmp/gradio/729fc49a48520873fdfd00b1d0c62b919c4c7afa885b1a76956d13301b97e5a5/animation_job.json', '/tmp/gradio/881ec75652127b313008d0b2f920e56d9925f597c654e38c1d9bd20d6b556ad7/oyen_preview.blend', '/tmp/gradio/b52368e4355f1439cbe32134b928a196ba9ea9c2aff5fefcdeadd6ab57220636/blender.log')
OYEN_MOTION_AI_V05_VERIFIED provider=Local fallback clips=['run', 'look', 'angry'] direction=forward forward_axis=-Y mp4_bytes=74058 blend_bytes=3384884

```
