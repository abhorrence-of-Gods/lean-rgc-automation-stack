# 敵対的レビュー課題ブリーフ: 上層設計 (U'系列 / ODLRQ) の妥当性

## 背景（確定事実 — 争わない前提）

リポジトリ: `<USER_HOME>\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics`
（Lean 4 定理証明の自動化スタック。Python パッケージ `lean_rgc` + Lean RPC worker）

直前に S'1m という中層実験が「freeze 前に終了」した。理由:
1. τ増幅 cone 介入は原理的に効かない（`max_mass=None` の cone は生成元スケール不変 → 順位を変えずスケールだけ変える。ρ_φ 0.070→最大0.083 で閾値 0.10 に届かない）。
2. 総 leakage の 57% は carrier 次元にあり、gate 次元内シェア 96.9% という数字は錯覚だった。
3. frame 不整合: α は 32次元 co-moving kernel 系、増幅対象は 34次元 raw file-lane 系 — 物理的に別の量を同一視していた。
4. α の根拠だったメモリ勝利 36.1% は 6次元中5次元が prev-fiber onehot（tactic 粘着性との交絡、未分解）。
5. 検証プロセス自体が反実仮想ゲート結果を観測してしまい、既存 103 タスクの score 側は汚染済み・退役。将来の主張には未曝露データ + 新規 preregistration が必要と登録済み。

## レビュー対象の提案（ユーザーが採用を検討している上層設計）

### A. パイプライン順序（添付 tex 文書由来）
exact generator → positive worst-case envelope → maximum-entropy lifting（envelope の内側のみ）→ global similarity（node/edge measure）→ finite-depth certificate。
「常に制御」= fail-closed control: certificate が成立しない状態では action を拒否し rollback/budgeted fallback/abstention。
数学的基盤は `<USER_HOME>\Downloads\fiber_closure_fixed_point_integrated_jp.tex`（Navier-Stokes 用、全20章。第9-11章 envelope/MaxEnt/KL-robust、第12-14章 similarity、第15-17章 finite-depth、第18-20章統合 certificate）。

### B. Frame contract（U'0）
- 各観測ベクトルに FrameId = (environment_hash, source_lane, granularity, coordinate_schema_hash, normalization_id, exposure_class) を型として付与。
- 32次元 kernel chart と 34次元 raw chart は共通 microstate Ω からの別々の observation map として扱い、結ぶ場合は明示的 transport J を登録し ε_frame と ε_nat = ||J G_kernel − G_raw J|| を certificate に入れる。
- `lean_rgc/qgen.py::_align_rows` の「min(rv.size, dv.size, len(keys)) で先頭共通次元へ切り詰め」を廃止し、FrameId 完全一致 / 登録済み FrameMorphism / それ以外 hard error の三択にする。

