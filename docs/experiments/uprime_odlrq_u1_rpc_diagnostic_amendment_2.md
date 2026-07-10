# U'1 live RPC diagnostic amendment 2: terminal response and process reap

Status: FROZEN BEFORE THE THIRD LIVE EXECUTION. This amendment, its harness
changes, and its tests must be committed, pushed, and green in CI before the
next canonical Windows CPU run. It does not reclassify either immutable prior
artifact.

## Trigger and scope

The run anchored at `fc6b69ea14fb2d7820a190aea22df9409f59b666` received all
23 registered JSON responses, including `ok=true, shutdown=true`, but the Lean
process did not exit during the harness's ten-second wait. The harness then
raised `HARNESS_ERROR` before its eleven-contract evaluator. The durable result
is recorded in
`uprime_odlrq_u1_rpc_diagnostic_amendment_1_execution_2026-07-10.md` and remains
`HARNESS_ERROR`.

The artifact shows that 13 states were reported and that process exit was not
observed inside the wait. It does not establish that retained states caused the
delay. This amendment changes only terminal transport accounting, compact
control-response evidence, and the verdict-level transport gate. It does not
repair or weaken any scientific contract.

The following base-anchor blobs remain normative and unchanged:

- native Lean worker: `5b9df6067ef739241ecf56bc0b8221791777c916`;
- original preregistration: `a4aeca102c907135fe61597405ab868d41419c8e`;
- amendment 1: `c608c876fc3789262bfec49ed0ceb1a4e834817a`;
- tier manifest: `c9a584e6a70ff246d674babc7c238573b452b4e6`.

The 23-frame sequence, fixtures, actions, heartbeat constants, expected state
and request counts, `CONTRACT_IDS`, and `evaluate_contracts` decision rules are
unchanged. Known null IDs/protocol fields, null budget telemetry, unknown
replay commands, and action failures make this a result-aware diagnostic rerun,
not a new blinded discovery attempt.

## Frozen terminal state machine

The scientific stream is complete when the fixed frame-23 request receives one
JSON object within the existing 900-second stream deadline. The response is
stored before any teardown operation. Three predicates remain distinct:

1. `stream_complete`: a frame-23 JSON response was received;
2. `shutdown_ack_ok`: `ok is true`, `shutdown is true`, and `error` is absent
   or JSON null;
3. the request ID and protocol envelope match, which is still evaluated only by
   `R0_request_id_echo`.

The reader thread captures the monotonic receipt time immediately after parsing
the complete JSON response and before placing it on the transport queue, UTC
formatting, or response hashing. That captured receipt time is the origin of
one non-configurable monotonic ten-second post-response deadline. It is
independent of the remaining 900-second
stream budget and is partitioned as follows:

- at most 5.0 seconds for natural process exit;
- at most 4.0 seconds for bounded forced reap;
- at least the final 1.0 second is reserved for joining both reader threads and
  checking terminal frames.

These values sum to the original preregistered ten-second post-response bound.
They cannot be changed by CLI input or selected from observed runtime.

If natural wait returns code zero, the exit is graceful. A natural nonzero code
is `HARNESS_ERROR`. The natural wait uses only the remainder of the interval
from receipt time through receipt time plus 5.0 seconds. An exit observed only
after that boundary is `natural_after_grace`: contracts may be aggregated, but
the transport clear gate fails. After the five-second boundary, the harness
polls once before sending a signal. If still alive, invocation of `terminate`
permanently sets `forced_reap=true`; later return codes cannot relabel it
natural. The terminate grace is at most 2.0 seconds. If still alive, `kill` is
invoked and the worker must exit inside the remaining four-second forced-reap
budget. Failure to reap is `HARNESS_ERROR`.

A successful forced reap permits contract aggregation only when
`shutdown_ack_ok=true`. If the shutdown acknowledgment is invalid and a signal
is required, the run is `HARNESS_ERROR`. An invalid acknowledgment followed by
natural code-zero exit may be aggregated and will fail the transport gate. R0
continues to evaluate its own shutdown flags and request envelope independently.

After process exit, both stdout and stderr reader threads must join inside the
same common ten-second deadline. Only then is the stdout queue drained. It must
contain exactly one `("eof", null)` terminal item, with no residual response,
missing/duplicate EOF, queue overflow, or non-JSON stdout. Any violation is
`HARNESS_ERROR`. Stderr count and tail are retained as telemetry but are not by
themselves a failure. HEAD and all anchor blobs are rechecked after this drain
and before contract evaluation; drift is `HARNESS_ERROR`.

Emergency cleanup following an already-classified harness exception does not
convert that exception into a contract result and cannot alter the recorded
exit mode.

## Transport clear gate and verdict matrix

The eleven scientific contracts remain unchanged. A separate verdict-level
gate, `X0_shutdown_transport_clear`, requires all of:

- complete stream and successful shutdown acknowledgment;
- response SHA bound to the stored frame-23 response;
- return-code-zero exit observed inside the five-second natural grace;
- no forced reap;
- both readers joined, exactly one EOF, no overflow, and JSON-only stdout;
- total post-response elapsed time no greater than 10.0 seconds and
  `transport_finalized=true`.

Forced reap is therefore allowed to expose the contract failures hidden by the
second harness error, but it can never license `U1_DIAGNOSTIC_CLEAR`.

| Stream/transport outcome | Eleven contracts | Top-level verdict |
|---|---|---|
| incomplete frame sequence, reap failure, reader/EOF/overflow/anchor error | not authoritative | `HARNESS_ERROR` |
| finalized transport, any contract false | one or more failures | `U1_DIAGNOSTIC_BLOCKED` |
| finalized transport with any X0 check false, all contracts true | none | `U1_DIAGNOSTIC_BLOCKED` via `X0_shutdown_transport_clear` |
| code-zero exit observed inside five-second natural grace and every X0 check true | all true | `U1_DIAGNOSTIC_CLEAR` |

Every outcome keeps `licenses_later_stage=false`. No U'0.5 kill probe, later
U' stage, or GPU construction is licensed by this diagnostic alone.

## Frozen evidence changes

New reports use schema `lean-rgc-uprime-rpc-diagnostic-v1.1`. Each compact
response entry retains its full-response SHA-256, frame index, receipt UTC
timestamp, and the previously omitted control fields `loaded`, `shutdown`,
`n_states`, `n_requests`, and `n_failures`. The report records the response
count.

Transport telemetry includes the fixed time partition, shutdown-response SHA,
ack status, exit mode, signal attempts, forced-reap success, reader status,
EOF/residual frame counts and kinds, overflow/non-JSON/stderr counts,
finalization status, return code, and post-response elapsed time. The
publication-safe artifact must retain these fields without interpreting a
forced reap as graceful shutdown.

## Execution discipline

Amendment 2 is a new anchor input in addition to amendment 1. Before the third
live run, the new anchor must be pushed, upstream must contain it, and CI must
pass. The command, Windows CPU lane, exact Lean executable digest, canonical
path reservation, non-overwrite publication, and 900-second CLI value remain
those in the original preregistration. A third unique artifact is mandatory;
neither earlier artifact may be overwritten or rerun under its old anchor.
