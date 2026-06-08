# converted from models/westmip_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── helper function (required by model construction) ─────────────────────────
def solve_linear_system(a_dict, alpha_dict, i_list):
    """Solve A*x = alpha using Gaussian elimination for small systems."""
    n = len(i_list)
    aug = [[0.0]*(n+1) for _ in range(n)]
    for ii, i_idx in enumerate(i_list):
        for jj, j_idx in enumerate(i_list):
            aug[ii][jj] = a_dict.get((i_idx, j_idx), 0.0)
        aug[ii][n] = alpha_dict.get(i_idx, 0.0)
    for col in range(n):
        max_row = col
        for row in range(col+1, n):
            if abs(aug[row][col]) > abs(aug[max_row][col]):
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]
        if abs(aug[col][col]) < 1e-12:
            continue
        for row in range(col+1, n):
            factor = aug[row][col] / aug[col][col]
            for j in range(col, n+1):
                aug[row][j] -= factor * aug[col][j]
    x = [0.0] * n
    for i in range(n-1, -1, -1):
        x[i] = aug[i][n]
        for j in range(i+1, n):
            x[i] -= aug[i][j] * x[j]
        if abs(aug[i][i]) > 1e-12:
            x[i] /= aug[i][i]
    return {i_list[ii]: x[ii] for ii in range(n)}
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# SET_BLOCK
model.i = Set(initialize=data['i'], doc='sectors')
model.n = Set(initialize=data['n'], doc='capacity type')
model.r = Set(initialize=data['r'], doc='resources')
model.te = Set(initialize=data['te'], ordered=True, doc='extended time horizon')
model.t = Set(initialize=data['t'], ordered=True, doc='time horizon')
model.ia = Set(initialize=data['ia'], doc='sectors needing aux units')
model.im = Set(initialize=data['im'], doc='import possible')
model.ie = Set(initialize=data['ie'], doc='export possible')
model.in_ = Set(initialize=data['in'], dimen=2, doc='capacity use')

# Derived sets
i_list = list(data['i'])
n_list = list(data['n'])
r_list = list(data['r'])
te_list = list(data['te'])
t_list = list(data['t'])

# ti = initial period (base), tb = all but last, tl = last period
ti = te_list[0]  # 'base'
tb = te_list[:-1]  # all but terminal
tl = te_list[-1]  # 'terminal'

# es(i,n) = units with economies of scale (where fixed cost > 0)
es = []
for i_idx in i_list:
    for n_idx in n_list:
        fixed_f = data.get('inv_fixed_foreign', {}).get((i_idx, n_idx), 0)
        fixed_d = data.get('inv_fixed_domestic', {}).get((i_idx, n_idx), 0)
        if fixed_f > 0 or fixed_d > 0:
            es.append((i_idx, n_idx))

# forn and dom subsets
forn = ['foreign']
dom = ['domestic']

# SCALAR_PARAMS_BLOCK
cmin = data['cmin']
dmax = data['dmax']
rho = data['rho']
vmax = data['vmax']

# PARAM_BLOCK
model.a = Param(model.i, model.i, initialize=data['a'], mutable=True, default=0, 
                doc='input output matrix')
model.u = Param(model.i, model.r, initialize=data['u'], mutable=True, default=0, 
                doc='resource use')
model.rbase = Param(model.r, initialize=data['rbase'], mutable=True, doc='base resources')
model.alpha = Param(model.i, initialize=data['alpha'], mutable=True, doc='allocation')
model.cbb = Param(model.i, initialize=data['cbb'], mutable=True, doc='base demand')
model.kb = Param(model.i, model.n, initialize=data['kb'], mutable=True, default=0, 
                 doc='base capacity')

# Investment cost parameters
inv_fixed_foreign = data.get('inv_fixed_foreign', {})
inv_fixed_domestic = data.get('inv_fixed_domestic', {})
inv_prop_foreign = data.get('inv_prop_foreign', {})
inv_prop_domestic = data.get('inv_prop_domestic', {})

