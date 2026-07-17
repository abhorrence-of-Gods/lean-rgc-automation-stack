from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

I0_COMMIT = "f1df8dd5d92706d907091e6add463fb6c9ca7130"
I0_TREE = "c15e50c683263b50c8ddf371938785d03353b1fc"
I0_PARENT = "2376aca8209c38a3a94dfa872334073d86dc4909"
I0_ENDPOINT_BLOBS = {
    "lean_rgc/evals/uprime_u2_u4_development.py":
        "32f68a477bbb2432a91cd463d49db658ff012258",
    "lean_rgc/odlrq/__init__.py":
        "7e08787436b385e50f071a44b9e26f31dea0c597",
    "lean_rgc/odlrq/certificates.py":
        "99e88abadaffc8c108953bcac663ffb135143317",
    "tests/test_odlrq_similarity.py":
        "3e579a088d6e6b1cde4aed605a90bc3ca12dfec6",
    "tests/test_uprime_u2_u4_development.py":
        "ef4a56778c9734952257e56f91a0b93003bc577a",
    "tests/uprime_u24_guard.py":
        "cd0a4fe0def1c5523e0c0b9fe023dde8fc0b09e7",
    "tests/tier_manifest.json":
        "1663889c4732481eb6e2176df7c48ee396868216",
    "tools/run_uprime_u2_u4_development_tests.ps1":
        "b79f1fa354cdddde2b2ae7b6efce8d9ac005be8b",
}

SIDECAR_COMMIT = "ee7a1c01dba376881d20962de664f4908acc7b0d"
SIDECAR_TREE = "ebc93e941df405b50f425f8c844de2597eaca1f4"
SIDECAR_BLOBS = {
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "envelope_core.json": "c2d6ea3e5874ea93b7ca93f042f8adb7b4e8fb0f",
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "global_measure.json": "986948538c2a18b906c1d8067d7b9e668f5d50f6",
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "integrated_certificate.json": "92bf03e20fcd583f6a196ff34b138ac08f60c969",
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "level_transport.json": "f3a4ff185882f3dae3fedb09864fab29fac59b07",
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "local_tower.json": "4170c34310efc834d2e46372e218169b4ccea071",
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "maxent_fixture.json": "d574b7fe48b946087bd718ec80ca5bfe9403c5ac",
    "docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/"
    "similarity_certificate.json": "bfc09299146cec8ee30232f6cde271a5a5dc37a9",
    "docs/experiments/uprime_odlrq_post_e2_upper_stack_closeout_2026-07-17.md":
        "fe2192c1dce8334fbfdeae03abbcf9551c372c36",
}
SIDECAR_CORRECTION_COMMIT = "c1f1957a3372f80f71b85151a793a4fa0fb218fa"
SIDECAR_CORRECTION_TREE = "e17ced0dbf26b3dd13a0cf6c6f4ba419438dff1f"
SIDECAR_CORRECTION_PATH = (
    "docs/experiments/"
    "uprime_odlrq_post_e2_upper_stack_closeout_correction_2026-07-17.md"
)
SIDECAR_CORRECTION_BLOB = "ad004ace10681ca7f4813c3bcbc6cc7bb6b5e1cd"

AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u15_l0_locality_cegar_phase_bundle_amendment_2026-07-17.md"
)
MATRIX_PATH = "docs/experiments/inputs/uprime_u15_l0_matrix.json"
A_PRIMARY_COMMIT = "3155da6ad99105d2ba0ba10124d7372508020a94"
A_PRIMARY_TREE = "ca7073c9ee67c53823127b2da3b11021dc520ccc"
A_PRIMARY_BLOBS = {
    AUTHORITY_DOCUMENT_PATH: "e2b8aad68a93514ee9270e4381b800b90523351e",
    MATRIX_PATH: "c4a66d0579cd5c6a648c23ea2073d721af5904b3",
}
A2_COMMIT = "933afa47efc4c1d80de1c1b7997c7f953c7fa033"
A2_TREE = "946d39999e6d4fd604ba2458359f1fe50ee1bf84"
A2_BLOBS = {
    AUTHORITY_DOCUMENT_PATH: "cd08087dcb593105d921411d6b4501013b581245",
    MATRIX_PATH: "91af3d8e95714a043e2ab0f1f564d7f4d1014dec",
}

PHASE_ALLOWLISTS = {
    "B": frozenset(
        {
            "tests/test_odlrq_similarity.py",
            "tests/test_uprime_u2_u4_development.py",
            "tests/test_uprime_u15_l0_identity.py",
            "tests/uprime_u24_guard.py",
            "tests/tier_manifest.json",
            "tools/run_uprime_u2_u4_development_tests.ps1",
        }
    ),
    "C": frozenset(
        {
            "lean_rgc/odlrq/locality_cegar.py",
            "lean_rgc/odlrq/__init__.py",
            "lean_rgc/evals/uprime_u15_l0_locality_cegar.py",
            "tests/test_odlrq_locality_cegar.py",
            "tests/test_uprime_u15_l0_locality_cegar.py",
            "tests/tier_manifest.json",
        }
    ),
    "D": frozenset(
        {
            "docs/experiments/"
            "uprime_odlrq_u15_l0_locality_cegar_closeout_2026-07-17.md",
            "docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717/"
            "locality_cegar_result.json",
        }
    ),
}
PHASE_REFS = {
    "B": (
        "codex/uprime-u15-l0-control-bootstrap",
        "codex/uprime-u15-l0-control-bootstrap-a2",
    ),
    "C": (
        "codex/uprime-u15-l0-candidate",
        "codex/uprime-u15-l0-candidate-a2",
    ),
    "D": (
        "codex/uprime-u15-l0-closeout",
        "codex/uprime-u15-l0-closeout-a2",
    ),
}
ALL_REGISTERED_L0_REFS = frozenset(
    {
        "codex/uprime-u15-l0-authority",
        "codex/uprime-u15-l0-authority-a2",
        "codex/uprime-u15-l0-plan",
        *(name for names in PHASE_REFS.values() for name in names),
    }
)
TEST_NAMES = (
    "test_u15_l0_frozen_parent_sidecars_and_authority_identity",
    "test_u15_l0_old_u24_epoch_is_immutable_and_handoff_is_exact",
    "test_u15_l0_phase_suffix_paths_parents_refs_and_budgets_are_exact",
    "test_u15_l0_static_scope_tier_firewall_and_terminal_topology",
)
CLOSEOUT_C_COMMIT_FIELD = "accepted_c_commit"
CLOSEOUT_C_TREE_FIELD = "accepted_c_tree"

