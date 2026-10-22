# Deadlock Simulator

An animated, dark-themed desktop app that shows **how a deadlock happens**, using a
Resource Allocation Graph. Built with plain Python and Tkinter, so there is
**nothing to install** and it works offline.

## Features

- Processes drawn as circles, resources as squares
- Animated arrows: **green = allocated (R → P)**, **orange dashed = request (P → R)**
- Deadlock cycle turns **red and pulses**; the processes involved are highlighted
- Start, Pause, Next Step, Reset, and a speed slider
- Plain-English explanation for every step, plus a step log
- Live checklist of the four conditions required for deadlock
- 5 scenarios, and a **Load Deadlock Example** button

| Scenario | Result |
|---|---|
| Classic Deadlock | Deadlock |
| Waiting, No Deadlock | Safe (P1 waits, then P2 releases R2) |
| Fix: Resource Ordering | Safe (both ask for R1 first, then R2) |
| Three-Process Circle | Deadlock |
| Deadlock + Bystander | Deadlock (P3 is blocked but not part of the cycle) |

## Requirements

- Python 3.8 or newer (https://www.python.org/downloads/)
- Tkinter (included with the Windows installer from python.org)

There are no `pip install` steps. `requirements.txt` is only a note saying so.

## How to run (VS Code on Windows)

1. Extract the ZIP. Install Python. In the installer, tick **"Add python.exe to PATH"**.
2. Open this folder in VS Code (**File → Open Folder…** → `DeadlockSimulator`).
3. Install the **Python** extension if VS Code asks.
4. Open a terminal (**Terminal → New Terminal**) and run:

   ```
   python main.py
   ```

   (If `python` is not found, try `py main.py`.) You can also open `main.py` and press the ▶ button.

### Quick check that Tkinter works

```
python -m tkinter
```

A small test window should appear. On Linux, if it fails: `sudo apt install python3-tk`.

## How to use

1. Pick a scenario on the left (or click **Load Deadlock Example**).
2. Click **Next Step** to go one step at a time, or **Start** to auto-play.
3. Read the **What is happening** panel and watch the arrows.
4. **Pause** stops auto-play, **Reset** returns to the beginning.
   Pressing **Start** after the run has finished restarts it.

Keyboard: `Space` start/pause, `→` next step, `R` reset.

## Project files

| File | What it does |
|---|---|
| `main.py` | Starts the program |
| `gui.py` | Window, buttons, animation and drawing |
| `simulator.py` | The simulation logic (no graphics) |
| `scenarios.py` | The predefined examples |
| `theme.py` | Colors and fonts |

## How the logic works

- `holder[R]` = which process currently holds resource `R`
- `waiting[P]` = which resource process `P` is waiting for
- A request for a **free** resource is granted. A request for a **held** resource makes the process wait.
- When a process **finishes**, it releases its resources, and each is handed to the first process waiting for it.
- After every step the simulator follows the chain *"P waits for R, R is held by Q, Q waits for …"*.
  If the chain returns to a process already visited, that is a cycle, so a **deadlock** exists.
  Every resource here has one instance, so a cycle always means deadlock.

## Add your own scenario

Open `scenarios.py`, copy one `Scenario(...)` block, and change it:

```python
Scenario(
    name="My Example", tag="DEADLOCK", description="What this shows.",
    processes=["P1", "P2"], resources=["R1", "R2"],
    positions=SQUARE,                       # or your own {"P1": (x, y), ...} with x, y from 0 to 1
    steps=[("request", "P1", "R1"), ("request", "P2", "R2"),
           ("request", "P1", "R2"), ("request", "P2", "R1")],
)
```

Add it to the `SCENARIOS` list and it appears in the sidebar automatically.
Step types: `("request", "P1", "R1")` and `("finish", "P1", None)`.

## Ideas to extend it

- Resources with multiple instances
- A "Back" button (replay the first N steps)
- Deadlock **recovery** (terminate a process in the cycle)
- Let the user click to add processes and resources
