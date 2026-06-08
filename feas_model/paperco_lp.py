# converted from models/paperco_lp.py
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

# Sets
model.L  = Set(initialize=data["l"], ordered=True, doc="log suppliers")
model.W  = Set(initialize=data["w"], ordered=True, doc="wood products")
model.P  = Set(initialize=data["p"], ordered=True, doc="pulp types")
model.Q  = Set(initialize=data["q"], ordered=True, doc="paper types")
model.SC = Set(initialize=data.get("scenario", []), ordered=True, doc="scenarios")

# Active scenario
current_scn = str(data.get("current_scenario", next(iter(model.SC)) if len(model.SC) > 0 else ""))

# Parameters
model.plog = Param(initialize=float(data["plog"]), mutable=True, doc="log price")

ap_src = data["ap"]   
aq_src = data["aq"]  
cw_src = data["cw"]  
cp_src = data["cp"]  

model.ap = Param(model.W, model.P, initialize=lambda model,w,p: float(ap_src[(w, p)]), mutable=True, doc="pulp input req")
model.aq = Param(model.P, model.Q, initialize=lambda model,p,q: float(aq_src[(p, q)]), mutable=True, doc="paper input req")
model.cw = Param(model.W, model.P, initialize=lambda model,w,p: float(cw_src[(w, p)]), mutable=True, doc="wood ship cost")
model.cp = Param(model.P, model.Q, initialize=lambda model,p,q: float(cp_src[(p, q)]), mutable=True, doc="pulp ship cost")

model.pq = Param(model.Q, initialize=lambda model,q: float(data["pq"][q]), mutable=True, doc="paper sales price")
model.pc = Param(model.W, initialize=lambda model,w: float(data["pc"][w]), mutable=True, doc="wood price")
model.paper_lb = Param(model.Q, initialize=lambda model,q: float(data["sdat_lower"][q]), mutable=True, doc="paper lower bound")
model.paper_ub = Param(model.Q, initialize=lambda model,q: float(data["sdat_upper"][q]), mutable=True, doc="paper upper bound")

# Scenario data 
ppdat   = data["ppdat"]     # (scenario, p) -> price
psdat_s = data["psdat_s"]   # (scenario, p) -> sales ub
psdat_p = data["psdat_p"]   # (scenario, p) -> purchase ub

model.pp = Param(model.P, initialize=lambda model,p: float(ppdat[(current_scn, p)]), mutable=True, doc="pulp price (scenario)")
model.sales_ub = Param(model.P, initialize=lambda model,p: float(psdat_s.get((current_scn, p), 0.0)), mutable=True, doc="sales ub")
model.purchase_ub = Param(model.P, initialize=lambda model,p: float(psdat_p.get((current_scn, p), 0.0)), mutable=True, doc="purchase ub")

# Variables
model.logs     = Var(model.L, domain=NonNegativeReals, doc="logs")
model.xw       = Var(model.W, model.P, domain=NonNegativeReals, doc="wood shipments")
model.pulp     = Var(model.P, domain=NonNegativeReals, doc="pulp production")
model.xp       = Var(model.P, model.Q, domain=NonNegativeReals, doc="pulp shipments")
model.paper    = Var(model.Q, domain=NonNegativeReals, bounds=lambda model,q: (model.paper_lb[q], model.paper_ub[q]), doc="paper output")
model.sales    = Var(model.P, domain=NonNegativeReals, bounds=lambda model,p: (0.0, model.sales_ub[p]), doc="pulp sales")
model.purchase = Var(model.P, domain=NonNegativeReals, bounds=lambda model,p: (0.0, model.purchase_ub[p]), doc="pulp purchase")
model.profit   = Var(domain=Reals, doc="net operating income")

# Constraints
# 0.97 * sum_l logs(l) = sum_{w,p} xw(w,p)
model.logbal = Constraint(rule=lambda model: 0.97 * sum(model.logs[l] for l in model.L) == sum(model.xw[w,p] for w in model.W for p in model.P), doc="logbal")

# xw(w,p) = ap(w,p) * pulp(p)
model.wbal = Constraint(model.W, model.P, rule=lambda model,w,p: model.xw[w,p] == model.ap[w,p] * model.pulp[p], doc="wbal")

# sum_q xp(p,q) = purchase(p) - sales(p) + pulp(p)
model.pbal = Constraint(model.P, rule=lambda model,p: sum(model.xp[p,q] for q in model.Q) == model.purchase[p] - model.sales[p] + model.pulp[p], doc="pbal")

# xp(p,q) = aq(p,q) * paper(q)
model.qbal = Constraint(model.P, model.Q, rule=lambda model,p,q: model.xp[p,q] == model.aq[p,q] * model.paper[q], doc="qbal")

# Profit definition
def _obj_def(model):
    revenue_pulp   = sum(model.pp[p] * model.sales[p] for p in model.P)
    revenue_paper  = sum(model.pq[q] * model.paper[q] for q in model.Q)
    cost_logs      = sum(model.plog * model.logs[l] for l in model.L)
    cost_pulp_tr   = sum(model.cp[p,q] * model.xp[p,q] for p in model.P for q in model.Q)
    cost_wood      = sum((model.cw[w,p] + model.pc[w]) * model.xw[w,p] for w in model.W for p in model.P)
    cost_purchase  = sum(model.pp[p] * model.purchase[p] for p in model.P)
    return model.profit == (revenue_pulp + revenue_paper - cost_logs - cost_pulp_tr - cost_wood - cost_purchase)
model.obj_def = Constraint(rule=_obj_def, doc="profit definition")

# Objective
model.obj = Objective(expr=model.profit, sense=maximize, doc="maximize profit")
