#!/usr/bin/env python
"""Builder for the mexls_lp (Mexico Steel, large static LP) constraint-generation dataset.

The native constraint rules bake their coefficients into Python preprocessing
(possibility-set masks, input-output tables, transport unit costs) that are NOT
exposed as model components. So the grading namespace ({model, Constraint, sum,
pyo, value, quicksum}) cannot re-run those rules. Instead we SERIALIZE each
already-built native constraint row into a self-contained Pyomo expression over
model.<var>[...] with literal coefficients (logically identical, exec-safe). The
descriptions remain Tier-1 plain language; the embedded numbers live only in the
ground-truth expected_pyomo, never in the description.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from grade_harness import _exec_base, _load_data  # noqa: E402
import pyomo.environ as pyo  # noqa: E402
from pyomo.repn import generate_standard_repn  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PY = ROOT / "../optichat_org/OptiChat/model_library/feas_model/mexls_lp.py"
DATA_JSON = ROOT / "../optichat_org/OptiChat/model_library/feas_model/mexls_lp_data.json"
OUT = HERE / "mexls_lp_constraint_gen.jsonl"

m = _exec_base(str(BASE_PY), _load_data(str(DATA_JSON)))


# ── serializer: native built constraint row → self-contained Pyomo source ─────
def _vref(v):
    comp = v.parent_component().name
    idx = v.index()
    if idx is None:
        return f"model.{comp}"
    if not isinstance(idx, tuple):
        idx = (idx,)
    return f"model.{comp}[{','.join(repr(k) for k in idx)}]"


def _ser_con(con):
    """Return a 'body OP rhs' string, or None if the row is trivial (no vars)."""
    r = generate_standard_repn(con.body, compute_values=True)
    terms = []
    if r.constant:
        terms.append(repr(float(r.constant)))
    for cf, v in zip(r.linear_coefs, r.linear_vars):
        terms.append(f"({repr(float(cf))})*{_vref(v)}")
    if not r.linear_vars:
        return None
    body = " + ".join(terms) if terms else "0"
    if con.equality:
        rhs = float(pyo.value(con.lower))
        # A "sum of nonnegative vars == 0" equality is logically identical to a
        # "<= 0" inequality given the nonneg domains; emit the inequality form so
        # the relop-flip negative control (-> ">= 0", trivially true) is caught.
        if rhs == 0.0 and all(
            v.domain is pyo.NonNegativeReals for v in r.linear_vars
        ) and all(c > 0 for c in r.linear_coefs):
            op = "<="
        else:
            op = "=="
    elif con.has_ub() and not con.has_lb():
        op, rhs = "<=", float(pyo.value(con.upper))
    elif con.has_lb() and not con.has_ub():
        op, rhs = ">=", float(pyo.value(con.lower))
    else:
        raise ValueError("range constraint not supported")
    return f"({body}) {op} {repr(rhs)}"


def gen(name, isets):
    """Serialize constraint `name` into self-contained Pyomo source.
    `isets` is the indexing-set source (e.g. 'model.cm, model.im') or '' for scalar.
    """
    c = m.component(name)
    items = list(c)
    if len(items) == 1 and items[0] is None:
        return f"model.{name} = Constraint(expr={_ser_con(c[None])})"
    rows = {}
    for i in items:
        s = _ser_con(c[i])
        if s is not None:
            rows[i] = s
    multi = isinstance(items[0], tuple)
    arg = "*k" if multi else "k"
    lines = [f"def {name}_rule(model, {arg}):", "    d = {"]
    for i, s in rows.items():
        lines.append(f"        {repr(i)}: {s},")
    lines.append("    }")
    lines.append("    return d.get(k, Constraint.Skip)")
    lines.append(f"model.{name} = Constraint({isets}, rule={name}_rule)")
    return "\n".join(lines)


ISETS = {
    "mbm": "model.cm, model.im",
    "mbr": "model.cr, model.ir",
    "mbs": "model.cs, model.iss",
    "ccm": "model.mm, model.im",
    "ccr": "model.mr, model.ir",
    "ccs": "model.ms, model.iss",
    "mreq": "model.cf, model.j",
    "me": "model.cf",
    "me2": "",
    "pelpc": "model.o",
    "pelal": "",
    "acost": "",
    "arec": "",
    "atrans": "",
    "aimp": "",
    "aexp": "",
}

CODE = {n: gen(n, s) for n, s in ISETS.items()}

# ── components ────────────────────────────────────────────────────────────────
COMPONENTS = {
    "sets": [
        {"name": "im", "members": list(m.im),
         "doc": "iron-ore and coal mining locations"},
        {"name": "ir", "members": list(m.ir),
         "doc": "raw-material plants that turn mined inputs into intermediate raw materials such as pellets and coke"},
        {"name": "iss", "members": list(m.iss),
         "doc": "integrated steel mills, the main production sites"},
        {"name": "j", "members": list(m.j),
         "doc": "domestic market areas where finished steel is demanded"},
        {"name": "pm", "members": list(m.pm),
         "doc": "production processes available at the mines"},
        {"name": "pr", "members": list(m.pr),
         "doc": "production processes available at the raw-material plants"},
        {"name": "ps", "members": list(m.ps),
         "doc": "production processes available at the steel mills"},
        {"name": "cm", "members": list(m.cm),
         "doc": "commodities handled at the mines"},
        {"name": "cr", "members": list(m.cr),
         "doc": "commodities handled at the raw-material plants"},
        {"name": "cs", "members": list(m.cs),
         "doc": "commodities handled at the steel mills, spanning ores, intermediates, finished products and purchased inputs"},
        {"name": "cf", "members": list(m.cf),
         "doc": "final finished steel products sold to markets"},
        {"name": "ce", "members": list(m.ce),
         "doc": "commodities that may be exported"},
        {"name": "o", "members": list(m.o),
         "doc": "ownership shares in the Pena Colorada pellet mine, one entry per owner"},
        {"name": "mm", "members": list(m.mm),
         "doc": "productive units (equipment groups) at the mines"},
        {"name": "mr", "members": list(m.mr),
         "doc": "productive units at the raw-material plants"},
        {"name": "ms", "members": list(m.ms),
         "doc": "productive units at the steel mills"},
    ],
    "params": [
        {"name": "km", "index": "mm, im", "kind": "capacity",
         "doc": "available capacity of each productive unit at each mine, in thousands of tons per year"},
        {"name": "kr", "index": "mr, ir", "kind": "capacity",
         "doc": "available capacity of each productive unit at each raw-material plant, in thousands of tons per year"},
        {"name": "ks", "index": "ms, iss", "kind": "capacity",
         "doc": "available capacity of each productive unit at each steel mill, in thousands of tons per year"},
        {"name": "d", "index": "cf, j", "kind": "demand",
         "doc": "required deliveries of each final product to each market area, in thousands of tons per year"},
        {"name": "emax", "index": "cf", "kind": "limit",
         "doc": "maximum allowed exports of each final product, in thousands of tons per year"},
        {"name": "etot", "index": "", "kind": "limit",
         "doc": "overall ceiling on total exports across all products, in thousands of tons per year"},
        {"name": "sh", "index": "", "kind": "rate",
         "doc": "shadow exchange rate used to convert foreign-currency import and export flows into the cost accounting"},
    ],
    "vars": [
        {"name": "zm", "index": "pm, im", "domain": "NonNegativeReals",
         "doc": "operating level of each mining process at each mine"},
        {"name": "zr", "index": "pr, ir", "domain": "NonNegativeReals",
         "doc": "operating level of each process at each raw-material plant"},
        {"name": "zs", "index": "ps, iss", "domain": "NonNegativeReals",
         "doc": "operating level of each process at each steel mill"},
        {"name": "xm", "index": "(commodity, mine, destination)", "domain": "NonNegativeReals",
         "doc": "shipments of mined commodities from a mine to a downstream raw-material plant or steel mill; only physically allowed origin-destination combinations are present"},
        {"name": "xr", "index": "cs, ir, iss", "domain": "NonNegativeReals",
         "doc": "shipments of commodities from a raw-material plant to a steel mill"},
        {"name": "xs", "index": "cs, iss, iss", "domain": "NonNegativeReals",
         "doc": "interplant shipments of commodities from one steel mill to another"},
        {"name": "xf", "index": "cs, iss, j", "domain": "NonNegativeReals",
         "doc": "shipments of finished products from a steel mill to a market area"},
        {"name": "ur", "index": "cs, ir", "domain": "NonNegativeReals",
         "doc": "domestic purchases of input commodities made at the raw-material plants"},
        {"name": "us", "index": "cs, iss", "domain": "NonNegativeReals",
         "doc": "domestic purchases of input commodities made at the steel mills"},
        {"name": "e", "index": "cs, iss", "domain": "NonNegativeReals",
         "doc": "exports of finished products shipped abroad from a steel mill"},
        {"name": "vs", "index": "cs, iss", "domain": "NonNegativeReals",
         "doc": "imports of input commodities delivered to a steel mill"},
        {"name": "vf", "index": "cs, j", "domain": "NonNegativeReals",
         "doc": "imports of finished products delivered directly to a market area to help meet demand"},
        {"name": "cost", "index": "", "domain": "Reals",
         "doc": "total system cost, in millions of US dollars; the quantity being minimized"},
        {"name": "recurrent", "index": "", "domain": "Reals",
         "doc": "recurrent operating cost: process operating costs plus the cost of domestically purchased inputs, in millions of US dollars"},
        {"name": "transport", "index": "", "domain": "Reals",
         "doc": "total transport cost over every shipment leg in the network, in millions of US dollars"},
        {"name": "imp", "index": "", "domain": "Reals",
         "doc": "total cost of imported commodities and finished products, in millions of US dollars"},
        {"name": "exp", "index": "", "domain": "Reals",
         "doc": "total revenue earned from exports, in millions of US dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "This is a planning model for an integrated Mexican steel industry made up of mines, "
    "raw-material plants, and steel mills serving a set of domestic market areas. We decide "
    "how intensively to run each production process at every mine, raw-material plant, and "
    "mill; how much of each commodity to ship along every leg of the network from mines to "
    "plants to mills to markets, including interplant transfers; how much of each input to "
    "buy domestically or import; and how much finished product to export or bring in from "
    "abroad. The goal is to minimize the total cost of the whole system, which combines "
    "recurrent operating and purchasing costs, transport costs across the network, and the "
    "net cost of imports against export revenue converted at the shadow exchange rate."
)

# ── per-constraint records (description = Tier-1, plain, silent) ──────────────
records = [
    {"name": "mbm", "description": (
        "At each mine, the production of every commodity must be enough to cover everything "
        "that leaves the mine. For each commodity at each mine, the amount produced by the "
        "mining processes there must be at least the total amount of that commodity shipped "
        "out to the downstream plants and mills.")},
    {"name": "mbr", "description": (
        "At each raw-material plant, the supply of every commodity must cover what is sent "
        "onward. For each commodity at each plant, the amount produced by the plant's "
        "processes plus what arrives from the mines plus what is purchased domestically must "
        "be at least the total amount of that commodity shipped out to the steel mills.")},
    {"name": "mbs", "description": (
        "At each steel mill, the availability of every commodity must cover all of its uses. "
        "For each commodity at each mill, the amount made on site plus everything brought in "
        "from mines, raw-material plants, other mills, domestic purchases, and imports must "
        "be at least the total of that commodity sent to other mills, delivered to markets, "
        "and exported.")},
    {"name": "ccm", "description": (
        "Mining capacity cannot be exceeded. For each productive unit at each mine, the total "
        "use of that unit across all processes running there must not exceed its available "
        "capacity.")},
    {"name": "ccr", "description": (
        "Raw-material plant capacity cannot be exceeded. For each productive unit at each "
        "raw-material plant, the total use of that unit across the processes running there "
        "must not exceed its available capacity.")},
    {"name": "ccs", "description": (
        "Steel-mill capacity cannot be exceeded. For each productive unit at each steel mill, "
        "the total use of that unit across the processes running there must not exceed its "
        "available capacity.")},
    {"name": "mreq", "description": (
        "Every market's demand for each final product must be met. For each final product in "
        "each market area, the total delivered from the steel mills plus any of that product "
        "imported directly into the market must be at least the required amount.")},
    {"name": "me", "description": (
        "Exports of each product are limited. For each final product, the total amount "
        "exported across all mills must not exceed the export limit set for that product.")},
    {"name": "me2", "description": (
        "Overall exports are capped. The total of all exports, summed over every product and "
        "every mill, must not exceed the overall export ceiling.")},
    {"name": "pelpc", "description": (
        "Each owner's pellet take from the Pena Colorada mine is limited by its ownership "
        "share. For each owner, the pellets shipped from that mine to mills it has a stake in "
        "must not exceed that owner's share of the mine's pellet capacity.")},
    {"name": "pelal", "description": (
        "The Alzada site ships no pellets. The total pellet shipments out of Alzada to the "
        "steel mills must be zero.")},
    {"name": "acost", "description": (
        "Total cost is assembled from its parts. The total cost equals the recurrent cost "
        "plus the transport cost plus the net of import cost minus export revenue, with that "
        "net foreign-currency amount converted using the shadow exchange rate.")},
    {"name": "arec", "description": (
        "Recurrent cost accounts for running processes and buying inputs. The recurrent cost "
        "equals the operating cost of all mining processes plus the cost of every input "
        "commodity purchased domestically at the raw-material plants and at the steel mills.")},
    {"name": "atrans", "description": (
        "Transport cost adds up the cost of every shipment in the network. The transport cost "
        "equals the sum over all shipment legs of the per-unit transport cost on that leg "
        "times the amount shipped, covering moves from mines, between plants and mills, to "
        "markets, and to and from the ports for imports and exports.")},
    {"name": "aimp", "description": (
        "Import cost values everything brought in from abroad. The import cost equals the sum "
        "over all imported input commodities and imported finished products of the import "
        "price times the quantity imported.")},
    {"name": "aexp", "description": (
        "Export revenue values everything shipped abroad. The export revenue equals the sum "
        "over all exported products of the export price times the quantity exported.")},
]

for r in records:
    r["expected_pyomo"] = CODE[r["name"]]

# ── whole-set record: ordinal narrative composing per-constraint intents ─────
WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, at each mine make sure each commodity produced is enough to cover everything shipped out of that mine. "
    "Second, at each raw-material plant make sure each commodity produced, received from the mines, and bought domestically covers everything shipped onward to the mills. "
    "Third, at each steel mill make sure each commodity made on site together with everything received, purchased, and imported covers everything sent to other mills, delivered to markets, and exported. "
    "Fourth, keep the use of every productive unit at each mine within its capacity. "
    "Fifth, keep the use of every productive unit at each raw-material plant within its capacity. "
    "Sixth, keep the use of every productive unit at each steel mill within its capacity. "
    "Seventh, meet every market's requirement for each final product from mill deliveries plus direct imports. "
    "Eighth, hold exports of each product within its product-specific export limit. "
    "Ninth, hold total exports across all products and mills within the overall export ceiling. "
    "Tenth, limit each owner's pellet take from the Pena Colorada mine to its ownership share of that mine's pellet capacity. "
    "Eleventh, force pellet shipments out of Alzada to be zero. "
    "Twelfth, set total cost equal to recurrent cost plus transport cost plus the net of imports minus exports converted at the shadow exchange rate. "
    "Thirteenth, set recurrent cost equal to the operating cost of the mining processes plus the cost of all domestically purchased inputs. "
    "Fourteenth, set transport cost equal to the sum over every shipment leg of its per-unit transport cost times the amount shipped. "
    "Fifteenth, set import cost equal to the sum over all imports of import price times quantity. "
    "Finally, set export revenue equal to the sum over all exports of export price times quantity."
)
WHOLESET_CODE = "\n".join(CODE[r["name"]] for r in records)

records.append({"name": "_wholeset", "description": WHOLESET_DESC,
                "expected_pyomo": WHOLESET_CODE})

# ── write ─────────────────────────────────────────────────────────────────────
with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "mexls_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
