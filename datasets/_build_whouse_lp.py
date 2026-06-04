#!/usr/bin/env python
"""Builder for the whouse_lp (warehouse) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "whouse_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "t", "members": ["q-1", "q-2", "q-3", "q-4"],
         "doc": "the time periods in chronological order, given as quarters; the first member is the opening period and each later member follows the one before it"},
    ],
    "params": [
        {"name": "price", "index": "t", "kind": "price",
         "doc": "the selling and buying price per unit in each period, in dollars per unit"},
        {"name": "istock", "index": "t", "kind": "supply",
         "doc": "an externally injected stock quantity that arrives in a period, in units; zero in periods with no injection"},
        {"name": "storecost", "index": "", "kind": "cost",
         "doc": "the storage cost charged for each unit held in the warehouse for one period, in dollars per unit per quarter"},
        {"name": "storecap", "index": "", "kind": "capacity",
         "doc": "the maximum number of units the warehouse can hold in any period, in units"},
    ],
    "vars": [
        {"name": "stock", "index": "t", "domain": "NonNegativeReals",
         "doc": "the number of units held in the warehouse at the end of each period"},
        {"name": "sell", "index": "t", "domain": "NonNegativeReals",
         "doc": "the number of units sold in each period"},
        {"name": "buy", "index": "t", "domain": "NonNegativeReals",
         "doc": "the number of units bought in each period"},
        {"name": "cost", "index": "", "domain": "Reals",
         "doc": "the total net cost over all periods, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We operate a warehouse over a sequence of quarters. In each quarter we decide how "
    "many units to buy, how many to sell, and how many to keep in storage. Buying and "
    "selling happen at a known per-unit price that changes from quarter to quarter, and "
    "holding units in the warehouse incurs a per-unit storage charge each quarter. The "
    "objective is to make the total net cost over the whole horizon as small as possible."
)

STOCK_BALANCE = (
    "def stock_balance_rule(model, tt):\n"
    "    t_list = list(model.t.data())\n"
    "    idx = t_list.index(tt)\n"
    "    prev = t_list[idx - 1] if idx > 0 else None\n"
    "    if prev is None:\n"
    "        return model.stock[tt] - model.buy[tt] + model.sell[tt] == model.istock[tt]\n"
    "    return model.stock[tt] - model.stock[prev] - model.buy[tt] + model.sell[tt] == model.istock[tt]\n"
    "model.stock_balance = Constraint(model.t, rule=stock_balance_rule)"
)
CAPACITY = (
    "def capacity_rule(model, tt):\n"
    "    return model.stock[tt] <= model.storecap\n"
    "model.capacity = Constraint(model.t, rule=capacity_rule)"
)
ACCOUNTING = (
    "def accounting_rule(model):\n"
    "    return model.cost == sum(model.price[tt] * (model.buy[tt] - model.sell[tt]) + model.storecost * model.stock[tt] for tt in model.t)\n"
    "model.accounting = Constraint(rule=accounting_rule)"
)
WHOLESET = "\n".join([STOCK_BALANCE, CAPACITY, ACCOUNTING])

records = [
    {"description": (
        "The units held in the warehouse at the end of each period must account for what "
        "carried over and what moved that period. For each period, the ending stock equals "
        "the stock left over from the immediately preceding period plus what was bought, "
        "minus what was sold, plus any externally injected stock that arrived that period. "
        "In the very first period there is no preceding period, so nothing carries over into it."),
     "expected_pyomo": STOCK_BALANCE},
    {"description": (
        "The warehouse has a limited holding capacity. For each period, the units held in "
        "storage must not exceed the warehouse capacity."),
     "expected_pyomo": CAPACITY},
    {"description": (
        "The total net cost adds up the buying and selling activity together with the storage "
        "charges across every period. For each period, value the units bought net of the units "
        "sold at that period's price, and add the storage charge applied to the units held that "
        "period. Set the total cost variable equal to the sum of these amounts over all periods."),
     "expected_pyomo": ACCOUNTING},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "whouse_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
