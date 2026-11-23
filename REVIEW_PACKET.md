# REVIEW_PACKET — BHIV Quantum Runtime / Execution-Layer Package

**Role scope:** Quantum Runtime + circuits + execution layer + hardware-execution readiness (role matrix).
**Status headline:** simulator-verified; **no hardware executed**; **domain data synthetic**; **federation simulated**;
QCG/InsightFlow **not integrated**. Algorithm Laboratory Labs 1–5 are **not in this repository snapshot** (see §12).

---

## 1. Entry Point

```bash
pip install -r requirements.txt
python phase1_learning/learning_experiments.py          # Phase 1: 13 concept experiments
python phase3_domains/domain_usecases.py                # Phase 3: VANA, UCICS, AIAIC, Bharat Mala, Marine (QAOA)
python phase4_network/qnet_physics.py                   # Phase 4: link fidelity, swapping chain, non-local CNOT
python phase5_hardware/hardware_manifest.py             # Phase 5: manifest, transpile tables, noise sensitivity
pytest phase6_testing algorithm_lab -v                  # Phase 6: 71 + 8 tests
```

## 2. Quantum Problem

Five QUBO workloads on **synthetic, seeded data** (templates for the domain teams to re-point at real data):

| Domain | Problem |
|---|---|
| VANA | fire-risk resource prioritisation: knapsack under a crew-day budget |
| UCICS | housing allocation on a 3×3 grid: maximum-weight independent set (no adjacent developed parcels) |
| AIAIC | crop allocation under a water budget with rotation-conflict penalties (quadratic knapsack) |
| Bharat Mala | choose 3 of 10 river-port hubs (p-median); **QUBO is a surrogate** |
| Marine | survey-vessel routing: base + 3 waypoints, one-hot TSP |

Plus network workloads: noisy entanglement distribution / swapping / non-local CNOT, and a sharded GHZ execution
workload with fault injection; plus a chemistry VQE adapter lab (H2, O2, toy model).

## 3. Mathematical Formulation

- QUBO: minimise Σᵢ aᵢxᵢ + Σᵢ<ⱼ bᵢⱼxᵢxⱼ + c, with x ∈ {0,1}ⁿ. Inequality budgets use slack bits and the penalty
  P·(Σ wᵢxᵢ + Σₖ 2ᵏsₖ − B)². Constraint penalties P ≥ 1.5·(max single gain) (Marine: 2.5·max distance).
- Ising map x = (1−z)/2 gives h, J; QAOA cost layer = RZZ(2γJᵢⱼ) and RZ(2γhᵢ), mixer = RX(2β). The QUBO↔Ising energy
  equality is asserted on sampled bitstrings for every instance.
- Werner link (depolarising λ on half a Bell pair): F = (1+3v)/4, S_CHSH = 2√2·v, v = 1−λ; swapping over m links: v → vᵐ.
- Decoherence-style channels (Phase 1): T1/T2 and depolarising channels checked against exp(−t/T).

## 4. Classical Baseline

- Exact brute force over all decision vectors (≤ 2¹² states) for every domain instance.
- Random search given the **same shot budget**, plus an exact "shots needed to find the optimum" curve computed from the statevector.
- Bharat Mala: the true p-median cost is used for evaluation; the surrogate-vs-true gap is reported separately (0.0 on this instance).
- Chemistry (Lab 6): exact diagonalisation of each Hamiltonian.
- Network: closed-form Werner/CHSH expressions.

## 5. Quantum Algorithm

QAOA, p = 2. Parameters tuned by COBYLA (4 random starts) on the exact statevector expectation (numpy fast path);
the same parameters are then built as a Qiskit circuit, **cross-checked against the numpy simulation (max probability
difference < 1e-8, asserted)**, and sampled with 4096 shots on AerSimulator. Lab 6 uses UCCSD-VQE (PySCF, Jordan–Wigner).

## 6. Core Execution Flow (5 critical files)

1. `phase5_hardware/hardware_manifest.py` — entry point: manifests, backend adapters, certification gate, fit check
2. `phase3_domains/domain_usecases.py` — QUBO builders, QAOA, baselines, evaluation
3. `phase4_network/qnet_workload.py` — transport interface, sharded execution, validation, replay
4. `phase6_testing/test_governance_execution.py` — governance + execution tests
5. `phase6_testing/test_qnet_workload.py` — network failure scenarios

## 7. Circuit / Network Flow

