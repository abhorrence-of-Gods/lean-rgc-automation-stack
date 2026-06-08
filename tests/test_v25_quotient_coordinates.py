from pathlib import Path
from lean_rgc.schemas import write_jsonl
from lean_rgc.quotient_coordinates import quotient_coordinates_from_files, compute_state_coker_normals, generate_quotient_coordinates
from lean_rgc.cli import build_parser


def _rows():
    return [
        {"state_id":"s1","action_id":"a_good","tactic":"simp","response_keys":["goal.eq","carrier.simp"],"response_flat":[0.2,0.0],"defect_before":{"flat":[1.0,0.2],"flat_keys":["goal.eq","carrier.simp"]}},
        {"state_id":"s1","action_id":"a_bad","tactic":"skip","response_keys":["goal.eq","carrier.simp"],"response_flat":[0.0,0.0],"defect_before":{"flat":[1.0,0.2],"flat_keys":["goal.eq","carrier.simp"]}},
        {"state_id":"s2","action_id":"a_good","tactic":"simp","response_keys":["goal.eq","carrier.simp"],"response_flat":[0.1,0.0],"defect_before":{"flat":[0.8,0.1],"flat_keys":["goal.eq","carrier.simp"]}},
        {"state_id":"s2","action_id":"a_car","tactic":"simp_all","response_keys":["goal.eq","carrier.simp"],"response_flat":[0.0,0.1],"defect_before":{"flat":[0.8,0.1],"flat_keys":["goal.eq","carrier.simp"]}},
    ]


def test_quotient_coordinates_from_response_coker(tmp_path: Path):
    path=tmp_path/'responses.jsonl'
    write_jsonl(path,_rows())
    normals, summary = compute_state_coker_normals(path)
    assert summary['n_state_normals'] >= 1
    coords, csum = generate_quotient_coordinates(normals, cosine_threshold=0.5, min_states=1)
    assert csum['n_quotient_coordinates'] >= 1
    assert coords[0].coordinate_map['formula'] == 'q_phi(d)=dot(phi,d)'
    out=tmp_path/'qcoords'
    report=quotient_coordinates_from_files(path,out_dir=out,cosine_threshold=0.5,margin_threshold=-999)
    assert (out/'quotient_coordinates.jsonl').exists()
    assert (out/'quotient_coordinate_action_scores.jsonl').exists()
    assert (out/'quotient_coordinate_selected_actions.jsonl').exists()
    assert report['coordinate_summary']['n_quotient_coordinates'] >= 1


def test_quotient_coordinates_cli(tmp_path: Path, capsys):
    path=tmp_path/'responses.jsonl'
    write_jsonl(path,_rows())
    out=tmp_path/'qc'
    parser=build_parser()
    args=parser.parse_args(['quotient-coordinates','--responses',str(path),'--out',str(out),'--cosine-threshold','0.5','--margin-threshold','-999'])
    rc=args.func(args)
    assert rc == 0
    assert (out/'quotient_coordinate_report.json').exists()
