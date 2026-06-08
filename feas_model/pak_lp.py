# converted from models/pak_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Optimal Patterns of Growth and Aid - Pakistan economic development model"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.te = Set(
    initialize=data["te"],
    ordered=True,
    doc="Extended planning period (1962-1985)"
)

model.t = Set(
    initialize=data["t"],
    within=model.te,
    ordered=True,
    doc="Planning period (1963-1985)"
)

model.j = Set(
    initialize=data["j"],
    doc="Sectors"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK (all mutable = True)
# ----------------------------------------------------------------------
model.fbb = Param(initialize=data["fbb"], mutable=True, doc="Foreign aid 1962")
model.sb = Param(initialize=data["sb"], mutable=True, doc="Saving 1962")
model.tib = Param(initialize=data["tib"], mutable=True, doc="Total investment 1962")
model.mb = Param(initialize=data["mb"], mutable=True, doc="Imports 1962")
model.eb = Param(initialize=data["eb"], mutable=True, doc="Exports 1962")
model.gnpb = Param(initialize=data["gnpb"], mutable=True, doc="GNP 1962")
model.cb = Param(initialize=data["cb"], mutable=True, doc="Consumption 1962")
model.rho = Param(initialize=data["rho"], mutable=True, doc="Discount rate")
model.r = Param(initialize=data["r"], mutable=True, doc="Post plan discount")
model.g = Param(initialize=data["g"], mutable=True, doc="Post plan growth")
model.gama = Param(initialize=data["gama"], mutable=True, doc="Cost of foreign capital")
model.d = Param(initialize=data["d"], mutable=True, doc="Post plan weight")
model.alpha = Param(initialize=data["alpha"], mutable=True, doc="Marginal savings rate")
model.mgnp = Param(initialize=data["mgnp"], mutable=True, doc="Marginal import rate on GNP")
model.mi = Param(initialize=data["mi"], mutable=True, doc="Marginal import rate on investment")
model.p = Param(initialize=data["p"], mutable=True, doc="Population growth")
model.beta = Param(initialize=data["beta"], mutable=True, doc="Maximum growth of investment")
model.ee = Param(initialize=data["ee"], mutable=True, doc="Export growth")
model.q = Param(initialize=data["q"], mutable=True, doc="Aid ratio")
model.num = Param(initialize=data["num"], mutable=True, doc="Years without aid")

model.k = Param(
    model.j,
    initialize=data["k"],
    mutable=True,
    doc="Capital output ratio"
)

# Pre-compute derived parameters
te_list = list(model.te)
t_list = list(model.t)
card_t = len(t_list)

# e(t) = eb*(1 + ee)**ord(t)
e_dict = {}
for i, t in enumerate(t_list, start=1):
    e_dict[t] = data["eb"] * (1 + data["ee"])**i

model.e = Param(
    model.t,
    initialize=e_dict,
    mutable=True,
    doc="Exports"
)

# delt(t) = (1 + rho)**(-ord(t))
delt_dict = {}
for i, t in enumerate(t_list, start=1):
    delt_dict[t] = (1 + data["rho"])**(-i)

model.delt = Param(
    model.t,
    initialize=delt_dict,
    mutable=True,
    doc="Discount factor"
)

# dis = (1 + r)**(-card(t))*(1 - alpha)*(1 + g)/(r - g)
dis_val = ((1 + data["r"])**(-card_t) *
           (1 - data["alpha"]) *
           (1 + data["g"]) /
           (data["r"] - data["g"]))

model.dis = Param(
    initialize=dis_val,
    mutable=True,
    doc="Discounting for post horizon consumption"
)

# vb(j) - base year outputs
vb_dict = {"non-traded": data["gnpb"]}

model.vb = Param(
    model.j,
    initialize=vb_dict,
    mutable=True,
    default=0,
    doc="Base year outputs"
)

# Pre-compute f_up bounds: f.up(t) = inf$(card(t) - ord(t) >= num)
# This means f(t) is unbounded if there are at least 'num' years left
f_up_dict = {}
for i, t in enumerate(t_list, start=1):
    years_left = card_t - i
    if years_left >= data["num"]:
        f_up_dict[t] = None  # No upper bound (unbounded)
    else:
        f_up_dict[t] = 0  # Bounded to 0 (effectively no aid)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.gnp = Var(
    model.t,
    domain=Reals,
    doc="Gross national product"
)

model.v = Var(
    model.t, model.j,
    domain=NonNegativeReals,
    doc="Net output"
)

model.ti = Var(
    model.te,
    domain=Reals,
    doc="Total investment"
)

model.i = Var(
    model.te, model.j,
    domain=NonNegativeReals,
    doc="Investment"
)

model.ks = Var(
    model.te, model.j,
    domain=Reals,
    doc="Capital stock"
)

model.s = Var(
    model.t,
    domain=NonNegativeReals,
    doc="Gross savings"
)

model.f = Var(
    model.t,
    domain=Reals,
    doc="Net capital inflow"
)

model.fb = Var(
    domain=Reals,
    doc="Total discounted aid"
)

model.m = Var(
    model.t,
    domain=Reals,
    doc="Traditional imports"
)

model.c = Var(
    model.te,
    domain=Reals,
    doc="Consumption"
)

model.w = Var(
    domain=Reals,
    doc="Welfare"
)

# Fix initial conditions
model.ks[1962, "non-traded"].fix(0)
model.ks[1962, "traded"].fix(0)
model.i[1962, "non-traded"].fix(data["tib"])
model.i[1962, "traded"].fix(0)
model.c[1962].fix(data["cb"])

