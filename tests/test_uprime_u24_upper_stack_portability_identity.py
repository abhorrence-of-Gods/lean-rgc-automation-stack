from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable

import uprime_u24_guard as u24_guard


REPO_ROOT = Path(__file__).resolve().parents[1]

AUTHORITY_COMMIT = "a1413bbeef03deb6eab8f2bd46ccc481bae6ea73"
AUTHORITY_PARENT = "f1df8dd5d92706d907091e6add463fb6c9ca7130"
AUTHORITY_TREE = "a3536963974528d3d22055bf62d5b49a2749c652"
AUTHORITY_REF = "refs/codex-authority/uprime-upper-portability-p0-20260718"
ACCEPTED_REF = "codex/uprime-upper-portability-plan"
RESOURCE_REF = (
    "refs/codex-authority/uprime-upper-portability-resource-20260718"
)

AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_upper_stack_portability_phase_bundle_amendment_2026-07-18.md"
)
AUTHORITY_DOCUMENT_BLOB = "7c0a5eea0df2224eed9594ee733184fba7771f66"
AUTHORITY_DOCUMENT_RAW_SHA256 = (
    "DED424629CA1C8DAFB31254DCBFDA63B0F3A15B7E09773B39495322924E8312C"
)
MATRIX_PATH = (
    "docs/experiments/inputs/uprime_u24_upper_stack_portability_matrix.json"
)
MATRIX_BLOB = "845e5de894462ee12a3de1606b3bfe2d7e966d40"
MATRIX_RAW_SHA256 = (
    "81FE1695435BC11526B8752CF80C907D58D0F85A27F678BE0C519C0FEE1E69A8"
)
IDENTITY_PATH = "tests/test_uprime_u24_upper_stack_portability_identity.py"
MANIFEST_PATH = "tests/tier_manifest.json"

H_ALLOWLIST = frozenset(
    {
        "tests/test_uprime_u2_u4_development.py",
        "tests/uprime_u24_guard.py",
        "tools/run_uprime_u2_u4_development_tests.ps1",
        "tests/test_odlrq_similarity.py",
        IDENTITY_PATH,
        MANIFEST_PATH,
    }
)
RESOURCE_PATH = (
    "docs/experiments/"
    "uprime_odlrq_upper_stack_portability_resource_authority_2026-07-18.md"
)
RESULT_PATHS = frozenset(
    {
        "docs/experiments/artifacts/"
        "uprime_u24_upper_stack_portability_20260718/result.json",
        "docs/experiments/"
        "uprime_odlrq_upper_stack_portability_closeout_2026-07-18.md",
    }
)
STAGE_ORDER = ("H", "G1", "G2", "G3", "G4", "A_RES", "R")
STAGE_ATTEMPT_REFS = {
    "H": (
        "refs/heads/codex/uprime-upper-portability-control",
        "refs/heads/codex/uprime-upper-portability-control-a2",
    ),
    "G1": (
        "refs/heads/codex/uprime-upper-portability-g1-e2",
        "refs/heads/codex/uprime-upper-portability-g1-e2-a2",
    ),
    "G2": (
        "refs/heads/codex/uprime-upper-portability-g2-maxent",
        "refs/heads/codex/uprime-upper-portability-g2-maxent-a2",
    ),
    "G3": (
        "refs/heads/codex/uprime-upper-portability-g3-similarity",
        "refs/heads/codex/uprime-upper-portability-g3-similarity-a2",
    ),
    "G4": (
        "refs/heads/codex/uprime-upper-portability-g4-candidate",
        "refs/heads/codex/uprime-upper-portability-g4-candidate-a2",
    ),
    "A_RES": (
        RESOURCE_REF,
        f"{RESOURCE_REF}-a2",
    ),
    "R": (
        "refs/heads/codex/uprime-upper-portability-closeout",
        "refs/heads/codex/uprime-upper-portability-closeout-a2",
    ),
}
STAGE_ALLOWLISTS = {
    "H": H_ALLOWLIST,
    "G1": frozenset(
        {
            "lean_rgc/odlrq/finite_e2.py",
            "lean_rgc/odlrq/__init__.py",
            "tests/test_odlrq_finite_e2.py",
            MANIFEST_PATH,
        }
    ),
    "G2": frozenset(
        {
            "lean_rgc/odlrq/finite_maxent.py",
            "lean_rgc/odlrq/__init__.py",
            "tests/test_odlrq_finite_maxent.py",
            MANIFEST_PATH,
        }
    ),
    "G3": frozenset(
        {
            "lean_rgc/odlrq/finite_similarity.py",
            "lean_rgc/odlrq/__init__.py",
            "tests/test_odlrq_finite_similarity.py",
            MANIFEST_PATH,
        }
    ),
    "G4": frozenset(
        {
            "lean_rgc/odlrq/finite_upper_stack.py",
            "lean_rgc/odlrq/__init__.py",
            "lean_rgc/evals/uprime_u24_upper_stack_portability.py",
            "tests/test_odlrq_finite_upper_stack.py",
            "tests/test_uprime_u24_upper_stack_portability.py",
            MANIFEST_PATH,
        }
    ),
    "A_RES": frozenset({RESOURCE_PATH}),
    "R": RESULT_PATHS,
}
STAGE_MANIFEST_ROWS = {
    "H": {Path(IDENTITY_PATH).name: ["unit"]},
    "G1": {"test_odlrq_finite_e2.py": ["unit"]},
    "G2": {"test_odlrq_finite_maxent.py": ["unit"]},
    "G3": {"test_odlrq_finite_similarity.py": ["unit"]},
    "G4": {
        "test_odlrq_finite_upper_stack.py": ["unit"],
        "test_uprime_u24_upper_stack_portability.py": ["unit"],
    },
    "A_RES": {},
    "R": {},
}
STAGE_TEST_COUNTS = {
    IDENTITY_PATH: 4,
    "tests/test_odlrq_finite_e2.py": 12,
    "tests/test_odlrq_finite_maxent.py": 10,
    "tests/test_odlrq_finite_similarity.py": 12,
    "tests/test_odlrq_finite_upper_stack.py": 8,
    "tests/test_uprime_u24_upper_stack_portability.py": 4,
}
CORE_SOURCE_PATHS = (
    "lean_rgc/odlrq/finite_e2.py",
    "lean_rgc/odlrq/finite_maxent.py",
    "lean_rgc/odlrq/finite_similarity.py",
    "lean_rgc/odlrq/finite_upper_stack.py",
)
EVALUATOR_PATH = "lean_rgc/evals/uprime_u24_upper_stack_portability.py"

