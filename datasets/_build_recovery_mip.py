#!/usr/bin/env python
"""Builder for the recovery_mip (reverse-logistics network) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "recovery_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "K", "members": "the primary customer zones that surrender used products, indexed 0..len(K)-1",
         "doc": "the set of primary customer zones; each zone returns a known quantity of used products that must all be collected"},
        {"name": "I", "members": "the candidate collection/inspection center locations, indexed 0..len(I)-1",
         "doc": "the set of candidate sites where a collection and inspection center may be opened; returned products arrive here, are inspected, then split into a recoverable stream and a scrapped stream"},
        {"name": "J", "members": "the candidate recovery center locations, indexed 0..len(J)-1",
         "doc": "the set of candidate sites where a recovery (remanufacturing) center may be opened; recoverable products are processed here"},
        {"name": "M", "members": "the candidate redistribution center locations, indexed 0..len(M)-1",
         "doc": "the set of candidate sites where a redistribution center may be opened; recovered products pass through here on the way back to customers"},
        {"name": "L", "members": "the secondary-market customer zones, indexed 0..len(L)-1",
         "doc": "the set of second-market customer zones that demand recovered products"},
        {"name": "N", "members": "the disposal center locations, indexed 0..len(N)-1",
         "doc": "the set of disposal centers that receive scrapped products"},
    ],
    "params": [
        {"name": "d", "index": "L", "kind": "demand",
         "doc": "the demand for recovered products of each second-market customer zone, in product units"},
        {"name": "r", "index": "K", "kind": "supply",
         "doc": "the quantity of used products that each primary customer zone returns and that must be fully collected, in product units"},
        {"name": "s", "index": "", "kind": "fraction",
         "doc": "the average disposal fraction; a single number between 0 and 1 giving the share of collected returns that is scrapped rather than recovered, so the recoverable share is one minus this value"},
        {"name": "cc", "index": "I", "kind": "capacity",
         "doc": "the throughput capacity for handling returned products at each candidate collection/inspection center, in product units"},
        {"name": "ce", "index": "M", "kind": "capacity",
         "doc": "the throughput capacity for handling recovered products at each candidate redistribution center, in product units"},
        {"name": "cr", "index": "J", "kind": "capacity",
         "doc": "the throughput capacity for handling recoverable products at each candidate recovery center, in product units"},
        {"name": "cd", "index": "N", "kind": "capacity",
         "doc": "the throughput capacity for handling scrapped products at each disposal center, in product units"},
        {"name": "f", "index": "I", "kind": "cost",
         "doc": "the fixed cost of opening a collection/inspection center at each candidate site"},
        {"name": "g", "index": "J", "kind": "cost",
         "doc": "the fixed cost of opening a recovery center at each candidate site"},
        {"name": "h", "index": "M", "kind": "cost",
         "doc": "the fixed cost of opening a redistribution center at each candidate site"},
        {"name": "c", "index": "K,I", "kind": "cost",
         "doc": "the per-unit shipping cost of returned products from a customer zone to a collection/inspection center"},
        {"name": "a", "index": "I,J", "kind": "cost",
         "doc": "the per-unit shipping cost of recoverable products from a collection/inspection center to a recovery center"},
        {"name": "b", "index": "J,M", "kind": "cost",
         "doc": "the per-unit shipping cost of recovered products from a recovery center to a redistribution center"},
        {"name": "e", "index": "M,L", "kind": "cost",
         "doc": "the per-unit shipping cost of recovered products from a redistribution center to a second-market customer zone"},
        {"name": "v", "index": "I,N", "kind": "cost",
         "doc": "the per-unit shipping cost of scrapped products from a collection/inspection center to a disposal center"},
        {"name": "pi", "index": "L", "kind": "penalty",
         "doc": "the per-unit penalty cost for demand of a second-market customer that is left unsatisfied"},
    ],
    "vars": [
        {"name": "X", "index": "K,I", "domain": "NonNegativeReals",
         "doc": "the quantity of returned products shipped from a customer zone to a collection/inspection center"},
        {"name": "U", "index": "I,J", "domain": "NonNegativeReals",
         "doc": "the quantity of recoverable products shipped from a collection/inspection center to a recovery center"},
        {"name": "P", "index": "J,M", "domain": "NonNegativeReals",
         "doc": "the quantity of recovered products shipped from a recovery center to a redistribution center"},
        {"name": "Q", "index": "M,L", "domain": "NonNegativeReals",
         "doc": "the quantity of recovered products shipped from a redistribution center to a second-market customer zone"},
        {"name": "T", "index": "I,N", "domain": "NonNegativeReals",
         "doc": "the quantity of scrapped products shipped from a collection/inspection center to a disposal center"},
        {"name": "delta", "index": "L", "domain": "NonNegativeReals",
         "doc": "the quantity of unsatisfied demand at each second-market customer zone"},
        {"name": "Y", "index": "I", "domain": "Binary",
         "doc": "equals 1 if a collection/inspection center is opened at the site and 0 otherwise"},
        {"name": "Z", "index": "J", "domain": "Binary",
         "doc": "equals 1 if a recovery center is opened at the site and 0 otherwise"},
        {"name": "W", "index": "M", "domain": "Binary",
         "doc": "equals 1 if a redistribution center is opened at the site and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We design a reverse-logistics network that collects used products from primary customers, "
    "recovers what it can, and redistributes recovered goods to a second market while disposing of "
    "the rest. We decide which collection/inspection centers, recovery centers, and redistribution "
    "centers to open, and we decide how much product to ship along every link of the network: from "
    "customers to collection/inspection centers, on to recovery centers, then to redistribution "
    "centers, out to second-market customers, and from collection/inspection centers to disposal "
    "centers for the scrapped portion. We also track any second-market demand we leave unmet. The "
    "objective is to minimize the total of fixed opening costs, per-unit shipping costs along all "
    "links, and penalty costs for unsatisfied demand."
)

# Sizes are read off the model: r->K, cc/Y->I, cr/Z->J, ce/W->M, d/pi->L, cd->N.
C1 = (
    "def constraint_1_rule(model, l):\n"
    "    nM = len(model.ce)\n"
    "    return sum(model.Q[m, l] for m in range(nM)) + model.delta[l] - model.d[l] >= 0\n"
    "model.constraint_1 = Constraint(range(len(model.d)), rule=constraint_1_rule)"
)
C2 = (
    "def constraint_2_rule(model, k):\n"
    "    nI = len(model.cc)\n"
    "    return sum(model.X[k, i] for i in range(nI)) - model.r[k] == 0\n"
    "model.constraint_2 = Constraint(range(len(model.r)), rule=constraint_2_rule)"
)
C3 = (
    "def constraint_3_rule(model, i):\n"
    "    nJ = len(model.cr)\n"
    "    nK = len(model.r)\n"
    "    return sum(model.U[i, j] for j in range(nJ)) - (1 - model.s) * sum(model.X[k, i] for k in range(nK)) == 0\n"
    "model.constraint_3 = Constraint(range(len(model.cc)), rule=constraint_3_rule)"
)
C4 = (
    "def constraint_4_rule(model, i):\n"
    "    nN = len(model.cd)\n"
    "    nK = len(model.r)\n"
    "    return sum(model.T[i, n] for n in range(nN)) - model.s * sum(model.X[k, i] for k in range(nK)) == 0\n"
    "model.constraint_4 = Constraint(range(len(model.cc)), rule=constraint_4_rule)"
)
C5 = (
    "def constraint_5_rule(model, m):\n"
    "    nJ = len(model.cr)\n"
    "    nL = len(model.d)\n"
    "    return sum(model.P[j, m] for j in range(nJ)) - sum(model.Q[m, l] for l in range(nL)) == 0\n"
    "model.constraint_5 = Constraint(range(len(model.ce)), rule=constraint_5_rule)"
)
C6 = (
    "def constraint_6_rule(model, j):\n"
    "    nM = len(model.ce)\n"
    "    nI = len(model.cc)\n"
    "    return sum(model.P[j, m] for m in range(nM)) - sum(model.U[i, j] for i in range(nI)) <= 0\n"
    "model.constraint_6 = Constraint(range(len(model.cr)), rule=constraint_6_rule)"
)
C7 = (
    "def constraint_7_rule(model, i):\n"
    "    nK = len(model.r)\n"
    "    return sum(model.X[k, i] for k in range(nK)) - model.Y[i] * model.cc[i] <= 0\n"
    "model.constraint_7 = Constraint(range(len(model.cc)), rule=constraint_7_rule)"
)
C8 = (
    "def constraint_8_rule(model, j):\n"
    "    nI = len(model.cc)\n"
    "    return sum(model.U[i, j] for i in range(nI)) - model.Z[j] * model.cr[j] <= 0\n"
    "model.constraint_8 = Constraint(range(len(model.cr)), rule=constraint_8_rule)"
)
C9 = (
    "def constraint_9_rule(model, m):\n"
    "    nJ = len(model.cr)\n"
    "    return sum(model.P[j, m] for j in range(nJ)) - model.W[m] * model.ce[m] <= 0\n"
    "model.constraint_9 = Constraint(range(len(model.ce)), rule=constraint_9_rule)"
)
C10 = (
    "def constraint_10_rule(model, n):\n"
    "    nI = len(model.cc)\n"
    "    return sum(model.T[i, n] for i in range(nI)) - model.cd[n] <= 0\n"
    "model.constraint_10 = Constraint(range(len(model.cd)), rule=constraint_10_rule)"
)
WHOLESET = "\n".join([C1, C2, C3, C4, C5, C6, C7, C8, C9, C10])

records = [
    {"description": (
        "Each second-market customer zone must have its demand for recovered products fully accounted "
        "for. For every such zone, the total amount of recovered product delivered into it from all "
        "redistribution centers, together with the amount of its demand recorded as unmet, must be at "
        "least its demand. This lets deliveries to a zone exceed its demand while keeping the recorded "
        "shortfall from going negative."),
     "expected_pyomo": C1},
    {"description": (
        "Every primary customer zone must surrender all of its returned products. For each such zone, "
        "the total quantity of returns it ships out across all collection and inspection centers must "
        "exactly equal the amount it returns."),
     "expected_pyomo": C2},
    {"description": (
        "At each collection and inspection center the recoverable portion of what arrives must flow on "
        "without accumulation. For every such center, the total amount of recoverable product it ships "
        "out to recovery centers must equal the recoverable share of all the returns it receives from "
        "customer zones, where the recoverable share is what remains after the disposal fraction is "
        "removed."),
     "expected_pyomo": C3},
    {"description": (
        "At each collection and inspection center the scrapped portion of what arrives must flow on to "
        "disposal without accumulation. For every such center, the total amount of scrapped product it "
        "ships out to disposal centers must equal the disposal share of all the returns it receives "
        "from customer zones."),
     "expected_pyomo": C4},
    {"description": (
        "Each redistribution center must pass through exactly what it receives. For every such center, "
        "the total amount of recovered product arriving from all recovery centers must equal the total "
        "amount it sends out to all second-market customer zones."),
     "expected_pyomo": C5},
    {"description": (
        "Each recovery center cannot send out more than it takes in. For every such center, the total "
        "amount of recovered product it ships to redistribution centers must not exceed the total "
        "amount of recoverable product it receives from collection and inspection centers."),
     "expected_pyomo": C6},
    {"description": (
        "A collection and inspection center can only handle returns if it is opened, and never beyond "
        "its capacity. For every candidate site, the total returns it receives from all customer zones "
        "must not exceed its handling capacity when it is opened, and must be zero when it is not "
        "opened."),
     "expected_pyomo": C7},
    {"description": (
        "A recovery center can only handle recoverable products if it is opened, and never beyond its "
        "capacity. For every candidate site, the total recoverable product it receives from all "
        "collection and inspection centers must not exceed its handling capacity when it is opened, and "
        "must be zero when it is not opened."),
     "expected_pyomo": C8},
    {"description": (
        "A redistribution center can only handle recovered products if it is opened, and never beyond "
        "its capacity. For every candidate site, the total recovered product it receives from all "
        "recovery centers must not exceed its handling capacity when it is opened, and must be zero "
        "when it is not opened."),
     "expected_pyomo": C9},
    {"description": (
        "No disposal center may receive more scrapped product than it can handle. For every disposal "
        "center, the total scrapped product arriving from all collection and inspection centers must "
        "not exceed its handling capacity."),
     "expected_pyomo": C10},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "recovery_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
