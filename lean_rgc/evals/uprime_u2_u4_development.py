"""Strict CPU-synthetic U-prime U2--U4 integration candidate.

This module is intentionally finite and fixture-specific.  It live-rebuilds
the accepted E1/E2/S0 hard authorities, parses the frozen Windows ME0 wire,
keeps nominal data outside the hard channel, and emits only the seven
registered development artifacts.  It is not a production Lean endpoint.
"""

from __future__ import annotations

import argparse
import base64
import copy
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import Any, Sequence
import zlib

from lean_rgc.odlrq import (
    CanonicalPayload,
    ExactRational,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    admit_synthetic_finite_snapshot,
    build_exact_quotient_coordinate_generator,
    build_fiber_envelope,
    build_synthetic_finite_snapshot,
    canonical_contract_bytes,
    certify_fiber_completeness,
    declare_synthetic_transfer_layer,
    make_exact_finite_fiber_law,
    make_positive_fiber_weights,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
    refine_exact_partition,
    verify_exact_partition,
)
from lean_rgc.odlrq import certificates as e2c
from lean_rgc.odlrq import maxent as me
from lean_rgc.odlrq import selection as e2s
from lean_rgc.odlrq import similarity as s0


__all__ = [
    "build_u24_i0_fixture",
    "build_u24_artifact_wires",
    "verify_u24_artifact_wires",
    "emit_u24_artifacts",
]


_ACCEPTED_E1_COMMIT = "6fb35aa229fc60e2220cbb68c1e7fff2ce64f199"
_ACCEPTED_E1_TREE = "b3fc7f21b6420e718eb954be0c1b5affca65d263"
_ACCEPTED_E2_COMMIT = "7a8b28872439dd61d40174c2500c5990790002be"
_ACCEPTED_E2_TREE = "d54ed9fab52da4929843fabdeb3c1e1920994f6a"
_ACCEPTED_ME0_COMMIT = "28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d"
_ACCEPTED_ME0_TREE = "a3b3513ca93430c9f15e5bd90888e81b0af1ff9c"
_ACCEPTED_S0_COMMIT = "2376aca8209c38a3a94dfa872334073d86dc4909"
_ACCEPTED_S0_TREE = "4b3a2c8b3f3364c411b5444885102035ff3a821f"

_S0_AUTHORITY_COMMIT_SHA = "48e8aa4b2a50d93367027d3c924944c160ef806a"
_S0_AUTHORITY_PARENT_SHA = _ACCEPTED_ME0_COMMIT
_S0_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/uprime_odlrq_post_me0_s0_i0_authority_2026-07-17.md"
)
_S0_AUTHORITY_DOCUMENT_BLOB_SHA = "f137a5c4f8411e2b68d6c88d6a6d09683a766aa2"
_S0_AUTHORITY_CI_RUN_ID = 29557149691
_S0_AUTHORITY_CI_JOB_ID = 87811636093

I0_ACTIVATION_COMMIT_SHA = "2e6d0b64a88877dd1f1bd87718186c3ac040c2a4"
I0_ACTIVATION_PARENT_SHA = _ACCEPTED_S0_COMMIT
I0_ACTIVATION_DOCUMENT_PATH = (
    "docs/experiments/uprime_odlrq_post_s0_i0_activation_2026-07-17.md"
)
I0_ACTIVATION_DOCUMENT_BLOB_SHA = "a2e7642e132226e50f7f238a7c6fa708f8492ec9"
I0_ACTIVATION_CI_RUN_ID = 29561412405
I0_ACTIVATION_CI_JOB_ID = 87824486788

_E1_ENVELOPE_SHA = "D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6"
_E2_M0_ENVELOPE_SHA = "9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C"
_E2_P1_SHA = "6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11"
_E2_P2_SHA = "BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D"
_E2_RETURN_SHA = "95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46"
_E2_TOKEN_SHA = "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660"
_ME0_RESULT_SHA = "DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3"
_S0_CERTIFICATE_SHA = "86C3AF246466BB62A2297EEF40E437CC9152110DC1EF69F64ACCA2A8D0FA3D35"
_S0_POSITIVE_SHA = "8670B7381468EC47EBF7DFCEEC6EF1B847A5B4DB40935B2A7521C22A645B96D7"
_S0_PREDICTIVE_SHA = "2AEF5156AB4A3C6D329C2346DFAD731D9B0E7BA33CEDC65487B187CF0E383F7E"
_FULL_RUNTIME_SHA = "F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A"
_S0_RUNTIME_SHA = "88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9"

_FRAME_ID = "u24.e2.declared_square.observation_frame.v1"
_REACHABLE_DOMAIN_ID = "u24.s0.declared_finite_similarity_domain.v1"
_RESPONSE_VOCABULARY_ID = "u24.e2.declared_square.response_vocabulary.v1"
_TRANSITION_SEMANTICS_ID = "u24.e2.declared_square.transition_semantics.v1"
_DOMAIN_SCOPE = "declared_finite_totalized_snapshot_only"
_NORM_ID = "weighted_l1_exact_rational_v1"

_MAX_ARTIFACT_BYTES = 1_048_576
_MAX_AGGREGATE_BYTES = 7 * 1_048_576
_MAX_JSON_DEPTH = 16
_MAX_JSON_ARRAY = 256
_MAX_JSON_KEYS = 64
_MAX_JSON_NODES = 8192
_MAX_STRING_BYTES = 4096
_MAX_ERROR_BYTES = 128 * 1024
_MAX_RECEIPT_BYTES = 4096

_ARTIFACT_NAMES = (
    "envelope_core.json",
    "maxent_fixture.json",
    "local_tower.json",
    "global_measure.json",
    "level_transport.json",
    "similarity_certificate.json",
    "integrated_certificate.json",
)

_ME0_RESULT_JSON = r'''{"certified_support_token_sha256":"D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660","dual_parameter":["0.14384103623693401"],"dual_residual_inf":"1.0601741706750545e-11","expected_row_load":"1.8000000000106016","fallback_candidate_id":null,"fallback_used":false,"fitted_expected_load":"1.8000000000106016","geometry":{"affine_rank":1,"declared_dimension":1,"membership_subset_indices":[0,1],"membership_weights":[{"denominator":"5","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"5","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"schema_version":"odlrq.me0.moment-geometry.v1","status":"INTERIOR_SOLVED","subset_work_bound":3,"supporting_face_indices":[],"tier":"NOMINAL_MODEL_SELECTION_ONLY"},"kl_divergence":"0.0097123133244110954","kl_radius":{"denominator":"20","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"kl_within_radius":true,"log_partition":"0.1053605156666611","me0_authority_ci_job_id":"87793466452","me0_authority_ci_run_id":"29551068987","me0_authority_commit_sha":"0ff63861a2957b53f4c0b5f2948d561d936337ca","me0_authority_document_blob_sha":"831c226a2b25ae367b288a8fb18d7cb7afb42124","me0_authority_document_path":"docs/experiments/uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md","me0_authority_parent_sha":"7a8b28872439dd61d40174c2500c5990790002be","moment_residual_inf":"1.0601741706750545e-11","operator_span":{"coefficients":["1.9999999999999996"],"column_ids":["g0"],"residual_l2":"9.9301366129890925e-16","schema_version":"odlrq.me0.operator-span-residual.v1","tier":"NOMINAL_MODEL_SELECTION_ONLY","tolerance":"1e-10","within_tolerance":true},"operator_span_residual":"9.9301366129890925e-16","operator_tier":"NOMINAL_MODEL_SELECTION_ONLY","orbit_expected_row_load":"1.6666666666666665","orbit_reference":{"normalization":{"denominator":"4","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"probabilities":[{"denominator":"3","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"3","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"schema_version":"odlrq.me0.orbit-reference-law.v1","support_candidate_ids":["c0","c2"],"tier":"NOMINAL_MODEL_SELECTION_ONLY","unnormalized_mass":[{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"4","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}]},"orbit_reference_probabilities":["0.66666666666666663","0.33333333333333331"],"pinsker_rhs":"1.9828944326835045","pinsker_upper":"1.9828944326835045","probabilities":["0.59999999999469911","0.40000000000530089"],"problem_sha256":"20A376AD298A285949284B19D8589AD190054D870B6A7341D598D59F7EBFAF8C","reference_expected_load":"1.6666666666666665","row_table_sha256":"75FFB3222E1CA31CF4F558F1955D18B74C62B6D622DE862820173FE329526A76","runtime_manifest_sha256":"F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A","schema_version":"odlrq.me0.maxent-result.v1","selected_candidate_id":"c0","simplex_error":"0","simplex_residual":"0","status":"INTERIOR_SOLVED","support_candidate_ids":["c0","c2"],"support_reference":{"accepted_e2_commit_sha":"7a8b28872439dd61d40174c2500c5990790002be","accepted_e2_tree_sha":"d54ed9fab52da4929843fabdeb3c1e1920994f6a","certified_support_token_sha256":"D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660","me0_authority_ci_job_id":"87793466452","me0_authority_ci_run_id":"29551068987","me0_authority_commit_sha":"0ff63861a2957b53f4c0b5f2948d561d936337ca","me0_authority_document_blob_sha":"831c226a2b25ae367b288a8fb18d7cb7afb42124","me0_authority_document_path":"docs/experiments/uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md","me0_authority_parent_sha":"7a8b28872439dd61d40174c2500c5990790002be","runtime_manifest_sha256":"F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A","schema_version":"odlrq.me0.declared-e2-support-reference.v1","support_candidate_ids":["c0","c2"],"tier":"NOMINAL_MODEL_SELECTION_ONLY"},"tier":"NOMINAL_MODEL_SELECTION_ONLY","verification_disposition":"CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"}'''

