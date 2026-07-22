from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

MOTION_TYPES = (
    "idle",
    "walk",
    "run",
    "jump",
    "turn",
    "look",
    "wave",
    "tail_wag",
    "surprised",
    "angry",
    "stop",
)
DIRECTIONS = ("forward", "backward", "left", "right", "none")
CAMERA_SHOTS = ("wide", "medium", "close")
CAMERA_ANGLES = ("front", "three_quarter", "side")

MOTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "clips": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": list(MOTION_TYPES)},
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "direction": {"type": "string", "enum": list(DIRECTIONS)},
                    "distance": {"type": "number"},
                    "intensity": {"type": "number"},
                    "target": {"type": "string"},
                },
                "required": [
                    "type",
                    "start",
                    "end",
                    "direction",
                    "distance",
                    "intensity",
                    "target",
                ],
                "additionalProperties": False,
            },
        },
        "camera": {
            "type": "array",
            "minItems": 1,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "shot": {"type": "string", "enum": list(CAMERA_SHOTS)},
                    "angle": {"type": "string", "enum": list(CAMERA_ANGLES)},
                    "follow": {"type": "boolean"},
                },
                "required": ["start", "end", "shot", "angle", "follow"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "clips", "camera"],
    "additionalProperties": False,
}


def _clamp(value: Any, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _clean_json_text(text: str) -> str:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def _normalise_plan(raw: dict[str, Any], duration: float) -> dict[str, Any]:
    duration = max(1.0, float(duration))
    clips: list[dict[str, Any]] = []
    for raw_clip in raw.get("clips", []):
        if not isinstance(raw_clip, dict):
            continue
        motion_type = str(raw_clip.get("type", "idle")).lower()
        if motion_type not in MOTION_TYPES:
            motion_type = "idle"
        start = _clamp(raw_clip.get("start"), 0.0, duration, 0.0)
        end = _clamp(raw_clip.get("end"), start + 0.1, duration, duration)
        if end <= start:
            end = min(duration, start + 0.25)
        direction = str(raw_clip.get("direction", "none")).lower()
        if direction not in DIRECTIONS:
            direction = "none"
        distance = _clamp(raw_clip.get("distance"), 0.0, 8.0, 0.0)
        intensity = _clamp(raw_clip.get("intensity"), 0.15, 1.0, 0.65)
        target = str(raw_clip.get("target", ""))[:80]
        clips.append(
            {
                "type": motion_type,
                "start": round(start, 3),
                "end": round(end, 3),
                "direction": direction,
                "distance": round(distance, 3),
                "intensity": round(intensity, 3),
                "target": target,
            }
        )

    if not clips:
        clips = _fallback_plan("", duration)["clips"]

    clips.sort(key=lambda item: (item["start"], item["end"]))
    for index, clip in enumerate(clips):
        if index == 0:
            clip["start"] = 0.0
        else:
            clip["start"] = max(clip["start"], clips[index - 1]["end"])
        clip["end"] = max(clip["start"] + 0.1, min(duration, clip["end"]))
    clips[-1]["end"] = duration

    camera: list[dict[str, Any]] = []
    for raw_camera in raw.get("camera", []):
        if not isinstance(raw_camera, dict):
            continue
        start = _clamp(raw_camera.get("start"), 0.0, duration, 0.0)
        end = _clamp(raw_camera.get("end"), start + 0.1, duration, duration)
        shot = str(raw_camera.get("shot", "medium")).lower()
        if shot not in CAMERA_SHOTS:
            shot = "medium"
        angle = str(raw_camera.get("angle", "three_quarter")).lower()
        if angle not in CAMERA_ANGLES:
            angle = "three_quarter"
        camera.append(
            {
                "start": round(start, 3),
                "end": round(max(start + 0.1, end), 3),
                "shot": shot,
                "angle": angle,
                "follow": bool(raw_camera.get("follow", True)),
            }
        )
    if not camera:
        camera = [
            {
                "start": 0.0,
                "end": duration,
                "shot": "medium",
                "angle": "three_quarter",
                "follow": True,
            }
        ]

    return {
        "summary": str(raw.get("summary", "AI motion plan for Oyen Purba"))[:240],
        "coordinate_system": {
            "character_forward": "-Y",
            "right": "+X",
            "up": "+Z",
        },
        "clips": clips[:8],
        "camera": camera[:4],
    }


def _planner_prompt(prompt: str, duration: float) -> str:
    return f"""
You are the motion director for a short Blender animation starring Oyen Purba,
a short chubby orange cartoon cat with a humanoid 34-bone rig.

Convert the Indonesian user prompt into a practical motion plan for Blender.
The plan must fit exactly {duration:.2f} seconds.

Important coordinate rules:
- Oyen's face and forward direction are world -Y.
- Moving forward MUST reduce Y. Never use X as forward.
- X is only left/right.
- Prefer readable anticipation, action, follow-through and a settle pose.
- Do not add waving unless the user asks for waving.
- Use run for "berlari", walk for "berjalan", jump for "melompat",
  look for "menoleh/melihat", turn for "berbalik", surprised for "terkejut",
  angry for "marah/kesal", and stop for "berhenti".
- A moving clip should use a useful distance: walk about 0.8-2.0,
  run about 1.8-4.5, jump about 0.2-1.2.
- Keep the camera mostly front or three-quarter and follow locomotion.
- Produce only JSON matching the supplied schema.

User prompt:
{prompt}
""".strip()


def _request_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 35) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details[-1200:]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError("AI response was not a JSON object")
    return parsed


