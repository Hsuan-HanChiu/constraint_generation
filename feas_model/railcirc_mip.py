# converted from gamslib railcirc (RAILCIRC, SEQ=220)
# Minimum Circulation of Railway Stock (Schrijver, CWI Quarterly 3, 1993).
# Primary model: the full two-traintype MIP (GAMS line 247, tu1+tu2, maxcars=15).
# The scenario re-solves (tu1-only, tu2-only) are dropped.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "s|t|ss|tt|c" → (s,t,ss,tt,c)).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Minimum Circulation of Railway Stock")

# =====================
# Sets (from data)
# =====================
tu_list = list(data["tu"])          # train unit types
class_list = list(data["c"])        # service classes: First, Second
station_list = list(data["s"])      # stations

# =====================
# Raw parameter data
# =====================
# trainunitdata keyed (tu, field) where field in {First, Second, NumberCars, Cost}
tud_raw = data["trainunitdata"]
# aggregated in-service demand keyed (s, t, ss, tt, class)  == sum(z, timetable(z,is,c))
dem_raw = data["demand_data"]

# =====================
# Build the timetable graph (mirrors the GAMS loops, lines 156-179)
# =====================
# In-service arcs: distinct (s,t,ss,tt) appearing in the timetable demand data.
is_arcs = sorted({(s, t, ss, tt) for (s, t, ss, tt, c) in dem_raw.keys()})

# Station timetable events ste(s,t): every (s,t) and (ss,tt) on an in-service arc.
ste = set()
for (s, t, ss, tt) in is_arcs:
    ste.add((s, t))
    ste.add((ss, tt))
ste_list = sorted(ste)

# Per station: sort events by time, add consecutive in-station ("waiting") arcs,
# and one overnight arc from the day's last event back to its first event.
g = set(is_arcs)
on_arcs = set()
for s in station_list:
    events = sorted([(st, ti) for (st, ti) in ste if st == s], key=lambda e: int(e[1]))
    if not events:
        continue
    for a, b in zip(events[:-1], events[1:]):
        g.add((a[0], a[1], b[0], b[1]))          # in-station arc
    first, last = events[0], events[-1]
    on_arcs.add((last[0], last[1], first[0], first[1]))
    g.add((last[0], last[1], first[0], first[1]))  # overnight arc

g_list = sorted(g)
on_list = sorted(on_arcs)

model.tu = pyo.Set(initialize=tu_list, doc="train unit types")
model.c = pyo.Set(initialize=class_list, doc="service classes")
model.s = pyo.Set(initialize=station_list, doc="stations")
model.g = pyo.Set(initialize=g_list, dimen=4, doc="timetable graph arcs (s,t,ss,tt)")
model.is_ = pyo.Set(initialize=is_arcs, dimen=4, doc="in-service arcs")
model.on = pyo.Set(initialize=on_list, dimen=4, doc="overnight arcs")
model.ste = pyo.Set(initialize=ste_list, dimen=2, doc="station timetable events")

# =====================
# Parameters
# =====================
def first_init(model, tu):
    return float(tud_raw[(tu, "First")])
model.first_cap = pyo.Param(model.tu, initialize=first_init, mutable=True,
                            doc="First class seats per train unit")

def second_init(model, tu):
    return float(tud_raw[(tu, "Second")])
model.second_cap = pyo.Param(model.tu, initialize=second_init, mutable=True,
                             doc="Second class seats per train unit")

def cars_init(model, tu):
    return float(tud_raw[(tu, "NumberCars")])
model.numcars = pyo.Param(model.tu, initialize=cars_init, mutable=True,
                          doc="Number of cars per train unit")

def cost_init(model, tu):
    return float(tud_raw[(tu, "Cost")])
model.cost = pyo.Param(model.tu, initialize=cost_init, mutable=True,
                       doc="Cost per stabled train unit")

# Per-class seat capacity, indexed (tu, class), for the demand constraint.
def seats_init(model, tu, c):
    return float(tud_raw[(tu, c)])
model.seats = pyo.Param(model.tu, model.c, initialize=seats_init, mutable=True,
                        doc="seats of class c per train unit tu")

# Aggregated demand on each in-service arc per class.
def demand_init(model, s, t, ss, tt, c):
    return float(dem_raw[(s, t, ss, tt, c)])
model.demand_param = pyo.Param(model.is_, model.c, initialize=demand_init, mutable=True,
                               doc="seat demand on in-service arc, by class")

model.maxcars = pyo.Param(initialize=float(data["maxcars"]), mutable=True,
                          doc="maximum number of cars on a track")

# =====================
# Variables
# =====================
model.f = pyo.Var(model.tu, model.g, domain=pyo.NonNegativeIntegers,
                  doc="flow of train units on each graph arc")
model.obj_var = pyo.Var(domain=pyo.Reals, doc="objective variable (total stabling cost)")

# =====================
# Constraints
# =====================
# circulation(tu, ste): inflow == outflow at each station timetable event.
def circulation_rule(model, tu, s, t):
    inflow = sum(model.f[tu, a] for a in g_list if a[2] == s and a[3] == t)
    outflow = sum(model.f[tu, a] for a in g_list if a[0] == s and a[1] == t)
    return inflow == outflow
model.circulation = pyo.Constraint(model.tu, model.ste, rule=circulation_rule,
                                   doc="inflow equals outflow at each node")

# demand(is, c): seat demand must be met by deployed train-unit capacity.
def demand_rule(model, s, t, ss, tt, c):
    return model.demand_param[s, t, ss, tt, c] <= sum(
        model.f[tu, s, t, ss, tt] * model.seats[tu, c] for tu in model.tu)
model.demand = pyo.Constraint(model.is_, model.c, rule=demand_rule,
                              doc="demand of first and second class seats")

# defmaxcars(is): cars on an in-service arc must not exceed track capacity.
def maxcars_rule(model, s, t, ss, tt):
    return sum(model.f[tu, s, t, ss, tt] * model.numcars[tu] for tu in model.tu) <= model.maxcars
model.defmaxcars = pyo.Constraint(model.is_, rule=maxcars_rule,
                                  doc="maximum cars on in-service arcs")

# defobj: objective = total cost of train units stabled on overnight arcs.
def defobj_rule(model):
    return model.obj_var == sum(
        model.f[tu, a] * model.cost[tu] for tu in model.tu for a in on_list)
model.defobj = pyo.Constraint(rule=defobj_rule, doc="objective function")

# =====================
# Objective
# =====================
model.obj = pyo.Objective(expr=model.obj_var, sense=pyo.minimize,
                          doc="minimize total stabling cost")