# Filled below with the byte-exact compressed activation certificate.  The
# decoded payload is compared byte-for-byte, not merely by digest.
_S0_CERTIFICATE_B85 = (
    "c-rk<Yg1b}w*4=BZZcbMslVwt!>uHw2;H}Orn+3lKJK_LV8%8{n5q8ncgZ$jo_PU*psH@i_@T$v(pqcl=*a)w7);)G)BYdb#?Sx7"
    "^Mj-PZjR^k>2ded^1W`@8%&N5=NmuE^H;{h*~ZWR+BoL2H>2L1dWVx?M;kw#y}}l+uwFO(qa(KV24B3y)?X66Ki*Ad^WL<ZA5RZA"
    "e!oynZ}zUwmEQPyBYUHTamtcOo)=;zdLAUVmZVEgN~^QXIdh+g2}OdHKq@j_SoR?&)Hs<A7v&xwj#0s^yYGI?2JgCqey`Rwo*beN"
    "li~jK-!EqLViD4AxOp1>%@5=GVK<w-c)uv|w0-B1UvKgq#^kS`HiqNb(PTEBFIyPj{L*{-+w0wb<lU{<+x_iLPQABVueM(Lovq#9"
    "dU1Ov_kPVgTV-nz(b4#DJnzuugZ}ss!R-yY>3lpI5Bl>3r24}@`-ARqe*TFX@c(WMyTi%B_^>~pOi`&sNr%S=h{W>m8iOmb+wb~^"
    "o6|oAn~NZBb|3qL`6j-Bcl-OBh}&O3J+X2ZNIzHvziR>doO1aSEBA67#8(65;w&v&ueWw{ZzsR<Tdz~zxn@f4ckjFXH3AtQuHG0N"
    "&nKf%Z?NAVA8h<Q>hI6Gb7owAYekDMD-*t~v3OYn^iot#TejkT*E^a{{_F;|LFatrv+<l#ikhrQJn0a5vfMKrMKL^O$F$Q%7{(0V"
    "6kJH}GgFdh&b$p9Yvs?U{X_J5I$!6M<>VN=>mMF=`>62E_S>!9tzYv-ol5=6kH<$x-Lz8A{UGwvK%Ca!+uiZ6-@e)2*}XIr_unAY"
    "@$cjQ{&;@UdpFsyBezuVgUR&h-FS9zJ~}c+7NUbhKrkGUW+|vxpa(%(9+PE-vm$IrA(7=$2JNKLIyh;K3>CcRMBm+Gmu}Y0Q*>;e"
    "p<}6-v&r#v08IAB)ARn4NFqkbGKpZdQwhCJ+&G4ZVuJFz*c^n_np~EW*$^y=l1=2HWGX0k-k<)_%`cT(Ah0E=s7<zB2}g=3aUpVH"
    "$y3N)s0wW%f)1Lv2|+qp5O{565>_sVqG9-}Fs!npqD^qd@EpAg$-69^%MqMYly!=OT)g(&#~3nfPS&KX71BAfQ9U&b!=z<nV{wiJ"
    "GA<M{g#)*axnwxkIWY(P7H4#_f(Oo3R;pOaOj0rGCJcY`-1uQJ`~V;(Ljb4*fhY{AlTPz!Eps7cr6c*`t;euR6C_2EFpkj~m6M6g"
    "a2E1Y1F<h57v-g5MyqUtu@D@Mq(n28a}=C-R0WeYOOpZKWRe8@igw;nDmQ}on<qyj;;$!S2Q5p%GbJMYUQv_*>BMBnR%S)gDl#f&"
    "uN9?iDTd^PQYKKfgQP!&Vg5{rxS5IXNW|GXScfH46|94n3Lc_(oj}nJ2=|<O&a#bCn`9xGC3v2l<OSp8)KdfTeGzeU6W<ZUKyN0S"
    "bY?*qD>9i>icGwOnto@=;h1f9G3#ieveKE9LNFXWrF~LgoYsjS6vW@o#C3UO+6~8p8y857HbO9-Qg&XW8#)xGk-7+D7@3-{B=X$W"
    "C0kU)t%#T=q*C&tgi<P>tkv*&OC&ovZN+P+(?(t3xdi>QPk$Qxi?82^(~f%6Zg#w1*M3Lcv^&H=o{ypT$;K!!M4|}Lhm*!>C34Iv"
    "InV+NDlruh`6%%eU}l_AWW_0!saE`Bu5X+T?&p~j3yZ-45h*1=lh7wEauN_Of)^9Qgn~IBd}6-9mar%d@(#-bcv_YlS2&!5;6WN$"
    "G7iI`HNI{YV((ZkMJItNVxmNdWs*K|=7CU_7<rFKN_&~lpA7_mgyo4ZgP=y*il!R`3BfB#N}(NmK$ae?7D2o$X+)C*$Fvi=XpSsE"
    "0;@nOOYX+p?pvY#U=U=F3xYqw;=-3fFbWULgG`L-)y-UT$dN!*pd#2GfeuEYq9|M{$Uxxam9{Pyq;rgj_)QS}W@tZK7W@I$1|A0s"
    "J{=)`WGwh2WcH7P1)C6mB?Nzjy!>%M@Y`AN*3DSUjS-t?!Cv+7cr+S+>>c#~oS^IT&)JqEp4fJjyDFDmDwn=;n+ve`u0I|2`p5Hk"
    "lWCp9XLEJ2nQSoVj^^F4*RkGUa&R!7SBO;g9qkF#?{n@(15F+0oCbS)+74J}MxzlQbXty>t17!*#)2poizaoAraOG!?N5%@SRnym"
    "flSPWym20!009ZkB_TK-9Huj8$}=lUOiIhZl{A>b+2oKY>Pywlr(L&d@SYeA%!so+Eje|D*>2A%x!2Kv?Wz7~H0WzJgf+NO0>9X4"
    ")3<xvT5zp!!=YwFNzBLrS40DaY|^+orS`f@WvsPgsAM;EqyC=a!@hLfSt;<>u-g-e9CN%1<w*By31=fRKR()Di;<NSq|Vw%k&6;6"
    "MG-+^8s<)fEE4xdFvQW@;^6cwCnJy=Gf)B2j<R6<Nu77S*#N<>t?CB*{kj)vwO?sInPZs#gBNCp{iE5t$-Fl?+&{q=Yef2o!|||>"
    "kDYChJm?>eN8N0G-bTT}tVnf2(jt;{o&~0ZG88N;DkUW6;AmT0UaT-eYI4yEP`n~|Gry{8xx`l60l}$@Zu80ib!%&Ti5N2^xygo^"
    "q-0eQj0hq5iVhT2R8T@?p$x2G&Lsu7Kw|_{69Lq;tmc3~e$%>T@+u%*@Y?Z={7ps`6=Wo34df}rRS<cX2m<1*wJ9qlAY~X2W}VJ1"
    "FlFMhhNC)r1}B5{Vbsy0**Qb#Y>1SMO~j=SsE8-XzpNdCoo96kRddG-j4Zbj5i7YYR=I1*{A$S|XH&ynKWTk&Tt`SmQHnTbPvC~E"
    "2fasbsVMkoE48&Q@Tka>R%u!Ca!+mVpo7ew^!6slhr_k7sK`SG<73Fksw_38Bnb<RFu}l?WJ(cj*H(on9KsP;h8;vI47reXo_6oY"
    "!=)v-jKbN;;rv}U9}g<WO{NFE@epr+=*EA%t21h!^%hLlJ7u!oQaosl#0KNupOd}i7p<|3X#s?ZYd$tTK3sl`!&exF+}&L*ZJh+9"
    "?QFj<_jq5?&<UXpaWfPH$EA~UfMlv0Sz1it3xy0P1MoFKwzrR#Ez24)VftzyM^-Y{aq#C*4=f(~dPq)N(TDPaWp6C&s6T&KLpK@B"
    "{?>hjCmYw7XMa0Bs?T~0-tQgNEz;GEp^Wi*F`T&GB(urPi-Y0iI#yF+*-#EqcY7l~BGA3r8z|N1vU44o(SSrBt=4+a*;OI6^5u@g"
    "Gm1DzPJvAziD^>mluU`>EdW?R&kF4|<ybUeFRjf9lLICs!2nxr4Cf`sjoWO+DTFqwrfr_}W%EqaUM%g`e(z}ic(!Dd<u?4bCBJRS"
    "KhJ@nPcQvW-G_g+FaPD6m%qGS&x5{RLlLsx5`otkT=qbQ@xIFCU%lV@^8}%})#g^4TWxN&xz*-YpNU(o=Ii?#hOZa)&z}`nhoZ{*"
    "!Z0mO>c2J)D-Gh|_n%Imv*mNPdj9*$VIh`4M1SSzjt@_5FBD;N2u<H#u6Qo$T|{_ggU<`ym`*+{Bfhk3lm75K#-AS9%Hb(4pJY^i"
    "U&q=4npd-*+t%n;U)@};oo@mt%baDkmOkxf;~~uB)hh`0ZsJk{^Ch69CzeG#3@GW*QRNMwypn)7Y<@q&<WCx#cTSjVYd{T^Ke~)R"
    "8B|_chJ57M{QdLVcWR1Xyyv%XA~?$|&XUv3{hB^(E><M2?c8!p$1-!i$4R)cKdIJxKKZb`m*ey_j=I3MaOl;7|9!{5{$+Xm3F`UZ"
    "?VZ$1`OWS>@W+l%Tfe;BxaoL?m-*NHviE9x=gmL1-o9F2uKi=$KRiZIYO;8`ab&S(_;C!6f2qovLLbj-Uy-R?jmBNgigw-M*<W`U"
    "OeeD$YI+Z3_Uro6-Z6SMzjkNVCo#Uzw}bwCI{sL5<sa?R!dIX9)5N|-;!-5OdX?zOPOqmo_`iSA+To(Y@!;IhTwv1geSgK8{n$LU"
    "9~ZWDE{=g(G;Mjc>(tGz+qu&#UNacNm6ch3dRfwF+CMnA!7n;~{>9n9kMZw|$=<A+zF%I>Tzq=@#kIz5{LB%o{%~B^n)z)#>K`3V"
    "Cm+WLi_$h1&EFgkmj!;nH0lkzqq^MB|2p%UkEW08{`z<Zzq8%D_vRn}x^#%x>gvGbi7mT}*s=w`{9u6jAv?t%L#OVZzJ5O~@w&Wm"
    "m5;WRv89YHWo(Jk4|qlGhf5jR^Gg|@%{2ItQpTm}c;wmQJs9K1oGr3D?&HH|i#IoYaaCq>aaHDWd#`i77cR*(=i8ibbH2^_Hs{-%"
    "Z*#uQ`F^|et>$BMVLqOj`+W}AO1_i({i_~G)1MtrPfzQ->?O{3c`fSrx|<FT`m<TPM__Gx-Vc3Qa|NgiI}d00t9NkoJtZq$e2Oqx"
    "DNMcDavAFb^abDi1x~vcwin6ZWnnp0ly{TQNDaSQN>Dt%$Kr3ftiM0m!^c)Yc(ICp<CexP_rom<_W0P?rLjw6m&Pvl!Y(Iw!!D04"
    "J#OsM*rl<{_hgp^5Wdp8Jn~<mZS3+C*yXt_*FRr&Ice<D*yRRxdBM19{-ybsuV$Dfy4vDPqnMT+HF~)xdO2zI(&(kpOQV-Nr<b~Y"
    "v$>Z>FO6Orz1$bQH22czrLFEZdbx9Y`A;{U+|{l+dK&EV&%CpJC+tG^%P!Q+OJkR(ZeHpklwEIMv;?U+m<QvSM}FC{am+n&OuI_m"
    "IHviSXTve<;W>u4JCGX3G>&N;^DQ^&eu86I<Cw-VjbolA$FK+D7-}5TIHqw-TaUSidmUHPt1b9m*d$MSu}i+OOk<hGGIz%^ZDY*y"
    "wK4Ta3K!>6zVCX2{%pZ6$NTfuF;xB83Ntf6YoncV+D<v`J|1<0dUjtoomQBFxAxZ{G#t<7Riu^xS+@4P0g6c%t=5c}oV4)5n&dKB"
    "#+;)pErnzgFDhgqGv_4<t({SYiRi2s{>nM3Z?@lV?QZ>=dvAToyTA2b`TyD8@vnE+k5XO!HhpjL<C5o1NzRw#v~sqH;xu=OWvhiF"
    ";wCdE81YiLh|E#(%t&oLBdc<eBt+!3DQBIYc1M^sr-x5oh{1jBPU(-j`cskpKPQlm`FA-7@wEG!r~O@`@ni2)Y|dkC05Bi9QZ{)@"
    "Bn#6aY7YQf?kLK_wenmjpR^N6a=~N{Rsakxs=O@q@~M1hrIW`<%BV#&D4qeRJlPl`%b^5@A<deiwWS2>oQ#=C?uz!FiI7ZE0i~bZ"
    "OPf#bvCV(g-<Iu$<H4m_x15eQ58AnN*{tNgxn%pxBX{kQaVNLEy)de4YEgNx=|$6vrWbdq7vkacLVQobkU5d?DjDs#jY4M<iF~v^"
    "8l$A-o>F$sX+%0&=8Z^6fF*5WJ~OMs?Si3%ks1G4$-LBDk~J}?B7Abj6wL*AHc1aC3&~8>IdMpV_o>JbqSMz426wzHMqkKcbMe{-"
    "BT0hYg`vV7<5}sbv@R-T0@rKIA*qYw0`C-cyI>>}DH`q!XF-y2MQHA&F-8Ov6EjwD&6q8kNJBrORjhDZOtP#vsnmlC#@RW5C%s#b"
    "^13V<mGhctG|_0H(M03RMMDEWvIt`{2tH^aEaKnHbP7UZq^0m$a?r45PBIonlnSz;OpZ{OBySfD7jt0Q1REmg*D6^^xZp*M7DUUy"
    "$W+J`8KYnU)k93UA@a^gO^(a!MMDCHkQ>PZd0i~zKrxY&ci`}1To#7qtZiXM)+UCG`4dZ4PH@u3h1*4=0xFiMAsR?8bi!nd%tLjY"
    "HrX;ROsXhMS-9jQ#4fnNAWbH60%rAtipJRiY$v^2&rrH78jI!erW#E(nrgJAsV^1{<tc(}eevAcXaold3zq|D00PKd$C4y*pFN1)"
    "P~@2bdrT3FJ}NS|iv}<FCTRsplFq46jB?46=cy#_RAQ17coq-RK{aemYM3foC~ZaZH;9H$kTx%+OwwduqTnp0sC-3-4aOy{y)VHR"
    "jcf*4i$)?)&;gHJ#7X@r(cluZFd=(^yb+><oCR5x^9fR!e0Ey06rgFIbg&Ld5poR2WK7AR5A>j-aenI6N$>W9Yp%#fWq=!HW7OZD"
    "UDXY7r@C>IJOm_!k#r<VhF}RCi!5QF6Ef7ooYqPOL>g)>g3VcK25La^nXQ6sd)4IO9^`>aEXo=$P(!wv!#?^D1(NsTJ=_`06=q8c"
    "Nqglr?4Oi@;0je8FC)VhdGO)wuHSmy+j<?hU%h#mcXKapLmK?w^K%h~PZ7fBvp7}fN<vqYZV`ErD<hhqlocUjtQ-;nP^%`HjY_0s"
    "3?VC<k}#FwKeb+zT&%9yM6#MNH-p1NA$W55WJ->e%&ozoI}aweb!nd%w^_p_SaUs#E2Ir3iy~a~IpjbI9PK@9ItkD=&m1`gtVMK2"
    "64Du6pcsI(CCu{V)9oxSp&qdPNf1;GSU|2qii5>17fwmANh*PpFanhds|!9%&^)a}zz531viRBQKPSE05Ae9m;`Pq^=KUMFH}BuP"
    "{}-zU{1O94GtGtZbx8yPWDMLZt*Z;|tZKb134w-dXHiAyKvs<W;)%UoHEf9xn-C!XN<xM-q#%+vu*(I~6AWPOP%tH+%$p#rhoOV@"
    "ONl3~Zt(th(B_kSZ1Y2^#@VSWC%1p#I?dSpzw!Ql6OJYvSA=7Evd!!5*Q<YbUip_>|Ma_C+pl}Cw%)$-yYU|z*DA|Oavlx*uicli"
    "x_PBRzd^rwrf=~~m(Qh859gV_t7(ccTCM;!CQ>QLNHNAP#K^dlHKEOQ%Z5i<O_YS^JiCw*`2diX1h;UzY4Sx!rvge~OhxJNDz{X~"
    "09MF<Ln<;O->%E26qrW3uSAqFdh2VW%Jrs6y8@7wSdgRJ$h8oL8Ar09I&z-XOt}Q1$s)^V)`VEgO5V$W^jUmjFCWXC8Sepa6q%}F"
    "GCJX#UewJg!Ny3A8{>^KC|bEJvLlx*F_J<>{=ljBg~OyydY^F~%$2=;%T4o5Lz;#(4QYAz7fXl$b(<2bK$>a5o=W@ZqZ5vqOe6yf"
    "!G;ux40p`>B6Spk31A~x?KQt$LIPJ{-fRQsx_H5PVg<At3#<GKJP9zc@KGwQwFIQ=E8YsEw_FFyua^)LL#RSgkbMLDHj^*bCY5r?"
    "Dx1he2_+^>5X#1Jp&d#uwr=SFR?8>yZnO?+7Lc#I0%<@dt%5daxlS=qunKduB<YnPo-#+_kQ@f(O3Bo%g%7*CZ|&aHlisK9EW3Dv"
    "(d5EfhBg$8une;)M`>~>1}dF%)VV-7rSU4r6eKwTPXGbsEOPEOqT_U`>*{NrZZ|JAwYoF4x+RzYZ`GUuI39nV^p1~?x@m6@Z6B@("
    "{E{N=<g^tRnv}NQ?)uj;uZvOlehi`>biMhwn_m3*>+M%tul>v3_Uo6wZPYtBX@ze5Gs4iW8q*&Px}(~q`T?N&U_7res~L(l((R4-"
    "h(-f#_6ADzx$Im=W;7ttAL@bDd(PIGaiNg;wCh$y^u?Y~Obq%?NI?TPVyaVnLr2!y&ayq~kJxDB2G{iDwE3^LQ-0Zdn_uR*SVLLs"
    "&e3$Tx8EIHVg*h$d+>=v;<;50Nq~hWfcuqoK0$y<$z(wt+8ZHRf@b6YQt1Pn94{6AVZ2^=p?V381Ub-(2Z9(#opLO>UdOE$*kSxx"
    "6%1atVd%O&TWcf1P|gJtP6uN00c4Ky*91Zpq!1hl4~y0L7g@mCg&{*qbytRrng^XU^a#d+TTaXfRLh;>=!jmG{9$}JoP3y_4)w*>"
    "CzK4Eq$6?)rgDN0Lb`$i4YCzpwB=4@3zK51vbi9Ii_GH{a#8XuE)wSCaR20#{-&6F<AZvq@8NjV&E{(n!+3C%qLtFw`>2pRMI(jv"
    "swfK=hQKSdA3e&jYIXa$3_MFwkjjzr8@Exz>Fv>*==w@~HqX$#<OfW<dA${SW9#)U=FRp_@9p->Ul)^ShRHXX&cXbL!||{`KjXMT"
    "oreRy@%u$tJm}^%ZMnf`og106Z(Ol5%grR0ZWg}o$^xPvxy^7lgp3t_7Jf8Ghh)(C$RThxGhT1;l1K#wGFlOw<F5FeL}AOyZn!u3"
    "<oZ^e+)FD?u5ZO(?H049>d!{iSyT0<>P^)jyQ;JMR(0=8NCx?S5Qtm0&PK?lM#c)H8DnMi!7Ce+4mu#27p|xRrs4+lmL<O%Rp&Bt"
    "1>7+Y&{-(9DaeJLA;wFh#3N>rq>#8G%`*UuH>HuB0A4b_JfNz#`v9A=H)U_i-juy5`=eHN>+6{=I{54=G)tC{@Zwa8CDrTD^&+t%"
    "L@}@o#YJopL@uN*zyw>INq7g!t}KIUqkhXJixhIbLL5|JQHJD*OIf@XMPjZ6?o3VHt#zQvl8eCO11fvFS+hy|BVUStv7DDp-kZEP"
    "d4Dd;@h?ur_^QMU%S?f=W{iSiItZq83BZYADP}>^s*Ip|;1@$yib~!)AgFEzF-G1|@@`CkTxZlsj2W3QD1m#CIIIO`f_A#ja159a"
    "2@{A5ZJ9PDp_wt|hg_0xx7M~>Yuk18Cge@Xn~*=2>*_u-CT)oZp|1xg8DhTPXf2%)f&*PSE6o)1)`p-=jKLMAZNV@Wt75nt5ic@J"
    "CxBqfq0T^|EtDY_NYgPiT4hR-QBWxc43@Dh#~6(gER(?`d&oS!-C5ld^``Aj+ncsGZGYt2t}+r~Dh`Y!BNrAyDH;$1mYf821yzq;"
    "l+FpAl1x6iSh2vofWDK}ceDoo?X7qyZEyF#H+gUOzqk9}8}!@mlICoivu)1yk?t;$!SN)3(_no8Xekwzyb6e!&&~^_5E*X0c2)?7"
    "=dn~*S<e-BHm}Z@{bpw?3@S;^Y9~Sg$^!;R3&E2C`jlZsVjv4@_S_jzCjbmzD}pK<?bGr>SFPG11x@Im(q5C*57RcaZ))Gv{+ZwV"
    "32IW_GDIZe(XeDAX9~k(n7|MfSAUhHNSCwChEp(_d_7v)S>i?9yqENpWIkW=nZW?n)8CD<XbTlr>Muo+Dc({2JrQYGmKZ3TqH>-Y"
    "uK+6OJyStpo<HQRB42)}#M;ph7fHnDf*xp(SuUbZm}ar=)lJ1GBUo~QFloFHF{h}Nv?efXVxcT-MfAoc;56=S+}pVK%efaUu;}lZ"
    "uRH%OrQ%s4iMd#`$vGutA}nV^o~+PbS72zSgtRuN%$asBB@U-&4Cf_RsNEbmYfIKyyAbqZqL+*?Mx6uaR3t~)o<ioza-F0F5r!m~"
    "ttSCt3|({^pG$4sbUq%92k8IehqV76RQf%K"
)


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return ExactRational(numerator, denominator)


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _raw_sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


