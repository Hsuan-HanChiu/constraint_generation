# converted from gamslib epscm (EPSCM, SEQ=319)
# eps-Constraint Method for Multiobjective Optimization.
#
# NOTE: The original GAMS model is the eps-constraint METHOD: it solves the same
# LP ~100 times, sweeping a grid of epsilon bounds on the secondary objectives to
# trace the Pareto front. We DROP that grid/payoff-table loop and build ONE single
# deterministic LP: MINIMIZE the PRIMARY objective (cost, = first element k1 of k),
# holding the two SECONDARY objectives as fixed eps-constraints
#   z[CO2emission] <= eps_co2   (a minimization objective, eps as an upper bound)
#   z[endogenous]  >= eps_es    (a maximization objective, eps as a lower bound)
# at the first grid point (g0) eps values from the payoff table
#   eps_co2 = 62460 (CO2 max from payoff table), eps_es = 27000 (endogenous min).
# These are the loosest eps bounds, so the cost minimum is the unconstrained
# cost-optimal point = payoff/Pareto solution s1 (cost = 3,075,000).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="eps-Constraint power generation: minimize cost with CO2/endogenous as eps-constraints")

# Sets
model.p = pyo.Set(initialize=data["p"], doc="Power generation units")
model.i = pyo.Set(initialize=data["i"], doc="Load areas")
model.pi = pyo.Set(
    dimen=2,
    initialize=data["pi"],
    doc="Availability of unit p for load type i",
)
model.es = pyo.Set(initialize=data["es"], within=model.p, doc="Endogenous sources")

# Parameters
model.ad = pyo.Param(initialize=data["ad"], mutable=True, doc="Annual demand in GWh")
model.df = pyo.Param(model.i, initialize=data["df"], mutable=True, doc="Demand fraction per load type")
model.capacity = pyo.Param(model.p, initialize=data["capacity"], mutable=True, doc="Capacity [GWh]")
model.cost = pyo.Param(model.p, initialize=data["cost"], mutable=True, doc="Cost [$/MWh]")
model.co2 = pyo.Param(model.p, initialize=data["co2"], mutable=True, doc="CO2 emission [t/MWh]")

# eps-constraint bounds (representative first grid point, g0)
model.eps_co2 = pyo.Param(initialize=data["eps_co2"], mutable=True, doc="Upper bound on CO2 emissions (eps-constraint)")
model.eps_es = pyo.Param(initialize=data["eps_es"], mutable=True, doc="Lower bound on endogenous sources (eps-constraint)")

# Variables
model.x = pyo.Var(model.pi, domain=pyo.NonNegativeReals, doc="Production level of unit in load area in GWh")
model.z_cost = pyo.Var(domain=pyo.Reals, doc="Cost objective value")
model.z_co2 = pyo.Var(domain=pyo.Reals, doc="CO2 emission objective value")
model.z_es = pyo.Var(domain=pyo.Reals, doc="Endogenous sources objective value")

# Objective accounting constraints
def objcost_rule(model):
    return sum(model.cost[p] * model.x[p, i] for (p, i) in model.pi) == model.z_cost
model.objcost = pyo.Constraint(rule=objcost_rule, doc="Cost accounting")

def objco2_rule(model):
    return sum(model.co2[p] * model.x[p, i] for (p, i) in model.pi) == model.z_co2
model.objco2 = pyo.Constraint(rule=objco2_rule, doc="CO2 accounting")

def objes_rule(model):
    return sum(model.x[p, i] for (p, i) in model.pi if p in model.es) == model.z_es
model.objes = pyo.Constraint(rule=objes_rule, doc="Endogenous sources accounting")

# Physical constraints
def defcap_rule(model, p):
    return sum(model.x[pp, i] for (pp, i) in model.pi if pp == p) <= model.capacity[p]
model.defcap = pyo.Constraint(model.p, rule=defcap_rule, doc="Capacity constraint")

def defdem_rule(model, i):
    return sum(model.x[p, ii] for (p, ii) in model.pi if ii == i) >= model.ad * model.df[i]
model.defdem = pyo.Constraint(model.i, rule=defdem_rule, doc="Demand satisfaction")

# eps-constraints on the secondary objectives
model.eps_con_co2 = pyo.Constraint(expr=model.z_co2 <= model.eps_co2, doc="CO2 eps-constraint (upper bound)")
model.eps_con_es = pyo.Constraint(expr=model.z_es >= model.eps_es, doc="Endogenous eps-constraint (lower bound)")

# Objective: minimize cost (primary objective)
model.obj = pyo.Objective(expr=model.z_cost, sense=pyo.minimize, doc="Minimize production cost")
