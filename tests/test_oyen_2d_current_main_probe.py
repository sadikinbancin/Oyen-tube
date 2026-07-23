from __future__ import annotations

import json
import unittest
import urllib.parse
import urllib.request


MAIN_SHA = "569a37335724f82646e7d908eda8dad03c17e46c"
REPO = "sadikinbancin/Oyen-tube"


def fetch_json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, application/json",
            "User-Agent": "oyen-v06-current-main-probe",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


class CurrentMainProbe(unittest.TestCase):
    def test_print_current_main_workflows(self) -> None:
        runs_url = (
            f"https://api.github.com/repos/{REPO}/actions/runs?"
            + urllib.parse.urlencode({"head_sha": MAIN_SHA, "per_page": 20})
        )
        code, payload = fetch_json(runs_url)
        print("CURRENT_MAIN_RUNS_HTTP", code)
        runs = payload.get("workflow_runs", [])
        print(
            "CURRENT_MAIN_RUNS",
            json.dumps(
                [
                    {
                        "id": run.get("id"),
                        "name": run.get("name"),
                        "status": run.get("status"),
                        "conclusion": run.get("conclusion"),
                        "run_number": run.get("run_number"),
                    }
                    for run in runs
                ],
                ensure_ascii=False,
            ),
        )
        for run in runs:
            jobs_code, jobs_payload = fetch_json(
                f"https://api.github.com/repos/{REPO}/actions/runs/{run['id']}/jobs?per_page=100"
            )
            print("CURRENT_MAIN_JOBS_HTTP", run["id"], jobs_code)
            print(
                "CURRENT_MAIN_JOBS",
                json.dumps(
                    [
                        {
                            "id": job.get("id"),
                            "name": job.get("name"),
                            "status": job.get("status"),
                            "conclusion": job.get("conclusion"),
                            "steps": [
                                {
                                    "name": step.get("name"),
                                    "status": step.get("status"),
                                    "conclusion": step.get("conclusion"),
                                    "number": step.get("number"),
                                }
                                for step in job.get("steps", [])
                            ],
                        }
                        for job in jobs_payload.get("jobs", [])
                    ],
                    ensure_ascii=False,
                ),
            )
        self.assertEqual(code, 200)
        self.assertGreater(len(runs), 0)


if __name__ == "__main__":
    unittest.main()
