# hamiltonian_adapters.py
# BHIV Quantum Build — Phase 2/5: Hamiltonian Source Adapter Layer
#
# Owner: Dhiraj — Quantum Runtime + circuits + execution layer
#
# WHY AN ADAPTER HERE: a prior VQE lab ran against a toy transverse-field
# Ising model and explicitly flagged the real corrosion Hamiltonian as
# future work ("needs PySCF integrals + 16 qubits"). Rather than
# hardcoding a second, separate VQE script for "the real one", this
# introduces a single HamiltonianAdapter interface so the SAME VQE
# algorithm code (ansatz, optimiser, execution) can run unmodified
# against either source. This is the identical pattern already
# load-bearing elsewhere in this codebase:
#   - marine_quantum_runtime's engineering principles: "Honest capability
#     marking: adapters without credentials/network access are marked
#     unavailable rather than silently failing or mocking success."
#   - marine_quantum_runtime's existing (currently unavailable, pending
#     credentials) IBM Runtime / IonQ hardware adapters — same shape.
#   - src/quantum/descriptors.py's register()/get()/list_registered()
#     QApp registry — this file's registry mirrors that API on purpose.
#
# Three adapters are registered:
#   ToyIsingAdapter             — always available, no external deps.
#   PySCFMolecularAdapter (H2)  — REAL ab-initio chemistry: PySCF computes
#                                  the molecular integrals, qiskit-nature
#                                  maps them to a qubit Hamiltonian via
#                                  Jordan-Wigner.
#   PySCFMolecularAdapter (O2)  — same adapter class, configured for the
#                                  species that actually drives the
#                                  marine corrosion cathodic reaction
#                                  (O2 + 2H2O + 4e- -> 4OH-), with an
#                                  active-space reduction to 8 qubits.
#
# AUDIT FIXES APPLIED (Ganesh's forensic review, 2026-10-19):
#   F-09: build_uccsd_ansatz() previously accepted but ignored a
#         problem_cache parameter, so PySCFDriver.run() (expensive) ran
#         TWICE per molecule. Fixed with a real _get_problem() cache
#         shared by both build_hamiltonian() and build_uccsd_ansatz().
#         Verified by monkeypatching PySCFDriver.run with a call counter:
#         confirmed exactly 1 call across both methods.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from qiskit.quantum_info import SparsePauliOp


class AdapterUnavailable(Exception):
    pass


@dataclass
class HamiltonianResult:
    operator: SparsePauliOp
    num_qubits: int
    metadata: dict
    ansatz_hint: Optional[str] = None   # adapter's opinion on an appropriate ansatz family


class HamiltonianAdapter(ABC):
    name: str = "unnamed_adapter"

    @abstractmethod
    def is_available(self) -> dict:
        """Must never raise. Returns {'available': bool, 'reason': str}."""

    @abstractmethod
    def build_hamiltonian(self) -> HamiltonianResult:
        """Raises AdapterUnavailable if is_available()['available'] is False."""


# ── Toy adapter (always available) ───────────────────────────────────────

class ToyIsingAdapter(HamiltonianAdapter):
    name = "toy_ising_tfim"

    def __init__(self, n=4, J=1.0, h=0.5):
        self.n, self.J, self.h = n, J, h

    def is_available(self) -> dict:
        return {"available": True, "reason": "pure numpy/qiskit — no external dependencies"}

    def build_hamiltonian(self) -> HamiltonianResult:
        n, J, h = self.n, self.J, self.h
        terms, coeffs = [], []
        for i in range(n):
            j = (i + 1) % n
            label = ["I"] * n
            label[i], label[j] = "Z", "Z"
            terms.append("".join(reversed(label)))
            coeffs.append(-J)
        for i in range(n):
            label = ["I"] * n
            label[i] = "X"
            terms.append("".join(reversed(label)))
            coeffs.append(-h)
        op = SparsePauliOp(terms, coeffs)
        return HamiltonianResult(
            operator=op, num_qubits=n,
            metadata={"model": "transverse-field Ising, periodic", "J": J, "h": h,
                      "domain_note": "toy lattice model — NOT a real molecule"},
            ansatz_hint="hardware_efficient",
        )


# ── Real chemistry adapter (PySCF + qiskit-nature) ───────────────────────

