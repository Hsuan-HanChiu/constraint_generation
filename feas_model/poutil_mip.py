# converted from models/poutil_mip.py
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
model.t = Set(initialize=data['t'], ordered=True, doc='time slices (quarter-hour)')
model.m = Set(initialize=data['m'], ordered=True, doc='plant stages m1..m8')
model.iS = Set(initialize=data['iS'], ordered=True, doc='interval for constant PP operation')
model.iI = Set(initialize=data['iI'], ordered=True, doc='idle time period indices')
model.b = Set(initialize=data['b'], ordered=True, doc='support points of zone prices')

# Parameters / Scalars
model.PowerForecast = Param(model.t, initialize=data['PowerForecast'], mutable=False,
                            doc='electric power forecast (MW)')

model.cPPvar = Param(initialize=data['cPPvar'], mutable=False, doc='variable cost of PP [euro/MWh]')
model.pPPMax = Param(initialize=data['pPPMax'], mutable=False, doc='maximal capacity of PP [MW]')

model.cBL = Param(initialize=data['cBL'], mutable=False, doc='cost for one base load contract [euro/MWh]')
model.cPL = Param(initialize=data['cPL'], mutable=False, doc='cost for one peak load contract [euro/MWh]')

model.pLFCref = Param(initialize=data['pLFCref'], mutable=False, doc='power reference level for the LFC [MW]')

# eLFCbY and cLFCvar (given per segment b)
model.eLFCbY = Param(model.b, initialize=data['eLFCbY'], mutable=False, doc='daily energy amount (yearly raw) per b')
model.cLFCvar = Param(model.b, initialize=data['cLFCvar'], mutable=False, doc='specific energy price in segment b')

# Derived: eLFCb (daily borders) and cLFCs (accumulated costs)
# Compute in Python and pass as params
eLFCb = {b: float(value(model.eLFCbY[b]) / 365.0) for b in model.b}
# accumulated cost cLFCs: cLFCs(b1)=0 ; cLFCs(b2)=cLFCvar(b1)*eLFCb(b1); others increment
cLFCs = {}
b_list = list(model.b)
for idx, b in enumerate(b_list):
    if idx == 0:
        cLFCs[b] = 0.0
    else:
        # accumulate previous segments' costs
        prev = b_list[idx - 1]
        cLFCs[b] = cLFCs[prev] + float(value(model.cLFCvar[prev]) * eLFCb[prev])

model.eLFCb = Param(model.b, initialize=eLFCb, mutable=False, doc='daily border of energy volumes for LFC')
model.cLFCs = Param(model.b, initialize=cLFCs, mutable=False, doc='accumulated cost for LFC up to segment b')

# Binary indicator IPL(t) for peak load contracts (ord 33..80 inclusive)
# We compute IPL on the Python side as boolean->0/1 values (GAMS used ord)
t_list = list(model.t)
IPL_init = {}
for idx, tname in enumerate(t_list, start=1):  # ord(t) starts at 1 in GAMS
    IPL_init[tname] = 1 if 33 <= idx <= 80 else 0
model.IPL = Param(model.t, initialize=IPL_init, mutable=False, doc='indicator for peak load contracts (0/1)')

# -----------------------
# Variables (GAMS names preserved)
# -----------------------
model.c = Var(domain=Reals, doc='total cost')
model.cPP = Var(domain=NonNegativeReals, doc='cost of PP usage')
model.pPP = Var(model.t, domain=NonNegativeReals, doc='power withdrawn from power plant (MW)')
model.delta = Var(model.m, model.t, domain=Binary, doc='indicate if PP is in stage m at time t')
model.chiS = Var(model.t, domain=NonNegativeReals, doc='indicate if a PP stage change occurs at t')
model.chiI = Var(model.t, domain=NonNegativeReals, doc='indicate if PP left idle stage at t')
model.cSM = Var(domain=NonNegativeReals, doc='cost of energy from spot market')
model.pSM = Var(model.t, domain=NonNegativeReals, doc='power from the spot market (MW)')
model.alpha = Var(domain=Integers, bounds=(0, max(data['PowerForecast'].values())), doc='quantity of base load contracts')
model.beta = Var(domain=Integers, bounds=(0, max(data['PowerForecast'].values())), doc='quantity of peak load contracts')
model.cLFC = Var(domain=NonNegativeReals, doc='cost of LFC (energy rate)')
model.eLFCtot = Var(domain=NonNegativeReals, doc='total LFC energy (MWh/day equivalent)')
model.eLFCs = Var(model.b, domain=NonNegativeReals, doc='energy from LFC in segment b (daily)')
model.pLFC = Var(model.t, domain=NonNegativeReals, doc='power from the LFC (MW)')
model.mu = Var(model.b, domain=Binary, doc='indicator for which LFC price segment (one-hot)')

