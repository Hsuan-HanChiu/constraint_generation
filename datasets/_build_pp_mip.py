#!/usr/bin/env python
"""Builder for the pp_mip (single-stage multiproduct plant planning) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "pp_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "C", "members": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"],
         "doc": "the set of customers the plant sells to"},
        {"name": "I", "members": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
         "doc": "the set of products the plant can manufacture; this is the same collection of products referred to as the predecessor product in a sequencing pair"},
        {"name": "J", "members": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
         "doc": "the same set of products as I, used as the second product when referring to an ordered pair of products such as a changeover from one product to another"},
        {"name": "W", "members": [1, 2, 3, 4, 5, 6, 7, 8],
         "doc": "the planning weeks in chronological order, indexed by consecutive integers starting at 1; week 1 is the first week of the horizon and each later week immediately follows the previous one"},
    ],
    "params": [
        {"name": "ps", "index": "I,C", "kind": "price",
         "doc": "unit selling price of a product when sold to a customer, in money per ton"},
        {"name": "cb", "index": "I,C", "kind": "cost",
         "doc": "unit backlog penalty cost charged per ton of a product still owed to a customer, in money per ton"},
        {"name": "ci", "index": "I", "kind": "cost",
         "doc": "unit inventory holding cost charged per ton of a product carried in inventory, in money per ton"},
        {"name": "tau", "index": "I,J", "kind": "time",
         "doc": "the changeover time needed when the machine switches directly from making the first product to making the second product of the pair, in hours; the changeover from a product to itself is zero"},
        {"name": "cc", "index": "I,J", "kind": "cost",
         "doc": "the changeover cost incurred when the machine switches directly from the first product to the second product of the pair, in money"},
        {"name": "d", "index": "C,I,W", "kind": "demand",
         "doc": "demand of a customer for a product in a given week, in tons; zero when a customer has no demand for that product in that week"},
        {"name": "ri", "index": "I", "kind": "rate",
         "doc": "processing rate of a product, in tons produced per hour of processing time"},
        {"name": "t_l", "index": "", "kind": "bound",
         "doc": "the minimum processing time that must be devoted to a product in a week if that product is processed at all, in hours; a single scalar value applying to every product and week"},
        {"name": "t_u", "index": "", "kind": "bound",
         "doc": "the total amount of machine time available in a week, in hours; also serves as the upper bound on the processing time of any single product in a week"},
        {"name": "bigm", "index": "", "kind": "big-M",
         "doc": "a single large constant used to relax the order-index and sequencing inequalities when the relevant assignment indicators are off, so that those inequalities do not bind in that case; a scalar"},
    ],
    "vars": [
        {"name": "e", "index": "I,W", "domain": "Binary",
         "doc": "equals 1 if the product is processed during the week and 0 otherwise"},
        {"name": "f", "index": "I,W", "domain": "Binary",
         "doc": "equals 1 if the product is the first one processed in the week and 0 otherwise"},
        {"name": "l", "index": "I,W", "domain": "Binary",
         "doc": "equals 1 if the product is the last one processed in the week and 0 otherwise"},
        {"name": "z", "index": "I,J,W", "domain": "Binary",
         "doc": "equals 1 if the first product immediately precedes the second product within the week and 0 otherwise"},
        {"name": "zf", "index": "I,J,W", "domain": "NonNegativeReals in the unit interval",
         "doc": "the cross-week changeover indicator, taking a value between 0 and 1, equal to 1 if the first product was the last one made in the previous week and the second product is the first one made in this week; the changeover that bridges the boundary from the previous week into this week"},
        {"name": "o", "index": "I,W", "domain": "NonNegativeReals",
         "doc": "the order index giving the position of the product in the processing sequence within the week; larger means later in the sequence, and it is driven to zero for products not processed that week"},
        {"name": "p", "index": "I,W", "domain": "NonNegativeReals",
         "doc": "the amount of the product produced during the week, in tons"},
        {"name": "s", "index": "C,I,W", "domain": "NonNegativeReals",
         "doc": "the sales volume of a product delivered to a customer during the week, in tons"},
        {"name": "t", "index": "I,W", "domain": "NonNegativeReals",
         "doc": "the processing time devoted to the product during the week, in hours"},
        {"name": "v", "index": "I,W", "domain": "NonNegativeReals",
         "doc": "the inventory of the product carried at the end of the week, in tons"},
        {"name": "delta", "index": "C,I,W", "domain": "NonNegativeReals",
         "doc": "the backlog of a product still owed to a customer at the end of the week, in tons"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We plan the medium-term operation of a single-stage plant that makes several products on one "
    "processing machine over a horizon of weeks. In each week we decide which products to run, the "
    "order in which they run, how long each one is processed and how much of it is produced, how "
    "much to sell to each customer, and how much inventory and customer backlog to carry into the "
    "next week. Switching the machine from one product to the next takes changeover time and incurs "
    "a changeover cost, both within a week and across the boundary between consecutive weeks. The "
    "objective is to maximize total profit, taken as sales revenue minus the changeover costs, the "
    "backlog penalty costs, and the inventory holding costs."
)

FPC = (
    "def first_product_rule(model, w):\n"
    "    return sum(model.f[i, w] for i in model.I) == 1\n"
    "model.fpc = Constraint(model.W, rule=first_product_rule)"
)
LPC = (
    "def last_product_rule(model, w):\n"
    "    return sum(model.l[i, w] for i in model.I) == 1\n"
    "model.lpc = Constraint(model.W, rule=last_product_rule)"
)
FPW = (
    "def first_prod_in_week(model, i, w):\n"
    "    return model.f[i, w] <= model.e[i, w]\n"
    "model.fpw = Constraint(model.I, model.W, rule=first_prod_in_week)"
)
LPW = (
    "def last_prod_in_week(model, i, w):\n"
    "    return model.l[i, w] <= model.e[i, w]\n"
    "model.lpw = Constraint(model.I, model.W, rule=last_prod_in_week)"
)
SPC = (
    "def sequence_1(model, j, w):\n"
    "    return sum(model.z[i, j, w] for i in model.I if i != j) == model.e[j, w] - model.f[j, w]\n"
    "model.spc = Constraint(model.I, model.W, rule=sequence_1)"
)
SFC = (
    "def sequence_2(model, i, w):\n"
    "    return sum(model.z[i, j, w] for j in model.I if i != j) == model.e[i, w] - model.l[i, w]\n"
    "model.sfc = Constraint(model.I, model.W, rule=sequence_2)"
)
CHANGE_L = (
    "def sequence_3(model, j, w):\n"
    "    if w > 1:\n"
    "        return sum(model.zf[i, j, w] for i in model.I) == model.f[j, w]\n"
    "    return Constraint.Skip\n"
    "model.change_l = Constraint(model.I, model.W, rule=sequence_3)"
)
CHANGE_N = (
    "def sequence_4(model, i, w):\n"
    "    if w > 1:\n"
    "        return sum(model.zf[i, j, w] for j in model.I) == model.l[i, w-1]\n"
    "    return Constraint.Skip\n"
    "model.change_n = Constraint(model.I, model.W, rule=sequence_4)"
)
SUBRULE = (
    "def subtour_rule(model, i, j, w):\n"
    "    if i == j:\n"
    "        return Constraint.Skip\n"
    "    return model.o[j, w] - (model.o[i, w] + 1) >= -model.bigm * (1 - model.z[i, j, w])\n"
    "model.subrule = Constraint(model.I, model.I, model.W, rule=subtour_rule)"
)
IND = (
    "def index_rule(model, i, w):\n"
    "    return model.o[i, w] <= model.bigm * model.e[i, w]\n"
    "model.ind = Constraint(model.I, model.W, rule=index_rule)"
)
IND2A = (
    "def index2a_rule(model, i, w):\n"
    "    return model.o[i, w] >= model.f[i, w]\n"
    "model.ind2a = Constraint(model.I, model.W, rule=index2a_rule)"
)
IND2B = (
    "def index2b_rule(model, i, w):\n"
    "    return model.o[i, w] <= sum(model.e[j, w] for j in model.I)\n"
    "model.ind2b = Constraint(model.I, model.W, rule=index2b_rule)"
)
PLB = (
    "def time_lb(model, i, w):\n"
    "    return model.t[i, w] >= model.t_l * model.e[i, w]\n"
    "model.plb = Constraint(model.I, model.W, rule=time_lb)"
)
PUB = (
    "def time_ub(model, i, w):\n"
    "    return model.t[i, w] <= model.t_u * model.e[i, w]\n"
    "model.pub = Constraint(model.I, model.W, rule=time_ub)"
)
TT = (
    "def total_time(model, w):\n"
    "    if w == 1:\n"
    "        return Constraint.Skip\n"
    "    processing_time = sum(model.t[i, w] for i in model.I)\n"
    "    changeover_time = sum((model.z[i, j, w] + model.zf[i, j, w]) * model.tau[i, j] for i in model.I for j in model.I if i != j)\n"
    "    return processing_time + changeover_time <= model.t_u\n"
    "model.tt = Constraint(model.W, rule=total_time)"
)
TTF = (
    "def time_first(model, w):\n"
    "    if w != 1:\n"
    "        return Constraint.Skip\n"
    "    processing_time = sum(model.t[i, w] for i in model.I)\n"
    "    changeover_time = sum(model.z[i, j, w] * model.tau[i, j] for i in model.I for j in model.I if i != j)\n"
    "    return processing_time + changeover_time <= model.t_u\n"
    "model.ttf = Constraint(model.W, rule=time_first)"
)
PA = (
    "def production_amount(model, i, w):\n"
    "    return model.p[i, w] == model.ri[i] * model.t[i, w]\n"
    "model.pa = Constraint(model.I, model.W, rule=production_amount)"
)
BACK = (
    "def backlog_rule(model, c, i, w):\n"
    "    previous_backlog = model.delta[c, i, w-1] if w > 1 else 0\n"
    "    return model.delta[c, i, w] == previous_backlog + model.d[c, i, w] - model.s[c, i, w]\n"
    "model.back = Constraint(model.C, model.I, model.W, rule=backlog_rule)"
)
IC = (
    "def inventory_rule(model, i, w):\n"
    "    previous_inventory = model.v[i, w-1] if w > 1 else 0\n"
    "    return model.v[i, w] == previous_inventory + model.p[i, w] - sum(model.s[c, i, w] for c in model.C)\n"
    "model.ic = Constraint(model.I, model.W, rule=inventory_rule)"
)

ALL = [FPC, LPC, FPW, LPW, SPC, SFC, CHANGE_L, CHANGE_N, SUBRULE, IND, IND2A,
       IND2B, PLB, PUB, TT, TTF, PA, BACK, IC]
WHOLESET = "\n".join(ALL)

records = [
    {"description": (
        "In every week exactly one product must be designated as the first product processed that "
        "week. Across all products, the first-product designations in a week must add up to a single "
        "product."),
     "expected_pyomo": FPC},
    {"description": (
        "In every week exactly one product must be designated as the last product processed that "
        "week. Across all products, the last-product designations in a week must add up to a single "
        "product."),
     "expected_pyomo": LPC},
    {"description": (
        "A product can only be the first one processed in a week if it is actually processed that "
        "week. For each product and week, being marked as the first product is not allowed unless "
        "the product is run that week."),
     "expected_pyomo": FPW},
    {"description": (
        "A product can only be the last one processed in a week if it is actually processed that "
        "week. For each product and week, being marked as the last product is not allowed unless "
        "the product is run that week."),
     "expected_pyomo": LPW},
    {"description": (
        "Within a week, every product that is processed but is not the first one processed must be "
        "immediately preceded by exactly one other product. For each product and week, count the "
        "number of distinct other products that immediately precede it that week; this count must "
        "equal one when the product is processed and is not the first product, and zero otherwise."),
     "expected_pyomo": SPC},
    {"description": (
        "Within a week, every product that is processed but is not the last one processed must be "
        "immediately followed by exactly one other product. For each product and week, count the "
        "number of distinct other products that immediately follow it that week; this count must "
        "equal one when the product is processed and is not the last product, and zero otherwise."),
     "expected_pyomo": SFC},
    {"description": (
        "From the second week onward, the product that is first in a week must be picked up by "
        "exactly one cross-week changeover coming in from the previous week. For each product and "
        "each week after the first, the total of the incoming cross-week changeovers that end on "
        "that product must equal whether or not it is the first product of the week. This does not "
        "apply to the opening week."),
     "expected_pyomo": CHANGE_L},
    {"description": (
        "From the second week onward, the product that is last in the previous week must hand off "
        "through exactly one cross-week changeover into the current week. For each product and each "
        "week after the first, the total of the outgoing cross-week changeovers starting from that "
        "product must equal whether or not that product was the last product in the previous week. "
        "This does not apply to the opening week."),
     "expected_pyomo": CHANGE_N},
    {"description": (
        "Within a week, if one product immediately precedes another in the processing sequence, the "
        "follower's position in the order must come at least one step after the predecessor's "
        "position. For each ordered pair of distinct products and each week, the follower's order "
        "index must be at least one more than the predecessor's order index whenever that immediate "
        "precedence holds; when it does not hold the requirement is relaxed by a large allowance so "
        "it does not bind. This is stated only for pairs of two different products."),
     "expected_pyomo": SUBRULE},
    {"description": (
        "A product's order index in a week must be forced to zero unless the product is actually "
        "processed that week. For each product and week, the order index cannot exceed a large "
        "allowance that is available only when the product is processed and is zero otherwise."),
     "expected_pyomo": IND},
    {"description": (
        "If a product is the first one processed in a week, its order index must be strictly "
        "positive. For each product and week, the order index must be at least as large as the "
        "indicator that the product is the first one processed that week."),
     "expected_pyomo": IND2A},
    {"description": (
        "A product's order index in a week cannot exceed the total number of products processed "
        "that week. For each product and week, the order index is bounded above by the count of all "
        "products run that week."),
     "expected_pyomo": IND2B},
    {"description": (
        "If a product is processed in a week, at least a minimum amount of processing time must be "
        "devoted to it. For each product and week, the processing time must be at least the minimum "
        "required time when the product is run, and is forced to zero when it is not run."),
     "expected_pyomo": PLB},
    {"description": (
        "The processing time given to a product in a week cannot exceed the available weekly time "
        "when it is run, and must be zero when it is not run. For each product and week, the "
        "processing time is bounded above by the weekly time limit only if the product is processed "
        "that week."),
     "expected_pyomo": PUB},
    {"description": (
        "In every week after the first, the machine time used must fit within the weekly time "
        "available. For each such week, the total processing time of all products run that week plus "
        "the changeover time of every switch between two different products, counting both the "
        "within-week switches and the changeover bridging in from the previous week, must not exceed "
        "the available weekly time. This does not apply to the opening week."),
     "expected_pyomo": TT},
    {"description": (
        "In the first week, the machine time used must fit within the weekly time available. For the "
        "opening week, the total processing time of all products run plus the changeover time of "
        "every switch between two different products within that week must not exceed the available "
        "weekly time. This applies only to the first week, which has no incoming changeover from a "
        "previous week."),
     "expected_pyomo": TTF},
    {"description": (
        "The amount of a product produced in a week is determined by how long it is processed. For "
        "each product and week, the production quantity equals the product's processing rate "
        "multiplied by the processing time devoted to it that week."),
     "expected_pyomo": PA},
    {"description": (
        "The backlog owed to a customer for a product is carried forward and updated each week by "
        "what is newly demanded and what is delivered. For each customer, product, and week, the "
        "end-of-week backlog equals the backlog carried over from the previous week plus that week's "
        "demand minus that week's sales. In the first week there is no carried-over backlog."),
     "expected_pyomo": BACK},
    {"description": (
        "The inventory of a product is carried forward and updated each week by what is produced and "
        "what is sold. For each product and week, the end-of-week inventory equals the inventory "
        "carried over from the previous week plus that week's production minus the total sold to all "
        "customers that week. In the first week there is no carried-over inventory."),
     "expected_pyomo": IC},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "pp_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
