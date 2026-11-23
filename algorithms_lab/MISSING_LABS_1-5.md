# Algorithm Laboratory — Labs 1–5 are NOT in this snapshot

Their source files were lost to a sandbox reset before this repository was assembled. They were delivered
earlier in the working session; restore them here from that download. Expected files:

| Lab | Family | Files |
|---|---|---|
| 1 | QAOA (marine hull-maintenance allocation) | `problem_marine_maintenance.py`, `qaoa_execution.py`, `test_failure_cases.py` |
| 2 | VQE (toy transverse-field Ising model) | `vqe_execution.py`, `test_vqe_correctness.py` |
| 3 | Quantum kernel / QML | `qkernel_execution.py`, `test_qkernel_correctness.py` |
| 4 | Quantum sampling (QCBM) | `qsampling_execution.py`, `test_qsampling_correctness.py` |
| 5 | Hybrid classical + quantum (large-neighbourhood search) | `hybrid_lns_execution.py`, `test_hybrid_lns_correctness.py` |
| – | Earlier combined review packet | `REVIEW_PACKET.md` (the version covering Labs 1–6) |

Headline results as reported in that earlier packet (**not re-verified in this snapshot**):
Lab 1 QAOA matched the brute-force optimum; Lab 2 VQE reached 0.62 % error vs exact; Lab 3 the quantum kernel scored 0.50
vs 1.00 for classical RBF (a reported negative result); Lab 4 QCBM KL ≈ 0.010 vs 0.927 for mean-field; Lab 5 hybrid LNS tied plain
QAOA at 2048 shots but reached the optimum at 64 shots where plain QAOA did not.

Until restored, the Algorithm Laboratory deliverable is **partial**: QAOA is covered by `phase3_domains/`, and VQE by Lab 6 here;
kernel, sampling and hybrid families are absent from this repository.