def _gemini_plan(prompt: str, duration: float) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": _planner_prompt(prompt, duration)}]}],
        "generationConfig": {
            "responseFormat": {
                "text": {
                    "mimeType": "application/json",
                    "schema": MOTION_SCHEMA,
                }
            }
        },
    }
    response = _request_json(
        url,
        payload,
        {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Gemini returned no motion plan: {response}") from exc
    return json.loads(_clean_json_text(text))


def _groq_plan(prompt: str, duration: float) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Return a strict JSON Blender motion plan. Do not include markdown.",
            },
            {"role": "user", "content": _planner_prompt(prompt, duration)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "oyen_motion_plan",
                "strict": True,
                "schema": MOTION_SCHEMA,
            },
        },
    }
    response = _request_json(
        "https://api.groq.com/openai/v1/chat/completions",
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Groq returned no motion plan: {response}") from exc
    return json.loads(_clean_json_text(text))


def _fallback_plan(prompt: str, duration: float) -> dict[str, Any]:
    text = (prompt or "").lower()
    duration = max(1.0, float(duration))
    clips: list[dict[str, Any]] = []

    def add(
        motion_type: str,
        start: float,
        end: float,
        direction: str = "none",
        distance: float = 0.0,
        intensity: float = 0.65,
        target: str = "",
    ) -> None:
        clips.append(
            {
                "type": motion_type,
                "start": round(start, 3),
                "end": round(end, 3),
                "direction": direction,
                "distance": distance,
                "intensity": intensity,
                "target": target,
            }
        )

    locomotion_end = duration * 0.72
    if any(word in text for word in ("berlari", "lari", "mengejar")):
        target = "ayam" if "ayam" in text else ("ikan" if "ikan" in text else "")
        add("run", 0.0, locomotion_end, "forward", min(4.2, duration * 0.75), 0.9, target)
    elif any(word in text for word in ("berjalan", "jalan", "melangkah")):
        add("walk", 0.0, locomotion_end, "forward", min(2.2, duration * 0.38), 0.68)
    else:
        add("idle", 0.0, max(0.6, duration * 0.35), "none", 0.0, 0.45)

    cursor = clips[-1]["end"]
    if any(word in text for word in ("melompat", "lompat")) and cursor < duration:
        jump_end = min(duration, cursor + duration * 0.3)
        add("jump", cursor, jump_end, "forward", 0.55, 0.85)
        cursor = jump_end
    if any(word in text for word in ("menoleh", "melihat", "menatap")) and cursor < duration:
        end = min(duration, cursor + max(0.5, duration * 0.16))
        add("look", cursor, end, "none", 0.0, 0.7, "camera")
        cursor = end
    if any(word in text for word in ("melambai", "melambaikan")) and cursor < duration:
        end = min(duration, cursor + max(0.55, duration * 0.18))
        add("wave", cursor, end, "none", 0.0, 0.75)
        cursor = end
    if any(word in text for word in ("terkejut", "kaget")) and cursor < duration:
        end = min(duration, cursor + max(0.45, duration * 0.14))
        add("surprised", cursor, end, "none", 0.0, 0.9)
        cursor = end
    if any(word in text for word in ("marah", "kesal")) and cursor < duration:
        end = min(duration, cursor + max(0.55, duration * 0.18))
        add("angry", cursor, end, "none", 0.0, 0.8)
        cursor = end

    if cursor < duration:
        add("stop", cursor, duration, "none", 0.0, 0.55)

    return {
        "summary": "Local motion planner fallback",
        "clips": clips,
        "camera": [
            {
                "start": 0.0,
                "end": duration,
                "shot": "medium",
                "angle": "three_quarter",
                "follow": True,
            }
        ],
    }


def available_ai_provider() -> str:
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "Gemini"
    if os.getenv("GROQ_API_KEY"):
        return "Groq"
    return "Local fallback"


def build_motion_plan(prompt: str, duration: float) -> tuple[dict[str, Any], str, str]:
    errors: list[str] = []
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        try:
            return _normalise_plan(_gemini_plan(prompt, duration), duration), "Gemini", "AI structured motion plan"
        except Exception as exc:
            errors.append(f"Gemini: {exc}")
    if os.getenv("GROQ_API_KEY"):
        try:
            return _normalise_plan(_groq_plan(prompt, duration), duration), "Groq", "AI structured motion plan"
        except Exception as exc:
            errors.append(f"Groq: {exc}")

    fallback = _normalise_plan(_fallback_plan(prompt, duration), duration)
    note = "Local prompt parser"
    if errors:
        note += " after API error: " + " | ".join(errors)[-500:]
    return fallback, "Local fallback", note
