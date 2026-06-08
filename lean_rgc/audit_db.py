from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "lean-rgc-audit-db-v24.0"


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = {"_parse_error": True, "raw_line": line}
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                rows.append({"value": obj})
    return rows


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_parse_error": str(exc), "raw_text_prefix": path.read_text(encoding="utf-8", errors="replace")[:2000]}


def _round_from_path(path: Path) -> int | None:
    for part in path.parts:
        m = re.match(r"round_(\d+)$", part)
        if m:
            return int(m.group(1))
    return None


def _kind_from_path(path: Path) -> str:
    name = path.name
    parent = path.parent.name
    if name == "micro_audit.jsonl":
        return "audit"
    if name == "responses.jsonl":
        if parent == "audit":
            return "responses_base"
        return f"responses_{parent}"
    if name == "defects.jsonl":
        return "defects"
    if name.endswith("accepted_actions.jsonl"):
        return "accepted_actions"
    if name.endswith("acceptance_rows.jsonl"):
        return "acceptance_rows"
    if name.endswith("candidates.jsonl"):
        return "candidate_actions"
    if name.endswith("actions.jsonl"):
        return "actions"
    if name == "qgen_carrier_incidence.jsonl" or name.endswith("carrier_incidence.jsonl"):
        return "carrier_incidence"
    if name == "qgen_carrier_incidence_audited.jsonl":
        return "carrier_incidence_audited"
    if "poms_status" in name:
        return "poms_status"
    if "poms_promotion" in name:
        return "poms_promotion"
    if "lineage" in name:
        return "lineage"
    if "action_geometry" in name:
        return "action_geometry"
    if name.endswith(".json"):
        return "json_report"
    return "jsonl"


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_dir TEXT,
            rel_path TEXT,
            abs_path TEXT,
            kind TEXT,
            round INTEGER,
            sha256 TEXT,
            n_rows INTEGER,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_unique ON artifacts(abs_path, sha256);

        CREATE TABLE IF NOT EXISTS audit_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            task_id TEXT,
            state_id TEXT,
            action_id TEXT,
            status TEXT,
            elapsed_ms REAL,
            heartbeats REAL,
            response_json TEXT,
            carrier_delta_json TEXT,
            defect_before_json TEXT,
            defect_after_json TEXT,
            audit_flags_json TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_audit_task_action ON audit_rows(task_id, action_id);
        CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_rows(status);

        CREATE TABLE IF NOT EXISTS response_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            state_id TEXT,
            action_id TEXT,
            audit_status TEXT,
            success INTEGER,
            response_json TEXT,
            carrier_delta_json TEXT,
            defect_before_json TEXT,
            defect_after_json TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_response_state_action ON response_rows(state_id, action_id);
        CREATE INDEX IF NOT EXISTS idx_response_status ON response_rows(audit_status);

        CREATE TABLE IF NOT EXISTS response_values (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            state_id TEXT,
            action_id TEXT,
            response_key TEXT,
            value REAL
        );
        CREATE INDEX IF NOT EXISTS idx_response_values_key ON response_values(response_key);
        CREATE INDEX IF NOT EXISTS idx_response_values_action ON response_values(action_id);

        CREATE TABLE IF NOT EXISTS carrier_values (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            state_id TEXT,
            action_id TEXT,
            carrier_key TEXT,
            value REAL
        );
        CREATE INDEX IF NOT EXISTS idx_carrier_values_key ON carrier_values(carrier_key);
        CREATE INDEX IF NOT EXISTS idx_carrier_values_action ON carrier_values(action_id);

        CREATE TABLE IF NOT EXISTS action_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            action_id TEXT,
            tactic TEXT,
            tactic_class TEXT,
            source TEXT,
            canonical_status TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_action_id ON action_rows(action_id);
        CREATE INDEX IF NOT EXISTS idx_action_source ON action_rows(source);

        CREATE TABLE IF NOT EXISTS acceptance_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            action_id TEXT,
            state_id TEXT,
            accepted INTEGER,
            margin REAL,
            robust_margin REAL,
            score REAL,
            accepted_by TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_acceptance_action ON acceptance_rows(action_id);
        CREATE INDEX IF NOT EXISTS idx_acceptance_accepted ON acceptance_rows(accepted);

        CREATE TABLE IF NOT EXISTS poms_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            record_id TEXT,
            kind TEXT,
            status TEXT,
            promoted_status TEXT,
            canonical_status TEXT,
            action_id TEXT,
            carrier_atom TEXT,
            residual_key TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_poms_status ON poms_rows(status, promoted_status);

        CREATE TABLE IF NOT EXISTS lineage_nodes (
            artifact_id INTEGER,
            node_id TEXT,
            node_type TEXT,
            action_id TEXT,
            residual_key TEXT,
            status TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, node_id)
        );
        CREATE TABLE IF NOT EXISTS lineage_edges (
            artifact_id INTEGER,
            edge_index INTEGER,
            src TEXT,
            dst TEXT,
            edge_type TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, edge_index)
        );

        CREATE TABLE IF NOT EXISTS json_reports (
            artifact_id INTEGER PRIMARY KEY,
            round INTEGER,
            kind TEXT,
            raw_json TEXT
        );
        """
    )
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("schema_version", SCHEMA_VERSION))
    conn.commit()


def _insert_artifact(conn: sqlite3.Connection, run_dir: Path, path: Path, kind: str, n_rows: int) -> int:
    abs_path = str(path.resolve())
    rel_path = str(path.resolve().relative_to(run_dir.resolve())) if _is_relative_to(path.resolve(), run_dir.resolve()) else str(path)
    sha = _sha256_file(path) if path.exists() else ""
    rnd = _round_from_path(path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO artifacts(run_dir, rel_path, abs_path, kind, round, sha256, n_rows)
        VALUES (?,?,?,?,?,?,?)
        """,
        (str(run_dir.resolve()), rel_path, abs_path, kind, rnd, sha, n_rows),
    )
    cur.execute("SELECT artifact_id FROM artifacts WHERE abs_path=? AND sha256=?", (abs_path, sha))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"failed to insert artifact {path}")
    return int(row[0])


