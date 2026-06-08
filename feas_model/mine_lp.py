# converted from models/mine_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# SET_BLOCK
model.L = Set(initialize=data["l"], ordered=True, doc="identifiers for level row and column labels")
model.I = Set(initialize=data["i"], ordered=True, doc="alias (rows)")
model.J = Set(initialize=data["j"], ordered=True, doc="alias (columns)")
model.K = Set(initialize=data["k"], ordered=True, doc="location of four neighboring blocks")

L_list = list(model.L); I_list = list(model.I); J_list = list(model.J)
ordL = {L_list[idx]: idx + 1 for idx in range(len(L_list))}
ordI = {I_list[idx]: idx + 1 for idx in range(len(I_list))}
ordJ = {J_list[idx]: idx + 1 for idx in range(len(J_list))}
cardL = len(L_list)

succL = {L_list[i]: (L_list[i + 1] if i + 1 < len(L_list) else None) for i in range(len(L_list))}

# PARAM_BLOCK
conc_map = data.get("conc", {})
def _conc_init(model, l, i, j):
    return float(conc_map.get((l, i, j), 0.0))
model.conc  = Param(model.L, model.I, model.J, initialize=_conc_init, within=NonNegativeReals, mutable=True,
                doc="estimated ore concentration (percent metal)")

model.cost  = Param(model.L, initialize={int(k): float(v) for k, v in data["cost"].items()},
                within=NonNegativeReals, mutable=True, doc="block extraction cost")
model.value = Param(initialize=float(data["value"]), within=NonNegativeReals, mutable=True,
                doc="extracted block value if 100 percent metal")

model.li = Param(model.K, initialize={k: int(v) for k, v in data["li"].items()},
             within=NonNegativeIntegers, mutable=True, doc="lead for i")
model.lj = Param(model.K, initialize={k: int(v) for k, v in data["lj"].items()},
             within=NonNegativeIntegers, mutable=True, doc="lead for j")

# Derived index sets
C_tuples, D_tuples = [], []
for l in model.L:
    for i in model.I:
        for j in model.J:
            if (ordL[l] + ordI[i] <= cardL) and (ordL[l] + ordJ[j] <= cardL):
                C_tuples.append((l, i, j))
            if (ordL[l] + ordI[i] <= cardL + 1) and (ordL[l] + ordJ[j] <= cardL + 1):
                D_tuples.append((l, i, j))
model.C = Set(dimen=3, initialize=C_tuples, doc="neighboring blocks related to extraction feasibility")
model.D = Set(dimen=3, initialize=D_tuples, doc="complete set of block identifiers")

# VAR_BLOCK
model.x = Var(model.L, model.I, model.J, domain=NonNegativeReals, bounds=(0.0, 1.0),
          doc="extraction of blocks")
model.profit = Var(domain=Reals, doc="profit")

# OBJ_BLOCK
model.obj = Objective(expr=model.profit, sense=maximize, doc="maximize profit")

# CONS_BLOCK
def _profit_rule(model):
    # def.. profit =e= sum((l,i,j)$d(l,i,j), (conc(l,i,j)*value/100 - cost(l))*x(l,i,j));
    return model.profit == sum(((model.conc[l, i, j] * model.value) / 100.0 - model.cost[l]) * model.x[l, i, j]
                           for (l, i, j) in model.D)
model.profit_def = Constraint(rule=_profit_rule, doc="profit definition")

def _precedence_rule(model, k, l, i, j):
    # pr(k,l+1,i,j)$c(l,i,j).. x(l,i+li(k),j+lj(k)) =g= x(l+1,i,j);
    lnext = succL[l]
    if lnext is None:
        return Constraint.Skip
    off_i = int(value(model.li[k])); off_j = int(value(model.lj[k]))
    ii_idx = ordI[i] - 1 + off_i
    jj_idx = ordJ[j] - 1 + off_j
    if ii_idx < 0 or jj_idx < 0 or ii_idx >= len(I_list) or jj_idx >= len(J_list):
        return Constraint.Skip
    ii = I_list[ii_idx]; jj = J_list[jj_idx]
    return model.x[l, ii, jj] >= model.x[lnext, i, j]
model.precedence = Constraint(model.K, model.C, rule=_precedence_rule, doc="precedence relationships")
