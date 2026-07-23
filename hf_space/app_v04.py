from __future__ import annotations

import spaces

APP_VERSION = "0.6.0"


def _zerogpu_duration(*_args, **_kwargs) -> int:
    """Compatibility probe only; Blender rendering is CPU-bound."""

    return 1


@spaces.GPU(duration=_zerogpu_duration)
def _zerogpu_compatibility_probe() -> str:
    return "OYEN_ZEROGPU_READY"


from app_v06 import demo  # noqa: E402


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, max_size=4).launch()
