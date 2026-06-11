from __future__ import annotations

from .lean.persistent_lean_worker import *  # noqa: F401,F403
from .lean.persistent_lean_worker import main  # noqa: F401

try:
    from .lean.persistent_lean_worker import __all__  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    from .lean import persistent_lean_worker as _worker

    __all__ = [name for name in dir(_worker) if not name.startswith("_")]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
