# converted from models/nurses_mip.py
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
    doc="Nurse Scheduling Problem: allocate nurses to shifts minimizing cost and maximizing fairness"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.nurse = Set(
    initialize=data["nurse"],
    doc="Nurses"
)
model.shift = Set(
    initialize=data["shift"],
    doc="Shifts"
)
model.department = Set(
    initialize=data["department"],
    doc="Departments"
)
model.skill = Set(
    initialize=data["skill"],
    doc="Nurse skills"
)
model.day = Set(
    initialize=data["day"],
    doc="Days of the week"
)
model.nh = Set(
    initialize=data["nh"],
    doc="NurseData header"
)
model.sh = Set(
    initialize=data["sh"],
    doc="ShiftData header"
)

# Set of tuples for nurse skills
model.nurseSkills = Set(
    initialize=data["nurseSkills"],
    dimen=2,
    doc="Nurse has particular skill"
)

# Set of tuples for vacations
model.vacation = Set(
    initialize=data["vacation"],
    dimen=2,
    doc="Nurse vacation days"
)

# Set of tuples for nurse associations
model.nurseAssoc = Set(
    initialize=data["nurseAssoc"],
    dimen=2,
    doc="Nurses that must work together"
)

# Set of tuples for nurse incompatibilities
model.nurseIncompat = Set(
    initialize=data["nurseIncompat"],
    dimen=2,
    doc="Nurses that cannot work together"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK  (all mutable = True)
# ----------------------------------------------------------------------
model.nurseData = Param(
    model.nurse, model.nh,
    initialize=data["nurseData"],
    mutable=True,
    doc="Nurse data (seniority, qualification, pay rate)"
)

model.shiftData = Param(
    model.shift, model.department, model.day, model.sh,
    initialize=data["shiftData"],
    mutable=True,
    doc="Shift data (start time, end time, min/max requirements)"
)

model.skillRequirements = Param(
    model.department, model.skill,
    initialize=data.get("skillRequirements", {}),
    mutable=True,
    default=0,
    doc="Skill requirements by department"
)

model.maxWorkTime = Param(
    initialize=data["maxWorkTime"],
    mutable=True,
    doc="Maximum working hours per nurse"
)

model.fairnessWeight = Param(
    initialize=data["fairnessWeight"],
    mutable=True,
    doc="Weight for fairness in objective"
)

model.assignmentWeight = Param(
    initialize=data["assignmentWeight"],
    mutable=True,
    doc="Weight for total assignments in objective"
)

# Compute the set s(shift,department,day) - valid shift-department-day combinations
# Extract from the data dictionary before model construction
def init_s(model):
    s_set = []
    # Get all keys from shiftData that have "Start time" as the 4th element
    for key in data["shiftData"].keys():
        if isinstance(key, tuple) and len(key) == 4:
            shift, dept, day, param = key
            if param == "Start time":
                s_set.append((shift, dept, day))
    return s_set

model.s = Set(
    initialize=init_s,
    dimen=3,
    doc="Valid shift-department-day combinations"
)

# Pre-compute duration, startTime, and endTime dictionaries from raw data
# This avoids accessing Pyomo parameters in boolean contexts
duration_dict = {}
startTime_dict = {}
endTime_dict = {}

day_list = list(data["day"])
for key in data["shiftData"].keys():
    if isinstance(key, tuple) and len(key) == 4:
        shift, dept, day, param = key
        if param == "Start time":
            start = data["shiftData"][(shift, dept, day, "Start time")]
            end = data["shiftData"][(shift, dept, day, "End time")]
            dur = (end - start + 24) % 24
            day_idx = day_list.index(day)

            duration_dict[(shift, dept, day)] = dur
            startTime_dict[(shift, dept, day)] = start + day_idx * 24
            endTime_dict[(shift, dept, day)] = start + day_idx * 24 + dur

# Pre-compute skillRequirements for boolean checks
skillRequirements_dict = {}
for key, val in data["skillRequirements"].items():
    if isinstance(key, tuple) and len(key) == 2:
        skillRequirements_dict[key] = val

# Create a function to compute duration (using pre-computed dict)
def duration(model, shift, dept, day):
    return duration_dict.get((shift, dept, day), 0)

# Compute startTime and endTime for each shift (continuous time parameters)
def init_startTime(model):
    return startTime_dict

model.startTime = Param(
    model.s,
    initialize=init_startTime,
    mutable=True,
    doc="Continuous start time for shift"
)

def init_endTime(model):
    return endTime_dict

model.endTime = Param(
    model.s,
    initialize=init_endTime,
    mutable=True,
    doc="Continuous end time for shift"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.nurseAssignments = Var(
    model.nurse, model.s,
    domain=Binary,
    doc="Assign nurse to shift"
)

model.nurseWorkTime = Var(
    model.nurse,
    domain=NonNegativeReals,
    bounds=(0, data["maxWorkTime"]),
    doc="Working time in hours by nurse"
)

model.nurseAvgHours = Var(
    domain=Reals,
    doc="Average working hours"
)

model.nurseMoreThanAvgHours = Var(
    model.nurse,
    domain=NonNegativeReals,
    doc="Overtime (more than average)"
)

model.nurseLessThanAvgHours = Var(
    model.nurse,
    domain=NonNegativeReals,
    doc="Undertime (less than average)"
)

model.fairness = Var(
    domain=Reals,
    doc="Aggregation of all over- and undertime"
)

model.costByDepartments = Var(
    model.department,
    domain=Reals,
    doc="Cost by department"
)

model.totalAssignments = Var(
    domain=Reals,
    doc="Total number of shift assignments"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return (
        sum(model.costByDepartments[d] for d in model.department) +
        model.fairnessWeight * model.fairness +
        model.assignmentWeight * model.totalAssignments
    )

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Composite objective: minimize cost + fairness penalty + assignment penalty"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# defCostDep: cost by department
def defCostDep_rule(model, d):
    return model.costByDepartments[d] == sum(
        model.nurseAssignments[n, shift, dept, day] *
        duration(model, shift, dept, day) *
        model.nurseData[n, "Pay rate"]
        for n in model.nurse
        for (shift, dept, day) in model.s
        if dept == d
    )

model.defCostDep = Constraint(
    model.department,
    rule=defCostDep_rule,
    doc="Cost by department"
)

# defShiftReqMin: minimum nurses required per shift
def defShiftReqMin_rule(model, shift, dept, day):
    return (
        sum(model.nurseAssignments[n, shift, dept, day] for n in model.nurse) >=
        model.shiftData[shift, dept, day, "Minimum requirement"]
    )

model.defShiftReqMin = Constraint(
    model.s,
    rule=defShiftReqMin_rule,
    doc="Minimum nurses required per shift"
)

# defShiftReqMax: maximum nurses allowed per shift
def defShiftReqMax_rule(model, shift, dept, day):
    return (
        sum(model.nurseAssignments[n, shift, dept, day] for n in model.nurse) <=
        model.shiftData[shift, dept, day, "Maximum requirement"]
    )

model.defShiftReqMax = Constraint(
    model.s,
    rule=defShiftReqMax_rule,
    doc="Maximum nurses allowed per shift"
)

# defNurseTime: time worked by each nurse
def defNurseTime_rule(model, n):
    return model.nurseWorkTime[n] == sum(
        model.nurseAssignments[n, shift, dept, day] *
        duration(model, shift, dept, day)
        for (shift, dept, day) in model.s
    )

model.defNurseTime = Constraint(
    model.nurse,
    rule=defNurseTime_rule,
    doc="Time worked by each nurse"
)

# defOneShift: two shifts at the same time are incompatible
def defOneShift_rule(model, n, shift1, dept1, day1, shift2, dept2, day2):
    if (shift1, dept1, day1) == (shift2, dept2, day2):
        return Constraint.Skip
    # Use pre-computed dictionaries to avoid Pyomo parameter comparison in if statement
    start1 = startTime_dict[(shift1, dept1, day1)]
    end1 = endTime_dict[(shift1, dept1, day1)]
    start2 = startTime_dict[(shift2, dept2, day2)]

    if start2 >= start1 and start2 < end1:
        return (
            model.nurseAssignments[n, shift1, dept1, day1] +
            model.nurseAssignments[n, shift2, dept2, day2] <= 1
        )
    return Constraint.Skip

model.defOneShift = Constraint(
    model.nurse, model.s, model.s,
    rule=defOneShift_rule,
    doc="Two shifts at the same time are incompatible"
)

# defNurseIncompat: incompatible nurses cannot work together
def defNurseIncompat_rule(model, n1, n2, shift, dept, day):
    if (n1, n2) in model.nurseIncompat:
        return (
            model.nurseAssignments[n1, shift, dept, day] +
            model.nurseAssignments[n2, shift, dept, day] <= 1
        )
    return Constraint.Skip

model.defNurseIncompat = Constraint(
    model.nurse, model.nurse, model.s,
    rule=defNurseIncompat_rule,
    doc="Incompatible nurses cannot work together"
)

# defNurseAssoc: associated nurses must work together
def defNurseAssoc_rule(model, n1, n2, shift, dept, day):
    if (n1, n2) in model.nurseAssoc:
        return (
            model.nurseAssignments[n1, shift, dept, day] ==
            model.nurseAssignments[n2, shift, dept, day]
        )
    return Constraint.Skip

model.defNurseAssoc = Constraint(
    model.nurse, model.nurse, model.s,
    rule=defNurseAssoc_rule,
    doc="Associated nurses must work together"
)

# defSkillReq: skill requirements must be met
def defSkillReq_rule(model, d, sk, shift, dept, day):
    # Use pre-computed dict to avoid Pyomo parameter comparison in if statement
    skill_req = skillRequirements_dict.get((d, sk), 0)
    if dept == d and skill_req > 0:
        return (
            sum(
                model.nurseAssignments[n, shift, dept, day]
                for n in model.nurse
                if (n, sk) in model.nurseSkills
            ) >= skill_req
        )
    return Constraint.Skip

model.defSkillReq = Constraint(
    model.department, model.skill, model.s,
    rule=defSkillReq_rule,
    doc="Skill requirements must be met"
)

# defAvgHours: compute average hours
def defAvgHours_rule(model):
    return (
        len(model.nurse) * model.nurseAvgHours ==
        sum(model.nurseWorkTime[n] for n in model.nurse)
    )

model.defAvgHours = Constraint(
    rule=defAvgHours_rule,
    doc="Compute average hours"
)

# defOverUnderTime: define over- and undertime
def defOverUnderTime_rule(model, n):
    return (
        model.nurseWorkTime[n] ==
        model.nurseAvgHours +
        model.nurseMoreThanAvgHours[n] -
        model.nurseLessThanAvgHours[n]
    )

model.defOverUnderTime = Constraint(
    model.nurse,
    rule=defOverUnderTime_rule,
    doc="Define over- and undertime"
)

# defFairness: aggregate over- and undertime
def defFairness_rule(model):
    return model.fairness == sum(
        model.nurseMoreThanAvgHours[n] + model.nurseLessThanAvgHours[n]
        for n in model.nurse
    )

model.defFairness = Constraint(
    rule=defFairness_rule,
    doc="Aggregate over- and undertime"
)

# defTotalAssign: total assignments
def defTotalAssign_rule(model):
    return model.totalAssignments == sum(
        model.nurseAssignments[n, shift, dept, day]
        for n in model.nurse
        for (shift, dept, day) in model.s
    )

model.defTotalAssign = Constraint(
    rule=defTotalAssign_rule,
    doc="Total number of assignments"
)

# Fix nurse assignments to 0 for vacation days
for n in model.nurse:
    for (shift, dept, day) in model.s:
        if (n, day) in model.vacation:
            model.nurseAssignments[n, shift, dept, day].fix(0)