# Set upper bounds on f(t) based on pre-computed values
for t in t_list:
    if f_up_dict[t] is not None:
        model.f[t].setub(f_up_dict[t])

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.w

model.obj = Objective(
    rule=obj_rule,
    sense=maximize,
    doc="Maximize welfare"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# gnpd(t): gnp(t) = sum(j, v(t,j))
def gnpd_rule(model, t):
    return model.gnp[t] == sum(model.v[t, j] for j in model.j)

model.gnpd = Constraint(
    model.t,
    rule=gnpd_rule,
    doc="GNP definition"
)

# invd(t): ti(t) = s(t) + f(t)
def invd_rule(model, t):
    return model.ti[t] == model.s[t] + model.f[t]

model.invd = Constraint(
    model.t,
    rule=invd_rule,
    doc="Investment definition"
)

# invt(te): ti(te) = sum(j, i(te,j))
def invt_rule(model, te):
    return model.ti[te] == sum(model.i[te, j] for j in model.j)

model.invt = Constraint(
    model.te,
    rule=invt_rule,
    doc="Investment totals"
)

# tgap(t): f(t) = m(t) - e(t) - v(t,"traded")
def tgap_rule(model, t):
    return model.f[t] == model.m[t] - e_dict[t] - model.v[t, "traded"]

model.tgap = Constraint(
    model.t,
    rule=tgap_rule,
    doc="Trade gap"
)

# incd(t): gnp(t) = c(t) + ti(t) - f(t)
def incd_rule(model, t):
    return model.gnp[t] == model.c[t] + model.ti[t] - model.f[t]

model.incd = Constraint(
    model.t,
    rule=incd_rule,
    doc="National income definition"
)

# capb(t,j): v(t,j) <= vb(j) + 1/k(j)*ks(t,j)
def capb_rule(model, t, j):
    vb_val = vb_dict.get(j, 0)
    k_val = data["k"][j]
    return model.v[t, j] <= vb_val + (1/k_val) * model.ks[t, j]

model.capb = Constraint(
    model.t, model.j,
    rule=capb_rule,
    doc="Capacity balance"
)

# kbal(te+1,j): ks(te+1,j) = ks(te,j) + i(te,j)
# This is for te+1, so we need to iterate over te except the last one
def kbal_rule(model, te, j):
    # Get the next period
    te_idx = te_list.index(te)
    if te_idx < len(te_list) - 1:
        te_next = te_list[te_idx + 1]
        return model.ks[te_next, j] == model.ks[te, j] + model.i[te, j]
    else:
        return Constraint.Skip

model.kbal = Constraint(
    model.te, model.j,
    rule=kbal_rule,
    doc="Capital stock balance"
)

# savl(t): s(t) <= sb + alpha*(gnp(t) - gnpb)
def savl_rule(model, t):
    return model.s[t] <= data["sb"] + data["alpha"] * (model.gnp[t] - data["gnpb"])

model.savl = Constraint(
    model.t,
    rule=savl_rule,
    doc="Maximum savings"
)

# impl(t): m(t) >= mb + mgnp*(gnp(t) - gnpb) + mi*(ti(t) - tib)
def impl_rule(model, t):
    return model.m[t] >= (data["mb"] +
                          data["mgnp"] * (model.gnp[t] - data["gnpb"]) +
                          data["mi"] * (model.ti[t] - data["tib"]))

model.impl = Constraint(
    model.t,
    rule=impl_rule,
    doc="Minimum imports"
)

# invu(te+1): ti(te+1) <= (1 + beta)*ti(te)
def invu_rule(model, te):
    te_idx = te_list.index(te)
    if te_idx < len(te_list) - 1:
        te_next = te_list[te_idx + 1]
        return model.ti[te_next] <= (1 + data["beta"]) * model.ti[te]
    else:
        return Constraint.Skip

model.invu = Constraint(
    model.te,
    rule=invu_rule,
    doc="Upper bound on investment"
)

# invl(te+1): ti(te+1) >= ti(te)
def invl_rule(model, te):
    te_idx = te_list.index(te)
    if te_idx < len(te_list) - 1:
        te_next = te_list[te_idx + 1]
        return model.ti[te_next] >= model.ti[te]
    else:
        return Constraint.Skip

model.invl = Constraint(
    model.te,
    rule=invl_rule,
    doc="Lower bound on investment"
)

# conl(te+1): c(te+1) >= (1 + p)*c(te)
def conl_rule(model, te):
    te_idx = te_list.index(te)
    if te_idx < len(te_list) - 1:
        te_next = te_list[te_idx + 1]
        return model.c[te_next] >= (1 + data["p"]) * model.c[te]
    else:
        return Constraint.Skip

model.conl = Constraint(
    model.te,
    rule=conl_rule,
    doc="Lower bound on consumption"
)

# fup(t): f(t) <= q*gnp(t)
def fup_rule(model, t):
    return model.f[t] <= data["q"] * model.gnp[t]

model.fup = Constraint(
    model.t,
    rule=fup_rule,
    doc="Upper bound on f(t)"
)

# taid: fb = sum(t, delt(t)*f(t))
def taid_rule(model):
    return model.fb == sum(delt_dict[t] * model.f[t] for t in model.t)

model.taid = Constraint(
    rule=taid_rule,
    doc="Total aid definition"
)

# wdef: w = sum(t, delt(t)*c(t)) - gama*fb + d*dis*gnp("1985")
def wdef_rule(model):
    return (model.w ==
            sum(delt_dict[t] * model.c[t] for t in model.t) -
            data["gama"] * model.fb +
            data["d"] * dis_val * model.gnp[1985])

model.wdef = Constraint(
    rule=wdef_rule,
    doc="Welfare definition"
)
