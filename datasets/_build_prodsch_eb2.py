#!/usr/bin/env python
"""Builder for the prodsch_eb2 (seasonal production scheduling) constraint-generation dataset.

All 13 constraints are LINEAR (polynomial degree 1): the /1000.0 scalings and the
delt discount weights are parameter-only multiplications/divisions. No nonlinear
constraint to exclude. Builds one record per constraint plus one whole-set record.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "prodsch_eb2_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "Q", "members": ["summer", "fall", "winter", "spring"],
         "doc": "the ordered set of quarters in the planning year; the order is summer, fall, winter, spring, and it wraps around so that the quarter before summer is spring"},
        {"name": "S", "members": ["first", "second"],
         "doc": "the set of work shifts that can be operated in a quarter"},
        {"name": "L", "members": [1, 2, 3, 4],
         "doc": "the ordered set of production-level breakpoints, indexed by consecutive integers starting at 1, used to express the piecewise relationship between motors produced and labor required on a shift"},
    ],
    "params": [
        {"name": "mc", "index": "", "kind": "cost",
         "doc": "material cost incurred per motor produced, in dollars per motor; a scalar"},
        {"name": "sr", "index": "", "kind": "cost",
         "doc": "space rental rate charged per unit of inventory held, in dollars per motor; a scalar"},
        {"name": "hc", "index": "", "kind": "cost",
         "doc": "cost of hiring one worker, in dollars per worker; a scalar"},
        {"name": "fc", "index": "", "kind": "cost",
         "doc": "cost of firing one worker, in dollars per worker; a scalar"},
        {"name": "d", "index": "Q", "kind": "demand",
         "doc": "motor demand to be met in each quarter, in motors; demand is zero in every quarter except spring"},
        {"name": "lc", "index": "Q", "kind": "cost",
         "doc": "fixed leasing cost of the extra storage facility in each quarter, in dollars; charged only when the lease is taken"},
        {"name": "pr_labor", "index": "L", "kind": "coefficient",
         "doc": "workers required at production-level breakpoint l on a shift, in workers; together with pr_motor it defines the breakpoints of the piecewise motors-to-labor relationship"},
        {"name": "pr_motor", "index": "L", "kind": "coefficient",
         "doc": "motors produced at production-level breakpoint l on a shift, in motors; together with pr_labor it defines the breakpoints of the piecewise motors-to-labor relationship"},
        {"name": "sc_fixed", "index": "S", "kind": "cost",
         "doc": "fixed cost of operating a shift, in dollars, charged when the shift is used in a quarter"},
        {"name": "sc_labor", "index": "S", "kind": "cost",
         "doc": "cost per worker employed on a shift, in dollars per worker"},
        {"name": "delt", "index": "Q", "kind": "weight",
         "doc": "discount factor applied to a quarter's cost, equal to one for the first quarter and shrinking geometrically for later quarters; a precomputed parameter"},
        {"name": "invmax", "index": "", "kind": "bound",
         "doc": "an upper bound on inventory equal to the total annual demand, in motors; a precomputed scalar used to switch off the space-rental requirement when the extra storage facility is leased"},
    ],
    "vars": [
        {"name": "cost", "index": "", "domain": "Reals",
         "doc": "the total discounted cost over the year, in thousands of dollars; this is the quantity the objective minimizes"},
        {"name": "dpc", "index": "Q", "domain": "Reals",
         "doc": "direct production cost in a quarter, in thousands of dollars, covering material, fixed shift, and shift labor costs"},
        {"name": "isc", "index": "Q", "domain": "Reals",
         "doc": "inventory storage cost in a quarter, in thousands of dollars"},
        {"name": "wfc", "index": "Q", "domain": "Reals",
         "doc": "workforce fluctuation cost in a quarter, in thousands of dollars, covering hiring and firing"},
        {"name": "src", "index": "Q", "domain": "NonNegativeReals",
         "doc": "space rental cost in a quarter, in dollars, before being folded into the storage cost"},
        {"name": "p", "index": "Q", "domain": "NonNegativeReals",
         "doc": "number of motors produced in a quarter"},
        {"name": "ss", "index": "L,Q,S", "domain": "NonNegativeReals",
         "doc": "weight placed on production-level breakpoint l on a shift in a quarter; these weights interpolate between the breakpoints to express production and labor on that shift"},
        {"name": "ssb", "index": "L,Q,S", "domain": "Binary",
         "doc": "breakpoint selector indicating which production-level breakpoint is active on a shift in a quarter, used to keep the interpolation weights on adjacent breakpoints"},
        {"name": "inv", "index": "Q", "domain": "NonNegativeReals",
         "doc": "motors held in inventory at the end of a quarter"},
        {"name": "lease", "index": "", "domain": "Binary",
         "doc": "whether the extra storage facility is leased for the year; one if leased, zero otherwise"},
        {"name": "e", "index": "Q", "domain": "NonNegativeReals",
         "doc": "total number of workers employed in a quarter"},
        {"name": "se", "index": "Q,S", "domain": "NonNegativeReals",
         "doc": "number of workers employed on a shift in a quarter"},
        {"name": "shift", "index": "Q,S", "domain": "Binary",
         "doc": "whether a shift is operated in a quarter; one if used, zero otherwise"},
        {"name": "h", "index": "Q", "domain": "NonNegativeReals",
         "doc": "number of workers hired at the start of a quarter"},
        {"name": "f", "index": "Q", "domain": "NonNegativeReals",
         "doc": "number of workers fired at the start of a quarter"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We plan motor production across the four quarters of a year. In each quarter we decide how "
    "many motors to produce, which shifts to operate and how many workers to staff on each, how "
    "many workers to hire or fire, and how much inventory to carry into the next quarter. We also "
    "decide once for the year whether to lease an extra storage facility. Production on each shift "
    "follows a piecewise relationship between motors made and workers needed, captured through "
    "interpolation weights over a set of production-level breakpoints. The objective is to "
    "minimize the total cost over the year, discounted quarter by quarter, where cost combines "
    "direct production cost, inventory storage cost, and the cost of hiring and firing workers."
)

# ---- per-constraint expected_pyomo (model. prefix, native names) ----

ACOST = (
    "model.acost = Constraint(expr=\n"
    "    model.cost == sum(model.delt[q] * (model.dpc[q] + model.isc[q] + model.wfc[q])\n"
    "                      for q in model.Q))"
)

DDPC = (
    "def ddpc_rule(model, q):\n"
    "    return model.dpc[q] == (model.mc * model.p[q]\n"
    "        + sum(model.sc_fixed[s] * model.shift[q, s] + model.sc_labor[s] * model.se[q, s]\n"
    "              for s in model.S)) / 1000.0\n"
    "model.ddpc = Constraint(model.Q, rule=ddpc_rule)"
)

SBP = (
    "def sbp_rule(model, q):\n"
    "    return model.p[q] == sum(model.pr_motor[l] * model.ss[l, q, s]\n"
    "                             for l in model.L for s in model.S)\n"
    "model.sbp = Constraint(model.Q, rule=sbp_rule)"
)

SBSE = (
    "def sbse_rule(model, q, s):\n"
    "    return model.se[q, s] == sum(model.pr_labor[l] * model.ss[l, q, s] for l in model.L)\n"
    "model.sbse = Constraint(model.Q, model.S, rule=sbse_rule)"
)

SCC = (
    "def scc_rule(model, q, s):\n"
    "    return sum(model.ss[l, q, s] for l in model.L) == model.shift[q, s]\n"
    "model.scc = Constraint(model.Q, model.S, rule=scc_rule)"
)

INVB = (
    "def invb_rule(model, q):\n"
    "    prev = model._prev_q[q]\n"
    "    if prev is None:\n"
    "        return model.inv[q] == model.p[q] - model.d[q]\n"
    "    return model.inv[q] == model.inv[prev] + model.p[q] - model.d[q]\n"
    "model.invb = Constraint(model.Q, rule=invb_rule)"
)

DISC = (
    "def disc_rule(model, q):\n"
    "    return model.isc[q] == (model.lc[q] * model.lease + model.src[q]) / 1000.0\n"
    "model.disc = Constraint(model.Q, rule=disc_rule)"
)

DSRC = (
    "def dsrc_rule(model, q):\n"
    "    return model.src[q] >= model.sr * (model.inv[q] - model.invmax * model.lease)\n"
    "model.dsrc = Constraint(model.Q, rule=dsrc_rule)"
)

DWFC = (
    "def dwfc_rule(model, q):\n"
    "    return model.wfc[q] == (model.hc * model.h[q] + model.fc * model.f[q]) / 1000.0\n"
    "model.dwfc = Constraint(model.Q, rule=dwfc_rule)"
)

ED = (
    "def ed_rule(model, q):\n"
    "    return model.e[q] == sum(model.se[q, s] for s in model.S)\n"
    "model.ed = Constraint(model.Q, rule=ed_rule)"
)

EB2 = (
    "def eb2_rule(model, q):\n"
    "    prev = model._prev_cyclic[q]\n"
    "    return model.e[q] == model.e[prev] + model.h[q] - model.f[q]\n"
    "model.eb2 = Constraint(model.Q, rule=eb2_rule)"
)

MESSB = (
    "def messb_rule(model, q, s):\n"
    "    return sum(model.ssb[l, q, s] for l in model.L) == 1\n"
    "model.messb = Constraint(model.Q, model.S, rule=messb_rule)"
)

LSSB = (
    "def lssb_rule(model, l, q, s):\n"
    "    lhs = model.ss[l, q, s]\n"
    "    if (l - 1) in model.L:\n"
    "        lhs += model.ss[l - 1, q, s]\n"
    "    rhs = model.ssb[l, q, s]\n"
    "    if (l - 1) in model.L:\n"
    "        rhs += model.ssb[l - 1, q, s]\n"
    "    if (l - 2) in model.L:\n"
    "        rhs += model.ssb[l - 2, q, s]\n"
    "    return lhs <= rhs\n"
    "model.lssb = Constraint(model.L, model.Q, model.S, rule=lssb_rule)"
)

WHOLESET = "\n".join([ACOST, DDPC, SBP, SBSE, SCC, INVB, DISC, DSRC, DWFC, ED, EB2, MESSB, LSSB])

records = [
    {"description": (
        "The total cost for the year is the sum over the quarters of that quarter's combined "
        "production, storage, and workforce costs, with each quarter's contribution scaled down "
        "by its own discount factor so that costs further into the year count for less."),
     "expected_pyomo": ACOST},

    {"description": (
        "For each quarter the direct production cost accounts for the material cost of the motors "
        "produced that quarter together with, for every shift, the fixed cost of running that shift "
        "when it is operated and the per-worker cost of the workers staffed on it. Because the "
        "production cost is tracked in thousands of dollars while the underlying costs are in "
        "dollars, the total is rescaled to thousands."),
     "expected_pyomo": DDPC},

    {"description": (
        "For each quarter the motors produced equal the production obtained by combining, across "
        "every shift and every production-level breakpoint, the breakpoint motor output weighted "
        "by how much that breakpoint is used on that shift."),
     "expected_pyomo": SBP},

    {"description": (
        "For each shift in each quarter the workers staffed on that shift equal the labor obtained "
        "by combining, across the production-level breakpoints, the breakpoint labor requirement "
        "weighted by how much that breakpoint is used on that shift."),
     "expected_pyomo": SBSE},

    {"description": (
        "For each shift in each quarter the interpolation weights placed on the production-level "
        "breakpoints must together add up to whether that shift is operated, so the weights sum to "
        "one when the shift runs and to zero when it does not."),
     "expected_pyomo": SCC},

    {"description": (
        "For each quarter the inventory carried at the end of the quarter equals the inventory "
        "brought in from the previous quarter plus the motors produced in the quarter minus the "
        "motors demanded in the quarter. For the very first quarter of the year there is no "
        "inventory carried in, so its ending inventory is simply production minus demand."),
     "expected_pyomo": INVB},

    {"description": (
        "For each quarter the inventory storage cost combines the fixed leasing cost of the extra "
        "storage facility, charged only when the lease is taken for the year, with the space rental "
        "cost incurred that quarter. As with the other cost terms this is expressed in thousands of "
        "dollars, so the underlying dollar amounts are rescaled to thousands."),
     "expected_pyomo": DISC},

    {"description": (
        "For each quarter the space rental cost must be at least the rental rate applied to the "
        "inventory held that quarter, except that when the extra storage facility is leased for the "
        "year the chargeable inventory is reduced by the full inventory bound, which relaxes the "
        "requirement so that no space rental cost is forced. The rental cost is also kept "
        "nonnegative."),
     "expected_pyomo": DSRC},

    {"description": (
        "For each quarter the workforce fluctuation cost accounts for the cost of the workers hired "
        "in that quarter and the cost of the workers fired in that quarter. This cost is expressed "
        "in thousands of dollars, so the underlying dollar amounts are rescaled to thousands."),
     "expected_pyomo": DWFC},

    {"description": (
        "For each quarter the total workers employed equal the sum of the workers staffed across "
        "all shifts in that quarter."),
     "expected_pyomo": ED},

    {"description": (
        "Employment evolves quarter to quarter as a steady cycle. For each quarter the workers "
        "employed equal the workers employed in the previous quarter plus those hired at the start "
        "of the quarter minus those fired, where the previous quarter wraps around so that the "
        "quarter before the first one is the last quarter of the year. This makes the workforce "
        "balance close on itself over the year."),
     "expected_pyomo": EB2},

    {"description": (
        "For each shift in each quarter exactly one production-level breakpoint must be selected as "
        "the active one, so the breakpoint selectors over all levels add up to one."),
     "expected_pyomo": MESSB},

    {"description": (
        "The interpolation weights must stay on adjacent production-level breakpoints, consistent "
        "with the selected active breakpoint. For each production level, shift, and quarter, the "
        "weight on that level together with the weight on the level just below it cannot exceed the "
        "combined selection of that level and the two levels just below it. This forces the nonzero "
        "weights to sit on neighboring breakpoints around the chosen one."),
     "expected_pyomo": LSSB},

    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as fh:
    for r in records:
        fh.write(json.dumps({
            "problem_id": "prodsch_eb2",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
