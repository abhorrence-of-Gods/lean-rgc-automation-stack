from __future__ import annotations

from .lean.persistent_worker import *  # noqa: F401,F403
from .lean.persistent_worker import __all__, main  # noqa: F401


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