EXPECTED_TEST_NAMES = (
    "test_u24_portability_authority_topology_and_natural_count_identity",
    "test_u24_portability_matrix_is_the_only_new_runtime_read_authority",
    "test_u24_portability_ast_capability_and_import_firewall",
    "test_u24_portability_literalness_and_noninput_firewall",
)
NATURAL_TEST_SHAPES = {
    "H": "2642 passed, 8 skipped, 161 deselected",
    "G1": "2654 passed, 8 skipped, 161 deselected",
    "G2": "2664 passed, 8 skipped, 161 deselected",
    "G3": "2676 passed, 8 skipped, 161 deselected",
    "G4": "2688 passed, 8 skipped, 161 deselected",
    "R": "2688 passed, 8 skipped, 161 deselected",
}

_FORBIDDEN_CORE_IMPORT_ROOTS = frozenset(
    {
        "asyncio",
        "builtins",
        "ctypes",
        "glob",
        "http",
        "importlib",
        "io",
        "multiprocessing",
        "os",
        "pathlib",
        "pytest",
        "requests",
        "runpy",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "tempfile",
        "tests",
        "unittest",
        "urllib",
    }
)
_FORBIDDEN_CORE_CALL_NAMES = frozenset(
    {
        "__import__",
        "compile",
        "eval",
        "exec",
        "open",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
    }
)
_OLD_EVALUATOR_MODULE = "lean_rgc.evals.uprime_u2_u4_development"
_OLD_EVALUATOR_NAMES = frozenset(
    {"build_u24_i0_fixture", "build_u24_artifact_wires"}
)


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "--no-replace-objects", *args],
        cwd=REPO_ROOT,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _raw_parents(commit: str) -> list[str]:
    payload = _git("cat-file", "-p", commit).stdout.decode("utf-8")
    return [row[7:] for row in payload.splitlines() if row.startswith("parent ")]


def _tree_blob(revision: str, path: str) -> str:
    return (
        _git("rev-parse", f"{revision}:{path}")
        .stdout.decode("ascii")
        .strip()
    )


def _changed_paths(commit: str) -> set[str]:
    return set(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--no-renames",
            "-r",
            commit,
        )
        .stdout.decode("utf-8")
        .splitlines()
    )


def _status_paths() -> set[str]:
    raw = _git(
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--no-renames",
    ).stdout.decode("utf-8")
    return {row[3:] for row in raw.split("\0") if row}


def _governed_status_paths() -> set[str]:
    dirty = _status_paths()
    setup = set(u24_guard.CI_SETUP_PATHS)
    visible_setup = dirty & setup
    assert visible_setup in (set(), setup)
    return dirty - setup


def _manifest(revision: str) -> dict[str, Any]:
    value = _strict_json(_git("show", f"{revision}:{MANIFEST_PATH}").stdout)
    assert type(value) is dict
    return value