CORE_C_TEST_NAMES = (
    "test_l0_before_region_features_are_relabel_invariant_and_exact",
    "test_l0_path_cycle_articulation_and_treewidth_features_are_known",
    "test_l0_after_audit_carrier_and_future_features_are_rejected",
    "test_l0_query_binds_complete_ordered_action_symbols_and_cost",
    "test_l0_cross_frame_query_and_response_splicing_reject",
    "test_l0_exact_counterexample_adds_must_separate_and_splits_monotonically",
    "test_l0_equality_and_no_counterexample_never_merge_or_promote",
    "test_l0_proposal_and_report_remain_nominal_and_hard_ineligible",
    "test_l0_ghost_noop_is_retained_by_delayed_return_witness",
    "test_l0_ghost_omission_changes_catalog_digest_and_rejects",
    "test_l0_full_conditional_covariance_reduction_is_exact_fraction",
    "test_l0_query_cost_reverses_ranking_and_tie_break_is_canonical",
    "test_l0_caps_apply_before_materialization_and_abstain",
    "test_l0_exact_partition_requires_independent_verifier",
    "test_l0_wire_caps_mutations_and_duplicate_keys_fail_closed",
    "test_l0_public_surface_has_no_merge_hard_promotion_or_forbidden_import",
)
EVAL_C_TEST_NAMES = (
    "test_u15_l0_matrix_identity_families_and_seeded_witnesses_are_exact",
    "test_u15_l0_family_stratified_paired_curves_use_fixed_denominator",
    "test_u15_l0_dispositions_cover_gain_no_gain_degraded_blocked_and_failed",
    "test_u15_l0_repeated_evaluation_is_byte_identical_and_budget_bound",
)
C_TEST_CONTRACTS = {
    "tests/test_odlrq_locality_cegar.py": CORE_C_TEST_NAMES,
    "tests/test_uprime_u15_l0_locality_cegar.py": EVAL_C_TEST_NAMES,
}
C_SCAN_PATHS = (
    "lean_rgc/odlrq/locality_cegar.py",
    "lean_rgc/evals/uprime_u15_l0_locality_cegar.py",
    *C_TEST_CONTRACTS,
)
L0_PUBLIC_NAMES = (
    "BeforeLocalRegion",
    "LocalityFeatureVector",
    "LocalityQuery",
    "ExactLocalResponseObservation",
    "ExactLocalCounterexample",
    "ProposedNominalPartition",
    "LocalityQueryScore",
    "LocalityCEGARReport",
    "LocalityResultDisposition",
    "make_before_local_region",
    "extract_before_locality_features",
    "make_locality_query",
    "derive_exact_query_cost",
    "make_exact_local_response_observation",
    "find_exact_local_counterexample",
    "propose_nominal_partition",
    "rank_locality_queries",
    "apply_exact_counterexample_split",
    "run_synthetic_locality_cegar",
    "verify_locality_cegar_report",
)
FORBIDDEN_C_IMPORT_PREFIXES = (
    "subprocess",
    "socket",
    "_socket",
    "ssl",
    "ctypes",
    "cffi",
    "multiprocessing",
    "asyncio",
    "concurrent",
    "threading",
    "os",
    "sys",
    "importlib",
    "runpy",
    "builtins",
    "pickle",
    "marshal",
    "pydoc",
    "pkgutil",
    "urllib",
    "http",
    "httpx",
    "requests",
    "aiohttp",
    "paramiko",
    "fabric",
    "ftplib",
    "telnetlib",
    "websocket",
    "websockets",
    "torch",
    "cupy",
    "tensorflow",
    "jax",
    "transformers",
    "openai",
    "vllm",
    "peft",
    "bitsandbytes",
    "accelerate",
    "numpy",
    "random",
    "secrets",
    "pluggy",
    "unittest.mock",
    "mock",
    "lean_rgc.native_lean",
    "lean_rgc.action_geometry",
    "lean_rgc.action_geometry_loop",
    "lean_rgc.response_learner",
    "lean_rgc.contextual_congruence",
    "lean_rgc.lean.mvar_blocks",
    "lean_rgc.mvar_blocks",
    "lean_rgc.odlrq.quotient_generator",
    "lean_rgc.odlrq.similarity",
    "lean_rgc.evals.uprime_u2_u4_development",
    "lean_rgc.bivariate_contextual_quotient",
    "lean_rgc.carrier_quotient",
    "lean_rgc.premise_contextual_quotient",
    "lean_rgc.quotient",
    "lean_rgc.quotient_coordinates",
    "lean_rgc.quotient_coordinate_loop",
    "lean_rgc.response_quotient",
    "lean_rgc.response_quotient_registry",
)
FORBIDDEN_C_SYMBOLS = frozenset(
    {
        "NominalOperator",
        "ExactDistinguishingWitness",
        "MonkeyPatch",
        "SkipTest",
    }
)
FORBIDDEN_DYNAMIC_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "import_module",
        "reload",
        "run_module",
        "run_path",
        "getattr",
        "setattr",
        "delattr",
        "__setattr__",
        "__delattr__",
        "globals",
        "locals",
        "vars",
    }
)
FORBIDDEN_TEST_CONTROL_NAMES = frozenset(
    {
        "pytestmark",
        "pytest_plugins",
        "collect_ignore",
        "collect_ignore_glob",
        "__test__",
        "__signature__",
        "pytest_generate_tests",
        "pytest_collection_modifyitems",
        "pytest_ignore_collect",
        "pytest_addoption",
        "pytest_configure",
        "pytest_unconfigure",
        "pytest_sessionstart",
        "pytest_sessionfinish",
        "pytest_runtest_setup",
        "pytest_runtest_call",
        "pytest_runtest_teardown",
        "load_tests",
        "__getattr__",
        "__dir__",
    }
)
FORBIDDEN_TEST_ACTION_NAMES = frozenset(
    {
        "skip",
        "skipif",
        "xfail",
        "importorskip",
        "parametrize",
        "expectedFailure",
        "mark",
        "fixture",
    }
)
SAFE_STDLIB_IMPORT_PREFIXES = (
    "__future__",
    "ast",
    "collections",
    "copy",
    "dataclasses",
    "enum",
    "fractions",
    "functools",
    "hashlib",
    "itertools",
    "json",
    "pathlib",
    "re",
    "types",
    "typing",
)
ALLOWED_C_REPO_IMPORTS = {
    "lean_rgc/odlrq/locality_cegar.py": frozenset(
        {
            "lean_rgc.odlrq.adapters",
            "lean_rgc.odlrq.behavioral_partition",
            "lean_rgc.odlrq.certificates",
            "lean_rgc.odlrq.contracts",
        }
    ),
    "lean_rgc/evals/uprime_u15_l0_locality_cegar.py": frozenset(
        {"lean_rgc.odlrq"}
    ),
    "tests/test_odlrq_locality_cegar.py": frozenset(
        {"lean_rgc.odlrq"}
    ),
    "tests/test_uprime_u15_l0_locality_cegar.py": frozenset(
        {
            "lean_rgc.evals.uprime_u15_l0_locality_cegar",
            "lean_rgc.odlrq",
        }
    ),
}