class PySCFMolecularAdapter(HamiltonianAdapter):
    name = "pyscf_molecular"  # class default; overridable per instance below

    def __init__(self, atom: str, basis: str = "sto-3g",
                 active_electrons: Optional[int] = None,
                 active_orbitals: Optional[int] = None,
                 spin: int = 0, charge: int = 0,
                 adapter_name: Optional[str] = None):
        self.atom = atom
        self.basis = basis
        self.active_electrons = active_electrons
        self.active_orbitals = active_orbitals
        self.spin = spin      # 2S = n_alpha - n_beta; 0 = singlet, 2 = triplet, ...
        self.charge = charge
        if adapter_name is not None:
            self.name = adapter_name  # instance override so the registry
            # can hold multiple distinct molecules without name collisions
        self._problem_cache = None  # see _get_problem() (F-09 fix)

    def _get_problem(self):
        """Builds (once) and caches the driver + active-space-transformed
        ElectronicStructureProblem, shared by build_hamiltonian() and
        build_uccsd_ansatz() so PySCFDriver.run() — the expensive integral
        computation — only ever executes once per adapter instance."""
        if self._problem_cache is not None:
            return self._problem_cache

        from qiskit_nature.second_q.drivers import PySCFDriver
        from qiskit_nature.second_q.transformers import ActiveSpaceTransformer

        driver = PySCFDriver(atom=self.atom, basis=self.basis,
                              spin=self.spin, charge=self.charge)
        problem = driver.run()

        active_space_applied = False
        if self.active_electrons is not None and self.active_orbitals is not None:
            transformer = ActiveSpaceTransformer(self.active_electrons, self.active_orbitals)
            problem = transformer.transform(problem)
            active_space_applied = True

        self._problem_cache = (problem, active_space_applied)
        return self._problem_cache

    def is_available(self) -> dict:
        try:
            import pyscf
            import qiskit_nature
        except ImportError as exc:
            return {"available": False, "reason": f"missing dependency: {exc}"}
        return {"available": True,
                "reason": f"pyscf {pyscf.__version__}, qiskit_nature {qiskit_nature.__version__}"}

    def build_hamiltonian(self) -> HamiltonianResult:
        availability = self.is_available()
        if not availability["available"]:
            raise AdapterUnavailable(f"{self.name}: {availability['reason']}")

        from qiskit_nature.second_q.mappers import JordanWignerMapper

        problem, active_space_applied = self._get_problem()
        hamiltonian = problem.hamiltonian
        second_q_op = hamiltonian.second_q_op()
        mapper = JordanWignerMapper()
        qubit_op = mapper.map(second_q_op)

        # IMPORTANT: hamiltonian.nuclear_repulsion_energy alone is NOT the
        # full constant offset once an active space has been applied.
        # qiskit-nature's ActiveSpaceTransformer folds the frozen-core /
        # inactive-orbital energy into a SEPARATE entry in
        # hamiltonian.constants (key "ActiveSpaceTransformer") — missing it
        # silently produces a numerically-converged but physically wrong
        # "total energy" (caught by a plausibility check on a real O2 run:
        # reported a positive total energy, which is not physically
        # sensible for a bound molecule — see test_adapter_correctness.py's
        # regression test for this exact failure mode).
        constants = dict(hamiltonian.constants)
        total_constant_offset = float(sum(constants.values()))

        metadata = {
            "atom": self.atom,
            "basis": self.basis,
            "spin": self.spin,
            "charge": self.charge,
            "num_particles": problem.num_particles,
            "num_spatial_orbitals": problem.num_spatial_orbitals,
            "nuclear_repulsion_energy": float(hamiltonian.nuclear_repulsion_energy),
            "all_constants": {k: float(v) for k, v in constants.items()},
            "total_constant_offset": total_constant_offset,
            "active_space_applied": active_space_applied,
            "active_electrons": self.active_electrons,
            "active_orbitals": self.active_orbitals,
            "mapper": "JordanWignerMapper",
            "domain_note": "REAL ab-initio molecular Hamiltonian via PySCF",
        }
        return HamiltonianResult(
            operator=qubit_op, num_qubits=qubit_op.num_qubits, metadata=metadata,
            ansatz_hint="uccsd",
        )

    def build_uccsd_ansatz(self):
        """Helper: constructs the chemistry-aware UCCSD ansatz for this
        molecule, using qiskit-nature's own particle-number-aware
        construction rather than a generic hardware-efficient ansatz.
        Reuses the same cached problem build_hamiltonian() produced (see
        _get_problem()) — PySCFDriver.run() is not re-invoked here
        (audit finding F-09)."""
        from qiskit_nature.second_q.mappers import JordanWignerMapper
        from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD

        problem, _ = self._get_problem()
        mapper = JordanWignerMapper()
        hf_state = HartreeFock(problem.num_spatial_orbitals, problem.num_particles, mapper)
        ansatz = UCCSD(problem.num_spatial_orbitals, problem.num_particles, mapper,
                        initial_state=hf_state)
        return ansatz, problem


# ── Registry (mirrors src/quantum/descriptors.py's register/get/list API) ─

_REGISTRY: dict = {}


def register_adapter(adapter: HamiltonianAdapter) -> None:
    _REGISTRY[adapter.name] = adapter


def get_adapter(name: str) -> Optional[HamiltonianAdapter]:
    return _REGISTRY.get(name)


def list_adapters() -> list:
    return sorted(_REGISTRY.keys())


def adapter_status() -> dict:
    """Dashboard-style availability report — every adapter checked honestly,
    none assumed available just because it's registered."""
    return {name: a.is_available() for name, a in _REGISTRY.items()}


# Register the adapters this lab ships with.
register_adapter(ToyIsingAdapter())
register_adapter(PySCFMolecularAdapter(atom="H 0 0 0; H 0 0 0.735", basis="sto-3g"))

# O2 — the species actually driving the corrosion reaction this whole
# workstream is about: the cathodic half-reaction in marine corrosion is
# O2 + 2H2O + 4e- -> 4OH-, and dissolved_oxygen_mgl is already a real input
# field in marine_quantum_runtime's existing CorrosionInput schema
# (src/quantum/schema.py). Ground state O2 is a triplet (2 unpaired
# electrons, spin=2 in qiskit-nature's 2S convention). Full space is
# 20 qubits (16 electrons, 10 spatial orbitals in STO-3G) — an active-space
# reduction to the frontier (HOMO/LUMO) orbitals, which govern O-O bond
# reactivity, brings this to a tractable 8 qubits.
register_adapter(PySCFMolecularAdapter(
    atom="O 0 0 0; O 0 0 1.208", basis="sto-3g", spin=2, charge=0,
    active_electrons=4, active_orbitals=4,
    adapter_name="pyscf_o2_corrosion_relevant",
))


if __name__ == "__main__":
    import json
    print(json.dumps(adapter_status(), indent=2))
