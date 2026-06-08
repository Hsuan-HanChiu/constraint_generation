#!/usr/bin/env python
"""Builder for the nonsharp_mip (Benders master MIP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "nonsharp_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "col", "members": ["col-1", "col-2"],
         "doc": "the candidate distillation columns of the separation superstructure; each may or may not be built"},
        {"name": "stm", "members": ["top", "bot"],
         "doc": "the two product streams leaving a column, the top stream and the bottom stream"},
        {"name": "cp", "members": ["a", "b", "c"],
         "doc": "the chemical components present in the feed"},
        {"name": "k", "members": [1, 2],
         "doc": "the stored Benders iterations; each one contributes a cut whose coefficients were generated earlier in the decomposition run"},
        {"name": "savkey", "members": ["(col-1,top,a)", "(col-2,top,b)", "(col-1,bot,b)", "(col-2,bot,c)"],
         "doc": "the set of feasible column-stream-component triples; lists which component is the key component recovered in each stream of each column"},
    ],
    "params": [
        {"name": "totfeed", "index": "", "kind": "flow",
         "doc": "the total feed flow entering the separation system, a single scalar in flow units"},
        {"name": "zlo", "index": "", "kind": "bound",
         "doc": "a known lower bound on the master objective value from earlier Benders iterations"},
        {"name": "nfeas", "index": "k", "kind": "flag",
         "doc": "a flag marking whether the primal subproblem at a stored iteration was feasible; 1 means feasible and 0 means infeasible"},
        {"name": "mcost", "index": "k,col", "kind": "coeff",
         "doc": "the stored linear cost coefficient on a column's build decision for an iteration"},
        {"name": "ma1", "index": "k,col", "kind": "coeff",
         "doc": "the stored constant part of a column's per-unit-flow cost coefficient for an iteration"},
        {"name": "ma2", "index": "k,col,stm", "kind": "coeff",
         "doc": "the stored recovery-sensitivity coefficient for a column stream at an iteration"},
        {"name": "ma3", "index": "k,col,cp", "kind": "coeff",
         "doc": "the stored composition-sensitivity coefficient for a column-component pair at an iteration"},
        {"name": "mint", "index": "k,col", "kind": "multiplier",
         "doc": "the stored logical multiplier from the feasible primal at an iteration, attached to the column linking term"},
        {"name": "mlint", "index": "k,col", "kind": "multiplier",
         "doc": "the stored logical multiplier from the relaxed primal at an infeasible iteration, attached to the column linking term"},
        {"name": "fink", "index": "k,col", "kind": "flow",
         "doc": "the stored inlet flow into a column recorded at an iteration, in flow units"},
        {"name": "reck", "index": "k,col,stm,cp", "kind": "recovery",
         "doc": "the stored fractional key-component recovery for a column stream at an iteration; defaults to zero where not listed"},
        {"name": "xkin", "index": "k,col,cp", "kind": "composition",
         "doc": "the stored inlet composition of a component into a column at an iteration, a mole fraction"},
        {"name": "cut", "index": "k", "kind": "rhs",
         "doc": "the right-hand-side value of the integer cut stored at an iteration"},
        {"name": "cutcol", "index": "k,col", "kind": "coeff",
         "doc": "the coefficient on a column's build decision in the integer cut stored at an iteration"},
    ],
    "vars": [
        {"name": "mu", "index": "", "domain": "Reals",
         "doc": "the master objective value, acting as the Benders lower bound being minimized"},
        {"name": "y", "index": "col", "domain": "Binary",
         "doc": "the build decision for each candidate column; 1 if the column is built and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "mu"},
}

NARRATIVE = (
    "We are synthesizing a distillation column sequence by deciding which candidate columns "
    "to build out of a superstructure. This is the master problem of a Benders decomposition: "
    "for each candidate column we choose whether or not to build it, and we also track a single "
    "master objective value that serves as a running lower bound on the overall cost assembled "
    "from earlier subproblem solutions. The objective is to minimize that master objective value."
)

BND = (
    "model.bnd = Constraint(expr=model.mu >= model.zlo)"
)

LAGRANGE = (
    "def lagrange_rule(model, k):\n"
    "    if abs(value(model.nfeas[k]) - 1.0) > 1e-9:\n"
    "        return Constraint.Skip\n"
    "    def objcoef(c):\n"
    "        return (model.ma1[k, c]\n"
    "                + sum(model.ma2[k, c, s] * model.reck[k, c, s, p] for (cc, s, p) in model.savkey if cc == c)\n"
    "                + sum(model.ma3[k, c, p] * model.xkin[k, c, p] for p in model.cp))\n"
    "    lhs = sum(model.mcost[k, c] * model.y[c] + objcoef(c) * model.fink[k, c] for c in model.col)\n"
    "    lhs += sum(model.mint[k, c] * (model.fink[k, c] - model.totfeed * model.y[c]) for c in model.col)\n"
    "    return lhs <= model.mu\n"
    "model.lagrange = Constraint(model.k, rule=lagrange_rule)"
)

LAERR = (
    "def laerr_rule(model, k):\n"
    "    if abs(value(model.nfeas[k])) > 1e-9:\n"
    "        return Constraint.Skip\n"
    "    expr = sum(model.mlint[k, c] * (model.fink[k, c] - model.totfeed * model.y[c]) for c in model.col)\n"
    "    if expr.__class__ in (int, float) and abs(float(expr)) < 1e-12:\n"
    "        return Constraint.Skip\n"
    "    return expr <= 0\n"
    "model.laerr = Constraint(model.k, rule=laerr_rule)"
)

INTCUT = (
    "def intcut_rule(model, k):\n"
    "    return sum(model.cutcol[k, c] * model.y[c] for c in model.col) <= model.cut[k]\n"
    "model.intcut = Constraint(model.k, rule=intcut_rule)"
)

WHOLESET = "\n".join([BND, LAGRANGE, LAERR, INTCUT])

records = [
    {"description": (
        "The master objective value must stay at or above the known lower bound carried over from "
        "earlier in the decomposition, so the master objective is never allowed to fall below that bound."),
     "expected_pyomo": BND},
    {"description": (
        "For each stored iteration whose primal subproblem came back feasible, add the Lagrange cut "
        "that iteration produced. The cut sums over the candidate columns a stored cost term tied to "
        "each column's build decision together with a stored per-unit-flow cost applied to that column's "
        "recorded inlet flow, and it also adds a linking term that weights, for each column, the gap "
        "between the recorded inlet flow and the total feed allocated according to the build decision. "
        "The whole sum must not exceed the master objective value. Iterations whose primal was infeasible "
        "contribute no such cut."),
     "expected_pyomo": LAGRANGE},
    {"description": (
        "For each stored iteration whose primal subproblem came back infeasible, add the feasibility cut "
        "that iteration produced. This cut sums over the candidate columns a stored multiplier applied to "
        "the gap between each column's recorded inlet flow and the total feed allocated according to that "
        "column's build decision, and requires that sum to be at most zero. Iterations whose primal was "
        "feasible contribute no such cut, and an iteration is also dropped when all of its stored multipliers "
        "are zero so the cut would be vacuous."),
     "expected_pyomo": LAERR},
    {"description": (
        "For each stored iteration, add the integer cut that rules out the build combinations already "
        "explored. The cut takes a stored coefficient on each candidate column's build decision, sums those "
        "weighted build decisions across all columns, and requires the total to be at most the stored "
        "right-hand-side value for that iteration."),
     "expected_pyomo": INTCUT},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, keep the master objective value at or above the known lower bound carried over from earlier "
        "in the decomposition. "
        "Second, for each stored iteration whose primal came back feasible, impose the Lagrange cut that "
        "combines, across the candidate columns, a stored cost on each build decision, a stored per-unit-flow "
        "cost on each recorded inlet flow, and a linking term on the gap between recorded inlet flow and the "
        "feed allocated by the build decision, all bounded above by the master objective value. "
        "Third, for each stored iteration whose primal came back infeasible, impose the feasibility cut that "
        "sums a stored multiplier times the gap between recorded inlet flow and allocated feed across the "
        "columns and holds it at or below zero, dropping any iteration whose multipliers are all zero. "
        "Finally, for each stored iteration, impose the integer cut that sums a stored coefficient times each "
        "column's build decision and keeps the total at or below that iteration's stored right-hand side."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "nonsharp_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
