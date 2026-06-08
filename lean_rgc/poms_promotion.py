from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import csv
import json

from .schemas import read_jsonl, write_jsonl


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _action(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get('action'), dict):
        return dict(row['action'])
    if isinstance(row.get('patch'), dict):
        return dict(row['patch'])
    meta = row.get('metadata') if isinstance(row.get('metadata'), dict) else {}
    if isinstance(meta.get('action'), dict):
        return dict(meta['action'])
    return row


def _action_id(row: dict[str, Any]) -> str:
    a = _action(row)
    return str(row.get('action_id') or a.get('action_id') or a.get('id') or '')


def _tactic(row: dict[str, Any]) -> str:
    a = _action(row)
    return str(row.get('tactic') or a.get('tactic') or a.get('full_tactic') or '')


def _carrier_atom(row: dict[str, Any]) -> str:
    return str(row.get('carrier_atom') or (row.get('patch') or {}).get('carrier_atom') or '')


def _parent_residual_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    a = _action(row)
    meta = a.get('metadata') if isinstance(a.get('metadata'), dict) else {}
    qgen = meta.get('qgen') if isinstance(meta.get('qgen'), dict) else {}
    for k in qgen.get('parent_residual_keys') or row.get('parent_residual_keys') or []:
        if k is not None:
            keys.append(str(k))
    # Some qgen rows store top contributions in metadata.
    for c in qgen.get('top_coordinate_contributions') or row.get('top_coordinate_contributions') or []:
        if isinstance(c, dict):
            k = c.get('key') or c.get('residual_key') or c.get('coordinate')
            if k is not None:
                keys.append(str(k))
    return sorted(set(keys))