```
QUBO ─► Ising (h,J) ─► H⊗n → [RZZ·RZ cost → RX mixer]×2 ─► measure ─► decode decision bits ─► domain objective
coordinator ─► shard(shots) ─► Transport.send(node) ─► validate(circuit_hash, shot-sum, support)
        └► retry / quarantine / dedup ─► aggregate ─► hash-chained event log ─► replay()
```

## 8. Live or Simulator Execution

Simulator only (AerSimulator / statevector / density matrix), fixed seed 42. Network transport is an in-process test double.

## 9. Real JSON / Result Evidence

Domain QAOA (`phase3_domains/domain_results.json`; "lift" = QAOA probability mass on the optimal decision vector ÷ uniform;
P(find) = chance the optimum appears within 16 shots, QAOA vs random):

| Domain | Qubits | Exact optimum | P(feasible): QAOA vs uniform | Lift | P(find ≤16 shots) | Slack bits |
|---|---|---|---|---|---|---|
| VANA | 12 | 3.92 (max) | 0.883 vs 0.500 | 1.02x | 0.0621 vs 0.0607 | yes |
| UCICS | 9 | 14.73 (max) | 0.713 vs 0.123 | 6.38x | 0.1819 vs 0.0308 | no |
| AIAIC | 12 | 21.13 (max) | 0.905 vs 0.539 | 0.76x | 0.0462 vs 0.0607 | yes |
| BHARAT_MALA | 10 | 128.5941 (min) | 0.557 vs 0.117 | 5.93x | 0.0888 vs 0.0155 | no |
| MARINE | 9 | 209.9104 (min) | 0.152 vs 0.012 | 13.84x | 0.3551 vs 0.0308 | no |

**Reading this honestly:** QAOA concentrates probability on *feasible* states for every problem, but on the two
**slack-bit knapsack** problems its mass on the *optimal decision vector* is no better than random: lift 1.02× for VANA
and **0.76× (worse than random) for AIAIC**, where QAOA is slightly *less* likely than random search to hit the optimum
within 16 shots (0.046 vs 0.061) — the slack qubits absorb the concentration. On the problems without slack (UCICS, Bharat Mala, Marine)
the lift is roughly 6–14×. With 4096 shots both QAOA and random search find the optimum on every instance
(search spaces ≤ 4096 states), so best-of-shots does not discriminate; the shots-to-optimum curve does.
Marine note: each tour has an equal-length mirror twin, so its single-vector lift slightly undercounts.

Chemistry adapters (`algorithm_lab/vqe_adapter_run_result.json`, Hartree units for molecules):

| Adapter | Qubits | Exact total energy | VQE total energy | Abs. error | Spectral gap | Error < gap |
|---|---|---|---|---|---|---|
| pyscf_molecular | 4 | -1.13730604 | -1.13730603 | 0.0 | 0.60093596 | True |
| pyscf_o2_corrosion_relevant | 8 | -147.6403771 | -147.63293154 | 0.00744556 | 0.0074455 | False |
| toy_ising_tfim | 4 | -4.27155841 | -4.23663685 | 0.03492156 | 0.03549043 | True |

O2's VQE error sits essentially **at** its spectral gap (a near-miss, reported as such, not rounded up to "converged").

Entanglement distribution (`qnet_physics_results.json`): depolarising link parameter λ → fidelity / CHSH S:

| λ | Fidelity | S_CHSH | Bell-violating |
|---|---|---|---|
| 0.00 | 1.0000 | 2.8284 | True |
| 0.05 | 0.9625 | 2.6870 | True |
| 0.10 | 0.9250 | 2.5456 | True |
| 0.20 | 0.8500 | 2.2627 | True |
| 0.25 | 0.8125 | 2.1213 | True |
| 0.29 | 0.7825 | 2.0082 | True |
| 0.30 | 0.7750 | 1.9799 | False |
| 0.40 | 0.7000 | 1.6971 | False |

Swapping chain at λ = 0.05 per link: **6 links** keep S > 2. Non-local CNOT is exact (F = 1) with a perfect pair and degrades with link noise.

Hardware-readiness manifest (`phase5_hardware/HARDWARE_EXECUTION_MANIFEST.json`; generic device **models**, assumed noise):