def _git(*args: str, check: bool = True) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "--no-replace-objects", *args],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"Git command failed ({completed.returncode}): {args!r}: "
            f"{completed.stderr.decode('utf-8', errors='replace')}"
        )
    return completed.stdout if completed.returncode == 0 else b""


def _commit_identity(commit: str) -> tuple[str, str, tuple[str, ...]]:
    raw = _git("show", "-s", "--format=%H%x00%T%x00%P", commit)
    fields = raw.rstrip(b"\n").decode("ascii").split("\x00")
    assert len(fields) == 3
    parents = tuple(fields[2].split()) if fields[2] else ()
    return fields[0], fields[1], parents


def _changed_paths(commit: str) -> frozenset[str]:
    raw = _git(
        "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", commit
    )
    paths = () if not raw else tuple(row.decode("utf-8") for row in raw.rstrip(b"\x00").split(b"\x00"))
    assert len(paths) == len(set(paths))
    return frozenset(paths)


def _blob(commit: str, path: str) -> str | None:
    raw = _git("rev-parse", "--verify", f"{commit}:{path}", check=False)
    if not raw:
        return None
    value = raw.decode("ascii").strip()
    assert re.fullmatch(r"[0-9a-f]{40}", value)
    return value


def _show_bytes(commit: str, path: str) -> bytes:
    return _git("show", f"{commit}:{path}")


def _remote_ref(name: str) -> str | None:
    raw = _git(
        "rev-parse", "--verify", f"refs/remotes/origin/{name}", check=False
    )
    if not raw:
        return None
    value = raw.decode("ascii").strip()
    assert re.fullmatch(r"[0-9a-f]{40}", value)
    return value


def _required_remote_ref(name: str) -> str:
    value = _remote_ref(name)
    assert value is not None
    return value


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        [
            "git", "-C", str(REPO_ROOT), "--no-replace-objects",
            "merge-base", "--is-ancestor", ancestor, descendant,
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert completed.returncode in (0, 1)
    return completed.returncode == 0


def _status_paths() -> frozenset[str]:
    raw = _git(
        "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"
    )
    records = () if not raw else tuple(raw.rstrip(b"\x00").split(b"\x00"))
    paths: list[str] = []
    for record in records:
        assert len(record) >= 4 and record[2:3] == b" "
        path = record[3:].decode("utf-8")
        if path.startswith("lean_rgc.egg-info/"):
            continue
        paths.append(path)
    assert len(paths) == len(set(paths))
    return frozenset(paths)


def _first_parent_suffix(head: str) -> tuple[str, ...]:
    raw = _git("rev-list", "--first-parent", "--reverse", f"{I0_COMMIT}..{head}")
    return tuple(raw.decode("ascii").splitlines())


def _phase_state() -> dict[str, Any]:
    head = _git("rev-parse", "HEAD").decode("ascii").strip()
    chain = _first_parent_suffix(head)
    assert chain and chain[0] == A2_COMMIT
    assert 1 <= len(chain) <= 4
    assert _commit_identity(A2_COMMIT) == (A2_COMMIT, A2_TREE, (I0_COMMIT,))
    assert _changed_paths(A2_COMMIT) == frozenset(A2_BLOBS)

    completed_names = ("B", "C", "D")[: len(chain) - 1]
    previous = A2_COMMIT
    for phase, commit in zip(completed_names, chain[1:]):
        observed, _tree, parents = _commit_identity(commit)
        assert observed == commit and parents == (previous,)
        assert _changed_paths(commit) == PHASE_ALLOWLISTS[phase]
        previous = commit

    dirty = _status_paths()
    pending: str | None = None
    if dirty:
        assert len(completed_names) < 3
        pending = ("B", "C", "D")[len(completed_names)]
        assert dirty <= PHASE_ALLOWLISTS[pending]
    return {
        "head": head,
        "chain": chain,
        "completed": completed_names,
        "dirty": dirty,
        "pending": pending,
    }


def _i0_extension(raw: bytes) -> bytes:
    begin = b"# U24_I0_TEST_EXTENSION_BEGIN\n"
    end = b"# U24_I0_TEST_EXTENSION_END"
    assert raw.count(begin) == 1 and raw.count(end) == 1
    start = raw.index(begin) + len(begin)
    stop = raw.index(end, start)
    return raw[start:stop]


def _identity_core(raw: bytes) -> bytes:
    begin = b"# U24_I0_TEST_EXTENSION_BEGIN\n"
    end = b"# U24_I0_TEST_EXTENSION_END"
    assert raw.count(begin) == 1 and raw.count(end) == 1
    start = raw.index(begin) + len(begin)
    stop = raw.index(end, start)
    return raw[:start] + raw[stop:]


def _single_assignment(text: str, pattern: str) -> str:
    matches = re.findall(pattern, text, flags=re.M)
    assert len(matches) == 1
    return matches[0]


def _single_closeout_identity(text: str, field: str) -> str:
    matches = re.findall(
        rf"^- {re.escape(field)}: `([0-9a-f]{{40}})`$", text, flags=re.M
    )
    assert len(matches) == 1
    return matches[0]


def _current_ref_name() -> str | None:
    head_ref = os.environ.get("GITHUB_HEAD_REF", "").strip()
    if head_ref:
        return head_ref
    github_ref = os.environ.get("GITHUB_REF", "").strip()
    prefix = "refs/heads/"
    if github_ref.startswith(prefix):
        return github_ref[len(prefix):]
    raw = _git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if not raw:
        return None
    value = raw.decode("utf-8").strip()
    return value.removeprefix("refs/heads/").removeprefix("origin/")


def _module_package(path: str) -> str | None:
    if path.startswith("tests/"):
        return None
    module = path.removesuffix(".py").replace("/", ".")
    return module.rsplit(".", 1)[0]


def _resolved_imports(
    path: str, tree: ast.Module
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, str]]:
    modules: list[str] = []
    symbols: list[str] = []
    aliases: dict[str, str] = {}
    package = _module_package(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "*"
                modules.append(alias.name)
                local = alias.asname or alias.name.split(".", 1)[0]
                aliases[local] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                assert package is not None
                package_parts = package.split(".")
                assert node.level <= len(package_parts)
                keep = len(package_parts) - node.level + 1
                base_parts = package_parts[:keep]
                if node.module:
                    base_parts.extend(node.module.split("."))
                module = ".".join(base_parts)
            else:
                assert node.module is not None
                module = node.module
            modules.append(module)
            for alias in node.names:
                assert alias.name != "*"
                symbols.append(alias.name)
                qualified = f"{module}.{alias.name}" if module else alias.name
                aliases[alias.asname or alias.name] = qualified
                if node.module is None:
                    modules.append(qualified)
    return tuple(modules), tuple(symbols), aliases


def _qualified_expression(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _qualified_expression(node.value, aliases)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (node.attr,)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(name for item in node.elts for name in _target_names(item))
    return ()


def _literal_all(tree: ast.Module) -> tuple[str, ...]:
    values: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            values.append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
            and node.value is not None
        ):
            values.append(node.value)
    assert len(values) == 1
    value = ast.literal_eval(values[0])
    assert isinstance(value, (list, tuple))
    assert all(type(item) is str for item in value)
    result = tuple(value)
    assert len(result) == len(set(result))
    return result


def _normalized_init_scaffold(tree: ast.Module) -> tuple[Any, ...]:
    rows: list[Any] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            fragment = ast.Module(body=[node], type_ignores=[])
            modules, _symbols, _aliases = _resolved_imports(
                "lean_rgc/odlrq/__init__.py", fragment
            )
            if modules == ("lean_rgc.odlrq.locality_cegar",):
                continue
        is_all = (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            )
        ) or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
        )
        if is_all:
            rows.append(
                (
                    "__all__",
                    tuple(
                        name
                        for name in _literal_all(tree)
                        if name not in L0_PUBLIC_NAMES
                    ),
                )
            )
        else:
            rows.append(ast.dump(node, annotate_fields=True, include_attributes=False))
    return tuple(rows)


