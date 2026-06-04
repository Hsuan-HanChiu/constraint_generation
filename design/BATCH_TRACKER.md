# feas_model -> training data: MODEL CHECKLIST — COMPLETE

**Total: 122 models | DONE: 110 | TODO: 0 gradable | dedup-skip: 8 | build-fail: 3 | excluded NLP: 1**

The full sweep is COMPLETE. Every gradable feas_model is now training data: **110 datasets, 850 records**, all selfcheck PASS (self-grade EQUIVALENT, relation-flip controls caught). The only models not turned into data are the 8 duplicates, the 3 build-failures, and the 1 genuine NLP — see the bottom sections.

Source: `optichat_org/OptiChat/model_library/feas_model/<name>.py` + `<name>_data.json`. Pipeline: inject+exec build -> freeze -> self-contained expected_pyomo -> Tier-1 descriptions -> `selfcheck` PASS (+ reduced instance if a MIP times out Z3). Harness auto-resolves by convention.

> **KEY FINDINGS**
> - The "nonlinear-flagged" tag is a regex artifact and almost always WRONG. Of 20 flagged models (5 LP + 15 MIP), only a handful had ANY genuinely nonlinear constraint, and each had just one. Always verify with `expr.body.polynomial_degree()`; param-only `**`/`/` are constant coefficients = LINEAR.
> - Genuinely nonlinear constraints actually excluded (Z3 can't grade): stockcc_mip `defobj` (var in denominator), cmo_mip `defpv`/`defpvres` (discount `(1+yield)^-t`), trnspwl_mip `defsqrt` (real sqrt), trip_mip `flow_conservation_const` (RHS is `np.random.normal` — non-reproducible). In every case the rest of the model's constraints were kept and graded.
> - STN_mip partial: only 2 of ~6 families gradable (rest depend on coefficient tables in module-level dicts never attached to model.*). icut_mip: only `obj_def` active (the whole cut family is Constraint.Skip-ped under the shipped data).
> - Binary fix-to-zero `x[i,i]==0` → emit `x[i,i] <= 0` so the relation-flip control is non-vacuous.
> - 10 models needed reduced instances (Z3 binary blow-up): binpacking, tsp1, csp, nurses, poutil, korpet (earlier) + tsp42_match, tsp42_tsp, pp_mip, mws_mip. Everything else graded on full data.
> - Recurring harness artifact: `_perturb` flips the FIRST relational operator, which can land on a Python branch guard (`if idx == 0`) instead of the constraint. Fix by writing the guard as `if idx > 0: ... else: ...` (or `< 1`, or truthy) so the constraint relop is first. Several agents applied this.
> - Do NOT have parallel subagents edit `MODEL_REGISTRY` — selfcheck uses explicit `--base-py`/`--data-json`; concurrent edits race.

## DONE (110) — grouped by build wave

Earlier (31): agreste_lp293, ajax_lp, asyncloop_lp, binpacking_mip(red), blend_lp54, blend_lp57, chance_lp, csp_mip(red), decomp_lp97, diet_lp, fawley_lp, fiveleap_mip, flowshop_mip, gussex1_lp, ibm1_lp, imsl_lp, jobt_lp, korpet_mip(red), lands_stoc_lp, markov_lp, mine_lp, nemhaus_mip, nurses_mip(red), orani_lp, poutil_mip(red), prodsp_lp, queens_mip, reaction_mip, robert_lp, tsp1_mip(red), whouse_lp.

LP sweep (26): aircraft_lp, airsp2_lp134, airsp2_lp87, airsp_lp121, airsp_lp165, ampl_lp, ampl_lp2, china_lp, dea_lp, demo1_lp, farm_lp86, iswnm_lp, lands_det_lp, macro_lp, paklive_lp, pdi_lp, sarf_lp, sparta_lp, spbenders3_lp, sroute_lp, uimp_profit_lp, danwolfe_lp, mesc_lp, pak_lp, paperco_lp, tforss_lp.

MIP-small (28): STN_mip*, allbases_mip, awktsp_mip_assign, bid_mip, chem_mip, cubesoln_mip, job_mip, landing_mip, latin_mip, magic_mip, maintenance_mip, multipleMB_mip, rdata_mip, ridesharing_mip, solnpool_mip, stockcc_easy_mip, stockcc_mip**, tba_mip, thai_mip, tsp3_subt1_mip, tsp3_subt2_mip, tsp42_match_mip(red), tsp42_tsp_mip(red), tsp4_assign_mip, tsp5_MTZ_mip, tvcsched_mip, vietman_vietmip_mip, vietman_viettag_mip.

MIP-large (10): coexx_mip, cta_mip, pg_mip***, pp_mip(red), process_mip, prodschx_1S1_mip, prodschx_1S2_mip, prodschx_2S1_mip, prodschx_2S2_mip, recovery_mip.

MIP nonlinear-flagged (15): andean_fixed, badmip_mip, cmo_mip****, cross_mip, icut_mip*****, mexsd_mip, mws_mip(red), prodsch_eb1, prodsch_eb2, prodsch_mip, trip_mip******, trnspwl_mip*******, trnspwlx_mip, westmip_mip, yemcem_mip.

(red) = uses a reduced instance in reduced_data/.
  *STN_mip partial — 2 of ~6 constraint families gradable.
  **stockcc_mip — excluded nonlinear `defobj` (var in denominator); 3 linear kept.
  ***pg_mip — source defines one constraint name twice; faithfully modeled the surviving definition.
  ****cmo_mip — excluded nonlinear `defpv`/`defpvres`; 19 linear kept.
  *****icut_mip — only `obj_def` active under shipped data (cut family all Skip-ped).
  ******trip_mip — excluded `flow_conservation_const` (random-normal RHS); 4 linear kept.
  *******trnspwl_mip — excluded the genuine sqrt `defsqrt`; 6 linear kept.

## DUP-SKIP (8) — covered by an equivalent model
- agreste_lp297 -> agreste_lp293 | awktsp_mip_cut -> awktsp_mip_assign | prodschx_1B_mip -> prodsch_eb1 | prodschx_2B_mip -> prodsch_eb2 | senstran_lp -> gussex1_lp | tgridmix_lp -> gussex1_lp | tsp4_tspcut_mip -> tsp42_tsp_mip | uimp_revenue_lp -> uimp_profit_lp

## BUILD-FAIL (3) — need a code/data fix before processing (only remaining work)
- RTN_mip: needs networkx module
- bchoil_mip: data KeyError on Param cap idx 2
- ccoil_mip: undefined fn _get_pair_val

## EXCLUDED (1)
- nemhaus_nlp — genuine NLP, not Z3-gradable.