def _assert_manifest_append(
    before: dict[str, Any], after: dict[str, Any], rows: dict[str, list[str]]
) -> None:
    assert set(after) - set(before) == set(rows)
    assert set(before) <= set(after)
    for name, tiers in before.items():
        assert after[name] == tiers
    for name, tiers in rows.items():
        assert after[name] == tiers


def _strict_json(raw: bytes) -> Any:
    def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_pairs,
        parse_constant=reject_constant,
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _source_tree(path: str) -> ast.Module | None:
    candidate = REPO_ROOT / path
    if not candidate.is_file():
        return None
    return ast.parse(candidate.read_text(encoding="utf-8"), filename=path)


def _import_rows(tree: ast.AST) -> Iterable[tuple[ast.AST, str, tuple[str, ...]]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node, alias.name, (alias.name,)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            yield node, node.module, tuple(alias.name for alias in node.names)


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        if prefix is not None:
            return f"{prefix}.{node.attr}"
    return None


def _enclosing_function(tree: ast.AST, target: ast.AST) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and target in set(ast.walk(node)):
            return node
    return None


def _literal_key_access(node: ast.AST, key: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and child.value == key:
            return True
        if isinstance(child, ast.Attribute) and child.attr == key:
            return True
        if isinstance(child, ast.Subscript):
            index = child.slice
            if isinstance(index, ast.Constant) and index.value == key:
                return True
    return False


def _all_literal_values(tree: ast.AST) -> Iterable[Any]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Dict, ast.List, ast.Tuple)):
            continue
        try:
            yield ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError):
            continue


def _assert_exact_test_file(path: str, expected_count: int) -> None:
    candidate = REPO_ROOT / path
    if not candidate.is_file():
        return
    tree = ast.parse(candidate.read_text(encoding="utf-8"), filename=path)
    tests = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    all_tests = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    assert tests == all_tests
    assert len(tests) == expected_count
    assert all(isinstance(node, ast.FunctionDef) for node in tests)
    for node in tests:
        assert not node.decorator_list
        assert not node.args.posonlyargs
        assert not node.args.args
        assert node.args.vararg is None
        assert not node.args.kwonlyargs
        assert node.args.kwarg is None
        assert not node.args.defaults
        assert not node.args.kw_defaults


