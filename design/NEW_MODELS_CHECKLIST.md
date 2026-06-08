# feas_model NEW BATCH (2026-06-05) — COMPLETE

feas_model grew 122 -> 199 (77 new models, +ridesharing_miqcp = 78 listed). **All processed.**

**Result: 71 new datasets built (all selfcheck PASS or faithful-with-caveat) + 6 dedup-skips + 1 skip (ridesharing_miqcp).**
Whole-set descriptions use the new ordinal-narrative rule. Reduced instances built where Z3 timed out.

Dataset total: **110 -> 181 | records 1347 | 32 reduced instances.**

## Dedup-skips (6) — identical constraint set to an existing model
- spbenders1_lp, spbenders2_lp, spbenders4_lp, spbenders5_lp -> all identical to spbenders3_lp (same 5 constraints, names, algebra, indices)
- thaix_mip -> identical constraint set to thai_mip (Thai Navy problem; only objective/symbol naming differs)
- dicegrid_mip -> identical to dice_mip (grid-compute wrapper around the same design MIP)

## Skipped (1)
- ridesharing_miqcp -> the source file already built as ridesharing_mip; MIQCP duplicate.

## Faithful-with-caveat (2) — kept; records self-grade EQUIVALENT, but one control is vacuous
- nonsharp_mip — Benders master; `laerr` is vacuous `0<=0` (all multipliers 0 in shipped data) and `intcut` is a symmetric ±1 cut pair, so their relation-flip controls cannot discriminate. Real perturbations ARE caught; dataset is base-faithful.
- cvrp_mip — `eq_node_balance` per-node flow equality is globally redundant (total in-degree ≡ out-degree identically over X), so flipping its `==` stays equivalent. Structural, data-independent. All 6 constraints self-grade EQUIVALENT; faithful.
(Both are the documented "symmetric/degenerate control" case — not sizing problems and not fixable via the `<=0` trick.)

## Reduced instances built this batch (Z3 would time out on full)
alum, cbenders, copper, dicex, lop, marilyn(opt), railcirc, rcpsp(4042 binaries), relief, swath, coex, lrs, sddp(61k cons), rotdk, boxpacking, maxcut, openpit, clad, bchfcnet, fertd. (indus89: graded on full data — pure LP, ~5.7s.)

## Notable new families gained
cutting stock (cutstock, bchstock), CVRP, RCPSP, generalized assignment (gapmin), linear ordering (lop), max-cut, knapsack, knights, open-pit mining, swath, tsp2, stochastic Benders, fixed-charge network (bchfcnet, trnsindic), and an economy/energy cluster (indus, indus89, egypt, turkpow, mexss, mexls, shale, copper, alum, nebrazil, sddp hydro).

## Genuinely nonlinear constraints excluded (kept the linear rest)
- bidsos_mip: `sos` (SOS2 constraint component — not Z3-gradable). 3 linear kept.
(qp5 turned out LP-solved with all-linear constraints; maxcut/solmpool were linearized, all-linear.)
