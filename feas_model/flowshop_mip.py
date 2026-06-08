# converted from models/flowshop_mip.py
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
model.i = Set(initialize=data['i'], doc='item')
model.m = Set(initialize=data['m'], doc='machine')
model.k = Set(initialize=data['k'], doc='position/rank')

# PARAM_BLOCK
model.proctime = Param(model.m, model.i, initialize=data['proctime'], mutable=True, default=0, 
                       doc='processing time')

# Ordered lists for constraint indexing
m_list = list(data['m'])
k_list = list(data['k'])
lastmachine = m_list[-1]
lastrank = k_list[-1]

# VAR_BLOCK
model.rank = Var(model.i, model.k, domain=Binary, doc='item i has position k')
model.start = Var(model.m, model.k, domain=NonNegativeReals, doc='start time for job in position k on m')
model.comp = Var(model.m, model.k, domain=NonNegativeReals, doc='completion time for job in position k on m')
model.totwait = Var(domain=NonNegativeReals, doc='makespan')

# OBJ_BLOCK
model.obj = Objective(expr=model.totwait, sense=minimize, doc='minimize makespan')

# CONS_BLOCK
def oneInPosition_rule(model, k):
    """Every position gets a job"""
    return sum(model.rank[i, k] for i in model.i) == 1
model.oneInPosition = Constraint(model.k, rule=oneInPosition_rule, doc='every position gets a job')

def oneRankPer_rule(model, i):
    """Every job is assigned a rank"""
    return sum(model.rank[i, k] for k in model.k) == 1
model.oneRankPer = Constraint(model.i, rule=oneRankPer_rule, doc='every job is assigned a rank')

def onmachrel_rule(model, m, k):
    """Relations between end of job rank k on machine m and start of job rank k+1 on machine m"""
    k_idx = k_list.index(k)
    if k_idx < len(k_list) - 1:
        k_next = k_list[k_idx + 1]
        return model.start[m, k_next] >= model.comp[m, k]
    return Constraint.Skip
model.onmachrel = Constraint(model.m, model.k, rule=onmachrel_rule, 
                              doc='relation between jobs on same machine')

def permachrel_rule(model, m, k):
    """Relations between end of job rank k on machine m and start of job rank k on machine m+1"""
    m_idx = m_list.index(m)
    if m_idx < len(m_list) - 1:
        m_next = m_list[m_idx + 1]
        return model.start[m_next, k] >= model.comp[m, k]
    return Constraint.Skip
model.permachrel = Constraint(model.m, model.k, rule=permachrel_rule,
                               doc='relation between machines for same job')

def defcomp_rule(model, m, k):
    """Calculation of completion time based on start time and proctime"""
    return model.comp[m, k] == model.start[m, k] + sum(model.proctime[m, i] * model.rank[i, k] for i in model.i)
model.defcomp = Constraint(model.m, model.k, rule=defcomp_rule, doc='completion time definition')

def defobj_rule(model):
    """Completion time of last job on last machine"""
    return model.totwait >= model.comp[lastmachine, lastrank]
model.defobj = Constraint(rule=defobj_rule, doc='objective definition')
