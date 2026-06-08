# converted from models/dea_lp.py
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
model.I  = Set(initialize=data["i"],  ordered=True)
model.J  = Set(initialize=data["j"],  ordered=True)
model.Ji = Set(initialize=data["ji"], within=model.J)
model.Jo = Set(initialize=data["jo"], within=model.J)

# Scalars
model.vlo  = Param(initialize=float(data.get("vlo", 1e-4)), mutable=True)
model.ulo  = Param(initialize=float(data.get("ulo", 1e-4)), mutable=True)
model.norm = Param(initialize=float(data.get("norm", 100.0)), mutable=True)
model.rts  = Param(initialize=str(data.get("returns_to_scale","CRS")).upper())

# Selected DMU
sel = data.get("selected_unit") or (data.get("ii",[None])[0]) or next(iter(model.I))
if sel not in data["i"]:
    raise ValueError(f"selected_unit='{sel}' not in set i")
model.isel = Param(initialize=str(sel))

# Data — accept both nested {"Depot": {"attr": v}} and tuple-keyed {("Depot","attr"): v}
# (the latter arises from add_indexes_and_solve normalizing pipe-keys to tuples)
_tab_raw = data["data"]
_tab = {}
for k, v in _tab_raw.items():
    if isinstance(v, dict):
        for jj, val in v.items():
            _tab[(k, jj)] = val
    elif isinstance(k, tuple) and len(k) == 2:
        _tab[k] = v
    else:
        raise KeyError(f"unsupported data entry key={k!r}")
def _d(_m, ii, jj):
    try: return float(_tab[(ii, jj)])
    except KeyError: raise KeyError(f"missing data[{ii}][{jj}]")
model.data = Param(model.I, model.J, initialize=_d, mutable=True)

# Dual vars
model.lam = Var(model.I,  domain=NonNegativeReals)
model.vs  = Var(model.Ji, domain=NonNegativeReals)
model.us  = Var(model.Jo, domain=NonNegativeReals)
model.z   = Var(domain=Reals)
model.eff = Var(domain=Reals)

# Dual constraints (only for isel in equalities)
def _dii(_m, jj):
    i0 = _m.isel.value
    return sum(_m.lam[i]*_m.data[i, jj] for i in _m.I) + _m.vs[jj] == _m.z * _m.data[i0, jj]
model.dii = Constraint(model.Ji, rule=_dii)

def _dio(_m, jj):
    i0 = _m.isel.value
    return sum(_m.lam[i]*_m.data[i, jj] for i in _m.I) - _m.us[jj] == _m.data[i0, jj]
model.dio = Constraint(model.Jo, rule=_dio)

# VRS: sum(lam) = 1; CRS: omit
if str(model.rts.value) == "VRS":
    model.defvar = Constraint(expr = sum(model.lam[i] for i in model.I) == 1)

# Objective (min)
model.obj = Objective(expr=model.eff, sense=minimize)

# eff = norm*z - vlo*sum(vs) - ulo*sum(us)
model.dobj = Constraint(expr = model.eff == model.norm*model.z
                              - model.vlo*sum(model.vs[j] for j in model.Ji)
                              - model.ulo*sum(model.us[j] for j in model.Jo))