def _is_relative_to(p: Path, base: Path) -> bool:
    try:
        p.relative_to(base)
        return True
    except Exception:
        return False


def _row_success(status: Any) -> int:
    return 1 if str(status).lower() in {"success", "ok", "proved"} else 0


def _extract_response_map(row: dict[str, Any]) -> dict[str, float]:
    r = row.get("response")
    if isinstance(r, dict):
        return {str(k): _as_float(v) for k, v in r.items()}
    keys = row.get("response_keys")
    vals = row.get("response_flat")
    if isinstance(keys, list) and isinstance(vals, list):
        return {str(k): _as_float(v) for k, v in zip(keys, vals)}
    return {}


def _extract_carrier_map(row: dict[str, Any]) -> dict[str, float]:
    cd = row.get("carrier_delta") or row.get("carrier_embedding") or row.get("carrier_deltas")
    if isinstance(cd, dict):
        return {str(k): _as_float(v) for k, v in cd.items() if isinstance(v, (int, float, str))}
    return {}


def _action_id(row: dict[str, Any]) -> str:
    return str(row.get("action_id") or row.get("id") or row.get("candidate_id") or row.get("tactic") or "")


def _state_id(row: dict[str, Any]) -> str:
    return str(row.get("state_id") or row.get("task_id") or row.get("state") or "")


def _insert_audit_rows(conn: sqlite3.Connection, artifact_id: int, round_id: int | None, rows: list[dict[str, Any]]) -> None:
    cur = conn.cursor()
    for i, row in enumerate(rows):
        response = _extract_response_map(row)
        carrier = _extract_carrier_map(row)
        cur.execute(
            """
            INSERT OR REPLACE INTO audit_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                artifact_id,
                i,
                round_id,
                str(row.get("task_id", "")),
                str(row.get("state_id", "")),
                _action_id(row),
                str(row.get("status", row.get("audit_status", ""))),
                _as_float(row.get("elapsed_ms")),
                _as_float(row.get("heartbeats"), 0.0),
                _json_dumps(response),
                _json_dumps(carrier),
                _json_dumps(row.get("defect_before")),
                _json_dumps(row.get("defect_after")),
                _json_dumps(row.get("audit_flags")),
                _json_dumps(row),
            ),
        )


def _insert_response_rows(conn: sqlite3.Connection, artifact_id: int, round_id: int | None, rows: list[dict[str, Any]]) -> None:
    cur = conn.cursor()
    for i, row in enumerate(rows):
        response = _extract_response_map(row)
        carrier = _extract_carrier_map(row)
        state = _state_id(row)
        action = _action_id(row)
        status = str(row.get("audit_status", row.get("status", "")))
        cur.execute(
            """
            INSERT OR REPLACE INTO response_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                artifact_id,
                i,
                round_id,
                state,
                action,
                status,
                _row_success(status),
                _json_dumps(response),
                _json_dumps(carrier),
                _json_dumps(row.get("defect_before")),
                _json_dumps(row.get("defect_after")),
                _json_dumps(row),
            ),
        )
        for k, v in response.items():
            cur.execute("INSERT INTO response_values VALUES (?,?,?,?,?,?,?)", (artifact_id, i, round_id, state, action, k, _as_float(v)))
        for k, v in carrier.items():
            cur.execute("INSERT INTO carrier_values VALUES (?,?,?,?,?,?,?)", (artifact_id, i, round_id, state, action, k, _as_float(v)))