def _require_sha1(value: Any, where: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise StrictContractError(f"{where} must be canonical lowercase SHA-1")
    return value


@lru_cache(maxsize=2)
def _e1_generator(role: str) -> Any:
    coordinates = (("s0", 0), ("s1", 0), ("s2", 1)) if role == "source" else (
        ("t0", 0), ("t1", 0), ("t2", 1)
    )
    environment = ("A1" if role == "source" else "B2") * 32
    action = SyntheticAction(
        f"unit_cpu_survivor_e1_{role}_a", _payload("action", f"{role}_a")
    )
    vocabulary = ResponseVocabularyId.from_coordinate_names(("block_index",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,), response_vocabulary_id=vocabulary
    )
    frame_sha = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_{name}",
            payload=_payload("state", f"{role}_{name}"),
            totalized_kind=TotalizedStatus.OPEN,
            response_coordinates=(_r(coordinate),),
            frame_digest=frame_sha,
        )
        for name, coordinate in coordinates
    ) + tuple(
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_{name}",
            payload=_payload("state", f"{role}_{name}"),
            totalized_kind=status,
            response_coordinates=(_r(coordinate),),
            frame_digest=frame_sha,
        )
        for name, status, coordinate in (
            ("CLOSED", TotalizedStatus.CLOSED, 2),
            ("SINK", TotalizedStatus.SINK, 3),
        )
    )
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=environment,
        coordinate_names=("block_index",),
        seed_state_ids=tuple(
            state.state_id for state in states
            if state.totalized_kind is TotalizedStatus.OPEN
        ),
        states=states,
        actions=(action,),
        transitions=tuple(
            SyntheticTransitionRow(
                source_state_id=state.state_id,
                action_id=action.action_id,
                target_state_id=state.state_id,
                transition_semantics_digest=semantics.semantics_digest,
            )
            for state in states
        ),
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    return build_exact_quotient_coordinate_generator(
        verify_exact_partition(admitted, refine_exact_partition(admitted))
    )


def _e1_id(role: str, name: str) -> str:
    return f"unit_cpu_survivor_e1_{role}_{name}"


@lru_cache(maxsize=1)
def _accepted_e1_envelope() -> Any:
    source = _e1_generator("source")
    target = _e1_generator("target")
    layer = declare_synthetic_transfer_layer(
        source,
        target,
        (
            (_e1_id("target", "t0"), _e1_id("source", "s0"), _r(1)),
            (_e1_id("target", "t0"), _e1_id("source", "s1"), _r(-2)),
            (_e1_id("target", "t1"), _e1_id("source", "s1"), _r(1)),
            (_e1_id("target", "t1"), _e1_id("source", "s2"), _r(1, 2)),
            (_e1_id("target", "t2"), _e1_id("source", "s0"), _r(3)),
            (_e1_id("target", "t2"), _e1_id("source", "s2"), _r(-1)),
        ),
    )
    source_weights = make_positive_fiber_weights(
        source,
        {
            _e1_id("source", "s0"): _r(1),
            _e1_id("source", "s1"): _r(2),
            _e1_id("source", "s2"): _r(1),
            _e1_id("source", "CLOSED"): _r(1),
            _e1_id("source", "SINK"): _r(1),
        },
    )
    target_weights = make_positive_fiber_weights(
        target,
        {
            _e1_id("target", "t0"): _r(2),
            _e1_id("target", "t1"): _r(1),
            _e1_id("target", "t2"): _r(3),
            _e1_id("target", "CLOSED"): _r(1),
            _e1_id("target", "SINK"): _r(1),
        },
    )
    law = make_exact_finite_fiber_law(
        source,
        {
            _e1_id("source", "s0"): _r(1, 3),
            _e1_id("source", "s1"): _r(2, 3),
            _e1_id("source", "s2"): _r(1),
            _e1_id("source", "CLOSED"): _r(1),
            _e1_id("source", "SINK"): _r(1),
        },
    )
    result = build_fiber_envelope(
        layer,
        source_weights,
        target_weights,
        law,
        certify_fiber_completeness(layer, "source"),
        certify_fiber_completeness(layer, "target"),
    )
    if _sha(result.to_dict()) != _E1_ENVELOPE_SHA:
        raise StrictContractError("accepted E1 envelope identity changed")
    return result


_E2_MATRICES = {
    "M0": ((1, 2), (0, Fraction(1, 2))),
    "M1": ((Fraction(1, 2), 0), (3, 1)),
    "MRET": ((0, 2), (3, Fraction(1, 2))),
}


@lru_cache(maxsize=2)
def _e2_side(side: str) -> tuple[Any, tuple[Any, ...]]:
    if side == "source":
        environment = "53" * 32
        action_id = "unit_cpu_survivor_u24_e2_source_a"
        specs = (
            ("unit_cpu_survivor_u24_e2_source_open0_a", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_source_open0_b", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_source_open1", TotalizedStatus.OPEN, 1),
            ("unit_cpu_survivor_u24_e2_source_closed", TotalizedStatus.CLOSED, 2),
            ("unit_cpu_survivor_u24_e2_source_sink", TotalizedStatus.SINK, 3),
        )
    elif side == "target":
        environment = "54" * 32
        action_id = "unit_cpu_survivor_u24_e2_target_a"
        specs = (
            ("unit_cpu_survivor_u24_e2_target_open0", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_target_open1", TotalizedStatus.OPEN, 1),
            ("unit_cpu_survivor_u24_e2_target_closed", TotalizedStatus.CLOSED, 2),
            ("unit_cpu_survivor_u24_e2_target_sink", TotalizedStatus.SINK, 3),
        )
    else:
        raise StrictContractError("unknown E2 side")
    action = SyntheticAction(action_id, _payload("action", action_id))
    vocabulary = ResponseVocabularyId.from_coordinate_names(("e2_coordinate",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,), response_vocabulary_id=vocabulary
    )
    frame_sha = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=state_id,
            payload=_payload("state", state_id),
            totalized_kind=status,
            response_coordinates=(_r(coordinate),),
            frame_digest=frame_sha,
        )
        for state_id, status, coordinate in specs
    )
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=environment,
        coordinate_names=("e2_coordinate",),
        seed_state_ids=tuple(
            state.state_id for state in states
            if state.totalized_kind is TotalizedStatus.OPEN
        ),
        states=states,
        actions=(action,),
        transitions=tuple(
            SyntheticTransitionRow(
                source_state_id=state.state_id,
                action_id=action.action_id,
                target_state_id=state.state_id,
                transition_semantics_digest=semantics.semantics_digest,
            )
            for state in states
        ),
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    generator = build_exact_quotient_coordinate_generator(
        verify_exact_partition(admitted, refine_exact_partition(admitted))
    )
    return generator, states