def _assert_zero_argument_test(node: ast.AST) -> None:
    assert isinstance(node, ast.FunctionDef)
    assert not node.decorator_list
    assert not node.args.posonlyargs and not node.args.args
    assert node.args.vararg is None and not node.args.kwonlyargs
    assert node.args.kwarg is None and not node.args.defaults
    assert not node.args.kw_defaults
    assert node.returns is None
    assert node.body and not all(isinstance(item, ast.Pass) for item in node.body)


def _assert_c_test_contract(
    path: str, tree: ast.Module, expected: tuple[str, ...]
) -> None:
    modules, symbols, aliases = _resolved_imports(path, tree)
    assert not (set(symbols) & FORBIDDEN_TEST_ACTION_NAMES)
    top_tests = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }
    assert frozenset(top_tests) == frozenset(expected)
    all_tests = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    assert {id(node) for node in all_tests} == {
        id(node) for node in top_tests.values()
    }
    for name in expected:
        test_node = top_tests[name]
        _assert_zero_argument_test(test_node)
        has_nonconstant_assert = any(
            isinstance(node, ast.Assert) and not isinstance(node.test, ast.Constant)
            for node in ast.walk(test_node)
        )
        has_raises_context = any(
            isinstance(node, ast.With)
            and any(
                isinstance(item.context_expr, ast.Call)
                and (
                    _qualified_expression(item.context_expr.func, aliases) or ""
                ).rsplit(".", 1)[-1] == "raises"
                for item in node.items
            )
            for node in ast.walk(test_node)
        )
        assert has_nonconstant_assert or has_raises_context
    assert not any(
        isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (node.name.startswith("pytest_") or node.name in {"load_tests", "__getattr__"})
        for node in ast.walk(tree)
    )
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else (node.target,)
            )
            names = tuple(name for target in targets for name in _target_names(target))
            assert not any(
                name.startswith("test_")
                or name.startswith("pytest_")
                or name in FORBIDDEN_TEST_CONTROL_NAMES
                for name in names
            )
        if isinstance(node, ast.Name):
            assert node.id not in FORBIDDEN_TEST_CONTROL_NAMES
            assert node.id not in FORBIDDEN_TEST_ACTION_NAMES
        elif isinstance(node, ast.Attribute):
            assert node.attr not in FORBIDDEN_TEST_CONTROL_NAMES
            assert node.attr not in FORBIDDEN_TEST_ACTION_NAMES
        elif isinstance(node, ast.Call):
            leaf = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else None
            )
            assert leaf not in FORBIDDEN_TEST_ACTION_NAMES
        elif isinstance(node, ast.Constant) and type(node.value) is str:
            assert node.value not in FORBIDDEN_TEST_CONTROL_NAMES
        elif isinstance(node, ast.Raise) and node.exc is not None:
            qualified = _qualified_expression(node.exc, {})
            assert qualified is None or not qualified.endswith("SkipTest")

    for module in modules:
        parts = module.split(".")
        assert "conftest" not in parts
        assert not any(part.startswith("test_") for part in parts)
        assert not (module == "tests" or module.startswith("tests."))


