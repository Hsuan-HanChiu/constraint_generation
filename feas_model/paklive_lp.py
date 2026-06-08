# converted from models/paklive_lp.py
import json
import pyomo.environ as pe
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pe.ConcreteModel()

# Sets
model.C = pe.Set(initialize=data["c"], doc="crops")
model.H = pe.Set(initialize=data["h"], doc="livestock types")
model.F = pe.Set(initialize=data["f"], doc="seasonal inputs")
model.N = pe.Set(initialize=data["n"], doc="nutrients")
model.DP = pe.Set(initialize=data["dp"], doc="draftpower rows")
model.TA = pe.Set(initialize=data["ta"], doc="seasons and annual")
model.T = pe.Set(initialize=data["t"], ordered=True, doc="seasons")

# Row labels for cinput/linput
cinput_data = data["cinput"]
row_labels = sorted({k[0] for k in cinput_data.keys()})
model.R = pe.Set(initialize=row_labels, doc="IO rows")

# Scalar parameters
model.fsize = pe.Param(initialize=data["fsize"], mutable=True, doc="farm size (acres)")
model.watercost = pe.Param(initialize=data["watercost"], mutable=True,
                       doc="water cost (rs/inch)")
model.laborcost = pe.Param(initialize=data["laborcost"], mutable=True,
                       doc="labor cost (rs/man-day)")
model.maxcredit = pe.Param(initialize=data["maxcredit"], mutable=True,
                       doc="max annual credit (rs)")
model.lrr = pe.Param(initialize=data["lrr"], mutable=True,
                 doc="livestock reproduction ratio")
model.wpup = pe.Param(initialize=data["wpup"], mutable=True,
                  doc="max purchased water (inches)")
model.draftcost = pe.Param(initialize=data["draftcost"], mutable=True,
                       doc="draftpower cost (rs/workday)")

# Indexed parameters
model.bullockr = pe.Param(
    model.C,
    initialize=data["bullockr"],
    default=0.0,
    mutable=True,
    doc="bullock requirements (work-days)",
)
model.bullocka = pe.Param(
    model.H,
    initialize=data["bullocka"],
    default=0.0,
    mutable=True,
    doc="bullock availability (work-days)",
)
model.waf = pe.Param(
    model.T,
    initialize=data["waf"],
    mutable=True,
    doc="free water per acre (inches)",
)
model.rationcost = pe.Param(
    model.N,
    initialize=data["rationcost"],
    mutable=True,
    doc="ration cost (rs/kg)",
)
model.cprice = pe.Param(
    model.C,
    initialize=data["cprice"],
    default=0.0,
    mutable=True,
    doc="crop price (rs/maund)",
)
model.gmargin = pe.Param(
    model.H,
    initialize=data["gmargin"],
    default=0.0,
    mutable=True,
    doc="livestock gross margin (rs)",
)
model.eff = pe.Param(
    model.N,
    initialize=data["eff"],
    default=0.0,
    mutable=True,
    doc="storage efficiency",
)
model.maxflab = pe.Param(
    model.T,
    initialize=data["maxflab"],
    mutable=True,
    doc="family labor (man-days)",
)
model.cinput = pe.Param(
    model.R,
    model.TA,
    model.C,
    initialize=data["cinput"],
    default=0.0,
    mutable=True,
    doc="crop IO matrix",
)
model.linput = pe.Param(
    model.R,
    model.TA,
    model.H,
    initialize=data["linput"],
    default=0.0,
    mutable=True,
    doc="livestock IO matrix",
)

# Derived parameters
def watavail_init(model, t):
    return model.fsize * model.waf[t]

model.watavail = pe.Param(
    model.T,
    initialize=watavail_init,
    mutable=True,
    doc="on-farm free water (inches)",
)

def crev_init(model, c):
    return -model.cprice[c] * model.cinput["yield", "annual", c]

model.crev = pe.Param(
    model.C,
    initialize=crev_init,
    mutable=True,
    doc="crop revenue (rs/acre)",
)

# Previous season map for fodder transfer
season_list = list(data["t"])
prev_t_map = {}
for i, t in enumerate(season_list):
    prev_t_map[t] = season_list[i - 1] if i > 0 else None
model._prev_t = prev_t_map

# Variables
model.xcrop = pe.Var(model.C, domain=pe.NonNegativeReals,
                 doc="cropping activities (acres)")
model.wpurchase = pe.Var(model.T, domain=pe.NonNegativeReals,
                     doc="water purchased (inches)")
model.xrations = pe.Var(model.N, model.T, domain=pe.NonNegativeReals,
                    doc="purchased rations (kg)")
model.xlabor = pe.Var(model.T, domain=pe.NonNegativeReals,
                  doc="hired labor (man-days)")
model.xtransf = pe.Var(model.N, model.T, domain=pe.NonNegativeReals,
                   doc="fodder transfer (kg)")
model.dhire = pe.Var(domain=pe.NonNegativeReals,
                 doc="hired draftpower (work-days)")
model.xlivestk = pe.Var(model.H, domain=pe.NonNegativeReals,
                    doc="livestock production (animals)")

