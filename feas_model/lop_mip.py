# converted from gamslib lop (LOP, SEQ=221) -- single standalone "lopdt" MIP
#
# Source GAMS solves a 4-model pipeline (shortest-path LP, lopdt MIP, ilp MIP,
# evaldt LP). This file converts ONLY the standalone `lopdt` model: choose an
# integer frequency phi for each candidate line so that edge frequency
# requirements are met, maximizing the number of direct travelers (dt).
#
# The candidate line set, line->edge membership, and station ranks per line are
# derived data produced by the GAMS shortest-path solve + BFS line generation;
# they are extracted into the JSON and treated here as fixed input.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# JSON uses {sets, scalar_params, indexed_params} format with pipe-key notation
# for multi-dimensional members/params (e.g. "Ah|Apd": value → (Ah, Apd): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Railway Line Optimization (lopdt) - maximize direct travelers")

# Sets
model.station = pyo.Set(initialize=data["station"], doc="Railway stations")
model.line = pyo.Set(dimen=2, initialize=data["line"], doc="Candidate lines (station pair representing a shortest-path line)")
model.edge = pyo.Set(dimen=2, initialize=data["edge"], doc="Network edges with a line-frequency requirement")
model.odpair = pyo.Set(dimen=2, initialize=data["odpair"], doc="Origin-destination pairs with demand")
model.line_edge = pyo.Set(dimen=4, initialize=data["line_edge"], doc="Membership: edge (s2,s3) belongs to line (s,s1)")
model.rp_idx = pyo.Set(dimen=3, initialize=data["rp_idx"], doc="Membership: station st has a rank on line (s,s1)")

# Parameters
model.maxtcap = pyo.Param(initialize=data["maxtcap"], mutable=True, within=pyo.NonNegativeReals,
                          doc="Maximum train capacity (passengers)")
model.freq = pyo.Param(model.edge, initialize=data["freq"], mutable=True, within=pyo.NonNegativeReals,
                       doc="Fixed line-frequency requirement on each edge")
model.od = pyo.Param(model.odpair, initialize=data["od"], mutable=True, within=pyo.NonNegativeReals,
                     doc="Origin-destination passenger demand")
model.rp = pyo.Param(model.rp_idx, initialize=data["rp"], mutable=True, within=pyo.NonNegativeReals,
                     doc="Rank of a station within a line")

# Precompute membership groupings (fixed structure, not decision data)
_lines_on_edge = {e: [] for e in data["edge"] if isinstance(e, tuple)}
for (la, lb, ea, eb) in model.line_edge:
    _lines_on_edge.setdefault((ea, eb), []).append((la, lb))

_line_has_station = set((la, lb, st) for (la, lb, st) in model.rp_idx)

# Variables
model.phi = pyo.Var(model.line, domain=pyo.NonNegativeIntegers,
                    doc="Integer frequency assigned to each candidate line")


def _dt_bounds(model, o, d):
    return (0, pyo.value(model.od[o, d]))


model.dt = pyo.Var(model.odpair, domain=pyo.NonNegativeReals, bounds=_dt_bounds,
                   doc="Direct travelers served between an origin-destination pair")

# Constraints
def deffreqlop_rule(model, e1, e2):
    lines = _lines_on_edge.get((e1, e2), [])
    return sum(model.phi[la, lb] for (la, lb) in lines) == model.freq[e1, e2]


model.deffreqlop = pyo.Constraint(model.edge, rule=deffreqlop_rule,
                                  doc="Edge frequency = total frequency of lines using that edge")


def dtlimit_rule(model, o, d):
    serving = [(la, lb) for (la, lb) in model.line
               if (la, lb, o) in _line_has_station and (la, lb, d) in _line_has_station]
    cap = min(pyo.value(model.od[o, d]), pyo.value(model.maxtcap))
    return model.dt[o, d] <= cap * sum(model.phi[la, lb] for (la, lb) in serving)


model.dtlimit = pyo.Constraint(model.odpair, rule=dtlimit_rule,
                               doc="Direct travelers limited by capacity of lines serving both endpoints")

# Objective
model.obj = pyo.Objective(expr=sum(model.dt[o, d] for (o, d) in model.odpair),
                          sense=pyo.maximize,
                          doc="Maximize total number of direct travelers")
