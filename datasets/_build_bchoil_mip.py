import json

NARRATIVE = (
    "A pipe network must be laid out to collect production from a set of nodes "
    "and route it to a single port. For each directed connection between two "
    "nodes the model decides whether to lay a baseline pipe and, on top of that "
    "baseline, whether to add a single capacity upgrade. It also decides how much "
    "flow runs along each connection. The goal is to choose the cheapest set of "
    "pipes and upgrades that can carry every node's production to the port, where "
    "the cost of any pipe scales with the distance it spans."
)

COMPONENTS = {
    "sets": [
        {"name": "n", "members": ["1", "2", "3", "4"], "doc": "nodes in the network"},
        {"name": "k", "members": ["1", "2", "3"], "doc": "pipe types; type 2 is the baseline and the rest are larger"},
        {"name": "kk", "members": ["3"], "doc": "upgrade pipe types, that is the pipe types larger than the baseline"},
        {"name": "regnode", "members": ["1", "2", "3"], "doc": "flow-conserving nodes, that is every node except the port"},
        {"name": "nw", "members": ["1", "2", "3", "4"], "doc": "nodes that may originate a pipe"},
        {"name": "arc", "members": ["('1','2')", "('1','3')", "('2','1')", "('2','3')", "('2','4')", "('3','1')", "('3','2')", "('3','4')"], "doc": "directed arcs (i, j); both orientations of every physical edge are present, but no arc leaves the port"},
    ],
    "params": [
        {"name": "cap1", "index": "", "kind": "scalar", "doc": "the baseline pipe capacity that any built pipe provides"},
        {"name": "pipecost1", "index": "", "kind": "scalar", "doc": "the baseline pipe cost per unit distance"},
        {"name": "cap_adj", "index": "kk", "kind": "indexed", "doc": "incremental flow capacity of an upgrade type, measured as the extra capacity it adds over the baseline"},
        {"name": "pipecost_adj", "index": "kk", "kind": "indexed", "doc": "incremental cost per unit distance of an upgrade type, measured as the extra cost it adds over the baseline"},
        {"name": "p", "index": "n", "kind": "indexed", "doc": "production at a node; a node with zero production is a pass-through node, a node with positive production is a source"},
    ],
    "vars": [
        {"name": "b", "index": "arc", "domain": "Binary", "doc": "1 if a baseline pipe is laid on the arc, else 0"},
        {"name": "bk", "index": "arc,k", "domain": "Binary", "doc": "1 if the given upgrade type is added on top of the baseline pipe on the arc, else 0; only upgrade types in kk are used"},
        {"name": "f", "index": "arc", "domain": "NonNegativeReals", "doc": "flow sent along the arc"},
        {"name": "cost", "index": "", "domain": "Reals", "doc": "total installation cost of the chosen network"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

# distance per arc in the reduced instance (edgedist(i,j)+edgedist(j,i)), used as
# literal coefficients in the cost-definition ground truth because the model
# exposes no distance parameter.
DIST_LITERAL = (
    "    _dist = {('1','2'): 3.1, ('1','3'): 2.4, ('2','1'): 3.1, ('2','3'): 4.6,\n"
    "             ('2','4'): 3.3, ('3','1'): 2.4, ('3','2'): 4.6, ('3','4'): 5.7}\n"
)

OBJ = (
    "def obj_constraint_rule(model):\n"
    + DIST_LITERAL +
    "    return sum(_dist.get((i, j), 0) * (model.pipecost1 * model.b[i, j] + sum(model.pipecost_adj[kk] * model.bk[i, j, kk] for kk in model.kk)) for (i, j) in model.arc) == model.cost\n"
    "model.obj_constraint = Constraint(rule=obj_constraint_rule)"
)

ONEOUT = (
    "def oneout_rule(model, i):\n"
    "    if value(model.p[i]) != 0.0:\n"
    "        return Constraint.Skip\n"
    "    outs = [(i, j) for (ii, j) in model.arc if ii == i]\n"
    "    if not outs:\n"
    "        return Constraint.Skip\n"
    "    return sum(model.b[i, j] for (i, j) in outs) <= 1\n"
    "model.oneout = Constraint(model.n, rule=oneout_rule)"
)

ONEOUTP = (
    "def oneoutp_rule(model, i):\n"
    "    if not (value(model.p[i]) != 0.0):\n"
    "        return Constraint.Skip\n"
    "    outs = [j for j in model.n if (i, j) in model.arc]\n"
    "    if not outs:\n"
    "        return Constraint.Skip\n"
    "    return sum(model.b[i, j] for j in outs) == 1\n"
    "model.oneoutp = Constraint(model.n, rule=oneoutp_rule)"
)

BAL = (
    "def bal_rule(model, i):\n"
    "    if i not in model.regnode:\n"
    "        return Constraint.Skip\n"
    "    outflow = sum(model.f[i, j] for j in model.n if (i, j) in model.arc)\n"
    "    inflow = sum(model.f[j, i] for j in model.n if (j, i) in model.arc)\n"
    "    return model.p[i] == outflow - inflow\n"
    "model.bal = Constraint(model.n, rule=bal_rule)"
)

BIGM = (
    "def bigM_rule(model, i, j):\n"
    "    return model.cap1 * model.b[i, j] + sum(model.cap_adj[kk] * model.bk[i, j, kk] for kk in model.kk) >= model.f[i, j]\n"
    "model.bigM = Constraint(model.arc, rule=bigM_rule)"
)

DEFB = (
    "def defb_rule(model, i, j):\n"
    "    return sum(model.bk[i, j, kk] for kk in model.kk) <= model.b[i, j]\n"
    "model.defb = Constraint(model.arc, rule=defb_rule)"
)

DESCRIPTIONS = {
    "obj_constraint": "Define the total installation cost as the sum over every arc of the arc's length multiplied by the cost of whatever is built on it, where a built baseline pipe contributes its baseline cost and each added upgrade contributes its own incremental cost.",
    "oneout": "At each pass-through node that has no production, allow at most one baseline pipe to leave the node. Skip this requirement at any node that has production and at any node with no outgoing arcs.",
    "oneoutp": "At each node that has production, require exactly one baseline pipe to leave the node so its output has a single starting direction. Skip this requirement at any node with no production and at any node with no outgoing arcs.",
    "bal": "At every flow-conserving node, the node's own production must equal the total flow leaving it minus the total flow entering it, so production plus whatever arrives is exactly what departs. Skip this at the port, which simply absorbs all the collected production.",
    "bigM": "On every arc, the capacity installed there must be enough to carry the flow on that arc, where the installed capacity is the baseline capacity of a built pipe plus the extra capacity contributed by any upgrade added to it.",
    "defb": "On every arc, an upgrade may only be added where a baseline pipe is actually built, and since only one upgrade can ever be present the total number of upgrades on the arc can be at most one when a baseline pipe is laid and none otherwise.",
}

ORDER = ["obj_constraint", "oneout", "oneoutp", "bal", "bigM", "defb"]
PYOMO = {"obj_constraint": OBJ, "oneout": ONEOUT, "oneoutp": ONEOUTP, "bal": BAL, "bigM": BIGM, "defb": DEFB}

WHOLE_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, define the total installation cost as the distance-weighted cost of "
    "every baseline pipe and every upgrade that is built across the network. "
    "Second, at each pass-through node with no production allow at most one "
    "baseline pipe to leave it. Third, at each node that has production require "
    "exactly one baseline pipe to leave it. Fourth, at every flow-conserving node "
    "make the node's production equal the flow leaving it minus the flow entering "
    "it, with the port exempt because it simply absorbs everything collected. "
    "Fifth, on every arc make the installed capacity, baseline plus any upgrade, "
    "at least the flow carried on that arc. Finally, allow an upgrade on an arc "
    "only where a baseline pipe is built."
)

records = []
for name in ORDER:
    records.append({
        "problem_id": "bchoil_mip",
        "model_narrative": NARRATIVE,
        "components": COMPONENTS,
        "description": DESCRIPTIONS[name],
        "expected_pyomo": PYOMO[name],
    })

records.append({
    "problem_id": "bchoil_mip",
    "model_narrative": NARRATIVE,
    "components": COMPONENTS,
    "description": WHOLE_DESC,
    "expected_pyomo": "\n\n".join(PYOMO[name] for name in ORDER),
})

out = "datasets/bchoil_mip_constraint_gen.jsonl"
with open(out, "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
print("wrote", len(records), "records to", out)