def _load_evidence(paths: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p0 in paths or []:
        p = Path(p0)
        if not p.exists():
            continue
        if p.suffix.lower() == '.jsonl':
            out.extend(read_jsonl(p))
        else:
            data = _read_json(p)
            if isinstance(data.get('rows'), list):
                out.extend([r for r in data['rows'] if isinstance(r, dict)])
            elif isinstance(data.get('evidence'), list):
                out.extend([r for r in data['evidence'] if isinstance(r, dict)])
            elif data:
                out.append(data)
    return out


def _truth(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.lower() in {'1', 'true', 'yes', 'y', 'passed', 'pass'}
    return False


def _evidence_matches(row: dict[str, Any], ev: dict[str, Any]) -> bool:
    aid = _action_id(row)
    atom = _carrier_atom(row)
    src = str(row.get('source') or '')
    kind = str(row.get('kind') or '')
    tactic = _tactic(row)
    rkeys = set(_parent_residual_keys(row))
    checks = [
        ('action_id', aid), ('match_action_id', aid), ('carrier_atom', atom),
        ('source', src), ('kind', kind), ('tactic', tactic),
    ]
    for k, val in checks:
        if val and str(ev.get(k) or '') == val:
            return True
    ev_rk = ev.get('residual_key') or ev.get('parent_residual_key') or ev.get('parent_id') or ev.get('least_repair_key') or ev.get('defect_atom') or ev.get('residual')
    if ev_rk is not None and str(ev_rk) in rkeys:
        return True
    ev_rks = ev.get('parent_residual_keys') or ev.get('residual_keys') or []
    if isinstance(ev_rks, list) and rkeys.intersection({str(x) for x in ev_rks}):
        return True
    return False


def _merge_evidence(row: dict[str, Any], evs: list[dict[str, Any]], *, global_parent_nonpaid: bool, global_dual_certificate: bool, global_least_repair: bool) -> dict[str, Any]:
    m = {
        'parent_nonpaid': bool(row.get('parent_nonpaid')) or global_parent_nonpaid,
        'dual_certificate': bool(row.get('dual_certificate')) or global_dual_certificate,
        'least_repair': bool(row.get('least_repair')) or global_least_repair,
        'parent_paid': bool(row.get('parent_paid')),
        'modality': row.get('modality'),
        'parent_obstruction': row.get('parent_obstruction'),
        'evidence_ids': [],
    }
    for ev in evs:
        if not _evidence_matches(row, ev):
            continue
        status = str(ev.get('parent_status') or ev.get('status') or '').strip().lower().replace('-', '_')
        m['parent_nonpaid'] = m['parent_nonpaid'] or _truth(ev.get('parent_nonpaid')) or status in {'nonpaid', 'non_paid', 'not_paid', 'forced', 'parent_nonpaid'}
        m['parent_paid'] = bool(m.get('parent_paid')) or _truth(ev.get('parent_paid')) or status in {'paid', 'parent_paid'}
        m['dual_certificate'] = m['dual_certificate'] or _truth(ev.get('dual_certificate'))
        m['least_repair'] = m['least_repair'] or _truth(ev.get('least_repair'))
        if ev.get('modality') and not m.get('modality'):
            m['modality'] = ev.get('modality')
        if ev.get('parent_obstruction') and not m.get('parent_obstruction'):
            m['parent_obstruction'] = ev.get('parent_obstruction')
        m['evidence_ids'].append(str(ev.get('id') or ev.get('evidence_id') or ev.get('name') or len(m['evidence_ids'])))
    return m


def _promote_status(row: dict[str, Any], ev: dict[str, Any], *, declare_canonical: bool) -> tuple[str, str, str]:
    poms = str(row.get('poms_status') or '')
    parent = bool(ev.get('parent_nonpaid'))
    dual = bool(ev.get('dual_certificate'))
    least = bool(ev.get('least_repair'))
    if bool(ev.get('parent_paid')):
        return 'witness_only_parent_paid', 'parent_obstruction_paid_downstream_stays_witness', 'not_canonical_parent_paid'
    if parent and dual and least:
        if declare_canonical:
            return 'canonical_observable', 'canonical_declared_by_explicit_poms_evidence', 'canonical_declared_requires_doctrine_review'
        return 'canonical_candidate', 'parent_nonpaid_dual_certificate_least_repair', 'canonical_candidate_not_declared'
    if parent and dual:
        return 'forced_candidate', 'parent_nonpaid_and_dual_certificate_but_not_least_repair', 'not_canonical_least_repair_missing'
    if parent:
        return 'open_parent_obstruction', 'parent_nonpaid_but_dual_certificate_missing', 'not_canonical_dual_certificate_missing'
    if poms.startswith('paid') or poms == 'paid_carrier_patch_witness':
        return 'paid_witness', 'paid_or_realized_witness_parent_not_nonpaid', 'not_canonical_parent_paid_or_unknown'
    if 'accepted' in poms or 'carrier_patch_witness' in poms:
        return 'accepted_witness', 'accepted_but_parent_nonpaid_not_established', 'not_canonical_parent_nonpaid_missing'
    return 'witness_candidate', 'candidate_or_unaccepted_chart', 'not_canonical_witness_only'


def collect_poms_promotion(
    run_dir: str | Path,
    *,
    poms_rows: str | Path | None = None,
    evidence: list[str | Path] | None = None,
    out_json: str | Path | None = None,
    out_jsonl: str | Path | None = None,
    out_csv: str | Path | None = None,
    out_promoted_actions: str | Path | None = None,
    global_parent_nonpaid: bool = False,
    global_dual_certificate: bool = False,
    global_least_repair: bool = False,
    declare_canonical: bool = False,
) -> dict[str, Any]:
    root = Path(run_dir)
    rows_path = Path(poms_rows) if poms_rows else root / 'poms_status_rows.jsonl'
    status_rows = read_jsonl(rows_path) if rows_path.exists() else []
    evs = _load_evidence(evidence)
    out_rows: list[dict[str, Any]] = []
    promoted_actions: list[dict[str, Any]] = []
    for r in status_rows:
        ev = _merge_evidence(r, evs, global_parent_nonpaid=global_parent_nonpaid, global_dual_certificate=global_dual_certificate, global_least_repair=global_least_repair)
        promoted, reason, canonical_status = _promote_status(r, ev, declare_canonical=declare_canonical)
        nr = dict(r)
        nr.update(ev)
        nr['poms_promoted_status'] = promoted
        nr['promotion_status'] = promoted
        nr['poms_promotion_reason'] = reason
        nr['promotion_reason'] = reason
        nr['canonical_status'] = canonical_status
        nr['promotion_calculus'] = {
            'requires_parent_nonpaid': True,
            'requires_dual_certificate': True,
            'requires_least_repair': True,
            'explicit_canonical_declaration': bool(declare_canonical),
        }
        out_rows.append(nr)
        if nr.get('kind') == 'context_action' and promoted in {'forced_candidate', 'canonical_candidate', 'canonical_observable'}:
            a = _action(nr)
            if a.get('tactic'):
                meta = a.setdefault('metadata', {})
                meta['poms_promoted_status'] = promoted
                meta['poms_promotion_reason'] = reason
                promoted_actions.append(a)
    by_status: dict[str, int] = {}
    for r in out_rows:
        s = str(r.get('poms_promoted_status'))
        by_status[s] = by_status.get(s, 0) + 1
    summary = {
        'run_dir': str(root),
        'n_records': len(out_rows),
        'n_evidence': len(evs),
        'by_promoted_status': by_status,
        'n_promoted_actions': len(promoted_actions),
        'canonical_status': 'promotion_calculus_chart_only_unless_explicit_evidence_declares_canonical',
        'notes': 'Canonical promotion requires parent_nonpaid + dual_certificate + least_repair. Without explicit evidence, rows remain witnesses or open/forced candidates.',
    }
    rep = {'summary': summary, 'rows': out_rows}
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding='utf-8')
    if out_jsonl:
        write_jsonl(out_jsonl, out_rows)
    if out_promoted_actions:
        write_jsonl(out_promoted_actions, promoted_actions)
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        fields = ['kind','round','source','action_id','tactic','carrier_atom','poms_status','poms_promoted_status','promotion_status','poms_promotion_reason','parent_nonpaid','dual_certificate','least_repair','canonical_status']
        with Path(out_csv).open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            w.writeheader()
            for r in out_rows:
                w.writerow(r)
    return rep


def promote_poms_status(
    run_dir: str | Path,
    *,
    status_rows: str | Path | None = None,
    parent_certificates: Iterable[str | Path] | None = None,
    out_json: str | Path | None = None,
    out_jsonl: str | Path | None = None,
    out_csv: str | Path | None = None,
    out_promoted_actions: str | Path | None = None,
    allow_canonical_promotion: bool = False,
    min_realized_goal_response: float = 0.0,
    require_realized_success: bool = False,
) -> dict[str, Any]:
    # Compatibility wrapper for the v19 CLI/iterate call sites.  The realized
    # filters are applied upstream by poms_status; promotion itself uses only
    # explicit parent evidence.
    return collect_poms_promotion(
        run_dir,
        poms_rows=status_rows,
        evidence=list(parent_certificates or []),
        out_json=out_json,
        out_jsonl=out_jsonl,
        out_csv=out_csv,
        out_promoted_actions=out_promoted_actions,
        declare_canonical=allow_canonical_promotion,
    )


__all__ = ['collect_poms_promotion', 'promote_poms_status']
