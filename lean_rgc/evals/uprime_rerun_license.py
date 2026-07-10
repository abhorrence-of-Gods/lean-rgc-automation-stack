from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA_UPRIME_RERUN_REGISTRY = "lean-rgc-uprime-u1-rerun-registry-v1.0"
RERUN_REGISTRY_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_rerun_license_registry.json"
)
_TOP_LEVEL_KEYS = ("default_allow", "licenses", "schema_version")
_MAX_REGISTRY_BYTES = 1024 * 1024
_FULL_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")


class UPrimeRerunLicenseError(RuntimeError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise UPrimeRerunLicenseError(
                f"duplicate key in U'1 rerun registry: {key}"
            )
        out[key] = value
    return out


def canonical_registry_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def load_rerun_registry(path: str | Path) -> dict[str, Any]:
    registry_path = Path(path)
    try:
        with registry_path.open("rb") as handle:
            raw = handle.read(_MAX_REGISTRY_BYTES + 1)
        if len(raw) > _MAX_REGISTRY_BYTES:
            raise UPrimeRerunLicenseError("U'1 rerun registry is too large")
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except UPrimeRerunLicenseError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UPrimeRerunLicenseError("U'1 rerun registry is unreadable") from exc
    if not isinstance(value, dict) or tuple(sorted(value)) != _TOP_LEVEL_KEYS:
        raise UPrimeRerunLicenseError("U'1 rerun registry field set is invalid")
    if value.get("schema_version") != SCHEMA_UPRIME_RERUN_REGISTRY:
        raise UPrimeRerunLicenseError("U'1 rerun registry schema is invalid")
    if value.get("default_allow") is not False:
        raise UPrimeRerunLicenseError("U'1 rerun registry must remain default-deny")
    if not isinstance(value.get("licenses"), dict):
        raise UPrimeRerunLicenseError("U'1 rerun license map must be an object")
    try:
        canonical = canonical_registry_bytes(value)
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise UPrimeRerunLicenseError(
            "U'1 rerun registry contains a noncanonical value"
        ) from exc
    if raw != canonical:
        raise UPrimeRerunLicenseError("U'1 rerun registry is not canonical JSON")
    return value


def reject_canonical_rerun_bootstrap(repo_root: str | Path, head_commit: str) -> None:
    """Fail closed until the separately reviewed claim-receipt verifier exists.

    This bootstrap assertion must not be upgraded into a remote one-shot claimant:
    several defense-in-depth boundaries call it independently.  Activation replaces
    those repeated assertions with one atomic claim and a bound opaque receipt.
    """

    root = Path(repo_root).resolve()
    normalized_commit = str(head_commit).strip().lower()
    if _FULL_COMMIT_RE.fullmatch(normalized_commit) is None:
        raise UPrimeRerunLicenseError(
            "U'1 rerun license requires a full 40-character Git commit"
        )
    registry = load_rerun_registry(root / RERUN_REGISTRY_PATH)
    licenses = registry["licenses"]
    if not licenses:
        raise UPrimeRerunLicenseError(
            "U'1 canonical rerun is not licensed; registry is default-deny"
        )
    raise UPrimeRerunLicenseError(
        "U'1 rerun license activation verifier is not implemented; "
        f"refusing HEAD {normalized_commit}"
    )


__all__ = [
    "RERUN_REGISTRY_PATH",
    "SCHEMA_UPRIME_RERUN_REGISTRY",
    "UPrimeRerunLicenseError",
    "canonical_registry_bytes",
    "load_rerun_registry",
    "reject_canonical_rerun_bootstrap",
]
