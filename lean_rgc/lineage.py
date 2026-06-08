from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, stable_hash


@dataclass
class LineageNode:
    node_id: str
    kind: str
    label: str
    status: str = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LineageEdge:
    src: str
    dst: str
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _action_id(row: dict[str, Any]) -> str:
    if row.get("action_id"):
        return str(row.get("action_id"))
    a = row.get("action") if isinstance(row.get("action"), dict) else {}
    if a.get("action_id"):
        return str(a.get("action_id"))
    if a.get("tactic"):
        return stable_hash(a, 12)
    return stable_hash(row, 12)


def _action_metadata(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action") if isinstance(row.get("action"), dict) else row
    meta = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
    return dict(meta)


def build_qgen_lineage(qgen_dir: str | Path, *, out: str | Path | None = None) -> dict[str, Any]:
    """Build a lightweight provenance graph for qgen artifacts.

    The graph is intentionally a chart/witness graph, not a canonical proof object.
    It records how finite coker residual coordinates generated candidate atoms,
    context actions, carrier-incidence patches, and failure-signature charts.
    """
    root = Path(qgen_dir)
    report = _load_json(root / "qgen_report.json")
    atoms = read_jsonl(root / "qgen_defect_atoms.jsonl") if (root / "qgen_defect_atoms.jsonl").exists() else []
    contexts = read_jsonl(root / "qgen_context_candidates.jsonl") if (root / "qgen_context_candidates.jsonl").exists() else []
    accepted = read_jsonl(root / "qgen_accepted_actions.jsonl") if (root / "qgen_accepted_actions.jsonl").exists() else []
    carriers = read_jsonl(root / "qgen_carrier_incidence.jsonl") if (root / "qgen_carrier_incidence.jsonl").exists() else []
    failures = read_jsonl(root / "qgen_failure_signatures.jsonl") if (root / "qgen_failure_signatures.jsonl").exists() else []

    nodes: dict[str, LineageNode] = {}
    edges: list[LineageEdge] = []

    projection = report.get("projection") if isinstance(report, dict) else {}
    proj_id = "projection:" + stable_hash(projection or {}, 12)
    nodes[proj_id] = LineageNode(
        node_id=proj_id,
        kind="coker_projection",
        label="finite_response_coker_projection",
        status="chart",
        metadata={
            "residual_norm": projection.get("residual_norm"),
            "relative_residual": projection.get("relative_residual"),
            "support_value": projection.get("support_value"),
            "canonical_status": "finite_chart_projection_not_canonical",
        },
    )

    for atom in atoms:
        aid = str(atom.get("atom_id") or "atom:" + stable_hash(atom, 10))
        nid = "defect:" + aid
        nodes[nid] = LineageNode(nid, "defect_atom_candidate", aid, atom.get("status", "candidate"), {"atom": atom})
        edges.append(LineageEdge(proj_id, nid, "residual_generates_defect_atom", {"detector": atom.get("detector")}))

    accepted_ids = {_action_id(a) for a in accepted}
    for act in contexts:
        aid = _action_id(act)
        nid = "context:" + aid
        meta = _action_metadata(act)
        qmeta = meta.get("qgen") if isinstance(meta.get("qgen"), dict) else {}
        status = "accepted" if aid in accepted_ids else "candidate"
        nodes[nid] = LineageNode(nid, "context_candidate", str(act.get("tactic") or aid), status, {"action": act, "qgen": qmeta})
        edges.append(LineageEdge(proj_id, nid, "coker_normal_generates_context", {"qgen": qmeta}))
        for key in qmeta.get("parent_residual_keys", []) or []:
            rid = "residual_key:" + str(key)
            nodes.setdefault(rid, LineageNode(rid, "residual_coordinate", str(key), "chart", {}))
            edges.append(LineageEdge(rid, nid, "residual_coordinate_supports_context", {}))

    for ci in carriers:
        cid = "carrier_patch:" + stable_hash(ci, 12)
        label = f"{ci.get('action_id','?')}->{ci.get('carrier_atom','?')}"
        nodes[cid] = LineageNode(cid, "carrier_incidence_patch", label, "candidate", {"patch": ci})
        edges.append(LineageEdge(proj_id, cid, "carrier_delta_mines_incidence", {}))
        aid = str(ci.get("action_id") or "")
        if aid:
            cn = "context:" + aid
            if cn in nodes:
                edges.append(LineageEdge(cn, cid, "context_has_carrier_patch", {}))

    for fs in failures:
        fid = "failure_chart:" + stable_hash(fs, 12)
        label = str(fs.get("signature") or fs.get("kind") or fs.get("failure_kind") or fid)
        nodes[fid] = LineageNode(fid, "failure_signature_chart", label, "chart", {"failure_signature": fs})
        edges.append(LineageEdge(proj_id, fid, "audit_failure_mines_signature_chart", {}))

    graph = {
        "version": "lean-rgc-qgen-lineage-v0.1",
        "source": str(root),
        "canonical_status": "lineage_chart_only_not_canonical",
        "nodes": [n.to_dict() for n in nodes.values()],
        "edges": [e.to_dict() for e in edges],
        "summary": {
            "n_nodes": len(nodes),
            "n_edges": len(edges),
            "n_defect_atoms": len(atoms),
            "n_context_candidates": len(contexts),
            "n_accepted_contexts": len(accepted_ids),
            "n_carrier_patches": len(carriers),
            "n_failure_charts": len(failures),
        },
    }
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    return graph



def _as_paths(paths: str | Path | list[str | Path] | None) -> list[Path]:
    if paths is None:
        return []
    if isinstance(paths, (str, Path)):
        return [Path(paths)]
    return [Path(p) for p in paths]


def build_qgen_acceptance_lineage(
    qgen_dir: str | Path,
    *,
    accepted_actions: str | Path | list[str | Path] | None = None,
    acceptance_rows: str | Path | list[str | Path] | None = None,
    audit_responses: str | Path | list[str | Path] | None = None,
    registry_candidates: str | Path | list[str | Path] | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """Augment qgen lineage with audit and acceptance provenance.

    This graph is deliberately a finite provenance chart: accepted actions are still
    witnesses unless later promoted by parent-non-paid + least-repair logic.
    """
    graph = build_qgen_lineage(qgen_dir)
    nodes: dict[str, LineageNode] = {n["node_id"]: LineageNode(**n) for n in graph.get("nodes", [])}
    edges: list[LineageEdge] = [LineageEdge(**e) for e in graph.get("edges", [])]

    def ensure_context(action: dict[str, Any], *, default_status: str = "candidate") -> str:
        aid = _action_id(action)
        nid = "context:" + aid
        if nid not in nodes:
            meta = _action_metadata(action)
            nodes[nid] = LineageNode(nid, "context_candidate", str(action.get("tactic") or aid), default_status, {"action": action, "qgen": meta.get("qgen", {}) if isinstance(meta.get("qgen"), dict) else {}})
        return nid

    # Registry-derived candidates are qgen defect-registry readouts, not raw qgen contexts.
    for path in _as_paths(registry_candidates):
        if not path.exists():
            continue
        for action in read_jsonl(path):
            cn = ensure_context(action, default_status="registry_candidate")
            rn = "registry_candidate:" + _action_id(action)
            nodes[rn] = LineageNode(rn, "qgen_registry_candidate", str(action.get("tactic") or _action_id(action)), "candidate", {"action": action})
            edges.append(LineageEdge(cn, rn, "context_readout_as_registry_candidate", {}))

    # Audit responses attach empirical statuses to candidate contexts.
    for path in _as_paths(audit_responses):
        if not path.exists():
            continue
        for row in read_jsonl(path):
            action = row.get("action") if isinstance(row.get("action"), dict) else row
            cn = ensure_context(action, default_status="audited")
            aid = _action_id(action)
            an = "audit:" + stable_hash({"path": str(path), "action": aid, "state": row.get("state_id") or row.get("task_id"), "status": row.get("audit_status") or row.get("status")}, 14)
            nodes[an] = LineageNode(an, "micro_audit_response", str(row.get("audit_status") or row.get("status") or aid), str(row.get("audit_status") or row.get("status") or "audited"), {"audit": {k: row.get(k) for k in ["task_id", "state_id", "action_id", "audit_status", "status", "response", "carrier_delta"]}})
            edges.append(LineageEdge(cn, an, "context_micro_audited", {"source": str(path)}))

    accepted_ids: set[str] = set()
    for path in _as_paths(accepted_actions):
        if not path.exists():
            continue
        for action in read_jsonl(path):
            cn = ensure_context(action, default_status="accepted")
            nodes[cn].status = "accepted"
            accepted_ids.add(_action_id(action))
            accn = "accepted:" + _action_id(action)
            meta = _action_metadata(action)
            nodes[accn] = LineageNode(accn, "accepted_context", str(action.get("tactic") or _action_id(action)), "accepted", {"action": action, "metadata": meta, "canonical_status": "accepted_witness_not_canonical"})
            edges.append(LineageEdge(cn, accn, "context_accepted_by_coker", {"source": str(path)}))

    for path in _as_paths(acceptance_rows):
        if not path.exists():
            continue
        for row in read_jsonl(path):
            action = row.get("action") if isinstance(row.get("action"), dict) else row
            cn = ensure_context(action, default_status="acceptance_scored")
            rid = "acceptance_row:" + stable_hash({"path": str(path), "row": row}, 14)
            status = "accepted" if row.get("accepted") else "rejected"
            nodes[rid] = LineageNode(rid, "coker_acceptance_record", str(row.get("robust_margin") or row.get("margin") or row.get("score") or status), status, {"row": row})
            edges.append(LineageEdge(cn, rid, "context_has_coker_acceptance_record", {"source": str(path)}))
            if row.get("accepted"):
                nodes[cn].status = "accepted"
                accepted_ids.add(_action_id(action))

    graph2 = {
        "version": "lean-rgc-qgen-acceptance-lineage-v0.1",
        "source": str(qgen_dir),
        "canonical_status": "acceptance_lineage_chart_only_not_canonical",
        "nodes": [n.to_dict() for n in nodes.values()],
        "edges": [e.to_dict() for e in edges],
        "summary": {
            "n_nodes": len(nodes),
            "n_edges": len(edges),
            "n_accepted_contexts": len(accepted_ids),
            "n_audit_nodes": sum(1 for n in nodes.values() if n.kind == "micro_audit_response"),
            "n_acceptance_records": sum(1 for n in nodes.values() if n.kind == "coker_acceptance_record"),
            "n_registry_candidates": sum(1 for n in nodes.values() if n.kind == "qgen_registry_candidate"),
        },
    }
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(graph2, indent=2, ensure_ascii=False), encoding="utf-8")
    return graph2


__all__ = ["LineageNode", "LineageEdge", "build_qgen_lineage", "build_qgen_acceptance_lineage"]
