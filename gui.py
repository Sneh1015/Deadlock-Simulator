"""
gui.py - the window, the animated drawing, and the buttons.

How the animation works (simple version):
  * A "frame loop" (_animate) runs about 60 times per second.
  * Each frame it moves every arrow a little closer to fully drawn (or fully
    erased), then clears the canvas and redraws everything.
  * The simulation (simulator.py) only decides WHAT happens. After each step
    we call _sync_edges(), which tells the drawing which arrows should exist.
"""
import math
import time
import tkinter as tk

import theme as T
from scenarios import SCENARIOS
from simulator import DeadlockSimulator

PROCESS_RADIUS = 36     # circle size
RESOURCE_HALF = 34      # half the side of the resource square
EDGE_SPEED = 1.0 / 0.7  # arrows take ~0.7 s to grow or shrink


# ======================================================================
# A small custom button (looks the same on every operating system)
# ======================================================================
class FlatButton(tk.Label):
    def __init__(self, parent, text, command, bg, hover, fg="#ffffff",
                 size=11, padx=18, pady=9):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=T.font(size, "bold"),
                         padx=padx, pady=pady, cursor="hand2")
        self.command = command
        self.normal_bg, self.hover_bg, self.normal_fg = bg, hover, fg
        self.enabled = True
        self.bind("<Enter>", lambda e: self.enabled and self.config(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.enabled and self.config(bg=self.normal_bg))
        self.bind("<Button-1>", self._clicked)

    def _clicked(self, event):
        if self.enabled:
            self.command()

    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.config(bg=self.normal_bg, fg=self.normal_fg, cursor="hand2")
        else:
            self.config(bg=T.DISABLED_BG, fg=T.DISABLED_FG, cursor="arrow")


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rectangle with rounded corners."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


# ======================================================================
# The application
# ======================================================================
class DeadlockApp:
    def __init__(self, root):
        self.root = root
        root.title("Deadlock Simulator")
        root.geometry("1320x760")
        root.minsize(1180, 680)
        root.configure(bg=T.BG)

        self.sim = None
        self.scenario_index = 0
        self.edges = []              # arrows currently on screen (see _sync_edges)
        self.running = False         # True while Start (auto-play) is active
        self.after_id = None         # id of the pending auto-play timer
        self.actor = (None, None)    # (process, resource) that just acted -> yellow ring
        self.actor_time = 0.0
        self.t0 = time.time()
        self.t = 0.0
        self.last_frame = time.time()

        self._build_sidebar()
        self._build_center()
        self._build_right_panel()

        # Keyboard shortcuts
        root.bind("<space>", lambda e: self.toggle_run())
        root.bind("<Right>", lambda e: self.next_step())
        root.bind("<r>", lambda e: self.reset())

        self.load_scenario(0)
        self._animate()

    # ==================================================================
    # Building the interface
    # ==================================================================
    def _build_sidebar(self):
        side = tk.Frame(self.root, bg=T.PANEL, width=240)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="DEADLOCK", bg=T.PANEL, fg=T.TEXT,
                 font=T.font(20, "bold")).pack(anchor="w", padx=20, pady=(22, 0))
        tk.Label(side, text="SIMULATOR", bg=T.PANEL, fg=T.BLUE,
                 font=T.font(12, "bold")).pack(anchor="w", padx=20)

        tk.Label(side, text="SCENARIOS", bg=T.PANEL, fg=T.MUTED,
                 font=T.font(9, "bold")).pack(anchor="w", padx=20, pady=(24, 6))

        self.cards = []
        for i, sc in enumerate(SCENARIOS):
            self.cards.append(self._make_card(side, i, sc))

        self.btn_example = FlatButton(side, "Load Deadlock Example",
                                      lambda: self.load_scenario(0),
                                      bg=T.RED, hover="#ff6b85", size=10)
        self.btn_example.pack(fill="x", padx=16, pady=(14, 0))

        tk.Label(side, text="SPEED", bg=T.PANEL, fg=T.MUTED,
                 font=T.font(9, "bold")).pack(anchor="w", padx=20, pady=(20, 0))
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_label = tk.Label(side, text="1.0x", bg=T.PANEL, fg=T.TEXT,
                                    font=T.font(10, "bold"))
        self.speed_label.pack(anchor="w", padx=20)
        tk.Scale(side, from_=0.5, to=3.0, resolution=0.5, orient="horizontal",
                 variable=self.speed_var, showvalue=False, command=self._on_speed,
                 bg=T.PANEL, fg=T.TEXT, troughcolor=T.CARD, highlightthickness=0,
                 bd=0, activebackground=T.BLUE, sliderrelief="flat").pack(fill="x", padx=16)

        # Legend
        tk.Label(side, text="LEGEND", bg=T.PANEL, fg=T.MUTED,
                 font=T.font(9, "bold")).pack(anchor="w", padx=20, pady=(16, 4))
        for glyph, color, label in [("━━▶", T.GREEN, "Allocated  (R → P)"),
                                    ("╌╌▶", T.ORANGE, "Request  (P → R)"),
                                    ("━━▶", T.RED, "Deadlock cycle")]:
            row = tk.Frame(side, bg=T.PANEL)
            row.pack(anchor="w", padx=20)
            tk.Label(row, text=glyph, bg=T.PANEL, fg=color, font=T.font(10, "bold")).pack(side="left")
            tk.Label(row, text=label, bg=T.PANEL, fg=T.TEXT, font=T.font(9)).pack(side="left", padx=6)

        tk.Label(side, text="Keys: Space = start/pause\nRight = next step, R = reset",
                 bg=T.PANEL, fg=T.MUTED, font=T.font(8), justify="left"
                 ).pack(side="bottom", anchor="w", padx=20, pady=14)

    def _make_card(self, parent, index, scenario):
        """One clickable scenario card in the sidebar."""
        frame = tk.Frame(parent, bg=T.CARD, cursor="hand2")
        frame.pack(fill="x", padx=16, pady=3)
        name = tk.Label(frame, text=scenario.name, bg=T.CARD, fg=T.TEXT,
                        font=T.font(10, "bold"), anchor="w")
        name.pack(fill="x", padx=12, pady=(8, 0))
        tag_color = T.RED if scenario.tag == "DEADLOCK" else T.GREEN
        tag = tk.Label(frame, text=scenario.tag, bg=T.CARD, fg=tag_color,
                       font=T.font(8, "bold"), anchor="w")
        tag.pack(fill="x", padx=12, pady=(0, 8))
        for widget in (frame, name, tag):
            widget.bind("<Button-1>", lambda e, i=index: self.load_scenario(i))
        return frame, name, tag

    def _build_center(self):
        center = tk.Frame(self.root, bg=T.BG)
        center.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        # The drawing area
        self.canvas = tk.Canvas(center, bg=T.CANVAS_BG, highlightthickness=1,
                                highlightbackground=T.BORDER)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._draw_grid)

        # Controls under the canvas
        bar = tk.Frame(center, bg=T.BG)
        bar.pack(fill="x", pady=(12, 0))

        self.btn_start = FlatButton(bar, "▶  Start", self.start, bg="#16a37a", hover=T.GREEN)
        self.btn_pause = FlatButton(bar, "⏸  Pause", self.pause, bg="#c58a0a", hover=T.ORANGE)
        self.btn_next = FlatButton(bar, "⏭  Next Step", self.next_step, bg="#2f6ae0", hover=T.BLUE)
        self.btn_reset = FlatButton(bar, "↺  Reset", self.reset, bg="#46506e", hover="#5d6a90")
        for b in (self.btn_start, self.btn_pause, self.btn_next, self.btn_reset):
            b.pack(side="left", padx=(0, 10))

        self.step_label = tk.Label(bar, text="Step 0 / 0", bg=T.BG, fg=T.TEXT,
                                   font=T.font(11, "bold"))
        self.step_label.pack(side="right", padx=4)

        # Progress bar
        self.progress = tk.Canvas(center, height=6, bg=T.CARD, highlightthickness=0)
        self.progress.pack(fill="x", pady=(10, 0))

    def _build_right_panel(self):
        right = tk.Frame(self.root, bg=T.PANEL, width=360)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Status badge
        self.badge = tk.Label(right, text="READY", font=T.font(11, "bold"), pady=8)
        self.badge.pack(fill="x", padx=16, pady=(18, 10))

        # "What is happening" card
        tk.Label(right, text="WHAT IS HAPPENING", bg=T.PANEL, fg=T.MUTED,
                 font=T.font(9, "bold")).pack(anchor="w", padx=18)
        card = tk.Frame(right, bg=T.CARD)
        card.pack(fill="x", padx=16, pady=(4, 12))
        self.exp_title = tk.Label(card, text="", bg=T.CARD, fg=T.TEXT, font=T.font(12, "bold"),
                                  wraplength=310, justify="left", anchor="w")
        self.exp_title.pack(fill="x", padx=14, pady=(12, 4))
        self.exp_body = tk.Label(card, text="", bg=T.CARD, fg=T.TEXT, font=T.font(10),
                                 wraplength=310, justify="left", anchor="nw", height=9)
        self.exp_body.pack(fill="x", padx=14, pady=(0, 12))

        # Coffman conditions
        tk.Label(right, text="CONDITIONS FOR DEADLOCK", bg=T.PANEL, fg=T.MUTED,
                 font=T.font(9, "bold")).pack(anchor="w", padx=18)
        cond = tk.Frame(right, bg=T.CARD)
        cond.pack(fill="x", padx=16, pady=(4, 12))
        self.cond_labels = []
        for _ in range(4):
            lbl = tk.Label(cond, text="", bg=T.CARD, font=T.font(10), anchor="w")
            lbl.pack(fill="x", padx=14, pady=3)
            self.cond_labels.append(lbl)

        # Step log
        tk.Label(right, text="STEP LOG", bg=T.PANEL, fg=T.MUTED,
                 font=T.font(9, "bold")).pack(anchor="w", padx=18)
        log_frame = tk.Frame(right, bg=T.CARD)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        self.log = tk.Text(log_frame, bg=T.CARD, fg=T.TEXT, font=T.font(9), wrap="word",
                           height=6, bd=0, highlightthickness=0, padx=10, pady=8,
                           state="disabled", cursor="arrow")
        scroll = tk.Scrollbar(log_frame, command=self.log.yview)
        self.log.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        for tag, color in [("grant", T.GREEN), ("wait", T.ORANGE), ("finish", T.BLUE),
                           ("skip", T.MUTED), ("deadlock", T.RED), ("info", T.MUTED)]:
            self.log.tag_config(tag, foreground=color)
        self.log.tag_config("deadlock", font=T.font(9, "bold"))

    # ==================================================================
    # Controls
    # ==================================================================
    def load_scenario(self, index):
        """Switch to scenario number `index` and reset everything."""
        self.scenario_index = index
        self.sim = DeadlockSimulator(SCENARIOS[index])
        for i, (frame, name, tag) in enumerate(self.cards):
            bg = T.CARD_SEL if i == index else T.CARD
            for w in (frame, name, tag):
                w.config(bg=bg)
        self.reset()

    def reset(self):
        self._stop_timer()
        self.running = False
        self.sim.reset()
        self.edges = []
        self.actor = (None, None)
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        sc = self.sim.scenario
        self._show_explanation(sc.name, sc.description +
                               "\n\nPress Start to watch it play automatically, "
                               "or Next Step to go one step at a time.", T.TEXT)
        self._log(f"Loaded: {sc.name}", "info")
        self._refresh_ui()

    def start(self):
        if self.running:
            return
        if self.sim.done:            # finished? start again from the beginning
            self.reset()
        self.running = True
        self._refresh_ui()
        self.after_id = self.root.after(300, self._tick)

    def pause(self):
        if not self.running:
            return
        self.running = False
        self._stop_timer()
        self._refresh_ui()

    def toggle_run(self):
        self.pause() if self.running else self.start()

    def next_step(self):
        if self.running or self.sim.done:
            return
        self._do_step()

    def _tick(self):
        """Auto-play: do one step, then schedule the next one."""
        self.after_id = None
        if not self.running:
            return
        self._do_step()
        if self.running and not self.sim.done:
            delay = int(2000 / self.speed_var.get())
            self.after_id = self.root.after(delay, self._tick)

    def _stop_timer(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _on_speed(self, value):
        self.speed_label.config(text=f"{float(value):.1f}x")

    # ------------------------------------------------------------------
    def _do_step(self):
        result = self.sim.next_step()
        if result is None:
            return
        self.actor = (result.process, result.resource)
        self.actor_time = time.time()
        self._sync_edges()

        colors = {"grant": T.GREEN, "wait": T.ORANGE, "finish": T.BLUE,
                  "skip": T.MUTED, "deadlock": T.RED}
        self._show_explanation(result.title, result.text, colors.get(result.kind, T.TEXT))
        self._log(f"{self.sim.step_index}. {result.title}", result.kind)

        if self.sim.done:
            self.running = False
            self._stop_timer()
            if not self.sim.deadlocked:
                self._log("Done - no deadlock.", "grant")
        self._refresh_ui()

    # ==================================================================
    # Updating the text panels
    # ==================================================================
    def _show_explanation(self, title, text, color):
        self.exp_title.config(text=title, fg=color)
        self.exp_body.config(text=text)

    def _log(self, text, tag):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _refresh_ui(self):
        sim = self.sim
        # Buttons
        self.btn_start.set_enabled(not self.running)
        self.btn_pause.set_enabled(self.running)
        self.btn_next.set_enabled(not self.running and not sim.done)
        self.btn_reset.set_enabled(True)

        # Step counter and progress bar
        self.step_label.config(text=f"Step {sim.step_index} / {sim.total_steps}")
        self.progress.delete("all")
        width = self.progress.winfo_width()
        fraction = sim.step_index / sim.total_steps if sim.total_steps else 0
        color = T.RED if sim.deadlocked else T.BLUE
        self.progress.create_rectangle(0, 0, width * fraction, 6, fill=color, outline="")

        # Status badge
        if sim.deadlocked:
            text, bg, fg = "DEADLOCK DETECTED", "#3a1624", T.RED
        elif sim.done:
            text, bg, fg = "COMPLETED - NO DEADLOCK", "#12372d", T.GREEN
        elif self.running:
            text, bg, fg = "RUNNING", "#12372d", T.GREEN
        elif sim.step_index > 0:
            text, bg, fg = "PAUSED", "#3a2e10", T.ORANGE
        else:
            text, bg, fg = "READY", T.CARD, T.BLUE
        self.badge.config(text=text, bg=bg, fg=fg)

        # Four conditions for deadlock
        for lbl, (name, desc, active) in zip(self.cond_labels, sim.coffman()):
            is_cycle = name == "Circular wait"
            color = (T.RED if is_cycle else T.ORANGE) if active else T.MUTED
            lbl.config(text=f"{'●' if active else '○'}  {name}", fg=color)

    # ==================================================================
    # Arrows: keeping the drawing in sync with the simulation
    # ==================================================================
    def _sync_edges(self):
        """
        Compare the arrows that SHOULD exist with the ones on screen.
        New ones start growing (target = 1); removed ones start shrinking (target = 0).
        Arrow key = (kind, process, resource), kind is "alloc" or "req".
        """
        wanted = set()
        for r, p in self.sim.holder.items():
            if p is not None:
                wanted.add(("alloc", p, r))
        for p, r in self.sim.waiting.items():
            if r is not None:
                wanted.add(("req", p, r))

        existing = {e["key"]: e for e in self.edges}
        for key in wanted:
            if key in existing:
                existing[key]["target"] = 1
            else:
                self.edges.append({"key": key, "prog": 0.0, "target": 1})
        for key, edge in existing.items():
            if key not in wanted:
                edge["target"] = 0

    def _update_edges(self, dt):
        alive = []
        for e in self.edges:
            if e["target"] == 1:
                e["prog"] = min(1.0, e["prog"] + dt * EDGE_SPEED)
            else:
                e["prog"] = max(0.0, e["prog"] - dt * EDGE_SPEED)
            if e["target"] == 1 or e["prog"] > 0:
                alive.append(e)
        self.edges = alive

    # ==================================================================
    # Drawing
    # ==================================================================
    def _draw_grid(self, event=None):
        c = self.canvas
        c.delete("grid")
        w, h = c.winfo_width(), c.winfo_height()
        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill=T.GRID, tags="grid")
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill=T.GRID, tags="grid")
        c.tag_lower("grid")
        self._refresh_ui()   # progress bar width depends on window size

    def _animate(self):
        """The frame loop: runs about 60 times per second."""
        now = time.time()
        dt = min(now - self.last_frame, 0.05)
        self.last_frame = now
        self.t = now - self.t0
        self._update_edges(dt)
        self._draw()
        self.root.after(16, self._animate)

    def _pos(self, name, w, h):
        """Turn a 0..1 position into real pixels, leaving room around the edges."""
        nx, ny = self.sim.scenario.positions[name]
        left, right, top, bottom = 110, 110, 120, 100
        return (left + nx * (w - left - right), top + ny * (h - top - bottom))

    def _draw(self):
        c = self.canvas
        c.delete("dyn")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 100 or h < 100:
            return
        sc = self.sim.scenario
        pos = {name: self._pos(name, w, h) for name in sc.positions}

        for e in self.edges:                 # arrows first (nodes cover their ends)
            self._draw_edge(e, pos)
        for p in sc.processes:
            self._draw_process(p, pos[p])
        for r in sc.resources:
            self._draw_resource(r, pos[r])

        # Scenario name (top left) and result banner (top centre)
        c.create_text(18, 18, text=sc.name, anchor="w", fill=T.MUTED,
                      font=T.font(11, "bold"), tags="dyn")
        if self.sim.deadlocked:
            c.create_text(w / 2, 40, text="DEADLOCK DETECTED", fill=T.RED,
                          font=T.font(20, "bold"), tags="dyn")
            c.create_text(w / 2, 68, text=self.sim.cycle_text.replace("->", "→"),
                          fill="#ff9aae", font=T.font(11), tags="dyn")
        elif self.sim.done:
            c.create_text(w / 2, 40, text="NO DEADLOCK - ALL GOOD", fill=T.GREEN,
                          font=T.font(20, "bold"), tags="dyn")

    # ---- helpers ------------------------------------------------------
    def _pulse(self, speed=5.0):
        """A number that smoothly goes 0 -> 1 -> 0 over and over."""
        return (math.sin(self.t * speed) + 1) / 2

    def _is_active(self, name):
        """True for ~1.6 seconds after a node took part in a step."""
        return name in self.actor and time.time() - self.actor_time < 1.6

    def _gap(self, name, ux, uy):
        """Distance from a node's centre to its edge, in direction (ux, uy)."""
        if name in self.sim.scenario.processes:
            return PROCESS_RADIUS
        return RESOURCE_HALF / max(abs(ux), abs(uy), 0.001)

    # ---- arrows -------------------------------------------------------
    def _draw_edge(self, e, pos):
        c = self.canvas
        kind, p, r = e["key"]
        src, dst = (r, p) if kind == "alloc" else (p, r)   # alloc: R -> P, request: P -> R
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist < 1:
            return
        ux, uy = (x1 - x0) / dist, (y1 - y0) / dist

        g0 = self._gap(src, ux, uy) + 4
        g1 = self._gap(dst, -ux, -uy) + 6
        sx, sy = x0 + ux * g0, y0 + uy * g0          # arrow start
        ex, ey = x1 - ux * g1, y1 - uy * g1          # arrow end

        p_ = e["prog"]
        prog = p_ * p_ * (3 - 2 * p_)                # smooth ease in/out
        tx, ty = sx + (ex - sx) * prog, sy + (ey - sy) * prog   # current tip

        in_cycle = e["key"] in self.sim.cycle_edges
        if in_cycle:
            color = T.RED
        else:
            color = T.GREEN if kind == "alloc" else T.ORANGE
        width = 3 + (self._pulse() * 2.5 if in_cycle else 0)

        if prog > 0.03:
            kw = dict(fill=color, width=width, arrow=tk.LAST, arrowshape=(14, 18, 6),
                      capstyle="round", tags="dyn")
            if kind == "req":
                kw["dash"] = (9, 6)
            c.create_line(sx, sy, tx, ty, **kw)

        if prog >= 0.999:
            # Moving dots show the direction of the arrow (they freeze on a deadlock)
            if not in_cycle:
                for k in range(2):
                    ph = (self.t * 0.45 + k * 0.5) % 1.0
                    dx, dy = sx + (ex - sx) * ph, sy + (ey - sy) * ph
                    c.create_oval(dx - 4, dy - 4, dx + 4, dy + 4, fill="#ffffff",
                                  outline="", tags="dyn")
            # Little label next to the middle of the arrow
            mx = (sx + ex) / 2 - uy * 16
            my = (sy + ey) / 2 + ux * 16
            c.create_text(mx, my, text="allocated" if kind == "alloc" else "waiting",
                          fill=color, font=T.font(8, "bold"), tags="dyn")

    # ---- nodes --------------------------------------------------------
    def _draw_process(self, p, xy):
        c = self.canvas
        x, y = xy
        R = PROCESS_RADIUS
        status = self.sim.status_of(p)

        if status == "deadlocked":
            outline, fill = T.RED, T.DEADLOCK_FILL
            pu = self._pulse()
            c.create_oval(x - R - 7 - pu * 7, y - R - 7 - pu * 7, x + R + 7 + pu * 7,
                          y + R + 7 + pu * 7, outline=T.RED, width=3, tags="dyn")
            c.create_oval(x - R - 16 - pu * 11, y - R - 16 - pu * 11, x + R + 16 + pu * 11,
                          y + R + 16 + pu * 11, outline="#7a2438", width=1, tags="dyn")
            label, label_color = "DEADLOCKED", T.RED
        elif status == "finished":
            outline, fill = T.FINISHED_LINE, T.FINISHED_FILL
            label, label_color = "finished", T.MUTED
        elif status == "waiting":
            outline, fill = T.ORANGE, T.PROCESS_FILL
            label, label_color = f"waiting for {self.sim.waiting[p]}", T.ORANGE
        else:
            outline, fill = T.BLUE, T.PROCESS_FILL
            label, label_color = status, T.BLUE

        if self._is_active(p):                       # yellow "just acted" ring
            pu = self._pulse(8)
            c.create_oval(x - R - 6 - pu * 4, y - R - 6 - pu * 4, x + R + 6 + pu * 4,
                          y + R + 6 + pu * 4, outline="#fde047", width=2, tags="dyn")

        c.create_oval(x - R, y - R, x + R, y + R, fill=fill, outline=outline, width=3, tags="dyn")
        c.create_text(x, y, text=p, fill=T.TEXT, font=T.font(15, "bold"), tags="dyn")
        c.create_text(x, y + R + 16, text=label, fill=label_color,
                      font=T.font(9, "bold"), tags="dyn")
        held = self.sim.held_by(p)
        if held:
            c.create_text(x, y + R + 32, text="holds " + ", ".join(held), fill=T.MUTED,
                          font=T.font(8), tags="dyn")

    def _draw_resource(self, r, xy):
        c = self.canvas
        x, y = xy
        H = RESOURCE_HALF
        owner = self.sim.holder[r]
        in_cycle = r in self.sim.cycle_resources

        outline = T.RED if in_cycle else T.TEAL
        fill = T.DEADLOCK_FILL if in_cycle else T.RESOURCE_FILL

        if in_cycle:
            pu = self._pulse()
            rounded_rect(c, x - H - 7 - pu * 6, y - H - 7 - pu * 6, x + H + 7 + pu * 6,
                         y + H + 7 + pu * 6, 16, fill="", outline=T.RED, width=3, tags="dyn")
        if self._is_active(r):
            pu = self._pulse(8)
            rounded_rect(c, x - H - 6 - pu * 4, y - H - 6 - pu * 4, x + H + 6 + pu * 4,
                         y + H + 6 + pu * 4, 14, fill="", outline="#fde047", width=2, tags="dyn")

        rounded_rect(c, x - H, y - H, x + H, y + H, 12, fill=fill, outline=outline,
                     width=3, tags="dyn")
        c.create_text(x, y, text=r, fill=T.TEXT, font=T.font(15, "bold"), tags="dyn")
        if owner is None:
            c.create_text(x, y + H + 16, text="free", fill=T.MUTED,
                          font=T.font(9, "bold"), tags="dyn")
        else:
            c.create_text(x, y + H + 16, text=f"held by {owner}",
                          fill=T.RED if in_cycle else T.GREEN,
                          font=T.font(9, "bold"), tags="dyn")
