# converted from gamslib openpit (OPENPIT, SEQ=309)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "p1|s1": value → (p1, s1): value).
#
# nev/evo/demand/delta are extracted from the GAMS uniform()/sign() data
# generator (deterministic, GAMS-seeded RNG) so this instance reproduces the
# reference objective exactly.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Dynamic Open Pit Mining Extraction - multi-period block precedence")

# =====================
# Sets (ordered)
# =====================
t_list = list(data["t"])  # extraction periods
s_list = list(data["s"])  # extraction segments
p_list = list(data["p"])  # pits

model.t = pyo.Set(initialize=t_list, ordered=True, doc="extraction periods")
model.s = pyo.Set(initialize=s_list, ordered=True, doc="extraction segments")
model.p = pyo.Set(initialize=p_list, ordered=True, doc="pits")

# 1-based ordinal helpers (GAMS ord())
t_ord = {tt: i + 1 for i, tt in enumerate(t_list)}
s_ord = {ss: i + 1 for i, ss in enumerate(s_list)}

# =====================
# Parameters
# =====================
nev_raw = data["nev"]
evo_raw = data["evo"]
demand_raw = data["demand"]
delta_raw = data["delta"]

model.nev = pyo.Param(
    model.p, model.s,
    initialize=lambda m, p, s: float(nev_raw[(p, s)]),
    mutable=True, within=pyo.Reals,
    doc="net extraction benefit",
)
model.evo = pyo.Param(
    model.p, model.s,
    initialize=lambda m, p, s: float(evo_raw[(p, s)]),
    mutable=True, within=pyo.NonNegativeReals,
    doc="extraction volume",
)
model.demand = pyo.Param(
    model.t,
    initialize=lambda m, t: float(demand_raw[t]),
    mutable=True, within=pyo.NonNegativeReals,
    doc="product demand",
)
model.delta = pyo.Param(
    model.t,
    initialize=lambda m, t: float(delta_raw[t]),
    mutable=True, within=pyo.NonNegativeReals,
    doc="discount factor",
)

# =====================
# Variables
# =====================
model.b = pyo.Var(model.p, model.s, model.t, domain=pyo.Binary,
                  doc="segment can be extracted")
model.e = pyo.Var(model.p, model.s, model.t, domain=pyo.Binary,
                  doc="last extracted segment and start")
model.open = pyo.Var(model.p, model.s, domain=pyo.Binary,
                     doc="segments activated")

# Integer variable: period of last segment (= ord of last extracted segment)
model.ej = pyo.Var(model.p, model.t, domain=pyo.Integers, bounds=(0, len(s_list)),
                   doc="period of last segment")

# Positive variables
model.out = pyo.Var(model.p, model.s, model.t, domain=pyo.NonNegativeReals,
                    doc="extraction level")


def pout_bounds(m, p, t):
    # pout.up(p,t) = 0.8*demand(t)
    return (0.0, 0.8 * float(demand_raw[t]))


model.pout = pyo.Var(model.p, model.t, domain=pyo.NonNegativeReals, bounds=pout_bounds,
                     doc="pit output")

model.obj_var = pyo.Var(domain=pyo.Reals, doc="total discounted net income")

# =====================
# Constraints
# =====================

# eone(p,t).. sum(s, e(p,s,t)) =e= 1;
def eone_rule(m, p, t):
    return sum(m.e[p, s, t] for s in m.s) == 1

model.eone = pyo.Constraint(model.p, model.t, rule=eone_rule,
                            doc="extraction sequence ends only once")


# etwo(p,t).. ej(p,t) =e= sum(s, ord(s)*e(p,s,t));
def etwo_rule(m, p, t):
    return m.ej[p, t] == sum(s_ord[s] * m.e[p, s, t] for s in m.s)

model.etwo = pyo.Constraint(model.p, model.t, rule=etwo_rule,
                            doc="extraction ending sequence")


# ethree(p,t-1).. ej(p,t-1) =l= ej(p,t);  (defined for consecutive period pairs)
def ethree_rule(m, p, t):
    i = t_ord[t]
    if i == len(t_list):  # no t+1; equation undefined for last period as t-1
        return pyo.Constraint.Skip
    t_next = t_list[i]  # i is 1-based ord => list index i is the next element
    return m.ej[p, t] <= m.ej[p, t_next]

