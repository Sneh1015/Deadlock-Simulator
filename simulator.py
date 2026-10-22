"""
simulator.py - the simulation LOGIC (no graphics in this file).

Key ideas:
  holder[R]  = the process that currently holds resource R (or None)
  waiting[P] = the resource that process P is waiting for (or None)

Because every resource has a single instance, a deadlock is exactly a
cycle in the "wait-for" relationship:
    P1 waits for a resource held by P2, P2 waits for a resource held by P1.
"""


class StepResult:
    """What happened in one step. The GUI uses it to show the explanation."""

    def __init__(self, kind, title, text, process=None, resource=None):
        self.kind = kind          # grant / wait / release / finish / skip / deadlock / complete
        self.title = title
        self.text = text
        self.process = process    # process involved (for highlighting)
        self.resource = resource  # resource involved (for highlighting)


class DeadlockSimulator:
    def __init__(self, scenario):
        self.scenario = scenario
        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        sc = self.scenario
        self.holder = {r: None for r in sc.resources}
        self.waiting = {p: None for p in sc.processes}
        self.queue = {r: [] for r in sc.resources}   # who is waiting for each resource
        self.finished = set()
        self.started = set()
        self.step_index = 0
        self.done = False
        self.deadlocked = []          # processes in the cycle
        self.cycle_edges = set()      # edges to draw in red
        self.cycle_resources = set()
        self.cycle_text = ""

    @property
    def total_steps(self):
        return len(self.scenario.steps)

    # ------------------------------------------------------------------
    # Small helpers used by the GUI
    # ------------------------------------------------------------------
    def held_by(self, process):
        return [r for r in self.scenario.resources if self.holder[r] == process]

    def status_of(self, process):
        """Return one of: finished, deadlocked, waiting, running, ready."""
        if process in self.finished:
            return "finished"
        if process in self.deadlocked:
            return "deadlocked"
        if self.waiting[process]:
            return "waiting"
        if process in self.started:
            return "running"
        return "ready"

    def coffman(self):
        """The four necessary conditions for deadlock: (name, description, true_now)."""
        any_held = any(p is not None for p in self.holder.values())
        hold_and_wait = any(self.waiting[p] and self.held_by(p) for p in self.scenario.processes)
        return [
            ("Mutual exclusion", "A resource can be used by one process at a time", any_held),
            ("Hold and wait", "A process holds one resource while waiting for another", hold_and_wait),
            ("No preemption", "Resources are only released voluntarily", any_held),
            ("Circular wait", "A cycle of processes each waiting for the next", bool(self.deadlocked)),
        ]

    # ------------------------------------------------------------------
    # Run ONE step of the script
    # ------------------------------------------------------------------
    def next_step(self):
        if self.done:
            return None

        action, p, r = self.scenario.steps[self.step_index]
        self.step_index += 1

        if p in self.finished:
            result = StepResult("skip", f"{p} already finished",
                                f"{p} has already finished, so this step is skipped.", p)
        elif self.waiting[p]:
            result = StepResult("skip", f"{p} is blocked",
                                f"{p} is waiting for {self.waiting[p]}, so it cannot do anything else.", p)
        elif action == "request":
            self.started.add(p)
            result = self._request(p, r)
        else:  # "finish"
            self.started.add(p)
            result = self._finish(p)

        # After every step, check for a deadlock.
        cycle = self._find_cycle()
        if cycle:
            self._record_deadlock(cycle)
            result.kind = "deadlock"
            result.title = f"{result.title} - DEADLOCK DETECTED"
            result.text += "\n\n" + self._deadlock_explanation(cycle)
            self.done = True
        elif self.step_index >= self.total_steps:
            self.done = True
            result.text += ("\n\nThe script is finished and there is no circular wait, "
                            "so there is no deadlock.")
        return result

    # ------------------------------------------------------------------
    def _request(self, p, r):
        owner = self.holder[r]
        if owner is None:
            self.holder[r] = p
            return StepResult("grant", f"{p} requests {r}",
                              f"{r} is free, so it is allocated to {p}.\n"
                              f"An allocation edge {r} -> {p} appears.", p, r)
        if owner == p:
            return StepResult("skip", f"{p} requests {r}",
                              f"{p} already holds {r}, nothing changes.", p, r)
        self.waiting[p] = r
        self.queue[r].append(p)
        return StepResult("wait", f"{p} requests {r}",
                          f"{r} is already held by {owner}, so {p} must wait.\n"
                          f"A request edge {p} -> {r} appears. {p} is blocked until "
                          f"{owner} releases {r}.", p, r)

    def _finish(self, p):
        released = self.held_by(p)
        self.finished.add(p)
        lines = [f"{p} has everything it needs, finishes, and releases "
                 f"{', '.join(released) if released else 'nothing (it held no resources)'}."]
        for r in released:
            self.holder[r] = None
            if self.queue[r]:                       # hand it to the first waiting process
                nxt = self.queue[r].pop(0)
                self.holder[r] = nxt
                self.waiting[nxt] = None
                lines.append(f"{r} is given to {nxt}, which was waiting for it. {nxt} is unblocked.")
        return StepResult("finish", f"{p} finishes", "\n".join(lines), p,
                          released[0] if released else None)

    # ------------------------------------------------------------------
    # Deadlock detection: follow the chain "P waits for R, R is held by Q, ..."
    # Each process waits for at most one resource, so a chain either ends
    # or comes back to a process it has already visited (a cycle).
    # ------------------------------------------------------------------
    def _find_cycle(self):
        for start in self.scenario.processes:
            path = []
            current = start
            while current is not None and self.waiting[current] and current not in path:
                path.append(current)
                current = self.holder[self.waiting[current]]
            if current is not None and current in path:
                return path[path.index(current):]
        return None

    def _record_deadlock(self, cycle):
        self.deadlocked = list(cycle)
        parts = []
        for p in cycle:
            r = self.waiting[p]
            self.cycle_edges.add(("req", p, r))
            self.cycle_edges.add(("alloc", self.holder[r], r))
            self.cycle_resources.add(r)
            parts += [p, r]
        self.cycle_text = " -> ".join(parts + [cycle[0]])

    def _deadlock_explanation(self, cycle):
        lines = ["Deadlock! A circular wait exists:"]
        for p in cycle:
            r = self.waiting[p]
            lines.append(f"  {p} waits for {r}, held by {self.holder[r]}")
        lines.append(f"Cycle: {self.cycle_text}")
        lines.append("None of them can ever continue, because each is waiting for a "
                     "resource that only another stuck process can release.")
        others = [q for q in self.scenario.processes
                  if self.waiting[q] and q not in cycle]
        for q in others:
            lines.append(f"{q} is also blocked (waiting for {self.waiting[q]}) but is not "
                         f"in the cycle.")
        return "\n".join(lines)