def _insert_action_rows(conn: sqlite3.Connection, artifact_id: int, round_id: int | None, rows: list[dict[str, Any]]) -> None:
    cur = conn.cursor()
    for i, row in enumerate(rows):
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        cur.execute(
            "INSERT OR REPLACE INTO action_rows VALUES (?,?,?,?,?,?,?,?,?)",
            (
                artifact_id,
                i,
                round_id,
                _action_id(row),
                str(row.get("tactic", "")),
                str(row.get("tactic_class", row.get("class", ""))),
                str(row.get("source", meta.get("source", ""))),
                str(row.get("canonical_status", meta.get("canonical_status", ""))),
                _json_dumps(row),
            ),
        )


def _insert_acceptance_rows(conn: sqlite3.Connection, artifact_id: int, round_id: int | None, rows: list[dict[str, Any]]) -> None:
    cur = conn.cursor()
    for i, row in enumerate(rows):
        accepted = row.get("accepted")
        if accepted is None:
            accepted = row.get("is_accepted")
        if accepted is None:
            accepted = row.get("accepted_by") is not None or row.get("status") in {"accepted", "robust_accepted"}
        cur.execute(
            "INSERT OR REPLACE INTO acceptance_rows VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                artifact_id,
                i,
                round_id,
                _action_id(row),
                _state_id(row),
                1 if bool(accepted) else 0,
                _as_float(row.get("margin", row.get("coker_margin", row.get("net_margin")))) ,
                _as_float(row.get("robust_margin", row.get("lcb", row.get("heldout_margin")))) ,
                _as_float(row.get("score", row.get("net_score"))),
                str(row.get("accepted_by", row.get("status", ""))),
                _json_dumps(row),
            ),
        )


def _insert_poms_rows(conn: sqlite3.Connection, artifact_id: int, round_id: int | None, rows: list[dict[str, Any]]) -> None:
    cur = conn.cursor()
    for i, row in enumerate(rows):
        cur.execute(
            "INSERT OR REPLACE INTO poms_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                artifact_id,
                i,
                round_id,
                str(row.get("id", row.get("record_id", row.get("action_id", i)))),
                str(row.get("kind", "")),
                str(row.get("status", "")),
                str(row.get("promoted_status", "")),
                str(row.get("canonical_status", "")),
                _action_id(row),
                str(row.get("carrier_atom", "")),
                str(row.get("residual_key", "")),
                _json_dumps(row),
            ),
        )


def _insert_lineage(conn: sqlite3.Connection, artifact_id: int, obj: Any) -> None:
    cur = conn.cursor()
    if not isinstance(obj, dict):
        return
    nodes = obj.get("nodes") or []
    if isinstance(nodes, dict):
        nodes = [{"node_id": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in nodes.items()]
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("node_id", node.get("id", node.get("key", ""))))
        if not nid:
            nid = hashlib.sha256(_json_dumps(node).encode()).hexdigest()[:16]
        cur.execute(
            "INSERT OR REPLACE INTO lineage_nodes VALUES (?,?,?,?,?,?,?)",
            (artifact_id, nid, str(node.get("type", node.get("node_type", ""))), _action_id(node), str(node.get("residual_key", "")), str(node.get("status", "")), _json_dumps(node)),
        )
    edges = obj.get("edges") or []
    if isinstance(edges, dict):
        edges = [{"src": k.split("->")[0] if "->" in k else k, "dst": k.split("->")[-1], **(v if isinstance(v, dict) else {})} for k, v in edges.items()]
    for i, edge in enumerate(edges if isinstance(edges, list) else []):
        if not isinstance(edge, dict):
            continue
        cur.execute(
            "INSERT OR REPLACE INTO lineage_edges VALUES (?,?,?,?,?,?)",
            (artifact_id, i, str(edge.get("src", edge.get("source", ""))), str(edge.get("dst", edge.get("target", ""))), str(edge.get("type", edge.get("edge_type", ""))), _json_dumps(edge)),
        )


