#!/usr/bin/env python
"""Builder for the epscm_lp (eps-constraint power generation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "epscm_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "p", "members": ["Lignite", "Oil", "Gas", "RES"],
         "doc": "the power generation units, each a technology that can produce electricity"},
        {"name": "i", "members": ["base", "middle", "peak"],
         "doc": "the load areas, the segments of the demand profile to be served"},
        {"name": "pi", "members": [["Lignite", "base"], ["Lignite", "middle"], ["Oil", "middle"], ["Oil", "peak"], ["Gas", "base"], ["Gas", "middle"], ["Gas", "peak"], ["RES", "base"], ["RES", "peak"]],
         "doc": "the feasible unit-load pairs; a pair is present only when that generation unit is allowed to serve that load area, so production is defined only over these pairs"},
        {"name": "es", "members": ["Lignite", "RES"],
         "doc": "the subset of generation units that count as endogenous sources, that is domestically sourced generation"},
    ],
    "params": [
        {"name": "ad", "index": "", "kind": "demand",
         "doc": "the total annual electricity demand to be met, in GWh"},
        {"name": "df", "index": "i", "kind": "fraction",
         "doc": "the fraction of total annual demand that falls in each load area, a dimensionless share that sums to one over the load areas"},
        {"name": "capacity", "index": "p", "kind": "capacity",
         "doc": "the maximum annual production each generation unit can deliver across all the load areas it serves, in GWh"},
        {"name": "cost", "index": "p", "kind": "cost",
         "doc": "the production cost of each generation unit, in dollars per MWh"},
        {"name": "co2", "index": "p", "kind": "emission",
         "doc": "the CO2 emission factor of each generation unit, in tons per MWh"},
        {"name": "eps_co2", "index": "", "kind": "bound",
         "doc": "the upper bound allowed on total CO2 emissions, an eps-constraint bound carried over from the multiobjective sweep"},
        {"name": "eps_es", "index": "", "kind": "bound",
         "doc": "the lower bound required on total endogenous production, an eps-constraint bound carried over from the multiobjective sweep"},
    ],
    "vars": [
        {"name": "x", "index": "pi", "domain": "NonNegativeReals",
         "doc": "the production level of each feasible unit-load pair, in GWh"},
        {"name": "z_cost", "index": "", "domain": "Reals",
         "doc": "the total production cost objective value"},
        {"name": "z_co2", "index": "", "domain": "Reals",
         "doc": "the total CO2 emissions objective value"},
        {"name": "z_es", "index": "", "domain": "Reals",
         "doc": "the total endogenous production objective value"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z_cost"},
}

NARRATIVE = (
    "We plan electricity generation across a set of generation units, each able to serve certain "
    "segments of the demand profile. For each unit and the load areas it is allowed to serve, we "
    "decide how much electricity it produces over the year. Producing electricity carries a per-unit "
    "cost, generates CO2 emissions, and some units count as domestically sourced endogenous "
    "generation. We track total cost, total emissions, and total endogenous production as accounting "
    "quantities. The objective is to make the total production cost as small as possible."
)

OBJCOST = (
    "def objcost_rule(model):\n"
    "    return sum(model.cost[p] * model.x[p, i] for (p, i) in model.pi) == model.z_cost\n"
    "model.objcost = Constraint(rule=objcost_rule)"
)
OBJCO2 = (
    "def objco2_rule(model):\n"
    "    return sum(model.co2[p] * model.x[p, i] for (p, i) in model.pi) == model.z_co2\n"
    "model.objco2 = Constraint(rule=objco2_rule)"
)
OBJES = (
    "def objes_rule(model):\n"
    "    return sum(model.x[p, i] for (p, i) in model.pi if p in model.es) == model.z_es\n"
    "model.objes = Constraint(rule=objes_rule)"
)
DEFCAP = (
    "def defcap_rule(model, p):\n"
    "    return sum(model.x[pp, i] for (pp, i) in model.pi if pp == p) <= model.capacity[p]\n"
    "model.defcap = Constraint(model.p, rule=defcap_rule)"
)
DEFDEM = (
    "def defdem_rule(model, i):\n"
    "    return sum(model.x[p, ii] for (p, ii) in model.pi if ii == i) >= model.ad * model.df[i]\n"
    "model.defdem = Constraint(model.i, rule=defdem_rule)"
)
EPS_CO2 = (
    "model.eps_con_co2 = Constraint(expr=model.z_co2 <= model.eps_co2)"
)
EPS_ES = (
    "model.eps_con_es = Constraint(expr=model.z_es >= model.eps_es)"
)

WHOLESET = "\n".join([OBJCOST, OBJCO2, OBJES, DEFCAP, DEFDEM, EPS_CO2, EPS_ES])

records = [
    {"description": (
        "Total production cost adds up the cost of every unit's production across the load areas it "
        "serves. For each feasible unit-load pair, value its production at that unit's per-unit cost, "
        "and set the total cost accounting quantity equal to the sum of these amounts over all the "
        "pairs."),
     "expected_pyomo": OBJCOST},
    {"description": (
        "Total CO2 emissions add up the emissions from every unit's production across the load areas "
        "it serves. For each feasible unit-load pair, multiply its production by that unit's emission "
        "factor, and set the total emissions accounting quantity equal to the sum of these amounts "
        "over all the pairs."),
     "expected_pyomo": OBJCO2},
    {"description": (
        "Total endogenous production adds up the production of only the units that count as "
        "endogenous sources, across the load areas they serve. Set the total endogenous accounting "
        "quantity equal to the sum of production over the feasible unit-load pairs whose unit is an "
        "endogenous source."),
     "expected_pyomo": OBJES},
    {"description": (
        "Each generation unit has a limited annual output. For each unit, the total production it "
        "delivers summed over the load areas it serves must not exceed that unit's capacity."),
     "expected_pyomo": DEFCAP},
    {"description": (
        "Demand in each load area must be met. For each load area, the total production delivered to "
        "it summed over the units that serve it must be at least the share of total annual demand "
        "that falls in that load area."),
     "expected_pyomo": DEFDEM},
    {"description": (
        "Total CO2 emissions must stay within the allowed emissions ceiling. The total emissions "
        "accounting quantity must not exceed the CO2 upper bound."),
     "expected_pyomo": EPS_CO2},
    {"description": (
        "Total endogenous production must meet the required endogenous floor. The total endogenous "
        "accounting quantity must be at least the endogenous lower bound."),
     "expected_pyomo": EPS_ES},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, set the "
        "total cost accounting quantity equal to the cost-weighted sum of production over every "
        "feasible unit-load pair. Second, set the total emissions accounting quantity equal to the "
        "emission-weighted sum of production over every feasible unit-load pair. Third, set the total "
        "endogenous accounting quantity equal to the sum of production over the feasible pairs whose "
        "unit is an endogenous source. Fourth, for each generation unit keep its total production "
        "across the load areas it serves within that unit's capacity. Fifth, for each load area "
        "ensure the total production delivered to it meets at least its share of total annual demand. "
        "Sixth, keep the total emissions accounting quantity within the allowed CO2 ceiling. Finally, "
        "ensure the total endogenous accounting quantity meets the required endogenous floor."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "epscm_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
