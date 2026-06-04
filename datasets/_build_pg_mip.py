#!/usr/bin/env python
"""Builder for the pg_mip (power-grid / microgrid unit-commitment MIP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "pg_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "T", "members": list(range(1, 25)),
         "doc": "the hours of the day in chronological order, indexed by the integers 1 through 24; the first member is the opening hour and each later member follows the one before it"},
    ],
    "params": [
        {"name": "power_lim_wind", "index": "T", "kind": "limit",
         "doc": "the maximum wind power that can be generated in each hour, in power units"},
        {"name": "power_lim_pv", "index": "T", "kind": "limit",
         "doc": "the maximum solar (photovoltaic) power that can be generated in each hour, in power units"},
        {"name": "power_lim_fuel", "index": "T", "kind": "limit",
         "doc": "the maximum fuel-cell power that can be generated in each hour, in power units; equal to 80 for every hour"},
        {"name": "power_lim_charge", "index": "T", "kind": "limit",
         "doc": "the maximum power that can flow into the battery while charging in each hour, in power units; equal to 200 for every hour"},
        {"name": "power_lim_discharge", "index": "T", "kind": "limit",
         "doc": "the maximum power that can flow out of the battery while discharging in each hour, in power units; equal to 50 for every hour"},
        {"name": "power_lim_battery", "index": "T", "kind": "capacity",
         "doc": "the maximum amount of energy the battery can hold in each hour, in power units; equal to 200 for every hour"},
        {"name": "initial_battery", "index": "", "kind": "level",
         "doc": "the amount of energy stored in the battery at the very start, before the first hour, in power units; a scalar equal to 100"},
        {"name": "load_demand", "index": "T", "kind": "demand",
         "doc": "the electricity load that must be served in each hour, in power units"},
        {"name": "cost_wind", "index": "T", "kind": "cost",
         "doc": "the unit cost of wind generation in each hour, in cost per power unit"},
        {"name": "cost_pv", "index": "T", "kind": "cost",
         "doc": "the unit cost of solar generation in each hour, in cost per power unit"},
        {"name": "cost_fuel", "index": "T", "kind": "cost",
         "doc": "the unit cost of fuel-cell generation in each hour, in cost per power unit"},
        {"name": "cost_charge", "index": "T", "kind": "cost",
         "doc": "the unit cost of charging the battery in each hour, in cost per power unit"},
        {"name": "cost_discharge", "index": "T", "kind": "cost",
         "doc": "the unit cost of discharging the battery in each hour, in cost per power unit"},
        {"name": "cost_undelivered", "index": "T", "kind": "cost",
         "doc": "the penalty cost for each unit of demand left unserved in each hour, in cost per power unit"},
        {"name": "cost_excess", "index": "T", "kind": "cost",
         "doc": "the unit cost charged for surplus generation that has to be dumped in each hour, in cost per power unit; equal to 0 for every hour"},
    ],
    "vars": [
        {"name": "wind", "index": "T", "domain": "NonNegativeReals",
         "doc": "the wind power actually generated in each hour, in power units"},
        {"name": "pv", "index": "T", "domain": "NonNegativeReals",
         "doc": "the solar power actually generated in each hour, in power units"},
        {"name": "fuel", "index": "T", "domain": "NonNegativeReals",
         "doc": "the fuel-cell power actually generated in each hour, in power units"},
        {"name": "charge", "index": "T", "domain": "NonNegativeReals",
         "doc": "the power sent into the battery to charge it in each hour, in power units"},
        {"name": "discharge", "index": "T", "domain": "NonNegativeReals",
         "doc": "the power drawn out of the battery in each hour, in power units"},
        {"name": "undelivered", "index": "T", "domain": "NonNegativeReals",
         "doc": "the amount of demand left unserved in each hour, in power units"},
        {"name": "excess", "index": "T", "domain": "NonNegativeReals",
         "doc": "the surplus generation that exceeds what is needed and must be dumped in each hour, in power units"},
        {"name": "x", "index": "T", "domain": "Binary",
         "doc": "the discharge indicator for each hour; equals 1 if the battery is allowed to discharge that hour and 0 otherwise"},
        {"name": "y", "index": "T", "domain": "Binary",
         "doc": "the charge indicator for each hour; equals 1 if the battery is allowed to charge that hour and 0 otherwise"},
        {"name": "battery", "index": "T", "domain": "NonNegativeReals",
         "doc": "the energy stored in the battery at the end of each hour, in power units"},
        {"name": "tc", "index": "", "domain": "Reals",
         "doc": "the total operating cost over the whole day, in cost units"},
    ],
    "objective": {"sense": "minimize", "expr_var": "tc"},
}

NARRATIVE = (
    "We operate a small power grid over a single day broken into 24 hourly periods. In each hour we "
    "decide how much power to generate from wind, solar, and a fuel cell, how much power to send into "
    "or draw out of a battery, and whether the battery is set to charge or to discharge that hour. We "
    "also account for any demand we fail to serve and any surplus generation that has to be dumped. "
    "Generation, charging, discharging, unserved demand, and surplus each carry their own per-unit "
    "cost that can vary by hour. The objective is to minimize the total operating cost over the day."
)

WIND = (
    "def wind_gen_constraint_rule(m, t):\n"
    "    return m.wind[t] <= m.power_lim_wind[t]\n"
    "model.wind_gen_constraint = Constraint(model.T, rule=wind_gen_constraint_rule)"
)
PV = (
    "def pv_gen_constraint_rule(m, t):\n"
    "    return m.pv[t] <= m.power_lim_pv[t]\n"
    "model.pv_gen_constraint = Constraint(model.T, rule=pv_gen_constraint_rule)"
)
FUEL = (
    "def fuel_gen_constraint_rule(m, t):\n"
    "    return m.fuel[t] <= m.power_lim_fuel[t]\n"
    "model.fuel_gen_constraint = Constraint(model.T, rule=fuel_gen_constraint_rule)"
)
BATTERY = (
    "def battery_constraint_rule(m, t):\n"
    "    return m.battery[t] <= m.power_lim_battery[t]\n"
    "model.battery_constraint = Constraint(model.T, rule=battery_constraint_rule)"
)
DISCHARGE = (
    "def discharge_constraint_rule(m, t):\n"
    "    return m.discharge[t] <= m.power_lim_discharge[t] * m.x[t]\n"
    "model.discharge_constraint = Constraint(model.T, rule=discharge_constraint_rule)"
)
CHARGE = (
    "def charge_constraint_rule(m, t):\n"
    "    return m.charge[t] <= m.power_lim_charge[t] * m.y[t]\n"
    "model.charge_constraint = Constraint(model.T, rule=charge_constraint_rule)"
)
NOSIM = (
    "def no_simultaneous_charge_discharge_constraint_rule(m, t):\n"
    "    return m.x[t] + m.y[t] <= 1\n"
    "model.no_simultaneous_charge_discharge_constraint = Constraint(model.T, rule=no_simultaneous_charge_discharge_constraint_rule)"
)
CHARGECAP = (
    "def discharge_limit_by_battery_constraint_rule(m, t):\n"
    "    return m.charge[t] + (m.initial_battery if t == 1 else m.battery[t-1]) <= m.power_lim_battery[t]\n"
    "model.discharge_limit_by_battery_constraint = Constraint(model.T, rule=discharge_limit_by_battery_constraint_rule)"
)
STATE = (
    "def state_of_battery_constraint_rule(m, t):\n"
    "    return m.battery[t] == (m.initial_battery if t == 1 else m.battery[t-1]) - m.discharge[t] + m.charge[t]\n"
    "model.state_of_battery_constraint = Constraint(model.T, rule=state_of_battery_constraint_rule)"
)
BALANCE = (
    "def power_balance_constraint_rule(m, t):\n"
    "    return m.wind[t] + m.pv[t] + m.fuel[t] + m.discharge[t] + m.undelivered[t] == m.load_demand[t] + m.charge[t] + m.excess[t]\n"
    "model.power_balance_constraint = Constraint(model.T, rule=power_balance_constraint_rule)"
)
TOTALCOST = (
    "def total_cost_definition_rule(m):\n"
    "    return m.tc == sum(m.wind[t]*m.cost_wind[t] + m.pv[t]*m.cost_pv[t] + m.fuel[t]*m.cost_fuel[t] + "
    "m.charge[t]*m.cost_charge[t] + m.discharge[t]*m.cost_discharge[t] + m.undelivered[t]*m.cost_undelivered[t] + "
    "m.excess[t]*m.cost_excess[t] for t in m.T)\n"
    "model.total_cost_definition = Constraint(rule=total_cost_definition_rule)"
)

WHOLESET = "\n".join([WIND, PV, FUEL, BATTERY, DISCHARGE, CHARGE, NOSIM, CHARGECAP, STATE, BALANCE, TOTALCOST])

records = [
    {"description": (
        "In every hour the wind power actually generated cannot exceed the most wind power that is "
        "available to generate that hour."),
     "expected_pyomo": WIND},
    {"description": (
        "In every hour the solar power actually generated cannot exceed the most solar power that is "
        "available to generate that hour."),
     "expected_pyomo": PV},
    {"description": (
        "In every hour the fuel-cell power actually generated cannot exceed the fuel cell's generation "
        "limit for that hour."),
     "expected_pyomo": FUEL},
    {"description": (
        "In every hour the energy held in the battery cannot exceed the battery's storage capacity "
        "for that hour."),
     "expected_pyomo": BATTERY},
    {"description": (
        "The battery can only draw power out when it is set to discharge that hour, and even then the "
        "power drawn out cannot exceed the discharging limit. In every hour the power discharged is "
        "held to zero unless the battery is in discharge mode, and when it is in discharge mode it is "
        "capped at the discharging limit for that hour."),
     "expected_pyomo": DISCHARGE},
    {"description": (
        "The battery can only take power in when it is set to charge that hour, and even then the power "
        "taken in cannot exceed the charging limit. In every hour the power charged is held to zero "
        "unless the battery is in charge mode, and when it is in charge mode it is capped at the "
        "charging limit for that hour."),
     "expected_pyomo": CHARGE},
    {"description": (
        "In every hour the battery cannot be set to charge and to discharge at the same time, so at "
        "most one of those two modes can be active in any given hour."),
     "expected_pyomo": NOSIM},
    {"description": (
        "In every hour the power sent into the battery added to the energy already stored coming into "
        "that hour cannot exceed the battery's storage capacity for that hour. The energy already "
        "stored coming into the hour is the level carried over from the end of the previous hour, "
        "except in the very first hour where it is the starting battery level."),
     "expected_pyomo": CHARGECAP},
    {"description": (
        "In every hour the energy stored in the battery at the end of the hour equals the energy it "
        "held coming into the hour, reduced by whatever was discharged and increased by whatever was "
        "charged that hour. The energy coming into the hour is the level carried over from the end of "
        "the previous hour, except in the very first hour where it is the starting battery level."),
     "expected_pyomo": STATE},
    {"description": (
        "In every hour supply must match demand. The wind, solar, and fuel-cell generation together "
        "with the power discharged from the battery and any unserved demand must equal the load to be "
        "served plus the power used to charge the battery plus any surplus generation that is dumped."),
     "expected_pyomo": BALANCE},
    {"description": (
        "The total operating cost is the sum over all hours of the cost of every activity that hour: "
        "wind, solar, and fuel-cell generation each valued at its own unit cost, charging and "
        "discharging each valued at its own unit cost, unserved demand valued at its penalty cost, and "
        "dumped surplus valued at its cost. Set the total cost variable equal to this sum."),
     "expected_pyomo": TOTALCOST},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "pg_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
