# Quantum Learning Record (Phase 1)

**Rule from the master task:** every major concept must connect to an executable circuit or experiment.
Each row below links a concept to code that was run and **asserted against an analytic result**
(`phase1_learning/learning_experiments.py` → `learning_results.json`, 13/13 pass).

> **Honest scope:** this is executable evidence that the concepts were exercised, not proof that they
> are understood. The exercises at the end are for you to do — predict first, then run.

## Concept → experiment map

| Concept (from the task) | Experiment | What is verified |
|---|---|---|
| Qubits, superposition, probability amplitudes | **E01** | H\|0⟩ amplitudes = 1/√2; probabilities 0.5/0.5 |
| Bloch sphere / unitary state evolution | **E02** | ⟨X⟩,⟨Y⟩,⟨Z⟩ = (sin θ cos φ, sin θ sin φ, cos θ); norm 1 |
| Measurement, shots | **E03** | sampling error scales as N^−1/2 (fitted log-log slope ≈ −0.5) |
| Interference | **E04** | H·H = I; H·Z·H = X; a measurement between the H's destroys interference (0.5) |
| Entanglement | **E05** | Bell state: CHSH S = 2√2 > 2 (classical bound), entanglement entropy = 1 bit; product state ≤ 2 |
| Quantum gates, circuits | **E06** | U†U = I; norm preserved |
| Quantum channels, density matrices, decoherence | **E07** | T1 decay and T2 dephasing match exp(−t/T) to 1e−12; depolarising lowers purity |
| Noise, NISQ depth limits | **E08** | Bell fidelity vs noisy layers = (1+3c^{2L})/4, c measured from the channel (= 1−p) |
| Transpilation | **E09** | basis-gate rewrite preserves the unitary; depth/gate counts change. Device-model tables: `phase5_hardware/HARDWARE_EXECUTION_MANIFEST.json` |
| Error mitigation | **E10** | readout calibration-matrix inversion moves ⟨ZZ⟩ toward the ideal 1 |
| Quantum communication | **E11, E12** | teleportation fidelity 1; BB84 QBER ≈ 0 without / ≈ 25% with an intercept-resend eavesdropper |
| Quantum–classical hybrid computation | **E13**, domain QAOA runs | COBYLA drives ⟨Z⟩ to −1; QAOA parameter loops in `phase3_domains/` |
| Quantum networking fundamentals | `phase4_network/qnet_physics.py` | Werner-link fidelity/CHSH vs link noise (Bell violation ends between λ=0.29 and 0.30); swapping chain: S>2 for up to 6 links at λ=0.05 per link |
| Distributed quantum computation | `qnet_physics.py` (non-local CNOT), `qnet_workload.py` | exact non-local CNOT with a shared pair (F=1), degrading with link noise; sharded execution with fault handling |

## One lesson learned the hard way
E08 first **failed** because my analytic formula assumed Qiskit's `depolarizing_error(p)` shrinks Pauli
correlators by (1−4p/3). The fit showed the factor is 1−p. The fix was to *measure* the contraction from
the channel instead of assuming it. The simulator was right; my formula was wrong — the check existed to catch that.

## Predict-then-run exercises (do these yourself)
1. Before running E04: what is P(0) if you put an **X** between the two Hadamards? Then run it.
2. Change E03's p from 0.5 to 0.1. Predict the new error at N=1600 (hint: σ = √(p(1−p)/N)); check the slope.
3. In E05, rotate Bob's angles by 10°. Predict whether S still exceeds 2; compute S(θ) = 2√2·cos(Δ) shape.
4. In E08, double p. How many layers until fidelity < 0.8? Derive it from the formula, then confirm.
5. In `qnet_physics.py`, find the per-link λ at which a 3-link chain stops violating CHSH (v³ = 1/√2).
6. Explain in two sentences why E10's mitigated ⟨ZZ⟩ is not exactly 1.

## Not covered by experiments (be explicit)
Reading assignments from the Learning Kit (IBM Quantum Learning, Qiskit docs, repeaters/architectures,
QKD theory beyond BB84) are not evidenced here; log them yourself if the reviewer expects them.