def _assert_c_capability_firewall(path: str, tree: ast.Module) -> dict[str, str]:
    modules, symbols, aliases = _resolved_imports(path, tree)
    allowed_repo = ALLOWED_C_REPO_IMPORTS[path]
    for module in modules:
        assert not any(
            module == forbidden or module.startswith(forbidden + ".")
            for forbidden in FORBIDDEN_C_IMPORT_PREFIXES
        )
        if module == "pytest":
            assert path.startswith("tests/")
        elif module.startswith("lean_rgc"):
            assert module in allowed_repo
        else:
            assert any(
                module == allowed or module.startswith(allowed + ".")
                for allowed in SAFE_STDLIB_IMPORT_PREFIXES
            )
    assert not (set(symbols) & FORBIDDEN_C_SYMBOLS)
    for qualified in aliases.values():
        assert not any(
            qualified == forbidden or qualified.startswith(forbidden + ".")
            for forbidden in FORBIDDEN_C_IMPORT_PREFIXES
        )
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in FORBIDDEN_C_SYMBOLS
            assert node.id not in FORBIDDEN_DYNAMIC_NAMES
        elif isinstance(node, ast.Attribute):
            assert node.attr not in FORBIDDEN_C_SYMBOLS
            assert node.attr not in FORBIDDEN_DYNAMIC_NAMES
            qualified = _qualified_expression(node, aliases)
            if qualified is not None:
                assert not any(
                    qualified == forbidden or qualified.startswith(forbidden + ".")
                    for forbidden in FORBIDDEN_C_IMPORT_PREFIXES
                )
        elif isinstance(node, ast.Call):
            qualified = _qualified_expression(node.func, aliases)
            if qualified is not None:
                assert qualified.rsplit(".", 1)[-1] not in FORBIDDEN_DYNAMIC_NAMES
    return aliases


def _assert_fixed_nominal_fields(
    tree: ast.Module, aliases: dict[str, str]
) -> None:
    classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    for class_name in (
        "ProposedNominalPartition",
        "LocalityQueryScore",
        "LocalityCEGARReport",
    ):
        class_node = classes[class_name]
        fields = {
            node.target.id: node.value
            for node in class_node.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        }
        for field_name in ("evidence_tier", "hard_eligible"):
            value = fields[field_name]
            assert isinstance(value, ast.Call)
            assert _qualified_expression(value.func, aliases) == "dataclasses.field"
            keywords = {keyword.arg: keyword.value for keyword in value.keywords}
            assert set(keywords) == {"default", "init"}
            assert isinstance(keywords["init"], ast.Constant)
            assert keywords["init"].value is False
            default = keywords["default"]
            if field_name == "hard_eligible":
                assert isinstance(default, ast.Constant) and default.value is False
            else:
                assert isinstance(default, ast.Attribute)
                assert _qualified_expression(default, aliases) == (
                    "lean_rgc.odlrq.certificates.PipelineEvidenceTier."
                    "NOMINAL_DIAGNOSTIC_ONLY"
                )


def _assert_locality_exact_capability_boundary(
    tree: ast.Module, aliases: dict[str, str]
) -> None:
    _modules, symbols, _aliases = _resolved_imports(
        "lean_rgc/odlrq/locality_cegar.py", tree
    )
    assert not (
        set(symbols)
        & {
            "ExactPartitionCertificate",
            "refine_exact_partition",
            "verify_exact_partition",
        }
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        qualified = _qualified_expression(node.func, aliases)
        if qualified is None:
            continue
        assert qualified.rsplit(".", 1)[-1] not in {
            "refine_exact_partition",
            "verify_exact_partition",
        }
        assert ".VerifiedExactPartition." not in qualified
        assert not qualified.endswith(".VerifiedExactPartition")
        assert ".AdmittedExactFiniteSnapshot." not in qualified
        assert not qualified.endswith(".AdmittedExactFiniteSnapshot")


def _is_fixed_false(
    value: ast.AST | None, aliases: dict[str, str] | None = None
) -> bool:
    if isinstance(value, ast.Constant):
        return value.value is False
    if isinstance(value, ast.Call):
        if _qualified_expression(value.func, aliases or {}) != "dataclasses.field":
            return False
        keywords = {keyword.arg: keyword.value for keyword in value.keywords}
        return (
            set(keywords) == {"default", "init"}
            and isinstance(keywords["default"], ast.Constant)
            and keywords["default"].value is False
            and isinstance(keywords["init"], ast.Constant)
            and keywords["init"].value is False
        )
    return False


def _assert_nominal_only_production(
    trees: tuple[tuple[ast.Module, dict[str, str]], ...]
) -> None:
    used_tiers: set[str] = set()
    for tree, aliases in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                qualified = _qualified_expression(node, aliases)
                if qualified is not None and ".PipelineEvidenceTier." in qualified:
                    used_tiers.add(qualified.rsplit(".", 1)[-1])
            elif isinstance(node, ast.keyword) and node.arg == "hard_eligible":
                assert isinstance(node.value, ast.Constant)
                assert node.value.value is False
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else (node.target,)
                )
                if any(
                    name == "hard_eligible"
                    for target in targets
                    for name in _target_names(target)
                ):
                    assert _is_fixed_false(node.value, aliases)
                for target in targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "hard_eligible"
                    ):
                        assert _is_fixed_false(node.value, aliases)
                value_qualified = _qualified_expression(node.value, aliases)
                assert value_qualified is None or not value_qualified.endswith(
                    ".PipelineEvidenceTier"
                )
            elif isinstance(node, ast.AugAssign):
                assert "hard_eligible" not in _target_names(node.target)
                assert not (
                    isinstance(node.target, ast.Subscript)
                    and isinstance(node.target.slice, ast.Constant)
                    and node.target.slice.value == "hard_eligible"
                )
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "hard_eligible"
                    ):
                        assert _is_fixed_false(value, aliases)
            elif isinstance(node, ast.Subscript):
                qualified = _qualified_expression(node.value, aliases)
                assert qualified is None or not qualified.endswith(
                    ".PipelineEvidenceTier"
                )
            elif isinstance(node, ast.Call):
                qualified = _qualified_expression(node.func, aliases)
                assert qualified is None or not qualified.endswith(
                    ".PipelineEvidenceTier"
                )
    assert used_tiers == {"NOMINAL_DIAGNOSTIC_ONLY"}


