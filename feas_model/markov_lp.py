# converted from models/markov_lp.py
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
model.s = Set(initialize=data['s'], doc='level of the reserve')
model.i = Set(initialize=data['i'], doc='state of the oil market')
# Aliases - use same underlying set
model.sp = Set(initialize=data['sp'], doc='alias for s')
model.spp = Set(initialize=data['spp'], doc='alias for s')
model.j = Set(initialize=data['j'], doc='alias for i')

# SCALAR_PARAMS_BLOCK
model.b = Param(initialize=data['b'], mutable=True, doc='discount factor')
model.beta = Param(initialize=data['beta'], mutable=True, doc='beta coefficient')
model.g = Param(initialize=data['g'], mutable=True, doc='u.s. demand share')
model.e = Param(initialize=data['e'], mutable=True, doc='elasticity')
model.q = Param(initialize=data['q'], mutable=True, doc='supply (million barrel per year)')
model.d = Param(initialize=data['d'], mutable=True, doc='demand curve intercept')
model.k = Param(initialize=data['k'], mutable=True, doc='demand curve coefficient')
model.pn = Param(initialize=data['pn'], mutable=True, doc='normal price (us$ per bbl)')
model.h = Param(initialize=data['h'], mutable=True, doc='storage cost')

# PARAM_BLOCK
model.pr = Param(model.i, model.j, initialize=data['pr'], mutable=True, 
                 doc='transition probability of the world oil market')
model.lev = Param(model.s, initialize={int(k) if isinstance(k, str) and k.isdigit() else k: v 
                                       for k, v in data['lev'].items()}, 
                  mutable=True, doc='level of reserve')
model.dis = Param(model.i, initialize=data['dis'], mutable=True, default=0,
                  doc='disruption')
model.p = Param(model.s, model.sp, model.i, initialize=data['p'], mutable=True,
                doc='price affected by action a')
model.c = Param(model.s, model.sp, model.i, initialize=data['c'], mutable=True,
                doc='cost of taking action a')
model.pi = Param(model.s, model.i, model.sp, model.j, model.spp, 
                 initialize=data['pi'], mutable=True, default=0,
                 doc='probability matrix for problem')

# Create ord mapping for position calculations (1-based like GAMS)
s_list = list(model.s)
model.ord_s = Param(model.s, initialize={s_val: idx+1 for idx, s_val in enumerate(s_list)},
                    doc='ordinal position of s elements')

spp_list = list(model.spp)
model.ord_spp = Param(model.spp, initialize={spp_val: idx+1 for idx, spp_val in enumerate(spp_list)},
                      doc='ordinal position of spp elements')

# VAR_BLOCK
model.z = Var(model.s, model.i, model.sp, domain=NonNegativeReals, 
              doc='multiple of joint probability')
model.pvcost = Var(domain=Reals, doc='present value of expected cost')

# OBJ_BLOCK
model.obj = Objective(expr=model.pvcost, sense=minimize, 
                      doc='minimize present value of expected cost')

# CONS_BLOCK
# constr(sp,j): sum(spp, z(sp,j,spp)) - b*sum((s,i,spp), pi(s,i,sp,j,spp)*z(s,i,spp)) = beta
def constr_rule(model, sp_idx, j_idx):
    return (sum(model.z[sp_idx, j_idx, spp_idx] for spp_idx in model.spp) - 
            model.b * sum(model.pi[s_idx, i_idx, sp_idx, j_idx, spp_idx] * 
                          model.z[s_idx, i_idx, spp_idx] 
                          for s_idx in model.s for i_idx in model.i for spp_idx in model.spp)
            == model.beta)
model.constr = Constraint(model.sp, model.j, rule=constr_rule, 
                          doc='steady state probability constraint')

# equil(s,spp): z(s,"disrupted",spp)*(ord(spp) - ord(s)) <= 0
def equil_rule(model, s_idx, spp_idx):
    return model.z[s_idx, "disrupted", spp_idx] * (model.ord_spp[spp_idx] - model.ord_s[s_idx]) <= 0
model.equil = Constraint(model.s, model.spp, rule=equil_rule,
                         doc='equilibrium - no stockpile increase during disruption')

# cost: pvcost = sum((s,i,spp), c(s,spp,i)*z(s,i,spp))
def cost_rule(model):
    return model.pvcost == sum(model.c[s_idx, spp_idx, i_idx] * model.z[s_idx, i_idx, spp_idx]
                               for s_idx in model.s for i_idx in model.i for spp_idx in model.spp)
model.cost = Constraint(rule=cost_rule, doc='cost definition')
