#!/usr/bin/env python
"""Builder for the prodschx_2S1_mip (production scheduling) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "prodschx_2S1_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "q", "members": ["summer", "fall", "winter", "spring"],
         "doc": "the production seasons in chronological order; the first member is the opening season and each later member immediately follows the one before it"},
        {"name": "s", "members": ["first", "second"],
         "doc": "the work shifts that can be run within a season"},
        {"name": "l", "members": [1, 2, 3, 4],
         "doc": "the ordered production levels, also called breakpoints, used to describe a piecewise relationship between labor used and motors produced on a shift; listed from lowest to highest"},
    ],
    "params": [
        {"name": "d", "index": "q", "kind": "demand",
         "doc": "the motor demand that must be met in each season, in motors"},
        {"name": "lc", "index": "q", "kind": "cost",
         "doc": "the leasing cost charged in each season if the extra space lease is taken, in dollars"},
        {"name": "delt", "index": "q", "kind": "discount",
         "doc": "the discount factor applied to each season's costs to convert them to present value; dimensionless"},
        {"name": "mc", "index": "", "kind": "cost",
         "doc": "the material cost per motor produced, in dollars per motor"},
        {"name": "sr", "index": "", "kind": "cost",
         "doc": "the space rental cost charged per unit of inventory held beyond the leased allowance, in dollars per motor"},
        {"name": "hc", "index": "", "kind": "cost",
         "doc": "the hiring cost per employee hired, in dollars per employee"},
        {"name": "fc", "index": "", "kind": "cost",
         "doc": "the firing cost per employee fired, in dollars per employee"},
        {"name": "invmax", "index": "", "kind": "capacity",
         "doc": "the inventory allowance that the space lease covers, equal to total demand across all seasons, in motors"},
        {"name": "pr_motor", "index": "(labor|motor), l",
         "kind": "breakpoint",
         "doc": "the breakpoint table for the piecewise labor-to-motor relationship; the 'labor' row gives the labor amount at each production level and the 'motor' row gives the motors produced at each production level, so a chosen mix over the levels yields a matching pair of labor and motors"},
        {"name": "sc", "index": "(fixed|labor), s",
         "kind": "cost",
         "doc": "the shift cost table; the 'fixed' row gives the fixed cost incurred when a shift is run and the 'labor' row gives the cost per employee on that shift, in dollars"},
    ],
    "vars": [
        {"name": "cost", "index": "", "domain": "NonNegativeReals",
         "doc": "the total discounted cost over the whole horizon, the quantity being minimized, in thousands of dollars"},
        {"name": "dpc", "index": "q", "domain": "NonNegativeReals",
         "doc": "the direct production cost in each season, in thousands of dollars"},
        {"name": "isc", "index": "q", "domain": "NonNegativeReals",
         "doc": "the inventory cost in each season, in thousands of dollars"},
        {"name": "wfc", "index": "q", "domain": "NonNegativeReals",
         "doc": "the workforce change cost in each season, in thousands of dollars"},
        {"name": "src", "index": "q", "domain": "NonNegativeReals",
         "doc": "the space rental charge in each season, in dollars"},
        {"name": "p", "index": "q", "domain": "NonNegativeReals",
         "doc": "the number of motors produced in each season"},
        {"name": "ss", "index": "q,s,l", "domain": "NonNegativeReals",
         "doc": "the weight placed on each production level for a season and shift; these weights select a point along the piecewise labor-to-motor breakpoints"},
        {"name": "ssb", "index": "q,s,l", "domain": "Binary",
         "doc": "an auxiliary 0/1 selector associated with each production level on a season and shift"},
        {"name": "inv", "index": "q", "domain": "NonNegativeReals",
         "doc": "the motors held in inventory at the end of each season"},
        {"name": "lease", "index": "", "domain": "Binary",
         "doc": "a single 0/1 decision that equals 1 if the extra space lease is taken for the horizon and 0 otherwise"},
        {"name": "e", "index": "q", "domain": "NonNegativeReals",
         "doc": "the total number of employees on the payroll in each season"},
        {"name": "se", "index": "q,s", "domain": "NonNegativeReals",
         "doc": "the number of employees working on each shift in each season"},
        {"name": "shift", "index": "q,s", "domain": "Binary",
         "doc": "a 0/1 indicator that equals 1 if the shift is run in the season and 0 otherwise"},
        {"name": "h", "index": "q", "domain": "NonNegativeReals",
         "doc": "the number of employees hired in each season"},
        {"name": "f", "index": "q", "domain": "NonNegativeReals",
         "doc": "the number of employees fired in each season"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We plan motor production across a sequence of seasons. In each season we decide how many "
    "motors to produce, which shifts to run, how many employees to put on each shift, how many "
    "employees to hire or fire, how much inventory to carry into the next season, and whether to "
    "take an extra space lease for the horizon. Production on a shift follows a piecewise "
    "relationship between the labor used and the motors produced, expressed by choosing weights "
    "over a set of production levels. Costs accrue from materials, running shifts and paying "
    "shift labor, carrying inventory and renting overflow space, and hiring and firing employees, "
    "and each season's costs are discounted to present value. The objective is to minimize the "
    "total discounted cost over the whole horizon."
)

ACOST = (
    "def acost_rule(m):\n"
    "    return m.cost == sum(m.delt[q] * (m.dpc[q] + m.isc[q] + m.wfc[q]) for q in m.q)\n"
    "model.acost = Constraint(rule=acost_rule)"
)
DDPC = (
    "def ddpc_rule(m, q):\n"
    "    return m.dpc[q] == (m.mc * m.p[q] + sum(m.sc['fixed', s] * m.shift[q, s] + m.sc['labor', s] * m.se[q, s] for s in m.s)) / 1000\n"
    "model.ddpc = Constraint(model.q, rule=ddpc_rule)"
)
SBP = (
    "def sbp_rule(m, q):\n"
    "    return m.p[q] == sum(m.pr_motor['motor', l] * m.ss[q, s, l] for s in m.s for l in m.l)\n"
    "model.sbp = Constraint(model.q, rule=sbp_rule)"
)
SBSE = (
    "def sbse_rule(m, q, s):\n"
    "    return m.se[q, s] == sum(m.pr_motor['labor', l] * m.ss[q, s, l] for l in m.l)\n"
    "model.sbse = Constraint(model.q, model.s, rule=sbse_rule)"
)
SCC = (
    "def scc_rule(m, q, s):\n"
    "    return sum(m.ss[q, s, l] for l in m.l) == m.shift[q, s]\n"
    "model.scc = Constraint(model.q, model.s, rule=scc_rule)"
)
INVB = (
    "def invb_rule(m, q):\n"
    "    qlist = list(m.q)\n"
    "    idx = qlist.index(q)\n"
    "    prev = m.inv[qlist[idx-1]] if idx > 0 else 0\n"
    "    return m.inv[q] == prev + m.p[q] - m.d[q]\n"
    "model.invb = Constraint(model.q, rule=invb_rule)"
)
DISC = (
    "def disc_rule(m, q):\n"
    "    return m.isc[q] == (m.lc[q] * m.lease + m.src[q]) / 1000\n"
    "model.disc = Constraint(model.q, rule=disc_rule)"
)
DSRC = (
    "def dsrc_rule(m, q):\n"
    "    return m.src[q] >= m.sr * (m.inv[q] - m.invmax * m.lease)\n"
    "model.dsrc = Constraint(model.q, rule=dsrc_rule)"
)
DWFC = (
    "def dwfc_rule(m, q):\n"
    "    return m.wfc[q] == (m.hc * m.h[q] + m.fc * m.f[q]) / 1000\n"
    "model.dwfc = Constraint(model.q, rule=dwfc_rule)"
)
ED = (
    "def ed_rule(m, q):\n"
    "    return m.e[q] == sum(m.se[q, s] for s in m.s)\n"
    "model.ed = Constraint(model.q, rule=ed_rule)"
)
EB2 = (
    "def eb2_rule(m, q):\n"
    "    qlist = list(m.q)\n"
    "    idx = qlist.index(q)\n"
    "    prev_e = m.e[qlist[idx-1]] if idx > 0 else 0\n"
    "    return m.e[q] == prev_e + m.h[q] - m.f[q]\n"
    "model.eb2 = Constraint(model.q, rule=eb2_rule)"
)
LSS1 = (
    "def lss1_rule(m, q, s, l):\n"
    "    llist = list(m.l)\n"
    "    lidx = llist.index(l)\n"
    "    lhs = m.ss[q, s, l]\n"
    "    if lidx > 0:\n"
    "        lhs += m.ss[q, s, llist[lidx-1]]\n"
    "    rhs = m.ss[q, s, l]\n"
    "    if lidx > 0:\n"
    "        rhs += m.ss[q, s, llist[lidx-1]]\n"
    "    if lidx > 1:\n"
    "        rhs += m.ss[q, s, llist[lidx-2]]\n"
    "    return lhs <= rhs\n"
    "model.lss1 = Constraint(model.q, model.s, model.l, rule=lss1_rule)"
)
MESS1 = (
    "def mess1_rule(m, q, s):\n"
    "    return sum(m.ss[q, s, l] for l in m.l) == 1\n"
    "model.mess1 = Constraint(model.q, model.s, rule=mess1_rule)"
)

WHOLESET = "\n".join([ACOST, DDPC, SBP, SBSE, SCC, INVB, DISC, DSRC, DWFC, ED, EB2, LSS1, MESS1])

records = [
    {"description": (
        "The total discounted cost ties together every season's costs. For each season add up its "
        "direct production cost, its inventory cost, and its workforce change cost, scale that sum "
        "by the season's discount factor, and set the total cost equal to these discounted season "
        "totals added across all seasons."),
     "expected_pyomo": ACOST},
    {"description": (
        "The direct production cost of a season comes from making motors and from running and "
        "staffing shifts. For each season it equals the material cost for every motor produced, "
        "plus for each shift the fixed cost charged when that shift is run together with the per "
        "employee labor cost applied to the employees on that shift, with the whole amount "
        "expressed in thousands of dollars."),
     "expected_pyomo": DDPC},
    {"description": (
        "Production in a season is set by how the chosen weights fall across the production levels "
        "on each shift. For each season the motors produced equal the sum over both shifts and all "
        "production levels of the motors associated with each level times the weight placed on that "
        "level."),
     "expected_pyomo": SBP},
    {"description": (
        "The employees on a shift follow from where the chosen weights fall across the production "
        "levels for that shift. For each season and each shift the shift employment equals the sum "
        "over all production levels of the labor associated with each level times the weight placed "
        "on that level."),
     "expected_pyomo": SBSE},
    {"description": (
        "The weights placed across the production levels on a shift are only available when that "
        "shift is actually run. For each season and each shift the weights across all production "
        "levels add up to the run indicator of that shift, so they sum to one when the shift is run "
        "and to zero otherwise."),
     "expected_pyomo": SCC},
    {"description": (
        "Inventory carries motors from one season into the next. For each season the ending "
        "inventory equals the inventory left from the immediately preceding season plus the motors "
        "produced that season minus the demand met that season. In the very first season there is "
        "no preceding season, so nothing carries in."),
     "expected_pyomo": INVB},
    {"description": (
        "The inventory cost of a season combines the leasing charge and the space rental charge. "
        "For each season it equals the season's leasing cost counted only when the lease is taken, "
        "plus that season's space rental charge, with the whole amount expressed in thousands of "
        "dollars."),
     "expected_pyomo": DISC},
    {"description": (
        "The space rental charge covers inventory held beyond what the lease allowance covers. For "
        "each season the rental charge must be at least the per unit rental rate applied to the "
        "inventory held that season reduced by the lease allowance when the lease is taken."),
     "expected_pyomo": DSRC},
    {"description": (
        "The workforce change cost of a season comes from hiring and firing. For each season it "
        "equals the hiring cost for every employee hired plus the firing cost for every employee "
        "fired, with the whole amount expressed in thousands of dollars."),
     "expected_pyomo": DWFC},
    {"description": (
        "Total employment in a season is shared across its shifts. For each season the total number "
        "of employees equals the employees summed over all shifts."),
     "expected_pyomo": ED},
    {"description": (
        "The workforce changes from season to season only through hiring and firing. For each "
        "season the total employment equals the employment carried from the immediately preceding "
        "season plus the employees hired that season minus the employees fired that season. In the "
        "very first season there is no preceding season, so the carried employment is zero."),
     "expected_pyomo": EB2},
    {"description": (
        "The weights across the production levels on a shift must respect the ordering of the "
        "levels, so that weight is placed only on neighboring levels rather than scattered across "
        "distant ones. For each season, each shift, and each production level, the weight on that "
        "level together with the weight on the level just below it cannot exceed the weight on that "
        "level together with the weights on the two levels just below it. The level just below and "
        "the two levels just below are only counted when they exist within the ordering."),
     "expected_pyomo": LSS1},
    {"description": (
        "Exactly one full unit of weight is spread across the production levels on every shift. For "
        "each season and each shift the weights across all production levels add up to one."),
     "expected_pyomo": MESS1},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as fp:
    for r in records:
        fp.write(json.dumps({
            "problem_id": "prodschx_2S1_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
