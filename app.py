from __future__ import annotations
import copy
import csv
import json
import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, simpledialog, ttk

TITLE = "Will it Break?"
INK, MUTED, LINE, GRID, BLUE, WOOD, DECK = "#17212b", "#61717f", "#d7dfe5", "#dbe3e8", "#285c87", "#8a5a36", "#9a7b57"
VEHICLES = {
    "Car": {"axles": [(0, 2000), (10, 2000)], "color": "#d9b72c", "kind": "car"},
    "Loaded Dump Truck": {"axles": [(0, 12000), (14, 17000), (18.5, 17000)], "color": "#bd642f", "kind": "dump"},
    "Semi": {"axles": [(0, 8000), (14, 32000), (28, 32000)], "color": "#4e6f93", "kind": "semi"},
    "Fire Engine": {"axles": [(0, 20000), (17, 27000), (21.5, 27000)], "color": "#c74343", "kind": "fire"},
}
VALIDATION_CASES = {
    "Problem 1 - Heavy Transport": [(10.0, 20000.0), (25.0, 40000.0), (50.0, 30000.0)],
    "Problem 2 - Asymmetric Traffic": [(10.0, 15000.0), (20.0, 25000.0), (30.0, 35000.0), (40.0, 10000.0)],
}
DECK_NODES = [(float(x), 0.0) for x in range(0, 61, 10)]

@dataclass
class Member:
    a: tuple[float, float]
    b: tuple[float, float]
    deck: bool = False
    @property
    def length(self): return math.dist(self.a, self.b)
    def key(self): return tuple(sorted((self.a, self.b)))

@dataclass
class Result:
    stable: bool
    message: str = ""
    forces: list[float] | None = None
    reactions: dict[str, float] | None = None

def gaussian_solve(matrix, rhs):
    n = len(rhs)
    if not n or len(matrix) != n or any(len(row) != n for row in matrix): return None
    aug = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    pivots = []
    for col in range(n):
        p = max(range(col, n), key=lambda row: abs(aug[row][col]))
        magnitude = abs(aug[p][col])
        if not math.isfinite(magnitude) or magnitude < 1e-9: return None
        aug[col], aug[p] = aug[p], aug[col]
        pivots.append(magnitude)
        for row in range(n):
            if row == col: continue
            factor = aug[row][col] / aug[col][col]
            if abs(factor) < 1e-12: continue
            for j in range(col, n + 1): aug[row][j] -= factor * aug[col][j]
    if min(pivots) / max(pivots) < 1e-8: return None
    solution = [aug[i][n] / aug[i][i] for i in range(n)]
    return solution if all(math.isfinite(v) for v in solution) else None

