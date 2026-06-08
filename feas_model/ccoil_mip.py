# converted from models/ccoil_mip.py
# CCOIL — capacitated pipe-network (collection-coil) design MIP.
# Choose, for each directed arc, whether to lay a pipe (b) and optionally upgrade it
# to a larger type (bk), routing each node's production to the port (sink) at minimum
# installation cost. Pipe capacity/cost use an INCREMENTAL encoding: a built pipe gets
# the baseline (type-2) capacity at type-2 cost, and a single optional upgrade bk[kk]
# adds the incremental capacity/cost of type kk over type 2.
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# normalize_model_data parses pipe-keys "1|2" into integer tuples (1, 2), while
# node ids load as strings ("1"), so 2-key lookups must coerce types — see
# _get_pair_val below. (The original conversion referenced this helper without
# defining it, leaving the arc set empty and the model infeasible.)
data = globals().get("data", {})


def _get_pair_val(d, i, j):
    """Resolve d[(i, j)] across tuple, pipe-string, and int-coerced-tuple keys."""
    if not isinstance(d, dict):
        return None
    cands = [(i, j), f"{i}|{j}", (str(i), str(j))]
    try:
        cands.append((int(i), int(j)))
    except (ValueError, TypeError):
        pass
    for key in cands:
        if key in d:
            return d[key]
    return None


# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# --- Sets ---
n_list = [str(x) for x in data["n"]]
k_list = [str(x) for x in data["k"]]
model.n = Set(initialize=n_list, doc="nodes")
model.k = Set(initialize=k_list, doc="pipe types")

# upgrade types kk = all pipe types except the two baseline types 1 and 2
kk_list = [k for k in k_list if k not in ("1", "2")]
model.kk = Set(initialize=kk_list, doc="upgrade pipe types (excl. baseline 1, 2)")

# port = sink node(s) (default: last node); regnode = flow-conserving nodes (all but port)
port_list = [str(x) for x in (data.get("port") or [n_list[-1]])]
regnode_list = [n for n in n_list if n not in port_list]
model.port = Set(initialize=port_list, doc="port / sink node(s)")
model.regnode = Set(initialize=regnode_list, doc="flow-conserving nodes")
# nw = nodes that may originate a pipe (GAMS: nw(n) = yes)
model.nw = Set(initialize=list(data.get("nw") or n_list), doc="nodes that can originate a pipe")

# --- Distance + directed arc set (both orientations of every undirected edge) ---
edgedist_raw = data.get("edgedist", {}) or {}
dist_dict = {}
arc_list = []
for i in n_list:
    for j in n_list:
        if i == j:
            continue
        d_ij = (_get_pair_val(edgedist_raw, i, j) or 0.0) + (_get_pair_val(edgedist_raw, j, i) or 0.0)
        if d_ij:
            dist_dict[(i, j)] = float(d_ij)
            arc_list.append((i, j))
model.arc = Set(dimen=2, initialize=arc_list, doc="directed arcs (i, j)")

# --- Capacity / cost params (incremental encoding) ---
cap_raw = {str(k): float(v) for k, v in (data.get("cap") or {}).items()}
pipecost_raw = {str(k): float(v) for k, v in (data.get("pipecost") or {}).items()}
cap1_val = cap_raw.get("2", 0.0)
pipecost1_val = pipecost_raw.get("2", 0.0)
cap_adj = {k: (cap_raw.get(k, 0.0) - cap1_val if k in kk_list else cap_raw.get(k, 0.0)) for k in k_list}
pipecost_adj = {k: (pipecost_raw.get(k, 0.0) - pipecost1_val if k in kk_list else pipecost_raw.get(k, 0.0)) for k in k_list}

model.cap = Param(model.k, initialize=cap_adj, mutable=True, doc="incremental capacity of type k")
model.pipecost = Param(model.k, initialize=pipecost_adj, mutable=True, doc="incremental cost of type k")
model.cap1 = Param(initialize=cap1_val, mutable=True, doc="baseline (type-2) capacity")
model.pipecost1 = Param(initialize=pipecost1_val, mutable=True, doc="baseline (type-2) cost")

# production p(n) — default 0 for unlisted nodes
p_raw = {str(k): float(v) for k, v in (data.get("p") or {}).items()}
model.p = Param(model.n, initialize={n: p_raw.get(n, 0.0) for n in n_list}, mutable=True, doc="production at node")

model.dist = Param(model.n, model.n, initialize=dist_dict, default=0.0, mutable=True, doc="arc distance")

# --- Variables ---
model.bk = Var(model.arc, model.kk, domain=Binary, doc="upgrade pipe of type kk on arc")
model.b = Var(model.arc, domain=Binary, doc="build a baseline pipe on arc")
model.f = Var(model.arc, domain=NonNegativeReals, doc="flow on arc")
model.cost = Var(domain=NonNegativeReals, doc="total installation cost")

# --- Objective definition ---
def obj_rule(m):
    return m.cost == sum(
        m.dist[i, j] * (m.pipecost1 * m.b[i, j] + sum(m.pipecost[kk] * m.bk[i, j, kk] for kk in m.kk))
        for (i, j) in m.arc if i in m.nw
    )
model.obj = Constraint(rule=obj_rule, doc="definition of cost")

# --- Constraints ---
def oneout_rule(m, i):
    # non-production node ($ not p(i)): at most one outgoing pipe
    if value(m.p[i]) != 0.0:
        return Constraint.Skip
    outs = [(i, j) for (ii, j) in m.arc if ii == i]
    if not outs:
        return Constraint.Skip
    return sum(m.b[i, j] for (i, j) in outs) <= 1
model.oneout = Constraint(model.n, rule=oneout_rule, doc="<=1 out-pipe at non-production nodes")

def oneoutp_rule(m, i):
    # production node ($ p(i)): exactly one outgoing pipe
    if value(m.p[i]) == 0.0:
        return Constraint.Skip
    outs = [(i, j) for (ii, j) in m.arc if ii == i]
    if not outs:
        return Constraint.Skip
    return sum(m.b[i, j] for (i, j) in outs) == 1
model.oneoutp = Constraint(model.n, rule=oneoutp_rule, doc="exactly 1 out-pipe at production nodes")

def bal_rule(m, i):
    # flow conservation at flow-conserving nodes; the port absorbs total production
    if i not in m.regnode:
        return Constraint.Skip
    outflow = sum(m.f[i, j] for (ii, j) in m.arc if ii == i)
    inflow = sum(m.f[j, i] for (j, jj) in m.arc if jj == i)
    return m.p[i] == outflow - inflow
model.bal = Constraint(model.n, rule=bal_rule, doc="flow conservation for regnode")

def bigM_rule(m, i, j):
    # installed capacity must cover the flow (big-M link between b/bk and f)
    if i not in m.nw:
        return Constraint.Skip
    return m.cap1 * m.b[i, j] + sum(m.cap[kk] * m.bk[i, j, kk] for kk in m.kk) >= m.f[i, j]
model.bigM = Constraint(model.arc, rule=bigM_rule, doc="flow capacity (big-M)")

def defb_rule(m, i, j):
    # an upgrade can only be installed where a baseline pipe is built (=> at most one upgrade)
    if i not in m.nw:
        return Constraint.Skip
    return sum(m.bk[i, j, kk] for kk in m.kk) <= m.b[i, j]
model.defb = Constraint(model.arc, rule=defb_rule, doc="upgrade requires baseline pipe")

# Final objective: minimize total installation cost
model.min_obj = Objective(expr=model.cost, sense=minimize)
