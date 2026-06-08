# converted from gamslib rcpsp (RCPSP, SEQ=429)
# Resource-Constrained Project Scheduling Problem, Pritsker time-indexed
# binary finishing-time formulation. Instance: PSPLIB j301_1.sm (makespan=43).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "j1|r1": value → (j1, r1): value).
# The 'pred' set members are pipe strings "i|j"; we split them to (i, j) tuples.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── primary data ──────────────────────────────────────────────────────────────
jobs = list(data["j"])                  # jobs, topologically ordered j1..jN
periods = list(data["t"])               # time periods t1..tT
resources = list(data["r"])             # renewable resources r1..rR
pred_pairs = [tuple(p.split("|")) for p in data["pred"]]  # (i, j): i precedes j

durations = {j: int(round(float(v))) for j, v in dict(data["durations"]).items()}
demands = {(jk[0], jk[1]) if isinstance(jk, tuple) else tuple(jk.split("|")): float(v)
           for jk, v in dict(data["demands"]).items()}
capacities = {r: float(v) for r, v in dict(data["capacities"]).items()}

# 1-based positional order, mirroring GAMS ord()
ordj = {j: ix + 1 for ix, j in enumerate(jobs)}
ordt = {t: ix + 1 for ix, t in enumerate(periods)}
cardj = len(jobs)
cardt = len(periods)
predset = set(pred_pairs)

# ── derived sets / parameters (replicate GAMS preprocessing) ──────────────────
# actual jobs: all but the first (super-source) and last (sink) dummy jobs
actual = [j for j in jobs if 1 < ordj[j] < cardj]
# lastJob: the single sink job (highest order)
lastJob = [j for j in jobs if ordj[j] == cardj]

# Forward pass: earliest finishing times
# efts(j1)=1; loop((j,i)$pred(i,j): efts(j)=max(efts(j), efts(i)+durations(j))
efts = {j: 0 for j in jobs}
efts[jobs[0]] = 1
for j in jobs:               # outer loop over successors j (ascending order)
    for i in jobs:           # inner loop over predecessors i (ascending order)
        if (i, j) in predset:
            efts[j] = max(efts[j], efts[i] + durations[j])

# Backward pass: latest finishing times
# lfts(j)=cardT; for it=cardj downto 1: loop i ord(i)=it: for jt=cardj downto 1:
#   loop j ord(j)=jt and pred(i,j): lfts(i)=min(lfts(i), lfts(j)-durations(j))
lfts = {j: cardt for j in jobs}
for it in range(cardj, 0, -1):
    i = jobs[it - 1]
    for jt in range(cardj, 0, -1):
        j = jobs[jt - 1]
        if (i, j) in predset:
            lfts[i] = min(lfts[i], lfts[j] - durations[j])

# Time window: tw(j,t) iff efts(j) <= ord(t) <= lfts(j)
tw = {j: [t for t in periods if efts[j] <= ordt[t] <= lfts[j]] for j in jobs}
tw_set = {(j, t) for j in jobs for t in tw[j]}

# Finish window: fw(j,t,tau) iff ord(tau)>=ord(t) and
#   ord(tau)<=ord(t)+durations(j)-1 and tw(j,tau)
# i.e. if job j is active in period t, the periods tau in which it can finish.
fw = {(j, t): [tau for tau in periods
               if ordt[tau] >= ordt[t]
               and ordt[tau] <= ordt[t] + durations[j] - 1
               and (j, tau) in tw_set]
      for j in jobs for t in periods}

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Resource-Constrained Project Scheduling (RCPSP) - minimize makespan")

# Sets
model.j = pyo.Set(initialize=jobs, ordered=True, doc="Jobs (topologically ordered)")
model.t = pyo.Set(initialize=periods, ordered=True, doc="Time periods")
model.r = pyo.Set(initialize=resources, ordered=True, doc="Renewable resources")
model.pred = pyo.Set(dimen=2, initialize=pred_pairs, doc="Precedence: i precedes j")

# Parameters
model.durations = pyo.Param(
    model.j, initialize=durations, mutable=True, within=pyo.NonNegativeReals,
    doc="Job durations (processing times)",
)
model.demands = pyo.Param(
    model.j, model.r, initialize=demands, mutable=True, within=pyo.NonNegativeReals,
    doc="Resource units of r required by job j while active",
)
model.capacities = pyo.Param(
    model.r, initialize=capacities, mutable=True, within=pyo.NonNegativeReals,
    doc="Renewable resource capacity available in every period",
)

# Variables
# x[j,t] = 1 iff job j finishes in period t. Defined only on the time window tw.
tw_index = [(j, t) for j in jobs for t in tw[j]]
model.x_index = pyo.Set(dimen=2, initialize=tw_index, doc="(j,t) in finish-time window")
model.x = pyo.Var(model.x_index, domain=pyo.Binary, doc="1 iff job j finishes in period t")

model.makespan = pyo.Var(domain=pyo.NonNegativeReals, doc="Total project duration")

# Constraints
def objective_rule(model):
    # makespan = finishing time of the last (sink) job
    return model.makespan == sum(
        model.x[j, t] * (ordt[t] - 1)
        for j in lastJob for t in tw[j]
    )
model.objective = pyo.Constraint(rule=objective_rule, doc="Makespan = finish of last job")

def precedence_rule(model, i, j):
    return (sum(ordt[t] * model.x[i, t] for t in tw[i])
            <= sum(ordt[t] * model.x[j, t] for t in tw[j]) - model.durations[j])
model.precedence = pyo.Constraint(model.pred, rule=precedence_rule, doc="Enforce job precedences")

def resusage_rule(model, r, t):
    return (sum(model.demands[j, r] * sum(model.x[j, tau] for tau in fw[j, t])
               for j in actual)
            <= model.capacities[r])
model.resusage = pyo.Constraint(model.r, model.t, rule=resusage_rule, doc="Renewable resource limits")

def once_rule(model, j):
    return sum(model.x[j, t] for t in tw[j]) == 1
model.once = pyo.Constraint(model.j, rule=once_rule, doc="Each job scheduled exactly once")

# Objective
model.obj = pyo.Objective(expr=model.makespan, sense=pyo.minimize, doc="Minimize makespan")
