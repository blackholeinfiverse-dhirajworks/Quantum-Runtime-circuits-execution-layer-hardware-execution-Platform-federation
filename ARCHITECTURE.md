# Architecture & Integration — Quantum Runtime / Execution Layer package

## 1. Position in the programme architecture

```
BHIV DOMAIN DATA ──► VANA / UCICS / AIAIC / BHARAT MALA / MARINE        (data: domain teams — PENDING real data)
        │
        ▼
PROBLEM FORMULATION ─► CLASSICAL BASELINE ─► QUANTUM ALGORITHM          phase3_domains/domain_usecases.py
        │                                                                (QUBO → Ising → QAOA; brute-force baseline)
        ▼
QUANTUM RUNTIME  ─────────────────────────────────────────────────────  hardware_manifest.py  (BackendAdapter,
        │                                                                 certify(), check_fit(), manifests)
        ▼
QUANTUM NETWORK  ─────────────────────────────────────────────────────  phase4_network/ (Transport interface,
        │                                                                 sharded execution, fault handling)
        ▼
REAL QUANTUM HARDWARE ◄── NOT AVAILABLE: adapters report unavailable; no hardware result exists
        │
        ▼
MEASUREMENT + UNCERTAINTY ──► QCG / GOVERNANCE / PROVENANCE ──► INSIGHTFLOW ──► BHIV INTELLIGENCE
                              (owned elsewhere — NOT integrated by this package)
```

## 2. Ownership boundaries (from the role matrix) and how this package respects them

| Boundary | How it is respected |
|---|---|
| Federation / connectivity is Kanishk's | Execution consumes an injected **`Transport`** interface. `SimTransport` is an in-process **test double**; no federation is implemented or claimed. |
| Domain applications are Ganesh's; data is the domain teams' | Domain files are **templates on synthetic data**, flagged `synthetic_data: true`. They should be reconciled with Ganesh's work, not treated as the domain deliverable. |
| Hardware/infra integration is Pritesh's | Cloud adapters (IBM, IonQ) only *declare* availability (dependency + credential env var); `execute()` raises `BackendUnavailable` and is otherwise unimplemented by design. |
| Governance, provenance, replay authority sit with TMS/GC/MDU | Outputs carry `decision_authority: "NONE"`, `authority_ceiling: "ADVISORY_COMPUTE"`, an explicit negative-authority list, deterministic IDs and hash-chained logs — they *emit* evidence; they do not own or judge it. |
| QCG repository | Not modified, not required by anything here. |

**Critical boundary honoured:** attachment does not transfer authority. No component here makes or executes a decision.

## 3. Interfaces

- **`BackendAdapter`** (`hardware_manifest.py`): `is_available() -> {available, reason}` (never raises) and `execute(circuit, shots, seed)`. Honest capability marking: a missing dependency or credential ⇒ unavailable ⇒ `execute` raises. Never mocks success.
- **`certify(result)`**: the only path to a certification label. `is_real_hardware=False → SIMULATOR_VERIFIED`; `HARDWARE_VERIFIED` requires `is_real_hardware=True` **and** a provider `job_id` and backend name; anything undeclared raises.
- **`check_fit(qubits, backend_qubits, depth, max_depth)`**: pre-flight rejection. `max_depth` is caller-supplied (derive from real calibration later; not invented here).
- **`Transport.send(node, request, now_ms) -> [Delivery]`** (`qnet_workload.py`): 0 deliveries = lost/down, >1 = duplicates. Coordinator provides idempotent `invocation_id`s, validation, quarantine, bounded retries, PARTIAL disclosure, hash-chained replayable log.

## 4. Determinism & provenance model
All IDs are SHA-256 over canonical JSON (sorted keys, compact separators). Seeds are fixed (42). Time in the network workload is a **virtual clock**; no wall-clock value enters any hash. Same inputs ⇒ same `aggregate_hash` / `events_head` (tested).

## 5. What is real vs simulated

| Item | Status |
|---|---|
| Circuits, statevector/density-matrix maths, QAOA optimisation | Real computation (Qiskit/Aer/numpy) |
| Device models for transpilation (line/grid/all-to-all, basis rz/sx/x/cz) | **Generic models, not any real device** |
| Noise model (1q 1e-3, 2q 1e-2, readout 2%) | **Assumed** round numbers, not measured |
| Network transport | **Simulated** test double; no real network |
| Domain data | **Synthetic**, seeded |
| Hardware results, calibration, job IDs | **None exist.** Fields are `NOT_YET_EXECUTED_ON_HARDWARE` |

## 6. Integration points still open (not bypassed, not simulated as done)
1. **QCG / InsightFlow ingestion** — needs the agreed result schema and approval; authentication (401) and unavailable InsightCore endpoints are to be documented as blockers when encountered. Nothing in this package calls them.
2. **Real federation transport** — implement `Transport` against Kanishk's layer; the 15 networking tests are the acceptance suite to re-run unchanged.
3. **Real backend submission** — implement `_CloudAdapter.execute` only once access and approval exist; `certify()` and `check_fit()` already gate the result.
4. **Real domain data** — replace the `*_fire_risk/_housing/_crops/_hubs/_routing` constructors' synthetic inputs; the evaluation harness is data-agnostic.
