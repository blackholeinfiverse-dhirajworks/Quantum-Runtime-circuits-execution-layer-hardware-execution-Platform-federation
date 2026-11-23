# AUDIT RESPONSE — Ganesh's Forensic Review (2026-10-19)

**Scope:** this document responds to the forensic audit of Lab 6 (the Hamiltonian
Source Adapter Layer, `hamiltonian_adapters.py` / `vqe_adapter_execution.py` /
`test_adapter_correctness.py`), assessed for integration compatibility with
Ganesh's QAL (Quantum Application Layer) codebase. It's meant to merge into
Addendum E of the main `REVIEW_PACKET.md` (delivered earlier) — attach it there
or treat it as a standalone follow-up, whichever's more convenient on your end.

**Headline:** the audit's science assessment was accurate — H2/O2 chemistry
correct, determinism holds, the O2 bug-and-fix was independently verified as
genuine. It also caught real code issues. Every finding owned solely by this
role is fixed below, **verified by actually re-running the affected code**,
not just edited and asserted to work. Two findings need the real QAL source
to fix correctly rather than guess at; they're flagged, not silently dropped.

---

## Finding-by-finding

| ID | Finding | Status | Evidence |
|---|---|---|---|
| **F-03** | Test cache filename (`vqe_adapter_output.json`) had silently drifted from the shipped evidence file (`vqe_adapter_run_result.json`) — a real bug, caught correctly | **FIXED** | `vqe_adapter_execution.py` now owns one canonical `RESULT_FILE` constant and writes it itself (`__main__` saves to disk, not a manual shell redirect); `test_adapter_correctness.py` imports that same constant instead of hardcoding a second copy. Single source of truth — this exact drift class can't recur. |
| **F-06** | Tests not pytest-discoverable (no `assert`, informational-only) | **FIXED** | Every test now ends in a real `assert`. Verified by actually installing pytest and running `pytest test_adapter_correctness.py -v`: **8 passed in 1.26s**, not just claimed to be compatible. |
| **F-07** | Fragile `isinstance(adapter, type(get_adapter("pyscf_molecular")))` ansatz dispatch — breaks for any adapter subclass or differently-named instance | **FIXED** | Replaced with `ansatz_hint == "uccsd" and hasattr(adapter, "build_uccsd_ansatz")` — dispatches on declared capability, never on a concrete class or registry name. |
| **F-09** | `build_uccsd_ansatz(problem_cache=None)` accepted but never used its cache parameter — `PySCFDriver.run()` (expensive) ran twice per molecule | **FIXED** | Replaced with a real `_get_problem()` cache shared by both `build_hamiltonian()` and `build_uccsd_ansatz()`. Verified by monkeypatching `PySCFDriver.run` with a call counter: confirmed exactly **1 call** across both methods, not 2. |
| **F-12** | Skipped tests `return True`, inflating the pass count | **FIXED — and a second real bug was found while fixing it** | Skips now tracked separately (`N passed, M failed, K skipped`). While implementing this, a first-draft `except Exception` handler silently failed to catch `pytest.skip()`'s exception — because `pytest.skip()` raises `Skipped`, which subclasses `BaseException` **directly**, not `Exception` (confirmed by direct test: `except Exception` genuinely does not catch it; the whole test run crashed uncaught). Fixed with `except pytest.skip.Exception` specifically. Verified by forcing both PySCF adapters unavailable and re-running: correctly reported `6 passed, 0 failed, 2 skipped` — not inflated to 8. |
| **F-08** | O2's VQE error (0.0082 Hartree) exceeded the spectral gap (0.0074) | **IMPROVED, reported honestly as still inconclusive** | Switched the UCCSD path to start from the Hartree-Fock-reference zero-parameter point (standard chemistry practice) instead of a random start — a legitimate optimizer choice, not post-hoc tuning to force a number. Result: error now **0.0074456 vs. gap 0.0074455** — reproduced identically across two different trust-region settings (not noise, a stable local optimum). This is now right at the boundary rather than clearly outside it. Reported as exactly that — `within_spectral_gap: false`, by a margin of ~10⁻⁷ Hartree — rather than rounded into a false "fixed" claim. |
| **F-05** | No provenance metadata matching QAL's documented `ProvenanceMetadata` shape | **DEFERRED** | Needs the actual QAL source (field names, types) to avoid guessing an incompatible shape. The audit documents plausible field names, but building against documented-but-unverified fields risks shipping a wrong contract that *looks* integrated but isn't. **Ask: share `qal/core/models.py` (or equivalent)** and this gets built properly, not guessed. |
| **F-01** | Return type mismatch: raw dict vs. `QuantumExecutionResult` | **DEFERRED — same reason as F-05** | Joint ownership per the audit; needs the real Pydantic model. |
| **F-02** | `HamiltonianAdapter` ABC vs. `BaseDomainAdapter`/`QuantumAlgorithm` — architectural decision (wrap vs. refactor vs. adapter-of-adapters) | **DEFERRED — architecture decision, not a code fix** | A real three-way design choice the audit itself lays out; making it unilaterally without Ganesh's input risks locking in the wrong one. Flagging back for a short sync rather than guessing. |
| F-04, F-10, F-11 | Dict vs. frozen dataclass equality notes; module-level adapter registration side effects; `HamiltonianResult` dataclass vs. Pydantic | **Acknowledged, not changed** | All real but low-severity (P2/P3), and either (a) tied to the same F-01/F-02 architecture decision, or (b) a working-as-intended trade-off (eager registration keeps the registry simple and is itself exercised by the `_DeliberatelyBrokenAdapter` test) not worth touching without a concrete reason. |

