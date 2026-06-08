#!/usr/bin/env python
"""Builder for the trnsindic_mip (fixed-charge transportation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "trnsindic_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the set of canning plants that can ship product, each a supply origin"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the set of markets that receive product, each a demand destination"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the production capacity of each plant, in cases; the most that plant can ship out across all markets"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the demand at each market, in cases; the amount that market must receive"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the per-case transport cost on the arc from a plant to a market, in thousands of dollars per case"},
        {"name": "fixcost", "index": "i,j", "kind": "cost",
         "doc": "the fixed charge incurred on a plant-to-market arc whenever that arc is used at all, in thousands of dollars; charged once regardless of volume"},
        {"name": "minshipping", "index": "", "kind": "threshold",
         "doc": "the minimum number of cases that must flow on any arc that is used, in cases; a single scalar applying to every arc"},
        {"name": "bigM", "index": "", "kind": "big-M",
         "doc": "a single large constant, set to the largest plant capacity, used to cap flow on an arc to zero when that arc is not used; a scalar"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the shipment quantity sent on each plant-to-market arc, in cases"},
        {"name": "use", "index": "i,j", "domain": "Binary",
         "doc": "arc-use indicator; equals 1 if the plant-to-market arc carries any shipment and 0 otherwise"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total transportation cost over all arcs, in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We plan shipments of a product from a set of canning plants to a set of markets. For each "
    "plant-to-market arc we decide how many cases to ship and whether to use that arc at all. "
    "Shipping incurs a per-case transport cost that varies by arc, and using an arc at all incurs "
    "a one-time fixed charge specific to that arc. The objective is to minimize the total "
    "transportation cost, combining the per-case shipping costs and the fixed charges of the arcs "
    "that are used."
)

SUPPLY = (
    "def supply_rule(m, i):\n"
    "    return sum(m.x[i, j] for j in m.j) <= m.a[i]\n"
    "model.supply = Constraint(model.i, rule=supply_rule)"
)
DEMAND = (
    "def demand_rule(m, j):\n"
    "    return sum(m.x[i, j] for i in m.i) >= m.b[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)
MINSHIP = (
    "def minship_rule(m, i, j):\n"
    "    return m.x[i, j] >= m.minshipping * m.use[i, j]\n"
    "model.minship = Constraint(model.i, model.j, rule=minship_rule)"
)
MAXSHIP = (
    "def maxship_rule(m, i, j):\n"
    "    return m.x[i, j] <= m.bigM * m.use[i, j]\n"
    "model.maxship = Constraint(model.i, model.j, rule=maxship_rule)"
)
COST = (
    "def cost_rule(m):\n"
    "    return m.z == sum(m.c[i, j] * m.x[i, j] + m.fixcost[i, j] * m.use[i, j] for i in m.i for j in m.j)\n"
    "model.cost = Constraint(rule=cost_rule)"
)
WHOLESET = "\n".join([SUPPLY, DEMAND, MINSHIP, MAXSHIP, COST])

SUPPLY_D = (
    "Each plant can ship out no more than its production capacity. For every plant, the total "
    "amount shipped from it across all markets must not exceed that plant's capacity.")
DEMAND_D = (
    "Every market must receive at least the amount it demands. For each market, the total amount "
    "shipped into it from all plants must be at least its demand.")
MINSHIP_D = (
    "If an arc is used to ship product, the amount sent on it must meet a minimum shipping level. "
    "For each plant-to-market arc, the amount shipped must be at least the minimum shipping "
    "quantity whenever that arc is marked as used, and may be nothing when the arc is not used.")
MAXSHIP_D = (
    "No product may flow on an arc unless that arc is marked as used. For each plant-to-market arc, "
    "the amount shipped must be zero when the arc is not used, and otherwise may go up to a large "
    "cap that does not otherwise restrict the flow.")
COST_D = (
    "The total transportation cost gathers both the per-case shipping costs and the one-time fixed "
    "charges. Across every plant-to-market arc, value the cases shipped at that arc's per-case "
    "transport cost and add the arc's fixed charge whenever the arc is used. Set the total cost "
    "equal to the sum of these amounts over all arcs.")

WHOLESET_D = (
    "To build the complete model, enforce the following relationships in order. "
    "First, each plant can ship out no more than its production capacity across all markets. "
    "Second, every market must receive at least the amount it demands from across all plants. "
    "Third, any arc that is used must carry at least a minimum shipping quantity, while an unused "
    "arc may carry nothing. "
    "Fourth, no product may flow on an arc unless that arc is marked as used, capping the flow on "
    "an unused arc to zero. "
    "Finally, set the total transportation cost equal to the per-case shipping costs over all arcs "
    "plus the one-time fixed charge on each arc that is used."
)

records = [
    {"description": SUPPLY_D, "expected_pyomo": SUPPLY},
    {"description": DEMAND_D, "expected_pyomo": DEMAND},
    {"description": MINSHIP_D, "expected_pyomo": MINSHIP},
    {"description": MAXSHIP_D, "expected_pyomo": MAXSHIP},
    {"description": COST_D, "expected_pyomo": COST},
    {"description": WHOLESET_D, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "trnsindic_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
