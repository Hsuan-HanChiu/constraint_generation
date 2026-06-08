from pyomo.environ import *
data = globals().get("data", {})
model = ConcreteModel()
model.n = Set(initialize=data["n"], doc="nutrients")
model.f = Set(initialize=data["f"], doc="foods")
model.b = Param(model.n, initialize=data["b"], mutable=True, doc="required daily allowances of nutrients")
model.a = Param(model.f, model.n, initialize=data["a"], mutable=True, doc="nutritive value of foods (per dollar spent)")
model.x = Var(model.f, within=NonNegativeReals, bounds=(0, None), initialize=0, doc="dollars of food f to be purchased daily (dollars)")
model.cost = Var(within=NonNegativeReals, bounds=(0, None), initialize=0, doc="total food bill (dollars)")
def nutrient_balance_rule(model, n):
    return sum(model.a[f, n] * model.x[f] for f in model.f) >= model.b[n]
model.nb = Constraint(model.n, rule=nutrient_balance_rule, doc="nutrient balance (units)")
def cost_balance_rule(model):
    return model.cost == sum(model.x[f] for f in model.f)
model.cb = Constraint(rule=cost_balance_rule, doc="cost balance   (dollars)")
model.obj = Objective(expr=model.cost, sense=minimize, doc="objective function")