| Workload | Qubits | Transpiled depth (all-to-all / line / grid) | CZ gates (all / line / grid) | Valid-shot fraction ideal → noisy |
|---|---|---|---|---|
| vana_qaoa_p2 | 12 | 243 / 681 / 724 | 264 / 648 / 504 | 0.8926 → 0.7969 |
| ucics_qaoa_p2 | 9 | 86 / 147 / 86 | 48 / 99 / 48 | 0.7305 → 0.5664 |
| aiaic_qaoa_p2 | 12 | 312 / 826 / 789 | 264 / 705 / 501 | 0.8984 → 0.8535 |
| bharat_mala_qaoa_p2 | 10 | 201 / 489 / 600 | 180 / 432 / 348 | 0.582 → 0.416 |
| marine_qaoa_p2 | 9 | 186 / 500 / 450 | 120 / 384 / 216 | 0.1738 → 0.0879 |
| ghz4_distributed_shots | 4 | 16 / 16 / 16 | 3 / 3 / 3 | 1.0 → 0.9082 |
| bell2_link_check | 2 | 8 / 8 / 8 | 1 / 1 / 1 | 1.0 → 0.9531 |

**Hardware reading:** the 9–12-qubit QAOA circuits transpile to depths of roughly 80–830 and lose roughly 5–50 % (relative) of their valid shots under the
assumed noise; only the Bell/GHZ workloads are realistic first hardware runs. This is a model-based readiness estimate, not a
device measurement.

## 10. Failure Cases

Covered by tests (all pass): node down; message drop (single flaky link, and all-links with 3 vs 4 attempts — a documented
retry-rotation limitation); duplicate messages (never double-counted); corrupt / physically impossible results and wrong
circuit hash (quarantine + re-run); latency straggler (bounded virtual time); partial execution (status PARTIAL with widened
uncertainty, never COMPLETE); total outage (PARTIAL, zero shots, no crash); tampered log (hash-chain failure); invalid shots /
shards / nodes / workload; unmeasured circuit; unavailable IBM/IonQ adapters (report unavailable, refuse to execute);
excess qubits / excess depth (fit check); certification gate (simulator can never become HARDWARE_VERIFIED); assumed-noise
degradation; readout-error mitigation.

## 11. Hardware Evidence

**None.** No hardware access; no hardware execution; `evidence_packet/hardware_results/` is empty by design. Hardware-only
fields are `NOT_YET_EXECUTED_ON_HARDWARE`. Simulator and hardware evidence are separate certification states enforced by `certify()`.

## 12. What Changed

This snapshot adds: Phase 1 learning experiments and record; five domain templates (incl. Marine routing); network physics and
a fault-tolerant sharded workload; the hardware-readiness manifest, adapters and gates; the governance/execution test suite;
architecture and handover documents; and the Lab 6 chemistry adapter layer with its audit response.

**Not in this snapshot:** Algorithm Laboratory Labs 1–5 (QAOA marine maintenance, VQE toy model, quantum kernel, QCBM sampling,
hybrid LNS) and their earlier review packet. Their sources were lost to a sandbox reset before this repository was assembled;
see `algorithm_lab/MISSING_LABS_1-5.md`. Domain QAOA here covers the QAOA family; the other four families need re-adding.

## 13. Limitations

- Domain data are **synthetic**; domain applications are Ganesh's ownership — reconcile before treating these as the domain deliverable.
- No quantum-advantage claim: every instance is solved exactly by brute force; QAOA is a heuristic, single seed, p = 2.
- Slack-bit problems show no lift on the optimal decision vector (see §9).
- Bharat Mala's QUBO is a surrogate objective; Marine routing uses 3 waypoints only.
- Device models and noise parameters are assumed, not measured. Transpilation uses generic coupling maps.
- Network transport is simulated; retry policy rotates nodes (documented limitation); validation checks support/hash/shot-sum, not full distribution fidelity.
- Cloud adapters only declare availability; submission is intentionally unimplemented.
- Screenshots, API samples and deployment proof are **not** included (see evidence_packet READMEs).
- QCG / InsightFlow integration, real federation and real data are not done. Authentication (401) and unavailable-endpoint blockers
  must be documented when encountered; none were exercised here.

## 14. Provenance / Replay

SHA-256 over canonical JSON for workload IDs, invocation IDs and aggregates; fixed seeds (42); virtual clock (no wall-clock in hashes);
append-only hash-chained event log; `replay()` reconstructs the aggregate even from a shuffled log and rejects a tampered one.
Every network result carries `schema_version`, `trace_id`, `certification_state = SIMULATOR_VERIFIED`, `decision_authority = NONE`,
and an uncertainty block. Manifests carry an explicit authority ceiling (`ADVISORY_COMPUTE`) and a negative-authority list.

## 15. Proof

Logs in `evidence_packet/runtime_logs/`:

| Suite | Result |
|---|---|
| Phase 1 experiments | 13 / 13 passed |
| Phase 6 governance + execution + network | 71 passed |
| Lab 6 chemistry adapter tests | 8 passed |

Reproduce: `pytest phase6_testing algorithm_lab -v` from the repository root.