model.ethree = pyo.Constraint(model.p, model.t, rule=ethree_rule,
                              doc="sequencing of end start")


# brun(p,s,t).. b(p,s,t) =e= b(p,s-1,t) - e(p,s-1,t) + e(p,s,t-1)
#                            + (ord(t)=1 and ord(s)=1);
def brun_rule(m, p, s, t):
    si = s_ord[s]
    ti = t_ord[t]
    rhs = 0
    if si > 1:  # s-1 exists
        s_prev = s_list[si - 2]
        rhs += m.b[p, s_prev, t] - m.e[p, s_prev, t]
    if ti > 1:  # t-1 exists
        t_prev = t_list[ti - 2]
        rhs += m.e[p, s, t_prev]
    if ti == 1 and si == 1:
        rhs += 1
    return m.b[p, s, t] == rhs

model.brun = pyo.Constraint(model.p, model.s, model.t, rule=brun_rule,
                            doc="define staircase for B")


# defpout(p,t).. pout(p,t) =e= sum(s, out(p,s,t));
def defpout_rule(m, p, t):
    return m.pout[p, t] == sum(m.out[p, s, t] for s in m.s)

model.defpout = pyo.Constraint(model.p, model.t, rule=defpout_rule,
                               doc="define pit output")


# dem(t).. sum(p, pout(p,t)) =e= demand(t);
def dem_rule(m, t):
    return sum(m.pout[p, t] for p in m.p) == m.demand[t]

model.dem = pyo.Constraint(model.t, rule=dem_rule, doc="total demand")


# opendef(p,s,t).. open(p,s) =g= b(p,s,t);
def opendef_rule(m, p, s, t):
    return m.open[p, s] >= m.b[p, s, t]

model.opendef = pyo.Constraint(model.p, model.s, model.t, rule=opendef_rule,
                               doc="set open to one")


# openlow(p,s).. open(p,s) =l= sum(t, b(p,s,t));
def openlow_rule(m, p, s):
    return m.open[p, s] <= sum(m.b[p, s, t] for t in m.t)

model.openlow = pyo.Constraint(model.p, model.s, rule=openlow_rule,
                               doc="set open to zero")


# outlim(p,s,t).. out(p,s,t) =l= evo(p,s)*b(p,s,t);
def outlim_rule(m, p, s, t):
    return m.out[p, s, t] <= m.evo[p, s] * m.b[p, s, t]

model.outlim = pyo.Constraint(model.p, model.s, model.t, rule=outlim_rule,
                              doc="extraction limit")


# outall(p,s).. sum(t, out(p,s,t)) =g= evo(p,s)*open(p,s+1);  (open(p,s51)=0)
def outall_rule(m, p, s):
    si = s_ord[s]
    if si == len(s_list):  # s+1 does not exist => open = 0 => rhs = 0
        rhs = 0
    else:
        s_next = s_list[si]  # si is 1-based ord => list index si is next element
        rhs = m.evo[p, s] * m.open[p, s_next]
    return sum(m.out[p, s, t] for t in m.t) >= rhs

model.outall = pyo.Constraint(model.p, model.s, rule=outall_rule,
                              doc="force complete extraction except last one")


# outmax(p,s).. sum(t, out(p,s,t)) =l= evo(p,s)*open(p,s);
def outmax_rule(m, p, s):
    return sum(m.out[p, s, t] for t in m.t) <= m.evo[p, s] * m.open[p, s]

model.outmax = pyo.Constraint(model.p, model.s, rule=outmax_rule,
                              doc="total extraction limit")


# defobj.. obj =e= sum((p,s,t), delta(t)*nev(p,s)*out(p,s,t));
def defobj_rule(m):
    return m.obj_var == sum(
        m.delta[t] * m.nev[p, s] * m.out[p, s, t]
        for p in m.p for s in m.s for t in m.t
    )

model.defobj = pyo.Constraint(rule=defobj_rule, doc="define objective")

# =====================
# Objective
# =====================
model.obj = pyo.Objective(expr=model.obj_var, sense=pyo.maximize,
                          doc="maximize total discounted net income")