def test_u24_portability_authority_topology_and_natural_count_identity():
    assert u24_guard.PORTABILITY_AUTHORITY_COMMIT == AUTHORITY_COMMIT
    assert u24_guard.PORTABILITY_AUTHORITY_PARENT == AUTHORITY_PARENT
    assert u24_guard.PORTABILITY_AUTHORITY_TREE == AUTHORITY_TREE
    assert u24_guard.PORTABILITY_AUTHORITY_REF == AUTHORITY_REF
    assert u24_guard.PORTABILITY_AUTHORITY_DOCUMENT_PATH == AUTHORITY_DOCUMENT_PATH
    assert u24_guard.PORTABILITY_AUTHORITY_DOCUMENT_BLOB == AUTHORITY_DOCUMENT_BLOB
    assert (
        u24_guard.PORTABILITY_AUTHORITY_DOCUMENT_RAW_SHA256
        == AUTHORITY_DOCUMENT_RAW_SHA256
    )
    assert u24_guard.PORTABILITY_MATRIX_PATH == MATRIX_PATH
    assert u24_guard.PORTABILITY_MATRIX_BLOB == MATRIX_BLOB
    assert u24_guard.PORTABILITY_MATRIX_RAW_SHA256 == MATRIX_RAW_SHA256
    assert u24_guard.PORTABILITY_ACCEPTED_REF == ACCEPTED_REF
    assert u24_guard.PORTABILITY_RESOURCE_REF == RESOURCE_REF
    assert frozenset(u24_guard.PORTABILITY_H_ALLOWLIST) == H_ALLOWLIST
    assert tuple(STAGE_ALLOWLISTS) == STAGE_ORDER
    assert tuple(STAGE_ATTEMPT_REFS) == STAGE_ORDER
    assert tuple(STAGE_MANIFEST_ROWS) == STAGE_ORDER

    assert _raw_parents(AUTHORITY_COMMIT) == [AUTHORITY_PARENT]
    assert _git("rev-parse", f"{AUTHORITY_COMMIT}^{{tree}}").stdout.decode(
        "ascii"
    ).strip() == AUTHORITY_TREE
    assert _changed_paths(AUTHORITY_COMMIT) == {
        AUTHORITY_DOCUMENT_PATH,
        MATRIX_PATH,
    }
    assert _tree_blob(AUTHORITY_COMMIT, AUTHORITY_DOCUMENT_PATH) == (
        AUTHORITY_DOCUMENT_BLOB
    )
    assert _tree_blob(AUTHORITY_COMMIT, MATRIX_PATH) == MATRIX_BLOB

    ref_probe = _git("show-ref", "--verify", "--quiet", AUTHORITY_REF, check=False)
    if ref_probe.returncode == 0:
        assert _git("rev-parse", AUTHORITY_REF).stdout.decode("ascii").strip() == (
            AUTHORITY_COMMIT
        )

    document = (REPO_ROOT / AUTHORITY_DOCUMENT_PATH).read_bytes()
    assert _sha256(document) == AUTHORITY_DOCUMENT_RAW_SHA256
    text = document.decode("utf-8", errors="strict")
    assert f"`{AUTHORITY_REF}`" in text
    assert f"`{ACCEPTED_REF}`" in text
    assert f"`{RESOURCE_REF}`" in text
    for stage_refs in STAGE_ATTEMPT_REFS.values():
        displayed_ref = stage_refs[0].removeprefix("refs/heads/")
        assert displayed_ref in text
    assert "`2638 passed, 8 skipped, 161 deselected`" in text
    for stage, shape in NATURAL_TEST_SHAPES.items():
        assert f"| {stage} | `{shape}` |" in text

    for path, expected_count in STAGE_TEST_COUNTS.items():
        _assert_exact_test_file(path, expected_count)
    identity_tree = ast.parse(
        (REPO_ROOT / IDENTITY_PATH).read_text(encoding="utf-8"),
        filename=IDENTITY_PATH,
    )
    assert tuple(
        node.name
        for node in identity_tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ) == EXPECTED_TEST_NAMES

    manifest = _strict_json((REPO_ROOT / MANIFEST_PATH).read_bytes())
    assert manifest[Path(IDENTITY_PATH).name] == ["unit"]

    head = _git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    if head == AUTHORITY_COMMIT:
        dirty = _governed_status_paths()
        assert {IDENTITY_PATH, MANIFEST_PATH} <= dirty
        assert dirty <= H_ALLOWLIST
        _assert_manifest_append(
            _manifest(AUTHORITY_COMMIT), manifest, STAGE_MANIFEST_ROWS["H"]
        )
    else:
        interval = (
            _git(
                "rev-list",
                "--first-parent",
                "--reverse",
                f"{AUTHORITY_COMMIT}..{head}",
            )
            .stdout.decode("ascii")
            .splitlines()
        )
        assert 1 <= len(interval) <= len(STAGE_ORDER)
        previous = AUTHORITY_COMMIT
        previous_manifest = _manifest(previous)
        for stage, commit in zip(
            STAGE_ORDER[: len(interval)], interval, strict=True
        ):
            assert _raw_parents(commit) == [previous]
            assert _changed_paths(commit) == STAGE_ALLOWLISTS[stage]
            assert _tree_blob(commit, AUTHORITY_DOCUMENT_PATH) == (
                AUTHORITY_DOCUMENT_BLOB
            )
            assert _tree_blob(commit, MATRIX_PATH) == MATRIX_BLOB
            current_manifest = _manifest(commit)
            _assert_manifest_append(
                previous_manifest,
                current_manifest,
                STAGE_MANIFEST_ROWS[stage],
            )
            visible_refs: list[tuple[str, str]] = []
            for stage_ref in STAGE_ATTEMPT_REFS[stage]:
                ref_probe = _git(
                    "show-ref", "--verify", "--quiet", stage_ref, check=False
                )
                if ref_probe.returncode == 0:
                    observed = _git("rev-parse", stage_ref).stdout.decode(
                        "ascii"
                    ).strip()
                    visible_refs.append((stage_ref, observed))
            if visible_refs:
                selected_refs = [
                    stage_ref
                    for stage_ref, observed in visible_refs
                    if observed == commit
                ]
                assert len(selected_refs) == 1
                for _stage_ref, observed in visible_refs:
                    if observed == commit:
                        continue
                    assert _raw_parents(observed) == [previous]
                    assert _changed_paths(observed) == STAGE_ALLOWLISTS[stage]
            previous = commit
            previous_manifest = current_manifest

        dirty = _governed_status_paths()
        if len(interval) >= STAGE_ORDER.index("A_RES") + 1:
            assert not dirty
        else:
            assert dirty <= STAGE_ALLOWLISTS[STAGE_ORDER[len(interval)]]

    u24_guard.validate_u24_portability_control(REPO_ROOT)


