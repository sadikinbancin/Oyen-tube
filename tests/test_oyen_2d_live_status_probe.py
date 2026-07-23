from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


MAIN_SHA = "bff849231851e625e80d16d8b16b4bac4ebda930"
REPO = "sadikinbancin/Oyen-tube"
SPACE_REPO = "lako123/Belajarh-ani"
SPACE_BASE = "https://lako123-belajarh-ani.hf.space"


def fetch_json(url: str) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, application/json",
            "User-Agent": "oyen-v06-status-probe",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"PROBE_HTTP_ERROR url={url} status={exc.code} body={body[:5000]}")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, {"error": body}
    except Exception as exc:
        print(f"PROBE_NETWORK_ERROR url={url} error={type(exc).__name__}: {exc}")
        return 0, {"error": f"{type(exc).__name__}: {exc}"}


def compact(value: Any, limit: int = 16000) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:limit]


class OyenV06LiveStatusProbe(unittest.TestCase):
    def test_print_exact_main_and_space_state(self) -> None:
        runs_url = (
            f"https://api.github.com/repos/{REPO}/actions/runs?"
            + urllib.parse.urlencode({"head_sha": MAIN_SHA, "per_page": 50})
        )
        runs_code, runs_payload = fetch_json(runs_url)
        print(f"OYEN_PROBE_RUNS_HTTP={runs_code}")
        runs = runs_payload.get("workflow_runs", []) if isinstance(runs_payload, dict) else []
        compact_runs = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "event": item.get("event"),
                "status": item.get("status"),
                "conclusion": item.get("conclusion"),
                "run_number": item.get("run_number"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "html_url": item.get("html_url"),
            }
            for item in runs
        ]
        print("OYEN_PROBE_MAIN_RUNS=" + compact(compact_runs))

        statuses_url = f"https://api.github.com/repos/{REPO}/commits/{MAIN_SHA}/statuses"
        statuses_code, statuses_payload = fetch_json(statuses_url)
        print(f"OYEN_PROBE_STATUSES_HTTP={statuses_code}")
        compact_statuses = [
            {
                "context": item.get("context"),
                "state": item.get("state"),
                "description": item.get("description"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "target_url": item.get("target_url"),
            }
            for item in statuses_payload
        ] if isinstance(statuses_payload, list) else statuses_payload
        print("OYEN_PROBE_COMMIT_STATUSES=" + compact(compact_statuses))

        hf_endpoints = {
            "space_info": f"https://huggingface.co/api/spaces/{SPACE_REPO}",
            "runtime": f"https://huggingface.co/api/spaces/{SPACE_REPO}/runtime",
            "tree": f"https://huggingface.co/api/spaces/{SPACE_REPO}/tree/main?recursive=true&expand=false",
            "config": f"{SPACE_BASE}/config?probe={MAIN_SHA[:12]}",
        }
        endpoint_results: dict[str, Any] = {}
        for name, url in hf_endpoints.items():
            code, payload = fetch_json(url)
            endpoint_results[name] = {"http": code, "payload": payload}
            print(f"OYEN_PROBE_HF_{name.upper()}=" + compact(endpoint_results[name]))

        config_entry = endpoint_results["config"]
        config_text = compact(config_entry["payload"], 200000)
        evidence = {
            "http": config_entry["http"],
            "has_render_mp4": "render_mp4" in config_text,
            "has_studio_title": "Oyen Purba 2D Cutout Studio" in config_text,
            "has_motion_button": "Susun Motion 2D" in config_text,
            "has_cutout_mode": "2D Cutout Blender" in config_text,
            "version_present": "0.6.0" in config_text,
            "bytes": len(config_text.encode("utf-8")),
        }
        print("OYEN_PROBE_SPACE_CONFIG_EVIDENCE=" + compact(evidence))

        self.assertEqual(runs_code, 200, runs_payload)
        self.assertEqual(statuses_code, 200, statuses_payload)
        self.assertGreater(len(runs), 0, "No workflow run found for final main commit")
        self.assertEqual(endpoint_results["space_info"]["http"], 200)
        self.assertEqual(endpoint_results["runtime"]["http"], 200)


if __name__ == "__main__":
    unittest.main()
