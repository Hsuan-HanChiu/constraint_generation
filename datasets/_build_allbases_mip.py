#!/usr/bin/env python
"""Builder for the allbases_mip constraint-generation dataset.

allbases_mip is a transportation model augmented with basis-indicator (big-M
linking) machinery. Shipments flow from plants to markets; supply and demand are
balanced with slack variables; and binary indicators mark which primal/slack
variables are in the basis, with the total basis size pinned to card(i)+card(j)-1.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "allbases_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the canning plants that ship product, that is the supply origins"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the markets that receive product, that is the demand destinations"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the supply capacity available at each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the demand required at each market, in cases"},
        {"name": "d", "index": "i,j", "kind": "distance",
         "doc": "the distance from each plant to each market, in thousands of miles"},
        {"name": "f", "index": "", "kind": "rate",
         "doc": "the freight rate, in dollars per case per thousand miles"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the transport cost per case shipped from each plant to each market, in thousands of dollars per case; it equals the freight rate times the distance divided by one thousand"},
        {"name": "min_ab", "index": "i,j", "kind": "bound",
         "doc": "for each plant and market, the smaller of that plant's supply capacity and that market's demand, in cases; it serves as the largest shipment that could ever flow on that lane and is used as the big-M upper bound for the corresponding shipment"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the quantity shipped from each plant to each market, in cases"},
        {"name": "sslack", "index": "i", "domain": "NonNegativeReals",
         "doc": "the unused supply at each plant, that is the supply slack, in cases"},
        {"name": "dslack", "index": "j", "domain": "NonNegativeReals",
         "doc": "the excess delivered above the demand at each market, that is the demand slack, in cases"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total transportation cost over all lanes, in thousands of dollars"},
        {"name": "xind", "index": "i,j", "domain": "Binary",
         "doc": "a binary indicator that is one when the shipment on a lane is allowed to be a basic variable and zero when it is forced out of the basis"},
        {"name": "sslind", "index": "i", "domain": "Binary",
         "doc": "a binary indicator that is one when a plant's supply slack is allowed to be a basic variable and zero when it is forced out of the basis"},
        {"name": "dslind", "index": "j", "domain": "Binary",
         "doc": "a binary indicator that is one when a market's demand slack is allowed to be a basic variable and zero when it is forced out of the basis"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We ship a product from a set of canning plants to a set of markets. For each "
    "plant and market pair we decide how many cases to ship. We also track the "
    "unused supply at each plant and the surplus delivered at each market, and we "
    "carry binary indicators that mark which shipments and slacks are allowed into "
    "the basis. The objective is to minimize the total transportation cost over all "
    "lanes."
)

# ── per-constraint expected Pyomo (native names) ─────────────────────────────
COST = (
    "def cost_rule(model):\n"
    "    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)\n"
    "model.cost = Constraint(rule=cost_rule)"
)
SUPPLY = (
    "def supply_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) == model.a[i] - model.sslack[i]\n"
    "model.supply = Constraint(model.i, rule=supply_rule)"
)
DEMAND = (
    "def demand_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) == model.b[j] + model.dslack[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)
DEFBASIS = (
    "def defbasis_rule(model):\n"
    "    return (len(model.i) + len(model.j)) == (\n"
    "        sum(model.xind[i, j] for i in model.i for j in model.j)\n"
    "        + sum(model.sslind[i] for i in model.i)\n"
    "        + sum(model.dslind[j] for j in model.j))\n"
    "model.defbasis = Constraint(rule=defbasis_rule)"
)
DEFXIMP = (
    "def defximp_rule(model, i, j):\n"
    "    return model.x[i, j] <= model.min_ab[i, j] * model.xind[i, j]\n"
    "model.defximp = Constraint(model.i, model.j, rule=defximp_rule)"
)
DEFSSLIMP = (
    "def defsslimp_rule(model, i):\n"
    "    return model.sslack[i] <= model.a[i] * model.sslind[i]\n"
    "model.defsslimp = Constraint(model.i, rule=defsslimp_rule)"
)
DEFDSLIMP = (
    "def defdslimp_rule(model, j):\n"
    "    return model.dslack[j] <= model.b[j] * model.dslind[j]\n"
    "model.defdslimp = Constraint(model.j, rule=defdslimp_rule)"
)
WHOLESET = "\n".join([COST, SUPPLY, DEMAND, DEFBASIS, DEFXIMP, DEFSSLIMP, DEFDSLIMP])

records = [
    {"description": (
        "The total transportation cost gathers the cost of every shipment across all lanes. "
        "For each plant and market pair, value the cases shipped on that lane at that lane's "
        "per case transport cost, and set the total cost variable equal to the sum of these "
        "amounts over every plant and market pair."),
     "expected_pyomo": COST},
    {"description": (
        "Each plant cannot ship out more than it has available, and any capacity it does not "
        "use is recorded as unused supply. For each plant, the total cases shipped from that "
        "plant to all markets must equal its supply capacity less its unused supply."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "Each market must receive at least the cases it demands, and anything delivered beyond "
        "that is recorded as surplus. For each market, the total cases shipped into that market "
        "from all plants must equal its demand plus its surplus."),
     "expected_pyomo": DEMAND},
    {"description": (
        "The number of variables marked as basic is fixed by the size of the problem. Across all "
        "the shipment indicators, all the supply slack indicators, and all the demand slack "
        "indicators, the count that are switched on must equal the number of plants plus the "
        "number of markets."),
     "expected_pyomo": DEFBASIS},
    {"description": (
        "A shipment can only flow on a lane when that lane's indicator is switched on. For each "
        "plant and market pair, the cases shipped on that lane must not exceed that lane's "
        "largest possible flow when the indicator is on, and must be zero when the indicator is "
        "off."),
     "expected_pyomo": DEFXIMP},
    {"description": (
        "A plant's unused supply can only be positive when its supply slack indicator is switched "
        "on. For each plant, the unused supply must not exceed that plant's supply capacity when "
        "the indicator is on, and must be zero when the indicator is off."),
     "expected_pyomo": DEFSSLIMP},
    {"description": (
        "A market's surplus can only be positive when its demand slack indicator is switched on. "
        "For each market, the surplus must not exceed that market's demand when the indicator is "
        "on, and must be zero when the indicator is off."),
     "expected_pyomo": DEFDSLIMP},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "allbases_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
