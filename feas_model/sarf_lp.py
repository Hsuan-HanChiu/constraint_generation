# converted from models/sarf_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Farm Credit and Income Distribution Model (SARF): "
        "maximize farm profit under land, water, labor, and equipment constraints"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.c = Set(
    initialize=data["c"],
    doc="crop commodities"
)
model.s = Set(
    initialize=data["s"],
    doc="cropping schedules"
)
model.w = Set(
    initialize=data["w"],
    doc="irrigation / water-stress levels"
)
model.t = Set(
    initialize=data["t"],
    doc="time periods (fortnights)"
)
model.g = Set(
    initialize=data["g"],
    doc="agricultural tasks"
)
model.mn = Set(
    initialize=data["mn"],
    doc="implements and power sources (all equipment items)"
)
model.m = Set(
    initialize=data["m"],
    within=model.mn,
    doc="implements / tools"
)
model.n = Set(
    initialize=data["n"],
    within=model.mn,
    doc="power sources"
)
model.cc = Set(
    initialize=data["cc"],
    doc="cost classifications"
)

# Sets of possibilities (already precomputed in sarf.json)
model.cposs = Set(
    dimen=2,
    initialize=data["cposs"],
    doc="(crop,schedule) combinations that are feasible"
)
model.taskposs = Set(
    dimen=2,
    initialize=data["taskposs"],
    doc="(task, time) pairs where the task may occur"
)
# Manual and self-propelled power sources are unrestricted in GAMS,
# so omit them from equipposs to skip the balance constraints.
forbidden_equip = {"manual", "self-prop"}
equipposs_data = [
    pair for pair in data["equipposs"]
    if pair[0] not in forbidden_equip
]
model.equipposs = Set(
    dimen=2,
    initialize=equipposs_data,
    doc="(equipment, time) pairs where the equipment may be used"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK  (all mutable=True; default=0.0 for sparse tensors)
# ----------------------------------------------------------------------

# Operating cost per ha of task g done with implement m and power n
model.oc = Param(
    model.g,
    model.mn,
    model.mn,
    initialize=data["oc"],
    default=0.0,
    mutable=True,
    doc="operating cost (1000 rials per ha) for task g with (m,n)"
)

# Equipment availability (hours per fortnight)
model.avail = Param(
    model.mn,
    initialize=data["avail"],
    mutable=True,
    doc="equipment availability (hours per fortnight)"
)

# Expected life of equipment (years)
model.life = Param(
    model.mn,
    initialize=data["life"],
    mutable=True,
    doc="expected life of equipment (years)"
)

# Capital recovery factor
model.crf = Param(
    model.mn,
    initialize=data["crf"],
    mutable=True,
    doc="capital recovery factor"
)

# Amortized capital cost per equipment unit (1000 rials)
model.cap = Param(
    model.mn,
    initialize=data["cap"],
    mutable=True,
    doc="amortized capital cost (1000 rials per unit)"
)

# Miscellaneous input cost per ha (seed+fertilizer+pesticide+herbicide)
model.pmisc = Param(
    model.c,
    initialize=data["pmisc"],
    mutable=True,
    doc="cost of miscellaneous inputs (1000 rials per ha)"
)

# Crop output price (1000 rials per ton)
model.pcrop = Param(
    model.c,
    initialize=data["pcrop"],
    mutable=True,
    doc="price of agricultural commodities (1000 rials per ton)"
)

# Crop yields and water use along yield-water curves
model.yield_ = Param(
    model.c,
    model.w,
    initialize=data["yield"],
    default=0.0,
    mutable=True,
    doc="crop yields (metric tons per ha)"
)
model.water = Param(
    model.c,
    model.w,
    initialize=data["water"],
    default=0.0,
    mutable=True,
    doc="water requirement (1000 m3 per ha)"
)

# Agronomic land limits for each crop
model.agrol = Param(
    model.c,
    initialize=data["agrol"],
    mutable=True,
    doc="agronomic land limit (ha)"
)

# Length of cropping season (fortnights) and land-use indicator
model.length = Param(
    model.c,
    model.s,
    initialize=data["length"],
    default=0.0,
    mutable=True,
    doc="length of season (fortnights)"
)
model.luse = Param(
    model.c,
    model.t,
    model.s,
    initialize=data["luse"],
    default=0.0,
    mutable=True,
    doc="land-use indicator: 1 if crop c with schedule s uses land at t"
)

# Task requirement per ha for each (g,t,c,s)
model.treq = Param(
    model.g,
    model.t,
    model.c,
    model.s,
    initialize=data["treq"],
    default=0.0,
    mutable=True,
    doc="task requirement per ha for task g, crop c, schedule s at time t"
)

# Labor requirements per ha in each fortnight
model.lreq = Param(
    model.c,
    model.s,
    model.t,
    initialize=data["lreq"],
    default=0.0,
    mutable=True,
    doc="labor requirement (hours per ha) for crop c, schedule s at time t"
)

# Loss in product from mechanical cotton picking
model.loss = Param(
    model.c,
    initialize=data["loss"],
    default=0.0,
    mutable=True,
    doc="product loss (tons/ha) from mechanical picking"
)

# Additional tasks needed for mechanical cotton picking (per ha)
model.tadj = Param(
    model.g,
    initialize=data["tadj"],
    default=0.0,
    mutable=True,
    doc="extra task requirement per ha for mechanical cotton picking"
)

# Technology: hours per ha (or per ton for transport) for each task with (m,n)
model.tech = Param(
    model.g,
    model.mn,
    model.mn,
    initialize=data["tech"],
    default=0.0,
    mutable=True,
    doc="technology coefficients (hours per ha or per ton)"
)

model.rho = Param(
    initialize=data["rho"],
    mutable=True,
    doc="interest rate"
)

# Scalar parameters (use JSON if present, otherwise GAMS defaults)
model.land = Param(
    initialize=data["land"],
    mutable=True,
    doc="farm size (ha)"
)
model.lcost = Param(
    initialize=data["lcost"],
    mutable=True,
    doc="labor cost (1000 rials per man-day)"
)
model.watercost = Param(
    initialize=data["watercost"],
    mutable=True,
    doc="water cost (1000 rials per 1000 m3)"
)
model.hrtoday = Param(
    initialize=data["hrtoday"],
    mutable=True,
    doc="hours in a man-day"
)

# ----------------------------------------------------------------------
# TASK possibility set
# ----------------------------------------------------------------------
# The GAMS source declares task only on the index tuples it actually uses.
# The dense conversion lost that restriction, declaring task over the full
# g*t*mn*mn cross product (~369k columns), ~99% of which are zero-coefficient
# inert variables. A task(g,t,m,n) column is structurally relevant only where
# (g,t) is a valid task-time pair AND the (g,m,n) technology OR operating-cost
# coefficient is nonzero, plus the cotton-picking entry referenced directly by
# the cbal loss term and the tbal adjustment term. Restricting task to this set
# removes the inert columns without changing any constraint or the objective.
def _as_tuple(k):
    return tuple(k.split("|")) if isinstance(k, str) else tuple(k)

_taskposs_pairs = {_as_tuple(p) for p in data["taskposs"]}
_gmn_nonzero = {_as_tuple(k) for k, v in data["tech"].items() if v != 0} | \
               {_as_tuple(k) for k, v in data["oc"].items() if v != 0}

TASK_LIVE = set()
for (_g, _t) in _taskposs_pairs:
    for (_gg, _m, _n) in _gmn_nonzero:
        if _gg == _g:
            TASK_LIVE.add((_g, _t, _m, _n))
    # cotton-picking entry referenced by cbal loss term and tbal adjustment term
    TASK_LIVE.add(("harvest-c", _t, "cotton-p", "self-prop"))

# xwater(c,w) is structurally relevant only on the (c,w) pairs of the yield-water
# curve (nonzero yield or water); the dense c*w declaration leaves the off-curve
# pairs (e.g. xwater[cotton,stress-3]) as inert, uninitialized columns.
XWATER_LIVE = {_as_tuple(k) for k, v in data["yield"].items() if v != 0} | \
              {_as_tuple(k) for k, v in data["water"].items() if v != 0}

# equipp(mn) is referenced only in the capital-cost sum (nonzero cap) and the
# equipment-balance constraints (equipposs membership). Power sources excluded
# from equipposs with zero capital cost (manual, self-prop) are inert columns.
_equipposs_equip = {_as_tuple(p)[0] for p in equipposs_data}
EQUIPP_LIVE = {mn for mn in data["mn"]
               if mn in _equipposs_equip or data["cap"].get(mn, 0) != 0}

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------

# xcrop(c,s): area planted under each crop/schedule (ha)
model.xcrop = Var(
    model.c,
    model.s,
    domain=NonNegativeReals,
    doc="cropping schedules (ha)"
)

# xwater(c,w): area of crop c under irrigation level w (ha)
# Indexed over XWATER_LIVE (yield-water curve support) rather than the full c*w
# cross product, dropping inert off-curve columns.
model.xwaterset = Set(
    dimen=2,
    initialize=sorted(XWATER_LIVE),
    doc="(crop, water-stress) pairs on the yield-water curve"
)
model.xwater = Var(
    model.xwaterset,
    domain=NonNegativeReals,
    doc="cropping by irrigation level (ha)"
)

# awater: annual water requirement (million m3)
model.awater = Var(
    domain=NonNegativeReals,
    doc="annual water requirement (million cubic meters)"
)

# task(g,t,m,n): area (or tons for transport) using technology (m,n) at time t
# Indexed over TASK_LIVE (see above) rather than the full g*t*mn*mn cross
# product, dropping ~99% zero-coefficient inert columns.
model.taskset = Set(
    dimen=4,
    initialize=sorted(TASK_LIVE),
    doc="(task, time, implement, power) tuples with a nonzero technology or "
        "operating-cost coefficient (plus the cotton-picking adjustment entry)"
)
model.task = Var(
    model.taskset,
    domain=NonNegativeReals,
    doc="agricultural tasks by technology (ha or tons equivalent)"
)

# sales(c): crop sales (tons)
model.sales = Var(
    model.c,
    domain=NonNegativeReals,
    doc="sales of agricultural commodities (tons)"
)

# equipp(mn): number of equipment units purchased
# Indexed over EQUIPP_LIVE (equipment with a capital cost or a balance
# constraint), dropping inert columns (e.g. manual, self-prop).
model.equippset = Set(
    initialize=sorted(EQUIPP_LIVE),
    within=model.mn,
    doc="equipment with a nonzero capital cost or an equipment-balance constraint"
)
model.equipp = Var(
    model.equippset,
    domain=NonNegativeReals,
    doc="equipment purchases (units)"
)

# emply(t): employment in man-days
model.emply = Var(
    model.t,
    domain=NonNegativeReals,
    doc="employment (man-days)"
)

# revenue, cost(cc), profit
model.revenue = Var(
    domain=Reals,
    doc="revenue from crop sales (1000 rials)"
)
model.cost = Var(
    model.cc,
    domain=NonNegativeReals,
    doc="cost categories (1000 rials)"
)
model.profit = Var(
    domain=Reals,
    doc="profit (1000 rials)"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
model.obj = Objective(
    expr=model.profit,
    sense=maximize,
    doc="maximize profit (1000 rials)"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

def cbal_rule(model, c):
    # loss term only nonzero for cotton
    loss_term = model.loss[c] * sum(
        model.task["harvest-c", t, "cotton-p", "self-prop"]
        for t in model.t
        if ("harvest-c", t) in model.taskposs
    )
    return model.sales[c] == \
        sum(model.yield_[c, w] * model.xwater[c, w]
            for w in model.w if (c, w) in XWATER_LIVE) - loss_term

model.cbal = Constraint(model.c, rule=cbal_rule,
                        doc="commodity balance (tons)")

def tbal_rule(model, g, t):
    if (g, t) not in model.taskposs:
        return Constraint.Skip

    left = sum(
        model.treq[g, t, c, s] * model.xcrop[c, s]
        for (c, s) in model.cposs
    )
    right = sum(
        model.task[g, t, m, n]
        for m in model.mn
        for n in model.mn
    )

    # extra tasks for mechanical cotton picking (only where tadj(g) != 0)
    right -= model.tadj[g] * model.task["harvest-c", t, "cotton-p", "self-prop"]

    return left == right * sum(model.tech[g, m, n] 
                                for m in model.mn 
                                for n in model.mn)

# FIX: Rewrite tbal properly
def tbal_rule(model, g, t):
    if (g, t) not in model.taskposs:
        return Constraint.Skip

    left = sum(
        model.treq[g, t, c, s] * model.xcrop[c, s]
        for (c, s) in model.cposs
    )
    right = sum(
        model.tech[g, m, n] * model.task[g, t, m, n]
        for m in model.mn
        for n in model.mn
        if (g, t, m, n) in TASK_LIVE
    )

    # extra tasks for mechanical cotton picking
    adj_term = model.tadj[g] * model.task["harvest-c", t, "cotton-p", "self-prop"]

    return left == right - adj_term

model.tbal = Constraint(
    model.g,
    model.t,
    rule=tbal_rule,
    doc="task balance (ha or equivalent)"
)

# cropd(c).. sum(s$cposs(c,s), xcrop(c,s)) =e= sum(w$yield(c,w), xwater(c,w));
# The $yield(c,w) in GAMS just filters to irrigation levels where yield is defined (non-zero)
# We need to check the data dictionary directly, not the param
def cropd_rule(model, c):
    left = sum(
        model.xcrop[c, s]
        for (cc, s) in model.cposs
        if cc == c
    )
    # Filter based on data, not param (to avoid boolean conversion error)
    right = sum(
        model.xwater[c, w]
        for w in model.w
        if data["yield"].get((c, w), 0.0) != 0.0
    )
    return left == right

model.cropd = Constraint(
    model.c,
    rule=cropd_rule,
    doc="crop-water balance (ha)"
)

# waterd.. awater =e= sum((c,w), water(c,w)*xwater(c,w))/1000;
def waterd_rule(model):
    return model.awater == \
        sum(model.water[c, w] * model.xwater[c, w]
            for c in model.c for w in model.w
            if (c, w) in XWATER_LIVE) / 1000.0

model.waterd = Constraint(
    rule=waterd_rule,
    doc="annual water requirement definition (million m3)"
)

# agroc(c).. sum(s$cposs(c,s), xcrop(c,s)) =l= agrol(c);
def agroc_rule(model, c):
    return sum(
        model.xcrop[c, s]
        for (cc, s) in model.cposs
        if cc == c
    ) <= model.agrol[c]

model.agroc = Constraint(
    model.c,
    rule=agroc_rule,
    doc="agronomic constraints (ha)"
)

# landc(t).. sum((c,s)$cposs(c,s), luse(c,t,s)*xcrop(c,s)) =l= land;
def landc_rule(model, t):
    return sum(
        model.luse[c, t, s] * model.xcrop[c, s]
        for (c, s) in model.cposs
    ) <= model.land

model.landc = Constraint(
    model.t,
    rule=landc_rule,
    doc="land constraints (ha)"
)

def labor_rule(model, t):
    crop_labor = sum(
        model.lreq[c, s, t] * model.xcrop[c, s]
        for (c, s) in model.cposs
    )
    task_labor = sum(
        model.tech[g, m, n] * model.task[g, t, m, n]
        for (g, tt) in model.taskposs if tt == t
        for m in model.mn
        for n in model.mn
        if (g, t, m, n) in TASK_LIVE
    )
    return crop_labor + task_labor <= model.hrtoday * model.emply[t]

model.labor = Constraint(
    model.t,
    rule=labor_rule,
    doc="labor requirements (man-days)"
)

def equipb1_rule(model, m, t):
    if (m, t) not in model.equipposs:
        return Constraint.Skip
    return sum(
        model.tech[g, m, n] * model.task[g, t, m, n]
        for (g, tt) in model.taskposs if tt == t
        for n in model.n
        if (g, t, m, n) in TASK_LIVE
    ) <= model.avail[m] * model.equipp[m]

model.equipb1 = Constraint(
    model.m,
    model.t,
    rule=equipb1_rule,
    doc="equipment balance for implements"
)

def equipb2_rule(model, n, t):
    if (n, t) not in model.equipposs:
        return Constraint.Skip
    return sum(
        model.tech[g, m, n] * model.task[g, t, m, n]
        for (g, tt) in model.taskposs if tt == t
        for m in model.m
        if (g, t, m, n) in TASK_LIVE
    ) <= model.avail[n] * model.equipp[n]

model.equipb2 = Constraint(
    model.n,
    model.t,
    rule=equipb2_rule,
    doc="equipment balance for power sources"
)

# arev.. revenue =e= sum(c, pcrop(c)*sales(c));
def arev_rule(model):
    return model.revenue == sum(model.pcrop[c] * model.sales[c] for c in model.c)

model.arev = Constraint(
    rule=arev_rule,
    doc="revenue accounting (1000 rials)"
)

# acost1.. cost("misc-input") =e= sum(c, pmisc(c)*sum(s$cposs(c,s), xcrop(c,s)));
def acost1_rule(model):
    return model.cost["misc-input"] == sum(
        model.pmisc[c] * sum(
            model.xcrop[c, s]
            for (cc, s) in model.cposs
            if cc == c
        )
        for c in model.c
    )

model.acost1 = Constraint(
    rule=acost1_rule,
    doc="cost of miscellaneous inputs (1000 rials)"
)

# acost2.. cost("water") =e= watercost*awater;
def acost2_rule(model):
    return model.cost["water"] == model.watercost * model.awater

model.acost2 = Constraint(
    rule=acost2_rule,
    doc="cost of water (1000 rials)"
)

# acost3.. cost("operating") =e= sum((g,t,m,n)$taskposs(g,t), oc(g,m,n)*task(g,t,m,n));
def acost3_rule(model):
    return model.cost["operating"] == sum(
        model.oc[g, m, n] * model.task[g, t, m, n]
        for (g, t) in model.taskposs
        for m in model.mn
        for n in model.mn
        if (g, t, m, n) in TASK_LIVE
    )

model.acost3 = Constraint(
    rule=acost3_rule,
    doc="operating cost (1000 rials)"
)

# acost4.. cost("capital") =e= sum(mn, cap(mn)*equipp(mn));
def acost4_rule(model):
    return model.cost["capital"] == sum(
        model.cap[mn] * model.equipp[mn]
        for mn in model.mn if mn in EQUIPP_LIVE
    )

model.acost4 = Constraint(
    rule=acost4_rule,
    doc="capital charges (1000 rials)"
)

# acost5.. cost("wages") =e= lcost*sum(t, emply(t));
def acost5_rule(model):
    return model.cost["wages"] == model.lcost * sum(
        model.emply[t] for t in model.t
    )

model.acost5 = Constraint(
    rule=acost5_rule,
    doc="labor cost (1000 rials)"
)

# obj.. profit =e= revenue - sum(cc, cost(cc));
def obj_balance_rule(model):
    return model.profit == model.revenue - sum(
        model.cost[cc] for cc in model.cc
    )

model.obj_balance = Constraint(
    rule=obj_balance_rule,
    doc="objective (profit) definition"
)

# ----------------------------------------------------------------------
# BOUNDS_BLOCK (from GAMS)
# ----------------------------------------------------------------------
# sales.lo("wheat") = 875;
if "wheat" in model.c:
    model.sales["wheat"].setlb(875.0)

# awater.up = 21.73;
model.awater.setub(21.73)
