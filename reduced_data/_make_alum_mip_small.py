#!/usr/bin/env python
"""Build a structurally-complete reduced instance for alum_mip Z3 grading.

The full instance has ~172 binary vars (ym over 22 mines + yr over 30x5) which
times out Z3. We keep a small subset of every index set, preserving:
  - cpospi(i,cm)  -> each kept mine maps to its kept bauxite (mbm/res/ccm/tba/aom/at/mbr)
  - fr/fi/fj over 2 groups (oecd, ldcs) with >=1 region IN and >=1 OUT each group
    so taa's `(f,rp) in fr and (f,r) not in fr` cross term is exercised
  - the a-coefficient chain bauxite->alumina->aluminum/electr (mbr, taa, aor)
  - prelec nonzero pairs (the electricity term in mbr for c in cl)
  - both an el-hicost (unbounded) and a bounded electricity type
This yields ~ (3 mines binary) + (3 r x 4 m = 12 yr) = 15 binaries -> Z3-fast.
"""
import json
from pathlib import Path

FULL = Path(__file__).resolve().parent.parent / ".." / "optichat_org" / "OptiChat" / "model_library" / "feas_model" / "alum_mip_data.json"
OUT = Path(__file__).resolve().parent / "alum_mip_small.json"

d = json.load(open(FULL))
S, SC, IP = d["sets"], d["scalar_params"], d["indexed_params"]

# ---- chosen subsets -------------------------------------------------------
keep = {
    "i":  ["usa", "w-europe", "guyana"],
    "r":  ["western-us", "eastern-us", "guyana"],
    "j":  ["wn-america", "c-amer+car"],
    "cm": ["highsi", "mono", "tri-201"],
    "ci": ["alumina"],
    "cf": ["aluminum"],
    "cl": ["electr"],
    "p":  ["ref-hs", "ref-m", "ref-t201", "smelting"],
    "m":  ["refineryss", "refinerym", "refineryt", "smelter"],
    "mr": ["refineryss", "refinerym", "refineryt"],
    "ms": ["smelter"],
    "seg": [1, 2],
    "l":  ["el-actual", "el-hicost"],
}
keep["c"] = keep["cm"] + keep["ci"] + keep["cf"] + keep["cl"]
KEEPF = ["oecd", "ldcs"]

sets_out = {k: v for k, v in keep.items()}

# membership sets (pipe-joined) ---------------------------------------------
def filt_pipe(key, cond):
    return [s for s in S[key] if cond(tuple(s.split("|")))]

ki, kcm, kr, kj = set(keep["i"]), set(keep["cm"]), set(keep["r"]), set(keep["j"])
sets_out["cpospi"] = filt_pipe("cpospi", lambda t: t[0] in ki and t[1] in kcm)
sets_out["fr"] = filt_pipe("fr", lambda t: t[0] in KEEPF and t[1] in kr)
sets_out["fi"] = filt_pipe("fi", lambda t: t[0] in KEEPF and t[1] in ki)
sets_out["fj"] = filt_pipe("fj", lambda t: t[0] in KEEPF and t[1] in kj)

# ---- params ---------------------------------------------------------------
# index signature per indexed param (which sets each dimension belongs to)
SIG = {
    "capm": ("i",), "d": ("j",), "nmaa2000": ("r",), "nmba2000": ("i",),
    "om": ("i",), "utr": ("m",), "zmbar": ("i",),
    "a": ("c", "p"), "b": ("m", "p"), "capr": ("r", "m"),
    "muf": ("r", "j"), "mui": ("r", "r"), "mur": ("i", "r"),
    "omegam": ("i", "seg"), "prelec": ("r", "l"), "sbm": ("i", "seg"),
    "ubar": ("r", "l"), "omegar": ("m", "seg", "r"), "sbr": ("m", "seg", "r"),
    "ors": ("r", "p"),
}
keepset = {k: set(str(x) for x in v) for k, v in keep.items()}

def keep_key(param, key):
    parts = key.split("|")
    for part, dim in zip(parts, SIG[param]):
        if part not in keepset[dim]:
            return False
    return True

ip_out = {}
for p, vals in IP.items():
    ip_out[p] = {k: v for k, v in vals.items() if keep_key(p, k)}

out = {"sets": sets_out, "scalar_params": SC, "indexed_params": ip_out}
json.dump(out, open(OUT, "w"), indent=1)
# report
print("wrote", OUT)
for k in ["cpospi", "fr", "fi", "fj"]:
    print(" ", k, sets_out[k])
for p in ip_out:
    print(" ", p, "n=", len(ip_out[p]))
