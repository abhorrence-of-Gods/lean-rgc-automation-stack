from __future__ import annotations

from .lean.native_worker import *  # noqa: F401,F403
from .lean.native_worker import __all__, main  # noqa: F401


if __name__ == "__main__":
    raise SystemExit(main())
