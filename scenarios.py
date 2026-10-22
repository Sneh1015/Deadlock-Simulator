"""
scenarios.py - the predefined examples.

A scenario is just data:
  processes : names of the processes
  resources : names of the resources (each has ONE instance)
  positions : where to draw each node (x, y between 0.0 and 1.0)
  steps     : the script, run one line at a time. Each step is a tuple:
                ("request", "P1", "R1")  -> P1 asks for R1
                ("finish",  "P1", None)  -> P1 finishes and releases everything it holds

To add your own scenario, copy one below and append it to SCENARIOS.
"""
import math


class Scenario:
    def __init__(self, name, tag, description, processes, resources, positions, steps):
        self.name = name
        self.tag = tag                  # "DEADLOCK" or "SAFE" (shown on the card)
        self.description = description
        self.processes = processes
        self.resources = resources
        self.positions = positions
        self.steps = steps


# Four nodes placed on the corners of a rectangle: P1 - R1 / R2 - P2
SQUARE = {
    "P1": (0.15, 0.10), "R1": (0.85, 0.10),
    "R2": (0.15, 0.90), "P2": (0.85, 0.90),
}


def ring_positions(order):
    """Place nodes evenly on a circle, starting at the top, going clockwise."""
    pos = {}
    for i, name in enumerate(order):
        angle = -math.pi / 2 + i * 2 * math.pi / len(order)
        pos[name] = (0.5 + 0.5 * math.cos(angle), 0.5 + 0.5 * math.sin(angle))
    return pos


SCENARIOS = [
    # ------------------------------------------------------------------
    Scenario(
        name="Classic Deadlock",
        tag="DEADLOCK",
        description=(
            "Two processes, two resources. Each process grabs one resource and "
            "then asks for the one the other process already holds."
        ),
        processes=["P1", "P2"],
        resources=["R1", "R2"],
        positions=SQUARE,
        steps=[
            ("request", "P1", "R1"),
            ("request", "P2", "R2"),
            ("request", "P1", "R2"),
            ("request", "P2", "R1"),
        ],
    ),
    # ------------------------------------------------------------------
    Scenario(
        name="Waiting, No Deadlock",
        tag="SAFE",
        description=(
            "P1 has to wait for R2, but P2 is not waiting for anything, so it "
            "finishes and releases R2. Waiting is not the same as deadlock!"
        ),
        processes=["P1", "P2"],
        resources=["R1", "R2"],
        positions=SQUARE,
        steps=[
            ("request", "P1", "R1"),
            ("request", "P2", "R2"),
            ("request", "P1", "R2"),
            ("finish", "P2", None),
            ("finish", "P1", None),
        ],
    ),
    # ------------------------------------------------------------------
    Scenario(
        name="Fix: Resource Ordering",
        tag="SAFE",
        description=(
            "Same two processes and resources as the classic example, but both "
            "ask for R1 first and R2 second. A fixed order prevents circular wait."
        ),
        processes=["P1", "P2"],
        resources=["R1", "R2"],
        positions=SQUARE,
        steps=[
            ("request", "P1", "R1"),
            ("request", "P2", "R1"),
            ("request", "P1", "R2"),
            ("finish", "P1", None),
            ("request", "P2", "R2"),
            ("finish", "P2", None),
        ],
    ),
    # ------------------------------------------------------------------
    Scenario(
        name="Three-Process Circle",
        tag="DEADLOCK",
        description=(
            "P1 holds R1 and wants R2, P2 holds R2 and wants R3, P3 holds R3 "
            "and wants R1. A bigger circular wait."
        ),
        processes=["P1", "P2", "P3"],
        resources=["R1", "R2", "R3"],
        positions=ring_positions(["P1", "R2", "P2", "R3", "P3", "R1"]),
        steps=[
            ("request", "P1", "R1"),
            ("request", "P2", "R2"),
            ("request", "P3", "R3"),
            ("request", "P1", "R2"),
            ("request", "P2", "R3"),
            ("request", "P3", "R1"),
        ],
    ),
    # ------------------------------------------------------------------
    Scenario(
        name="Deadlock + Bystander",
        tag="DEADLOCK",
        description=(
            "P1 and P2 deadlock. P3 is also stuck waiting for R1, but it is not "
            "part of the cycle. Only the cycle members are deadlocked."
        ),
        processes=["P1", "P2", "P3"],
        resources=["R1", "R2"],
        positions={
            "P1": (0.15, 0.10), "R1": (0.85, 0.10),
            "R2": (0.15, 0.90), "P2": (0.85, 0.90),
            "P3": (0.50, 0.50),
        },
        steps=[
            ("request", "P1", "R1"),
            ("request", "P2", "R2"),
            ("request", "P3", "R1"),
            ("request", "P1", "R2"),
            ("request", "P2", "R1"),
        ],
    ),
]
