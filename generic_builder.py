#!/usr/bin/env python
"""
PROTOTYPE: a single generic base-model builder (option B).

A constraint-generation grade only needs the SCAFFOLD a constraint references:
the sets (so sums expand), the params (so numbers substitute), and the variables
(so they become Z3 unknowns with the right domain/bounds/fixings). It does NOT
need any of the model's own constraints — the Z3 checker isolates and compares
only the single ADDED constraint. So one generic builder can replace per-model
.py base builders, driven by the dataset's `components` block + a data dict.

This module:
  - generic_build_model(components, data, extras) -> ConcreteModel (scaffold only)
  - freeze_scaffold(model) -> (components, data, extras) extracted from a built
    model, so we can MIGRATE any corpus .py automatically (no hand authoring).

`extras` carries the two things the prose `components` block doesn't encode yet:
  - bounds:  {var_name: [lo, hi]}            (per-var rectangular bounds)
  - fixings: [{"var","index","value"}, ...]  (e.g. tsp diagonal x[i,i]=0, u[start]=1)

Run `python generic_builder.py` (in the `opti` env) to verify the generic base
gives IDENTICAL grading verdicts to the original .py base on every registered
model — the empirical faithfulness gate.
"""
from __future__ import annotations
import copy
import pyomo.environ as pyo

# domain word -> pyomo domain object
_DOMAINS = {
    "Binary": pyo.Binary, "Boolean": pyo.Binary,
    "Reals": pyo.Reals, "NonNegativeReals": pyo.NonNegativeReals,
    "PositiveReals": pyo.PositiveReals, "NegativeReals": pyo.NegativeReals,
    "Integers": pyo.Integers, "NonNegativeIntegers": pyo.NonNegativeIntegers,
    "PositiveIntegers": pyo.PositiveIntegers,
}

def _norm_key(k):
    """Normalize a param key to what Pyomo expects: split pipe-joined multi-dim
    string keys into int-coerced tuples; leave tuples/scalars as-is. Mirrors the
    loader's _conv_key so generic_build accepts both loader-shaped (tuple) and
    frozen-shaped (pipe-string) data."""
    if isinstance(k, str) and "|" in k:
        parts = k.split("|")
        out = [int(x) if x.lstrip("-").isdigit() else x for x in parts]
        return tuple(out)
    if isinstance(k, str) and k.lstrip("-").isdigit():
        return int(k)
    if isinstance(k, list):
        return tuple(k)
    return k

def _domain_of(domain_str: str):
    """Parse the leading domain word from a (possibly prose) domain string."""
    if not domain_str:
        return pyo.Reals
    head = domain_str.strip().split()[0].strip(",")
    return _DOMAINS.get(head, pyo.Reals)

def _index_sets(model, index_str: str):
    """Resolve a comma-separated index spec like 'i,j' to a list of model Set objs."""
    if not index_str:
        return []
    return [getattr(model, s.strip()) for s in index_str.split(",") if s.strip()]

def generic_build_model(components: dict, data: dict, extras: dict | None = None):
    """Build a CONSTRAINT-FREE scaffold model from the components block + data."""
    extras = extras or {}
    bounds = extras.get("bounds", {})
    fixings = extras.get("fixings", [])
    m = pyo.ConcreteModel()

    # --- sets: members come from data[name] (already tuple-ized by the loader) ---
    for s in components.get("sets", []):
        name = s["name"]
        members = data.get(name, s.get("members", []))
        dimen = 1
        if members and isinstance(members[0], (tuple, list)):
            dimen = len(members[0])
        setattr(m, name, pyo.Set(initialize=[tuple(x) if isinstance(x, list) else x for x in members],
                                 dimen=dimen, ordered=True))

    def _index_for(comp):
        """Return a concrete index (a named anonymous Set built from captured member
        keys) if the freeze stored 'index_members', else resolve the 'index' string
        to declared Set objects. The concrete path is robust to set unions, Any, and
        products that name-resolution can't handle."""
        mem = comp.get("index_members")
        if mem is not None:
            if len(mem) == 0:
                return None                              # scalar
            keys = [tuple(k) if isinstance(k, list) else k for k in mem]
            dimen = len(keys[0]) if isinstance(keys[0], tuple) else 1
            idxname = f"_{comp['name']}_idx"
            setattr(m, idxname, pyo.Set(initialize=keys, dimen=dimen, ordered=True))
            return [getattr(m, idxname)]
        sets = _index_sets(m, comp.get("index", ""))
        return sets or None

    # --- params: values from data[name], over their (concrete or named) index ---
    for p in components.get("params", []):
        name = p["name"]
        sets = _index_for(p)
        val = data.get(name, {})
        mutable = p.get("mutable", True)
        if sets:
            init = {_norm_key(k): vv for k, vv in val.items()} if isinstance(val, dict) else {}
            setattr(m, name, pyo.Param(*sets, initialize=init, mutable=mutable, default=0))
        else:                                            # scalar
            setattr(m, name, pyo.Param(initialize=(val if not isinstance(val, dict) else 0),
                                       mutable=mutable, default=0))

    # --- vars: domain (+ optional rectangular bounds), over their index ---
    for v in components.get("vars", []):
        name = v["name"]
        sets = _index_for(v)
        dom = _domain_of(v.get("domain", "Reals"))
        bnd = tuple(bounds[name]) if name in bounds else None
        if sets:
            setattr(m, name, pyo.Var(*sets, domain=dom, bounds=bnd))
        else:
            setattr(m, name, pyo.Var(domain=dom, bounds=bnd))

    # --- fixings: pin specific variable cells (diagonal, start node, etc.) ---
    for fx in fixings:
        var = getattr(m, fx["var"])
        idx = fx.get("index")
        if idx is None:                                  # scalar var
            var.fix(fx["value"]); continue
        key = tuple(idx) if isinstance(idx, list) and len(idx) > 1 else (idx[0] if isinstance(idx, list) else idx)
        var[key].fix(fx["value"])

    return m


