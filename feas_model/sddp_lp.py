# converted from gamslib sddp (SDDP, SEQ=357)
#
# Source is a multi-stage stochastic water-reservoir model solved by the SDDP
# (Stochastic Dual Dynamic Programming) algorithm.  The SDDP forward/backward
# iteration is DROPPED.  What is reproduced here is the underlying deterministic
# "core" LP (model `water` in the GAMS source, the `$if set solvedet` solve):
# a full-year, 52-week / 8736-hour hydro-thermal dispatch with a single reservoir
# operated under the mean weekly inflow.  This is the deterministic-equivalent /
# extensive-form single-scenario reservoir LP.  It is a pure (large) LP.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# Sectioned JSON {sets, scalar_params, indexed_params}; pipe-keys for 2D params
# (e.g. "w1|HardCoal" → (w1, HardCoal)).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

HPW = int(round(data["hpw"]))  # hours per week (168)

# Map each hour t (t1..t8736) to its week w (w1..w52): hour i (1-based) → week
# ((i-1)//HPW)+1.  Mirrors the GAMS wt(w,t) construction.
hours = list(data["t"])
weeks = list(data["w"])


def _week_of(t_label):
    idx = int(t_label[1:]) - 1  # 0-based hour index
    return weeks[idx // HPW]


# Reservoir-level bounds: all hours share the "normal" limits except the very
# last hour t8736, which is pinned to the terminal level (GAMS resmax/resmin).
last_hour = hours[-1]

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(
    doc="Deterministic water-reservoir hydro-thermal dispatch (SDDP core LP)"
)

# Sets
model.t = pyo.Set(initialize=hours, ordered=True, doc="Hours of the year (t1..t8736)")
model.w = pyo.Set(initialize=weeks, ordered=True, doc="Weeks (w1..w52)")
model.ft = pyo.Set(initialize=list(data["ft"]), doc="Fuel/plant types")
model.pc = pyo.Set(initialize=list(data["pc"]), doc="Price columns (HardCoal, CO2)")

# Parameters (raw weekly + hourly data; mutable for OptiChat tooling)
model.demand = pyo.Param(
    model.t, initialize=data["demand"], mutable=True, within=pyo.Reals,
    doc="Power demand in hour t (MW)",
)
model.exchange = pyo.Param(
    model.t, initialize=data["exchange"], mutable=True, within=pyo.Reals,
    doc="Cross-border flow in hour t (MW)",
)
model.wInflow = pyo.Param(
    model.w, initialize=data["wInflow"], mutable=True, within=pyo.NonNegativeReals,
    doc="Inflow into the reservoir per week (MWh/week)",
)
model.wCapacity = pyo.Param(
    model.w, model.ft, initialize=data["wCapacity"], mutable=True,
    within=pyo.NonNegativeReals, doc="Plant capacity per week (MW)",
)
model.wPrices = pyo.Param(
    model.w, model.pc, initialize=data["wPrices"], mutable=True,
    within=pyo.NonNegativeReals, doc="Coal & CO2 prices per week (EUR/ton)",
)

# Scalars
model.gencost_nuclear = pyo.Param(initialize=data["gencost_nuclear"], mutable=True,
                                  doc="Nuclear generating cost (EUR/MW)")
model.gencost_co2_factor = pyo.Param(initialize=data["gencost_co2_factor"], mutable=True,
                                     doc="CO2 emission factor for hard coal")
model.gencost_denom = pyo.Param(initialize=data["gencost_denom"], mutable=True,
                                doc="Hard-coal efficiency denominator")
model.resmax_normal = pyo.Param(initialize=data["resmax_normal"], mutable=True,
                                doc="Max reservoir level, normal hours (MW)")
model.resmax_last = pyo.Param(initialize=data["resmax_last"], mutable=True,
                              doc="Max reservoir level, terminal hour (MW)")
model.resmin_normal = pyo.Param(initialize=data["resmin_normal"], mutable=True,
                                doc="Min reservoir level, normal hours (MW)")
model.resmin_last = pyo.Param(initialize=data["resmin_last"], mutable=True,
                              doc="Min reservoir level, terminal hour (MW)")
model.gap_penalty = pyo.Param(initialize=data["gap_penalty"], mutable=True,
                              doc="Penalty for gap (unserved) generation")
model.slack_penalty = pyo.Param(initialize=data["slack_penalty"], mutable=True,
                                doc="Penalty for reservoir-bound slack")


# Derived per-hour quantities (expressions over the weekly params)
def inflow_expr(m, t):
    return m.wInflow[_week_of(t)] / HPW


def capacity_expr(m, t, ft):
    return m.wCapacity[_week_of(t), ft]


def gencost_expr(m, t, ft):
    if ft == "Hydro":
        return 0.0
    if ft == "Nuclear":
        return m.gencost_nuclear
    # HardCoal
    w = _week_of(t)
    return (m.wPrices[w, "HardCoal"] + m.gencost_co2_factor * m.wPrices[w, "CO2"]) / m.gencost_denom


def resmax_expr(m, t):
    return m.resmax_last if t == last_hour else m.resmax_normal


def resmin_expr(m, t):
    return m.resmin_last if t == last_hour else m.resmin_normal


# Variables
model.GAP = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Gap generation (MW)")
model.RES = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Reservoir level end of t (MW)")
model.SPILL = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Spillage (MW)")
model.X = pyo.Var(model.t, model.ft, domain=pyo.NonNegativeReals, doc="Generation by fuel (MW)")
model.SLACKUP = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Upper reservoir slack")
model.SLACKLO = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Lower reservoir slack")


# Constraints
def cont_rule(m, t):
    # Circular previous hour (GAMS t--1): t1's predecessor is t8736.
    idx = hours.index(t)
    prev = hours[idx - 1]  # idx==0 → hours[-1] (circular)
    return m.RES[t] - m.RES[prev] + m.X[t, "Hydro"] + m.SPILL[t] == inflow_expr(m, t)


model.Cont = pyo.Constraint(model.t, rule=cont_rule, doc="Hydraulic continuity")


def demsat_rule(m, t):
    return sum(m.X[t, ft] for ft in m.ft) + m.GAP[t] >= m.demand[t] - m.exchange[t]


model.DemSat = pyo.Constraint(model.t, rule=demsat_rule, doc="Demand satisfaction")


def resup_rule(m, t):
    return -m.RES[t] + m.SLACKUP[t] >= -resmax_expr(m, t)


model.ResUp = pyo.Constraint(model.t, rule=resup_rule, doc="Max reservoir level")


def reslo_rule(m, t):
    return m.RES[t] + m.SLACKLO[t] >= resmin_expr(m, t)


model.ResLo = pyo.Constraint(model.t, rule=reslo_rule, doc="Min reservoir level")


def plantcap_rule(m, t, ft):
    return m.X[t, ft] <= capacity_expr(m, t, ft)


model.PlantCap = pyo.Constraint(model.t, model.ft, rule=plantcap_rule, doc="Plant capacity")


# Objective: generation cost + gap penalty + reservoir-slack penalty
def obj_rule(m):
    gen = sum(gencost_expr(m, t, ft) * m.X[t, ft] for t in m.t for ft in m.ft)
    pen = sum(m.gap_penalty * m.GAP[t]
              + m.slack_penalty * (m.SLACKUP[t] + m.SLACKLO[t]) for t in m.t)
    return gen + pen


model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize,
                          doc="Total generation cost + penalties (EUR)")
