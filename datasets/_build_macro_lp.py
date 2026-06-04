#!/usr/bin/env python
"""Builder for the macro_lp (mini oil refining) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "macro_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "cr", "members": ["mid-c", "w-tex"],
         "doc": "the crude oil types that can be purchased and refined"},
        {"name": "p", "members": ["a-dist", "n-reform", "cc-dist", "cc-gas-oil", "hydro"],
         "doc": "the refining processes that turn crude into intermediate materials"},
        {"name": "c", "members": ["crude", "butane", "mid-c", "w-tex", "sr-gas", "sr-naphtha", "sr-dist", "sr-gas-oil", "sr-res", "rf-gas", "fuel-gas", "cc-gas", "cc-gas-oil", "hydro-res", "premium", "regular", "distillate", "fuel-oil"],
         "doc": "the material components that appear in process yields, including crude itself, the intermediate streams, and the final products"},
        {"name": "cf", "members": ["premium", "regular", "distillate", "fuel-oil", "fuel-gas"],
         "doc": "the final blended products that are sold"},
        {"name": "ci", "members": ["butane", "sr-gas", "sr-naphtha", "sr-dist", "sr-gas-oil", "sr-res", "rf-gas", "fuel-gas", "cc-gas", "cc-gas-oil", "hydro-res"],
         "doc": "the intermediate blending materials produced by the processes and combined into final products"},
        {"name": "cd", "members": ["butane"],
         "doc": "the subset of intermediate materials that may also be bought externally rather than only produced in house; this is a subset of the intermediate materials"},
        {"name": "m", "members": ["a-still", "reformer", "c-crack", "hydro"],
         "doc": "the capacity-limited processing units whose throughput is bounded"},
        {"name": "q", "members": ["octane", "vapor-pr", "density", "sulfur"],
         "doc": "the measurable quality attributes of a blended product, such as octane and sulfur content"},
        {"name": "lim", "members": ["lower", "upper"],
         "doc": "the two directions a quality specification can take, a lower bound or an upper bound"},
        {"name": "bp", "members": [["premium", "butane"], ["premium", "sr-gas"], ["premium", "rf-gas"], ["premium", "cc-gas"], ["premium", "sr-naphtha"], ["regular", "butane"], ["regular", "sr-gas"], ["regular", "rf-gas"], ["regular", "cc-gas"], ["regular", "sr-naphtha"], ["distillate", "sr-dist"], ["distillate", "sr-naphtha"], ["distillate", "sr-gas-oil"], ["distillate", "cc-gas-oil"], ["fuel-oil", "sr-gas-oil"], ["fuel-oil", "sr-res"], ["fuel-oil", "cc-gas-oil"], ["fuel-oil", "hydro-res"], ["fuel-gas", "fuel-gas"]],
         "doc": "the set of allowed pairs of a final product and an intermediate material; a pair belongs to this set exactly when that intermediate is permitted to be blended into that final product"},
    ],
    "params": [
        {"name": "a", "index": "cr,c,p", "kind": "yield",
         "doc": "the yield coefficient of component c from crude cr in process p; a positive value means the process produces that component and a negative value means it consumes it, per unit of process run; defaults to zero when a component is not involved in a process"},
        {"name": "b", "index": "m,p", "kind": "usage",
         "doc": "the amount of capacity of processing unit m consumed per unit of process p run; defaults to zero when a process does not use a unit"},
        {"name": "k", "index": "m", "kind": "capacity",
         "doc": "the available capacity of processing unit m"},
        {"name": "ur", "index": "cr", "kind": "bound",
         "doc": "the maximum quantity of crude oil of type cr that may be purchased"},
        {"name": "qs", "index": "lim,cf,q", "kind": "spec",
         "doc": "the quality specification bound for final product cf on attribute q in direction lim; a lower entry gives a minimum required level and an upper entry gives a maximum allowed level; a direction is present only for the product and attribute pairs that are actually specified"},
        {"name": "atc", "index": "cr,ci,q", "kind": "content",
         "doc": "the level of quality attribute q carried by intermediate material ci derived from crude cr; this is the attribute content per unit of that material that gets carried into a blend"},
        {"name": "pf", "index": "cf", "kind": "price",
         "doc": "the selling price per unit of final product cf"},
        {"name": "pr", "index": "cr", "kind": "cost",
         "doc": "the purchase cost per unit of crude oil of type cr"},
        {"name": "pd", "index": "cd", "kind": "cost",
         "doc": "the purchase cost per unit of an externally bought intermediate material"},
        {"name": "op", "index": "p", "kind": "cost",
         "doc": "the operating cost per unit of process p run"},
    ],
    "vars": [
        {"name": "z", "index": "cr,p", "domain": "NonNegativeReals",
         "doc": "how much of process p is run on crude cr, the process level"},
        {"name": "x", "index": "cf", "domain": "NonNegativeReals",
         "doc": "how much of final product cf is sold"},
        {"name": "u", "index": "cr", "domain": "NonNegativeReals",
         "doc": "how much crude oil of type cr is purchased"},
        {"name": "ui", "index": "cr,ci", "domain": "NonNegativeReals",
         "doc": "how much of intermediate material ci is purchased externally under crude cr"},
        {"name": "w", "index": "cr,ci,cf", "domain": "NonNegativeReals",
         "doc": "how much of intermediate material ci derived from crude cr is blended into final product cf, the blending level"},
        {"name": "phi", "index": "", "domain": "Reals",
         "doc": "total income"},
        {"name": "phir", "index": "", "domain": "Reals",
         "doc": "the revenue earned from selling final products"},
        {"name": "phip", "index": "", "domain": "Reals",
         "doc": "the cost of input materials, both crude and externally purchased intermediates"},
        {"name": "phiw", "index": "", "domain": "Reals",
         "doc": "the operating cost of running the processes"},
    ],
    "objective": {"sense": "maximize", "expr_var": "phir - phip - phiw"},
}

NARRATIVE = (
    "We run a small oil refinery. We buy crude oil of different types, run it through a set of "
    "refining processes to produce intermediate streams, optionally buy some intermediates from "
    "outside, then blend those intermediates into a handful of final products that we sell. We "
    "choose how much of each process to run on each crude, how much crude and how much external "
    "intermediate material to purchase, how to blend intermediates into each product, and how "
    "much of each product to sell. The goal is to maximize profit, which is sales revenue minus "
    "the cost of input materials minus the operating cost of the processes."
)

MBR = (
    "def mbr_rule(model, cr):\n"
    "    return sum(model.a[cr, 'crude', p] * model.z[cr, p] for p in model.p) + model.u[cr] >= 0\n"
    "model.mbr = Constraint(model.cr, rule=mbr_rule)"
)
MB = (
    "def mb_rule(model, cr, ci):\n"
    "    if ci in model.cd:\n"
    "        return sum(model.a[cr, ci, p] * model.z[cr, p] for p in model.p) + model.ui[cr, ci] >= sum(model.w[cr, ci, cf] for cf in model.cf if (cf, ci) in model.bp)\n"
    "    else:\n"
    "        return sum(model.a[cr, ci, p] * model.z[cr, p] for p in model.p) >= sum(model.w[cr, ci, cf] for cf in model.cf if (cf, ci) in model.bp)\n"
    "model.mb = Constraint(model.cr, model.ci, rule=mb_rule)"
)
CC = (
    "def cc_rule(model, m):\n"
    "    return sum(model.b[m, p] * sum(model.z[cr, p] for cr in model.cr) for p in model.p) <= model.k[m]\n"
    "model.cc = Constraint(model.m, rule=cc_rule)"
)
LCP = (
    "def lcp_rule(model, cr):\n"
    "    return model.u[cr] <= model.ur[cr]\n"
    "model.lcp = Constraint(model.cr, rule=lcp_rule)"
)
BB = (
    "def bb_rule(model, cf):\n"
    "    return model.x[cf] == sum(model.w[cr, ci, cf] for cr in model.cr for ci in model.ci if (cf, ci) in model.bp)\n"
    "model.bb = Constraint(model.cf, rule=bb_rule)"
)
QLB = (
    "def qlb_rule(model, cf, q):\n"
    "    if model.qs['lower', cf, q] != 0:\n"
    "        return sum(model.atc[cr, ci, q] * model.w[cr, ci, cf] for cr in model.cr for ci in model.ci) >= model.qs['lower', cf, q] * model.x[cf]\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.qlb = Constraint(model.cf, model.q, rule=qlb_rule)"
)
QUB = (
    "def qub_rule(model, cf, q):\n"
    "    if model.qs['upper', cf, q] != 0:\n"
    "        return sum(model.atc[cr, ci, q] * model.w[cr, ci, cf] for cr in model.cr for ci in model.ci) <= model.qs['upper', cf, q] * model.x[cf]\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.qub = Constraint(model.cf, model.q, rule=qub_rule)"
)
AREV = (
    "def arev_rule(model):\n"
    "    return model.phir == sum(model.pf[cf] * model.x[cf] for cf in model.cf)\n"
    "model.arev = Constraint(rule=arev_rule)"
)
AMAT = (
    "def amat_rule(model):\n"
    "    return model.phip == sum(model.pr[cr] * model.u[cr] for cr in model.cr) + sum(model.pd[cd] * model.ui[cr, cd] for cd in model.cd for cr in model.cr)\n"
    "model.amat = Constraint(rule=amat_rule)"
)
AOPER = (
    "def aoper_rule(model):\n"
    "    return model.phiw == sum(model.op[p] * sum(model.z[cr, p] for cr in model.cr) for p in model.p)\n"
    "model.aoper = Constraint(rule=aoper_rule)"
)

WHOLESET = "\n".join([MBR, MB, CC, LCP, BB, QLB, QUB, AREV, AMAT, AOPER])

records = [
    {"description": (
        "For each crude oil type, the refinery cannot consume more of that crude than it has "
        "available. Across all the refining processes, the net amount of crude produced or "
        "consumed by running those processes on that crude, taken together with the amount of "
        "that crude purchased, must be at least zero."),
     "expected_pyomo": MBR},
    {"description": (
        "For each crude type and each intermediate material, the supply of that intermediate "
        "must cover everything blended out of it. The amount of the intermediate produced by "
        "running the processes on that crude, plus any of it purchased from outside when that "
        "intermediate is one that can be bought externally, must be at least the total amount "
        "of that intermediate blended into the final products it is allowed to go into. For an "
        "intermediate that cannot be purchased externally, only the produced amount counts on "
        "the supply side."),
     "expected_pyomo": MB},
    {"description": (
        "Each processing unit has a limited capacity. For each unit, the total capacity it "
        "consumes, summed over every process across both crudes according to how much capacity "
        "each process draws from that unit, must not exceed the capacity available on that unit."),
     "expected_pyomo": CC},
    {"description": (
        "For each crude oil type, the amount of that crude purchased must not exceed the "
        "maximum purchase quantity allowed for it."),
     "expected_pyomo": LCP},
    {"description": (
        "For each final product, the amount sold must equal the total amount blended into it "
        "from all the intermediate materials, across both crudes, that are allowed to go into "
        "that product."),
     "expected_pyomo": BB},
    {"description": (
        "Some final products must meet a minimum level on a quality attribute. For each product "
        "and attribute that carries a lower specification, the total amount of that attribute "
        "contributed by everything blended into the product must be at least the required "
        "minimum level for that product and attribute applied to the amount of the product sold."),
     "expected_pyomo": QLB},
    {"description": (
        "Some final products must stay under a maximum level on a quality attribute. For each "
        "product and attribute that carries an upper specification, the total amount of that "
        "attribute contributed by everything blended into the product must not exceed the "
        "maximum allowed level for that product and attribute applied to the amount of the "
        "product sold."),
     "expected_pyomo": QUB},
    {"description": (
        "Sales revenue is defined as the income from selling the final products. Set the revenue "
        "equal to the sum over all final products of each product's selling price times the "
        "amount of that product sold."),
     "expected_pyomo": AREV},
    {"description": (
        "Input material cost is defined as what is paid for purchased inputs. Set it equal to "
        "the cost of buying crude, which is each crude's purchase price times the amount of that "
        "crude bought summed over the crudes, plus the cost of externally purchased intermediate "
        "materials, which is each such material's purchase price times the amount of it bought, "
        "summed over those materials and over the crudes they are bought under."),
     "expected_pyomo": AMAT},
    {"description": (
        "Operating cost is defined as the cost of running the processes. Set it equal to the sum "
        "over all processes of each process's per unit operating cost times the total amount of "
        "that process run across both crudes."),
     "expected_pyomo": AOPER},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "macro_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