def solve_truss(nodes, members, front_x, vehicle_name):
    joints, unknowns = len(nodes), len(members) + 3
    if unknowns != joints * 2:
        return Result(False, f"Unstable: {len(members)} members and {joints} joints; M + 3 must equal 2 × J.")
    if (0.0, 0.0) not in nodes or (60.0, 0.0) not in nodes:
        return Result(False, "Unstable: both the pin and roller supports are required.")
    ni = {node: i for i, node in enumerate(nodes)}
    matrix = [[0.0] * unknowns for _ in range(unknowns)]
    rhs = [0.0] * unknowns
    if vehicle_name in VALIDATION_CASES:
        applied_loads = VALIDATION_CASES[vehicle_name]
    else:
        applied_loads = [(front_x-offset, load) for offset, load in VEHICLES[vehicle_name]["axles"]]
    for x, load in applied_loads:
        if not 0 <= x <= 60: continue
        left_i = min(5, int(x // 10))
        left, fraction = left_i * 10.0, (x - left_i * 10.0) / 10.0
        for node, share in [((left, 0.0), 1 - fraction), ((left + 10, 0.0), fraction)]:
            if node in ni: rhs[ni[node] * 2 + 1] += load * share
    for mi, member in enumerate(members):
        dx, dy = member.b[0] - member.a[0], member.b[1] - member.a[1]
        length = math.hypot(dx, dy)
        if length < 1e-8 or member.a not in ni or member.b not in ni:
            return Result(False, "Unstable: a member has invalid or coincident endpoints.")
        ux, uy = dx / length, dy / length
        a, b = ni[member.a], ni[member.b]
        matrix[2*a][mi] += ux; matrix[2*a+1][mi] += uy
        matrix[2*b][mi] -= ux; matrix[2*b+1][mi] -= uy
    pi, ri = ni[(0.0, 0.0)], ni[(60.0, 0.0)]
    matrix[2*pi][len(members)] = 1
    matrix[2*pi+1][len(members)+1] = 1
    matrix[2*ri+1][len(members)+2] = 1
    values = gaussian_solve(matrix, rhs)
    if values is None: return Result(False, "Unstable: the equilibrium system is singular or nearly singular.")
    return Result(True, forces=values[:len(members)], reactions={
        "Pin X": values[len(members)], "Pin Y": values[len(members)+1], "Roller Y": values[len(members)+2]})

class BridgeApp:
    def __init__(self, root):
        self.root = root
        root.title(TITLE); root.geometry("1420x900"); root.minsize(1100, 720); root.configure(bg="#eef2f4")
        self.nodes = set(DECK_NODES)
        self.members = [Member(DECK_NODES[i], DECK_NODES[i+1], True) for i in range(6)]
        self.undo_stack = []; self.mode = "Build"; self.tool = "member"
        self.first_joint = self.drag_joint = self.hover_point = None
        self.position = tk.DoubleVar(value=44.0); self.vehicle = tk.StringVar(value="Semi")
        self.hint = tk.StringVar(value="Build mode: click two grid points to add a member.")
        self.cost, self.joint_count, self.member_count = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.status, self.count_hint = tk.StringVar(), tk.StringVar()
        self.last_result = None; self.max_forces = []; self.crossing_result = False; self.drive_after = None; self.paused = False; self.driving = False; self.drive_front = 0.0
        self.project_path = None; self.support_type = "Pin and roller"; self.span_ft = 60.0
        self.section = "Uniform truss members"; self.deflection_limit_ft = None
        self._build_ui(); self._update_stats(); self._draw()
        root.bind("<Control-z>", lambda _e: self.undo()); root.bind("<Escape>", lambda _e: self.detach())
        root.bind("<Key-a>", lambda _e: self.set_tool("member")); root.bind("<Key-e>", lambda _e: self.set_tool("erase"))
        root.bind("<Key-d>", lambda _e: self.set_tool("drag")); root.bind("<Left>", lambda _e: self.step(-.5)); root.bind("<Right>", lambda _e: self.step(.5))

    def _build_ui(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_project)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Set deflection limit...", command=self.set_deflection_limit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.configure(menu=menubar)
        self.root.bind("<Control-s>", lambda _e: self.save_project())
        self.root.bind("<Control-o>", lambda _e: self.open_project())
        top = tk.Frame(self.root, bg="white", highlightbackground=LINE, highlightthickness=1); top.pack(fill="x")
        tk.Label(top, text=TITLE, bg="white", fg=INK, font=("Segoe UI", 18, "bold")).pack(side="left", padx=18, pady=12)
        tk.Label(top, text="2D BRIDGE DESIGN SIMULATOR", bg="white", fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        modebar = tk.Frame(top, bg="#f7f9fb"); modebar.pack(side="right", padx=18, pady=9)
        self.mode_buttons = {}
        for mode in ("Build", "Test"):
            b = tk.Button(modebar, text=mode, command=lambda m=mode: self.set_mode(m), takefocus=True, padx=15, pady=7)
            b.pack(side="left", padx=2); self.mode_buttons[mode] = b
        self.export_button = tk.Button(modebar, text="Export results", command=self.export_results,
            state="disabled", takefocus=True, padx=12, pady=7, fg=BLUE, bg="white")
        self.export_button.pack(side="left", padx=(8, 4))
        work = tk.Frame(self.root, bg="#eef2f4"); work.pack(fill="both", expand=True, padx=12, pady=12)
        work.columnconfigure(1, weight=1); work.rowconfigure(0, weight=1)
        self.tools = self._panel(work, 0, "BUILD TOOLS", 160)
        center = tk.Frame(work, bg="white", highlightbackground=LINE, highlightthickness=1)
        center.grid(row=0, column=1, sticky="nsew", padx=10); center.columnconfigure(0, weight=1); center.rowconfigure(1, weight=1)
        tk.Label(center, textvariable=self.hint, anchor="w", justify="left", bg="#f7f9fb", fg=MUTED,
                 padx=12, pady=10, wraplength=780).grid(row=0, column=0, sticky="ew")
        self.canvas = tk.Canvas(center, bg="white", highlightthickness=0, takefocus=True); self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _e: self._draw()); self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda _e: (setattr(self, "hover_point", None), self._draw()))
        self.canvas.bind("<Button-1>", self._button_down)
        self.canvas.bind("<B1-Motion>", self._drag); self.canvas.bind("<ButtonRelease-1>", self._release)
        self.controls = tk.Frame(center, bg="#f7f9fb", padx=10, pady=9); self.controls.grid(row=2, column=0, sticky="ew"); self._test_controls(); self.controls.grid_remove()
        self.right = self._panel(work, 2, "BRIDGE STATUS", 220)
        self._stat(self.right, "Estimated cost", self.cost); self._stat(self.right, "Joints", self.joint_count)
        self._stat(self.right, "Members", self.member_count); self._stat(self.right, "Structure", self.status)
        tk.Label(self.right, textvariable=self.count_hint, bg="white", fg=MUTED, wraplength=190, justify="left").pack(fill="x", padx=12, pady=5)
        tk.Label(self.right, text="CAPACITIES\nTension  90,000 lb\nCompression  75,000 lb", bg="white", fg=INK,
                 justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=14)
        self.banner = tk.Frame(self.root, bg="#edf8f1", highlightbackground="#2f7d4d", highlightthickness=1)
        self.details = tk.Frame(self.root, bg="white", highlightbackground=LINE, highlightthickness=1); self.details.pack(fill="x", padx=12, pady=(0, 12))
        head = tk.Frame(self.details, bg="white"); head.pack(fill="x")
        self.details_button = tk.Button(head, text="Open details", command=self.toggle_details, fg=BLUE, bg="white", relief="flat", padx=12, pady=9, takefocus=True)
        self.details_button.pack(side="left")
        tk.Label(head, text="Separate reaction and member force tables · + tension / − compression", bg="white", fg=MUTED).pack(side="left")
        content = tk.Frame(self.details, bg="white"); self.detail_content = content
        self.reaction_tree = self._tree(content, "JOINT REACTIONS"); self.member_tree = self._tree(content, "MEMBER FORCES")
        self._build_tools(); self.set_mode("Build")

    def _panel(self, parent, col, title, width):
        f = tk.Frame(parent, width=width, bg="white", highlightbackground=LINE, highlightthickness=1)
        f.grid(row=0, column=col, sticky="ns"); f.grid_propagate(False)
        tk.Label(f, text=title, bg="white", fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(14, 10))
        return f

    def _stat(self, parent, label, var):
        block = tk.Frame(parent, bg="white"); block.pack(fill="x", padx=12, pady=(0, 9))
        tk.Label(block, text=label.upper(), bg="white", fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(block, textvariable=var, bg="white", fg=INK, font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", pady=3)
        tk.Frame(block, bg=LINE, height=1).pack(fill="x")

    def _build_tools(self):
        self.tool_buttons = {}
        for label, key in (("✚  Add member", "member"), ("⌫  Erase member", "erase"), ("↔  Drag joint", "drag")):
            b = tk.Button(self.tools, text=label, anchor="w", command=lambda k=key: self.set_tool(k), bg="white", fg=INK,
                          relief="flat", highlightthickness=1, highlightbackground=LINE, padx=9, pady=10, takefocus=True)
            b.pack(fill="x", padx=8, pady=4); self.tool_buttons[key] = b
        tk.Frame(self.tools, bg=LINE, height=1).pack(fill="x", padx=9, pady=8)
        tk.Button(self.tools, text="↶  Undo", anchor="w", command=self.undo, bg="white", relief="flat", padx=9, pady=10, takefocus=True).pack(fill="x", padx=8, pady=3)
        tk.Button(self.tools, text="▧  Delete all", anchor="w", command=self.clear, bg="white", relief="flat", padx=9, pady=10, takefocus=True).pack(fill="x", padx=8, pady=3)
        tk.Label(self.tools, text="A  Add member\nE  Erase member\nD  Drag joint\nEsc  Detach\nCtrl+Z  Undo", bg="white", fg=MUTED, justify="left").pack(anchor="w", padx=12, pady=12)

    def _test_controls(self):
        left = tk.Frame(self.controls, bg="#f7f9fb"); left.pack(side="left", padx=(0, 10))
        tk.Label(left, text="VEHICLE / LOAD CASE", bg="#f7f9fb", fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        combo = ttk.Combobox(left, values=list(VEHICLES)+list(VALIDATION_CASES), textvariable=self.vehicle, state="readonly", width=24)
        combo.pack(pady=3); combo.bind("<<ComboboxSelected>>", lambda _e: self.park())
        pos = tk.Frame(self.controls, bg="#f7f9fb"); pos.pack(side="left", padx=6)
        tk.Label(pos, text="FRONT AXLE (FT)", bg="#f7f9fb", fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(pos, bg="#f7f9fb"); row.pack(pady=3)
        tk.Button(row, text="−", command=lambda: self.step(-.5), width=2).pack(side="left")
        tk.Spinbox(row, from_=0, to=60, increment=.5, textvariable=self.position, width=7, command=self.park, takefocus=True).pack(side="left", padx=3)
        tk.Button(row, text="+", command=lambda: self.step(.5), width=2).pack(side="left")
        tk.Scale(self.controls, from_=0, to=60, resolution=.5, orient="horizontal", showvalue=False, variable=self.position,
                 command=lambda _v: self._position_changed(), length=150, bg="#f7f9fb", highlightthickness=0, takefocus=True).pack(side="left", padx=7)
        actions = tk.Frame(self.controls, bg="#f7f9fb"); actions.pack(side="right")
        tk.Button(actions, text="Park", command=self.park, takefocus=True, padx=10).pack(side="left", padx=2)
        self.drive_button = tk.Button(actions, text="Drive Across", command=self.start_drive, bg=BLUE, fg="white", takefocus=True, padx=10)
        self.drive_button.pack(side="left", padx=2)
        self.pause_button = tk.Button(actions, text="Pause", command=self.pause_resume, state="disabled", takefocus=True, padx=10)
        self.pause_button.pack(side="left", padx=2)

    def _tree(self, parent, title):
        f = tk.Frame(parent, bg="white"); f.pack(side="left", fill="both", expand=True, padx=10, pady=7)
        tk.Label(f, text=title, bg="white", fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        t = ttk.Treeview(f, columns=("name", "force"), show="headings", height=5)
        t.heading("name", text="Item"); t.heading("force", text="Force (lb)")
        t.column("name", width=180); t.column("force", width=140, anchor="e"); t.pack(fill="both", expand=True)
        return t
    def _snapshot(self):
        self.undo_stack.append((set(self.nodes), copy.deepcopy(self.members)))
        if len(self.undo_stack) > 50: self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack: self.hint.set("Nothing to undo."); return
        self.nodes, self.members = self.undo_stack.pop(); self.first_joint = None
        self._draw(); self._update_stats(); self.hint.set("Last bridge edit undone.")

    def clear(self):
        if len(self.nodes) == 7 and len(self.members) == 6:
            self.hint.set("There are no structural members to clear. Deck members and joints are permanent."); return
        self._snapshot(); self.nodes = set(DECK_NODES)
        self.members = [Member(DECK_NODES[i], DECK_NODES[i+1], True) for i in range(6)]
        self.first_joint = None; self._draw(); self._update_stats()
        self.hint.set("Bridge cleared. The deck joints, deck members, and supports remain.")

    def set_tool(self, tool):
        if self.mode != "Build": return
        self.tool, self.first_joint = tool, None
        for key, button in self.tool_buttons.items():
            button.configure(bg="#edf4fa" if key == tool else "white", highlightbackground=BLUE if key == tool else LINE)
        self.hint.set({"member": "Add Member: click the first endpoint, then a second. Press Esc to detach.",
                       "erase": "Erase Member: click a structural member to delete it.",
                       "drag": "Drag Joint: move a structural joint to another 1 ft grid point."}[tool])
        self._draw()

    def set_mode(self, mode):
        self._stop_drive(); self.mode = mode
        for key, button in self.mode_buttons.items():
            button.configure(bg=BLUE if key == mode else "#f7f9fb", fg="white" if key == mode else MUTED)
        if mode == "Test":
            self.tools.grid_remove()
            self.controls.grid(); self.tool = ""; self.first_joint = None
            self.hint.set("Test mode: park a vehicle or drive it across the bridge.")
        else:
            self.tools.grid()
            self.controls.grid_remove(); self.banner.pack_forget(); self.tool = "member"; self.first_joint = None
            self.hint.set("Build mode: click two grid points to add a member.")
        self._draw(); self._update_stats()

    def toggle_details(self):
        if self.detail_content.winfo_manager():
            self.detail_content.pack_forget(); self.details_button.configure(text="Open details")
        else:
            self.detail_content.pack(fill="both", expand=True); self.details_button.configure(text="Close details")

    def _metrics(self):
        w, h = max(500, self.canvas.winfo_width()), max(350, self.canvas.winfo_height())
        left, right, top, bottom = 38, 18, 35, 38
        scale = max(4, min((w-left-right)/95, (h-top-bottom)/25))
        x0 = left + (w-left-right-95*scale)/2 + 5*scale
        y0 = top + (h-top-bottom-25*scale)/2
        return x0, y0, scale

    def _xy(self, point):
        x0, y0, s = self._metrics(); return x0+point[0]*s, y0+(25-point[1])*s

    def _point_at(self, px, py, snap=True):
        x0, y0, s = self._metrics(); x, y = round((px-x0)/s), round(25-(py-y0)/s)
        if not (0 <= x <= 60 and 0 <= y <= 25): return None
        point = (float(x), float(y))
        if snap and self.nodes:
            near = min(self.nodes, key=lambda n: math.dist(n, point))
            if math.dist(near, point) <= 2: point = near
        if point[1] == 0 and point not in DECK_NODES: return None
        return point

    def _motion(self, event):
        self.hover_point = self._point_at(event.x, event.y)
        if self.mode == "Build" and self.tool == "member":
            if self.hover_point is None: self.hint.set("Choose a point on the 60 ft by 25 ft grid.")
            elif self.first_joint is None: self.hint.set(f"Existing members: {len(self.members)}. First endpoint at ({self.hover_point[0]:g}, {self.hover_point[1]:g}) ft.")
            elif self.hover_point != self.first_joint:
                length = math.dist(self.first_joint, self.hover_point)
                self.hint.set(f"Existing members: {len(self.members)}. Proposed member length: {length:.2f} ft. Click to add.")
        self._draw()

    def _button_down(self, event):
        if self.mode == "Build" and self.tool == "drag": self._press(event)
        else: self._click(event)

    def _click(self, event):
        if self.mode != "Build" or self.tool not in ("member", "erase"): return
        if self.tool == "erase":
            member = self._member_near(event.x, event.y)
            if member is None: self.hint.set("Click a structural member to erase it.")
            elif member.deck: self.hint.set("Deck members cannot be erased.")
            else:
                self._snapshot(); self.members.remove(member); self._orphans(); self._draw(); self._update_stats(); self.hint.set("Member erased.")
            return
        point = self._point_at(event.x, event.y)
        if point is None: self.hint.set("Use the 1 ft grid; the deck has fixed joints every 10 ft."); return
        if self.first_joint is None:
            self.first_joint = point; self.hint.set(f"First endpoint set at ({point[0]:g}, {point[1]:g}) ft. Choose the second endpoint."); self._draw(); return
        if point == self.first_joint: self.hint.set("A member needs two distinct endpoints."); return
        candidate = Member(self.first_joint, point)
        if any(m.key() == candidate.key() for m in self.members): self.hint.set("A member already exists between those joints."); return
        self._snapshot(); self.nodes.update((candidate.a, candidate.b)); self.members.append(candidate); self.first_joint = point
        self._draw(); self._update_stats(); self.hint.set(f"Member added ({candidate.length:.2f} ft). Choose next endpoint or Esc to detach.")

    def detach(self):
        if self.mode == "Build" and self.tool == "member":
            self.first_joint = None; self._draw(); self.hint.set("Member placement detached. Choose a new first joint.")

    def _press(self, event):
        if self.mode != "Build" or self.tool != "drag": return
        node = self._joint_near(event.x, event.y)
        if node is None or node in DECK_NODES: return
        self.drag_joint = node; self._snapshot(); self.hint.set("Dragging joint. Release at a 1 ft grid intersection.")

    def _drag(self, event):
        if self.drag_joint is None: return
        self.hover_point = self._point_at(event.x, event.y, snap=False); self._draw()
        if self.hover_point:
            a, b = self._xy(self.drag_joint), self._xy(self.hover_point)
            self.canvas.create_line(*a, *b, fill=BLUE, width=2, dash=(4, 3), tags="preview")

    def _release(self, event):
        if self.drag_joint is None: return
        old, self.drag_joint = self.drag_joint, None
        point = self._point_at(event.x, event.y, snap=False); self.canvas.delete("preview")
        if point is None:
            self.undo_stack.pop(); self.hint.set("Choose a grid point inside the site; joint returned to its original location."); return
        if point[1] == 0 and point not in DECK_NODES:
            self.undo_stack.pop(); self.hint.set("Only fixed deck joints can lie on the roadway."); return
        self._move_joint(old, point); self._draw(); self._update_stats(); self.hint.set("Joint moved; nearby duplicate joints were merged.")

    def _move_joint(self, old, point):
        if old == point: self.undo_stack.pop(); return
        close = min((n for n in self.nodes if n != old), key=lambda n: math.dist(n, point), default=None)
        target = close if close and math.dist(close, point) <= 2 else point
        changed = []
        for member in self.members:
            if member.deck: changed.append(member); continue
            a = target if member.a == old else member.a; b = target if member.b == old else member.b
            if a != b: changed.append(Member(a, b))
        by_key = {m.key(): m for m in changed}; self.members = list(by_key.values())
        self.nodes.discard(old); self.nodes.add(target); self._orphans()

    def _orphans(self):
        used = set(DECK_NODES)
        for m in self.members: used.update((m.a, m.b))
        self.nodes.intersection_update(used)

    def _joint_near(self, x, y):
        near, dist = None, 12
        for node in self.nodes:
            px, py = self._xy(node); d = math.hypot(x-px, y-py)
            if d < dist: near, dist = node, d
        return near

    def _member_near(self, x, y):
        result, best = None, 11
        for m in self.members:
            ax, ay = self._xy(m.a); bx, by = self._xy(m.b); dx, dy = bx-ax, by-ay
            denom = dx*dx+dy*dy; t = 0 if not denom else max(0, min(1, ((x-ax)*dx+(y-ay)*dy)/denom))
            d = math.hypot(x-ax-t*dx, y-ay-t*dy)
            if d < best: result, best = m, d
        return result
    def _update_stats(self):
        self.last_result = None
        self.max_forces = []
        self.export_button.configure(state="disabled")
        count, members = len(self.nodes), len(self.members)
        difference = members + 3 - 2*count
        self.cost.set(f"${count*500+sum(m.length for m in self.members)*100:,.0f}")
        self.joint_count.set(str(count)); self.member_count.set(str(members))
        if difference > 0:
            self.status.set("Redundant")
            self.count_hint.set(f"{difference} redundant structural member{'s are' if difference != 1 else ' is'} present. Pink dashed members are candidates to remove.")
        elif difference < 0:
            needed = -difference; self.status.set("Incomplete")
            self.count_hint.set(f"Add {needed} more member{'s' if needed != 1 else ''} to reach a determinate bridge.")
        else:
            result = solve_truss(sorted(self.nodes), self.members, float(self.position.get()), self.vehicle.get())
            self.status.set("Stable" if result.stable else "Unstable")
            self.count_hint.set("Determinate by count; equilibrium system is checked for singularity." if result.stable else result.message)
        self._draw()

    def _member_color(self, force):
        if force is None: return WOOD
        capacity = 90000 if force >= 0 else 75000; magnitude = abs(force)
        if magnitude > capacity: return "#111111"
        if magnitude <= capacity*.5: return WOOD
        t = (magnitude-capacity*.5)/(capacity*.5)
        start, end = ((43,132,73),(40,92,135)) if force >= 0 else ((229,190,50),(207,55,55))
        rgb = [round(a+(b-a)*t) for a,b in zip(start,end)]
        return "#%02x%02x%02x" % tuple(rgb)

    def _draw(self):
        if not hasattr(self, "canvas"): return
        c = self.canvas; c.delete("all")
        x0, y0, s = self._metrics(); right, bottom = x0+60*s, y0+25*s
        # Road approaches and abutment banks.
        c.create_line(x0-5*s, bottom, x0, bottom, fill="#737d84", width=4)
        c.create_line(right, bottom, right+5*s, bottom, fill="#737d84", width=4)
        for bx in (2.5, 57.5):
            px, py = self._xy((bx,0)); c.create_polygon(px-3*s,py+4,px+3*s,py+4,px,py+4+2*s, fill="#b7a78f", outline="#766d5f")
            c.create_line(px-3*s,py+4+2*s,px+3*s,py+4+2*s, fill="#766d5f", width=3)
        for x in range(61):
            px, _ = self._xy((x,0)); c.create_line(px,y0,px,bottom, fill="#c6d1d8" if x%5==0 else GRID, width=1)
        for y in range(26):
            _, py = self._xy((0,y)); c.create_line(x0,py,right,py, fill="#c6d1d8" if y%5==0 else GRID, width=1)
        for x in range(0,61,10):
            px,py=self._xy((x,0)); c.create_text(px,py+15,text=str(x),fill=MUTED,font=("Segoe UI",8))
        c.create_text(right,bottom+27,text="60 ft span · 1 ft grid",fill=MUTED,font=("Segoe UI",9))
        difference = len(self.members)+3-2*len(self.nodes)
        structural = [m for m in self.members if not m.deck]
        for i, m in enumerate(self.members):
            a,b=self._xy(m.a),self._xy(m.b)
            force = self.last_result.forces[i] if self.mode=="Test" and self.last_result and self.last_result.stable and i<len(self.last_result.forces) else None
            color = DECK if m.deck else self._member_color(force)
            redundant = not m.deck and difference>0 and structural.index(m)>=max(0,len(structural)-difference)
            c.create_line(*a,*b,fill="#e44e78" if redundant else color,width=5 if m.deck else 4,
                          dash=(8,4) if redundant else (),capstyle="round",tags="member")
        px,py=self._xy((0,0)); rx,ry=self._xy((60,0))
        c.create_polygon(px-10,py+3,px+10,py+3,px,py+18,fill="#dfe8ee",outline=INK,width=2)
        c.create_polygon(rx-10,ry+3,rx+10,ry+3,rx,ry+18,fill="#dfe8ee",outline=INK,width=2)
        c.create_oval(rx-3,ry+19,rx+3,ry+25,fill=INK)
        for node in sorted(self.nodes):
            x,y=self._xy(node); r=6 if node in DECK_NODES else 5
            fill="#cfe5f5" if node in (self.hover_point,self.first_joint) else "white"
            c.create_oval(x-r,y-r,x+r,y+r,fill=fill,outline=INK,width=2,tags="joint")
        if self.mode=="Build" and self.tool=="member" and self.first_joint and self.hover_point and self.first_joint!=self.hover_point:
            c.create_line(*self._xy(self.first_joint),*self._xy(self.hover_point),fill=BLUE,width=2,dash=(5,3))
        if self.mode=="Test": self._draw_vehicle()

    def _draw_vehicle(self):
        if self.vehicle.get() in VALIDATION_CASES:
            for x, load in VALIDATION_CASES[self.vehicle.get()]:
                px, deck_y = self._xy((x, 0.0))
                top_y = self._xy((x, 3.0))[1]
                self.canvas.create_line(px, top_y, px, deck_y-5, fill="#c74343", width=3, arrow="last")
                self.canvas.create_text(px, top_y-10, text=f"{load:,.0f} lb", fill="#7a2525", font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(12, 14, anchor="nw", text=self.vehicle.get(), fill=INK, font=("Segoe UI", 9, "bold"))
            return
        spec = VEHICLES[self.vehicle.get()]
        front = self.drive_front if self.driving else float(self.position.get())
        axles = [front-offset for offset, _load in spec["axles"]]
        rear = min(axles)
        left, right = rear-1.5, front+2.0
        xl, deck_y = self._xy((left, 0)); xr, _ = self._xy((right, 0))
        scale = self._metrics()[2]; top = deck_y-2.8*scale; color = spec["color"]
        if spec["kind"] == "car":
            self.canvas.create_polygon(xl, deck_y-.7*scale, xl+1.1*scale, top+.5*scale,
                xl+3.0*scale, top, xr-1.0*scale, top+.2*scale, xr, deck_y-.7*scale,
                fill=color, outline=INK, width=2)
        elif spec["kind"] == "semi":
            cab = self._xy((front-5, 0))[0]
            self.canvas.create_rectangle(xl, top+.25*scale, cab-.3*scale, deck_y-.7*scale,
                fill="#e5e8eb", outline=INK, width=2)
            self.canvas.create_polygon(cab, top+1.2*scale, cab+.9*scale, top+.2*scale,
                xr-.2*scale, top+.2*scale, xr, top+1.2*scale, xr, deck_y-.7*scale,
                cab, deck_y-.7*scale, fill=color, outline=INK, width=2)
        elif spec["kind"] == "dump":
            cab = self._xy((front-5, 0))[0]
            self.canvas.create_polygon(xl+.3*scale, top+1.2*scale, cab-.4*scale, top+.2*scale,
                cab, top+.4*scale, cab, deck_y-.7*scale, xl+.3*scale, deck_y-.7*scale,
                fill="#bc8d48", outline=INK, width=2)
            self.canvas.create_rectangle(cab, top+1.0*scale, xr, deck_y-.7*scale,
                fill=color, outline=INK, width=2)
        else:
            self.canvas.create_rectangle(xl, top+.3*scale, xr, deck_y-.7*scale, fill=color, outline=INK, width=2)
            self.canvas.create_rectangle(xr-1.4*scale, top+.8*scale, xr-.3*scale, top+1.5*scale,
                fill="#dcebf2", outline=INK)
            self.canvas.create_line(xl+.5*scale, top, xr-.4*scale, top, fill="#f1d567", width=4)
        radius = max(4, .32*scale)
        for axle in sorted(set(axles)):
            if -5 <= axle <= 90:
                wx, wy = self._xy((axle, 0))
                self.canvas.create_oval(wx-radius, wy-radius, wx+radius, wy+radius, fill="#26323b", outline="white")
        self.canvas.create_text((xl+xr)/2, top-.7*scale,
            text=f"{self.vehicle.get()} ? front axle x={front:.1f} ft", fill=INK, font=("Segoe UI", 9, "bold"))

    def _position_changed(self):
        try: value=float(self.position.get())
        except (ValueError,tk.TclError): return
        self.position.set(max(0,min(60,round(value*2)/2)))
        if self.mode=="Test": self._draw()

    def step(self, amount):
        try: value=float(self.position.get())
        except (ValueError,tk.TclError): value=44
        self.position.set(max(0,min(60,round((value+amount)*2)/2))); self._position_changed()

    def park(self):
        self._stop_drive()
        self.crossing_result=False
        self._position_changed(); result=solve_truss(sorted(self.nodes),self.members,float(self.position.get()),self.vehicle.get())
        self.last_result=result; self._draw(); self._details(result)
        if result.stable:
            if self.vehicle.get() in VALIDATION_CASES:
                self.hint.set(f"Solved static load case: {self.vehicle.get()}.")
            else:
                self.hint.set(f"Parked load solved at front axle x = {self.position.get():g} ft.")
        else: self.hint.set(result.message)

    def _details(self, result, crossing=False):
        for tree in (self.reaction_tree,self.member_tree):
            for row in tree.get_children(): tree.delete(row)
        if not result or not result.stable: return
        for name,force in result.reactions.items():
            self.reaction_tree.insert("","end",values=(name,f"{force:+,.2f}".rstrip("0").rstrip(".")))
        forces=self.max_forces if crossing and self.max_forces else result.forces
        for i,force in enumerate(forces,1):
            if force is not None: self.member_tree.insert("","end",values=(f"Member {i}",f"{force:+,.2f}".rstrip("0").rstrip(".")))
        self.reaction_tree.insert("","end",values=("Sign","+ tension · − compression"))

    def start_drive(self):
        if self.mode!="Test": return
        if self.vehicle.get() in VALIDATION_CASES:
            self.hint.set("Validation load cases are static; use Park to solve this load situation.")
            return
        self._stop_drive(); self.driving=True; self.drive_front=0.0; self.position.set(0); self.max_forces=[None]*len(self.members); self.crossing_result=True
        self.last_result=None; self.export_button.configure(state="disabled")
        self.pause_button.configure(state="normal",text="Pause"); self.drive_button.configure(state="disabled")
        self.banner.pack_forget(); self._drive_step()

    def _drive_step(self):
        front=self.drive_front
        result=solve_truss(sorted(self.nodes),self.members,front,self.vehicle.get()); self.last_result=result
        if not result.stable:
            self._stop_drive(); self.hint.set(result.message); self._draw(); return
        failed=None
        for i,force in enumerate(result.forces):
            if self.max_forces[i] is None or abs(force)>abs(self.max_forces[i]): self.max_forces[i]=force
            capacity=90000 if force>=0 else 75000
            if abs(force)>capacity: failed=(i,force); break
        self._draw(); self._details(result,crossing=True)
        self.export_button.configure(state="normal")
        if failed:
            self._stop_drive(); i,force=failed
            self._show_result(True,f"Your Bridge Failed · Member {i+1} reached {abs(force):,.0f} lb."); return
        last_offset=max(o for o,_ in VEHICLES[self.vehicle.get()]["axles"])
        if front-last_offset>=60:
            self._stop_drive(); self._show_result(False,f"{self.vehicle.get()} crossed the 60 ft bridge safely."); self._details(result,crossing=True); return
        self.drive_front=front+.5; self.drive_after=self.root.after(120,self._drive_step)

    def pause_resume(self):
        if self.drive_after is None and not self.paused: return
        self.paused=not self.paused
        if self.paused:
            if self.drive_after: self.root.after_cancel(self.drive_after); self.drive_after=None
            self.pause_button.configure(text="Resume"); self.hint.set("Vehicle paused.")
        else:
            self.pause_button.configure(text="Pause"); self.hint.set("Vehicle moving."); self.drive_after=self.root.after(1,self._drive_step)

    def _stop_drive(self):
        if self.drive_after:
            try: self.root.after_cancel(self.drive_after)
            except tk.TclError: pass
        self.drive_after=None; self.paused=False; self.driving=False
        if hasattr(self,"pause_button"): self.pause_button.configure(state="disabled",text="Pause")
        if hasattr(self,"drive_button"): self.drive_button.configure(state="normal")
    def _show_result(self, failed, message):
        bg="#fff1f1" if failed else "#edf8f1"; fg="#7a2525" if failed else "#1f5535"
        self.banner.configure(bg=bg,highlightbackground="#a43b3b" if failed else "#2f7d4d")
        for child in self.banner.winfo_children(): child.destroy()
        tk.Label(self.banner,text=message,bg=bg,fg=fg,font=("Segoe UI",11,"bold"),anchor="w").pack(side="left",fill="x",expand=True,padx=12,pady=10)
        if failed:
            tk.Button(self.banner,text="Restart",command=self._restart,takefocus=True).pack(side="right",padx=10,pady=7)
        else:
            tk.Button(self.banner,text="Drive another vehicle",command=self._another,takefocus=True).pack(side="right",padx=10,pady=7)
        self.banner.pack(fill="x",padx=12,pady=(0,10)); self.hint.set(message)

    def _restart(self):
        self.banner.pack_forget(); self.set_mode("Build"); self.hint.set("Restarted in Build mode. The current bridge is unchanged.")

    def _another(self):
        self.banner.pack_forget(); self.position.set(44); self.set_mode("Test")
        self.hint.set("Choose another vehicle or adjust the front axle position.")


    def set_deflection_limit(self):
        initial = "" if self.deflection_limit_ft is None else str(self.deflection_limit_ft)
        value = simpledialog.askstring("Deflection limit", "Maximum deflection in feet (leave blank to clear):",
                                       initialvalue=initial, parent=self.root)
        if value is None: return
        if not value.strip():
            self.deflection_limit_ft = None
        else:
            try: number = float(value)
            except ValueError:
                messagebox.showerror("Invalid limit", "Enter a number in feet or leave the field blank.", parent=self.root); return
            if not math.isfinite(number) or number < 0:
                messagebox.showerror("Invalid limit", "The deflection limit must be a finite non-negative number.", parent=self.root); return
            self.deflection_limit_ft = number
        self.hint.set("Deflection limit saved in project settings; the truss solver does not calculate deflection.")

    def _current_loads(self):
        if self.vehicle.get() in VALIDATION_CASES:
            source = VALIDATION_CASES[self.vehicle.get()]
        else:
            front = float(self.position.get())
            source = [(front-offset, load) for offset, load in VEHICLES[self.vehicle.get()]["axles"]]
        return [{"x_ft": float(x), "load_lb": float(load)} for x, load in source]

    def save_project(self):
        path = self.project_path
        if not path:
            path = filedialog.asksaveasfilename(parent=self.root, title="Save bridge project",
                defaultextension=".wib.json", filetypes=(("Will it Break project", "*.wib.json"), ("JSON files", "*.json")))
            if not path: return
        document = {
            "format": "will-it-break-project", "version": 1,
            "beam": {"support_type": self.support_type, "span_ft": self.span_ft,
                     "section": self.section, "deflection_limit_ft": self.deflection_limit_ft,
                     "load_situation": self.vehicle.get(), "front_axle_x_ft": float(self.position.get()), "mode": self.mode,
                     "loads": self._current_loads()},
            "bridge": {"nodes": [list(n) for n in sorted(self.nodes)],
                       "members": [{"a": list(m.a), "b": list(m.b), "deck": m.deck} for m in self.members]},
        }
        try:
            with open(path, "w", encoding="utf-8") as stream: json.dump(document, stream, indent=2)
            self.project_path = path
            self.hint.set(f"Project saved to {path}.")
        except OSError as error:
            messagebox.showerror("Save failed", str(error), parent=self.root)

    def open_project(self):
        path = filedialog.askopenfilename(parent=self.root, title="Open bridge project",
            filetypes=(("Will it Break project", "*.wib.json"), ("JSON files", "*.json"), ("All files", "*.*")))
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as stream: document = json.load(stream)
            if document.get("format") != "will-it-break-project" or document.get("version") != 1:
                raise ValueError("This is not a supported Will it Break project file.")
            beam, bridge = document["beam"], document["bridge"]
            if beam["support_type"] != self.support_type or float(beam["span_ft"]) != self.span_ft or beam["section"] != self.section:
                raise ValueError("This project uses support, span, or section settings that this app does not support.")
            nodes = {tuple(map(float, pair)) for pair in bridge["nodes"]}
            members = [Member(tuple(map(float, item["a"])), tuple(map(float, item["b"])), bool(item.get("deck", False)))
                       for item in bridge["members"]]
            if not set(DECK_NODES).issubset(nodes) or any(m.a not in nodes or m.b not in nodes for m in members):
                raise ValueError("The project has invalid joints or member endpoints.")
            load_situation = beam["load_situation"]
            if load_situation not in VEHICLES and load_situation not in VALIDATION_CASES:
                raise ValueError("The project uses an unknown load situation.")
            limit = beam.get("deflection_limit_ft")
            if limit is not None and (not math.isfinite(float(limit)) or float(limit) < 0):
                raise ValueError("The project's deflection limit is invalid.")
            position = max(0.0, min(60.0, float(beam.get("front_axle_x_ft", 44.0))))
            mode = beam.get("mode", "Build")
            if mode not in ("Build", "Test"): raise ValueError("The project mode is invalid.")
            if load_situation in VALIDATION_CASES: mode = "Test"
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            messagebox.showerror("Open failed", str(error), parent=self.root); return
        self._stop_drive(); self.nodes, self.members = nodes, members
        self.vehicle.set(load_situation); self.position.set(position)
        self.deflection_limit_ft = None if limit is None else float(limit); self.project_path = path
        self.set_mode(mode)
        self._update_stats(); self._draw()
        self.hint.set(f"Project opened from {path}.")

    def export_results(self):
        if not self.last_result or not self.last_result.stable:
            messagebox.showinfo("No results", "Park or drive a stable load situation before exporting results.", parent=self.root); return
        path = filedialog.asksaveasfilename(parent=self.root, title="Export calculation results",
            defaultextension=".csv", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if not path: return
        forces = self.max_forces if self.crossing_result and self.max_forces else self.last_result.forces
        loads = self._current_loads()
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Load situation", self.vehicle.get()])
                writer.writerow(["Applied loads (x ft, lb)", "; ".join(f"{v['x_ft']:g}, {v['load_lb']:g}" for v in loads)])
                writer.writerow(["Category", "Item", "Force (lb)"])
                for name, value in self.last_result.reactions.items(): writer.writerow(["Reaction", name, value])
                for index, value in enumerate(forces or [], 1):
                    if value is not None: writer.writerow(["Member force", f"Member {index}", value])
            self.hint.set(f"Results exported to {path}.")
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self.root)


def main():
    root=tk.Tk(); BridgeApp(root); root.mainloop()

if __name__=="__main__": main()