def freeze_scaffold(model):
    """Extract (components, data, extras) from an ALREADY-BUILT model, so a corpus
    .py can be migrated to the generic builder with zero hand-authoring. Captures
    declared sets, param values (incl. COMPUTED params — they exist post-build),
    var domains/bounds, and fixed cells."""
    comps = {"sets": [], "params": [], "vars": [], "objective": {}}
    data = {}
    extras = {"bounds": {}, "fixings": []}

    # index sets that pyomo auto-creates for multi-dim components are SetProduct /
    # have '*' in name or are not directly declared; we keep only "real" declared sets.
    declared_sets = []
    for s in model.component_objects(pyo.Set, descend_into=False):
        nm = s.local_name
        if nm.endswith("_index") or nm.endswith("_domain") or "*" in nm:
            continue
        try:
            members = [list(x) if isinstance(x, tuple) else x for x in s]
        except Exception:
            continue
        declared_sets.append(nm)
        comps["sets"].append({"name": nm, "members": members, "doc": s.doc or ""})
        data[nm] = [tuple(x) if isinstance(x, list) else x for x in members]

    def _setname_of(index_set):
        # map a (possibly product) index set back to comma-joined declared-set names
        subs = list(getattr(index_set, "subsets", lambda **k: [index_set])(expand_all_set_operators=False)) \
            if hasattr(index_set, "subsets") else [index_set]
        names = [ss.local_name for ss in subs]
        return ",".join(names)

    for p in model.component_objects(pyo.Param, descend_into=False):
        nm = p.local_name
        idx = "" if p.index_set() is None or not p.is_indexed() else _setname_of(p.index_set())
        members = [list(k) if isinstance(k, tuple) else k for k in p] if p.is_indexed() else []
        comps["params"].append({"name": nm, "index": idx, "index_members": members,
                                "mutable": bool(getattr(p, "mutable", True)), "kind": "", "doc": p.doc or ""})
        if p.is_indexed():
            data[nm] = {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): pyo.value(p[k]) for k in p}
        else:
            data[nm] = pyo.value(p)

    for v in model.component_objects(pyo.Var, descend_into=False):
        nm = v.local_name
        idx = "" if not v.is_indexed() else _setname_of(v.index_set())
        members = [list(k) if isinstance(k, tuple) else k for k in v] if v.is_indexed() else []
        # domain name (use the first cell's domain)
        anycell = next(iter(v.values())) if v.is_indexed() else v
        domname = type(anycell.domain).__name__.replace("Set", "") if anycell.domain else "Reals"
        # normalize common ones
        for dn in _DOMAINS:
            if anycell.domain is _DOMAINS[dn]:
                domname = dn; break
        comps["vars"].append({"name": nm, "index": idx, "index_members": members,
                               "domain": domname, "doc": v.doc or ""})
        # fixings + bounds
        for k, cell in (v.items() if v.is_indexed() else [(None, v)]):
            if cell.fixed:
                extras["fixings"].append({"var": nm, "index": (list(k) if isinstance(k, tuple) else [k]) if k is not None else None,
                                          "value": pyo.value(cell)})
    return comps, data, extras