@lru_cache(maxsize=3)
def _e2_parent(selector: str) -> dict[str, Any]:
    if selector not in _E2_MATRICES:
        raise StrictContractError("unknown E2 parent selector")
    source, source_states = _e2_side("source")
    target, target_states = _e2_side("target")
    matrix = _E2_MATRICES[selector]
    source_ids = (
        "unit_cpu_survivor_u24_e2_source_open0_a",
        "unit_cpu_survivor_u24_e2_source_open0_b",
        "unit_cpu_survivor_u24_e2_source_open1",
    )
    target_ids = (
        "unit_cpu_survivor_u24_e2_target_open0",
        "unit_cpu_survivor_u24_e2_target_open1",
    )
    coefficients = []
    for target_index, target_id in enumerate(target_ids):
        for source_id, coefficient in (
            (source_ids[0], matrix[target_index][0]),
            (source_ids[1], -matrix[target_index][0]),
            (source_ids[2], matrix[target_index][1]),
        ):
            exact = Fraction(coefficient)
            if exact:
                coefficients.append(
                    (target_id, source_id, _r(exact.numerator, exact.denominator))
                )
    layer = declare_synthetic_transfer_layer(source, target, tuple(coefficients))
    source_weights = make_positive_fiber_weights(
        source, {state.state_id: _r(1) for state in source_states}
    )
    target_weights = make_positive_fiber_weights(
        target, {state.state_id: _r(1) for state in target_states}
    )
    probabilities = {state.state_id: _r(1) for state in source_states}
    probabilities[source_ids[0]] = _r(1, 3)
    probabilities[source_ids[1]] = _r(2, 3)
    law = make_exact_finite_fiber_law(source, probabilities)
    source_completeness = certify_fiber_completeness(layer, "source")
    target_completeness = certify_fiber_completeness(layer, "target")
    envelope = build_fiber_envelope(
        layer,
        source_weights,
        target_weights,
        law,
        source_completeness,
        target_completeness,
    )
    return {
        "source_generator": source,
        "target_generator": target,
        "layer": layer,
        "source_weights": source_weights,
        "target_weights": target_weights,
        "source_law": law,
        "source_completeness": source_completeness,
        "target_completeness": target_completeness,
        "envelope": envelope,
    }


@lru_cache(maxsize=3)
def _e2_identification(selector: str) -> Any:
    parent = _e2_parent(selector)
    return e2c.identify_e2_source_target_coordinates(
        envelope=parent["envelope"],
        layer=parent["layer"],
        source_generator=parent["source_generator"],
        target_generator=parent["target_generator"],
        source_weights=parent["source_weights"],
        target_weights=parent["target_weights"],
        source_law=parent["source_law"],
        source_completeness=parent["source_completeness"],
        target_completeness=parent["target_completeness"],
    )


@lru_cache(maxsize=3)
def _e2_restriction(selector: str) -> Any:
    return e2c.build_e2_envelope_restriction(
        envelope=_e2_parent(selector)["envelope"],
        identification=_e2_identification(selector),
    )


@lru_cache(maxsize=2)
def _e2_safety(selector: str) -> Any:
    parent = _e2_parent(selector)
    return e2c.certify_e2_lifting_uniform_safety(
        envelope=parent["envelope"],
        identification=_e2_identification(selector),
        restriction=_e2_restriction(selector),
    )


@lru_cache(maxsize=2)
def _e2_cocycle(channel: str) -> Any:
    return e2c.certify_e2_cocycle(
        channel=channel,
        first=_e2_restriction("M0"),
        second=_e2_restriction("M1"),
    )


@lru_cache(maxsize=1)
def _e2_return_memory() -> Any:
    restriction = _e2_restriction("MRET")
    split = e2c.resolve_e2_memory_split(restriction=restriction)
    return e2c.bound_e2_finite_return_memory(restriction=restriction, split=split)


@lru_cache(maxsize=1)
def _e2_token() -> Any:
    manifest = e2s.build_declared_e2_candidate_universe(
        m0_identification=_e2_identification("M0"),
        m0_restriction=_e2_restriction("M0"),
        m0_safety=_e2_safety("M0"),
        m1_identification=_e2_identification("M1"),
        m1_restriction=_e2_restriction("M1"),
        m1_safety=_e2_safety("M1"),
    )
    token = e2s.apply_e2_binding_gate(
        manifest=manifest,
        p1_cocycle=_e2_cocycle("P1_BRANCHING_ADJUSTED"),
        p2_cocycle=_e2_cocycle("P2_BRANCHING_ADJUSTED"),
        return_memory=_e2_return_memory(),
    )
    token_bytes = canonical_contract_bytes(token.to_dict())
    if len(token_bytes) != 2185 or _raw_sha(token_bytes) != _E2_TOKEN_SHA:
        raise StrictContractError("live E2 support token identity changed")
    if _sha(_e2_parent("M0")["envelope"].to_dict()) != _E2_M0_ENVELOPE_SHA:
        raise StrictContractError("live E2 M0 envelope identity changed")
    return token


@lru_cache(maxsize=1)
def _me0_objects() -> tuple[Any, Any]:
    reference = me.make_declared_e2_support_reference(
        _e2_token().to_dict(),
        accepted_e2_commit_sha=_ACCEPTED_E2_COMMIT,
        accepted_e2_tree_sha=_ACCEPTED_E2_TREE,
    )
    problem = me.MaxEntProblem.create(
        reference,
        reference_mass_rows=(("c0", _r(1, 2)), ("c2", _r(1, 2))),
        statistic_rows=(("c0", (_r(0),)), ("c2", (_r(2),))),
        orbit_size_rows=(("c0", 1), ("c2", 2)),
        target=(_r(4, 5),),
        kl_radius=_r(1, 20),
        row_load_rows=(("c0", _r(1)), ("c2", _r(3))),
        nominal_operator_rows=(("c0", _r(2)), ("c2", _r(4))),
        exact_rule_column_ids=("g0",),
        exact_rule_rows=(("c0", (_r(1),)), ("c2", (_r(2),))),
    )
    result_raw = _ME0_RESULT_JSON.encode("utf-8")
    if len(result_raw) != 4177 or _raw_sha(result_raw) != _ME0_RESULT_SHA:
        raise StrictContractError("frozen Windows ME0 result bytes changed")
    result_wire = _strict_json_loads(result_raw)
    if canonical_contract_bytes(result_wire) != result_raw:
        raise StrictContractError("frozen Windows ME0 result is not canonical")
    result = me.MaxEntResult.from_dict(result_wire, problem=problem)
    me.verify_maxent_result(problem, result)
    return problem, result


def _primitive_rows() -> tuple[Any, ...]:
    ids = (
        "u24_s0_t0_node0",
        "u24_s0_t1_node1_edge01",
        "u24_s0_t2_edge11",
        "u24_s0_t3_ghost_return",
    )
    return (
        s0.PrimitiveTargetRow(ids[0], (_r(1), _r(0)), (_r(1), _r(0), _r(0)), _r(1, 8)),
        s0.PrimitiveTargetRow(ids[1], (_r(0), _r(2)), (_r(0), _r(1), _r(0)), _r(1, 8)),
        s0.PrimitiveTargetRow(ids[2], (_r(0), _r(0)), (_r(0), _r(0), _r(2)), _r(1, 8)),
        s0.PrimitiveTargetRow(ids[3], (_r(0), _r(0)), (_r(0), _r(0), _r(0)), _r(1, 8)),
    )