**Merge readiness:** every P1/P2 item fully inside this role's ownership is
fixed and re-verified. F-01/F-02/F-05 need the actual QAL source before they
can be fixed correctly rather than guessed at — that's the one open ask.
F-08 is now a much tighter, honestly-reported near-miss rather than a clear
failure.

---

## Updated Lab 6 figures (Addendum E, §8–9 of the main packet)

The O2 convergence improvement (F-08) changed the reported numbers slightly.
Current, re-verified values:

```json
"pyscf_o2_corrosion_relevant": {
  "status": "SUCCESS",
  "num_qubits": 8,
  "ansatz": "UCCSD (chemistry-aware, qiskit-nature), 15 parameters",
  "exact_baseline": { "total_ground_energy": -147.6403771, "spectral_gap": 0.0074455 },
  "vqe_result":     { "total_energy": -147.63293154 },
  "comparison": {
    "absolute_error_hartree_or_units": 0.00744556,
    "relative_error_pct": 0.00504,
    "within_spectral_gap": false
  }
}
```

H2 and toy_ising_tfim results are unchanged from the original Addendum E
(H2 still essentially exact; toy model's hardware-efficient ansatz untouched
by the F-08 fix, which only applies to the UCCSD/Hartree-Fock-start path).

## Final test run (all 8, both runners)

```
$ python test_adapter_correctness.py
[PASS]  registry contains all shipped adapters
[PASS]  toy_ising_tfim.is_available() == True
[PASS]  pyscf_molecular.is_available() returns well-formed status without raising
[PASS]  deliberately broken adapter correctly marked unavailable, not crashed
[PASS]  toy_ising_tfim Hamiltonian matrix is Hermitian
[PASS]  H2 exact diagonalisation = -1.13730604 Hartree, VQE/UCCSD error = 1.00e-08
[PASS]  O2 active-space total energy -147.6403771 Hartree is physically plausible
[PASS]  all adapters returned a well-formed status via the shared run_adapter() path

[PASS]  8 passed, 0 failed, 0 skipped  (8 total)

$ python -m pytest test_adapter_correctness.py -v
======================== 8 passed in 1.26s ========================
```

## Forced-skip verification (proving F-12 actually works, not just the happy path)

```
[both PySCF adapters' is_available() forced to False]
[SKIP]  pyscf_molecular unavailable in this environment — skipped honestly, not faked as a pass
[SKIP]  pyscf_o2_corrosion_relevant unavailable in this environment — skipped honestly, not faked as a pass

[PASS]  6 passed, 0 failed, 2 skipped  (8 total)
```