# Compute discount factors
card_t = len(t_list)
delt = {t_idx: (1 + rho)**(-ord) for ord, t_idx in enumerate(t_list, 1)}
dft1 = (1/(1 + rho))**card_t / (1 - 1/(1 + rho))
dft3 = (1/(1 + rho))**(card_t + 2) / (1 - 1/(1 + rho))
dft8 = (1/(1 + rho))**(card_t + 7) / (1 - 1/(1 + rho))

model.delt = Param(model.t, initialize=delt, mutable=True, doc='discount factor')

# Solve the CNS system to get xone values
# mbone(i): sum(j, a(i,j)*xone(j)) = alpha(i)
xone = solve_linear_system(data['a'], data['alpha'], i_list)

# Compute aic and ar
clev = 265
aic = {}
for i_idx in i_list:
    for n_idx in n_list:
        if (i_idx, n_idx) in data['in']:
            for r_idx in r_list:
                if r_idx == 'foreign':
                    fixed = inv_fixed_foreign.get((i_idx, n_idx), 0)
                    prop = inv_prop_foreign.get((i_idx, n_idx), 0)
                else:
                    fixed = inv_fixed_domestic.get((i_idx, n_idx), 0)
                    prop = inv_prop_domestic.get((i_idx, n_idx), 0)
                aic[(i_idx, n_idx, r_idx)] = fixed / (clev * xone[i_idx]) + prop if xone[i_idx] != 0 else prop

ar = {}
for r_idx in r_list:
    ar[r_idx] = sum(aic.get((i_idx, n_idx, r_idx), 0) * xone[i_idx] 
                    for i_idx in i_list for n_idx in n_list if (i_idx, n_idx) in data['in'])

# VAR_BLOCK
model.x = Var(model.te, model.i, domain=NonNegativeReals, doc='production')
model.m = Var(model.te, model.i, domain=NonNegativeReals, doc='imports')
model.e = Var(model.te, model.i, domain=NonNegativeReals, doc='exports')
model.v = Var(model.te, model.i, model.n, domain=NonNegativeReals, doc='capacity expansion')
model.f = Var(model.te, model.i, model.n, domain=Binary, doc='fixed charge variable')
model.k = Var(model.te, model.i, model.n, domain=Reals, doc='capacity stock')
model.ke3 = Var(model.i, model.n, domain=NonNegativeReals, doc='excess capacity: first 5 post-terminal years')
model.ke8 = Var(model.i, model.n, domain=NonNegativeReals, doc='excess capacity: second 5 post-terminal years')
model.c = Var(model.t, domain=NonNegativeReals, doc='consumption increment')
model.d = Var(model.te, domain=Reals, doc='level of debt')
model.ufe = Var(model.te, domain=NonNegativeReals, doc='unused foreign exchange')
model.ms = Var(model.te, domain=NonNegativeReals, doc='foreign exchange into domestic')
model.vr = Var(domain=NonNegativeReals, doc='terminal savings')
model.vc3 = Var(domain=NonNegativeReals, doc='terminal excess capacity value 3')
model.vc8 = Var(domain=NonNegativeReals, doc='terminal excess capacity value 8')
model.vc = Var(domain=NonNegativeReals, doc='post terminal consumption valuation')
model.wterm = Var(domain=Reals, doc='terminal valuation')
model.welfare = Var(domain=Reals, doc='discounted welfare')

# OBJ_BLOCK
model.obj = Objective(expr=model.welfare, sense=maximize, doc='maximize welfare')

# CONS_BLOCK

# mb(t,i): material balance
def mb_rule(model, t_idx, i_idx):
    j_sum = sum(model.a[i_idx, j] * model.x[t_idx, j] for j in model.i)
    m_val = model.m[t_idx, i_idx] if i_idx in data['im'] else 0
    e_val = model.e[t_idx, i_idx] if i_idx in data['ie'] else 0
    return j_sum + m_val == e_val + model.alpha[i_idx] * model.c[t_idx] + model.cbb[i_idx]