### C. Envelope を safety governor に（U'2）
- signed operator A_n を positive envelope M_n(Q',Q) = sup_{ω∈fiber} Σ |A| ϖ比 で支配。
- M_n^T w ≤ θ w (θ<1) の Lyapunov certificate。
- Lean 側の envelope 内容: closed goal 吸収、open goal/mvar/carrier debt 増減、branching 数、heartbeat/wall-clock/memory budget、timeout 遷移、hidden-state return risk、proof-term support 増大、scheduler pruning。
- goal/carrier/resource/audit の typed block 全体で構成（M_gg, M_gc, M_cg, M_cc）。carrier block が contractive でなければ action を通さない。
- `action_geometry.py` の scalar score（response + carrier − λ_tail·risk）を lexicographic hard gate に置換: frame certificate → hard envelope → support/KL risk → finite-depth certificate を全部通った候補のみ utility 順位付け。

### D. MaxEnt は envelope の内側のみ（U'3）
- profile fiber 上で KL 最小化 + moment 制約。hard/robust/nominal の三層 certificate を混同しない。
- α（メモリ統計）は generator ray の倍率には二度と使わない。profile split statistic か ME sufficient statistic のみ。
- reference measure は一様 counting ではなく canonical transition orbit + automorphism multiplicity 補正。

### E. Global similarity（U'4）
- 単一 embedding でなく (M_1, ρ^(1), M_2, ρ^(2))（node/edge measure + total mass 保持）。
- d_pred（予測用）と d_+（safety upper bound 用）を分離。U_+(z) = inf_i {U_i + L_+ d_+(z, z_i)} < 1 のときのみ similarity extension 許可。

### F. ODLRQ 理論（Oracle-Driven Local Response Quotient — Lean 固有の新理論）
- Lean を exact transition oracle とみなし、Koopman U_a f = f∘τ_a、差分 Δ_a = U_a − I を定義。
- fiber closure: F_N = σ(E∘τ_w : |w|≤N)、F_* = ∨F_N が最小 action-invariant response algebra（定理1）。
- 差分積公式: Δ_a(f^m) = Σ_j C(m,j) f^{m-j}(Δ_a f)^j（「二項定理チック」な exact 展開）。可換なら multinomial、非可換（共有 mvar）なら ordered word 保持。
- Lean–Nerode 応答商（定理2）: x∼*y iff E(τ_w x)=E(τ_w y) ∀w。quotient 上に τ̄_a が well-defined。
- contextual response equivalence（定理3）: u≡v iff 全 closing context c・全 action word w・全観測 h で応答一致。最粗の十分局所表現。
- 局所性の定義: 「外部の影響が低複雑度な boundary statistic b_u^*(o) を通してのみ伝わる」。
- 三欠陥分解（定理4）: Err_T ≤ C^loc ε_loc + C^lump δ_lump + C^mem μ_N(T)。ε_loc = ||RK − K_R R||、δ_lump = ||K_R J − J K̄||、μ_N(T) = Σ_j ||B D^j C_0||。
- 「exact response quotient では return-memory は自動的に消える（QKP=0）」という主張。
- response Hankel 行列: 有限 index → exact 離散商、有限 rank → linear predictive state (PSR)。σ_min ≥ κ の conditioning（persistent excitation）。
- active queries 四種: congruence / identification / memory / safety。witness-complete な (ε,c)-separating test 言語上で反例不在 → δ_lump ≤ (ε+η)/c という「証明可能な」主張。
- 三軸 closure: R（依存グラフ半径）× N（action word 深さ）× G（action 粒度: aesop macro=0 … kernel mutation=3）。
- 有限 Lean–Galerkin program: cutoff Λ で有限化した X_Λ 上で全 germ 列挙 → 全 transition 評価 → exact partition refinement → quotient 安定性を Λ 増加で測る。
- 三層 quotient generator: exact（match-count signature 完全一致）/ robust（区間 [N_under, N_over] 保持）/ nominal（学習 or ME）。
- 学習器の役割限定: match multiplicity・kernel transition・FrameId transport を決めない。λ_θ(r,m|q_R(x))（selection law）と quotient 座標・metric の発見のみ。
- CEGAR: learner が merge/split 提案 → Lean exact probe が反例 → split → envelope 成立まで反復。
- rule algebra: ρ(r)|x⟩ = Σ_{m∈Match(r,x)} |τ_{r,m}(x)⟩。係数 = 正確な match/history 重複数。multiplicity:Nat / signed_amplitude:Rat / positive_upper:Rat≥0 / proposal_prob を分離保持。

### G. U'0–U'5 preregistration 順序
| 段階 | freeze | gate |
|---|---|---|
| U'0 Frame contract | FrameId, coordinate keys, morphism, exposure ledger | silent truncation 0, 未登録 morphism 0 |
| U'1 Exact generator | primitive action set, site API, canonicalizer, coefficient ring | replay 一致, litmus 全通過 |
| U'2 Envelope | profile map, M_n, weight, budget clock | hard/robust/statistical-only tier 確定 |
| U'3 MaxEnt | reference law, statistics, moments, KL radius | held-out moment/risk/support test |
| U'4 Similarity | nested H^(R), node/edge measure, d_pred/d_+ | finite-radius remainder, violation 0 |
| U'5 Sealed evaluation | 新規未曝露 tasks, one-shot runner, 停止規則 | certificate 通過 action のみ評価 |
現 103 タスクと現 φ/α は U'0–U'4 の開発には使えるが U'5 の証拠には使えない。validation runner と evaluation runner を分離。

### H. 提案されたコード変更
- `RGCKernelRPC.lean` の `stepTactic`（first open goal に適用）を `apply_tactic_at(state_id, target_mvar_id, tactic_ast, occurrence_spec, explicit_premises)` に拡張。
- macro tactic（simp/aesop/omega）は当面 kernel-audited opaque hyperedge、trace が得られたものから primitive expansion へ。
- `contextual_congruence.py`: cosine fingerprint clustering → response Hankel observation table + counterexample test 管理。
- `response_quotient.py`: representative action への射影をやめ、class ごとに member transitions / match-count table / nominal kernel / ambiguity set / envelope / support を保持。
- `gamma_transition_learner.py`: affine mean map → distributional local transducer K̂(z',ΔE,Δ∂|z,a)。
- `lean/goal_state_dynamics.py`: target site, read/write set, boundary ports, premise/simp/typeclass input, env/frame hash, replay certificate, local radius を追加。
- 新規モジュール: local_region.py / primitive_events.py / rule_algebra.py / behavioral_quotient.py / local_causal_learner.py / quotient_generator.py / locality_memory_certificate.py。
- 最初の実験 fragment: intro / constructor / exact / apply / occurrence 指定 rw / frozen simp only / explicit target mvar。

## 既に確認済みのコード事実（レビュー時に再検証してよい）
- `lean_rgc/qgen.py:209-234` `_align_rows`: `n = min(rv.size, dv.size, len(keys))` の切り詰めが実在。D は「mean positive defect」。
- `lean_rgc/native_lean/RGCKernelRPC.lean`: 1162行。`stepTactic` は :604。`apply_tactic` コマンドは :996-1015 で `state_id` or `task` のみ（target mvar 指定なし）。
- `lean_rgc/nonlinear_generator.py`: 52行の thin wrapper。
- `lean_rgc/response_quotient.py`: 276行。`lean_rgc/contextual_congruence.py`: 448行。`lean_rgc/gamma_transition_learner.py`: 478行。`lean_rgc/action_geometry.py`: 997行。`lean_rgc/lean/goal_state_dynamics.py`: 605行。

## あなた（レビュアー）への指示
自分の担当レンズで、この提案を**本気で潰しに行く**こと。礼儀的な懸念表明ではなく、「この設計はここで死ぬ」という具体的な攻撃を、コード・数学・統計・計算量の証拠つきで出す。ただし攻撃が事実誤認なら出さない — コードを実際に読み、主張を検証してから断定する。提案の中で**生き残る部分**があればそれも明示する（steelman）。tex 文書は `<USER_HOME>\Downloads\fiber_closure_fixed_point_integrated_jp.tex`（UTF-8, 1990行）を必要な範囲で読む。