def test_u15_l0_frozen_parent_sidecars_and_authority_identity():
    assert _commit_identity(I0_COMMIT) == (I0_COMMIT, I0_TREE, (I0_PARENT,))
    assert _commit_identity(A_PRIMARY_COMMIT) == (
        A_PRIMARY_COMMIT, A_PRIMARY_TREE, (I0_COMMIT,)
    )
    assert _commit_identity(A2_COMMIT) == (A2_COMMIT, A2_TREE, (I0_COMMIT,))
    assert _changed_paths(A_PRIMARY_COMMIT) == frozenset(A_PRIMARY_BLOBS)
    assert _changed_paths(A2_COMMIT) == frozenset(A2_BLOBS)
    for path, expected in A_PRIMARY_BLOBS.items():
        assert _blob(A_PRIMARY_COMMIT, path) == expected
    for path, expected in A2_BLOBS.items():
        assert _blob(A2_COMMIT, path) == expected
    assert _required_remote_ref("codex/uprime-u15-l0-authority") == A_PRIMARY_COMMIT
    assert _required_remote_ref("codex/uprime-u15-l0-authority-a2") == A2_COMMIT
    assert not _is_ancestor(A_PRIMARY_COMMIT, A2_COMMIT)
    assert not _is_ancestor(A2_COMMIT, A_PRIMARY_COMMIT)

    assert _commit_identity(SIDECAR_COMMIT) == (
        SIDECAR_COMMIT, SIDECAR_TREE, (I0_COMMIT,)
    )
    assert _changed_paths(SIDECAR_COMMIT) == frozenset(SIDECAR_BLOBS)
    for path, expected in SIDECAR_BLOBS.items():
        assert _blob(SIDECAR_COMMIT, path) == expected
    assert _commit_identity(SIDECAR_CORRECTION_COMMIT) == (
        SIDECAR_CORRECTION_COMMIT,
        SIDECAR_CORRECTION_TREE,
        (SIDECAR_COMMIT,),
    )
    assert _changed_paths(SIDECAR_CORRECTION_COMMIT) == frozenset(
        {SIDECAR_CORRECTION_PATH}
    )
    assert _blob(SIDECAR_CORRECTION_COMMIT, SIDECAR_CORRECTION_PATH) == (
        SIDECAR_CORRECTION_BLOB
    )
    assert _required_remote_ref("codex/uprime-post-e2-upper-stack-closeout") == (
        SIDECAR_COMMIT
    )
    assert _required_remote_ref(
        "codex/uprime-post-e2-upper-stack-closeout-correction"
    ) == SIDECAR_CORRECTION_COMMIT
    assert not _is_ancestor(SIDECAR_COMMIT, A2_COMMIT)
    assert not _is_ancestor(A2_COMMIT, SIDECAR_COMMIT)


def test_u15_l0_old_u24_epoch_is_immutable_and_handoff_is_exact():
    assert _required_remote_ref("codex/uprime-odlrq-plan") == I0_COMMIT
    for path, expected in I0_ENDPOINT_BLOBS.items():
        assert _blob(I0_COMMIT, path) == expected

    identity_path = REPO_ROOT / "tests/test_uprime_u2_u4_development.py"
    identity_raw = identity_path.read_bytes()
    frozen_identity_raw = _show_bytes(I0_COMMIT, "tests/test_uprime_u2_u4_development.py")
    assert _i0_extension(identity_raw) == _i0_extension(frozen_identity_raw)
    identity_text = identity_raw.decode("utf-8")
    assert identity_text.count("MAX_BUILD_COMMITS = 6") == 1
    assert identity_text.count(
        f'OLD_U24_ENDPOINT_COMMIT = "{I0_COMMIT}"'
    ) == 1
    assert identity_text.count(f'OLD_U24_ENDPOINT_TREE = "{I0_TREE}"') == 1
    assert identity_text.count(f'OLD_U24_ENDPOINT_PARENT = "{I0_PARENT}"') == 1
    assert identity_text.count("CONTROL = _project_old_u24_epoch(RAW_CONTROL)") == 1
    for path, expected in I0_ENDPOINT_BLOBS.items():
        if path in {
            "tests/test_odlrq_similarity.py",
            "tests/uprime_u24_guard.py",
            "tools/run_uprime_u2_u4_development_tests.ps1",
        }:
            continue
        assert expected in identity_text

    guard_path = REPO_ROOT / "tests/uprime_u24_guard.py"
    runner_path = REPO_ROOT / "tools/run_uprime_u2_u4_development_tests.ps1"
    guard_raw = guard_path.read_bytes()
    runner_raw = runner_path.read_bytes()
    frozen_guard_raw = _show_bytes(I0_COMMIT, "tests/uprime_u24_guard.py")
    frozen_runner_raw = _show_bytes(
        I0_COMMIT, "tools/run_uprime_u2_u4_development_tests.ps1"
    )
    guard_text = guard_raw.decode("utf-8")
    assert "\r" not in guard_text
    identity_core_sha = hashlib.sha256(_identity_core(identity_raw)).hexdigest().upper()
    frozen_identity_core = _single_assignment(
        guard_text, r'^FROZEN_IDENTITY_CORE_SHA256 = "([0-9A-F]{64})"$'
    )
    frozen_runner_sha = _single_assignment(
        guard_text, r'^FROZEN_RUNNER_SHA256 = "([0-9A-F]{64})"$'
    )
    guard_canonical = re.sub(
        r'(?m)^FROZEN_RUNNER_SHA256 = "[0-9A-F]{64}"$',
        'FROZEN_RUNNER_SHA256 = "' + "0" * 64 + '"',
        guard_text,
    )
    guard_core_sha = hashlib.sha256(guard_canonical.encode("utf-8")).hexdigest().upper()
    normalized_runner = runner_raw.replace(b"\r\n", b"\n")
    assert b"\r" not in normalized_runner
    runner_sha = hashlib.sha256(normalized_runner).hexdigest().upper()
    runner_text = normalized_runner.decode("utf-8")
    expected_guard_core = _single_assignment(
        runner_text, r'^\$ExpectedGuardCoreSha256 = "([0-9A-F]{64})"$'
    )

    guard_scaffold = re.sub(
        r'(?m)^(FROZEN_(?:IDENTITY_CORE|RUNNER)_SHA256) = "[0-9A-F]{64}"$',
        lambda match: f'{match.group(1)} = "' + "0" * 64 + '"',
        guard_text,
    ).encode("utf-8")
    frozen_guard_scaffold = re.sub(
        rb'(?m)^(FROZEN_(?:IDENTITY_CORE|RUNNER)_SHA256) = "[0-9A-F]{64}"$',
        lambda match: match.group(1) + b' = "' + b"0" * 64 + b'"',
        frozen_guard_raw,
    )
    runner_scaffold = re.sub(
        rb'(?m)^\$ExpectedGuardCoreSha256 = "[0-9A-F]{64}"$',
        b'$ExpectedGuardCoreSha256 = "' + b"0" * 64 + b'"',
        normalized_runner,
    )
    frozen_runner_scaffold = re.sub(
        rb'(?m)^\$ExpectedGuardCoreSha256 = "[0-9A-F]{64}"$',
        b'$ExpectedGuardCoreSha256 = "' + b"0" * 64 + b'"',
        frozen_runner_raw.replace(b"\r\n", b"\n"),
    )
    assert guard_scaffold == frozen_guard_scaffold
    assert runner_scaffold == frozen_runner_scaffold

    closed = (
        frozen_identity_core == identity_core_sha
        and expected_guard_core == guard_core_sha
        and frozen_runner_sha == runner_sha
    )
    pristine_pending_cycle = (
        guard_raw == frozen_guard_raw
        and normalized_runner == frozen_runner_raw.replace(b"\r\n", b"\n")
    )
    if not closed:
        state = _phase_state()
        assert state["head"] == A2_COMMIT and state["pending"] == "B"
        assert pristine_pending_cycle


