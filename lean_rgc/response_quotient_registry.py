"""Compatibility wrapper for v33 response quotient registry.

The canonical implementation lives in :mod:`lean_rgc.response_quotient`.
This module preserves older import paths used by intermediate v33 drafts.
"""
from __future__ import annotations

from .response_quotient import (  # noqa: F401
    build_response_quotient_registry,
    project_actions_by_response_quotient,
    response_quotient_from_congruence_dir,
)

# Backward-compatible aliases.
response_quotient_registry_from_files = build_response_quotient_registry
apply_response_quotient_to_actions = project_actions_by_response_quotient
