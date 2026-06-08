#!/usr/bin/env python
"""Build a small but structurally-complete copper_mip instance for Z3 grading.

Z3 runtime is dominated by binary count (ym over m x i, ys over m x j). The full
instance has ~15 i and ~13 j -> ~170 binaries and times out. We subset to a few
locations while keeping every structural feature that any constraint depends on:
  - >=3 i, >=2 j  (so degree/coupling errors surface)
  - both ore mining processes (pmm), both interplant commodities (cim=ore,blister)
    with >=2 i so xi[cim,i,ip] coupling is non-degenerate
  - >=2 scrap types (cil), all process families (pm, psm), all units (mm, ms)
  - the masks mapic/mapip/mapjc/mapjp kept consistent with the retained members
Indexed params are filtered to retained index members; varied original values are
preserved (no flattening) to avoid coincidental passes.
"""
import json
from pathlib import Path

FULL = Path(__file__).resolve().parents[1].parent / "optichat_org" / "OptiChat" / "model_library" / "feas_model" / "copper_mip_data.json"
OUT = Path(__file__).resolve().parent / "copper_mip_small.json"

raw = json.load(open(FULL))
sets = raw["sets"]
ip_ = raw["indexed_params"]

# Retain a small slice. i: 3 mine/smelter/refinery locations that are also j-plants
# where possible; j: 2 plant/market locations. Keep western-us because it has the
# fullest process/commodity coverage (scrap-s, smelting-s, refining-s).
KEEP_I = ["western-us", "canada", "peru"]
KEEP_J = ["canada", "mex+cam"]

# Sets that are subsets of i or j get filtered; commodity/process sets kept whole
# (they are small and every family should be representable).
new_sets = dict(sets)
new_sets["i"] = KEEP_I
new_sets["j"] = KEEP_J

ID = set(KEEP_I)
JD = set(KEEP_J)


def filt(d, keep_pos):
    """Keep entries whose tuple-key positions named in keep_pos all survive.
    keep_pos: dict {position_index: allowed_set}. Scalar keys treated as 1-tuple."""
    out = {}
    for k, v in d.items():
        parts = k.split("|")
        ok = True
        for pos, allowed in keep_pos.items():
            if parts[pos] not in allowed:
                ok = False
                break
        if ok:
            out[k] = v
    return out


new_ip = {}
# a, b: indexed by (commodity/unit, process) -> no i/j -> keep whole
new_ip["a"] = ip_["a"]
new_ip["b"] = ip_["b"]
# i-indexed (pos 0 = i)
for name in ["mapic", "mapip", "capm", "hhatm", "hbarm", "omegam", "num", "opm", "reserves"]:
    new_ip[name] = filt(ip_[name], {0: ID})
# j-indexed (pos 0 = j)
for name in ["mapjc", "mapjp", "demand", "caps", "hhats", "hbars", "omegas", "nus", "ops"]:
    new_ip[name] = filt(ip_[name], {0: JD})
# mur: (i, i, cim) -> pos 0 and 1 both i
new_ip["mur"] = filt(ip_["mur"], {0: ID, 1: ID})
# mufs: (j, j)
new_ip["mufs"] = filt(ip_["mufs"], {0: JD, 1: JD})
# mui: (i, j)
new_ip["mui"] = filt(ip_["mui"], {0: ID, 1: JD})
# tariffr: (i, j)
new_ip["tariffr"] = filt(ip_["tariffr"], {0: ID, 1: JD})
# tariffs: (j, j)
new_ip["tariffs"] = filt(ip_["tariffs"], {0: JD, 1: JD})
# bound-defining params consumed directly by the model:
# resc (i, pmh), scrapi (i, cil) -> pos 0 = i; scrapj_scrap keyed by j
new_ip["resc"] = filt(ip_["resc"], {0: ID})
new_ip["scrapi"] = filt(ip_["scrapi"], {0: ID})
new_ip["scrapj_scrap"] = {k: v for k, v in ip_["scrapj_scrap"].items() if k in JD}

out = {"sets": new_sets, "scalar_params": raw["scalar_params"], "indexed_params": new_ip}
json.dump(out, open(OUT, "w"), indent=2)
print(f"wrote {OUT}")
print("i =", new_sets["i"], "| j =", new_sets["j"])