def test_u15_l0_phase_suffix_paths_parents_refs_and_budgets_are_exact():
    state = _phase_state()
    completed = state["completed"]
    chain = state["chain"]
    assert _required_remote_ref("codex/uprime-odlrq-plan") == I0_COMMIT

    published = {}
    raw_refs = _git(
        "for-each-ref", "--format=%(refname) %(objectname)",
        "refs/remotes/origin",
    ).decode("ascii").splitlines()
    for row in raw_refs:
        refname, commit = row.split()
        prefix = "refs/remotes/origin/"
        assert refname.startswith(prefix)
        short = refname[len(prefix):]
        if not short.startswith("codex/uprime-u15-l0-"):
            continue
        assert short in ALL_REGISTERED_L0_REFS
        assert short not in published
        published[short] = commit
    assert published["codex/uprime-u15-l0-authority"] == A_PRIMARY_COMMIT
    assert published["codex/uprime-u15-l0-authority-a2"] == A2_COMMIT

    selected_by_phase = {
        phase: chain[index]
        for index, phase in enumerate(completed, start=1)
    }
    current_ref = _current_ref_name()
    if current_ref is not None and current_ref.startswith("codex/uprime-u15-l0-"):
        assert current_ref in ALL_REGISTERED_L0_REFS

    visible_refs = dict(published)
    current_phase = next(
        (
            phase
            for phase, names in PHASE_REFS.items()
            if current_ref in names
        ),
        None,
    )
    if current_phase is not None:
        if current_phase in selected_by_phase:
            assert current_phase == completed[-1]
            assert selected_by_phase[current_phase] == state["head"]
            if current_ref in visible_refs:
                assert visible_refs[current_ref] == state["head"]
            else:
                visible_refs[current_ref] = state["head"]
        else:
            next_phase = ("B", "C", "D")[len(completed)]
            assert current_phase == next_phase
            assert state["pending"] in {None, current_phase}
    elif current_ref == "codex/uprime-u15-l0-plan":
        assert completed
        assert state["head"] == selected_by_phase[completed[-1]]
        if current_ref in visible_refs:
            assert visible_refs[current_ref] == state["head"]
        else:
            visible_refs[current_ref] = state["head"]

    for phase in ("B", "C", "D"):
        primary, replacement = PHASE_REFS[phase]
        phase_commits = [
            visible_refs[name]
            for name in (primary, replacement)
            if name in visible_refs
        ]
        assert len(phase_commits) <= 2 and len(phase_commits) == len(set(phase_commits))
        if replacement in visible_refs:
            assert primary in visible_refs
        if not phase_commits:
            continue
        if phase == "B":
            accepted_predecessor = A2_COMMIT
        elif phase == "C":
            assert "B" in selected_by_phase
            accepted_predecessor = selected_by_phase["B"]
        else:
            assert "C" in selected_by_phase
            accepted_predecessor = selected_by_phase["C"]
        for commit in phase_commits:
            observed, _tree, parents = _commit_identity(commit)
            assert observed == commit and parents == (accepted_predecessor,)
            assert _changed_paths(commit) == PHASE_ALLOWLISTS[phase]
        if replacement in visible_refs and phase in selected_by_phase:
            assert selected_by_phase[phase] == visible_refs[replacement]

    for index, phase in enumerate(completed, start=1):
        selected = chain[index]
        bindings = tuple(
            visible_refs[name]
            for name in PHASE_REFS[phase]
            if name in visible_refs
        )
        assert sum(commit == selected for commit in bindings) == 1

    accepted = visible_refs.get("codex/uprime-u15-l0-plan")
    execution_role: str | None
    if current_phase is not None:
        execution_role = current_phase
    elif current_ref == "codex/uprime-u15-l0-plan":
        execution_role = "accepted"
    elif completed and accepted == state["head"]:
        execution_role = "accepted"
    elif completed:
        execution_role = completed[-1]
    else:
        execution_role = None

    if execution_role == "B":
        assert accepted is None
    elif execution_role == "C":
        assert "B" in selected_by_phase
        assert accepted == selected_by_phase["B"]
    elif execution_role == "D":
        assert "C" in selected_by_phase
        assert accepted == selected_by_phase["C"]
    elif execution_role == "accepted":
        assert completed
        assert accepted == state["head"] == selected_by_phase[completed[-1]]
    else:
        assert state["head"] == A2_COMMIT
        assert accepted is None


