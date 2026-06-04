#!/usr/bin/env python
"""Builder for the cmo_mip (collateralized mortgage obligation structuring) constraint-generation dataset.

The corpus model is FLAGGED nonlinear: two constraints (defpv, defpvres) discount
cashflows with a per-tranche yield raised to a time power, which is NOT a polynomial
and therefore not Z3-gradable for equivalence. Those two are EXCLUDED; the remaining
19 constraints are linear and are graded.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "cmo_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["n1", "n2", "n3", "n4", "n5", "n6", "m"],
         "doc": "the set of all tranches in the structure; it is the union of the normal tranches and the single mortgage (residual) tranche"},
        {"name": "N", "members": ["n1", "n2", "n3", "n4", "n5", "n6"],
         "doc": "the normal (sequential-pay) tranches; a subset of the tranches, listed in their fixed payment-priority order"},
        {"name": "M", "members": ["m"],
         "doc": "the special tranches that absorb residual coupon and principal; a subset of the tranches"},
        {"name": "TP", "members": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         "doc": "all time periods including the settlement period; an ordered set of consecutive integer periods starting at 0"},
        {"name": "T", "members": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         "doc": "the payment periods; an ordered subset of the time periods, excluding the settlement period 0. For any payment period the immediately preceding period is obtained by subtracting one"},
        {"name": "TS", "members": [0],
         "doc": "the settlement period; a single-element subset of the time periods at which the deal settles and tranche balances are established"},
        {"name": "TL", "members": [10],
         "doc": "the last payment period; a single-element subset of the time periods marking the final period"},
        {"name": "ZPOS", "members": "list of (tranche, period) pairs",
         "doc": "the set of admissible tranche-period combinations; a tranche may only be active (carry balance, pay principal, be selected) in a period if the pair is in this set. Pairs outside this set are structurally forbidden and the corresponding relations are simply not imposed for them"},
    ],
    "params": [
        {"name": "coupon", "index": "I", "kind": "rate",
         "doc": "the per-period coupon rate of each tranche, as a decimal fraction applied to the outstanding balance to compute interest owed"},
        {"name": "prin", "index": "T", "kind": "amount",
         "doc": "the scheduled principal collected from the underlying collateral in each payment period, in currency units"},
        {"name": "cflow", "index": "T", "kind": "amount",
         "doc": "the total cash available to distribute to the tranches in each payment period, in currency units"},
        {"name": "wallo", "index": "N", "kind": "bound",
         "doc": "the lower weighted-average-life bound for each normal tranche, expressed as a coefficient that multiplies the tranche's settlement balance to give the minimum allowed time-weighted principal"},
        {"name": "walup", "index": "N", "kind": "bound",
         "doc": "the upper weighted-average-life bound for each normal tranche, expressed as a coefficient that multiplies the tranche's settlement balance to give the maximum allowed time-weighted principal"},
        {"name": "bign", "index": "", "kind": "big-M",
         "doc": "a large upper constant used to switch a tranche's settlement balance off when the tranche is not included in the structure; a single scalar"},
        {"name": "smalln", "index": "", "kind": "threshold",
         "doc": "a small positive constant giving the minimum settlement balance a tranche must carry when it is included in the structure; a single scalar"},
        {"name": "minn", "index": "", "kind": "count",
         "doc": "the minimum number of normal tranches that must be included in the structure; a single scalar"},
        {"name": "minm", "index": "", "kind": "count",
         "doc": "the minimum number of special tranches that must be included in the structure; a single scalar"},
    ],
    "vars": [
        {"name": "x", "index": "I,TP", "domain": "NonNegativeReals",
         "doc": "the outstanding principal balance of each tranche at the end of each period; the settlement-period balance is the tranche's initial face amount"},
        {"name": "p", "index": "I,TP", "domain": "Reals",
         "doc": "the principal paid down on each tranche in each period; constrained to be nonnegative for the normal tranches"},
        {"name": "c", "index": "I,TP", "domain": "NonNegativeReals",
         "doc": "the total cash (interest plus principal) paid to each tranche in each period"},
        {"name": "r", "index": "T", "domain": "NonNegativeReals",
         "doc": "the residual cash left over and paid out in each period after all tranche distributions"},
        {"name": "tpp", "index": "I", "domain": "NonNegativeReals",
         "doc": "the time-weighted principal of each tranche, i.e. principal paid in each period weighted by the period's elapsed time, accumulated over all payment periods"},
        {"name": "z", "index": "I,TP", "domain": "Binary",
         "doc": "the activity indicator; equals 1 if the tranche is the one being paid down in that period and 0 otherwise"},
        {"name": "y", "index": "I,TP", "domain": "NonNegativeReals",
         "doc": "a cumulative-activity helper accumulating the activity indicators across tranches within a period, in the fixed tranche order; used to enforce sequential pay"},
        {"name": "tin", "index": "I", "domain": "Binary",
         "doc": "the inclusion indicator; equals 1 if the tranche is part of the chosen structure and 0 otherwise"},
        {"name": "pv", "index": "I", "domain": "Reals",
         "doc": "the present value of each tranche's cashflows"},
        {"name": "pvres", "index": "", "domain": "Reals",
         "doc": "the present value of the residual cashflows"},
        {"name": "proceeds", "index": "", "domain": "Reals",
         "doc": "the total gross proceeds raised by the structure"},
    ],
    "objective": {"sense": "maximize", "expr_var": "proceeds"},
}

NARRATIVE = (
    "We design a collateralized mortgage obligation by carving the cashflows of an underlying "
    "mortgage pool into a set of tranches. For each tranche we decide whether to include it in the "
    "deal, how large its initial balance is, how its balance is paid down period by period, the "
    "principal and total cash it receives each period, and the order in which the tranches are "
    "retired. We also track the residual cash and the present value of every tranche. The objective "
    "is to maximize the total gross proceeds raised by the structure."
)

# ---- per-constraint expected_pyomo (linear constraints only) ---------------
# Every rule is self-contained: it derives positions/orderings from model sets,
# because the grader exposes only `model`, `Constraint`, `sum`, `pyo`, `value`.

P_NONNEG = (
    "def p_nonneg_rule(m, n, tp):\n"
    "    return m.p[n, tp] >= 0.0\n"
    "model.p_nonneg = Constraint(model.N, model.TP, rule=p_nonneg_rule)"
)

PDEF = (
    "def pdef_rule(m, i, tp):\n"
    "    if tp not in m.T or (i, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    return m.p[i, tp] == m.x[i, tp - 1] - m.x[i, tp]\n"
    "model.pdef = Constraint(model.I, model.TP, rule=pdef_rule)"
)

CDEF = (
    "def cdef_rule(m, i, tp):\n"
    "    if tp not in m.T or (i, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    return m.c[i, tp] == m.coupon[i] * m.x[i, tp - 1] + m.p[i, tp]\n"
    "model.cdef = Constraint(model.I, model.TP, rule=cdef_rule)"
)

RETIREN1 = (
    "def retiren1_rule(m, tp):\n"
    "    return sum(m.p[n, tp] for n in m.N if (n, tp) in m.ZPOS) == m.prin[tp] + sum(\n"
    "        m.x[mi, tp - 1] * m.coupon[mi] - m.c[mi, tp]\n"
    "        for mi in m.M if (mi, tp) in m.ZPOS)\n"
    "model.retiren1 = Constraint(model.T, rule=retiren1_rule)"
)

RETIRE = (
    "def retire_rule(m, n, tp):\n"
    "    if (n, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    return m.p[n, tp] <= m.cflow[tp] * m.z[n, tp]\n"
    "model.retire = Constraint(model.N, model.T, rule=retire_rule)"
)

RETIREM = (
    "def retirem_rule(m, mi, tp):\n"
    "    if (mi, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    return m.c[mi, tp] <= m.cflow[tp] * m.z[mi, tp]\n"
    "model.retirem = Constraint(model.M, model.T, rule=retirem_rule)"
)

RETIREM1 = (
    "def retirem1_rule(m, mi, tp):\n"
    "    if (mi, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    return m.p[mi, tp] <= m.prin[tp] * m.z[mi, tp]\n"
    "model.retirem1 = Constraint(model.M, model.T, rule=retirem1_rule)"
)

CBAL = (
    "def cbal_rule(m, tp):\n"
    "    return sum(m.c[i, tp] for i in m.I if (i, tp) in m.ZPOS) + m.r[tp] == m.cflow[tp]\n"
    "model.cbal = Constraint(model.T, rule=cbal_rule)"
)

TPPDEF = (
    "def tppdef_rule(m, n):\n"
    "    ord_t = {t: k for k, t in enumerate(m.T, start=1)}\n"
    "    return m.tpp[n] == sum(ord_t[t] * m.p[n, t] for t in m.T if (n, t) in m.ZPOS)\n"
    "model.tppdef = Constraint(model.N, rule=tppdef_rule)"
)

LOWAL = (
    "def lowal_rule(m, n):\n"
    "    return m.wallo[n] * sum(m.x[n, ts] for ts in m.TS) <= m.tpp[n]\n"
    "model.lowal = Constraint(model.N, rule=lowal_rule)"
)

UPWAL = (
    "def upwal_rule(m, n):\n"
    "    return m.walup[n] * sum(m.x[n, ts] for ts in m.TS) >= m.tpp[n]\n"
    "model.upwal = Constraint(model.N, rule=upwal_rule)"
)

SEQ1 = (
    "def seq1_rule(m, tp):\n"
    "    return sum(m.z[i, tp] for i in m.I if (i, tp) in m.ZPOS) == 1.0\n"
    "model.seq1 = Constraint(model.T, rule=seq1_rule)"
)

SEQ2 = (
    "def seq2_rule(m, i, tp):\n"
    "    TL = list(m.TL)[0]\n"
    "    if tp not in m.T or tp == TL or (i, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    return m.y[i, tp] >= m.y[i, tp + 1]\n"
    "model.seq2 = Constraint(model.I, model.TP, rule=seq2_rule)"
)

YDEF = (
    "def ydef_rule(m, i, tp):\n"
    "    if tp not in m.T or (i, tp) not in m.ZPOS:\n"
    "        return Constraint.Skip\n"
    "    I_list = list(m.I)\n"
    "    idx = I_list.index(i)\n"
    "    if idx < 1:\n"
    "        return m.y[i, tp] == m.z[i, tp]\n"
    "    prev_i = I_list[idx - 1]\n"
    "    return m.y[i, tp] == m.y[prev_i, tp] + m.z[i, tp]\n"
    "model.ydef = Constraint(model.I, model.TP, rule=ydef_rule)"
)

TINDEF1 = (
    "def tindef1_rule(m, i):\n"
    "    return sum(m.x[i, ts] for ts in m.TS) <= m.tin[i] * m.bign\n"
    "model.tindef1 = Constraint(model.I, rule=tindef1_rule)"
)

TINDEF2 = (
    "def tindef2_rule(m, i):\n"
    "    return sum(m.x[i, ts] for ts in m.TS) >= m.tin[i] * m.smalln\n"
    "model.tindef2 = Constraint(model.I, rule=tindef2_rule)"
)

NCON = (
    "def ncon_rule(m):\n"
    "    return sum(m.tin[n] for n in m.N) >= 3.0\n"
    "model.ncon = Constraint(rule=ncon_rule)"
)

MCON = (
    "def mcon_rule(m):\n"
    "    return sum(m.tin[mi] for mi in m.M) >= 1.0\n"
    "model.mcon = Constraint(rule=mcon_rule)"
)

PROCEEDS_DEF = (
    "def proceeds_rule(m):\n"
    "    return m.proceeds == sum(m.pv[i] for i in m.I) + m.pvres\n"
    "model.proceeds_def = Constraint(rule=proceeds_rule)"
)

WHOLESET = "\n".join([
    P_NONNEG, PDEF, CDEF, RETIREN1, RETIRE, RETIREM, RETIREM1, CBAL, TPPDEF,
    LOWAL, UPWAL, SEQ1, SEQ2, YDEF, TINDEF1, TINDEF2, NCON, MCON, PROCEEDS_DEF,
])

records = [
    {"description": (
        "The principal paid down on any normal tranche in any period can never be negative, so a "
        "normal tranche never pays back less than nothing in a period."),
     "expected_pyomo": P_NONNEG},
    {"description": (
        "For every tranche and every payment period where that tranche is allowed to be active, the "
        "principal it pays down in the period equals how much its outstanding balance falls from the "
        "previous period to this one. This ties the principal paydown to the decline in the tranche's "
        "balance over the period."),
     "expected_pyomo": PDEF},
    {"description": (
        "For every tranche and every payment period where that tranche is allowed to be active, the "
        "total cash the tranche receives in the period equals the interest accrued on its balance "
        "carried in from the previous period plus the principal it pays down that period."),
     "expected_pyomo": CDEF},
    {"description": (
        "In each payment period, the principal paid across all the normal tranches must equal the "
        "scheduled principal collected from the collateral that period, adjusted by the special "
        "tranches: for each special tranche we add the interest accrued on its prior balance and "
        "subtract the total cash it receives. Only tranche-period combinations that are allowed "
        "enter this balance."),
     "expected_pyomo": RETIREN1},
    {"description": (
        "A normal tranche can only pay down principal in a period when it is the tranche being "
        "retired that period, and even then the paydown cannot exceed the cash available that "
        "period. When it is not the active tranche, its principal paydown is forced to zero. This "
        "is imposed only for allowed tranche-period combinations."),
     "expected_pyomo": RETIRE},
    {"description": (
        "A special tranche can only receive cash in a period when it is the active tranche that "
        "period, and even then the cash it receives cannot exceed the cash available that period. "
        "When it is not active, its cash is forced to zero. This is imposed only for allowed "
        "tranche-period combinations."),
     "expected_pyomo": RETIREM},
    {"description": (
        "A special tranche can only pay down principal in a period when it is the active tranche "
        "that period, and even then its paydown cannot exceed the scheduled principal collected "
        "that period. When it is not active, its principal paydown is forced to zero. This is "
        "imposed only for allowed tranche-period combinations."),
     "expected_pyomo": RETIREM1},
    {"description": (
        "In each payment period the total cash distributed across all tranches plus the residual "
        "cash paid out must exactly use up the cash available that period. Only allowed "
        "tranche-period combinations contribute to the distributed total."),
     "expected_pyomo": CBAL},
    {"description": (
        "For each normal tranche, its time-weighted principal equals the sum over the payment "
        "periods of the principal it pays down in each period weighted by how many periods have "
        "elapsed. Only periods where the tranche is allowed to be active contribute."),
     "expected_pyomo": TPPDEF},
    {"description": (
        "Each normal tranche must meet a minimum weighted average life: its time-weighted principal "
        "must be at least its lower-bound coefficient times its settlement balance."),
     "expected_pyomo": LOWAL},
    {"description": (
        "Each normal tranche must not exceed a maximum weighted average life: its time-weighted "
        "principal must be no more than its upper-bound coefficient times its settlement balance."),
     "expected_pyomo": UPWAL},
    {"description": (
        "In each payment period exactly one tranche is the active tranche being paid down, so the "
        "activity indicators over all allowed tranches in that period add up to one."),
     "expected_pyomo": SEQ1},
    {"description": (
        "The tranches are retired in a fixed order, so the cumulative-activity helper for a tranche "
        "in a period must be at least its value in the next period. This is imposed for every "
        "tranche and every payment period except the final one, and only for allowed "
        "tranche-period combinations."),
     "expected_pyomo": SEQ2},
    {"description": (
        "The cumulative-activity helper accumulates the activity indicators across the tranches "
        "within each period, following the fixed tranche order. For the first tranche the helper "
        "equals its own activity indicator, and for every later tranche the helper equals the "
        "previous tranche's helper plus its own activity indicator. This is imposed for each payment "
        "period and only for allowed tranche-period combinations."),
     "expected_pyomo": YDEF},
    {"description": (
        "A tranche's settlement balance is switched off unless the tranche is included in the "
        "structure: for every tranche the settlement balance cannot exceed the large inclusion cap "
        "times its inclusion indicator."),
     "expected_pyomo": TINDEF1},
    {"description": (
        "When a tranche is included in the structure it must carry at least a minimum settlement "
        "balance: for every tranche the settlement balance must be at least the small threshold "
        "times its inclusion indicator."),
     "expected_pyomo": TINDEF2},
    {"description": (
        "At least a minimum number of normal tranches must be included in the structure, so the "
        "inclusion indicators of the normal tranches add up to at least that minimum."),
     "expected_pyomo": NCON},
    {"description": (
        "At least a minimum number of special tranches must be included in the structure, so the "
        "inclusion indicators of the special tranches add up to at least that minimum."),
     "expected_pyomo": MCON},
    {"description": (
        "The total gross proceeds equal the sum of the present values of all the tranches plus the "
        "present value of the residual cashflows."),
     "expected_pyomo": PROCEEDS_DEF},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "cmo_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