def test_u24_portability_matrix_is_the_only_new_runtime_read_authority():
    assert "docs/experiments/inputs/" in u24_guard.DENYLIST_ROWS
    assert "docs/experiments/artifacts/" in u24_guard.DENYLIST_ROWS
    raw = (REPO_ROOT / MATRIX_PATH).read_bytes()
    assert _sha256(raw) == MATRIX_RAW_SHA256
    assert _tree_blob(AUTHORITY_COMMIT, MATRIX_PATH) == MATRIX_BLOB
    matrix = _strict_json(raw)
    assert matrix["schema_version"] == (
        "lean-rgc-uprime-u24-upper-stack-portability-matrix-v1"
    )
    assert matrix["family_order"] == [
        "orbit_symmetry",
        "nilpotent_nonnormal",
        "ghost_return_memory",
        "separator_rank2_coupling",
    ]

    policy = u24_guard.GuardPolicy(u24_guard.GuardMode.SEMANTIC, REPO_ROOT)
    with u24_guard.install_guard(policy):
        assert _sha256((REPO_ROOT / MATRIX_PATH).read_bytes()) == MATRIX_RAW_SHA256
        for forbidden in (
            "docs/experiments/inputs/uprime_u15_l0_matrix.json",
            "docs/experiments/inputs/uprime_kp3_d4_actions.json",
            "docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717/"
            "locality_cegar_result.json",
        ):
            try:
                (REPO_ROOT / forbidden).read_bytes()
            except u24_guard.U24ResourceOrScopeBlocked:
                pass
            else:
                raise AssertionError(f"guard admitted forbidden runtime input: {forbidden}")
        try:
            u24_guard._check_path(policy, REPO_ROOT / MATRIX_PATH, write=True)
        except u24_guard.U24ResourceOrScopeBlocked:
            pass
        else:
            raise AssertionError("matrix exception admitted write capability")
        try:
            u24_guard._check_path(
                policy,
                REPO_ROOT / MATRIX_PATH,
                read=True,
                enumerate_directory=True,
            )
        except u24_guard.U24ResourceOrScopeBlocked:
            pass
        else:
            raise AssertionError("matrix exception admitted directory enumeration")


def test_u24_portability_ast_capability_and_import_firewall():
    assert tuple(u24_guard.PORTABILITY_CORE_SOURCE_PATHS) == CORE_SOURCE_PATHS
    assert u24_guard.PORTABILITY_EVALUATOR_PATH == EVALUATOR_PATH
    assert set(u24_guard.PORTABILITY_CORE_IMPORT_MODULES) == set(CORE_SOURCE_PATHS)
    for allowed in u24_guard.PORTABILITY_CORE_IMPORT_MODULES.values():
        assert "lean_rgc.odlrq.maxent" not in allowed
        assert "lean_rgc.odlrq.similarity" not in allowed
        assert "lean_rgc.odlrq.selection" not in allowed
        assert "lean_rgc.odlrq.certificates" not in allowed
        assert "lean_rgc.odlrq" not in allowed
    u24_guard.verify_u24_portability_source_firewall(REPO_ROOT)

    presence = tuple((REPO_ROOT / path).is_file() for path in CORE_SOURCE_PATHS)
    evaluator_present = (REPO_ROOT / EVALUATOR_PATH).is_file()
    assert (presence, evaluator_present) in {
        ((False, False, False, False), False),  # H control handoff
        ((True, False, False, False), False),   # G1 finite E2
        ((True, True, False, False), False),    # G2 finite MaxEnt
        ((True, True, True, False), False),     # G3 finite similarity
        ((True, True, True, True), True),       # G4 integrated evaluator
    }

    for path in CORE_SOURCE_PATHS:
        tree = _source_tree(path)
        if tree is None:
            continue
        allowed_internal = set(u24_guard.PORTABILITY_CORE_IMPORT_MODULES[path])
        allowed_stdlib = set(u24_guard.PORTABILITY_PURE_STDLIB_IMPORT_ROOTS)
        for _node, module, _aliases in u24_guard._resolved_import_rows(
            tree, package="lean_rgc.odlrq"
        ):
            assert (
                module.split(".", 1)[0] in allowed_stdlib
                or module in allowed_internal
            )
        for _node, module, _names in _import_rows(tree):
            assert module.split(".", 1)[0] not in _FORBIDDEN_CORE_IMPORT_ROOTS
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _qualified_name(node.func)
            assert name is None or name.rsplit(".", 1)[-1] not in (
                _FORBIDDEN_CORE_CALL_NAMES
            )

    evaluator = _source_tree(EVALUATOR_PATH)
    if evaluator is None:
        return
    old_imports = [
        (node, names)
        for node, module, names in _import_rows(evaluator)
        if module == _OLD_EVALUATOR_MODULE
    ]
    assert len(old_imports) == 1
    old_node, old_names = old_imports[0]
    assert frozenset(old_names) == _OLD_EVALUATOR_NAMES
    assert _enclosing_function(evaluator, old_node) is not None
    for _node, module, _names in _import_rows(evaluator):
        root = module.split(".", 1)[0]
        if module != _OLD_EVALUATOR_MODULE:
            assert root not in {
                "asyncio",
                "builtins",
                "ctypes",
                "glob",
                "http",
                "importlib",
                "io",
                "multiprocessing",
                "os",
                "requests",
                "runpy",
                "shutil",
                "socket",
                "subprocess",
                "sys",
                "tempfile",
                "tests",
                "unittest",
                "urllib",
            }
    matrix_bindings = [
        node.targets[0].id
        for node in evaluator.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
        and node.value.value == MATRIX_PATH
    ]
    matrix_bindings.extend(
        node.target.id
        for node in evaluator.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
        and node.value.value == MATRIX_PATH
    )
    matrix_reads = [
        node
        for node in ast.walk(evaluator)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_bytes"
    ]
    assert len(matrix_bindings) == 1
    assert len(matrix_reads) == 1
    assert not matrix_reads[0].args and not matrix_reads[0].keywords
    assert u24_guard._is_exact_matrix_receiver(
        matrix_reads[0].func.value, matrix_bindings[0]
    )