model.mb = Constraint(model.t, model.i, rule=mb_rule, doc='material balance')

# cc(t,i,n): capacity constraint
def cc_rule(model, t_idx, i_idx, n_idx):
    if (i_idx, n_idx) in data['in']:
        return model.x[t_idx, i_idx] <= model.k[t_idx, i_idx, n_idx]
    return Constraint.Skip
model.cc = Constraint(model.t, model.i, model.n, rule=cc_rule, doc='capacity constraint')

# ecc(i,n): excess capacity valuation
def ecc_rule(model, i_idx, n_idx):
    if (i_idx, n_idx) in data['in']:
        return model.ke3[i_idx, n_idx] + model.ke8[i_idx, n_idx] == model.k[tl, i_idx, n_idx] - model.x[tl, i_idx]
    return Constraint.Skip
model.ecc = Constraint(model.i, model.n, rule=ecc_rule, doc='excess capacity valuation')

# cb(te,i,n): capacity balance - k(te) = k(te-1) + v(te-1)
def cb_rule(model, te_idx, i_idx, n_idx):
    if (i_idx, n_idx) not in data['in']:
        return Constraint.Skip
    te_idx_pos = te_list.index(te_idx)
    if te_idx_pos == 0:
        return Constraint.Skip  # skip base period
    te_prev = te_list[te_idx_pos - 1]
    return model.k[te_idx, i_idx, n_idx] == model.k[te_prev, i_idx, n_idx] + model.v[te_prev, i_idx, n_idx]
model.cb = Constraint(model.te, model.i, model.n, rule=cb_rule, doc='capacity balance')

# bi(te,i,n): integer constraint - v(te) <= vmax*f(te)
def bi_rule(model, te_idx, i_idx, n_idx):
    if (i_idx, n_idx) not in es:
        return Constraint.Skip
    te_idx_pos = te_list.index(te_idx)
    if te_idx_pos == 0:
        return Constraint.Skip  # skip base period
    te_prev = te_list[te_idx_pos - 1]
    return model.v[te_prev, i_idx, n_idx] <= vmax * model.f[te_prev, i_idx, n_idx]
model.bi = Constraint(model.te, model.i, model.n, rule=bi_rule, doc='integer constraint')

# rb(te,r): resource balance
def rb_rule(model, te_idx, r_idx):
    te_idx_pos = te_list.index(te_idx)
    is_ti = (te_idx == ti)
    is_tb = (te_idx in tb)
    is_tl = (te_idx == tl)
    is_t = (te_idx in t_list)
    is_forn = (r_idx == 'foreign')
    is_dom = (r_idx == 'domestic')

    expr = 0

    # Production/trade terms (only for t periods)
    if is_t:
        for i_idx in i_list:
            expr += model.u[i_idx, r_idx] * model.x[te_idx, i_idx]
            if is_forn:
                if i_idx in data['im']:
                    expr += model.m[te_idx, i_idx]
                if i_idx in data['ie']:
                    expr -= model.e[te_idx, i_idx]

    # Investment terms (only for tb periods)
    if is_tb:
        for i_idx in i_list:
            for n_idx in n_list:
                if (i_idx, n_idx) in data['in']:
                    if r_idx == 'foreign':
                        fixed = inv_fixed_foreign.get((i_idx, n_idx), 0)
                        prop = inv_prop_foreign.get((i_idx, n_idx), 0)
                    else:
                        fixed = inv_fixed_domestic.get((i_idx, n_idx), 0)
                        prop = inv_prop_domestic.get((i_idx, n_idx), 0)
                    expr += fixed * model.f[te_idx, i_idx, n_idx] + prop * model.v[te_idx, i_idx, n_idx]

    # Debt terms
    if te_idx_pos > 0:
        te_prev = te_list[te_idx_pos - 1]
        expr += (1 + rho) * model.d[te_prev]
    if is_tb:
        expr -= model.d[te_idx]

    # Foreign exchange conversion
    if is_forn:
        expr += model.ms[te_idx]
    if is_dom:
        expr -= 0.8 * model.ms[te_idx]

    # Unused foreign exchange
    if is_forn:
        if is_tb:
            expr += model.ufe[te_idx]
        if te_idx_pos > 0:
            te_prev = te_list[te_idx_pos - 1]
            expr -= model.ufe[te_prev]

    # Terminal savings
    if is_tl:
        expr += ar[r_idx] * model.vr

    # RHS
    rhs = data['rbase'].get(r_idx, 0) if is_ti else 0

    return expr <= rhs