def _structural_measure_rows(certificate_wire: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for measure in certificate_wire["measures"]:
        projection = {
            "schema_version": "odlrq.s0.global-measure-structural-projection.v1",
            "measure_id": measure["measure_id"],
            "level": measure["level"],
            "normalization_mode": measure["normalization_mode"],
            "node_ids": measure["node_ids"],
            "edge_ids": measure["edge_ids"],
            "node_mass": measure["node_mass"],
            "edge_mass": measure["edge_mass"],
            "rho1": measure["rho1"],
            "rho2": measure["rho2"],
        }
        rows.append({"measure_id": measure["measure_id"], "measure_sha256": _sha(projection)})
    return rows


def _s0_positive_projection(
    certificate_wire: dict[str, Any], target_residuals: list[dict[str, Any]]
) -> dict[str, Any]:
    finite = certificate_wire["finite_remainder_certificate"]
    return {
        "schema_version": "odlrq.s0.positive-core-projection.v1",
        "hard_authority_reference": certificate_wire["hard_authority_reference"],
        "primitive_universe_sha256": certificate_wire["primitive_universe_sha256"],
        "l_plus_token": certificate_wire["l_plus_token"],
        "structural_measure_sha256_rows": _structural_measure_rows(certificate_wire),
        "positive_case_results": certificate_wire["positive_case_results"],
        "positive_transport_certificates": finite["positive_transport_certificates"],
        "coverage": certificate_wire["coverage"],
        "target_residuals": target_residuals,
        "positive_finite_remainder": {
            "adjacent_remainders": finite["adjacent_remainders"],
            "suffix_majorants": finite["suffix_majorants"],
            "composite_remainders": finite["composite_remainders"],
            "infinite_cutoff_claim": False,
        },
        "runtime_manifest_sha256": certificate_wire["runtime_manifest_sha256"],
        "disposition": certificate_wire["disposition"],
    }


def _s0_predictive_projection(certificate_wire: dict[str, Any]) -> dict[str, Any]:
    finite = certificate_wire["finite_remainder_certificate"]
    return {
        "schema_version": "odlrq.s0.predictive-core-projection.v1",
        "predictive_me0_result_reference": certificate_wire["predictive_me0_result_reference"],
        "structural_measure_sha256_rows": _structural_measure_rows(certificate_wire),
        "predictive_case_results": certificate_wire["predictive_case_results"],
        "predictive_transport_certificates": finite["predictive_transport_certificates"],
        "predictive_finite_remainder": {
            "adjacent_remainders": finite["adjacent_remainders"],
            "suffix_majorants": finite["suffix_majorants"],
            "composite_remainders": finite["composite_remainders"],
            "infinite_cutoff_claim": False,
        },
        "runtime_manifest_sha256": certificate_wire["runtime_manifest_sha256"],
        "disposition": certificate_wire["disposition"],
    }


@lru_cache(maxsize=1)
def _s0_fixture() -> Any:
    problem, result = _me0_objects()
    hard_reference = s0.make_declared_s0_hard_authority_reference(
        primitive_rows=_primitive_rows()
    )
    me0_reference = s0.make_declared_me0_result_reference(
        problem_wire=problem.to_dict(), result_wire=result.to_dict()
    )
    fixture = s0.build_declared_synthetic_similarity_fixture(
        hard_reference=hard_reference, me0_reference=me0_reference
    )
    certificate = fixture.similarity_certificate
    certificate_wire = certificate.to_dict()
    raw = canonical_contract_bytes(certificate_wire)
    if len(raw) != 78139 or _raw_sha(raw) != _S0_CERTIFICATE_SHA:
        raise StrictContractError("live S0 certificate identity changed")
    frozen = zlib.decompress(base64.b85decode(_S0_CERTIFICATE_B85.encode("ascii")))
    if frozen != raw:
        raise StrictContractError("live S0 certificate differs from activation bytes")
    target_residuals = [item.to_dict() for item in fixture.target_residuals]
    positive = canonical_contract_bytes(
        _s0_positive_projection(certificate_wire, target_residuals)
    )
    predictive = canonical_contract_bytes(_s0_predictive_projection(certificate_wire))
    if len(positive) != 44883 or _raw_sha(positive) != _S0_POSITIVE_SHA:
        raise StrictContractError("live S0 positive projection changed")
    if len(predictive) != 25173 or _raw_sha(predictive) != _S0_PREDICTIVE_SHA:
        raise StrictContractError("live S0 predictive projection changed")
    return fixture


# I0 typed-bound and artifact construction follows below.


_I0_FIXTURE_SEAL = object()
_I0_FIXTURE_CANONICAL_BYTES: tuple[bytes, bytes, bytes, bytes] | None = None
_I0_FIXTURE_CANONICAL_OBJECTS: tuple[Any, ...] | None = None


def _ordered_json_bytes(value: Any, where: str) -> bytes:
    try:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StrictContractError(f"{where} is not strict ordered JSON") from exc
    if len(raw) > _MAX_ARTIFACT_BYTES:
        raise StrictContractError(f"{where} exceeds one MiB")
    return raw


class _RawObjectPairs(list):
    """Marker used to retain object order and duplicates until validation."""


def _canonical_json_integer(token: str) -> int:
    try:
        value = int(token, 10)
    except ValueError as exc:
        raise StrictContractError("JSON integer token is invalid") from exc
    if token == "-0" or str(value) != token or not (-(2**63) <= value < 2**63):
        raise StrictContractError("JSON integer is not canonical signed-64")
    return value


def _reject_json_number(token: str) -> Any:
    raise StrictContractError(f"non-integer JSON number is forbidden: {token[:32]}")


def _strict_json_loads(raw: bytes, where: str = "strict JSON") -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > _MAX_ARTIFACT_BYTES:
        raise StrictContractError(f"{where} bytes are missing or over cap")
    try:
        decoded = raw.decode("utf-8", errors="strict")
        parsed = json.loads(
            decoded,
            object_pairs_hook=_RawObjectPairs,
            parse_int=_canonical_json_integer,
            parse_float=_reject_json_number,
            parse_constant=_reject_json_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictContractError(f"{where} bytes are not strict UTF-8 JSON") from exc

    node_count = 0

    def count_node() -> None:
        nonlocal node_count
        node_count += 1
        if node_count > _MAX_JSON_NODES:
            raise StrictContractError(f"{where} exceeds the JSON node cap")

    def check_string(value: str) -> None:
        try:
            size = len(value.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise StrictContractError(f"{where} contains invalid Unicode") from exc
        if size > _MAX_STRING_BYTES:
            raise StrictContractError(f"{where} contains an over-cap string")

    def convert(value: Any, depth: int) -> Any:
        if depth > _MAX_JSON_DEPTH:
            raise StrictContractError(f"{where} exceeds the JSON depth cap")
        count_node()
        if type(value) is _RawObjectPairs:
            if len(value) > _MAX_JSON_KEYS:
                raise StrictContractError(f"{where} object exceeds the key cap")
            result: dict[str, Any] = {}
            for key, item in value:
                if type(key) is not str:
                    raise StrictContractError(f"{where} object key is not a string")
                check_string(key)
                count_node()  # Object key strings count independently.
                if key in result:
                    raise StrictContractError(f"{where} contains duplicate key {key!r}")
                result[key] = convert(item, depth + 1)
            return result
        if type(value) is list:
            if len(value) > _MAX_JSON_ARRAY:
                raise StrictContractError(f"{where} array exceeds the length cap")
            return [convert(item, depth + 1) for item in value]
        if type(value) is str:
            check_string(value)
            return value
        if value is None or type(value) is bool:
            return value
        if type(value) is int:
            if not (-(2**63) <= value < 2**63):
                raise StrictContractError(f"{where} integer exceeds signed-64")
            return value
        raise StrictContractError(f"{where} contains a forbidden JSON scalar")

    value = convert(parsed, 0)
    if type(value) is not dict:
        raise StrictContractError(f"{where} root must be an object")
    if _ordered_json_bytes(value, where) != raw:
        raise StrictContractError(f"{where} is not exact insertion-order JSON")
    return value


def _ordered_json_object(raw: bytes, where: str) -> dict[str, Any]:
    return _strict_json_loads(raw, where)


def _live_candidate_manifest_wire(
    *,
    accepted_e1_envelope: Any,
    e2_m0_parent: dict[str, Any],
    p1_cocycle: Any,
    p2_cocycle: Any,
    return_memory: Any,
    support_token: Any,
    me0_result: Any,
    similarity_fixture: Any,
) -> dict[str, Any]:
    if type(e2_m0_parent) is not dict:
        raise StrictContractError("live E2 M0 parent must be the sealed fixture row")
    certificate_wire = similarity_fixture.similarity_certificate.to_dict()
    target_residuals = [item.to_dict() for item in similarity_fixture.target_residuals]
    positive_wire = _s0_positive_projection(certificate_wire, target_residuals)
    predictive_wire = _s0_predictive_projection(certificate_wire)
    live_wires = (
        e2_m0_parent["source_generator"].to_dict(),
        e2_m0_parent["target_generator"].to_dict(),
        accepted_e1_envelope.to_dict(),
        e2_m0_parent["envelope"].to_dict(),
        p1_cocycle.to_dict(),
        p2_cocycle.to_dict(),
        return_memory.to_dict(),
        support_token.to_dict(),
        me0_result.to_dict(),
        positive_wire,
        predictive_wire,
        certificate_wire,
    )
    manifest = e2c._i0_expected_manifest_wire()
    rows = manifest["ordered_bindings"]
    if type(rows) is not list or len(rows) != len(live_wires) or len(rows) != 12:
        raise StrictContractError("I0 candidate manifest does not contain twelve rows")
    for index, (row, live_wire) in enumerate(zip(rows, live_wires, strict=True)):
        if type(row) is not dict or type(live_wire) is not dict:
            raise StrictContractError(f"I0 live binding {index} is not an exact object")
        if live_wire.get("schema_version") != row["object_schema"]:
            raise StrictContractError(
                f"I0 live binding {row['binding_id']} object schema changed"
            )
        live_sha = _sha(live_wire)
        if live_sha != row["object_sha256"]:
            raise StrictContractError(
                f"I0 live binding {row['binding_id']} object identity changed"
            )
        # Assign the independently recomputed identity before strict manifest
        # parsing.  This prevents the frozen expected row from acting as a
        # digest-only substitute for its live predecessor.
        row["object_sha256"] = live_sha
    parsed = e2c._CandidateAuthorityManifest.from_dict(manifest)
    live_manifest = parsed.to_dict()
    if live_manifest != manifest:
        raise StrictContractError("I0 live candidate manifest failed strict roundtrip")
    return live_manifest


def _typed_bound(
    *,
    manifest: dict[str, Any],
    fail: bool,
    abstain: bool,
) -> e2c.TypedPipelineBound:
    factors = tuple(
        e2c.TypedPipelineFactor.from_dict(row)
        for row in e2c._i0_expected_factor_wires(fail=fail, abstain=abstain)
    )
    nominal = e2c.NominalPipelineAddendum.from_dict(
        e2c._i0_expected_nominal_wire()
    )
    result = e2c.construct_typed_pipeline_bound(
        candidate_authority_manifest=copy.deepcopy(manifest),
        ordered_hard_factors=factors,
        initial_residual=_r(1, 16),
        hard_threshold=_r(3, 4),
        nominal_addendum=nominal,
    )
    verified = e2c.verify_typed_pipeline_bound(
        bound=result,
        expected_candidate_authority_manifest=copy.deepcopy(manifest),
    )
    expected = (
        e2c.PipelineDisposition.ABSTAIN_INCOMPLETE_COVERAGE
        if abstain
        else e2c.PipelineDisposition.FAIL_HARD_BOUND_EXCEEDED
        if fail
        else e2c.PipelineDisposition.PASS
    )
    if verified.disposition is not expected:
        raise StrictContractError("I0 typed bound disposition changed")
    return verified


@dataclass(frozen=True, init=False)
class _U24I0Fixture:
    _candidate_manifest_bytes: bytes = field(repr=False)
    _pass_bound_bytes: bytes = field(repr=False)
    _fail_bound_bytes: bytes = field(repr=False)
    _abstain_bound_bytes: bytes = field(repr=False)
    _accepted_e1_envelope: Any = field(repr=False)
    _e2_m0_parent: dict[str, Any] = field(repr=False)
    _p1_cocycle: Any = field(repr=False)
    _p2_cocycle: Any = field(repr=False)
    _return_memory: Any = field(repr=False)
    _e2_support_token: Any = field(repr=False)
    _me0_problem: Any = field(repr=False)
    _me0_result: Any = field(repr=False)
    _similarity_fixture: Any = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("U24 I0 fixture has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not _U24I0Fixture:
            raise StrictContractError("U24 I0 fixture subclasses are forbidden")
        if self._construction_seal is not _I0_FIXTURE_SEAL:
            raise StrictContractError("U24 I0 fixture construction seal changed")
        manifest = _ordered_json_object(
            self._candidate_manifest_bytes, "I0 candidate manifest"
        )
        e2c._CandidateAuthorityManifest.from_dict(manifest)
        for name, raw, disposition in (
            ("PASS", self._pass_bound_bytes, e2c.PipelineDisposition.PASS),
            (
                "FAIL",
                self._fail_bound_bytes,
                e2c.PipelineDisposition.FAIL_HARD_BOUND_EXCEEDED,
            ),
            (
                "ABSTAIN",
                self._abstain_bound_bytes,
                e2c.PipelineDisposition.ABSTAIN_INCOMPLETE_COVERAGE,
            ),
        ):
            bound = e2c.TypedPipelineBound.from_dict(
                _ordered_json_object(raw, f"I0 {name} bound")
            )
            if bound.disposition is not disposition:
                raise StrictContractError(f"I0 {name} bound disposition changed")
        token_wire = e2s.CertifiedSupportToken.to_dict(self._e2_support_token)
        if len(canonical_contract_bytes(token_wire)) != 2185 or _sha(token_wire) != _E2_TOKEN_SHA:
            raise StrictContractError("fixture E2 support token changed")
        problem_wire = me.MaxEntProblem.to_dict(self._me0_problem)
        result_wire = me.MaxEntResult.to_dict(self._me0_result)
        if _sha(result_wire) != _ME0_RESULT_SHA:
            raise StrictContractError("fixture ME0 result changed")
        me.verify_maxent_result(self._me0_problem, self._me0_result)
        if self._similarity_fixture.similarity_certificate.to_dict()["disposition"] != (
            "CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED"
        ):
            raise StrictContractError("fixture S0 certificate disposition changed")
        del problem_wire

    @property
    def candidate_authority_manifest(self) -> dict[str, Any]:
        _quick_fixture_integrity(self)
        return _ordered_json_object(
            self._candidate_manifest_bytes, "I0 candidate manifest"
        )

    @property
    def pass_bound(self) -> e2c.TypedPipelineBound:
        _quick_fixture_integrity(self)
        return e2c.TypedPipelineBound.from_dict(
            _ordered_json_object(self._pass_bound_bytes, "I0 PASS bound")
        )

    @property
    def fail_bound(self) -> e2c.TypedPipelineBound:
        _quick_fixture_integrity(self)
        return e2c.TypedPipelineBound.from_dict(
            _ordered_json_object(self._fail_bound_bytes, "I0 FAIL bound")
        )

    @property
    def abstain_bound(self) -> e2c.TypedPipelineBound:
        _quick_fixture_integrity(self)
        return e2c.TypedPipelineBound.from_dict(
            _ordered_json_object(self._abstain_bound_bytes, "I0 ABSTAIN bound")
        )

    @property
    def e2_support_token(self) -> Any:
        _quick_fixture_integrity(self)
        return self._e2_support_token


def _quick_fixture_integrity(value: Any) -> _U24I0Fixture:
    if (
        type(value) is not _U24I0Fixture
        or value._construction_seal is not _I0_FIXTURE_SEAL
        or _I0_FIXTURE_CANONICAL_BYTES is None
        or _I0_FIXTURE_CANONICAL_OBJECTS is None
    ):
        raise StrictContractError("U24 I0 fixture seal is unavailable")
    current_bytes = (
        value._candidate_manifest_bytes,
        value._pass_bound_bytes,
        value._fail_bound_bytes,
        value._abstain_bound_bytes,
    )
    if current_bytes != _I0_FIXTURE_CANONICAL_BYTES:
        raise StrictContractError("U24 I0 fixture canonical bytes changed")
    current_objects = (
        value._accepted_e1_envelope,
        value._e2_m0_parent,
        value._p1_cocycle,
        value._p2_cocycle,
        value._return_memory,
        value._e2_support_token,
        value._me0_problem,
        value._me0_result,
        value._similarity_fixture,
    )
    if any(
        current is not expected
        for current, expected in zip(
            current_objects, _I0_FIXTURE_CANONICAL_OBJECTS, strict=True
        )
    ):
        raise StrictContractError("U24 I0 fixture live predecessor identity changed")
    return value


def _construct_i0_fixture(
    *,
    candidate_manifest: dict[str, Any],
    pass_bound: e2c.TypedPipelineBound,
    fail_bound: e2c.TypedPipelineBound,
    abstain_bound: e2c.TypedPipelineBound,
    accepted_e1_envelope: Any,
    e2_m0_parent: dict[str, Any],
    p1_cocycle: Any,
    p2_cocycle: Any,
    return_memory: Any,
    support_token: Any,
    me0_problem: Any,
    me0_result: Any,
    similarity_fixture: Any,
) -> _U24I0Fixture:
    global _I0_FIXTURE_CANONICAL_BYTES, _I0_FIXTURE_CANONICAL_OBJECTS
    result = object.__new__(_U24I0Fixture)
    object.__setattr__(
        result,
        "_candidate_manifest_bytes",
        _ordered_json_bytes(copy.deepcopy(candidate_manifest), "I0 candidate manifest"),
    )
    for name, bound in (
        ("_pass_bound_bytes", pass_bound),
        ("_fail_bound_bytes", fail_bound),
        ("_abstain_bound_bytes", abstain_bound),
    ):
        object.__setattr__(
            result,
            name,
            _ordered_json_bytes(e2c.TypedPipelineBound.to_dict(bound), name),
        )
    object.__setattr__(result, "_accepted_e1_envelope", accepted_e1_envelope)
    object.__setattr__(result, "_e2_m0_parent", e2_m0_parent)
    object.__setattr__(result, "_p1_cocycle", p1_cocycle)
    object.__setattr__(result, "_p2_cocycle", p2_cocycle)
    object.__setattr__(result, "_return_memory", return_memory)
    object.__setattr__(result, "_e2_support_token", support_token)
    object.__setattr__(result, "_me0_problem", me0_problem)
    object.__setattr__(result, "_me0_result", me0_result)
    object.__setattr__(result, "_similarity_fixture", similarity_fixture)
    object.__setattr__(result, "_construction_seal", _I0_FIXTURE_SEAL)
    result.__post_init__()
    canonical_bytes = (
        result._candidate_manifest_bytes,
        result._pass_bound_bytes,
        result._fail_bound_bytes,
        result._abstain_bound_bytes,
    )
    canonical_objects = (
        result._accepted_e1_envelope,
        result._e2_m0_parent,
        result._p1_cocycle,
        result._p2_cocycle,
        result._return_memory,
        result._e2_support_token,
        result._me0_problem,
        result._me0_result,
        result._similarity_fixture,
    )
    if _I0_FIXTURE_CANONICAL_BYTES is None:
        _I0_FIXTURE_CANONICAL_BYTES = canonical_bytes
        _I0_FIXTURE_CANONICAL_OBJECTS = canonical_objects
    elif (
        canonical_bytes != _I0_FIXTURE_CANONICAL_BYTES
        or _I0_FIXTURE_CANONICAL_OBJECTS is None
        or any(
            current is not expected
            for current, expected in zip(
                canonical_objects, _I0_FIXTURE_CANONICAL_OBJECTS, strict=True
            )
        )
    ):
        raise StrictContractError("U24 I0 fixture reconstruction changed")
    return result


@lru_cache(maxsize=1)
def build_u24_i0_fixture() -> _U24I0Fixture:
    accepted_e1 = _accepted_e1_envelope()
    e2_m0 = _e2_parent("M0")
    p1 = _e2_cocycle("P1_BRANCHING_ADJUSTED")
    p2 = _e2_cocycle("P2_BRANCHING_ADJUSTED")
    return_memory = _e2_return_memory()
    support_token = _e2_token()
    me0_problem, me0_result = _me0_objects()
    similarity_fixture = _s0_fixture()
    manifest = _live_candidate_manifest_wire(
        accepted_e1_envelope=accepted_e1,
        e2_m0_parent=e2_m0,
        p1_cocycle=p1,
        p2_cocycle=p2,
        return_memory=return_memory,
        support_token=support_token,
        me0_result=me0_result,
        similarity_fixture=similarity_fixture,
    )
    pass_bound = _typed_bound(manifest=manifest, fail=False, abstain=False)
    fail_bound = _typed_bound(manifest=manifest, fail=True, abstain=False)
    abstain_bound = _typed_bound(manifest=manifest, fail=False, abstain=True)
    return _construct_i0_fixture(
        candidate_manifest=manifest,
        pass_bound=pass_bound,
        fail_bound=fail_bound,
        abstain_bound=abstain_bound,
        accepted_e1_envelope=accepted_e1,
        e2_m0_parent=e2_m0,
        p1_cocycle=p1,
        p2_cocycle=p2,
        return_memory=return_memory,
        support_token=support_token,
        me0_problem=me0_problem,
        me0_result=me0_result,
        similarity_fixture=similarity_fixture,
    )


# Artifact construction starts after this typed fixture boundary.


_ARTIFACT_SCHEMAS = (
    "u24_envelope_core_v1",
    "u24_maxent_fixture_v1",
    "u24_local_tower_v1",
    "u24_global_measure_v1",
    "u24_level_transport_v1",
    "u24_similarity_certificate_v1",
    "u24_integrated_certificate_v1",
)
_ARTIFACT_TIERS = (
    "EXACT_DECLARED_SYNTHETIC",
    "NOMINAL_DIAGNOSTIC_ONLY",
    "CERTIFIED_SYNTHETIC",
    "TYPED_MIXED_CONTAINER_NOT_HARD_ELIGIBLE",
    "CERTIFIED_SYNTHETIC",
    "TYPED_HARD_WITH_PREDICTIVE_SIDECAR",
    "TYPED_HARD_WITH_NOMINAL_DIAGNOSTIC",
)
_ARTIFACT_PROJECTION_SCHEMAS = (
    "u24_envelope_core_operator_projection_v1",
    "u24_maxent_fixture_operator_projection_v1",
    "u24_local_tower_positive_operator_projection_v1",
    "u24_global_measure_operator_projection_v1",
    "u24_level_transport_positive_operator_projection_v1",
    "u24_similarity_certificate_operator_projection_v1",
    "u24_integrated_certificate_operator_projection_v1",
)
_ARTIFACT_RUNTIMES = (
    _S0_RUNTIME_SHA,
    _FULL_RUNTIME_SHA,
    _S0_RUNTIME_SHA,
    _FULL_RUNTIME_SHA,
    _S0_RUNTIME_SHA,
    _FULL_RUNTIME_SHA,
    _FULL_RUNTIME_SHA,
)
_ARTIFACT_DISPOSITIONS = (
    "CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED",
    "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED",
    "FINITE_LEVEL_MORPHISM_VERIFIED",
    "CPU_SYNTHETIC_GLOBAL_MEASURE_CONTAINER_VERIFIED",
    "FINITE_LEVEL_MORPHISM_VERIFIED",
    "CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED",
    "CPU_SYNTHETIC_U2_U4_CANDIDATE_CONSTRUCTED",
)
_ARTIFACT_PREDECESSORS = (
    ("E2.m0_parent_envelope",),
    ("E2.support_token", "ME0.nontrivial_orbit_windows_result"),
    ("S0.local_tower", "S0.full_similarity_certificate"),
    (
        "ME0.nontrivial_orbit_windows_result",
        "S0.positive_core",
        "S0.predictive_core",
        "S0.full_similarity_certificate",
    ),
    ("S0.local_tower", "S0.positive_core", "S0.full_similarity_certificate"),
    ("S0.positive_core", "S0.predictive_core", "S0.full_similarity_certificate"),
    ("I0.candidate_authority_manifest", "I0.typed_pipeline_bound"),
)


def _artifact_coverage(
    covered: int, universe: int, scope: str, complete: bool
) -> dict[str, Any]:
    if (
        type(covered) is not int
        or type(universe) is not int
        or type(complete) is not bool
        or not (0 <= covered <= universe <= 256)
        or complete is not (covered == universe)
    ):
        raise StrictContractError("artifact coverage is not counted exactly")
    return {
        "schema_version": "u24_artifact_coverage_v1",
        "covered_count": covered,
        "universe_count": universe,
        "coverage_scope": scope,
        "complete": complete,
    }


def _positive_morphism_projection(wire: dict[str, Any]) -> dict[str, Any]:
    expected = (
        "schema_version",
        "axis",
        "source_level",
        "target_level",
        "node_matrix",
        "edge_matrix",
        "edge_orientation",
        "coverage",
        "commutator_l1",
        "target_residual_transport",
        "cross_covariance_budget",
        "numeric_residual_budget",
        "remainder_e",
        "norm_id",
        "disposition",
    )
    if type(wire) is not dict or tuple(wire) != expected:
        raise StrictContractError("production morphism wire order changed")
    return {
        "schema_version": "u24_positive_morphism_projection_v1",
        "axis": wire["axis"],
        "source_level": copy.deepcopy(wire["source_level"]),
        "target_level": copy.deepcopy(wire["target_level"]),
        "node_matrix": copy.deepcopy(wire["node_matrix"]),
        "edge_matrix": copy.deepcopy(wire["edge_matrix"]),
        "edge_orientation": wire["edge_orientation"],
        "coverage": copy.deepcopy(wire["coverage"]),
        "commutator_l1": copy.deepcopy(wire["commutator_l1"]),
        "target_residual_transport": copy.deepcopy(
            wire["target_residual_transport"]
        ),
        "remainder_e": copy.deepcopy(wire["remainder_e"]),
        "norm_id": wire["norm_id"],
        "disposition": wire["disposition"],
    }


def _matrix_product(
    left: list[list[dict[str, Any]]], right: list[list[dict[str, Any]]]
) -> list[list[dict[str, Any]]]:
    if (
        type(left) is not list
        or type(right) is not list
        or not left
        or not right
        or any(type(row) is not list for row in (*left, *right))
        or any(len(row) != len(left[0]) for row in left)
        or any(len(row) != len(right[0]) for row in right)
        or len(left[0]) != len(right)
    ):
        raise StrictContractError("morphism matrices are not composable")
    result: list[list[dict[str, Any]]] = []
    for row in left:
        result_row: list[dict[str, Any]] = []
        for column in range(len(right[0])):
            value = sum(
                Fraction(
                    ExactRational.from_dict(row[index]).numerator,
                    ExactRational.from_dict(row[index]).denominator,
                )
                * Fraction(
                    ExactRational.from_dict(right[index][column]).numerator,
                    ExactRational.from_dict(right[index][column]).denominator,
                )
                for index in range(len(right))
            )
            result_row.append(_r(value.numerator, value.denominator).to_dict())
        result.append(result_row)
    return result


def _finite_remainder_projection(
    remainder: dict[str, Any], *, predictive: bool
) -> dict[str, Any]:
    channel = (
        "predictive_transport_certificates"
        if predictive
        else "positive_transport_certificates"
    )
    schema = (
        "u24_predictive_finite_remainder_projection_v1"
        if predictive
        else "u24_positive_finite_remainder_projection_v1"
    )
    certificates = remainder[channel]
    return {
        "schema_version": schema,
        "adjacent_remainders": copy.deepcopy(remainder["adjacent_remainders"]),
        "suffix_majorants": copy.deepcopy(remainder["suffix_majorants"]),
        "composite_remainders": copy.deepcopy(remainder["composite_remainders"]),
        "transport_certificate_sha256s": [_sha(row) for row in certificates],
        "infinite_cutoff_claim": remainder["infinite_cutoff_claim"],
    }


def _predictive_upper_rows(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in case_rows:
        distance = case["predictive_distance"]
        rows.append(
            {
                "schema_version": "u24_predictive_upper_row_v1",
                "case_id": case["case_id"],
                "distance": None if distance is None else distance["predictive_metric"],
                "upper_bound": (
                    None if distance is None else distance["discrepancy_upper_bound"]
                ),
            }
        )
    return {"schema_version": "u24_predictive_upper_rows_v1", "rows": rows}


def _safety_majorant_rows(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in case_rows:
        distance = case["positive_distance"]
        rows.append(
            {
                "schema_version": "u24_safety_majorant_row_v1",
                "case_id": case["case_id"],
                "representation_distance": (
                    None
                    if distance is None
                    else copy.deepcopy(distance["positive_representation_distance"])
                ),
                "safety_majorant": (
                    None if distance is None else copy.deepcopy(distance["safety_majorant"])
                ),
                "disposition": (
                    case["expected_error"]
                    if distance is None
                    else distance["disposition"]
                ),
            }
        )
    return {"schema_version": "u24_safety_majorant_rows_v1", "rows": rows}


def _assert_positive_only(value: Any, where: str) -> None:
    if type(value) is dict:
        for key, item in value.items():
            lowered = key.lower()
            if key in ("cross_covariance_budget", "numeric_residual_budget"):
                raise StrictContractError(f"{where} contains a predictive budget")
            if "me0" in lowered:
                raise StrictContractError(f"{where} contains ME0 provenance")
            if lowered.startswith("predictive_") and item is not None:
                raise StrictContractError(f"{where} contains predictive data")
            _assert_positive_only(item, where)
        return
    if type(value) is list:
        for item in value:
            _assert_positive_only(item, where)
        return
    if type(value) is str and ("NOMINAL" in value or "PREDICTIVE" in value):
        raise StrictContractError(f"{where} contains a nominal/predictive value")


@lru_cache(maxsize=1)
def _artifact_context() -> dict[str, Any]:
    fixture = build_u24_i0_fixture()
    _quick_fixture_integrity(fixture)
    manifest = fixture.candidate_authority_manifest
    bound = e2c.verify_typed_pipeline_bound(
        bound=fixture.pass_bound,
        expected_candidate_authority_manifest=manifest,
    )
    if bound.disposition is not e2c.PipelineDisposition.PASS:
        raise StrictContractError("artifact construction requires the exact PASS bound")

    e2_parent = fixture._e2_m0_parent
    token = fixture._e2_support_token
    problem = fixture._me0_problem
    result = fixture._me0_result
    similarity_fixture = fixture._similarity_fixture
    certificate = similarity_fixture.similarity_certificate
    hard_binding = s0.bind_s0_hard_authorities(
        accepted_e1_qualification_envelope=fixture._accepted_e1_envelope,
        e2_m0_parent_envelope=e2_parent["envelope"],
        e2_support_token=token,
    )
    me0_binding = s0.bind_me0_result(problem=problem, result=result)
    s0.verify_similarity_certificate_live(
        certificate=certificate,
        hard_binding=hard_binding,
        me0_binding=me0_binding,
    )
    me.bind_e2_support(token)
    me.verify_maxent_result(problem, result)

    certificate_wire = certificate.to_dict()
    target_residuals = [item.to_dict() for item in similarity_fixture.target_residuals]
    positive_wire = _s0_positive_projection(certificate_wire, target_residuals)
    predictive_wire = _s0_predictive_projection(certificate_wire)
    tower_wire = similarity_fixture.local_tower.to_dict()
    manifest_wire = copy.deepcopy(manifest)
    bound_wire = bound.to_dict()
    live_wires = {
        "E2.m0_parent_envelope": e2_parent["envelope"].to_dict(),
        "E2.support_token": token.to_dict(),
        "ME0.nontrivial_orbit_windows_result": result.to_dict(),
        "S0.positive_core": positive_wire,
        "S0.predictive_core": predictive_wire,
        "S0.full_similarity_certificate": certificate_wire,
        "S0.local_tower": tower_wire,
        "I0.candidate_authority_manifest": manifest_wire,
        "I0.typed_pipeline_bound": bound_wire,
    }
    manifest_rows = {row["binding_id"]: row for row in manifest["ordered_bindings"]}
    if len(manifest_rows) != 12:
        raise StrictContractError("candidate authority binding IDs are not unique")
    for binding_id, live_wire in live_wires.items():
        if binding_id in manifest_rows:
            row = manifest_rows[binding_id]
            if (
                live_wire.get("schema_version") != row["object_schema"]
                or _sha(live_wire) != row["object_sha256"]
            ):
                raise StrictContractError(f"live predecessor {binding_id} changed")

    return {
        "fixture": fixture,
        "manifest": manifest_wire,
        "manifest_rows": manifest_rows,
        "bound": bound_wire,
        "e2_parent": e2_parent,
        "problem": problem.to_dict(),
        "result": result.to_dict(),
        "similarity_fixture": similarity_fixture,
        "certificate": certificate_wire,
        "target_residuals": target_residuals,
        "positive": positive_wire,
        "predictive": predictive_wire,
        "tower": tower_wire,
        "live_wires": live_wires,
    }


def _predecessor_rows(
    context: dict[str, Any], binding_ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    rows = []
    local_types = {
        "S0.local_tower": (
            "odlrq.s0.local-tower.v1",
            "CANONICAL_CONTRACT_BYTES_SHA256",
        ),
        "I0.candidate_authority_manifest": (
            "odlrq.i0.candidate-authority-manifest.v1",
            "CANONICAL_CONTRACT_BYTES_SHA256",
        ),
        "I0.typed_pipeline_bound": (
            "odlrq.i0.typed-pipeline-bound.v1",
            "CANONICAL_CONTRACT_BYTES_SHA256",
        ),
    }
    for binding_id in binding_ids:
        live_wire = context["live_wires"].get(binding_id)
        if type(live_wire) is not dict:
            raise StrictContractError(f"missing live predecessor {binding_id}")
        if binding_id in context["manifest_rows"]:
            authority = context["manifest_rows"][binding_id]
            object_schema = authority["object_schema"]
            digest_domain = authority["digest_domain"]
            expected_sha = authority["object_sha256"]
        else:
            object_schema, digest_domain = local_types[binding_id]
            expected_sha = _sha(live_wire)
        live_sha = _sha(live_wire)
        if live_wire.get("schema_version") != object_schema or live_sha != expected_sha:
            raise StrictContractError(f"predecessor {binding_id} failed live binding")
        rows.append(
            {
                "schema_version": "u24_artifact_predecessor_binding_v1",
                "binding_id": binding_id,
                "object_schema": object_schema,
                "object_sha256": live_sha,
                "digest_domain": digest_domain,
                "live_verified": True,
            }
        )
    return rows


def _artifact_payloads(context: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    parent = context["e2_parent"]
    problem = context["problem"]
    result = context["result"]
    certificate = context["certificate"]
    tower = context["tower"]
    remainder = certificate["finite_remainder_certificate"]

    radius = _positive_morphism_projection(tower["radius_morphism"])
    word_depth = _positive_morphism_projection(tower["word_depth_morphism"])
    granularity = _positive_morphism_projection(tower["granularity_morphism"])
    composite_node = _matrix_product(
        tower["radius_morphism"]["node_matrix"],
        _matrix_product(
            tower["word_depth_morphism"]["node_matrix"],
            tower["granularity_morphism"]["node_matrix"],
        ),
    )
    composite_edge = _matrix_product(
        tower["radius_morphism"]["edge_matrix"],
        _matrix_product(
            tower["word_depth_morphism"]["edge_matrix"],
            tower["granularity_morphism"]["edge_matrix"],
        ),
    )
    composition = {
        "schema_version": "u24_level_composition_v1",
        "composition_order": copy.deepcopy(tower["composition_order"]),
        "composite_node_matrix": composite_node,
        "composite_edge_matrix": composite_edge,
        "positive_composite_remainders": copy.deepcopy(
            remainder["composite_remainders"]
        ),
    }
    restrictions = {
        "schema_version": "u24_local_restrictions_v1",
        "radius_morphism": radius,
        "word_depth_morphism": word_depth,
        "granularity_morphism": granularity,
    }
    cauchy = {
        "schema_version": "u24_cauchy_majorant_v1",
        "adjacent_remainders": copy.deepcopy(remainder["adjacent_remainders"]),
        "suffix_majorants": copy.deepcopy(remainder["suffix_majorants"]),
        "composite_remainders": copy.deepcopy(remainder["composite_remainders"]),
        "infinite_cutoff_claim": remainder["infinite_cutoff_claim"],
    }
    predictive_remainder = _finite_remainder_projection(remainder, predictive=True)
    positive_remainder = _finite_remainder_projection(remainder, predictive=False)
    predictive_metric = {
        "schema_version": "u24_predictive_metric_projection_v1",
        "case_results": copy.deepcopy(certificate["predictive_case_results"]),
        "transport_certificates": copy.deepcopy(
            remainder["predictive_transport_certificates"]
        ),
        "finite_remainder_projection": predictive_remainder,
    }
    positive_metric = {
        "schema_version": "u24_positive_metric_projection_v1",
        "case_results": copy.deepcopy(certificate["positive_case_results"]),
        "transport_certificates": copy.deepcopy(
            remainder["positive_transport_certificates"]
        ),
        "finite_remainder_projection": positive_remainder,
    }
    maxent_residuals = {
        "schema_version": "u24_maxent_residuals_v1",
        "simplex_residual": result["simplex_residual"],
        "moment_residual_inf": result["moment_residual_inf"],
        "dual_residual_inf": result["dual_residual_inf"],
        "operator_span_residual": result["operator_span_residual"],
        "kl_divergence": result["kl_divergence"],
        "kl_within_radius": result["kl_within_radius"],
    }
    bound = context["bound"]

    payloads = (
        {
            "generator": {
                "schema_version": "u24_envelope_generator_pair_v1",
                "source_generator": parent["source_generator"].to_dict(),
                "target_generator": parent["target_generator"].to_dict(),
            },
            "source_weights": parent["source_weights"].to_dict(),
            "target_weights": parent["target_weights"].to_dict(),
            "fiber_law": parent["source_law"].to_dict(),
            "transfer_layer": parent["layer"].to_dict(),
            "completeness_witness": {
                "schema_version": "u24_completeness_witness_pair_v1",
                "source_witness": parent["source_completeness"].to_dict(),
                "target_witness": parent["target_completeness"].to_dict(),
            },
            "inclusion_witness": {
                "schema_version": "u24_inclusion_witness_absence_v1",
                "comparison_performed": False,
                "reason": "SINGLE_ENVELOPE_NO_MONOTONE_EXTENSION_CLAIM",
                "sole_envelope_sha256": _E2_M0_ENVELOPE_SHA,
            },
            "envelope": parent["envelope"].to_dict(),
        },
        {
            "support_token": context["live_wires"]["E2.support_token"],
            "reference_law": {
                "schema_version": "u24_maxent_reference_law_v1",
                "support_candidate_ids": copy.deepcopy(problem["support_candidate_ids"]),
                "reference_mass_rows": copy.deepcopy(problem["reference_mass_rows"]),
            },
            "orbit_law": copy.deepcopy(result["orbit_reference"]),
            "statistics": {
                "schema_version": "u24_maxent_statistics_v1",
                "statistic_rows": copy.deepcopy(problem["statistic_rows"]),
            },
            "target": copy.deepcopy(problem["target"]),
            "kl_radius": copy.deepcopy(problem["kl_radius"]),
            "status": result["status"],
            "probabilities": copy.deepcopy(result["probabilities"]),
            "residuals": maxent_residuals,
        },
        {
            "levels": copy.deepcopy(tower["ordered_levels"]),
            "restrictions": restrictions,
            "cauchy_majorant": cauchy,
        },
        {
            "measures": copy.deepcopy(certificate["measures"]),
            "predictive_metric": predictive_metric,
            "predictive_upper_bound": _predictive_upper_rows(
                certificate["predictive_case_results"]
            ),
            "positive_representation_distance": positive_metric,
            "safety_majorant": _safety_majorant_rows(
                certificate["positive_case_results"]
            ),
        },
        {
            "radius_morphism": radius,
            "word_depth_morphism": word_depth,
            "granularity_morphism": granularity,
            "composition": composition,
        },
        {
            "coverage": copy.deepcopy(certificate["coverage"]),
            "target_residuals": copy.deepcopy(context["target_residuals"]),
            "l_plus_token": copy.deepcopy(certificate["l_plus_token"]),
            "remainder_certificate": copy.deepcopy(remainder),
        },
        {
            "candidate_manifest": copy.deepcopy(context["manifest"]),
            "stages": copy.deepcopy(bound["ordered_hard_factors"]),
            "initial_residual": copy.deepcopy(bound["initial_residual"]),
            "hard_bound": copy.deepcopy(bound["hard_bound"]),
            "nominal_addendum": copy.deepcopy(bound["nominal_addendum"]),
            "total_bound": copy.deepcopy(bound["total_bound"]),
            "coverage": copy.deepcopy(bound["coverage"]),
            "disposition": bound["disposition"],
        },
    )
    _assert_positive_only(payloads[0], "envelope hard payload")
    _assert_positive_only(payloads[2], "local tower hard payload")
    _assert_positive_only(payloads[4], "level transport hard payload")
    _assert_positive_only(positive_metric, "positive metric projection")
    _assert_positive_only(payloads[3]["safety_majorant"], "safety majorant")
    return payloads


def _artifact_coverages() -> tuple[dict[str, Any], ...]:
    return (
        _artifact_coverage(4, 4, "E2_M0_SOURCE_BLOCKS", True),
        _artifact_coverage(2, 3, "E2_CANDIDATE_UNIVERSE_SUPPORT", False),
        _artifact_coverage(4, 4, "S0_DECLARED_SIMILARITY_DOMAIN", True),
        _artifact_coverage(4, 4, "S0_DECLARED_SIMILARITY_DOMAIN", True),
        _artifact_coverage(4, 4, "S0_DECLARED_SIMILARITY_DOMAIN", True),
        _artifact_coverage(4, 4, "S0_DECLARED_SIMILARITY_DOMAIN", True),
        _artifact_coverage(4, 4, "I0_HARD_DOMAIN_CHAIN", True),
    )


def _build_u24_artifact_wires(
    *, source_commit: str, source_tree: str
) -> tuple[tuple[str, bytes], ...]:
    source_commit = _require_sha1(source_commit, "source_commit")
    _require_sha1(source_tree, "source_tree")
    context = _artifact_context()
    payloads = _artifact_payloads(context)
    coverages = _artifact_coverages()
    if not all(
        len(rows) == 7
        for rows in (
            _ARTIFACT_NAMES,
            _ARTIFACT_SCHEMAS,
            _ARTIFACT_TIERS,
            _ARTIFACT_PROJECTION_SCHEMAS,
            _ARTIFACT_RUNTIMES,
            _ARTIFACT_DISPOSITIONS,
            _ARTIFACT_PREDECESSORS,
            payloads,
            coverages,
        )
    ):
        raise StrictContractError("seven-artifact contract table changed")

    wires: list[tuple[str, bytes]] = []
    for index, name in enumerate(_ARTIFACT_NAMES):
        payload_without_report = payloads[index]
        projection: dict[str, Any] = {
            "schema_version": _ARTIFACT_PROJECTION_SCHEMAS[index]
        }
        for key, value in payload_without_report.items():
            projection[key] = copy.deepcopy(value)
        operator_sha = _sha(projection)
        report_schema = _ARTIFACT_SCHEMAS[index][:-3] + "_verification_report_v1"
        report = {
            "schema_version": report_schema,
            "operator_projection_sha256": operator_sha,
            "ordered_predecessor_bindings": _predecessor_rows(
                context, _ARTIFACT_PREDECESSORS[index]
            ),
            "runtime_identity_sha256": _ARTIFACT_RUNTIMES[index],
            "coverage_verified": True,
            "tier_firewall_verified": True,
            "live_verification_disposition": (
                "STRICT_ARTIFACT_PREDECESSORS_LIVE_VERIFIED"
            ),
        }
        payload = copy.deepcopy(payload_without_report)
        payload["verification_report"] = report
        wrapper = {
            "schema_version": _ARTIFACT_SCHEMAS[index],
            "evidence_scope": "synthetic_development",
            "source_commit": source_commit,
            "observation_frame_id": _FRAME_ID,
            "reachable_domain_id": _REACHABLE_DOMAIN_ID,
            "response_vocabulary_id": _RESPONSE_VOCABULARY_ID,
            "transition_semantics_id": _TRANSITION_SEMANTICS_ID,
            "domain_scope": _DOMAIN_SCOPE,
            "runtime_identity_sha256": _ARTIFACT_RUNTIMES[index],
            "operator_tier": _ARTIFACT_TIERS[index],
            "operator_sha256": operator_sha,
            "coverage": coverages[index],
            "censors": [],
            "disposition": _ARTIFACT_DISPOSITIONS[index],
            "payload": payload,
        }
        raw = _ordered_json_bytes(wrapper, name)
        _strict_json_loads(raw, name)
        wires.append((name, raw))
    if sum(len(raw) for _name, raw in wires) > _MAX_AGGREGATE_BYTES:
        raise StrictContractError("artifact aggregate exceeds seven MiB")
    return tuple(wires)


def _require_i0_fixture(value: Any) -> _U24I0Fixture:
    expected = build_u24_i0_fixture()
    if type(value) is not _U24I0Fixture or value is not expected:
        raise StrictContractError("fixture is not the sealed live I0 fixture")
    return _quick_fixture_integrity(value)


def build_u24_artifact_wires(
    *, fixture: Any, source_commit: Any, source_tree: Any
) -> tuple[tuple[str, bytes], ...]:
    _require_i0_fixture(fixture)
    source_commit = _require_sha1(source_commit, "source_commit")
    source_tree = _require_sha1(source_tree, "source_tree")
    return _build_u24_artifact_wires(
        source_commit=source_commit, source_tree=source_tree
    )


def verify_u24_artifact_wires(
    *,
    fixture: Any,
    source_commit: Any,
    source_tree: Any,
    ordered_wires: Any,
) -> tuple[tuple[str, bytes], ...]:
    _require_i0_fixture(fixture)
    source_commit = _require_sha1(source_commit, "source_commit")
    source_tree = _require_sha1(source_tree, "source_tree")
    if type(ordered_wires) is not tuple or len(ordered_wires) != 7:
        raise StrictContractError("ordered_wires must be the exact seven-row tuple")
    supplied: list[tuple[str, bytes]] = []
    aggregate = 0
    for index, row in enumerate(ordered_wires):
        if type(row) is not tuple or len(row) != 2:
            raise StrictContractError("artifact wire row must be an exact pair")
        name, raw = row
        if name != _ARTIFACT_NAMES[index] or type(raw) is not bytes or not raw:
            raise StrictContractError("artifact name/order/byte type changed")
        if len(raw) > _MAX_ARTIFACT_BYTES:
            raise StrictContractError(f"{name} exceeds one MiB")
        aggregate += len(raw)
        if aggregate > _MAX_AGGREGATE_BYTES:
            raise StrictContractError("artifact aggregate exceeds seven MiB")
        obj = _strict_json_loads(raw, name)
        if obj.get("source_commit") != source_commit:
            raise StrictContractError(f"{name} source commit changed")
        supplied.append((name, raw))
    expected = _build_u24_artifact_wires(
        source_commit=source_commit, source_tree=source_tree
    )
    if tuple(supplied) != expected:
        raise StrictContractError("artifact wires differ from live strict reconstruction")
    return expected


def _is_reparse(metadata: os.stat_result) -> bool:
    return bool(getattr(metadata, "st_file_attributes", 0) & 0x400)


def _lstat_no_reparse(path: Path, *, directory: bool) -> os.stat_result:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise StrictContractError(str(exc)[:4096]) from exc
    if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
        raise StrictContractError("symlink/reparse traversal is forbidden")
    if directory and not stat.S_ISDIR(metadata.st_mode):
        raise StrictContractError("expected an exact directory")
    if not directory and not stat.S_ISREG(metadata.st_mode):
        raise StrictContractError("expected an exact regular file")
    return metadata


def _require_safe_ancestor_chain(
    path: Path,
) -> tuple[tuple[Path, os.stat_result], ...]:
    cursor = path
    rows: list[tuple[Path, os.stat_result]] = []
    while True:
        if not os.path.lexists(cursor):
            raise StrictContractError("destination parent chain must already exist")
        metadata = _lstat_no_reparse(cursor, directory=True)
        rows.append((cursor, metadata))
        if cursor.parent == cursor:
            return tuple(rows)
        cursor = cursor.parent


def _require_same_directory(path: Path, expected: os.stat_result) -> None:
    current = _lstat_no_reparse(path, directory=True)
    if (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino):
        raise StrictContractError("directory identity changed during emission")


def _require_same_ancestor_chain(
    expected: tuple[tuple[Path, os.stat_result], ...]
) -> None:
    if type(expected) is not tuple or not expected:
        raise StrictContractError("ancestor identity snapshot is unavailable")
    for path, metadata in expected:
        _require_same_directory(path, metadata)


def _read_regular_file(path: Path) -> bytes:
    _lstat_no_reparse(path, directory=False)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise StrictContractError(str(exc)[:4096]) from exc
    chunks: list[bytes] = []
    total = 0
    try:
        metadata = os.fstat(descriptor)
        if (
            stat.S_ISLNK(metadata.st_mode)
            or _is_reparse(metadata)
            or not stat.S_ISREG(metadata.st_mode)
        ):
            raise StrictContractError("opened artifact is not a regular file")
        while True:
            block = os.read(descriptor, min(65_536, _MAX_ARTIFACT_BYTES + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > _MAX_ARTIFACT_BYTES:
                raise StrictContractError("reread artifact exceeds one MiB")
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _directory_wires(root: Path) -> tuple[tuple[str, bytes], ...]:
    _lstat_no_reparse(root, directory=True)
    try:
        with os.scandir(root) as entries:
            rows = list(entries)
    except OSError as exc:
        raise StrictContractError(str(exc)[:4096]) from exc
    if len(rows) != 7 or {row.name for row in rows} != set(_ARTIFACT_NAMES):
        raise StrictContractError("artifact directory is not the exact seven-file set")
    for row in rows:
        metadata = row.stat(follow_symlinks=False)
        if row.is_symlink() or _is_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
            raise StrictContractError("artifact directory contains a reparse/non-file entry")
    return tuple((name, _read_regular_file(root / name)) for name in _ARTIFACT_NAMES)


def _write_regular_once(path: Path, raw: bytes) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise StrictContractError(str(exc)[:4096]) from exc
    try:
        written = os.write(descriptor, raw)
        if written != len(raw):
            raise StrictContractError("one-shot artifact write was partial")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if _read_regular_file(path) != raw:
        raise StrictContractError("artifact reread differs from in-memory bytes")


def _cleanup_owned_staging(
    staging: Path, expected_metadata: os.stat_result
) -> None:
    if not os.path.lexists(staging):
        return
    _require_same_directory(staging, expected_metadata)
    try:
        with os.scandir(staging) as entries:
            rows = list(entries)
    except OSError as exc:
        raise StrictContractError(str(exc)[:4096]) from exc
    for row in rows:
        metadata = row.stat(follow_symlinks=False)
        if (
            row.name not in _ARTIFACT_NAMES
            or row.is_symlink()
            or _is_reparse(metadata)
            or not stat.S_ISREG(metadata.st_mode)
        ):
            raise StrictContractError("refusing to clean staging with foreign content")
    try:
        for row in rows:
            _require_same_directory(staging, expected_metadata)
            os.unlink(staging / row.name)
        _require_same_directory(staging, expected_metadata)
        os.rmdir(staging)
    except OSError as exc:
        raise StrictContractError(str(exc)[:4096]) from exc


def _emission_receipt(
    *,
    source_commit: str,
    source_tree: str,
    ordered_wires: tuple[tuple[str, bytes], ...],
) -> bytes:
    receipt = {
        "schema_version": "u24_artifact_emission_receipt_v1",
        "source_commit": source_commit,
        "source_tree": source_tree,
        "ordered_artifacts": [
            [name, len(raw), _raw_sha(raw)] for name, raw in ordered_wires
        ],
        "disposition": "CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED",
    }
    raw = _ordered_json_bytes(receipt, "artifact emission receipt")
    if len(raw) > _MAX_RECEIPT_BYTES:
        raise StrictContractError("artifact emission receipt exceeds 4096 bytes")
    return raw


def emit_u24_artifacts(
    *, fixture: Any, source_commit: Any, source_tree: Any, destination_root: Any
) -> bytes:
    """Emit under the registered single-writer Windows runner.

    Existing reparse points and every observed directory-identity change fail
    closed.  The contract does not claim isolation from a hostile same-privilege
    process racing filesystem path lookup; the registered parent preflight is
    therefore an exclusive single-writer boundary.
    """
    fixture = _require_i0_fixture(fixture)
    source_commit = _require_sha1(source_commit, "source_commit")
    source_tree = _require_sha1(source_tree, "source_tree")
    if type(destination_root) is not type(Path()):
        raise StrictContractError("destination_root must be an exact concrete Path")
    wires = build_u24_artifact_wires(
        fixture=fixture, source_commit=source_commit, source_tree=source_tree
    )
    verify_u24_artifact_wires(
        fixture=fixture,
        source_commit=source_commit,
        source_tree=source_tree,
        ordered_wires=wires,
    )
    receipt = _emission_receipt(
        source_commit=source_commit, source_tree=source_tree, ordered_wires=wires
    )
    destination = destination_root.absolute()
    parent = destination.parent
    ancestor_chain = _require_safe_ancestor_chain(parent)
    parent_metadata = ancestor_chain[0][1]
    if os.path.lexists(destination):
        raise StrictContractError("destination_root must be absent")
    nonce = secrets.token_hex(16)
    if len(nonce) != 32 or any(ch not in "0123456789abcdef" for ch in nonce):
        raise StrictContractError("control nonce is not canonical")
    staging = parent / (
        ".uprime_odlrq_post_e2_upper_stack_20260717.staging."
        f"{source_commit[:12]}.{os.getpid()}.{nonce}"
    )
    if os.path.lexists(staging):
        raise StrictContractError("fresh staging path already exists")

    created = False
    published = False
    staging_metadata: os.stat_result | None = None
    try:
        os.mkdir(staging, 0o700)
        created = True
        staging_metadata = _lstat_no_reparse(staging, directory=True)
        _require_same_ancestor_chain(ancestor_chain)
        _require_same_directory(parent, parent_metadata)
        for name, raw in wires:
            _require_same_ancestor_chain(ancestor_chain)
            _require_same_directory(parent, parent_metadata)
            _require_same_directory(staging, staging_metadata)
            _write_regular_once(staging / name, raw)
        staged_wires = _directory_wires(staging)
        verify_u24_artifact_wires(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            ordered_wires=staged_wires,
        )
        _require_same_ancestor_chain(ancestor_chain)
        _require_same_directory(parent, parent_metadata)
        _require_same_directory(staging, staging_metadata)
        if os.path.lexists(destination):
            raise StrictContractError("destination appeared before atomic rename")
        os.rename(staging, destination)
        published = True
        published_metadata = _lstat_no_reparse(destination, directory=True)
        if (published_metadata.st_dev, published_metadata.st_ino) != (
            staging_metadata.st_dev,
            staging_metadata.st_ino,
        ):
            raise StrictContractError("published directory identity changed")
        published_wires = _directory_wires(destination)
        verify_u24_artifact_wires(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            ordered_wires=published_wires,
        )
        return receipt
    except StrictContractError:
        raise
    except Exception as exc:
        raise StrictContractError(str(exc)[:4096]) from exc
    finally:
        if (
            created
            and not published
            and staging_metadata is not None
            and os.path.lexists(staging)
        ):
            _cleanup_owned_staging(staging, staging_metadata)


class _FixedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise StrictContractError(f"CLI argument error: {message[:4096]}")


def _official_artifact_root() -> Path:
    leaf = "uprime_" + "odlrq_" + "post_e2_" + "upper_stack_" + "20260717"
    return Path("docs") / "experiments" / "artifacts" / leaf


def _main(*, argv: Sequence[str] | None = None) -> int:
    parser = _FixedArgumentParser(
        prog="uprime_u2_u4_development", allow_abbrev=False
    )
    commands = parser.add_subparsers(dest="command", required=True)
    emit = commands.add_parser("emit", allow_abbrev=False)
    emit.add_argument("--source-commit", required=True)
    emit.add_argument("--source-tree", required=True)
    arguments = parser.parse_args(argv)
    if arguments.command != "emit":
        raise StrictContractError("only the fixed emit command is licensed")
    fixture = build_u24_i0_fixture()
    receipt = emit_u24_artifacts(
        fixture=fixture,
        source_commit=arguments.source_commit,
        source_tree=arguments.source_tree,
        destination_root=_official_artifact_root(),
    )
    sys.stdout.buffer.write(receipt)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except StrictContractError as error:
        diagnostic = str(error).encode("utf-8", errors="replace")
        if len(diagnostic) >= _MAX_ERROR_BYTES:
            diagnostic = diagnostic[: _MAX_ERROR_BYTES - 1]
        sys.stderr.buffer.write(diagnostic + b"\n")
        sys.stderr.buffer.flush()
        raise SystemExit(2) from None
