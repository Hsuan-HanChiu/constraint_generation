#!/usr/bin/env python
"""Builder for the copper_mip (world copper sector investment MIP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "copper_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["peru", "chile", "zambia", "zaire", "mex+cam", "s-africa",
                                   "philipines", "papua-ng", "western-us", "eastern-us",
                                   "canada", "ee+ussr", "australia", "w-europe", "japan+kor"],
         "doc": "mine, smelter and refinery locations"},
        {"name": "j", "members": ["mex+cam", "s-africa", "canada", "ee+ussr", "australia",
                                  "w-europe", "japan+kor", "usa", "es-america", "ws-america",
                                  "c-africa", "o-asia", "china"],
         "doc": "wire, tube and sheet plant and market locations"},
        {"name": "cm", "members": ["ore", "scrap-s", "blister", "scrap-r", "refined-cu"],
         "doc": "commodities present in mining and processing (ore, blister, scrap, refined copper)"},
        {"name": "cs", "members": ["refined-cu", "scrap-sps", "sheets+p+s", "wire", "scrap-t", "tubes+rods"],
         "doc": "commodities present at wire, tube and sheet plants"},
        {"name": "cf", "members": ["refined-cu", "sheets+p+s", "wire", "tubes+rods"],
         "doc": "final demanded products (refined copper plus the three semi-manufactures)"},
        {"name": "cfr", "members": ["refined-cu"],
         "doc": "final products that are refined copper; a subset of the commodities"},
        {"name": "cfs", "members": ["sheets+p+s", "wire", "tubes+rods"],
         "doc": "final products that are semi-manufactures; a subset of the commodities"},
        {"name": "cim", "members": ["ore", "blister"],
         "doc": "commodities that can be shipped between mine/smelter/refinery locations, namely ore and blister"},
        {"name": "cil", "members": ["scrap-s", "scrap-r", "scrap-sps", "scrap-t"],
         "doc": "scrap commodity types"},
        {"name": "pm", "members": ["high-grade", "med-grade", "smelting-o", "smelting-s",
                                   "refining-b", "refining-s"],
         "doc": "processes carried out at mines, smelters and refineries"},
        {"name": "pmm", "members": ["high-grade", "med-grade"],
         "doc": "ore mining processes (high-grade and medium-grade)"},
        {"name": "psm", "members": ["wire-ref-c", "tube-ref-c", "tube-scrap", "s-ref-c", "s-scrap"],
         "doc": "semi-manufacturing processes at wire, tube and sheet plants"},
        {"name": "m", "members": ["open-pit", "smelter", "refinery", "wire", "tubes+rods", "sheets+p+s"],
         "doc": "productive units (capacity types)"},
        {"name": "mm", "members": ["open-pit", "smelter", "refinery"],
         "doc": "productive units at mining and processing plants; a subset of the productive units"},
        {"name": "ms", "members": ["wire", "tubes+rods", "sheets+p+s"],
         "doc": "productive units at semi-manufacture plants; a subset of the productive units"},
    ],
    "params": [
        {"name": "sigma", "index": "", "kind": "factor",
         "doc": "capital recovery factor applied to capital charges, a scalar"},
        {"name": "rph", "index": "", "kind": "horizon",
         "doc": "reserve-horizon period length in years, a scalar equal to 20"},
        {"name": "a", "index": "(cm|cs),(pm|psm)", "kind": "io-coefficient",
         "doc": "input-output coefficients of each commodity in each process; positive for an output of the process and negative for an input it consumes; zero where the commodity is not involved"},
        {"name": "b", "index": "m,(pm|psm)", "kind": "capacity-coefficient",
         "doc": "capacity utilization matrix giving how much of a productive unit each process consumes per unit of activity; zero where the unit is not used by the process"},
        {"name": "mapic", "index": "i,cm", "kind": "0/1 mask",
         "doc": "equals 1 if the commodity is present at the mine/smelter/refinery location and 0 otherwise; used to decide which material balances exist there"},
        {"name": "mapip", "index": "i,pm", "kind": "0/1 mask",
         "doc": "equals 1 if the process is available at the mine/smelter/refinery location and 0 otherwise; processes whose mask is 0 are not run there"},
        {"name": "mapjc", "index": "j,cs", "kind": "0/1 mask",
         "doc": "equals 1 if the commodity is present at the wire/tube/sheet plant location and 0 otherwise"},
        {"name": "mapjp", "index": "j,psm", "kind": "0/1 mask",
         "doc": "equals 1 if the semi-manufacturing process is available at the plant location and 0 otherwise"},
        {"name": "demand", "index": "j,cf", "kind": "demand",
         "doc": "required quantity of each final product at each market location, in thousand tons"},
        {"name": "capm", "index": "i,mm", "kind": "capacity",
         "doc": "existing capacity of each productive unit at each mine/smelter/refinery location"},
        {"name": "caps", "index": "j,ms", "kind": "capacity",
         "doc": "existing capacity of each productive unit at each semi-manufacturing location"},
        {"name": "hhatm", "index": "i,mm", "kind": "upper-bound",
         "doc": "maximum permissible plant-size expansion of a productive unit at a mine/smelter/refinery location"},
        {"name": "hhats", "index": "j,ms", "kind": "upper-bound",
         "doc": "maximum permissible plant-size expansion of a productive unit at a semi-manufacturing location"},
        {"name": "hbarm", "index": "i,mm", "kind": "scale-size",
         "doc": "economies-of-scale reference size for an expansion at a mine/smelter/refinery location"},
        {"name": "hbars", "index": "j,ms", "kind": "scale-size",
         "doc": "economies-of-scale reference size for an expansion at a semi-manufacturing location"},
        {"name": "omegam", "index": "i,mm", "kind": "cost",
         "doc": "fixed scale-related capital cost coefficient for mines/smelters/refineries"},
        {"name": "num", "index": "i,mm", "kind": "cost",
         "doc": "proportional (per-unit-of-expansion) capital cost coefficient for mines/smelters/refineries"},
        {"name": "omegas", "index": "j,ms", "kind": "cost",
         "doc": "fixed scale-related capital cost coefficient for semi-manufacturing plants"},
        {"name": "nus", "index": "j,ms", "kind": "cost",
         "doc": "proportional (per-unit-of-expansion) capital cost coefficient for semi-manufacturing plants"},
        {"name": "opm", "index": "i,pm", "kind": "cost",
         "doc": "operating cost per unit of process activity at mines/smelters/refineries"},
        {"name": "ops", "index": "j,psm", "kind": "cost",
         "doc": "operating cost per unit of process activity at semi-manufacturing plants"},
        {"name": "mur", "index": "i,i,cim", "kind": "cost",
         "doc": "transport cost per unit of ore or blister shipped between two mine/smelter/refinery locations"},
        {"name": "mufs", "index": "j,j", "kind": "cost",
         "doc": "transport cost per unit of semi-manufactures shipped between two plant/market locations"},
        {"name": "mui", "index": "i,j", "kind": "cost",
         "doc": "transport cost per unit of refined copper shipped from a smelter/refinery to a plant or market"},
        {"name": "tariffr", "index": "i,j", "kind": "tariff",
         "doc": "tariff per unit of refined copper moved from origin to destination"},
        {"name": "tariffs", "index": "j,j", "kind": "tariff",
         "doc": "tariff per unit of semi-manufactured goods moved from origin to destination"},
        {"name": "reserves", "index": "i,pmm", "kind": "reserves",
         "doc": "ore reserves available for each mining process at each location, in million tons"},
    ],
    "vars": [
        {"name": "zm", "index": "pm,i", "domain": "NonNegativeReals",
         "doc": "activity level of each mining/smelting/refining process at each mine/smelter/refinery location"},
        {"name": "zs", "index": "psm,j", "domain": "NonNegativeReals",
         "doc": "activity level of each semi-manufacturing process at each plant location"},
        {"name": "xi", "index": "cim,i,i", "domain": "NonNegativeReals",
         "doc": "interplant shipment of ore or blister from one mine/smelter/refinery location to another; the second index is the origin and the third is the destination"},
        {"name": "xir", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "refined copper shipped from a smelter/refinery to a semi-manufacturing plant"},
        {"name": "xfr", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "refined copper shipped to a market for end use"},
        {"name": "xfs", "index": "cfs,j,j", "domain": "NonNegativeReals",
         "doc": "semi-manufactured product shipped from a plant to a market; the second index is the origin and the third is the destination"},
        {"name": "ssr", "index": "cil,i", "domain": "NonNegativeReals",
         "doc": "scrap of each type supplied at smelters and refineries"},
        {"name": "ssm", "index": "cil,j", "domain": "NonNegativeReals",
         "doc": "scrap of each type supplied at sheet and tube plants"},
        {"name": "ssa", "index": "j", "domain": "NonNegativeReals",
         "doc": "total scrap supplied at a semi-manufacturing location"},
        {"name": "hm", "index": "m,i", "domain": "NonNegativeReals",
         "doc": "amount of capacity expansion of a productive unit at a mine/smelter/refinery location"},
        {"name": "sm", "index": "m,i", "domain": "NonNegativeReals",
         "doc": "unused economies-of-scale slack for an expansion at a mine/smelter/refinery location"},
        {"name": "hs", "index": "m,j", "domain": "NonNegativeReals",
         "doc": "amount of capacity expansion of a productive unit at a semi-manufacturing location"},
        {"name": "ss", "index": "m,j", "domain": "NonNegativeReals",
         "doc": "unused economies-of-scale slack for an expansion at a semi-manufacturing location"},
        {"name": "ym", "index": "m,i", "domain": "Binary",
         "doc": "equals 1 if a productive unit is expanded at a mine/smelter/refinery location and 0 otherwise"},
        {"name": "ys", "index": "m,j", "domain": "Binary",
         "doc": "equals 1 if a productive unit is expanded at a semi-manufacturing location and 0 otherwise"},
        {"name": "phikm", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total capital charges for mines/smelters/refineries"},
        {"name": "phiks", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total capital charges for semi-manufacturing plants"},
        {"name": "phiom", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total operating cost at mines/smelters/refineries"},
        {"name": "phios", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total operating cost at semi-manufacturing plants"},
        {"name": "phit", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total transport cost"},
        {"name": "phitf", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total tariff cost"},
        {"name": "phiutf", "index": "", "domain": "Reals",
         "doc": "accounting variable holding total annual undiscounted cost including tariffs"},
        {"name": "phi2", "index": "", "domain": "Reals",
         "doc": "accounting variable holding the total cost with tariffs that is minimized"},
    ],
    "objective": {"sense": "minimize", "expr_var": "phi2"},
}

NARRATIVE = (
    "We plan investment and production for the world copper sector for a single base year. "
    "Across many regions we decide how intensely to run each mining, smelting, refining and "
    "semi-manufacturing process, how much to ship ore, blister, refined copper and finished "
    "semi-manufactures between locations and to markets, how much scrap to supply, and which "
    "productive units to expand and by how much, with expansion decisions being yes-or-no choices "
    "that then permit a continuous amount of added capacity. A set of accounting quantities gather "
    "the capital charges, operating costs, transport costs and tariffs into a single total. The "
    "objective is to minimize that total annual cost including tariffs."
)

# ── Per-constraint expected_pyomo (rule bodies mirror the base model exactly) ──

MBM = (
    "def mbm_rule(model, cm, i):\n"
    "    if pyo.value(model.mapic[i, cm]) == 0:\n"
    "        return pyo.Constraint.Skip\n"
    "    lhs = sum(model.a[cm, pm] * model.zm[pm, i] for pm in model.pm if pyo.value(model.mapip[i, pm]) != 0)\n"
    "    if cm in model.cim:\n"
    "        lhs += sum(model.xi[cm, ip, i] for ip in model.i)\n"
    "    if cm in model.cil:\n"
    "        lhs += model.ssr[cm, i]\n"
    "    rhs = 0\n"
    "    if cm in model.cfr:\n"
    "        rhs += sum(model.xfr[i, j] for j in model.j)\n"
    "        rhs += sum(model.xir[i, j] for j in model.j)\n"
    "    if cm in model.cim:\n"
    "        rhs += sum(model.xi[cm, i, ip] for ip in model.i)\n"
    "    return lhs >= rhs\n"
    "model.mbm = Constraint(model.cm, model.i, rule=mbm_rule)"
)
MBS = (
    "def mbs_rule(model, cs, j):\n"
    "    if pyo.value(model.mapjc[j, cs]) == 0:\n"
    "        return pyo.Constraint.Skip\n"
    "    lhs = sum(model.a[cs, psm] * model.zs[psm, j] for psm in model.psm if pyo.value(model.mapjp[j, psm]) != 0)\n"
    "    if cs in model.cfr:\n"
    "        lhs += sum(model.xir[i, j] for i in model.i)\n"
    "    if cs in model.cil:\n"
    "        lhs += model.ssm[cs, j]\n"
    "    rhs = 0\n"
    "    if cs in model.cfs:\n"
    "        rhs += sum(model.xfs[cs, j, jp] for jp in model.j)\n"
    "    return lhs >= rhs\n"
    "model.mbs = Constraint(model.cs, model.j, rule=mbs_rule)"
)
MR = (
    "def mr_rule(model, cf, j):\n"
    "    lhs = 0\n"
    "    if cf in model.cfr:\n"
    "        lhs += sum(model.xfr[i, j] for i in model.i)\n"
    "    if cf in model.cfs:\n"
    "        lhs += sum(model.xfs[cf, jp, j] for jp in model.j)\n"
    "    return lhs >= model.demand[j, cf]\n"
    "model.mr = Constraint(model.cf, model.j, rule=mr_rule)"
)
CCM = (
    "def ccm_rule(model, mm, i):\n"
    "    lhs = sum(model.b[mm, pm] * model.zm[pm, i] for pm in model.pm if pyo.value(model.mapip[i, pm]) != 0)\n"
    "    return lhs <= model.capm[i, mm] + model.hm[mm, i]\n"
    "model.ccm = Constraint(model.mm, model.i, rule=ccm_rule)"
)
CCS = (
    "def ccs_rule(model, ms, j):\n"
    "    lhs = sum(model.b[ms, psm] * model.zs[psm, j] for psm in model.psm if pyo.value(model.mapjp[j, psm]) != 0)\n"
    "    return lhs <= model.caps[j, ms] + model.hs[ms, j]\n"
    "model.ccs = Constraint(model.ms, model.j, rule=ccs_rule)"
)
ICM1 = (
    "def icm1_rule(model, mm, i):\n"
    "    return model.hm[mm, i] <= model.hhatm[i, mm] * model.ym[mm, i]\n"
    "model.icm1 = Constraint(model.mm, model.i, rule=icm1_rule)"
)
ICS1 = (
    "def ics1_rule(model, ms, j):\n"
    "    return model.hs[ms, j] <= model.hhats[j, ms] * model.ys[ms, j]\n"
    "model.ics1 = Constraint(model.ms, model.j, rule=ics1_rule)"
)
ICM2 = (
    "def icm2_rule(model, mm, i):\n"
    "    return model.hm[mm, i] + model.sm[mm, i] >= model.hbarm[i, mm] * model.ym[mm, i]\n"
    "model.icm2 = Constraint(model.mm, model.i, rule=icm2_rule)"
)
ICS2 = (
    "def ics2_rule(model, ms, j):\n"
    "    return model.hs[ms, j] + model.ss[ms, j] >= model.hbars[j, ms] * model.ys[ms, j]\n"
    "model.ics2 = Constraint(model.ms, model.j, rule=ics2_rule)"
)
OREC = (
    "def orec_rule(model, pmm, i):\n"
    "    return model.rph * model.zm[pmm, i] <= 1000 * model.reserves[i, pmm]\n"
    "model.orec = Constraint(model.pmm, model.i, rule=orec_rule)"
)
SBS = (
    "def sbs_rule(model, j):\n"
    "    return model.ssa[j] == sum(model.ssm[cil, j] for cil in model.cil)\n"
    "model.sbs = Constraint(model.j, rule=sbs_rule)"
)
AKM = (
    "def akm_rule(model):\n"
    "    return model.phikm == model.sigma * sum(\n"
    "        model.omegam[i, mm] * model.sm[mm, i] + model.num[i, mm] * model.hm[mm, i]\n"
    "        for i in model.i for mm in model.mm)\n"
    "model.akm = Constraint(rule=akm_rule)"
)
AKS = (
    "def aks_rule(model):\n"
    "    return model.phiks == model.sigma * sum(\n"
    "        model.omegas[j, ms] * model.ss[ms, j] + model.nus[j, ms] * model.hs[ms, j]\n"
    "        for j in model.j for ms in model.ms)\n"
    "model.aks = Constraint(rule=aks_rule)"
)
AOM = (
    "def aom_rule(model):\n"
    "    return model.phiom == sum(\n"
    "        model.opm[i, pm] * model.zm[pm, i]\n"
    "        for pm in model.pm for i in model.i if pyo.value(model.mapip[i, pm]) != 0) / 1000.0\n"
    "model.aom = Constraint(rule=aom_rule)"
)
AOS = (
    "def aos_rule(model):\n"
    "    return model.phios == sum(\n"
    "        model.ops[j, psm] * model.zs[psm, j] for psm in model.psm for j in model.j)\n"
    "model.aos = Constraint(rule=aos_rule)"
)
AOT = (
    "def aot_rule(model):\n"
    "    expr = (\n"
    "        sum(model.mur[i, ip, cim] * model.xi[cim, i, ip] for cim in model.cim for i in model.i for ip in model.i)\n"
    "        + sum(model.mufs[j, jp] * model.xfs[cfs, j, jp] for cfs in model.cfs for j in model.j for jp in model.j)\n"
    "        + sum(model.mui[i, j] * (model.xir[i, j] + model.xfr[i, j]) for i in model.i for j in model.j)\n"
    "    )\n"
    "    return model.phit == expr / 1000.0\n"
    "model.aot = Constraint(rule=aot_rule)"
)
AOTF = (
    "def aotf_rule(model):\n"
    "    expr = (\n"
    "        sum(model.tariffr[i, j] * (model.xfr[i, j] + model.xir[i, j]) for i in model.i for j in model.j)\n"
    "        + sum(model.tariffs[jp, j] * model.xfs[cfs, jp, j] for cfs in model.cfs for jp in model.j for j in model.j)\n"
    "    )\n"
    "    return model.phitf == expr / 1000.0\n"
    "model.aotf = Constraint(rule=aotf_rule)"
)
AUTF = (
    "def autf_rule(model):\n"
    "    return model.phiutf == model.phikm + model.phiks + model.phiom + model.phios + model.phit + model.phitf\n"
    "model.autf = Constraint(rule=autf_rule)"
)
AOBJTF = (
    "def aobjtf_rule(model):\n"
    "    return model.phi2 == model.phiutf\n"
    "model.aobjtf = Constraint(rule=aobjtf_rule)"
)

records = [
    {"description": (
        "At each mine, smelter and refinery location, and for each material that is present there, "
        "the material has to balance. Add up the net amount of that material produced by the "
        "processes run at the location, counting each process by how much of the material it makes "
        "or uses. For ore and blister also add what is shipped in from other locations, and for "
        "scrap materials add the scrap supplied locally. This available amount must be at least what "
        "is needed, which for refined copper is everything shipped out from the location to plants "
        "and to markets, and for ore and blister is everything shipped from this location out to "
        "other locations. Locations where a material is not present have no such requirement."),
     "expected_pyomo": MBM},
    {"description": (
        "At each wire, tube and sheet plant, and for each material present there, the material has "
        "to balance. Add up the net amount of that material produced by the semi-manufacturing "
        "processes run at the plant, and for refined copper also add what is shipped in from "
        "smelters and refineries, and for scrap materials add the scrap supplied at the plant. This "
        "available amount must be at least the amount of finished semi-manufactures shipped out from "
        "the plant to markets. Plants where a material is not present have no such requirement."),
     "expected_pyomo": MBS},
    {"description": (
        "Every market must have its demand met for each final product. For each location and each "
        "final product, the total amount delivered there must be at least the demand. Refined copper "
        "is delivered as refined copper shipments arriving at the location, while each semi-"
        "manufactured product is delivered as shipments of that product arriving from the plants."),
     "expected_pyomo": MR},
    {"description": (
        "No mine, smelter or refinery may run its processes beyond the capacity of each of its "
        "productive units. For each location and each of its productive units, the total use of that "
        "unit across all the processes run there must not exceed the existing capacity of the unit "
        "plus any capacity added by expansion."),
     "expected_pyomo": CCM},
    {"description": (
        "No semi-manufacturing plant may run its processes beyond the capacity of each of its "
        "productive units. For each plant and each of its productive units, the total use of that "
        "unit across all the processes run there must not exceed the existing capacity of the unit "
        "plus any capacity added by expansion."),
     "expected_pyomo": CCS},
    {"description": (
        "Expanding a productive unit at a mine, smelter or refinery is only allowed if the location "
        "decides to expand that unit, and even then the expansion cannot exceed an allowed maximum "
        "size. For each location and each of its productive units, the amount of expansion is held "
        "to zero unless the expansion decision is taken, in which case it may go up to the maximum "
        "permissible plant size."),
     "expected_pyomo": ICM1},
    {"description": (
        "Expanding a productive unit at a semi-manufacturing plant is only allowed if the plant "
        "decides to expand that unit, and even then the expansion cannot exceed an allowed maximum "
        "size. For each plant and each of its productive units, the amount of expansion is held to "
        "zero unless the expansion decision is taken, in which case it may go up to the maximum "
        "permissible plant size."),
     "expected_pyomo": ICS1},
    {"description": (
        "When a productive unit at a mine, smelter or refinery is expanded, the expansion must reach "
        "the economies-of-scale reference size, with any shortfall taken up by a slack quantity. For "
        "each location and each of its productive units, the expansion amount together with its "
        "unused-scale slack must be at least the reference size whenever the expansion decision is "
        "taken, and the requirement is inactive when it is not."),
     "expected_pyomo": ICM2},
    {"description": (
        "When a productive unit at a semi-manufacturing plant is expanded, the expansion must reach "
        "the economies-of-scale reference size, with any shortfall taken up by a slack quantity. For "
        "each plant and each of its productive units, the expansion amount together with its unused-"
        "scale slack must be at least the reference size whenever the expansion decision is taken, "
        "and the requirement is inactive when it is not."),
     "expected_pyomo": ICS2},
    {"description": (
        "Mining cannot draw down more ore than the reserves allow over the planning horizon. For "
        "each ore mining process at each location, the process activity run over the whole reserve "
        "horizon must stay within the ore reserves available to that process at that location."),
     "expected_pyomo": OREC},
    {"description": (
        "At each semi-manufacturing location, the total scrap supplied there equals the sum of the "
        "scrap supplied of every individual scrap type at that location."),
     "expected_pyomo": SBS},
    {"description": (
        "The total capital charges for mines, smelters and refineries are defined by their cost "
        "drivers. Summed over every location and each of its productive units, take the fixed scale-"
        "related cost applied to the unused-scale slack plus the proportional cost applied to the "
        "amount of expansion, scale the whole sum by the capital recovery factor, and set the mine "
        "and smelter and refinery capital-charge accounting quantity equal to it."),
     "expected_pyomo": AKM},
    {"description": (
        "The total capital charges for semi-manufacturing plants are defined by their cost drivers. "
        "Summed over every plant and each of its productive units, take the fixed scale-related cost "
        "applied to the unused-scale slack plus the proportional cost applied to the amount of "
        "expansion, scale the whole sum by the capital recovery factor, and set the semi-"
        "manufacturing capital-charge accounting quantity equal to it."),
     "expected_pyomo": AKS},
    {"description": (
        "The total operating cost at mines, smelters and refineries is defined by process activity. "
        "Summed over every location and each process actually run there, multiply the operating cost "
        "of the process by its activity level, then divide the total by one thousand, and set the "
        "mine and smelter and refinery operating-cost accounting quantity equal to that amount."),
     "expected_pyomo": AOM},
    {"description": (
        "The total operating cost at semi-manufacturing plants is defined by process activity. "
        "Summed over every plant and each semi-manufacturing process, multiply the operating cost of "
        "the process by its activity level, and set the semi-manufacturing operating-cost accounting "
        "quantity equal to that total."),
     "expected_pyomo": AOS},
    {"description": (
        "The total transport cost adds up the cost of moving everything that is shipped. Take the "
        "cost of shipping ore and blister between mine, smelter and refinery locations, plus the "
        "cost of shipping finished semi-manufactures between plant and market locations, plus the "
        "cost of shipping refined copper from smelters and refineries both to plants and to markets, "
        "each priced at its own per-unit shipping rate. Divide the combined total by one thousand "
        "and set the transport-cost accounting quantity equal to it."),
     "expected_pyomo": AOT},
    {"description": (
        "The total tariff cost adds up the tariffs charged on what crosses borders. Take the tariff "
        "on refined copper, charged on both the refined copper sent to markets and the refined "
        "copper sent to plants, plus the tariff on semi-manufactured goods moved between locations, "
        "each priced at its own per-unit tariff rate. Divide the combined total by one thousand and "
        "set the tariff-cost accounting quantity equal to it."),
     "expected_pyomo": AOTF},
    {"description": (
        "The total annual undiscounted cost with tariffs is the sum of all the cost components: the "
        "capital charges for mines, smelters and refineries, the capital charges for semi-"
        "manufacturing plants, the operating costs at both kinds of location, the transport cost and "
        "the tariff cost. Set the undiscounted-total accounting quantity equal to that sum."),
     "expected_pyomo": AUTF},
    {"description": (
        "The total cost that is minimized equals the total annual undiscounted cost with tariffs. "
        "Set the final cost accounting quantity equal to the undiscounted-total accounting quantity."),
     "expected_pyomo": AOBJTF},
]

WHOLESET = "\n".join(r["expected_pyomo"] for r in records)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, balance every material present at each mine, smelter and refinery so that what its "
    "processes net out plus inbound ore, blister and local scrap covers everything shipped out. "
    "Second, balance every material present at each wire, tube and sheet plant so that process "
    "output plus inbound refined copper and local scrap covers the semi-manufactures shipped to "
    "markets. Third, meet the demand for each final product at every market. Fourth, keep process "
    "use within existing plus expanded capacity at each mine, smelter and refinery. Fifth, keep "
    "process use within existing plus expanded capacity at each semi-manufacturing plant. Sixth, "
    "allow expansion of a mine, smelter or refinery unit only when its expansion decision is taken "
    "and only up to the maximum permissible size. Seventh, allow expansion of a semi-manufacturing "
    "unit only when its expansion decision is taken and only up to the maximum permissible size. "
    "Eighth, require an expanded mine, smelter or refinery unit, together with its unused-scale "
    "slack, to reach the economies-of-scale reference size. Ninth, require the same of an expanded "
    "semi-manufacturing unit. Tenth, keep each mining process within its ore reserves over the "
    "reserve horizon. Eleventh, set the total scrap at each semi-manufacturing location equal to "
    "the scrap supplied of every type there. Twelfth, define the capital charges for mines, "
    "smelters and refineries from their fixed and proportional cost drivers scaled by the capital "
    "recovery factor. Thirteenth, define the capital charges for semi-manufacturing plants the same "
    "way. Fourteenth, define the operating cost at mines, smelters and refineries from process "
    "activity, scaled down by one thousand. Fifteenth, define the operating cost at semi-"
    "manufacturing plants from process activity. Sixteenth, define the transport cost from all ore, "
    "blister, refined-copper and semi-manufacture shipments, scaled down by one thousand. "
    "Seventeenth, define the tariff cost from refined-copper and semi-manufacture movements, scaled "
    "down by one thousand. Eighteenth, set the total annual undiscounted cost with tariffs equal to "
    "the sum of the capital, operating, transport and tariff components. Finally, set the total "
    "cost that is minimized equal to that undiscounted total."
)

records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "copper_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