# Set variable upper bounds consistent with GAMS
# alpha.up = smax(t, PowerForecast(t))  -> maximum forecast value
max_pf = max(data['PowerForecast'].values())
model.alpha.setub(int(max_pf))
model.beta.setub(int(max_pf))
# pLFC.up(t) = pLFCref
for tt in model.t:
    model.pLFC[tt].setub(float(value(model.pLFCref)))

# -----------------------
# Constraints (GAMS names preserved). Each has doc string set via "doc" arg.
# -----------------------

# obj.. c =e= cPP + cSM + cLFC;
def obj_rule(m):
    return m.c == m.cPP + m.cSM + m.cLFC
model.obj = Constraint(rule=obj_rule, doc='objective function: total cost')

# demand(t).. pPP(t) + pSM(t) + pLFC(t) =e= PowerForecast(t);
def demand_rule(m, t):
    return m.pPP[t] + m.pSM[t] + m.pLFC[t] == m.PowerForecast[t]
model.demand = Constraint(model.t, rule=demand_rule, doc='demand constraint per time slice')

# PPcost.. cPP =e= cPPvar*sum(t, 0.25*pPP(t));
def PPcost_rule(m):
    return m.cPP == float(m.cPPvar) * sum(0.25 * m.pPP[t] for t in m.t)
model.PPcost = Constraint(rule=PPcost_rule, doc='power plant cost (variable cost term)')

# PPpower(t).. pPP(t) =e= pPPMax*sum(m$(ord(m) > 1), 0.1*(ord(m) + 2)*delta(m,t));
def PPpower_rule(m, t):
    # sum over m with ord(m)>1. In Python indices start at 0 -> ord>1 means index>=1
    m_list = list(m.m)
    val = 0.0
    for idx, mm in enumerate(m_list, start=1):
        if idx > 1:
            val += 0.1 * (idx + 2) * m.delta[mm, t]
    return m.pPP[t] == float(m.pPPMax) * val
model.PPpower = Constraint(model.t, rule=PPpower_rule, doc='power produced by PP from stage indicators')

# PPstage(t).. sum(m, delta(m,t)) =e= 1;
def PPstage_rule(m, t):
    return sum(m.delta[mm, t] for mm in m.m) == 1
model.PPstage = Constraint(model.t, rule=PPstage_rule, doc='exactly one stage at any time')

# PPchiS1(t,m)$(ord(t)>1).. chiS(t) =g= delta(m,t) - delta(m,t-1);
# PPchiS2(t,m)$(ord(t)>1).. chiS(t) =g= delta(m,t-1) - delta(m,t);
t_list = list(model.t)
def PPchiS1_rule(m, t, mm):
    idx = t_list.index(t)
    if idx == 0:
        return Constraint.Skip
    prev_t = t_list[idx - 1]
    return m.chiS[t] >= m.delta[mm, t] - m.delta[mm, prev_t]
model.PPchiS1 = Constraint(model.t, model.m, rule=PPchiS1_rule, doc='relate chiS and delta (1)')

def PPchiS2_rule(m, t, mm):
    idx = t_list.index(t)
    if idx == 0:
        return Constraint.Skip
    prev_t = t_list[idx - 1]
    return m.chiS[t] >= m.delta[mm, prev_t] - m.delta[mm, t]
model.PPchiS2 = Constraint(model.t, model.m, rule=PPchiS2_rule, doc='relate chiS and delta (2)')

# PPstageChange(t)$(ord(t) < card(t) - card(iS) + 2).. sum(iS, chiS(t + ord(iS))) =l= 1;
iS_list = list(model.iS)
n_t = len(t_list)
n_iS = len(iS_list)
def PPstageChange_rule(m, t):
    idx = t_list.index(t)  # 0-based
    # GAMS ord starts at 1; condition ord(t) < card(t) - card(iS) + 2
    # Translate: (idx+1) < n_t - n_iS + 2 -> idx < n_t - n_iS + 1
    if not (idx < (n_t - n_iS + 1)):
        return Constraint.Skip
    # sum over iS: chiS(t + ord(iS))
    s = 0.0
    for iS_idx, iSname in enumerate(iS_list, start=1):
        # t + ord(iS) => shift by iS_idx
        new_idx = idx + iS_idx
        if new_idx < n_t:
            s += m.chiS[t_list[new_idx]]
    return s <= 1