model.rb = Constraint(model.te, model.r, rule=rb_rule, doc='resource balance')

# vc38(r): terminal excess capacity valuation
def vc38_rule(model, r_idx):
    lhs = sum(aic.get((i_idx, n_idx, r_idx), 0) * (model.ke3[i_idx, n_idx] + model.ke8[i_idx, n_idx])
              for i_idx in i_list for n_idx in n_list if (i_idx, n_idx) in data['in'])
    rhs = ar[r_idx] * (model.vc3 + model.vc8)
    return lhs >= rhs
model.vc38 = Constraint(model.r, rule=vc38_rule, doc='terminal excess capacity valuation')

# clow(t): increment bounds - c(t+1) >= cmin + c(t)
def clow_rule(model, t_idx):
    t_idx_pos = t_list.index(t_idx)
    if t_idx_pos == 0:
        return Constraint.Skip
    t_prev = t_list[t_idx_pos - 1]
    return model.c[t_idx] >= cmin + model.c[t_prev]
model.clow = Constraint(model.t, rule=clow_rule, doc='increment bounds')

# xlow(t): production bounds - x(t+1,primary) >= x(t,primary)
def xlow_rule(model, t_idx):
    t_idx_pos = t_list.index(t_idx)
    if t_idx_pos == 0:
        return Constraint.Skip
    t_prev = t_list[t_idx_pos - 1]
    return model.x[t_idx, 'primary'] >= model.x[t_prev, 'primary']
model.xlow = Constraint(model.t, rule=xlow_rule, doc='production bounds')

# vcdef(i): utilized capacity valuation
def vcdef_rule(model, i_idx):
    lhs = sum(model.a[i_idx, j] * (model.x[tl, j] - model.kb[j, 'normal']) for j in model.i)
    rhs = model.alpha[i_idx] * model.vc
    return lhs >= rhs
model.vcdef = Constraint(model.i, rule=vcdef_rule, doc='utilized capacity valuation')

# term: terminal value definition
def term_rule(model):
    return model.wterm == dft1 * model.vr + dft3 * model.vc3 + dft8 * model.vc8 + dft1 * model.vc
model.term = Constraint(rule=term_rule, doc='terminal value definition')

# obj: objective definition
def objdef_rule(model):
    return model.welfare == sum(model.delt[t_idx] * model.c[t_idx] for t_idx in model.t) + model.wterm
model.objdef = Constraint(rule=objdef_rule, doc='objective definition')

# BOUNDS
for te_idx in model.te:
    model.d[te_idx].setub(dmax)

# Fix initial capacity k.fx(ti,i,n) = kb(i,n)
for i_idx in model.i:
    for n_idx in model.n:
        kb_val = data['kb'].get((i_idx, n_idx), 0)
        model.k[ti, i_idx, n_idx].fix(kb_val)

# ke3.up(i,n) = 5*cmin*xone(i)
for i_idx in model.i:
    for n_idx in model.n:
        if (i_idx, n_idx) in data['in']:
            model.ke3[i_idx, n_idx].setub(5 * cmin * xone[i_idx])