def test_u15_l0_static_scope_tier_firewall_and_terminal_topology():
    state = _phase_state()
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=__file__)
    discovered = tuple(
        sorted(
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_u15_l0_")
        )
    )
    assert discovered == tuple(sorted(TEST_NAMES))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in TEST_NAMES:
            assert isinstance(node, ast.FunctionDef)
            assert not node.decorator_list
            assert not node.args.posonlyargs and not node.args.args
            assert node.args.vararg is None and not node.args.kwonlyargs
            assert node.args.kwarg is None and not node.args.defaults
            assert not node.args.kw_defaults
            assert node.returns is None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            names = tuple(
                name for target in targets for name in _target_names(target)
            )
            assert not (set(names) & {"pytest" + "mark", "pytest" + "_plugins"})

    manifest = json.loads(
        (REPO_ROOT / "tests/tier_manifest.json").read_text(encoding="utf-8")
    )
    assert type(manifest) is dict
    assert manifest["test_uprime_u15_l0_identity.py"] == ["unit"]
    semantic_active = "C" in state["completed"] or state["pending"] == "C"
    semantic_nodes = {
        "test_odlrq_locality_cegar.py",
        "test_uprime_u15_l0_locality_cegar.py",
    }
    for node in semantic_nodes:
        if semantic_active:
            assert manifest[node] == ["unit"]
        else:
            assert node not in manifest

    for path, expected in A2_BLOBS.items():
        assert _blob(state["head"], path) == expected

    semantic_new_paths = PHASE_ALLOWLISTS["C"] - {
        "lean_rgc/odlrq/__init__.py", "tests/tier_manifest.json"
    }
    if semantic_active:
        assert all((REPO_ROOT / path).is_file() for path in semantic_new_paths)
        c_trees: dict[str, ast.Module] = {}
        c_aliases: dict[str, dict[str, str]] = {}
        for path in C_SCAN_PATHS:
            module_text = (REPO_ROOT / path).read_text(encoding="utf-8")
            module_tree = ast.parse(module_text, filename=path)
            c_trees[path] = module_tree
            c_aliases[path] = _assert_c_capability_firewall(path, module_tree)
        for path, expected in C_TEST_CONTRACTS.items():
            _assert_c_test_contract(path, c_trees[path], expected)

        locality_path = "lean_rgc/odlrq/locality_cegar.py"
        locality_tree = c_trees[locality_path]
        assert _literal_all(locality_tree) == L0_PUBLIC_NAMES
        locality_definitions = [
            node
            for node in locality_tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        ]
        assert tuple(node.name for node in locality_definitions) == L0_PUBLIC_NAMES
        assert all(
            isinstance(node, ast.ClassDef) for node in locality_definitions[:9]
        )
        assert all(
            isinstance(node, ast.FunctionDef) for node in locality_definitions[9:]
        )
        assert not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in {"__getattr__", "__dir__"}
            for node in locality_tree.body
        )
        for node in locality_tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                assigned = tuple(
                    name for target in targets for name in _target_names(target)
                )
                assert not (set(assigned) & set(L0_PUBLIC_NAMES))
            elif isinstance(node, ast.Delete):
                deleted = tuple(
                    name for target in node.targets for name in _target_names(target)
                )
                assert not (set(deleted) & (set(L0_PUBLIC_NAMES) | {"__all__"}))
        for node in ast.walk(locality_tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "__all__"
            ):
                raise AssertionError("the frozen locality __all__ may not be mutated")
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                assert not any(
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "__all__"
                    for target in targets
                )
        _assert_locality_exact_capability_boundary(
            locality_tree, c_aliases[locality_path]
        )
        _assert_fixed_nominal_fields(locality_tree, c_aliases[locality_path])
        _assert_nominal_only_production(
            (
                (locality_tree, c_aliases[locality_path]),
                (
                    c_trees["lean_rgc/evals/uprime_u15_l0_locality_cegar.py"],
                    c_aliases["lean_rgc/evals/uprime_u15_l0_locality_cegar.py"],
                ),
            )
        )

        init_path = "lean_rgc/odlrq/__init__.py"
        init_text = (REPO_ROOT / init_path).read_text(encoding="utf-8")
        init_tree = ast.parse(init_text, filename=init_path)
        locality_imports: list[str] = []
        for node in init_tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            fragment = ast.Module(body=[node], type_ignores=[])
            modules, symbols, _aliases = _resolved_imports(init_path, fragment)
            if modules == ("lean_rgc.odlrq.locality_cegar",):
                assert all(alias.asname is None for alias in node.names)
                locality_imports.extend(symbols)
        assert tuple(locality_imports) == L0_PUBLIC_NAMES

        b_commit = state["chain"][1]
        old_init_tree = ast.parse(
            _show_bytes(b_commit, init_path).decode("utf-8"),
            filename=f"{b_commit}:{init_path}",
        )
        old_all = _literal_all(old_init_tree)
        current_all = _literal_all(init_tree)
        assert set(old_all).isdisjoint(L0_PUBLIC_NAMES)
        assert tuple(
            name for name in current_all if name not in L0_PUBLIC_NAMES
        ) == old_all
        assert set(current_all) - set(old_all) == set(L0_PUBLIC_NAMES)
        assert len(current_all) == len(set(current_all))
        assert _normalized_init_scaffold(init_tree) == _normalized_init_scaffold(
            old_init_tree
        )
    else:
        assert all(not (REPO_ROOT / path).exists() for path in semantic_new_paths)

    d_active = "D" in state["completed"] or state["pending"] == "D"
    d_paths = PHASE_ALLOWLISTS["D"]
    if d_active:
        assert all((REPO_ROOT / path).is_file() for path in d_paths)
        assert len(state["chain"]) >= 3
        c_commit = state["chain"][2]
        observed_c, c_tree, _c_parents = _commit_identity(c_commit)
        assert observed_c == c_commit
        closeout_path = next(
            path for path in d_paths if path.endswith(".md")
        )
        closeout_text = (REPO_ROOT / closeout_path).read_text(encoding="utf-8")
        assert _single_closeout_identity(
            closeout_text, CLOSEOUT_C_COMMIT_FIELD
        ) == c_commit
        assert _single_closeout_identity(
            closeout_text, CLOSEOUT_C_TREE_FIELD
        ) == c_tree
        artifact_root = REPO_ROOT / (
            "docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717"
        )
        assert tuple(
            sorted(path.relative_to(REPO_ROOT).as_posix() for path in artifact_root.rglob("*"))
        ) == tuple(sorted(path for path in d_paths if path.startswith("docs/experiments/artifacts/")))
    else:
        assert all(not (REPO_ROOT / path).exists() for path in d_paths)