model.PPstageChange = Constraint(model.t, rule=PPstageChange_rule,
                                 doc='restrict the number of stage changes (minimum up-time logic)')

# PPstarted(t).. chiI(t) =g= delta("m1",t-1) - delta("m1",t);
def PPstarted_rule(m, t):
    idx = t_list.index(t)
    if idx == 0:
        return Constraint.Skip
    prev = t_list[idx - 1]
    return m.chiI[t] >= m.delta['m1', prev] - m.delta['m1', t]
model.PPstarted = Constraint(model.t, rule=PPstarted_rule, doc='indicate if plant left idle state')

# PPidleTime(t)$(ord(t) < card(t) - card(iI) + 2).. sum(iI, chiI(t + ord(iI))) =l= 1;
iI_list = list(model.iI)
n_iI = len(iI_list)
def PPidleTime_rule(m, t):
    idx = t_list.index(t)
    if not (idx < (n_t - n_iI + 1)):
        return Constraint.Skip
    s = 0.0
    for iI_idx, iIname in enumerate(iI_list, start=1):
        new_idx = idx + iI_idx
        if new_idx < n_t:
            s += m.chiI[t_list[new_idx]]
    return s <= 1
model.PPidleTime = Constraint(model.t, rule=PPidleTime_rule, doc='control minimum idle time')

# SMcost.. cSM =e= 24*cBL*alpha + 12*cPL*beta;
def SMcost_rule(m):
    return m.cSM == 24.0 * float(m.cBL) * m.alpha + 12.0 * float(m.cPL) * m.beta
model.SMcost = Constraint(rule=SMcost_rule, doc='cost associated with spot market')

# SMpower(t).. pSM(t) =e= alpha + IPL(t)*beta;
def SMpower_rule(m, t):
    return m.pSM[t] == m.alpha + int(m.IPL[t]) * m.beta
model.SMpower = Constraint(model.t, rule=SMpower_rule, doc='spot market supply by contracts')

# LFCcost.. cLFC =e= sum(b, cLFCs(b)*mu(b) + cLFCvar(b)*eLFCs(b));
def LFCcost_rule(m):
    return m.cLFC == sum(m.cLFCs[b] * m.mu[b] + float(m.cLFCvar[b]) * m.eLFCs[b] for b in m.b)
model.LFCcost = Constraint(rule=LFCcost_rule, doc='cost of the LFC (accumulated + variable part)')

# LFCenergy.. eLFCtot =e= sum(t, 0.25*pLFC(t));
def LFCenergy_rule(m):
    return m.eLFCtot == sum(0.25 * m.pLFC[t] for t in m.t)
model.LFCenergy = Constraint(rule=LFCenergy_rule, doc='total energy from LFC (daily)')

# LFCmu.. sum(b, mu(b)) =e= 1;
def LFCmu_rule(m):
    return sum(m.mu[b] for b in m.b) == 1
model.LFCmu = Constraint(rule=LFCmu_rule, doc='one price segment selected for LFC')

# LFCenergyS.. eLFCtot =e= sum(b$(ord(b) > 1), eLFCb(b-1)*mu(b)) + sum(b, eLFCs(b));
def LFCenergyS_rule(m):
    b_list_local = list(m.b)
    part = 0.0
    for idx, b in enumerate(b_list_local):
        if idx > 0:
            part += m.eLFCb[b_list_local[idx - 1]] * m.mu[b]
    return m.eLFCtot == part + sum(m.eLFCs[b] for b in m.b)
model.LFCenergyS = Constraint(rule=LFCenergyS_rule, doc='connect mu with total energy amount')

# LFCemuo.. eLFCs("b1") =l= eLFCb("b1")*mu("b1");
def LFCemuo_rule(m):
    b1 = list(m.b)[0]
    return m.eLFCs[b1] <= m.eLFCb[b1] * m.mu[b1]
model.LFCemuo = Constraint(rule=LFCemuo_rule, doc='accumulated energy amount for segment b1')

# LFCemug(b)$(ord(b) > 1).. eLFCs(b) =l= (eLFCb(b) - eLFCb(b-1))*mu(b);
def LFCemug_rule(m, b):
    b_list_local = list(m.b)
    idx = b_list_local.index(b)
    if idx == 0:
        return Constraint.Skip
    prev = b_list_local[idx - 1]
    return m.eLFCs[b] <= (m.eLFCb[b] - m.eLFCb[prev]) * m.mu[b]
model.LFCemug = Constraint(model.b, rule=LFCemug_rule, doc='accumulated energy amount for other segments')

# Objective: minimize c
model.min_obj = Objective(expr=model.c, sense=minimize)