def import_artifact(conn: sqlite3.Connection, run_dir: Path, path: Path) -> int:
    kind = _kind_from_path(path)
    if path.suffix == ".jsonl":
        rows = _read_jsonl(path)
    elif path.suffix == ".json":
        obj = _read_json(path)
        rows = obj.get("rows", []) if isinstance(obj, dict) and isinstance(obj.get("rows"), list) else []
    else:
        rows = []
    artifact_id = _insert_artifact(conn, run_dir, path, kind, len(rows))
    round_id = _round_from_path(path)
    if path.suffix == ".json":
        obj = _read_json(path)
        conn.execute("INSERT OR REPLACE INTO json_reports VALUES (?,?,?,?)", (artifact_id, round_id, kind, _json_dumps(obj)))
        if "lineage" in kind or "lineage" in path.name:
            _insert_lineage(conn, artifact_id, obj)
        return artifact_id
    if kind == "audit":
        _insert_audit_rows(conn, artifact_id, round_id, rows)
        # Also expose response/carrier values when present.
        _insert_response_rows(conn, artifact_id, round_id, rows)
    elif kind.startswith("responses"):
        _insert_response_rows(conn, artifact_id, round_id, rows)
    elif kind in {"candidate_actions", "accepted_actions", "actions", "action_geometry"}:
        _insert_action_rows(conn, artifact_id, round_id, rows)
        if kind == "accepted_actions":
            _insert_acceptance_rows(conn, artifact_id, round_id, rows)
    elif kind == "acceptance_rows":
        _insert_acceptance_rows(conn, artifact_id, round_id, rows)
    elif kind in {"poms_status", "poms_promotion"}:
        _insert_poms_rows(conn, artifact_id, round_id, rows)
    else:
        # Generic rows may still contain useful action IDs.
        if rows and any(("action_id" in r or "tactic" in r) for r in rows if isinstance(r, dict)):
            _insert_action_rows(conn, artifact_id, round_id, rows)
    return artifact_id


def discover_artifacts(run_dir: str | Path) -> list[Path]:
    root = Path(run_dir)
    if not root.exists():
        return []
    patterns = ["*.jsonl", "*.json"]
    paths: list[Path] = []
    for pat in patterns:
        paths.extend(root.rglob(pat))
    # Avoid cache/build internals and huge generated Lean files.
    skip_parts = {".git", "__pycache__", ".pytest_cache", "build"}
    out = []
    for p in paths:
        if any(part in skip_parts for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def build_audit_db(run_dir: str | Path, db_path: str | Path | None = None, *, reset: bool = True) -> dict[str, Any]:
    root = Path(run_dir)
    if db_path is None:
        db = root / "audit.db"
    else:
        db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    if reset and db.exists():
        db.unlink()
    conn = sqlite3.connect(db)
    try:
        _ensure_schema(conn)
        paths = discover_artifacts(root)
        imported = []
        for p in paths:
            try:
                aid = import_artifact(conn, root, p)
                imported.append({"artifact_id": aid, "path": str(p), "kind": _kind_from_path(p)})
            except Exception as exc:
                imported.append({"path": str(p), "error": str(exc), "kind": _kind_from_path(p)})
        conn.commit()
        summary = summarize_db(conn)
        summary.update({"db_path": str(db), "run_dir": str(root), "n_import_attempts": len(paths), "n_imported_records": len([x for x in imported if "artifact_id" in x]), "schema_version": SCHEMA_VERSION})
        (db.parent / "audit_db_summary.json").write_text(_json_dumps(summary), encoding="utf-8")
        return summary
    finally:
        conn.close()


def summarize_db(conn: sqlite3.Connection) -> dict[str, Any]:
    cur = conn.cursor()
    tables = [
        "artifacts", "audit_rows", "response_rows", "response_values", "carrier_values", "action_rows", "acceptance_rows", "poms_rows", "lineage_nodes", "lineage_edges", "json_reports"
    ]
    counts: dict[str, int] = {}
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = int(cur.fetchone()[0])
        except Exception:
            counts[t] = 0
    by_kind = {}
    try:
        for kind, n in cur.execute("SELECT kind, COUNT(*) FROM artifacts GROUP BY kind ORDER BY kind"):
            by_kind[str(kind)] = int(n)
    except Exception:
        pass
    by_round = {}
    try:
        for rnd, n in cur.execute("SELECT COALESCE(round, -1), COUNT(*) FROM artifacts GROUP BY round ORDER BY round"):
            by_round[str(rnd)] = int(n)
    except Exception:
        pass
    return {"tables": counts, "artifacts_by_kind": by_kind, "artifacts_by_round": by_round}


def query_audit_db(db_path: str | Path, sql: str, *, max_rows: int = 1000) -> list[dict[str, Any]]:
    sql_stripped = sql.strip().lower()
    if not (sql_stripped.startswith("select") or sql_stripped.startswith("with") or sql_stripped.startswith("pragma")):
        raise ValueError("audit-db-query only allows SELECT/WITH/PRAGMA statements")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        rows = []
        for i, row in enumerate(cur):
            if i >= max_rows:
                break
            rows.append({k: row[k] for k in row.keys()})
        return rows
    finally:
        conn.close()


def write_query_outputs(rows: list[dict[str, Any]], *, out_json: str | Path | None = None, out_csv: str | Path | None = None) -> None:
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(_json_dumps({"rows": rows, "n_rows": len(rows)}), encoding="utf-8")
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            if not rows:
                f.write("")
                return
            fieldnames = sorted({k for r in rows for k in r.keys()})
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)


__all__ = [
    "SCHEMA_VERSION",
    "build_audit_db",
    "query_audit_db",
    "write_query_outputs",
    "discover_artifacts",
]