def test_u24_portability_literalness_and_noninput_firewall():
    u24_guard.verify_u24_portability_source_firewall(REPO_ROOT)
    matrix = _strict_json((REPO_ROOT / MATRIX_PATH).read_bytes())
    family_ids = frozenset(matrix["family_order"])
    forbidden_strings = family_ids.union(
        {
            "docs/experiments/inputs/uprime_u15_l0_matrix.json",
            "docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717/"
            "locality_cegar_result.json",
            "ee7a1c01dba376881d20962de664f4908acc7b0d",
            "c1f1957a3372f80f71b85151a793a4fa0fb218fa",
            "8ec852aa3a82be237841f81bf41f3cf8a6ef4cd4",
        }
    )
    forbidden_structures: list[Any] = []
    for family in matrix["families"]:
        forbidden_structures.extend(
            (
                family["signed_coordinate_matrix_target_row_source_column"],
                family["expected_positive_envelope"],
                family["expected_return_memory"],
                family["expected_maxent_probabilities"],
                family["expected_hard_bound"],
            )
        )
    forbidden_structure_bytes = {
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        for value in forbidden_structures
    }

    trees: list[tuple[str, ast.Module]] = []
    for path in (*CORE_SOURCE_PATHS, EVALUATOR_PATH):
        tree = _source_tree(path)
        if tree is not None:
            trees.append((path, tree))
    for path, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and type(node.value) is str:
                assert node.value not in forbidden_strings, (path, node.lineno)
            if isinstance(
                node,
                (ast.If, ast.IfExp, ast.While, ast.Match, ast.BoolOp),
            ):
                assert not _literal_key_access(node, "family_id"), (
                    path,
                    node.lineno,
                )
            if isinstance(node, ast.Call):
                assert not _literal_key_access(node.func, "family_id"), (
                    path,
                    node.lineno,
                )
            if isinstance(node, ast.Subscript) and not (
                isinstance(node.slice, ast.Constant)
                and node.slice.value == "family_id"
            ):
                assert not _literal_key_access(node.slice, "family_id"), (
                    path,
                    node.lineno,
                )
        for value in _all_literal_values(tree):
            try:
                encoded = json.dumps(
                    value,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            except (TypeError, ValueError):
                continue
            assert encoded not in forbidden_structure_bytes, path

    fragment_prefix = f'''from pathlib import Path
import json
_MATRIX_PATH = "{MATRIX_PATH}"

def evaluate(record, handlers):
    matrix = json.loads((Path(__file__).parents[2] / _MATRIX_PATH).read_bytes())
    rows = []
    for order_id, row in zip(matrix["family_order"], matrix["families"], strict=True):
'''

    def fragment(body: str, *, helpers: str = "") -> ast.Module:
        indented = "".join(f"        {line}\n" for line in body.splitlines())
        return ast.parse(helpers + fragment_prefix + indented)

    for allowed in (
        fragment(
            'fid = row["family_id"]\n'
            'label = f"u24__{fid}"\n'
            'rows.append({"family_id": fid, "label": label})\n'
            'rows.append({"label": label})\n'
            "record(fid)"
        ),
        fragment(
            'index = 0\nvalue = row["block_sizes"][index]\n'
            "record(value)\nrecord(order_id)"
        ),
        fragment(
            'fid = row["family_id"]\nrecord(fid)',
            helpers=(
                'def harmless(obj):\n    key = "status"\n'
                '    if obj["status"]:\n        return key\n    return ""\n\n'
            ),
        ),
    ):
        u24_guard._reject_family_identity_dispatch(allowed)

    rejected = (
        fragment(
            'key = "family_%s" % ("id",)\n'
            "fid = row[key]\nif fid:\n    record(fid)"
        ),
        fragment(
            'suffix = "id"\nkey = "family_{suffix}".format(suffix=suffix)\n'
            "fid = row[key]\nif fid:\n    record(fid)"
        ),
        fragment(
            'key = operator.add("family_", "id")\n'
            "fid = row[key]\nif fid:\n    record(fid)",
            helpers="import operator\n",
        ),
        fragment(
            'key = "".join(chr(n) for n in '
            "(102, 97, 109, 105, 108, 121, 95, 105, 100))\n"
            "fid = row[key]\nif fid:\n    record(fid)"
        ),
        fragment('fid = row.get("family_id")\nif fid:\n    record(fid)'),
        fragment(
            'fid = operator.getitem(row, "family_id")\n'
            "if fid:\n    record(fid)",
            helpers="import operator\n",
        ),
        fragment(
            'fid = row["family_id"]\n'
            'chosen = fid.startswith("o") and handlers[0] or handlers[1]\n'
            "record(chosen)"
        ),
        fragment('fid = row["family_id"]\nhandlers[fid]()'),
        fragment(
            'fid = row["family_id"]\nselected = handlers[fid]\nrecord(selected)'
        ),
        fragment(
            'fid = row["family_id"]\nrecord(choose(fid))',
            helpers=(
                "def choose(value):\n    if value:\n        return 1\n"
                "    return 0\n\n"
            ),
        ),
        fragment('fid = row["family_id"]\nrecord(fid == "")'),
        fragment(
            'fid = row["family_id"]\napply(choose, fid, record)',
            helpers=(
                "def choose(value, record):\n    if value:\n"
                "        record(1)\n\n"
            ),
        ),
        fragment('row["block_sizes"] = [999]\nrecord(order_id)'),
        fragment('del row["family_id"]\nrecord(order_id)'),
        fragment('row["block_sizes"] += [999]\nrecord(order_id)'),
        fragment('row["block_sizes"].append(999)\nrecord(order_id)'),
        fragment('row["block_sizes"].__setitem__(0, 999)\nrecord(order_id)'),
        fragment(
            'sizes = row["block_sizes"]\nsizes.append(999)\nrecord(order_id)'
        ),
        fragment("row += row\nrecord(order_id)"),
        fragment(
            'fid = row["family_id"]\nbox = []\nbox.append(fid)\n'
            "if box[0]:\n    record(fid)"
        ),
        fragment(
            'fid = row["family_id"]\nbox = {}\n'
            'box.update({"x": fid})\nif box["x"]:\n    record(fid)'
        ),
        fragment(
            'fid = row["family_id"]\nboxes = [[]]\n'
            "boxes[0].append(fid)\nif boxes[0][0]:\n    record(fid)"
        ),
        fragment(
            'fid = row["family_id"]\nbox = []\nmutate((box,), fid)\n'
            "if box[0]:\n    record(fid)",
            helpers=(
                "def mutate(containers, value):\n"
                "    containers[0].append(value)\n\n"
            ),
        ),
        fragment(
            'j.loads = parser\nfid = row["family_id"]\nrecord(fid)',
            helpers="import json as j\n",
        ),
        fragment(
            'fid = row["family_id"]\ntry:\n    raise ValueError(fid)\n'
            "except ValueError as error:\n    if error.args[0]:\n"
            "        record(fid)"
        ),
    )
    for attacked in rejected:
        try:
            u24_guard._reject_family_identity_dispatch(attacked)
        except u24_guard.U24ResourceOrScopeBlocked:
            pass
        else:
            raise AssertionError("family-row positive fragment admitted an attack")

    assert u24_guard.PORTABILITY_CORE_FAMILY_LABEL_SINKS == (
        "lean_rgc.odlrq.contracts.CanonicalPayload.from_value",
        "lean_rgc.odlrq.contracts.canonical_contract_bytes",
    )

    def core_sources(**sources: str) -> dict[str, ast.Module]:
        return {module: ast.parse(source) for module, source in sources.items()}

    core_positive = core_sources(
        **{
            "lean_rgc.odlrq.finite_e2": (
                "from dataclasses import dataclass\n"
                "from lean_rgc.odlrq.contracts import "
                "CanonicalPayload, canonical_contract_bytes\n"
                "@dataclass(frozen=True)\n"
                "class Label:\n"
                "    family_id: str\n"
                "    def wire(self):\n"
                "        return f'label:{self.family_id}'\n"
                "def store(family_id):\n"
                "    stored = Label(family_id=family_id)\n"
                "    label = f'label:{family_id}'\n"
                 "    payload = CanonicalPayload.from_value("
                 "{'family_id': family_id, 'label': label})\n"
                 "    wire = canonical_contract_bytes(payload)\n"
                 "    return (stored, label, wire)\n"
                 "def local_accumulator(values):\n"
                 "    rows = []\n"
                 "    nested = {'rows': []}\n"
                 "    for value in values:\n"
                 "        rows.append(value)\n"
                 "        nested['rows'].append(value)\n"
                 "    return (rows, nested)\n"
             )
         }
     )
    u24_guard._reject_core_family_identity_dispatch(core_positive)

    core_attacks = (
        core_sources(
            **{
                "lean_rgc.odlrq.finite_e2": (
                    "def choose(value):\n"
                    "    if value:\n        return 1\n"
                    "    return 0\n"
                ),
                "lean_rgc.odlrq.finite_maxent": (
                    "from lean_rgc.odlrq.finite_e2 import choose\n"
                    "def route(family_id):\n"
                    "    return choose(family_id)\n"
                ),
            }
        ),
        core_sources(
            **{
                "lean_rgc.odlrq.finite_e2": (
                    "class Label:\n"
                    "    def decide(self):\n"
                    "        if self.family_id:\n            return 1\n"
                    "        return 0\n"
                )
            }
        ),
        core_sources(
            **{
                "lean_rgc.odlrq.finite_e2": (
                    "def route(family_id):\n"
                    "    return external(family_id)\n"
                )
            }
        ),
        core_sources(
            **{
                "lean_rgc.odlrq.finite_e2": (
                    "def choose(value):\n"
                    "    if value:\n        return 1\n"
                    "    return 0\n"
                    "def route(family_id, apply):\n"
                    "    return apply(choose, family_id)\n"
                )
            }
        ),
        core_sources(
            **{
                "lean_rgc.odlrq.finite_e2": (
                    "def choose(left, right):\n"
                    "    if right:\n        return 1\n"
                    "    return 0\n"
                    "def route(family_id):\n"
                    "    args = (0, family_id)\n"
                    "    return choose(*args)\n"
                )
            }
        ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "def route(family_id, other):\n"
                     "    return (family_id == other) * 7\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "_CACHE = {}\n"
                     "def save(family_id):\n"
                     "    _CACHE['selector'] = family_id\n"
                     "def choose():\n"
                     "    if _CACHE['selector']:\n"
                     "        return 1\n"
                     "    return 0\n"
                     "def run(family_id):\n"
                     "    save(family_id)\n"
                     "    return choose()\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "from itertools import count\n"
                     "_COUNTER = count()\n"
                     "def route(family_id):\n"
                     "    return next(_COUNTER)\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "def mutate_shared(shared):\n"
                     "    box = [shared]\n"
                     "    box[0].append(1)\n"
                     "    return shared\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "def mutate_shared(shared):\n"
                     "    return shared.__iadd__([1])\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "def mutate_shared(shared):\n"
                     "    shared.appendleft(1)\n"
                     "    return shared\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "def route(row):\n"
                     "    key = 'family_' + 'id'\n"
                     "    fid = row[key]\n"
                     "    target = 'orbit_' + 'symmetry'\n"
                     "    return 1 if fid == target else 0\n"
                 )
             }
         ),
         core_sources(
             **{
                 "lean_rgc.odlrq.finite_e2": (
                     "def route(row):\n"
                     "    key = ''.join(chr(n) for n in "
                     "(102, 97, 109, 105, 108, 121, 95, 105, 100))\n"
                     "    fid = row[key]\n"
                     "    return bool(fid)\n"
                 )
             }
         ),
     )
    for attacked in core_attacks:
        try:
            u24_guard._reject_core_family_identity_dispatch(attacked)
        except u24_guard.U24ResourceOrScopeBlocked:
            pass
        else:
            raise AssertionError("core family-control attack was admitted")

    entry_core = core_sources(
        **{
            "lean_rgc.odlrq.finite_e2": (
                "def choose(value):\n"
                "    if value:\n        return 1\n"
                "    return 0\n"
            )
        }
    )
    entry_attack = fragment(
        'fid = row["family_id"]\nresult = choose(fid)\nrecord(result)',
        helpers="from lean_rgc.odlrq.finite_e2 import choose\n",
    )
    try:
        u24_guard._reject_core_family_identity_dispatch(
            entry_core,
            entrypoint=entry_attack,
        )
    except u24_guard.U24ResourceOrScopeBlocked:
        pass
    else:
        raise AssertionError("evaluator-to-core family dispatch was admitted")

    evaluator = dict(trees).get(EVALUATOR_PATH)
    if evaluator is None:
        return
    family_order_loops = [
        node
        for node in ast.walk(evaluator)
        if isinstance(node, (ast.For, ast.comprehension))
        and _literal_key_access(node.iter, "family_order")
    ]
    assert family_order_loops
