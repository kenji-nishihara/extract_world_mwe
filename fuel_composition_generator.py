#!/usr/bin/env python3
from __future__ import annotations

"""Generate random fuel compositions under constraints.

Sampling is based on a uniform Dirichlet distribution (alpha=1 for all nuclides)
with rejection sampling for constraints.
"""

import argparse
import json
import random
from typing import Dict, List

NUCLIDES: List[str] = [
    "U235",
    "U238",
    "Pu238",
    "Pu239",
    "Pu240",
    "Pu241",
    "Pu242",
    "Am241",
]

BOUNDS = {
    "U235": (0.00, 0.20),
    "U238": (0.56, 1.00),
    "Pu238": (0.00, 0.03),
    "Pu239": (0.00, 0.24),
    "Pu240": (0.00, 0.24),
    "Pu241": (0.00, 0.06),
    "Pu242": (0.00, 0.06),
    "Am241": (0.00, 0.06),
}

PU_TOTAL_MIN = 0.00
PU_TOTAL_MAX = 0.30
FISSILE_MIN = 0.00
FISSILE_MAX = 0.10


def sample_dirichlet_uniform(rng: random.Random) -> Dict[str, float]:
    gamma = [rng.gammavariate(1.0, 1.0) for _ in NUCLIDES]
    total = sum(gamma)
    return {k: v / total for k, v in zip(NUCLIDES, gamma)}


def is_valid(composition: Dict[str, float], tol: float = 1e-12) -> bool:
    if abs(sum(composition.values()) - 1.0) > tol:
        return False

    for nuclide, (mn, mx) in BOUNDS.items():
        value = composition[nuclide]
        if value < mn - tol or value > mx + tol:
            return False

    pu_total = sum(composition[n] for n in ("Pu238", "Pu239", "Pu240", "Pu241", "Pu242"))
    fissile = composition["U235"] + composition["Pu239"] + composition["Pu241"]

    if pu_total < PU_TOTAL_MIN - tol or pu_total > PU_TOTAL_MAX + tol:
        return False
    if fissile < FISSILE_MIN - tol or fissile > FISSILE_MAX + tol:
        return False
    return True


def generate_one(rng: random.Random, max_attempts: int = 1_000_000) -> Dict[str, float]:
    for _ in range(max_attempts):
        candidate = sample_dirichlet_uniform(rng)
        if is_valid(candidate):
            return candidate
    raise RuntimeError(f"No valid composition found after {max_attempts} attempts")


def format_output(composition: Dict[str, float]) -> Dict[str, object]:
    pu_total = sum(composition[n] for n in ("Pu238", "Pu239", "Pu240", "Pu241", "Pu242"))
    fissile = composition["U235"] + composition["Pu239"] + composition["Pu241"]
    return {
        "nuclides": composition,
        "derived": {
            "pu_total": pu_total,
            "fissile": fissile,
            "sum": sum(composition.values()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate constrained random fuel composition(s) as JSON")
    parser.add_argument("-n", "--count", type=int, default=1, help="Number of compositions to generate")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    parser.add_argument("--max-attempts", type=int, default=1_000_000, help="Max rejection attempts per sample")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    results = [format_output(generate_one(rng, args.max_attempts)) for _ in range(args.count)]

    payload: object
    if args.count == 1:
        payload = results[0]
    else:
        payload = {"items": results}

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