model.rev = pe.Var(domain=pe.Reals, doc="total revenue (rs)")
model.lcost = pe.Var(domain=pe.Reals, doc="labor cost (rs)")
model.dcost = pe.Var(domain=pe.Reals, doc="draftpower cost (rs)")
model.wcost = pe.Var(domain=pe.Reals, doc="water cost (rs)")
model.rcost = pe.Var(domain=pe.Reals, doc="ration cost (rs)")
model.net_return = pe.Var(domain=pe.Reals, doc="net return (rs)")

# Variable bounds
if "sugar" in model.C:
    model.xcrop["sugar"].setub(2.0)
for t in model.T:
    model.wpurchase[t].setub(model.wpup)

# Revenue and cost definitions
def totalrev_rule(model):
    return model.rev == sum(model.crev[c] * model.xcrop[c] for c in model.C) + sum(
        model.gmargin[h] * model.xlivestk[h] for h in model.H
    )

model.totalrev = pe.Constraint(rule=totalrev_rule,
                           doc="total revenue (rs)")

def costdraft_rule(model):
    return model.dcost == model.draftcost * model.dhire

model.costdraft = pe.Constraint(rule=costdraft_rule,
                            doc="draftpower cost (rs)")

def costlabor_rule(model):
    return model.lcost == model.laborcost * sum(model.xlabor[t] for t in model.T)

model.costlabor = pe.Constraint(rule=costlabor_rule,
                            doc="labor cost (rs)")

def costwater_rule(model):
    return model.wcost == model.watercost * sum(model.wpurchase[t] for t in model.T)

model.costwater = pe.Constraint(rule=costwater_rule,
                            doc="water cost (rs)")

def costrat_rule(model):
    return model.rcost == sum(
        model.rationcost[n] * sum(model.xrations[n, t] for t in model.T) for n in model.N
    )

model.costrat = pe.Constraint(rule=costrat_rule,
                          doc="ration cost (rs)")

# constraints
def land_rule(model, t):
    return sum(model.cinput["landuse", t, c] * model.xcrop[c] for c in model.C) <= model.fsize

model.land = pe.Constraint(model.T, rule=land_rule,
                       doc="land use (acres)")

def water_rule(model, t):
    # NOTE: vars (wpurchase) moved to LHS so watavail[t] stays on con.upper —
    # exposes watavail as a SENSITIVITY-targetable RHS Param. Mathematically
    # identical to `LHS <= watavail + wpurchase`.
    return (
        sum(model.cinput["irrwat", t, c] * model.xcrop[c] for c in model.C)
        - model.wpurchase[t]
        <= model.watavail[t]
    )

model.water = pe.Constraint(model.T, rule=water_rule,
                        doc="irrigation water (inches)")

def labor_rule(model, t):
    # NOTE: vars (xlabor) moved to LHS so maxflab[t] stays on con.upper —
    # exposes maxflab as a SENSITIVITY-targetable RHS Param. Mathematically
    # identical to `LHS <= maxflab + xlabor`.
    return (
        sum(model.cinput["labor", t, c] * model.xcrop[c] for c in model.C)
        + sum(model.linput["labor", t, h] * model.xlivestk[h] for h in model.H)
        - model.xlabor[t]
        <= model.maxflab[t]
    )

model.labor = pe.Constraint(model.T, rule=labor_rule,
                        doc="labor balance (man-days)")

def draft_rule(model, dp, t):
    return sum(model.cinput[dp, t, c] * model.xcrop[c] for c in model.C) <= -sum(
        model.linput[dp, t, h] * model.xlivestk[h] for h in model.H
    )

model.draft = pe.Constraint(model.DP, model.T, rule=draft_rule,
                        doc="draftpower balance (work-days)")

def bullock_rule(model):
    return sum(model.bullockr[c] * model.xcrop[c] for c in model.C) <= sum(
        model.bullocka[h] * model.xlivestk[h] for h in model.H
    ) + model.dhire

model.bullock = pe.Constraint(rule=bullock_rule,
                          doc="bullock requirement")

def credit_rule(model):
    return (
        sum(model.cinput["credit", "annual", c] * model.xcrop[c] for c in model.C)
        + sum(model.linput["credit", "annual", h] * model.xlivestk[h] for h in model.H)
        + model.rcost
        + model.lcost
        + model.wcost
        + model.dcost
        <= model.maxcredit
    )

model.credit = pe.Constraint(rule=credit_rule,
                         doc="credit limit (rs)")

def nutbal_rule(model, n, t):
    prev_t = model._prev_t.get(t, None)
    transf = 0.0
    if prev_t is not None:
        transf = model.eff[n] * model.xtransf[n, prev_t]
    return (
        -sum(model.cinput[n, t, c] * model.xcrop[c] for c in model.C)
        + transf
        + model.xrations[n, t]
        >= sum(model.linput[n, t, h] * model.xlivestk[h] for h in model.H)
    )

model.nutbal = pe.Constraint(model.N, model.T, rule=nutbal_rule,
                         doc="nutrient balance (kg)")

# Net return definition
def net_return_rule(model):
    return model.net_return == model.rev - model.lcost - model.wcost - model.rcost - model.dcost

model.obj_balance = pe.Constraint(rule=net_return_rule,
                              doc="net return definition")

# Objective
model.obj = pe.Objective(expr=model.net_return,
                     sense=pe.maximize,
                     doc="maximize net return")
