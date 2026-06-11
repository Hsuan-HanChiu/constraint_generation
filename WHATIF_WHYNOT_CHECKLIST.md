# What-if / Why-not query tracking (2026-06-10)

> **STATUS NOTE (2026-06-10):** what-if/why-not record creation is largely DONE — 521 graded records across 138 models in `datasets/<model>_optichat_query.jsonl`. Hsuan-Han hand-edited ~175 testing_library/feas_test files, so the dataset reflects those edits, BUT it was assembled incrementally while editing was ongoing, so a small number of records may be from superseded query versions (dataset 521 vs current testing_library clean-complex 516). **Recommended once query editing is fully finished: one clean rebuild** (`build_optichat_queries.py` -> grade reduced-then-full -> re-add the 2 converted allbases heuristics) so the dataset matches the final testing_library exactly. Finalized-by-hand models so far: allbases_mip, bidpwl_mip.


Source: OptiChat `testing_library/feas_test/<model>.txt`. Builder: `build_optichat_queries.py` (+ `partition_grade.py`).

**BUILT INTO DATASET: 406 records across 125 models** in `datasets/<model>_optichat_query.jsonl` (same 5-field schema, OptiChat `Q` -> `query`, real `Constraint` -> `expected_pyomo`; all self-grade EQUIVALENT via Z3). 60 of these have a VACUOUS relation-flip control (faithful but non-discriminating, flagged like the existing nonsharp/cvrp cases).

This file tracks everything NOT in the dataset, with full source info.


**Deferred counts:** simple variable bounds = 787 | tangled heuristics (manual extraction) = 442 | quarantined grading failures = 33 | deferred-no-dataset = 26


---


## 1. Simple variable bounds (deferred — 'make harder later')

Single variable term vs a constant, no sum/coupling/index-rule. Too easy as-is.


### RTN_mip  (5)  — `testing_library/feas_test/RTN_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The reactor is booked at time 5, so Rx1 can't fire then. Let's see what happens to the plan if we forbid triggering Rx1 at time 5. | `model.no_rx1_t5 = Constraint(expr=model.N['Rx1', 5] <= 0)` | 3.0 |
| WHAT-IF/new_constraint | There's a proposal to require a larger Rx1 run — at least 55 units in its batch at time 5. What's the resulting number of task triggerings? | `model.big_rx1 = Constraint(expr=model.E['Rx1', 5] >= 55)` | 3.0 |
| WHY-NOT/constraint_rule | Is firing Rx2 at time 4 really necessary? Couldn't we just skip the Rx2 trigger at time 4 and schedule around it? What's keeping the model on it? | `model.no_rx2_t4 = Constraint(expr=model.N['Rx2', 4] <= 0)` | 3.0 |
| WHY-NOT/constraint_rule | Why is Rx3 pinned to time 3? Is there a reason we couldn't just keep Rx3 off time 3 entirely? What's the model seeing that I'm not? | `model.no_rx3_t3 = Constraint(expr=model.N['Rx3', 3] <= 0)` | 3.0 |
| WHY-NOT/constraint_rule | The Rx2 run at time 4 looks oversized. Couldn't we hold that batch to at most 40 units? What's the tradeoff that pushes it higher? | `model.cap_rx2_batch = Constraint(expr=model.E['Rx2', 4] <= 40)` | 3.0 |

### STN_mip  (6)  — `testing_library/feas_test/STN_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose a downstream buyer can only take 80 units of Product_1 this horizon, so there's no point ending with more. What does the optimizer return for net value if we cap final Product_1 at 80? | `model.p1_cap = Constraint(expr=model.S['Product_1', 8] <= 80)` | 2350.2500000000005 |
| WHAT-IF/new_constraint | Finance wants a tight production-cost budget — hold total production cost to no more than 12. Run it and tell me the net value. | `model.cost_budget = Constraint(expr=model.Cost <= 12)` | 1788.0000942451106 |
| WHAT-IF/new_constraint | We're stress-testing a softer revenue target — what happens to the plan if we hold end-of-horizon product revenue to at most 2600? | `model.value_cap = Constraint(expr=model.Value <= 2600)` | 2584.0 |
| WHY-NOT/constraint_rule | We're ending with a big pile of Product_1. Shouldn't we be able to hold final Product_1 to 70 and still do well? What's keeping the model from trimming it? | `model.p1_trim = Constraint(expr=model.S['Product_1', 8] <= 70)` | 2338.0000327704483 |
| WHY-NOT/constraint_rule | Production cost looks low — maybe suspiciously so. Is there a reason we couldn't run a richer schedule that spends at least 20 on production? What's the tradeoff the model is making? | `model.cost_floor = Constraint(expr=model.Cost >= 20)` | 2740.0 |
| WHY-NOT/constraint_rule | Product_2 ends up barely stocked. Wouldn't it be fine to deliberately keep final Product_2 under 15 and lean into Product_1 instead? Walk me through what that costs. | `model.p2_low = Constraint(expr=model.S['Product_2', 8] <= 15)` | 2654.0 |

### absmip_mip  (8)  — `testing_library/feas_test/absmip_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at a scenario where the position can't be allowed below -3 (a hard stop-loss on x). What downside does the optimizer report under that floor? | `model.stop_loss = Constraint(expr=model.x >= -3)` | -3.0 |
| WHAT-IF/new_constraint | There's a proposal to force the position onto its positive branch — pin the indicator b to 1 so only the non-negative side is in play. What does y come back as? | `model.force_pos = Constraint(expr=model.b == 1)` | 0.0 |
| WHAT-IF/new_constraint | Let's try capping the negative part xn at 3 — say the most downside we'll book in one period is 3. What downside value results? | `model.cap_xn = Constraint(expr=model.xn <= 3)` | -3.0 |
| WHAT-IF/new_constraint | Suppose policy puts a hard floor on the recognized downside at -2 (we won't carry a y below that). What does the model return? | `model.floor_y = Constraint(expr=model.y >= -2)` | -2.0 |
| WHY-NOT/constraint_rule | The plan drives the position all the way to -5. Shouldn't we be holding x at no worse than -2 rather than letting it bottom out? What's the model seeing that makes the floor worth chasing? | `model.hold_x2 = Constraint(expr=model.x >= -2)` | -2.0 |
| WHY-NOT/constraint_rule | Why is the negative part allowed to run out to 5? Couldn't we just cap xn at 2 and avoid the deep downside? What's the tradeoff there? | `model.why_xn2 = Constraint(expr=model.xn <= 2)` | -2.0 |
| WHY-NOT/constraint_rule | Is there a reason the model doesn't keep the negative part under 4? Wouldn't holding xn at 4 or less be the prudent move? What's pulling it the other way? | `model.why_xn4 = Constraint(expr=model.xn <= 4)` | -4.0 |
| WHY-NOT/constraint_rule | The downside y bottoms out at -5. Couldn't we just insist y never drop below -1? What's keeping the optimizer from staying that shallow? | `model.why_y1 = Constraint(expr=model.y >= -1)` | -1.0 |

### agreste_lp293  (2)  — `testing_library/feas_test/agreste_lp293.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to lighten the payroll by holding the permanent crew to at most one and a half full-time workers. If we cap permanent labor at 1.5 workers, what does the optimizer return for farm income and the plan? | `model.perm_cap = Constraint(expr=model.plab <= 1.5)` | 15930.89 |
| WHAT-IF/new_constraint | We're considering a food-security floor for the household: keep at least 1.5 tons of manioc coming out of the ground each season so the family pantry is covered before anything gets sold. Plug that in and tell me where farm income lands. | `model.manioc_floor = Constraint(expr=model.xprod['manioc'] >= 1.5)` | 16195.431 |

### agreste_lp297  (3)  — `testing_library/feas_test/agreste_lp297.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're weighing whether to keep the permanent hand on at full time. There's a proposal to hold permanent labor to a single worker-equivalent and lean on family and seasonal hands for the rest. If we cap permanent labor at one worker, what does the optimizer return for farm income? | `model.plab_cap = Constraint(expr=model.plab <= 1.0)` | 16732.061 |
| WHAT-IF/new_constraint | There's a proposal to scale up the herd for a milk-cooperative contract that needs a minimum throughput. If we require at least 15 head of livestock in the plan, where does farm income land? | `model.min_livestock = Constraint(expr=model.xlive >= 15)` | 17331.014 |
| WHY-NOT/constraint_rule | The plan leans awfully hard on corn — we're selling more than three tons of it and riding the corn price for a big slice of income. That feels exposed if the corn market turns. Couldn't we hold corn sales to no more than 1.5 tons and let other crops carry their weight? What's keeping the model from spreading the risk like that? | `model.corn_sales_cap = Constraint(expr=model.sales['corn'] <= 1.5)` | 17381.799 |

### aircraft_lp  (4)  — `testing_library/feas_test/aircraft_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Marketing is floating a peak-demand promise on route-4 — carry at least 120 passengers when it hits its top state. What does the optimizer return for cost if we hold to that? | `model.route4_peak = Constraint(expr=model.y['route-4', 5] >= 120)` | 5551.756528129593 |
| WHY-NOT/constraint_rule | Route-3 sits empty of our flexible type-a jets while it bleeds bumped passengers. Shouldn't we be putting at least a couple of type-a aircraft on route-3? What's keeping the model from making that move? | `model.force_a_route3 = Constraint(expr=model.x['a', 'route-3'] >= 2)` | 5555.928482972136 |
| WHY-NOT/constraint_rule | Type-d aircraft are stacking up on route-1 and that looks heavy to me. Wouldn't it be smarter to hold type-d on route-1 to two at most? What's the model seeing that I'm not? | `model.cap_d_route1 = Constraint(expr=model.x['d', 'route-1'] <= 2)` | 5549.561103292992 |
| WHY-NOT/constraint_rule | We've got cheap type-c capacity sitting idle while route-2 still bumps people. Is there a reason the plan doesn't put at least a couple of type-c aircraft on route-2? What's the tradeoff I'm missing? | `model.force_c_route2 = Constraint(expr=model.x['c', 'route-2'] >= 2)` | 5539.815351659005 |

### airsp2_lp134  (1)  — `testing_library/feas_test/airsp2_lp134.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Route-1 is soaking up nearly all the denied boardings in this plan. Couldn't we just hold route-1's bumping to 20 passengers and let the fleet carry the rest? Shouldn't that still come in at a workable cost? What's stopping the model from doing that on its own? | `model.r1_bump_cap = Constraint(expr=model.bumped['route-1'] <= 20)` | 1734.618582 |

### airsp2_lp87  (1)  — `testing_library/feas_test/airsp2_lp87.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | We're stranding over a hundred passengers on route-5 every cycle. Shouldn't the plan hold route-5 bumping under 60 — surely shaving that overflow is worth a small bump in flying cost? What's keeping the model from doing that on its own? | `model.r5_bump_cap = Constraint(expr=model.bumped['route-5'] <= 60)` | 1014.041 |

### airsp_lp121  (1)  — `testing_library/feas_test/airsp_lp121.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Operations is evaluating a cap on the long-haul run — they want route-5's allocated seat capacity held to no more than 560 so a backup frame is always free. If we hold z[route-5] at 560, what does the optimizer return for expected cost? | `model.z5_cap = Constraint(expr=model.z['route-5'] <= 560)` | 1571.7381138975966 |

### airsp_lp165  (1)  — `testing_library/feas_test/airsp_lp165.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to commit more seats to the long-haul: hold route-5's allocated capacity at no less than 200. We're evaluating it before the next schedule cut — what does the optimizer return for expected cost if route-5 capacity is floored at 200? | `model.r5_cap_floor = Constraint(expr=model.z['route-5'] >= 200)` | 2137.318 |

### allbases_mip  (6)  — `testing_library/feas_test/allbases_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at opening up the Seattle-to-New-York lane and putting at least 50 cases on it for delivery redundancy. What does the optimizer come back with for total cost? | `model.seNY_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 50)` | 153.675 |
| WHAT-IF/new_constraint | There's a proposal on the table to have Seattle pick up a chunk of the Topeka orders — at least 100 cases on the Seattle-Topeka lane. Plug that in and tell me the resulting shipping cost. | `model.setop_floor = Constraint(expr=model.x['seattle', 'topeka'] >= 100)` | 165.6 |
| WHAT-IF/new_constraint | Procurement wants to dual-source Chicago so we're not leaning on one plant — route at least 100 cases into Chicago from San Diego. Run it and walk me through the new total cost. | `model.sdchi_floor = Constraint(expr=model.x['san-diego', 'chicago'] >= 100)` | 156.15 |
| WHY-NOT/constraint_rule | Topeka gets supplied entirely from San Diego way down south, while Seattle sits on idle capacity. Shouldn't Seattle cover at least 50 cases of Topeka instead of railing it all the long way? What's the plan seeing that keeps Seattle off that lane? | `model.want_setop = Constraint(expr=model.x['seattle', 'topeka'] >= 50)` | 155.475 |
| WHY-NOT/constraint_rule | All of Chicago is hauled out of Seattle, even though San Diego is reasonably placed for the Midwest too. Wouldn't it be more balanced to have San Diego carry at least 50 of those Chicago cases? What's the tradeoff pulling the optimizer the other way? | `model.want_sdchi = Constraint(expr=model.x['san-diego', 'chicago'] >= 50)` | 156.15 |
| WHY-NOT/constraint_rule | San Diego ends up covering the whole New York market while Seattle, our flagship plant, runs below capacity. Shouldn't Seattle take a bigger bite of our largest market — say at least 100 cases into New York? What's keeping it from making that move? | `model.want_seNY = Constraint(expr=model.x['seattle', 'new-york'] >= 100)` | 156.15 |

### alphamet_mip  (4)  — `testing_library/feas_test/alphamet_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We want to double-check the solver isn't quietly leaning on M being a small digit. Suppose we tell it M's digit has to be at least 7 — does the puzzle still close, and at what carry total? | `model.m_high = Constraint(expr=model.y['m'] >= 7)` | 9.0 |
| WHAT-IF/new_constraint | We'd like to see what happens if the letter T is required to land on an odd-ish high digit — say its value has to be 7 or more. Does the puzzle still have an answer, and where does the objective land? | `model.t_high = Constraint(expr=model.y['t'] >= 7)` | 9.0 |
| WHY-NOT/constraint_rule | It bugs me that the letter I gets shoved all the way down to zero. Couldn't the solver just keep I's digit at zero and prove that's really the only place it fits? Force I no higher than zero and show me — what's the model seeing there? | `model.why_i = Constraint(expr=model.y['i'] <= 0)` | 9.0 |
| WHY-NOT/constraint_rule | V is a leading letter, so I'd expect it to grab a hefty digit, yet it seems to come out tiny. Shouldn't we be able to hold V's digit down to at most one without breaking anything? What's the optimizer's logic there? | `model.why_v = Constraint(expr=model.y['v'] <= 1)` | 9.0 |

### alum_mip  (7)  — `testing_library/feas_test/alum_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at de-risking our reliance on the West Europe smelters self-supplying their home market. Suppose we hold that local West-Europe-to-West-Europe flow to at most 3500 tonnes and let the rest of the network make up the balance — what total cost does the optimizer return? | `model.cap_we = Constraint(expr=model.xf['w-europe', 'w-europe'] <= 3500)` | 49568.59054524622 |
| WHAT-IF/new_constraint | There's interest in keeping the Western US plants busier serving their own backyard. If we require the Western-US-to-Western-North-America lane to carry at least 2200 tonnes, what does the freight-and-production bill come to? | `model.floor_wus = Constraint(expr=model.xf['western-us', 'wn-america'] >= 2200)` | 49628.546637101 |
| WHAT-IF/new_constraint | Brazil is currently leaning heavily on the Eastern South America market. We want to see the case where Brazil's deliveries into that market are held to no more than 1000 tonnes — what's the resulting total cost? | `model.cap_br_esa = Constraint(expr=model.xf['brazil', 'es-america'] <= 1000)` | 49567.270335061585 |
| WHY-NOT/constraint_rule | The Western US plants are right across the Atlantic from West Europe, yet the plan ships them nothing into that market — it's all sourced elsewhere. Shouldn't Western US be carrying at least 500 tonnes into West Europe? What's the model seeing that makes that a worse plan? | `model.cr_wus_we = Constraint(expr=model.xf['western-us', 'w-europe'] >= 500)` | 49619.120238868905 |
| WHY-NOT/constraint_rule | Japan has its own smelters yet the plan never has them serve the Eastern North America market at all. Couldn't Japan pitch in even 200 tonnes there to spread the sourcing? What's steering the optimizer away from that? | `model.cr_jp_ena = Constraint(expr=model.xf['japan', 'en-america'] >= 200)` | 49585.636666717415 |
| WHY-NOT/constraint_rule | I'd have expected the Eastern US plants to back-fill some of West Europe's demand for resilience, but the plan leaves that lane completely shut. Couldn't we route at least 400 tonnes Eastern-US-to-West-Europe? What's the tradeoff the model is making by keeping it dark? | `model.cr_eus_we = Constraint(expr=model.xf['eastern-us', 'w-europe'] >= 400)` | 49569.52236524416 |
| WHY-NOT/constraint_rule | The plan leaves the USA bauxite mine without any new fixed expansion at all, even though we own the deposit. Shouldn't we be committing to at least one expansion segment there? What's keeping the optimizer from breaking ground on the USA mine? | `model.cr_open_usa = Constraint(expr=model.ym['usa'] >= 1)` | 49569.19050786989 |

### ampl_lp2  (2)  — `testing_library/feas_test/ampl_lp2.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a smoothing idea for the line crew — they don't want any single period slammed with a giant nuts batch. Suppose we hold nuts production in period 4 to no more than 30 units. What does the optimizer return for profit? | `model.nuts4_cap = Constraint(expr=model.x['nuts', 4] <= 30)` | 93.93539620253162 |
| WHAT-IF/new_constraint | Finance wants a safety buffer on raw stock — leave at least 2 units of iron on hand at the end of the horizon rather than running it to zero. We're evaluating that buffer; how does it move the profit? | `model.iron_reserve = Constraint(expr=model.s['iron', 5] >= 2)` | 94.39620253164554 |

### andean_fixed  (7)  — `testing_library/feas_test/andean_fixed.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating pulling Barrancabermeja's ammonium nitrate off the export market in the first period — sell none of it abroad. What does that do to the plan's bottom line? | `model.cap_e1 = Constraint(expr=model.e['amm-nitr', 'barrancabr', '1981-83'] <= 0)` | -20300.870823601857 |
| WHAT-IF/new_constraint | Suppose Moron stops exporting ammonium sulfate in the first period and holds it for the home market. Run it and tell me where the discounted cost lands. | `model.cap_e2 = Constraint(expr=model.e['amm-sulf', 'moron', '1981-83'] <= 0)` | -20335.43734519591 |
| WHAT-IF/new_constraint | There's a proposal to keep Cartagena's urea entirely domestic in the first period — zero exports. What's the resulting cost figure? | `model.cap_e3 = Constraint(expr=model.e['urea', 'cartagena', '1981-83'] <= 0)` | -19965.661350726365 |
| WHAT-IF/new_constraint | We're looking at Cuzco holding back its ammonium nitrate exports in the first period. Plug that in and let me see the discounted total cost. | `model.cap_e4 = Constraint(expr=model.e['amm-nitr', 'cuzco', '1981-83'] <= 0)` | -20319.837368908178 |
| WHY-NOT/constraint_rule | Barranquilla is shipping a lot of ammonium sulfate abroad. Wouldn't it be smarter to keep that output for our own farmers and stop exporting it? What's the plan getting out of selling it overseas instead? | `model.want_cap_baranq = Constraint(expr=model.e['amm-sulf', 'baranquill', '1981-83'] <= 0)` | -20360.41055450818 |
| WHY-NOT/constraint_rule | Callao keeps sending ammonium nitrate out of the region. Shouldn't we just stop those exports and serve domestic demand first? What's the optimizer seeing that keeps that export flowing? | `model.want_cap_callao = Constraint(expr=model.e['amm-nitr', 'callao-f', '1981-83'] <= 0)` | -20305.395643845146 |
| WHY-NOT/constraint_rule | Callao's ammonium sulfate barely moves at home yet some still goes to export. Couldn't we just halt that small export stream? What's the trade-off the model is weighing by keeping it on? | `model.want_cap_callao_sulf = Constraint(expr=model.e['amm-sulf', 'callao-f', '1981-83'] <= 0)` | -20407.62214972636 |

### asyncincbi_mip  (5)  — `testing_library/feas_test/asyncincbi_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're checking how sensitive the bottleneck is to one switch — suppose b34 has to be turned on. What does xmax come back as? | `model.on_b34 = Constraint(expr=model.b['b34'] == 1)` | 13.0 |
| WHAT-IF/new_constraint | There's a proposal to require b35 in the configuration. What bottleneck value results? | `model.on_b35 = Constraint(expr=model.b['b35'] == 1)` | 15.0 |
| WHAT-IF/new_constraint | Let's try a configuration that commits b40. Where does xmax land? | `model.on_b40 = Constraint(expr=model.b['b40'] == 1)` | 14.0 |
| WHAT-IF/new_constraint | Suppose we pin b53 into the solution. What's the resulting bottleneck? | `model.on_b53 = Constraint(expr=model.b['b53'] == 1)` | 12.0 |
| WHY-NOT/constraint_rule | The plan leaves b58 switched off. Shouldn't that one be on given how the rows couple? What's the optimizer seeing that keeps it dark? | `model.why_b58 = Constraint(expr=model.b['b58'] == 1)` | 12.0 |

### asyncloop_lp  (1)  — `testing_library/feas_test/asyncloop_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Our New York buyer wants supply continuity — they're asking us to commit at least 120 cases a month coming directly off the Seattle line so a San Diego hiccup can't strand the whole order. We're evaluating that commitment. Where does the cost land if we hold Seattle-to-NY at 120 or more? | `model.seattle_ny_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 120)` | 154.305 |

### awktsp_mip_assign  (3)  — `testing_library/feas_test/awktsp_mip_assign.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A dispatcher wants city 1 hooked straight out to city 6 no matter the cost. Force that link in and tell me what the assignment total becomes. | `model.link_16 = Constraint(expr=model.x['i1', 'i6'] == 1)` | 106.0 |
| WHAT-IF/new_constraint | There's a proposal to route city 2 straight out to city 5. Pin that link in and tell me what the assignment ends up costing. | `model.link_25 = Constraint(expr=model.x['i2', 'i5'] == 1)` | 72.0 |
| WHAT-IF/new_constraint | The depot at city 6 is being told to feed city 1 directly on its outgoing link. Lock that in and let me see the resulting assignment total. | `model.link_61 = Constraint(expr=model.x['i6', 'i1'] == 1)` | 110.0 |

### awktsp_mip_cut  (3)  — `testing_library/feas_test/awktsp_mip_cut.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A dispatcher wants city 1 hooked straight out to city 6 no matter the cost. Force that link in and tell me what the assignment total becomes. | `model.link_16 = Constraint(expr=model.x['i1', 'i6'] == 1)` | 106.0 |
| WHAT-IF/new_constraint | There's a proposal to route city 2 straight out to city 5. Pin that link in and tell me what the assignment ends up costing. | `model.link_25 = Constraint(expr=model.x['i2', 'i5'] == 1)` | 72.0 |
| WHAT-IF/new_constraint | The depot at city 6 is being told to feed city 1 directly on its outgoing link. Lock that in and let me see the resulting assignment total. | `model.link_61 = Constraint(expr=model.x['i6', 'i1'] == 1)` | 110.0 |

### bchfcnet_mip  (7)  — `testing_library/feas_test/bchfcnet_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're sizing up what happens if the lead trunk out of the depot gets throttled — say a permit limits the n1-to-n23 corridor to 3 units a cycle and the rest of the deliveries have to find another way down. What total cost does the optimizer return for that? | `model.cap_n1n23 = Constraint(expr=model.x['n1', 'n23', 'a1'] <= 3)` | 1055.0 |
| WHAT-IF/new_constraint | Curious about a bottleneck mid-network: if the n34-to-n37 link can only push 3 units through at most, where does the total build-and-haul cost land? | `model.cap_n34n37 = Constraint(expr=model.x['n34', 'n37', 'a1'] <= 3)` | 1046.0 |
| WHAT-IF/new_constraint | Suppose the n13-to-n11 arc is off the table this cycle — easement dispute, can't use it. If we forbid the network from opening that arc at all, what does the plan cost? | `model.no_n13n11 = Constraint(expr=model.y['n13', 'n11', 'a1'] == 0)` | 1052.0 |
| WHY-NOT/constraint_rule | n2 is one of our delivery points and the depot ships it the long way round through the tree. Wouldn't it be cleaner to just open a direct n1-to-n2 line and feed it straight from the source? What's the model seeing that makes the direct arc a bad call? | `model.open_n1n2 = Constraint(expr=model.y['n1', 'n2', 'a1'] >= 1)` | 1107.0 |
| WHY-NOT/constraint_rule | n47 sits at the tail end of a long chain in the plan. Couldn't the depot just truck at least one unit straight to it on the n1-to-n47 lane instead of relaying it through half the network? What's the tradeoff the optimizer is making by not doing that? | `model.direct_n1n47 = Constraint(expr=model.x['n1', 'n47', 'a1'] >= 1)` | 1111.0 |
| WHY-NOT/constraint_rule | The n1-to-n4 arc is sitting dark in the solution. I'd have expected a direct hop to n4 to earn its keep — why won't the model open that arc? Shouldn't we at least light it up? | `model.open_n1n4 = Constraint(expr=model.y['n1', 'n4', 'a1'] >= 1)` | 1104.0 |
| WHY-NOT/constraint_rule | For n17 the plan routes everything through intermediate hops rather than serving it from the depot. Couldn't we just push a unit directly from n1 to n17 and cut out the relay? What's pulling the optimizer away from the direct route? | `model.direct_n1n17 = Constraint(expr=model.x['n1', 'n17', 'a1'] >= 1)` | 1067.0 |

### bchmknap_mip  (4)  — `testing_library/feas_test/bchmknap_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Column c5 covers a strategic line we'd like represented regardless. If we require c5 to be included in the slate, what's the resulting total value the model lands on? | `model.want_c5 = Constraint(expr=model.x['c5'] >= 1)` | 3700.0 |
| WHY-NOT/constraint_rule | Column c4 is by far the most valuable single item on the board at 2400, yet the plan leaves it out entirely. Shouldn't we just take the biggest prize and force c4 into the selection? What is the model seeing that makes skipping it the better call? | `model.force_c4 = Constraint(expr=model.x['c4'] >= 1)` | 2400.0 |
| WHY-NOT/constraint_rule | c1 is a cheap, low-footprint column — it barely uses any resources. Couldn't we just tuck it into the slate alongside the rest? Why does the optimizer keep leaving c1 on the bench? | `model.force_c1 = Constraint(expr=model.x['c1'] >= 1)` | 3300.0 |
| WHY-NOT/constraint_rule | I'm skeptical c3 is really earning its spot — it's eating a lot of the tight rows. If we just dropped c3 from the selection, surely the freed-up capacity buys back more elsewhere? What's the model's reasoning for keeping it in? | `model.drop_c3 = Constraint(expr=model.x['c3'] <= 0)` | 3100.0 |

### bchoil_mip  (9)  — `testing_library/feas_test/bchoil_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Survey crews flagged a right-of-way issue on the 14-to-15 corridor, so we may not be able to lay pipe there. Take that segment off the table and tell me what the network ends up costing. | `model.block_14_15 = Constraint(expr=model.b['14', '15'] == 0)` | 1469.0 |
| WHAT-IF/new_constraint | We're weighing a scenario where the 26-to-23 link can't be built. Drop it from the options and let me see the resulting construction cost. | `model.block_26_23 = Constraint(expr=model.b['26', '23'] == 0)` | 1436.0 |
| WHAT-IF/new_constraint | There's a proposal to commit to a pipe on the 12-to-13 corridor as part of the layout. Force that segment in and tell me what it does to total cost. | `model.use_12_13 = Constraint(expr=model.b['12', '13'] == 1)` | 1449.5 |
| WHAT-IF/new_constraint | Let's try locking in a pipe from node 5 to node 6 and see how the rest of the network reorganizes around it. | `model.use_5_6 = Constraint(expr=model.b['5', '6'] == 1)` | 1468.0 |
| WHY-NOT/constraint_rule | The 24-to-17 segment looks like one of the pricier runs in the plan. Shouldn't we route around it instead of committing to it? What's the model seeing that makes it worth building? | `model.avoid_24_17 = Constraint(expr=model.b['24', '17'] == 0)` | 1654.0 |
| WHY-NOT/constraint_rule | Everything seems to funnel into the port through the single 15-to-33 pipe. Shouldn't we avoid leaning so hard on that one segment? What's the trade-off if we don't build it? | `model.avoid_15_33 = Constraint(expr=model.b['15', '33'] == 0)` | 1605.75 |
| WHY-NOT/constraint_rule | Node 12 sits right next to node 11 — wouldn't it be obvious to run a short pipe straight from 12 to 11? Why does the plan skip that connection? | `model.want_12_11 = Constraint(expr=model.b['12', '11'] == 1)` | 1444.5 |
| WHY-NOT/constraint_rule | The 4-to-6 segment is in the build — do we actually need it? Couldn't we drop it and still get the oil to the port? What's pulling the plan toward keeping it? | `model.avoid_4_6 = Constraint(expr=model.b['4', '6'] == 0)` | 1433.0 |
| WHY-NOT/constraint_rule | Why isn't there a direct pipe from node 9 over to node 12? On the map it looks like a natural link — what's keeping the design from building it? | `model.want_9_12 = Constraint(expr=model.b['9', '12'] == 1)` | 1497.25 |

### bchstock_mip  (7)  — `testing_library/feas_test/bchstock_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at spreading wear across the cutting line rather than leaning so hard on the p6 setup. Say we hold pattern p6 to no more than 150 rolls and let the plan make up the difference elsewhere — what does the total roll count come out to? | `model.cap_p6 = Constraint(expr=model.xp['p6'] <= 150)` | 461.0 |
| WHAT-IF/new_constraint | The crew can only reset the slitter to the p5 layout so many times a shift. If we cap pattern p5 at 100 rolls, what roll total does the optimizer return? | `model.cap_p5 = Constraint(expr=model.xp['p5'] <= 100)` | 455.0 |
| WHAT-IF/new_constraint | Suppose a supply contract obliges us to run at least 80 rolls on the simple p1 pattern this cycle regardless. With that floor in place, where does the total roll count settle? | `model.floor_p1 = Constraint(expr=model.xp['p1'] >= 80)` | 484.0 |
| WHY-NOT/constraint_rule | We've got a perfectly good dedicated pattern p3 for the 31-wide product that slices three to a roll, yet the plan barely touches it and leans on the mixed cuts instead. Shouldn't we be running p3 properly — say at least 50 rolls of it? What's the model seeing that makes that worse? | `model.use_p3 = Constraint(expr=model.xp['p3'] >= 50)` | 466.0 |
| WHY-NOT/constraint_rule | Pattern p4 cuts seven of the 14-wide strip out of a single roll — that's the most efficient way to make that product, and yet the plan never uses it. Couldn't we run it at least 30 rolls? What's pulling the optimizer away from that? | `model.use_p4 = Constraint(expr=model.xp['p4'] >= 30)` | 483.0 |
| WHY-NOT/constraint_rule | Almost half our rolls go through that one p6 setup, which feels like putting all our eggs in one basket. Couldn't we hold p6 down to 100 rolls and balance the work better? What's the tradeoff the model is making by hammering it that hard? | `model.cap_p6_tight = Constraint(expr=model.xp['p6'] <= 100)` | 469.0 |
| WHY-NOT/constraint_rule | Even a gentler limit on p6 ought to be harmless — say no more than 180 rolls on it. Wouldn't that barely move the total? What's the model giving up to keep p6 above that? | `model.cap_p6_soft = Constraint(expr=model.xp['p6'] <= 180)` | 456.0 |

### bchtsp_mip  (7)  — `testing_library/feas_test/bchtsp_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at a pilot where the driver always makes a delivery on the city-1 to city-6 corridor for a partner depot. If we require the tour to include that direct leg from city 1 to city 6, what total distance does the planner come back with? | `model.use_16 = Constraint(expr=model.x['i1', 'i6'] == 1)` | 112.0 |
| WHAT-IF/new_constraint | Suppose a return-haul contract forces the truck to come back into city 1 directly from city 7 at the end of its run. With that city-7-to-city-1 leg locked in, where does the total route length land? | `model.use_71 = Constraint(expr=model.x['i7', 'i1'] == 1)` | 116.0 |
| WHAT-IF/new_constraint | There's a scheduling idea on the table to chain city 2 directly into city 5 so a shared crew can ride along. If we require the route to take the city-2-to-city-5 leg, what does that do to the overall mileage? | `model.use_25 = Constraint(expr=model.x['i2', 'i5'] == 1)` | 84.0 |
| WHY-NOT/constraint_rule | City 5 sits right next to city 3 on our map, but the plan never drives straight from 3 into 5 — it always sneaks in some other way. Shouldn't the route just take the direct city-3-to-city-5 leg? What's the model seeing that makes it avoid that? | `model.force_35 = Constraint(expr=model.x['i3', 'i5'] == 1)` | 84.0 |
| WHY-NOT/constraint_rule | Coming back into the home base from city 6 looks like the natural way to close the loop, yet the plan leaves that city-6-to-city-1 leg switched off completely. Couldn't we just route the return that way? What's pushing the optimizer off it? | `model.force_61 = Constraint(expr=model.x['i6', 'i1'] == 1)` | 116.0 |
| WHY-NOT/constraint_rule | I'd have expected the driver to head out from base straight to city 7, but the plan never opens the city-1-to-city-7 leg. Why couldn't we just start the run with that hop? What's the tradeoff the model is making by keeping it dark? | `model.force_17 = Constraint(expr=model.x['i1', 'i7'] == 1)` | 112.0 |
| WHY-NOT/constraint_rule | City 4 and city 5 are neighbors on the route sheet, so handing one straight to the other seems obvious — but the optimizer never runs the city-4-to-city-5 leg. Shouldn't it just take that direct connection? What's keeping it from doing so? | `model.force_45 = Constraint(expr=model.x['i4', 'i5'] == 1)` | 84.0 |

### bid_mip  (5)  — `testing_library/feas_test/bid_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to lean less on vendor a — suppose we hold the purchase from a to 20000 units at most. What does the optimizer return for cost? | `model.cap_a = Constraint(expr=model.pl['a', 1] <= 20000)` | 15303108.552000001 |
| WHAT-IF/new_constraint | We're evaluating a cap on the smaller vendor e — hold its first-segment volume to 20000 units and tell me the resulting cost. | `model.cap_e = Constraint(expr=model.pl['e', 1] <= 20000)` | 15218065.6912 |
| WHY-NOT/constraint_rule | We're putting an awful lot of the order through vendor c. Shouldn't we hold c to no more than 120000 units and spread the rest around? What's keeping the model from doing that? | `model.cap_c_120k = Constraint(expr=model.pl['c', 1] <= 120000)` | 15487241.78352 |
| WHY-NOT/constraint_rule | I'm uneasy about how dependent this plan is on vendor c. Is there a reason we couldn't drop c entirely and still cover the requirement? Walk me through the tradeoff. | `model.drop_c = Constraint(expr=model.plb['c', 1] <= 0)` | 15981973.392 |
| WHY-NOT/constraint_rule | Vendor a comes with a setup charge for not that much volume. Couldn't we just leave a out of the award? What's pulling the plan toward keeping it? | `model.drop_a = Constraint(expr=model.plb['a', 1] <= 0)` | 15439252.712000001 |

### bidpwl_mip  (8)  — `testing_library/feas_test/bidpwl_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We don't want to be over-exposed to any single supplier. Suppose we hold vendor C's award to no more than 120,000 units and let the rest of the panel pick up the slack — what total cost does the optimizer return? | `model.cap_c = Constraint(expr=model.x['c'] <= 120000)` | 15487241.78352 |
| WHAT-IF/new_constraint | Procurement wants to seed a relationship with vendor B by giving them a guaranteed slice. If we commit at least 50,000 units to B this cycle, where does the total bill land? | `model.min_b = Constraint(expr=model.x['b'] >= 50000)` | 15305000.5312 |
| WHAT-IF/new_constraint | We're looking at keeping vendor D in the rotation for supply-base resilience. Say we require at least 10,000 units to go to D — what does the optimizer come back with for the overall cost? | `model.min_d = Constraint(expr=model.x['d'] >= 10000)` | 15240073.492 |
| WHAT-IF/new_constraint | Vendor E's logistics can only reliably handle so much per cycle. Let's see the case where their award is capped at 30,000 units — what's the resulting procurement cost? | `model.cap_e = Constraint(expr=model.x['e'] <= 30000)` | 15242412.61424 |
| WHY-NOT/constraint_rule | Vendor B put in a full bid and the plan still leaves them with nothing. Shouldn't we at least light up their first pricing tier rather than shutting them out entirely? What's the model seeing that makes awarding B a worse deal? | `model.cr_open_b = Constraint(expr=model.segb['b', 1] >= 1)` | 15251822.36752 |
| WHY-NOT/constraint_rule | Vendor D is sitting completely idle in the award. Couldn't we hand them their full 12,000-unit tier to keep a second source warm? What's pulling the optimizer away from using D at all? | `model.cr_use_d = Constraint(expr=model.x['d'] >= 12000)` | 15244749.492 |
| WHY-NOT/constraint_rule | Vendor E offers a deeper-discount tier above their first one, yet the plan keeps them parked on the cheaper-looking first tier. Wouldn't pushing E onto that deeper tier save us money? What's the model seeing that keeps it from doing that? | `model.cr_e_deep = Constraint(expr=model.segb['e', 2] >= 1)` | 15218065.6912 |
| WHY-NOT/constraint_rule | Leaning this hard on vendor C feels risky — they're carrying almost 70% of the order. Shouldn't no single vendor exceed 150,000 units so we're not so concentrated? What's the tradeoff the model is making by piling it all onto C? | `model.cr_spread_c = Constraint(expr=model.x['c'] <= 150000)` | 15305084.552000001 |

### bidsos_mip  (8)  — `testing_library/feas_test/bidsos_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're wary of putting too much of the order on a single supplier. Suppose we don't let vendor C's segment-1 bid carry more than half the blend — cap pl[c,1] at 0.5 and let the others pick up the slack. What total cost does the optimizer return? | `model.cap_c = Constraint(expr=model.pl['c', 1] <= 0.5)` | 15584385.64752 |
| WHAT-IF/new_constraint | There's interest in keeping vendor B engaged for the future rather than letting them walk. We're looking at requiring B to take a real bid instead of 'nodeal' — force pl[b,nodeal] down to 0. What does the plan cost in that case? | `model.force_b = Constraint(expr=model.pl['b', 'nodeal'] <= 0.0)` | 15423180.5312 |
| WHAT-IF/new_constraint | Vendor D has been asking for a guaranteed slice of the volume. We want to see what happens if we commit at least half of D's segment-1 tier — set pl[d,1] to no less than 0.5. Where does the total purchase cost land? | `model.floor_d = Constraint(expr=model.pl['d', 1] >= 0.5)` | 15230721.492 |
| WHAT-IF/new_constraint | Right now vendor E is split between two bid tiers. We're curious what it costs if we instead settle E entirely on its segment-1 breakpoint — pin pl[e,1] to a full 1. What total bill does that scenario produce? | `model.pin_e = Constraint(expr=model.pl['e', 1] >= 1.0)` | 15218065.6912 |
| WHY-NOT/constraint_rule | Vendor A is the cheapest unit price in the whole field, yet the plan only buys their 33,000-unit tier and then walks away from them on the margin. Shouldn't we be leaning on A more, not capping them — what's the model seeing that stops A's segment-1 bid from carrying more than half the blend? | `model.cap_a = Constraint(expr=model.pl['a', 1] <= 0.5)` | 15327608.552 |
| WHY-NOT/constraint_rule | I don't get why vendor A wins anything at all when their tier is so small. Couldn't we just hand the whole thing to the bigger suppliers and let A walk — force pl[a,nodeal] to 1? What's pulling the optimizer toward keeping A in the mix? | `model.why_a = Constraint(expr=model.pl['a', 'nodeal'] >= 1.0)` | 15439252.712 |
| WHY-NOT/constraint_rule | Vendor D is sitting completely on the bench in this plan. For supply security we'd rather not have a supplier with zero business — couldn't D pick up at least 30% of its segment-1 tier? What's the tradeoff the model is making by leaving D dark? | `model.why_d = Constraint(expr=model.pl['d', 1] >= 0.3)` | 15225110.292000001 |
| WHY-NOT/constraint_rule | Vendor B has a big mid-tier bid at segment 2 that the plan never touches. Wouldn't it make sense to put a real chunk of the order through B's segment-2 breakpoint, say 40% of the weight? What's keeping the model from using that tier? | `model.why_b = Constraint(expr=model.pl['b', 2] >= 0.4)` | 15469488.531200001 |

### boxpacking_mip  (2)  — `testing_library/feas_test/boxpacking_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Carton b31 is one of the big ones, and there's a chance it ships separately on a flat-rack instead. If we hold b31 out of this container entirely, what total volume does the rest of the load come to? | `model.hold_b31 = Constraint(expr=model.OMEGA['b31'] == 0)` | 11.743240000000002 |
| WHY-NOT/constraint_rule | We've got an awkward mid-size carton b17 that the crew would rather not handle this run. Is there really no harm in just pulling it out? Force b17 to stay out of the container and show me where the loaded volume lands. | `model.skip_b17 = Constraint(expr=model.OMEGA['b17'] == 0)` | 12.034850000000002 |

### cbenders_mip  (5)  — `testing_library/feas_test/cbenders_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose the w4 site falls through entirely and we can't stand it up at all this cycle. With w4 forced shut, what total cost does the optimizer return for serving everyone from the remaining three? | `model.close_w4 = Constraint(expr=model.ow['w4'] == 0)` | 12821.0 |
| WHY-NOT/constraint_rule | Region r8 is being served entirely out of w4, which sits a fair way off. Couldn't w1 carry at least a slice of r8's k1 volume — say 10 units — to hedge that single dependency? What's the model seeing that makes leaning on w4 alone the better call? | `model.force_w1r8 = Constraint(expr=model.x['w1', 'r8', 'k1'] >= 10)` | 12131.0 |
| WHY-NOT/constraint_rule | Warehouse w3 never gets an arc into region r3 in the plan, even though it's a sizable site. Shouldn't we wire w3 up to serve r3 for resilience? What's pulling the optimizer away from opening that lane? | `model.force_w3r3 = Constraint(expr=model.oa['w3', 'r3'] >= 1)` | 11725.0 |
| WHY-NOT/constraint_rule | Region r1 is sourced wholly from w1 right now. Wouldn't it be smarter to have w2 also feed r1 — at least 10 units of k1 — so we're not putting all of r1 on a single bay? What's the tradeoff that keeps the model from splitting it? | `model.force_w2r1 = Constraint(expr=model.x['w2', 'r1', 'k1'] >= 10)` | 11815.0 |
| WHY-NOT/constraint_rule | The w2 plant has no arc into the big r9 market at all in the current plan. Shouldn't w2 be opened up to r9 to share that load? What's the model weighing that leaves that lane shut? | `model.open_w2r9 = Constraint(expr=model.oa['w2', 'r9'] >= 1)` | 11669.0 |

### ccoil_mip  (7)  — `testing_library/feas_test/ccoil_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to oversize the 1-to-3 segment up front — lay the largest pipe type (6) on that arc. What does the resulting build cost? | `model.big_13 = Constraint(expr=model.bk['1', '3', '6'] == 1)` | 1527.5 |
| WHAT-IF/new_constraint | A landowner is blocking the 15-to-33 corridor, so we may not be able to run that pipe at all. If arc 15-33 is off the table, what does rerouting cost us? | `model.drop_1533 = Constraint(expr=model.b['15', '33'] == 0)` | 1605.75 |
| WHAT-IF/new_constraint | Suppose the 24-to-17 link can't be built — say there's a right-of-way conflict. Where does the total land once the flow has to find another way? | `model.drop_2417 = Constraint(expr=model.b['24', '17'] == 0)` | 1654.0 |
| WHY-NOT/constraint_rule | The design lays a little pipe from node 1 to node 3. That looks like avoidable clutter — shouldn't we just skip building 1-to-3 entirely? What's the routing seeing that makes it worth laying? | `model.skip_13 = Constraint(expr=model.b['1', '3'] == 0)` | 1437.5 |
| WHY-NOT/constraint_rule | Why does the plan bother running a pipe from 7 straight into the port at 33? Couldn't that flow ride an existing line instead of getting its own? What's the trade-off keeping it separate? | `model.skip_733 = Constraint(expr=model.b['7', '33'] == 0)` | 1483.75 |
| WHY-NOT/constraint_rule | The 8-to-9 segment looks like an odd little spur. Wouldn't it be cleaner to leave it out and route node 8's output another way? What's pulling the optimizer toward building it? | `model.skip_89 = Constraint(expr=model.b['8', '9'] == 0)` | 1473.0 |
| WHY-NOT/constraint_rule | Building the 23-to-24 link feels like it's just duplicating capacity we already have nearby. Shouldn't we drop it? What's the reason the plan won't let that go? | `model.skip_2324 = Constraint(expr=model.b['23', '24'] == 0)` | 1442.0 |

### chance_lp  (4)  — `testing_library/feas_test/chance_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Sesame's been showing up in news bulletins about export-quota tightening — procurement wants a hard cap at 20% of our blend before anything blows up. What does the optimizer return for the feed cost? | `model.cap_sesame = Constraint(expr=model.x['sesame'] <= 0.2)` | 29.339149209710353 |
| WHAT-IF/new_constraint | There's a proposal to keep a steady call on the oats contract — hold oats to at least 10% of the blend so the supplier stays warm. What's the resulting feed cost? | `model.floor_oats = Constraint(expr=model.x['oats'] >= 0.10)` | 29.059845432214903 |
| WHAT-IF/new_constraint | We're evaluating a plan to keep ground meal in rotation for shelf-life reasons — require at least 5% of the blend be ground meal. Where does the blend cost land? | `model.floor_gm = Constraint(expr=model.x['grnd-meal'] >= 0.05)` | 29.201532705099776 |
| WHY-NOT/constraint_rule | Leaning this hard on barley feels risky if a single harvest comes in bad. Couldn't we hold barley to no more than 40% of the blend? What's the model seeing that makes it pile in? | `model.cap_barley40 = Constraint(expr=model.x['barley'] <= 0.40)` | 29.361726484971545 |

### chem_mip  (8)  — `testing_library/feas_test/chem_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Our supplier just flagged an outage on the hydronium ion, chemical 5. If we can't source it, is acetone still synthesizable? Run it and tell me where producibility lands. | `model.material_cons[5].deactivate() model.lose_c5 = Constraint(expr=model.y[5] == 0)` | 1.0 |
| WHAT-IF/new_constraint | Chemical 31, nacn, is going off the market for a stretch. Plug that in — does acetone stay producible without it? | `model.material_cons[31].deactivate() model.lose_c31 = Constraint(expr=model.y[31] == 0)` | 0.0 |
| WHAT-IF/new_constraint | There's a chance we run short on raw material 10 for a while. Let's see whether acetone production still goes through if 10 is out. | `model.material_cons[10].deactivate() model.lose_c10 = Constraint(expr=model.y[10] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | The route keeps insisting on chemical 22. Do we genuinely need it to make acetone, or is the model just being conservative? What's it seeing if we try to do without? | `model.material_cons[22].deactivate() model.drop_c22 = Constraint(expr=model.y[22] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | Chemical 25 keeps showing up as a must-have. Is it really load-bearing for acetone, or could we just leave it off the list? What's the trade-off? | `model.material_cons[25].deactivate() model.drop_c25 = Constraint(expr=model.y[25] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | Why does the solution keep hanging on to chemical 33? Couldn't we make acetone without it and trim the material list? | `model.material_cons[33].deactivate() model.drop_c33 = Constraint(expr=model.y[33] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | We keep stocking chemical 17 for this process. Do we actually need it on the acetone route, or is it just along for the ride? What's the model seeing if we drop it? | `model.material_cons[17].deactivate() model.drop_c17 = Constraint(expr=model.y[17] == 0)` | 1.0 |
| WHY-NOT/constraint_rule | Is chemical 15 truly necessary here, or is it dead weight on the material list? Could acetone be made without it? | `model.drop_c15 = Constraint(expr=model.y[15] == 0)` | 1.0 |

### clad_mip  (8)  — `testing_library/feas_test/clad_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're curious how the censored fit behaves if the constant term isn't allowed to go negative — some reviewers expect a non-negative baseline. If we require beta[Intcpt] to be at least zero, what sum of absolute deviations does the estimator report? | `model.c_intcpt_nn = Constraint(expr=model.beta['Intcpt'] >= 0)` | 365.6121132713747 |
| WHAT-IF/new_constraint | Let's look at a scenario where prior theory pins the marriage-rating effect to be solidly positive. If we force the rateMar coefficient up to at least 1.0, what deviation total does the model land on? | `model.c_ratemar_floor = Constraint(expr=model.beta['rateMar'] >= 1)` | 261.6136348981933 |
| WHAT-IF/new_constraint | Suppose we wanted to drop the years-married regressor entirely and refit — i.e. hold its coefficient at exactly zero. What's the resulting absolute-deviation objective for that reduced specification? | `model.c_yearsma_zero = Constraint(expr=model.beta['YearsMa'] == 0)` | 261.2974683764617 |
| WHAT-IF/new_constraint | For the first household in the file, we want to see what happens if its fitted value phi[h1] is required to stay non-negative rather than being allowed to dip below zero. What does that one restriction do to the overall deviation total? | `model.c_phi_h1_nn = Constraint(expr=model.phi['h1'] >= 0)` | 349.08285846785117 |
| WHY-NOT/constraint_rule | The fitted value phi[h10] is coming out negative for household 10, which feels off for what's supposed to be a censored-from-below quantity. Shouldn't that fitted value be held at zero or above? What's the estimator seeing that makes a negative fit cheaper here? | `model.why_phi_h10 = Constraint(expr=model.phi['h10'] >= 0)` | 292.23412932430574 |
| WHY-NOT/constraint_rule | The Age coefficient comes back at nearly -9.6, which strikes me as an implausibly strong negative pull. Couldn't the model keep beta[Age] to something milder, say no lower than -5, and still fit reasonably? What's driving it that far down? | `model.why_age_floor = Constraint(expr=model.beta['Age'] >= -5)` | 256.4007959733549 |
| WHY-NOT/constraint_rule | An intercept of about -18 seems extreme for a baseline. Wouldn't a less drastic constant, say beta[Intcpt] no lower than -10, give essentially the same fit? Why is the estimator pushing the intercept so far down? | `model.why_intcpt_floor = Constraint(expr=model.beta['Intcpt'] >= -10)` | 255.19958672819328 |
| WHY-NOT/constraint_rule | Household 5's fitted value phi[h5] is sitting below zero in the solution. For a left-censored response that should bottom out at the threshold, that looks wrong — shouldn't phi[h5] be at least zero? What is the model trading off by letting it go negative? | `model.why_phi_h5 = Constraint(expr=model.phi['h5'] >= 0)` | 265.5916334567817 |

### cmo_mip  (5)  — `testing_library/feas_test/cmo_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating forcing the n6 tranche into the structure this time. Run it and tell me what the proceeds become. | `model.use_n6 = Constraint(expr=model.tin['n6'] == 1)` | 97.32314087055501 |
| WHAT-IF/new_constraint | There's a proposal to put tranche n4 into the deal. Plug that in and let me see the resulting proceeds. | `model.use_n4 = Constraint(expr=model.tin['n4'] == 1)` | 97.31483452770306 |
| WHAT-IF/new_constraint | Suppose we take n1 out of the structure entirely. What does that do to the gross proceeds? | `model.drop_n1 = Constraint(expr=model.tin['n1'] == 0)` | 97.323140870555 |
| WHAT-IF/new_constraint | We're looking at a deal that leaves the big n5 tranche out altogether. Run that scenario and walk me through where proceeds end up. | `model.drop_n5 = Constraint(expr=model.tin['n5'] == 0)` | 96.90168705150822 |
| WHY-NOT/constraint_rule | Tranche n3 is sitting on the shelf unused. Wouldn't it make sense to put it to work in the structure? What's the deal giving up by leaving n3 out? | `model.want_n3 = Constraint(expr=model.tin['n3'] == 1)` | 97.31483452770306 |

### coex_mip  (2)  — `testing_library/feas_test/coex_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're curious whether anchoring a black queen on the centre of the board changes how big the armies can get. Suppose we plant a black queen on the row-4, column-4 square and let the rest of the placement adjust around it — what total army size does the optimizer return? | `model.anchor_b44 = Constraint(expr=model.b[4, 4] >= 1)` | 9.0 |
| WHAT-IF/new_constraint | Say the white army insists on holding the far corner at row 8, column 8 for symbolic reasons. If we pin a white queen there and let everything else fall into place, what's the largest each army can still be? | `model.hold_w88 = Constraint(expr=model.w[8, 8] >= 1)` | 9.0 |

### coexx_mip  (10)  — `testing_library/feas_test/coexx_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at a layout that stations a white queen on row 2, column 4. Lock that square in for white and tell me how big each army can still be. | `model.place_w_2_4 = Constraint(expr=model.xw['2', '4'] == 1)` | 3.0 |
| WHAT-IF/new_constraint | There's a proposal to plant a white queen on row 3, column 5. Put that square in and tell me the resulting army size. | `model.place_w_3_5 = Constraint(expr=model.xw['3', '5'] == 1)` | 3.0 |
| WHAT-IF/new_constraint | Let's try committing a white queen to row 3, column 2 and see whether the armies can still field their full count. | `model.place_w_3_2 = Constraint(expr=model.xw['3', '2'] == 1)` | 4.0 |
| WHAT-IF/new_constraint | Suppose we hand the black army the bottom-right corner at row 5, column 5. Add that and let me see how large the armies come out. | `model.place_b_5_5 = Constraint(expr=model.xb['5', '5'] == 1)` | 4.0 |
| WHAT-IF/new_constraint | There's a proposal to hand the black army the square at row 2, column 4. Place a black queen there and tell me how large the armies come out. | `model.place_b_2_4 = Constraint(expr=model.xb['2', '4'] == 1)` | 3.0 |
| WHY-NOT/constraint_rule | Row 4, column 2 looks like wide-open space for white, yet the plan leaves it empty. Shouldn't white just grab that square? What's the model seeing that keeps it off? | `model.want_w_4_2 = Constraint(expr=model.xw['4', '2'] == 1)` | 3.0 |
| WHY-NOT/constraint_rule | Square (5,3) along the bottom edge sits unused. Wouldn't it be obvious to drop a white queen there? What's the trade-off pulling the layout the other way? | `model.want_w_5_3 = Constraint(expr=model.xw['5', '3'] == 1)` | 3.0 |
| WHY-NOT/constraint_rule | The whole center of the board is empty — shouldn't the black army at least claim the middle square (3,3)? What's keeping a queen off the center? | `model.want_b_3_3 = Constraint(expr=model.xb['3', '3'] == 1)` | 4.0 |
| WHY-NOT/constraint_rule | White already has room on row 2, column 5 — shouldn't it take that square too? What's the model trading off by leaving it open? | `model.want_w_2_5 = Constraint(expr=model.xw['2', '5'] == 1)` | 4.0 |
| WHY-NOT/constraint_rule | Square (4,2) sits open for the black army too — shouldn't black just grab it? What's the model trading off by leaving it unclaimed? | `model.want_b_4_2 = Constraint(expr=model.xb['4', '2'] == 1)` | 3.0 |

### copper_mip  (5)  — `testing_library/feas_test/copper_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're curious how much the network leans on Chile's richest deposit. Suppose we held the activity on Chile's high-grade mining process to no more than 400 units a year — what total cost does the optimizer come back with? | `model.cap_chi_hg = Constraint(expr=model.zm['high-grade', 'chile'] <= 400)` | 73933.29050853153 |
| WHAT-IF/new_constraint | Suppose Peru lands a long-term supply contract to feed refined copper into the US market — at least 400 units a cycle on the Peru-to-USA lane. What does committing to that do to total network cost? | `model.peru_usa = Constraint(expr=model.xfr['peru', 'usa'] >= 400)` | 73140.36203896781 |
| WHY-NOT/constraint_rule | The plan pours a huge expansion into Chile's open-pit. That feels like over-concentration — shouldn't we hold that one open-pit build to something more modest, say at most 200 units of added capacity, and lean on other mines? What's the model seeing that makes the big Chile build worth it? | `model.cap_chi_hm = Constraint(expr=model.hm['open-pit', 'chile'] <= 200)` | 72870.93686211717 |
| WHY-NOT/constraint_rule | Chile sits relatively close to Western Europe, yet the plan ships nothing refined from Chile into that market. Couldn't we route at least 500 units of refined copper Chile-to-Western-Europe and shorten the supply lines? What's pulling the optimizer away from that? | `model.chi_weu = Constraint(expr=model.xfr['chile', 'w-europe'] >= 500)` | 72665.60760822191 |
| WHY-NOT/constraint_rule | Canada is a stone's throw from the US market, but the plan barely uses the Canada-to-USA refined lane. Shouldn't Canada be carrying at least 300 units into the States instead of sourcing it from further afield? What's the tradeoff the model is making there? | `model.can_usa = Constraint(expr=model.xfr['canada', 'usa'] >= 300)` | 72795.58912739853 |

### cross_mip  (8)  — `testing_library/feas_test/cross_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Say a holdup means nothing can be all-across until period 9 at the earliest. Add that and tell me how many all-clear periods we end up with. | `model.delay8 = Constraint(expr=model.done['t8'] == 0)` | 2.0 |
| WHAT-IF/new_constraint | There's a scenario where the corn can't be loaded onto the boat until after period 6 — so it isn't across at period 6. Plug that in and see how the count comes out. | `model.hold_corn6 = Constraint(expr=model.y['corn', 't6'] == 0)` | 1.0 |
| WHAT-IF/new_constraint | We're evaluating a case where the goose still isn't on the far bank at period 8. Run it and tell me the resulting number of all-clear periods. | `model.goose_late = Constraint(expr=model.y['goose', 't8'] == 0)` | 1.0 |
| WHY-NOT/constraint_rule | The goose paddles over early and then gets hauled right back to the near bank — that round trip looks like wasted effort. Shouldn't it just stay put on the far side from period 5 on? What's the model seeing that forces the goose back? | `model.goose_stay5 = Constraint(expr=model.y['goose', 't5'] == 1)` | 1.0 |
| WHY-NOT/constraint_rule | All this shuttling the goose back and forth seems pointless — wouldn't it be obvious to have it settled on the far bank by period 6 and leave it there? What's the trade-off pulling it back across? | `model.goose_stay6 = Constraint(expr=model.y['goose', 't6'] == 1)` | 1.0 |
| WHY-NOT/constraint_rule | Why rush the wolf over at period 6 at all? Couldn't it just sit on the near bank a while longer and keep things simple? What's the optimizer weighing that gets the wolf moving so soon? | `model.hold_wolf6 = Constraint(expr=model.y['wolf', 't6'] == 0)` | 1.0 |
| WHY-NOT/constraint_rule | The plan scrambles to get everyone across by period 8. Do we really need to push that hard — couldn't we ease off and not insist on being all-clear at period 9? What's the cost of relaxing that? | `model.relax9 = Constraint(expr=model.done['t9'] == 0)` | 2.0 |
| WHY-NOT/constraint_rule | Do we even need the corn hauled all the way across by the end? Suppose we just leave it on the near bank at period 8 — what does insisting otherwise actually buy us? | `model.leave_corn = Constraint(expr=model.y['corn', 't8'] == 0)` | 0.0 |

### csp_mip  (1)  — `testing_library/feas_test/csp_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Position c5 is all over the place across the strings, so it feels like a coin flip. Why not just pin it to character 'a1' (the value s2 carries there) and move on — wouldn't nailing that one position down cost us anything on the worst-case distance? | `model.pin_c5 = Constraint(expr=model.v['c5', 'a1'] == 1)` | 4.0 |

### cubesoln_mip  (1)  — `testing_library/feas_test/cubesoln_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Putting a cell dead-center of the cube feels wasteful. Why not just leave the very middle position empty — wouldn't the layout be just as clean without it? | `model.no_center = Constraint(expr=model.core[2, 2, 2] == 0)` | 4.0 |

### cutstock_mip  (7)  — `testing_library/feas_test/cutstock_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Pattern p6 needs a particular knife setup our crew finds slow to change over, and the plan leans on it hard. We're looking at holding p6 to no more than 180 rolls a cycle and letting the rest of the pattern mix absorb the difference — what total roll count does the optimizer come back with? | `model.cap_p6 = Constraint(expr=model.xp['p6'] <= 180)` | 456.0 |
| WHAT-IF/new_constraint | Pattern p3 is set up and idle right now. We're considering keeping it warm by committing at least 50 rolls to it each cycle so the operators stay practiced on it. Where does that land the total roll usage? | `model.use_p3 = Constraint(expr=model.xp['p3'] >= 50)` | 466.0 |
| WHAT-IF/new_constraint | There's a contractual minimum from the customer who specs pattern p4 (the seven-up cut of the 14-wide). Suppose we have to run p4 at least 10 times a cycle to honour that — what's the resulting roll total? | `model.use_p4 = Constraint(expr=model.xp['p4'] >= 10)` | 463.0 |
| WHY-NOT/constraint_rule | The whole plan leans heavily on pattern p6 — almost 200 rolls of it. That feels like putting all our eggs in one setup. Couldn't we just hold p6 down to 100 rolls and spread the work around? What is the model seeing that makes leaning on p6 the right call? | `model.cap_p6 = Constraint(expr=model.xp['p6'] <= 100)` | 469.0 |
| WHY-NOT/constraint_rule | Pattern p3 gives a clean three-up of the 31-wide with hardly any trim, yet the plan never touches it. Shouldn't we be running it a good amount — say at least 100 rolls — instead of leaving it parked? What's steering the optimizer away from p3? | `model.use_p3 = Constraint(expr=model.xp['p3'] >= 100)` | 478.0 |
| WHY-NOT/constraint_rule | I don't get why pattern p4 sits completely unused — it's the most efficient way to make the 14-wide, seven per roll. Couldn't we lean on it for at least 20 rolls? What's the trade-off the model is making by keeping p4 off? | `model.use_p4 = Constraint(expr=model.xp['p4'] >= 20)` | 473.0 |
| WHY-NOT/constraint_rule | If pattern p4 really is the cleanest cut for the 14-wide, why not commit to it in volume — make it carry at least 50 rolls of the load? Where does the model think that goes wrong? | `model.use_p4 = Constraint(expr=model.xp['p4'] >= 50)` | 503.0 |

### danwolfe_lp  (2)  — `testing_library/feas_test/danwolfe_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to lean harder on the n15 to n20 bypass for k5 — route at least 60 units of k5 over that link so we're not so dependent on the n15-n11 corridor. What does the optimizer return for total cost if we require that? | `model.k5_bypass_min = Constraint(expr=model.x['k5', 'n15', 'n20'] >= 60)` | 2920.236757 |
| WHY-NOT/constraint_rule | The plan keeps shoving the bulk of k5 onto the n15 to n11 corridor right up to its limit. Couldn't we hold k5's flow on that one link to 60 units and spread the rest over the bypass? What's keeping the model from de-risking that pinch point? | `model.k5_n15n11_cap60 = Constraint(expr=model.x['k5', 'n15', 'n11'] <= 60)` | 2939.46528 |

### decomp_lp97  (1)  — `testing_library/feas_test/decomp_lp97.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | It bugs me that plant-1 is shut out of terminal 2 entirely — that's our biggest account sitting on a single supplier. Shouldn't plant-1 be carrying at least a couple of units of terminal 2's demand for resilience? What's holding the optimizer back from spreading that account? | `model.p1_serve_t2 = Constraint(expr=model.x['plant-1', 'term-2'] >= 2.0)` | 57.0 |

### dice_mip  (4)  — `testing_library/feas_test/dice_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're toying with a more compact first die so it's easier to read at a glance. Suppose we hold die1's top face down to at most 10 pips and let the other two dice adjust around it — what win count does the optimizer come back with? | `model.cap_d1top = Constraint(expr=model.fval['dice1', 'face6'] <= 10)` | 20.0 |
| WHAT-IF/new_constraint | Marketing wants the third die to feel like the 'heavy' die, so none of its faces should be tiny. We're looking at requiring die3's lowest face to be at least 5 — what does the optimizer return for the per-die win count under that floor? | `model.floor_d3low = Constraint(expr=model.fval['dice3', 'face1'] >= 5)` | 20.0 |
| WHY-NOT/constraint_rule | The first die's faces bunch up at the top — 14, 15, 16 almost on top of each other. Wouldn't a flatter die that caps out around 10 be just as competitive? Force die1's top face down to 10 and tell me what the model loses by clustering it high. | `model.why_cap_d1 = Constraint(expr=model.fval['dice1', 'face6'] <= 10)` | 20.0 |
| WHY-NOT/constraint_rule | Die3 is carrying values as low as 3, which seems wasteful when die1 starts at 1 anyway. Shouldn't die3's smallest face sit at 5 or higher so it isn't competing down in the basement? What's the model seeing that makes keeping it low the better call? | `model.why_floor_d3 = Constraint(expr=model.fval['dice3', 'face1'] >= 5)` | 20.0 |

### dicegrid_mip  (4)  — `testing_library/feas_test/dicegrid_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Before we kick off another batch on the grid, we're curious what happens if die1 is kept low-profile — its top face held to no more than 10 pips while the rest of the set rearranges. What win count does the solver report for that scenario? | `model.cap_d1top = Constraint(expr=model.fval['dice1', 'face6'] <= 10)` | 20.0 |
| WHAT-IF/new_constraint | One experiment we'd like to queue: insist the third die's lowest face start no lower than 5, so it never carries the tiny values. What does the optimizer come back with for the per-die win count when we add that floor? | `model.floor_d3low = Constraint(expr=model.fval['dice3', 'face1'] >= 5)` | 20.0 |
| WHY-NOT/constraint_rule | Die1 packs 14, 15, 16 right next to each other at the top — that clustering looks inefficient. Couldn't a flatter die capped at 10 do the same job? Hold die1's top face to 10 and show me exactly what the model gives up by stacking it high. | `model.why_cap_d1 = Constraint(expr=model.fval['dice1', 'face6'] <= 10)` | 20.0 |
| WHY-NOT/constraint_rule | Why is die3 allowed to sink as low as 3 when die1 already owns the bottom of the range starting at 1? Shouldn't die3's smallest face be lifted to at least 5 so it isn't fighting in the basement? Force that floor and tell me what the model is protecting by keeping it low. | `model.why_floor_d3 = Constraint(expr=model.fval['dice3', 'face1'] >= 5)` | 20.0 |

### dicex_mip  (5)  — `testing_library/feas_test/dicex_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're curious where the score lands if we don't insist on the very best non-transitive set. Suppose we only ask each die to win at most 18 of its face matchups against the next die — what does the optimizer report for the common win count then? | `model.cap_w = Constraint(expr=model.wnx <= 18)` | 18.0 |
| WHAT-IF/new_constraint | Manufacturing would prefer die 1 not carry too high a top face. If we hold die 1's largest face value to 12 or below, what's the best win count the design can still reach? | `model.d1cap = Constraint(expr=model.fval['dice1', 'face6'] <= 12)` | 20.0 |
| WHAT-IF/new_constraint | Let's look at a layout where die 2 doesn't start so low. If we require die 2's smallest face to be at least 5, what win count does the optimizer come back with? | `model.d2lo = Constraint(expr=model.fval['dice2', 'face1'] >= 5)` | 21.0 |
| WHY-NOT/constraint_rule | It looks odd that die 3 is the one hoarding the top value 18 while die 1 wins the most. Shouldn't die 2 be the one carrying 18 on its top face instead? Pin die 2's highest face to 18 and tell me — does the win count actually suffer, and what's the model seeing? | `model.d2top = Constraint(expr=model.fval['dice2', 'face6'] == 18)` | 21.0 |
| WHY-NOT/constraint_rule | The plan has die 1's bottom face beating die 2's bottom face. That seems like a wasted win to hand to the weakest matchup. Why couldn't we just switch that particular comparison off and let the win go somewhere more useful? | `model.no_lowwin = Constraint(expr=model.comp['dice1', 'face1', 'face1'] == 0)` | 21.0 |

### diet_lp  (7)  — `testing_library/feas_test/diet_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Nutritionists worry the plan leans too hard on wheat. Let's see what the diet costs if we hold wheat to at most 2 cents a day. | `model.cap_wheat = Constraint(expr=model.x['wheat'] <= 0.02)` | 0.11381124731897624 |
| WHAT-IF/new_constraint | There's a push to get more leafy greens in — suppose we require at least 2 cents a day of cabbage. What does that do to the bill? | `model.floor_cabbage = Constraint(expr=model.x['cabbage'] >= 0.02)` | 0.1154325686273148 |
| WHAT-IF/new_constraint | The plan relies a lot on navy beans. We're evaluating a variety cap — hold navy beans to no more than 4 cents a day. What's the resulting cost? | `model.cap_navybeans = Constraint(expr=model.x['navybeans'] <= 0.04)` | 0.11011616102257213 |
| WHY-NOT/constraint_rule | This diet is heavy on wheat and that feels monotonous. Couldn't we just leave wheat out entirely and still hit every nutrient target? What's keeping the model on it? | `model.ban_wheat = Constraint(expr=model.x['wheat'] <= 0)` | 0.12481168827882236 |
| WHY-NOT/constraint_rule | Liver barely shows up in the plan even though it's a nutrition powerhouse. Shouldn't we be buying at least a cent of it a day? What's the tradeoff the model is seeing? | `model.floor_liver = Constraint(expr=model.x['liver'] >= 0.01)` | 0.11485807515421648 |
| WHY-NOT/constraint_rule | Spinach in the plan seems like an odd choice to me. Is there a reason we couldn't drop it altogether? Walk me through what it's buying us. | `model.ban_spinach = Constraint(expr=model.x['spinach'] <= 0)` | 0.11377559648016705 |
| WHY-NOT/constraint_rule | Canned milk is cheap and convenient, yet the plan skips it. Wouldn't it make sense to include at least a cent of it daily? What's pulling the optimizer away from it? | `model.floor_cannedmilk = Constraint(expr=model.x['cannedmilk'] >= 0.01)` | 0.10933606008178842 |

### dinam_lp  (4)  — `testing_library/feas_test/dinam_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We want to test a tighter investment envelope in 1974 — keep gross domestic investment that year under 78. What does that scenario give us for the objective? | `model.inv74_cap = Constraint(expr=model.inv['y1974'] <= 78.0)` | 251.31926846213582 |
| WHY-NOT/constraint_rule | The plan keeps ramping investment hard right out to the end — gross investment in 1986 looks aggressive. Shouldn't we hold 1986 investment under 160 and not over-build? What's the model seeing that makes it push it that high? | `model.inv86_cap = Constraint(expr=model.inv['y1986'] <= 160.0)` | 247.27833970840072 |
| WHY-NOT/constraint_rule | Why is the plan leaning so heavily on consumption way out in 1986 — that's a long way off and the forecast is shaky. Couldn't we just cap 1986 consumption at 600 and stay more conservative? What's the tradeoff the model is chasing? | `model.con86_cap = Constraint(expr=model.con['y1986'] <= 600.0)` | 245.79131378555812 |
| WHY-NOT/constraint_rule | We seem to be banking an awful lot in 1974 — savings that year run higher than I'd expect. Shouldn't 1974 savings stay under 78 so more flows through to consumption now? What's the model trading off by socking that much away? | `model.sav74_cap = Constraint(expr=model.sav['y1974'] <= 78.0)` | 251.21521434553415 |

### egypt_lp  (6)  — `testing_library/feas_test/egypt_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're studying a soil-rotation limit in the eastern delta that would hold rice there to no more than 400 thousand feddans. What does the plan return for surplus if rice in e-delta is capped at 400? | `model.rice_edelta_cap = Constraint(expr=model.xcrop['e-delta', 'rice'] <= 400.0)` | 4131097.623310254 |
| WHAT-IF/new_constraint | Suppose a foreign-exchange ceiling forces us to bring in at most 3,000 thousand tons of wheat imports. We're curious where the optimizer lands on surplus under that import cap. | `model.wheat_import_cap = Constraint(expr=model.imports['wheat'] <= 3000.0)` | 4061897.8876206204 |
| WHAT-IF/new_constraint | The sugar ministry is looking at a processing-capacity bound that would limit national sugarcane output to 8,000 thousand tons. What does serving that cap do to the surplus? | `model.sugarcane_output_cap = Constraint(expr=model.sales['sugarcane'] <= 8000.0)` | 4113969.2960081883 |
| WHY-NOT/constraint_rule | The eastern delta is prime rice country, yet the plan parks rice there at well under what the land could carry. Shouldn't we be growing at least 800 thousand feddans of rice in e-delta? What's the model seeing that holds it back? | `model.rice_edelta_floor = Constraint(expr=model.xcrop['e-delta', 'rice'] >= 800.0)` | 4132206.5491809025 |
| WHY-NOT/constraint_rule | We're leaning awfully hard on imported wheat to feed the country. Couldn't we tighten our belt and keep wheat imports under 2,000 thousand tons? What's the tradeoff the optimizer is making by buying so much abroad? | `model.wheat_import_floor_cut = Constraint(expr=model.imports['wheat'] <= 2000.0)` | 3952206.817746482 |
| WHY-NOT/constraint_rule | The plan packs a lot of cotton into the middle delta. That feels like over-concentration — shouldn't m-delta cotton be held to 200 thousand feddans at most? What's pulling the model toward loading it up there? | `model.cotton_mdelta_cap = Constraint(expr=model.xcrop['m-delta', 'cotton'] <= 200.0)` | 4122406.7043935554 |

### embmiex1_lp  (6)  — `testing_library/feas_test/embmiex1_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Our drivers are griping about the long San Diego-to-Topeka keg run. We're looking at holding that lane to 150 kegs. What does the optimizer return for cost and routing under that limit? | `model.sd_top_cap = Constraint(expr=model.x['san-diego', 'topeka'] <= 150)` | 158.85 |
| WHAT-IF/new_constraint | There's a proposal to spread the Seattle line's load — keep the Seattle-to-Chicago lane at 200 kegs or under. Plug it in and walk me through the result. | `model.sea_chi_cap = Constraint(expr=model.x['seattle', 'chicago'] <= 200)` | 154.575 |
| WHAT-IF/new_constraint | We'd like San Diego to keep a steady presence at the Chicago hub — at least 100 kegs on that lane. Let's see what that does to the bill. | `model.sd_chi_floor = Constraint(expr=model.x['san-diego', 'chicago'] >= 100)` | 154.575 |
| WHY-NOT/constraint_rule | San Diego is trucking a huge load up to New York. Shouldn't we hold that lane under 150 kegs and let Seattle carry more of the New York hub? What's keeping the model from doing that? | `model.sd_ny_cap = Constraint(expr=model.x['san-diego', 'new-york'] <= 150)` | 154.8 |
| WHY-NOT/constraint_rule | Seattle sends nothing to Topeka, which feels like an idle northern route. Wouldn't it be smarter to keep at least 50 kegs flowing Seattle-to-Topeka? What's the model seeing that I'm not? | `model.sea_top_floor = Constraint(expr=model.x['seattle', 'topeka'] >= 50)` | 155.475 |
| WHY-NOT/constraint_rule | Seattle barely serves New York even though it's a major hub. Shouldn't Seattle be pulling at least 120 kegs of the New York order? Walk me through what's pushing it the other way. | `model.sea_ny_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 120)` | 154.305 |

### epscm_lp  (1)  — `testing_library/feas_test/epscm_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Gas is our flexible cleaner unit, so leaning on it for peaks seems sensible. Couldn't we have gas cover at least 8000 GWh of peak load? What tradeoff is the model making that holds gas back at peak? | `model.gas_peak_floor = Constraint(expr=model.x['Gas', 'peak'] >= 8000.0)` | 3219000.0 |

### epscmmip_mip  (7)  — `testing_library/feas_test/epscmmip_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a standing commitment to keep item j1 in the program regardless of the numbers. If we force j1 into the basket, where does the primary score land? | `model.force_j1 = Constraint(expr=model.X['j1'] == 1)` | 1969.0 |
| WHAT-IF/new_constraint | Suppose item j17 turns out to be unavailable this cycle and has to be dropped from consideration entirely. What's the best primary score the optimizer can reach without it? | `model.drop_j17 = Constraint(expr=model.X['j17'] == 0)` | 1959.0 |
| WHAT-IF/new_constraint | Marketing is pushing to guarantee item j22 a slot this time. If we require j22 to be selected, what primary score does that scenario yield? | `model.force_j22 = Constraint(expr=model.X['j22'] == 1)` | 1970.0 |
| WHY-NOT/constraint_rule | Item j26 has a perfectly respectable primary value, yet the plan skips it entirely. Shouldn't we just go ahead and include j26? What's the model seeing that makes leaving it out the better call? | `model.why_j26 = Constraint(expr=model.X['j26'] == 1)` | 1957.0 |
| WHY-NOT/constraint_rule | I keep coming back to item j36 — it's not nothing on the primary score, but the optimizer won't touch it. Couldn't we just force j36 in? What's the tradeoff that keeps it out? | `model.why_j36 = Constraint(expr=model.X['j36'] == 1)` | 1951.0 |
| WHY-NOT/constraint_rule | Item j13 barely contributes anything to the primary score, but it's still sitting in the chosen basket. Why is the optimizer bothering to keep j13 in at all — couldn't it just be dropped? | `model.why_drop_j13 = Constraint(expr=model.X['j13'] == 0)` | 1973.0 |
| WHY-NOT/constraint_rule | Item j14 is about the weakest primary contributor we've got, yet there it is in the selection. Shouldn't we kick j14 out to make room for something better? What's the model holding onto it for? | `model.why_drop_j14 = Constraint(expr=model.X['j14'] == 0)` | 1973.0 |

### feasopt1_lp  (2)  — `testing_library/feas_test/feasopt1_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Dumping the entire 130-case shortfall onto new-york looks brutal for that one market. Why not spread it — make chicago absorb at least 200 of the unmet demand instead? Wouldn't a more even split be better overall? | `model.chi_relax_floor = Constraint(expr=model.r['chicago'] >= 200)` | 200.0 |
| WHY-NOT/constraint_rule | Topeka sits furthest out — intuitively it should be the one we under-serve, not new-york. Why not push at least 150 cases of the shortfall onto topeka? What's the plan trading off by keeping topeka fully supplied? | `model.top_relax_floor = Constraint(expr=model.r['topeka'] >= 150)` | 150.0 |

### fertd_mip  (6)  — `testing_library/feas_test/fertd_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The Aswan-to-Quena corridor for CAN-335 carries an awful lot of tonnage late in the plan. We're curious what happens if that single lane is held to 50 thousand tons in 1985-87 and the network reroutes the balance — where does the cost settle? | `model.cap_aswan_quena = Constraint(expr=model.xf['can-335', 'aswan', 'quena', '1985-87'] <= 50)` | 173.5323434379891 |
| WHAT-IF/new_constraint | Trade policy may pull our export allowance back in the last period. We want to see the case where total exports in 1985-87 are limited to 80 thousand tons instead of the full 100 — what does that scenario cost overall? | `model.cap_export = Constraint(expr=model.et['1985-87'] <= 80)` | 173.58111541125993 |
| WHY-NOT/constraint_rule | The plan leaves the ammonia-from-coke-gas upgrade at Helwan switched off in the opening period. With all that gas around, shouldn't we just commit to that upgrade in 1979-81? What's the model seeing that makes keeping it idle the better call? | `model.force_upgrade = Constraint(expr=model.up['amm-c-n', 'helwan', '1979-81'] >= 1)` | 179.3224150105226 |
| WHY-NOT/constraint_rule | We're running exports right up to the cap in the final period while domestic regions still lean on imports. Couldn't we hold late-period exports to 50 thousand tons and keep more product at home? What's the tradeoff the optimizer is making by exporting so much? | `model.trim_export = Constraint(expr=model.et['1985-87'] <= 50)` | 173.85463452211482 |
| WHY-NOT/constraint_rule | It looks risky to pile 140-odd thousand tons of CAN-335 onto the single Aswan-to-Quena lane in the last period. Shouldn't we spread that out and hold the lane to, say, 100 thousand tons? What's keeping the model from splitting it? | `model.spread_aswan = Constraint(expr=model.xf['can-335', 'aswan', 'quena', '1985-87'] <= 100)` | 173.46353309563523 |
| WHY-NOT/constraint_rule | The Abu Kir urea plant ships a huge slug into Behera late in the plan. Wouldn't it be more balanced to cap that one flow at 80 thousand tons and let other regions or sources carry the rest? What's the model trading off by routing it all there? | `model.urea_behera = Constraint(expr=model.xf['urea', 'abu-kir', 'behera', '1985-87'] <= 80)` | 173.4952639060655 |

### ferts_lp  (7)  — `testing_library/feas_test/ferts_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose Aswan's calcium-ammonium-nitrate line gets a firm output target — at least 260 of can-310 in the plan. What does the optimizer return for total cost under that floor? | `model.aswan_can310_floor = Constraint(expr=model.z['can-310', 'aswan'] >= 260.0)` | 59160.12560063064 |
| WHAT-IF/new_constraint | If we throttled the assiout single-superphosphate plant and held its SSP-155 output to no more than 100, where would total cost land? | `model.assiout_ssp_cap = Constraint(expr=model.z['ssp-155', 'assiout'] <= 100.0)` | 59652.73844282664 |
| WHAT-IF/new_constraint | What does the model return for total cost if Aswan's nitric-acid unit is limited to a process level of 140 — say for a maintenance window? | `model.aswan_nitric_cap = Constraint(expr=model.z['nitr-acid', 'aswan'] <= 140.0)` | 59583.908285701065 |
| WHY-NOT/constraint_rule | The plan pushes Aswan's calcium-ammonium-nitrate line right up to 235. That feels like a lot to lean on one unit — shouldn't we hold its can-310 output under 200? What's the model seeing that makes it run that line so hard? | `model.aswan_can310_pullback = Constraint(expr=model.z['can-310', 'aswan'] <= 200.0)` | 59511.76664063064 |
| WHY-NOT/constraint_rule | kafr-el-zt's superphosphate line is running near its ceiling. Couldn't we ease it back and keep its SSP-155 output under 120 to spread the load? What's pulling the model to load it up like that? | `model.kafr_ssp_pullback = Constraint(expr=model.z['ssp-155', 'kafr-el-zt'] <= 120.0)` | 59319.53307008945 |
| WHY-NOT/constraint_rule | Helwan's CAN-335 plant looks like it's doing more than its share. Shouldn't we hold that unit's output under 80? What's keeping the model from backing it off? | `model.helwan_can335_cap = Constraint(expr=model.z['can-335', 'helwan'] <= 80.0)` | 58808.069918336645 |
| WHY-NOT/constraint_rule | assiout makes its own SSP-155 yet the plan ships a lot of it out and barely keeps any locally. Shouldn't assiout cover at least 50 of its own SSP-155 demand from its own plant? Why does the model route it the way it does instead? | `model.assiout_local_ssp = Constraint(expr=model.xf['ssp-155', 'assiout', 'assiout'] >= 50.0)` | 58979.83512153064 |

### fiveleap_mip  (9)  — `testing_library/feas_test/fiveleap_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Say a damaged square blocks the leap from (1,1) straight across to (1,6) — that move is off the table. Can the leaper still complete a full tour, and how many leaps does it take? | `model.block_a = Constraint(expr=model.xm['1', '1', '1', '6'] == 0)` | 64.0 |
| WHAT-IF/new_constraint | We're evaluating forcing the tour to open by leaping straight down from (1,1) to (6,1). Does a full tour still exist with that opening, and what's the leap count? | `model.open_a = Constraint(expr=model.xm['1', '1', '6', '1'] == 1)` | 64.0 |
| WHAT-IF/new_constraint | Suppose we pin the first leap out of the corner to land on (5,4). Run it and tell me whether a complete tour holds up and how many leaps it has. | `model.open_b = Constraint(expr=model.xm['1', '1', '5', '4'] == 1)` | 64.0 |
| WHAT-IF/new_constraint | Let's try making the leaper start by jumping from the corner to (4,5). What does the tour come out to under that opening? | `model.open_c = Constraint(expr=model.xm['1', '1', '4', '5'] == 1)` | 64.0 |
| WHAT-IF/new_constraint | There's a proposal to take the (1,3)->(6,3) leap out of play entirely. With that move banned, does a full tour survive and at what leap count? | `model.block_b = Constraint(expr=model.xm['1', '3', '6', '3'] == 0)` | 64.0 |
| WHY-NOT/constraint_rule | The tour has the leaper fling itself from (1,2) clear across to (5,5). That looks like a wasteful long hop — couldn't it route somewhere tidier? What's keeping the model on that particular leap? | `model.want_no_25 = Constraint(expr=model.xm['1', '2', '5', '5'] == 0)` | 64.0 |
| WHY-NOT/constraint_rule | Why does the plan send the leaper from (1,4) down to (5,1)? It seems like an odd corner-bound hop. Couldn't the tour just skip that move? What's the model seeing that I'm not? | `model.want_no_41 = Constraint(expr=model.xm['1', '4', '5', '1'] == 0)` | 64.0 |
| WHY-NOT/constraint_rule | The leaper leaves square (5,5) heading to (1,2). Shouldn't it pick a closer landing instead of bouncing all the way back to the top edge? What's the trade-off forcing that move? | `model.want_no_55 = Constraint(expr=model.xm['5', '5', '1', '2'] == 0)` | 64.0 |
| WHY-NOT/heuristic | Here's a simpler idea: just make the leaper open by dropping straight down the file from (1,1) to (6,1), and let it sort out the rest. Does that rule-of-thumb start still complete a tour? | `model.h1 = Constraint(expr=model.xm['1', '1', '6', '1'] == 1)` | 64.0 |

### flowshop_mip  (7)  — `testing_library/feas_test/flowshop_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to lead the run off with part i6 so it's done early and out of the way. Lock it into the first slot and tell me the new makespan. | `model.i6_first = Constraint(expr=model.rank['i6', 'i1'] == 1)` | 38.0 |
| WHAT-IF/new_constraint | We're evaluating ending the run on part i1 — putting it in the last slot. Run it and let me see where the finish time lands. | `model.i1_last = Constraint(expr=model.rank['i1', 'i6'] == 1)` | 39.0 |
| WHAT-IF/new_constraint | Let's try finishing the run with part i3 in the final slot and see what the makespan comes out to. | `model.i3_last = Constraint(expr=model.rank['i3', 'i6'] == 1)` | 36.0 |
| WHAT-IF/new_constraint | Suppose we slot part i6 into the second position in the sequence. What's the resulting total run time? | `model.i6_second = Constraint(expr=model.rank['i6', 'i2'] == 1)` | 36.0 |
| WHY-NOT/constraint_rule | Part i2 is one of our lighter jobs — wouldn't it be obvious to run it first and get the floor moving? Yet the plan doesn't lead with it. What's the model seeing that keeps i2 out of the first slot? | `model.want_i2_first = Constraint(expr=model.rank['i2', 'i1'] == 1)` | 38.0 |
| WHY-NOT/constraint_rule | Part i4 is our heaviest piece through the line — shouldn't it close out the run so nothing waits on it? The plan buries it mid-sequence instead. What's the trade-off pulling it away from the last slot? | `model.want_i4_last = Constraint(expr=model.rank['i4', 'i6'] == 1)` | 39.0 |
| WHY-NOT/constraint_rule | Couldn't we just wrap the run with part i5 in the final slot? It looks like a natural closer to me. What's keeping the optimizer from ending on i5? | `model.want_i5_last = Constraint(expr=model.rank['i5', 'i6'] == 1)` | 36.0 |

### food_mip  (6)  — `testing_library/feas_test/food_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're scoping a maintenance slowdown on the month-one line that would hold its refined output to no more than 400 tons. If we run the plan with that single-month throughput limit in place, what total profit does the optimizer return? | `model.cap_prod_m1 = Constraint(expr=model.produce['m1'] <= 400)` | 99239.57326892111 |
| WHAT-IF/new_constraint | A supplier offered us a contracted lot of oil o1 and we'd like to know what it costs us to actually fold it into the blend. Suppose we require o1 to be switched on as a blend component in month four — what does the plan come back at? | `model.use_o1_m4 = Constraint(expr=model.induse['m4', 'o1'] >= 1)` | 99908.33333333337 |
| WHY-NOT/constraint_rule | The plan runs the month-four batch at only 405 tons while the early months sit at the full 450. Couldn't we just hold month four to 450 as well and sell more? What's the model seeing that makes it throttle that batch? | `model.full_m4 = Constraint(expr=model.produce['m4'] >= 450)` | 100213.88888888889 |
| WHY-NOT/constraint_rule | Month five gets dialed back to 405 tons too. Shouldn't we be running that line flat out at 450 every month rather than leaving it part-idle? What's the tradeoff that keeps the optimizer from doing that? | `model.full_m5 = Constraint(expr=model.produce['m5'] >= 450)` | 99988.88888888889 |
| WHY-NOT/constraint_rule | Oil o2 looks cheap in month one yet the plan waits and buys it later. Wouldn't it be smarter to lock in at least 100 tons of o2 up front in month one? What's the model weighing that steers it away from buying early? | `model.early_o2 = Constraint(expr=model.buy['m1', 'o2'] >= 100)` | 97778.70370370371 |
| WHY-NOT/constraint_rule | The month-four blend leans heavily on vegetable oil v1, which feels like over-concentration in a single feedstock. Couldn't we hold v1 to at most 100 tons that month and spread the blend out? What's the optimizer seeing that makes it pile onto v1? | `model.cap_v1_m4 = Constraint(expr=model.use['m4', 'v1'] <= 100)` | 100213.8888888889 |

### gapmin_mip  (5)  — `testing_library/feas_test/gapmin_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a compliance reason we might not be able to run item i1 on resource r1 anymore. Suppose we just block that pairing and let the network re-shuffle — what does the optimizer say the total cost becomes? | `model.no_r1_i1 = Constraint(expr=model.x['r1', 'i1'] == 0)` | 245.0 |
| WHAT-IF/new_constraint | Operations is curious about pinning item i10 to resource r3 instead of wherever it naturally falls — maybe for co-location with related work. If we require i10 to run on r3, what's the resulting total assignment cost? | `model.force_i10_r3 = Constraint(expr=model.x['r3', 'i10'] == 1)` | 226.0 |
| WHY-NOT/constraint_rule | Item i8 lands on r4 in the plan, but r2 is barely used and could clearly hold it. Shouldn't we just move i8 onto r2 to even out the load? What's the model seeing that makes that a bad trade? | `model.force_i8_r2 = Constraint(expr=model.x['r2', 'i8'] == 1)` | 279.0 |
| WHY-NOT/constraint_rule | Item i9 is on r3, but r1 looks like it has a slot to spare. Wouldn't it make sense to shift i9 over to r1? What's keeping the optimizer from doing that? | `model.force_i9_r1 = Constraint(expr=model.x['r1', 'i9'] == 1)` | 252.0 |
| WHY-NOT/constraint_rule | Item i5 went to r3, but r5 is right there and could take it. Shouldn't the model have put i5 on r5 instead — they look interchangeable to me? What's the cost the optimizer is dodging by not doing that? | `model.force_i5_r5 = Constraint(expr=model.x['r5', 'i5'] == 1)` | 226.0 |

### gussex1_lp  (2)  — `testing_library/feas_test/gussex1_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a service-level commitment to Chicago: under the proposal, Seattle would have to ship New York its full 325-case order directly so San Diego stays free to cover the interior. If we lock in Seattle-to-New-York at the entire 325, what cost and plan does the model return? | `model.ny_from_seattle = Constraint(expr=model.x['seattle', 'new-york'] >= 325)` | 107.77499999999999 |
| WHY-NOT/constraint_rule | Topeka leans entirely on San Diego today, which leaves us exposed if that plant stumbles. Shouldn't Seattle be carrying at least 100 cases into Topeka as a hedge? Why won't the model route some Topeka volume through Seattle on its own? | `model.seattle_topeka_floor = Constraint(expr=model.x['seattle', 'topeka'] >= 100)` | 110.24999999999999 |

### gussgrid_lp  (5)  — `testing_library/feas_test/gussgrid_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a lane-balancing guideline so San Diego isn't overcommitted to Topeka — hold the San Diego-to-Topeka lane at 250 loads or under. What does the optimizer return for cost and routing? | `model.sd_top_cap = Constraint(expr=model.x['san-diego', 'topeka'] <= 250)` | 154.575 |
| WHAT-IF/new_constraint | There's a proposal to keep Seattle firmly supplying New York — at least 200 loads on the Seattle-to-New York lane. Plug it in and walk me through the cost. | `model.sea_ny_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 200)` | 155.025 |
| WHAT-IF/new_constraint | We'd like San Diego to keep a foothold at Chicago for redundancy — at least 50 loads on that lane. Let's see the cost impact. | `model.sd_chi_floor = Constraint(expr=model.x['san-diego', 'chicago'] >= 50)` | 154.125 |
| WHY-NOT/constraint_rule | Seattle leaves Topeka totally untouched, which seems to waste a usable northern lane. Shouldn't Seattle be running at least 150 loads to Topeka? What's keeping the model from doing that? | `model.sea_top_floor = Constraint(expr=model.x['seattle', 'topeka'] >= 150)` | 159.975 |
| WHY-NOT/constraint_rule | San Diego does nothing for Chicago even though it has spare output. Shouldn't it cover at least 150 loads of the Chicago line for supply security? Walk me through what's pulling the plan the other way. | `model.sd_chi_floor150 = Constraint(expr=model.x['san-diego', 'chicago'] >= 150)` | 155.025 |

### ibm1_lp  (1)  — `testing_library/feas_test/ibm1_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Bin-5 inventory has been piling up in the yard cycle after cycle while the plan never touches it. Shouldn't we mandate at least 200 lb of bin-5 gets worked into the alloy so the stockpile doesn't keep growing? What's keeping the model from pulling it in? | `model.bin5_floor_200 = Constraint(expr=model.x['bin-5'] >= 200.0)` | 301.8537185003073 |

### icut_mip  (5)  — `testing_library/feas_test/icut_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating holding the first dial at 3 or higher this run. With that floor in place, what does the combined index read? | `model.x1_floor = Constraint(expr=model.x[1] >= 3)` | 3322.0 |
| WHAT-IF/new_constraint | Suppose the third position has to sit at 3 or above. Run it and tell me where the index lands. | `model.x3_floor = Constraint(expr=model.x[3] >= 3)` | 2332.0 |
| WHAT-IF/new_constraint | There's a proposal to push the last dial up to at least 3. What's the resulting combined reading? | `model.x4_floor = Constraint(expr=model.x[4] >= 3)` | 2323.0 |
| WHY-NOT/constraint_rule | The first dial is parked right at the bottom of its range. Couldn't we crank it all the way up to 4 for more margin? What's the setup protecting by keeping it pinned that low? | `model.want_x1_max = Constraint(expr=model.x[1] >= 4)` | 4322.0 |
| WHY-NOT/constraint_rule | The third dial could clearly go up to 4 — yet it's left at the floor. Wouldn't maxing it out be the natural call? What's keeping the optimizer from raising it? | `model.want_x3_max = Constraint(expr=model.x[3] >= 4)` | 2342.0 |

### imsl_lp  (3)  — `testing_library/feas_test/imsl_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to pin the leading approximation node a-00 exactly to zero, since the physical signal is known to start at the origin. We're evaluating whether forcing that anchor is worth it — what total deviation does the fit return with ym[a-00] held at 0? | `model.zero_start = Constraint(expr=model.ym['a-00'] == 0.0)` | 0.1321621666666667 |
| WHY-NOT/constraint_rule | The fit barely clears the measured peak, and I'm worried it's clipping the top of the signal. Couldn't we insist the peak approximation node a-05 reach at least 1.05 so the crest is properly captured? What's stopping the optimizer from sitting higher there? | `model.peak_floor = Constraint(expr=model.ym['a-05'] >= 1.05)` | 0.31493577777777815 |
| WHY-NOT/constraint_rule | The tail node a-10 is sitting almost flat at zero, which doesn't match where I'd expect the curve to still be carrying some signal. Shouldn't it hold at least 0.10? What's pulling the model down to nearly nothing there? | `model.tail_floor = Constraint(expr=model.ym['a-10'] >= 0.10)` | 0.4739016666666671 |

### indus89_lp  (8)  — `testing_library/feas_test/indus89_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at putting a ceiling on activity x4 — say it can't run above 20000 units. What does the optimizer return for total surplus under that cap? | `model.cap_x4 = Constraint(expr=model.x['x4'] <= 20000)` | 114328.3900912776 |
| WHAT-IF/new_constraint | If we held activity x1729 to no more than 15000, where would total surplus land? | `model.cap_x1729 = Constraint(expr=model.x['x1729'] <= 15000)` | 114684.31664684849 |
| WHAT-IF/new_constraint | Curious what happens if we throttle x797 down to 800 units — what total surplus does the model report? | `model.cap_x797 = Constraint(expr=model.x['x797'] <= 800)` | 114746.76068880473 |
| WHAT-IF/new_constraint | Say we restrict activity x829 to a maximum of 600 — what does total surplus come to under that limit? | `model.cap_x829 = Constraint(expr=model.x['x829'] <= 600)` | 114684.10258954653 |
| WHY-NOT/constraint_rule | Activity x8 is running over 7500 units, which looks like a lot of weight on one lever. Couldn't we hold it under 6000 and spread the plan out? What's the model seeing that makes it lean on x8 so hard? | `model.limit_x8 = Constraint(expr=model.x['x8'] <= 6000)` | 113939.89170739613 |
| WHY-NOT/constraint_rule | The plan pushes x6 past 7000 units. That concentration makes me nervous — shouldn't we cap it at 5500? What's the tradeoff the optimizer is making by running it that high? | `model.limit_x6 = Constraint(expr=model.x['x6'] <= 5500)` | 113800.36122116994 |
| WHY-NOT/constraint_rule | Activity x1213 is sitting pinned at its ceiling of 588. Shouldn't we deliberately back it off to 400 to leave ourselves some slack? What's steering the model to max it out? | `model.limit_x1213 = Constraint(expr=model.x['x1213'] <= 400)` | 114402.23326293347 |
| WHY-NOT/constraint_rule | We're running x1221 near 580 units and it feels overcommitted. Couldn't we just hold it to 450? What is the optimizer getting out of pushing it that hard? | `model.limit_x1221 = Constraint(expr=model.x['x1221'] <= 450)` | 114614.6652742319 |

### indus_lp  (2)  — `testing_library/feas_test/indus_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | The plan keeps poly-17+19's bullock numbers fairly lean. Shouldn't we be running at least 90 thousand bullocks there to cover the draft-power demand comfortably? What's the model seeing that makes it keep the herd that small? | `model.bullock_floor = Constraint(expr=model.animal['poly-17+19', 'bullock'] >= 90.0)` | 891.507022380124 |
| WHY-NOT/constraint_rule | poly-18 is leaning hard into cotton. Couldn't we dial that back and hold poly-18's cotton to no more than 80 thousand acres to rotate in something else? What's the tradeoff the model is making by pushing cotton there? | `model.cotton_p18_cap = Constraint(expr=model.xca['poly-18', 'cotton'] <= 80.0)` | 892.3750816640618 |

### job_mip  (5)  — `testing_library/feas_test/job_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The crew for Job 1 won't be available right at the start of the window — they can only begin on day 5 or later. We're evaluating that scenario; what total cost does the plan come out to if Job 1 can't start before day 5? | `model.j1_avail = Constraint(expr=model.s[1] >= 5)` | 13375.0 |
| WHAT-IF/new_constraint | Engineering is pitching a tighter spec on Job 5 — they want it completed in no more than 10 days. Let's try capping Job 5's duration at 10 and see what the optimizer returns for cost. | `model.j5_cap = Constraint(expr=model.t[5] <= 10)` | 13925.0 |
| WHY-NOT/constraint_rule | The plan runs Job 6 out to its full allowed length, which seems wasteful. Couldn't we just hold Job 6 to the minimum 12 days instead of dragging it on? What's keeping the model from doing that? | `model.j6_min = Constraint(expr=model.t[6] <= 12)` | 13700.0 |
| WHY-NOT/constraint_rule | Job 2 kicks off on the very first day, which crowds the early schedule. Wouldn't it be cleaner to delay Job 2's start to day 3? What's the model seeing that I'm not? | `model.j2_delay = Constraint(expr=model.s[2] >= 3)` | 13825.0 |
| WHY-NOT/constraint_rule | Job 4 is scheduled to take the full 20 days even though it could finish in 16, and that long block ties up the crew. Shouldn't we cap Job 4 at 16 days so Job 7 can start sooner? Walk me through what that's costing us. | `model.j4_cap = Constraint(expr=model.t[4] <= 16)` | 13375.0 |

### kand_lp  (5)  — `testing_library/feas_test/kand_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to keep the raw-1 stream active for supplier-relationship reasons — at least 10 units of raw-1 bought in the first period. Plug that in and walk me through the resulting cost. | `model.raw1_floor = Constraint(expr=model.x['raw-1', 'time-1'] >= 10)` | 2930.9999999999995 |
| WHAT-IF/new_constraint | Let's try a tank-turnover rule that holds second-period raw-2 purchasing to 20 units or fewer. What's the cost impact? | `model.raw2_t2_cap = Constraint(expr=model.x['raw-2', 'time-2'] <= 20)` | 2883.0 |
| WHY-NOT/constraint_rule | We're leaning hard on raw-2 in the first period. Shouldn't we hold first-period raw-2 buying to 10 units or under and lean on raw-1 instead? What's keeping the model from doing that? | `model.raw2_t1_cap = Constraint(expr=model.x['raw-2', 'time-1'] <= 10)` | 2870.999999999999 |
| WHY-NOT/constraint_rule | It seems risky to leave raw-1 out of the second period entirely. Shouldn't we keep at least 8 units of raw-1 flowing in time-2? Walk me through what's pulling the plan the other way. | `model.raw1_t2_floor = Constraint(expr=model.x['raw-1', 'time-2'] >= 8)` | 2822.5999999999995 |
| WHY-NOT/constraint_rule | Buying 20 units of raw-2 up front feels heavy on the first period. Couldn't we just hold first-period raw-2 to 15 and spread the rest out? What's the tradeoff I'm missing? | `model.raw2_t1_cap15 = Constraint(expr=model.x['raw-2', 'time-1'] <= 15)` | 2712.000000000001 |

### knapsack_mip  (7)  — `testing_library/feas_test/knapsack_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A sponsor wants their product, item i1, guaranteed a spot in the bag no matter what. If we force i1 into the load, what total profit does the optimizer come back with for the rest of the pack? | `model.must_take_i1 = Constraint(expr=model.x['i1'] == 1)` | 288.0 |
| WHAT-IF/new_constraint | We're curious what happens if item i6 is treated as a mandatory inclusion this run. Lock i6 in and let the model fill the rest — where does total profit land? | `model.must_take_i6 = Constraint(expr=model.x['i6'] == 1)` | 293.0 |
| WHAT-IF/new_constraint | Item i9 turns out to be unavailable from the supplier this cycle. If we take i9 off the table entirely and repack with what's left, what's the best total profit we can still manage? | `model.block_i9 = Constraint(expr=model.x['i9'] == 0)` | 260.0 |
| WHY-NOT/constraint_rule | Item i1 carries one of the bigger profit tags on the list, yet the plan just skips it. Shouldn't we be packing i1 instead of leaving that value on the shelf? What's the model seeing that makes dropping it the better call? | `model.why_i1 = Constraint(expr=model.x['i1'] >= 1)` | 288.0 |
| WHY-NOT/constraint_rule | Item i6 isn't exactly featherweight but it's hardly the worst on profit either, and the plan still leaves it out. Couldn't we just squeeze i6 in? What's pulling the optimizer away from taking it? | `model.why_i6 = Constraint(expr=model.x['i6'] >= 1)` | 293.0 |
| WHY-NOT/constraint_rule | Item i5 is one of the lightest things we've got — barely any weight at all. It seems almost free to throw in, so why does the plan leave it out? Shouldn't a near-weightless item always make the bag? | `model.why_i5 = Constraint(expr=model.x['i5'] >= 1)` | 294.0 |
| WHY-NOT/constraint_rule | There's a standing request to keep item i7 in our regular rotation, but the optimizer never picks it. Is there really no room for i7? What's the tradeoff the model is making by keeping it out? | `model.why_i7 = Constraint(expr=model.x['i7'] >= 1)` | 251.0 |

### knights_mip  (4)  — `testing_library/feas_test/knights_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to nail a knight down on the top-left corner, row 1 column 1. Lock that in and tell me whether the board still fills out to the same count and at what objective. | `model.pin_1_1 = Constraint(expr=model.x['1', '1'] == 1)` | 32.0 |
| WHAT-IF/new_constraint | Let's try keeping the central square at row 4, column 4 clear of any knight. Run it and see whether we still seat the full count, and at what objective. | `model.block_4_4 = Constraint(expr=model.x['4', '4'] == 0)` | 32.0 |
| WHY-NOT/constraint_rule | Square (1,2) sits there wide open right on the top edge. Shouldn't a knight just claim it? Why does the layout leave that one empty — what's it weighing? | `model.want_1_2 = Constraint(expr=model.x['1', '2'] == 1)` | 32.0 |
| WHY-NOT/constraint_rule | The left-edge square at row 4, column 1 looks like an easy, uncontested spot, yet the plan skips it. Couldn't we just anchor a knight there? What's the trade-off pulling the knight away from that square? | `model.want_4_1 = Constraint(expr=model.x['4', '1'] == 1)` | 32.0 |

### korpet_mip  (3)  — `testing_library/feas_test/korpet_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to seed a catalytic-cracking unit at Inchon early — build it in the very first expansion window (1985-89). Where does the total cost land if we commit to that? | `model.seed_cc = Constraint(expr=model.y['cc', 'inchon', '1985-89'] == 1)` | 171125159.1227246 |
| WHAT-IF/new_constraint | We're evaluating an early steam-cracker at Yosu — commit to building it in the 1985-89 window. What's the resulting total cost? | `model.seed_sc = Constraint(expr=model.y['sc', 'yosu', '1985-89'] == 1)` | 171023842.51316804 |
| WHY-NOT/constraint_rule | Inchon serves the Seoul market, which is huge — surely its crude unit should get a bigger early expansion. Shouldn't we add at least 2000 of crude-distillation capacity there in the first window? What's keeping the optimizer from investing more in Inchon up front? | `model.push_inchon = Constraint(expr=model.h['ad', 'inchon', '1985-89'] >= 2000)` | 170977487.53956577 |

### landing_mip  (2)  — `testing_library/feas_test/landing_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose a connecting-passenger transfer means aircraft 2 cannot be on the ground before time 12. Holding aircraft 2's landing to no earlier than 12, what happens to the delay bill? | `model.a2_hold = Constraint(expr=model.t[2] >= 12)` | 390.0 |
| WHY-NOT/constraint_rule | Aircraft 5 gets slotted in at the very front, but it's the costliest one to delay anyway — surely we could hold it back to at least time 10 without much harm? The model won't do that on its own, so what am I missing? | `model.a5_hold = Constraint(expr=model.t[5] >= 10)` | 450.0 |

### lands_det_lp  (3)  — `testing_library/feas_test/lands_det_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to keep plant-4 as a thin peaking asset rather than a baseload anchor - hold its installed capacity to at most 2 units. We're evaluating that ceiling now; what does the optimizer return for the build mix and total cost? | `model.plant4_cap = Constraint(expr=model.x['plant-4'] <= 2)` | 295.0 |
| WHY-NOT/constraint_rule | Plant-3 is one of the pricier units yet the plan loads three whole units of capacity onto it. Couldn't we hold plant-3 to at most 2 units and lean on the cheaper plants instead? What's keeping the model from trimming that expensive build down? | `model.plant3_trim = Constraint(expr=model.x['plant-3'] <= 2)` | 295.0 |
| WHY-NOT/constraint_rule | Plant-1 is one of our most flexible units but the plan only builds three units of it. Shouldn't we be standing up at least four units of plant-1 to keep more of the schedule on the flexible asset? What's keeping the model from leaning on it harder? | `model.plant1_floor = Constraint(expr=model.x['plant-1'] >= 4)` | 295.0 |

### lands_stoc_lp  (2)  — `testing_library/feas_test/lands_stoc_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to keep plant-3 as a thin specialty asset rather than a baseload anchor - hold its installed capacity to at most 2.5 units. We're evaluating that ceiling now; what does the optimizer return for the build mix and expected total cost? | `model.plant3_cap = Constraint(expr=model.x['plant-3'] <= 2.5)` | 383.20000000000005 |
| WHY-NOT/constraint_rule | Plant-1 is one of our most flexible units but the plan only builds two and two-thirds units of it. Shouldn't we be standing up at least three and a half units of plant-1 to keep more of the schedule on the flexible asset? What's keeping the model from leaning on it harder? | `model.plant1_floor = Constraint(expr=model.x['plant-1'] >= 3.5)` | 382.22555555555556 |

### latin_mip  (3)  — `testing_library/feas_test/latin_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to pin value 2 into the row-2, column-3 cell of the first square. Lock that in and tell me whether a valid filled-in pair still comes back, and at what objective. | `model.pin_one_v2_r2c3 = Constraint(expr=model.y['one', 'val2', 'row2', 'col3'] == 1)` | 32.0 |
| WHAT-IF/new_constraint | We're evaluating fixing value 3 into the bottom-right corner of the second square. Plug that in — does it still resolve, and what's the objective? | `model.pin_two_v3_r4c4 = Constraint(expr=model.y['two', 'val3', 'row4', 'col4'] == 1)` | 32.0 |
| WHAT-IF/new_constraint | We're weighing anchoring value 4 in the top-right cell of the first square. Add that and tell me whether it still solves and what the objective comes to. | `model.pin_one_v4_r1c4 = Constraint(expr=model.y['one', 'val4', 'row1', 'col4'] == 1)` | 32.0 |

### lop_mip  (7)  — `testing_library/feas_test/lop_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The Amsterdam-Sloterdijk-to-Utrecht line shares track with a freight slot that may get pulled. Let's look at the case where that line can't run at all — frequency held to zero — and the network has to meet the same edge requirements without it. What direct-traveler count comes out? | `model.drop_asd_ut = Constraint(expr=model.phi['Asd', 'Ut'] <= 0)` | 81298.0 |
| WHAT-IF/new_constraint | There's interest in guaranteeing the Arnhem-to-Schiphol line is part of the timetable for connectivity. If we require that line to run at least once a cycle, where does the network's direct-traveler total land? | `model.run_ah_shl = Constraint(expr=model.phi['Ah', 'Shl'] >= 1)` | 80705.0 |
| WHAT-IF/new_constraint | The Utrecht-to-Amsterdam-Sloterdijk-Zuid corridor is carrying a huge share of the direct ridership and we want to understand the network if it's deliberately rationed. Cap the direct travelers on that pair at 3000 and let the optimizer rebalance — what's the resulting system-wide direct-traveler count? | `model.cap_ut_asdz = Constraint(expr=model.dt['Ut', 'Asdz'] <= 3000)` | 78693.0 |
| WHY-NOT/constraint_rule | There's a candidate line straight from Arnhem to Amsterdam-Sloterdijk-Zuid, yet the plan leaves it switched off entirely. Shouldn't we at least run it once to give that corridor a direct service? What's the model seeing that makes keeping it dark the better call? | `model.force_ah_asdz = Constraint(expr=model.phi['Ah', 'Asdz'] >= 1)` | 81419.0 |
| WHY-NOT/constraint_rule | The Groningen-to-Rotterdam line eats a frequency slot but it's a long haul — couldn't we just drop it and serve those edges with shorter lines? If we hold that line to zero, does the plan really come out worse, and by how much? | `model.ban_gn_rtd = Constraint(expr=model.phi['Gn', 'Rtd'] <= 0)` | 81423.0 |
| WHY-NOT/constraint_rule | Lelystad gets no direct line in the plan even though there's an Arnhem-to-Lelystad candidate sitting unused. Couldn't we just run that line once and give Lelystad a one-seat ride? What's the tradeoff the optimizer is making by leaving it idle? | `model.force_ah_lls = Constraint(expr=model.phi['Ah', 'Lls'] >= 1)` | 81332.0 |
| WHY-NOT/constraint_rule | The Schiphol-Amsterdam-Sloterdijk pair is grabbing the lion's share of direct travelers, which feels lopsided. Shouldn't we hold it back a bit — say no more than 4000 direct riders on that single pair — and spread the benefit around? What's the optimizer telling us about doing that? | `model.cap_shl_asd = Constraint(expr=model.dt['Shl', 'Asd'] <= 4000)` | 79050.0 |

### lrs_mip  (7)  — `testing_library/feas_test/lrs_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're testing how locked-in the lead bit is — suppose the recurrence has to start with k(1) switched off instead of on. What disagreement count does the optimizer come back with? | `model.flip_k1 = Constraint(expr=model.k[1] == 0)` | 115.0 |
| WHAT-IF/new_constraint | Let's look at the case where seed bit k(3) is held at zero. What does that do to the fit quality? | `model.fix_k3 = Constraint(expr=model.k[3] == 0)` | 115.0 |
| WHAT-IF/new_constraint | Suppose we require seed bit k(4) to be switched on. Where does the disagreement count settle? | `model.set_k4 = Constraint(expr=model.k[4] == 1)` | 114.0 |
| WHAT-IF/new_constraint | What if seed bit k(8) is pinned off? How does the fit hold up? | `model.fix_k8 = Constraint(expr=model.k[8] == 0)` | 112.0 |
| WHY-NOT/constraint_rule | The fit keeps seed bit k(2) on. Wouldn't it be cleaner to start it at zero? What's the recurrence seeing that makes k(2)=1 worth it? | `model.why_k2 = Constraint(expr=model.k[2] == 0)` | 112.0 |
| WHY-NOT/constraint_rule | Seed bit k(5) comes back off. Shouldn't we be switching it on instead? What's the tradeoff the fit is making by leaving it at zero? | `model.why_k5 = Constraint(expr=model.k[5] == 1)` | 112.0 |
| WHY-NOT/constraint_rule | Is there a reason k(10) stays on? Couldn't we just hold it at zero and still track the signal? What's keeping the optimizer from doing that? | `model.why_k10 = Constraint(expr=model.k[10] == 0)` | 113.0 |

### macro_lp  (8)  — `testing_library/feas_test/macro_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Sales has a standing order they want us to honor — at least 5 units of regular gasoline. Let's see what committing to that does to income. | `model.regular_order = Constraint(expr=model.x['regular'] >= 5)` | 0.8395594252926024 |
| WHAT-IF/new_constraint | There's a proposal to diversify the slate and stop over-producing premium — cap premium at 35 units. What does the optimizer return for income? | `model.premium_cap = Constraint(expr=model.x['premium'] <= 35)` | 5.451583970101895 |
| WHAT-IF/new_constraint | Supply is pushing us to take some West Texas crude for relationship reasons. If we commit to buying at least 20 barrels of it, how does income shift? | `model.wtex_min = Constraint(expr=model.u['w-tex'] >= 20)` | -22.652149433078034 |
| WHAT-IF/new_constraint | We're weighing a distillate supply contract that would oblige us to make at least 5 units of distillate. Run it and tell me the income impact. | `model.distillate_min = Constraint(expr=model.x['distillate'] >= 5)` | -13.937407883824886 |
| WHY-NOT/constraint_rule | Fuel oil margins look fine to me, yet the plan caps it around 37. Shouldn't we be pushing fuel oil to at least 40? What's the model seeing that I'm not? | `model.fueloil_floor = Constraint(expr=model.x['fuel-oil'] >= 40)` | -1.4325875374714343 |
| WHY-NOT/constraint_rule | We seem to be dumping a lot into fuel gas. Wouldn't it be smarter to hold fuel gas to 5 units and redirect that material? What's pulling the plan the other way? | `model.fuelgas_cap = Constraint(expr=model.x['fuel-gas'] <= 5)` | 4.3785907651248746 |
| WHY-NOT/constraint_rule | Leaning this hard on premium feels risky for the slate. Couldn't we hold premium to 40 and still do fine? Walk me through the tradeoff the optimizer is making. | `model.premium_cap40 = Constraint(expr=model.x['premium'] <= 40)` | 6.230381680116615 |
| WHY-NOT/constraint_rule | The plan buys zero West Texas crude. Is there really a reason we couldn't take at least 30 barrels of it to balance our supply? What's the tradeoff I'm missing? | `model.wtex_floor = Constraint(expr=model.u['w-tex'] >= 30)` | -37.272434887957914 |

### magic_mip  (5)  — `testing_library/feas_test/magic_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Grid operators want firmer big-unit coverage at the peak — let's see the cost if we commit at least 3 type-3 units in the 3pm-6pm block. | `model.t3_peak = Constraint(expr=model.n['type-3', '3pm-6pm'] >= 3)` | 989040.0 |
| WHAT-IF/new_constraint | Engineering wants to test a per-unit-type output ceiling in the peak. If type-1 output in the 3pm-6pm block is held to 15, what's the resulting cost? | `model.t1_peak_cap = Constraint(expr=model.x['type-1', '3pm-6pm'] <= 15)` | 990290.0 |
| WHY-NOT/constraint_rule | We're running all twelve type-1 units overnight when demand is lowest. Shouldn't we be able to shut type-1 down entirely in the 12pm-6am block? What's keeping the model from doing that? | `model.no_t1_overnight = Constraint(expr=model.n['type-1', '12pm-6am'] <= 0)` | 1050650.0 |
| WHY-NOT/constraint_rule | Starting up the big type-3 units for the afternoon peak looks expensive. Couldn't we just avoid any type-3 startups in the 3pm-6pm block? Walk me through what that costs us. | `model.no_t3_startup = Constraint(expr=model.s['type-3', '3pm-6pm'] <= 0)` | 992680.0 |
| WHY-NOT/constraint_rule | Type-2 output in the afternoon peak looks high to me. Wouldn't it be better to hold type-2 production in the 3pm-6pm block to 10? What's the model seeing that I'm not? | `model.t2_peak_out = Constraint(expr=model.x['type-2', '3pm-6pm'] <= 10)` | 994840.0 |

### maintenance_mip  (3)  — `testing_library/feas_test/maintenance_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A vendor can only mobilize a crew for a month-20 outage, and the board wants to lock that visit in regardless. We're looking at committing to a shutdown in month 20 — what does that do to the total cost? | `model.fix_m20 = Constraint(expr=model.o[20] >= 1)` | 36070.0 |
| WHAT-IF/new_constraint | There's talk of a mandatory commissioning outage right at the start, in month 1, before the line is fully handed over. Let's try forcing a shutdown in month 1 and see what the optimizer reports for total cost. | `model.fix_m1 = Constraint(expr=model.o[1] >= 1)` | 36870.0 |
| WHY-NOT/constraint_rule | The plant sits idle of any outage right at the front of the year and then we scramble in month 4. Shouldn't we just take it down in month 2 and get ahead of the early maintenance? What's keeping the model from making that move? | `model.outage_m2 = Constraint(expr=model.o[2] == 1)` | 36620.0 |

### marilyn_mip  (7)  — `testing_library/feas_test/marilyn_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're curious how the puzzle reshuffles if the busiest circle isn't allowed to hold the very smallest digit. Suppose we require circle c3 to carry at least a 2 — what does the optimizer report back for the digit total? | `model.c3_floor = Constraint(expr=model.x['c3'] >= 2)` | 36.0 |
| WHAT-IF/new_constraint | Let's look at a layout where a corner circle pulls some weight: if we make circle c8 take a digit of 5 or more, does a valid placement still exist, and what's the resulting sum of digits? | `model.c8_high = Constraint(expr=model.x['c8'] >= 5)` | 36.0 |
| WHAT-IF/new_constraint | Suppose the central circle c6 is barred from taking either of the top digits and must stay at 6 or below. What total does the optimizer come back with for that scenario? | `model.c6_cap = Constraint(expr=model.x['c6'] <= 6)` | 36.0 |
| WHAT-IF/new_constraint | Here's a placement we'd like to pin down: route the digit 5 specifically into circle c2 by switching its assignment indicator on. Does the puzzle still solve, and what's the digit total? | `model.c2_takes5 = Constraint(expr=model.y['c2', 'c5'] == 1)` | 36.0 |
| WHY-NOT/constraint_rule | It bugs me that the most-connected circle c3 gets handed the smallest possible digit. That seems backwards for the hub of the whole layout — shouldn't c3 carry something more substantial, say a 4 or higher? What is the model seeing that makes parking the 1 there the right call? | `model.c3_substantial = Constraint(expr=model.x['c3'] >= 4)` | 36.0 |
| WHY-NOT/constraint_rule | Circle c1 sits out on the edge with only three neighbors, yet the plan loads it up with a 7. Couldn't we keep the big numbers toward the middle and hold c1 down to a 3 or less instead? What's pulling the optimizer toward putting a high digit on that corner? | `model.c1_low = Constraint(expr=model.x['c1'] <= 3)` | 36.0 |
| WHY-NOT/constraint_rule | I don't see why the central circle c6 has to be the one holding the 8. Wouldn't it be tidier to keep the top digit off the busiest node and cap c6 at 4? What's the tradeoff the model is making by maxing out that central circle? | `model.c6_modest = Constraint(expr=model.x['c6'] <= 4)` | 36.0 |

### mexls_lp  (6)  — `testing_library/feas_test/mexls_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Logistics wants to test easing the load on the ahmsa-to-capital plate lane — limit ahmsa's plate shipments into mexico-df to 400 thousand tons. What's the cost picture? | `model.plate_lane_cap = Constraint(expr=model.xf['plate', 'ahmsa', 'mexico-df'] <= 400)` | 27583.97226364958 |
| WHAT-IF/new_constraint | We're considering throttling the tamsa-to-puebla seamless lane to free up rail slots — cap that shipment at 150 thousand tons. What does the optimizer return for total cost? | `model.seamless_lane_cap = Constraint(expr=model.xf['seamless', 'tamsa', 'puebla'] <= 150)` | 27571.50778914958 |
| WHY-NOT/constraint_rule | ahmsa's blast-furnace-to-pellet route is carrying an awful lot of the iron-making load. Shouldn't we ease off and keep that pig-from-pellet process under 1000? What's the model seeing that makes it push that unit so hard? | `model.ahmsa_pigpel_cap = Constraint(expr=model.zs['pig-pel', 'ahmsa'] <= 1000)` | 27777.438406532965 |
| WHY-NOT/constraint_rule | sicartsa's continuous billet caster is running hot. Couldn't we throttle it back to 450 and lean on the other mills? What's the tradeoff the optimizer is weighing here? | `model.sicartsa_billet_cap = Constraint(expr=model.zs['billets-cc', 'sicartsa'] <= 450)` | 28370.04902137974 |
| WHY-NOT/constraint_rule | sicartsa sits right on the coast — wouldn't it make sense to push at least 30 thousand tons of its wire into the export market? Why does the plan hold its wire exports down the way it does? | `model.sicartsa_wire_export = Constraint(expr=model.e['wire', 'sicartsa'] >= 30)` | 27571.02322368115 |
| WHY-NOT/constraint_rule | ahmsa is the closest big mill to monterrey, so intuitively it should cover a good chunk of monterrey's plate. Shouldn't ahmsa be shipping at least 180 thousand tons of plate up there? What's pulling the plan another way? | `model.ahmsa_plate_mty = Constraint(expr=model.xf['plate', 'ahmsa', 'monterrey'] >= 180)` | 27574.09588964958 |

### mexsd_mip  (5)  — `testing_library/feas_test/mexsd_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating putting a blast furnace into Ahmsa right away in 1984-86. Add that and tell me the total cost. | `model.force_bf_ahmsa = Constraint(expr=model.y['blast-furn', 'ahmsa', '1984-86'] == 1)` | 12894.608223205089 |
| WHAT-IF/new_constraint | Suppose we stand up an electric-arc furnace at Hylsa in 1984-86. What does the optimizer return for total cost? | `model.force_ea_hylsa = Constraint(expr=model.y['elec-arc', 'hylsa', '1984-86'] == 1)` | 12858.905439406328 |
| WHAT-IF/new_constraint | Let's try giving Hylsa a BOF in 1987-89 and see where the total program cost lands. | `model.force_bof_hylsa = Constraint(expr=model.y['bof', 'hylsa', '1987-89'] == 1)` | 12865.67216936481 |
| WHY-NOT/constraint_rule | The plan sinks its very first capital into a direct-reduction unit at Sicartsa back in 1984-86. That feels premature — shouldn't we hold off on that one? What's the model seeing that makes it build there so early? | `model.skip_dr_sicartsa = Constraint(expr=model.y['direct-red', 'sicartsa', '1984-86'] == 0)` | 12984.597953700684 |
| WHY-NOT/constraint_rule | Sicartsa already has plenty, yet the plan still slots in another BOF there in 1990-92. Why double down on that site again? Couldn't we just drop that one? What's keeping the optimizer on it? | `model.skip_bof_sicartsa = Constraint(expr=model.y['bof', 'sicartsa', '1990-92'] == 0)` | 12866.22604989154 |

### mexss_lp  (2)  — `testing_library/feas_test/mexss_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | ahmsa's blast furnace is doing an awful lot of the heavy lifting on pig iron. Shouldn't we ease off and keep it under 2.5 mill tons? What's the model seeing that makes it push that unit so hard? | `model.ahmsa_pigiron_cap = Constraint(expr=model.z['pig-iron', 'ahmsa'] <= 2.5)` | 581.937954172958 |
| WHY-NOT/constraint_rule | sicartsa sits on the coast not far from the north — wouldn't it make sense for it to cover at least a full mill ton of monterrey's steel? Why does the plan route monterrey the way it does instead? | `model.sicartsa_serves_mty = Constraint(expr=model.x['steel', 'sicartsa', 'monterrey'] >= 1.0)` | 556.0343638778572 |

### mrp2_mip  (6)  — `testing_library/feas_test/mrp2_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're considering keeping a finished-goods cushion for the late surge by carving out a dedicated AJ8172 run in the last bucket. Suppose we require at least 50 AJ8172 units to be built in t8 — what does the optimizer return for the weighted production total? | `model.aj_t8_run = Constraint(expr=model.x['AJ8172', 't8'] >= 50)` | 7400.0 |
| WHAT-IF/new_constraint | Procurement is floating the idea of pulling the LQ8811 sub-assembly build a period earlier so the line isn't idle at the start. If we have LQ8811 fire its setup in t2, what total does the model come back with? | `model.lq_t2_setup = Constraint(expr=model.d['LQ8811', 't2'] >= 1)` | 7600.0 |
| WHAT-IF/new_constraint | Let's look at the case where the line has to start AJ8172 right out of the gate — say at least 20 finished units built in t1 to get ahead of the early orders. What's the resulting weighted production figure? | `model.aj_t1_start = Constraint(expr=model.x['AJ8172', 't1'] >= 20)` | 7000.0 |
| WHY-NOT/constraint_rule | The plan leaves AJ8172 dark through the middle of the run and then crams a batch into t6. Wouldn't it be steadier to have a build going in t5 as well? Force a setup there and tell me what the model is seeing that makes it avoid that. | `model.aj_t5_setup = Constraint(expr=model.d['AJ8172', 't5'] >= 1)` | 7800.0 |
| WHY-NOT/constraint_rule | RN0098 doesn't get touched until t2, but we've got the line free in t1. Shouldn't we just kick its production off in the first period instead of waiting? Force an RN0098 setup in t1 and explain what the model gives up by doing that. | `model.rn_t1_setup = Constraint(expr=model.d['RN0098', 't1'] >= 1)` | 6900.0 |
| WHY-NOT/constraint_rule | I'd rather we got the full RN0098 lot down in the very first period to de-risk the downstream builds. Put at least 100 units of RN0098 into t1 production and tell me what the model is trading off by holding it back. | `model.rn_t1_lot = Constraint(expr=model.x['RN0098', 't1'] >= 100)` | 6900.0 |

### msm_lp  (3)  — `testing_library/feas_test/msm_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The rail siding at the Taza center can only handle so much. We're looking at a limit of 15 tons loaded onto rail there — what does the model say total cost becomes? | `model.taza_rail_cap = Constraint(expr=model.y['taza', 'rail'] <= 15.0)` | 3971.979999999997 |
| WHY-NOT/constraint_rule | The plan leans hard on rail out of Oued-Zem, but that siding has been unreliable. Couldn't we just keep Oued-Zem entirely on road and skip rail loading there? What's the model seeing that makes it want rail at that center? | `model.oz_no_rail = Constraint(expr=model.y['oued-zem', 'rail'] <= 0.0)` | 3972.5849999999973 |
| WHY-NOT/constraint_rule | Safi barely touches road haulage in the plan. Our road partner there needs the work — shouldn't we push at least 15 tons of Safi's volume onto road? What's the tradeoff the optimizer is making by keeping it so low? | `model.safi_road_floor = Constraint(expr=model.y['safi', 'road'] >= 15.0)` | 3967.979999999997 |

### multipleMB_mip  (6)  — `testing_library/feas_test/multipleMB_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a downstream handoff that means job G can't begin before time 15. Let's see what holding G's start to no earlier than 15 does to the schedule length. | `model.g_late = Constraint(expr=model.start['G'] >= 15)` | 17.0 |
| WHAT-IF/new_constraint | Planning wants job B to finish well ahead of its due date for a buffer — require at least 10 units of earliness on B. How does the schedule respond? | `model.b_buffer = Constraint(expr=model.early['B'] >= 10)` | 16.0 |
| WHAT-IF/new_constraint | We're considering dedicating job F to machine B for tooling reasons. If F must run on machine B, what's the resulting makespan? | `model.f_on_b = Constraint(expr=model.z['F', 'B'] >= 1)` | 15.0 |
| WHY-NOT/constraint_rule | Job B kicks off pretty early in the plan. Shouldn't we be able to delay B's start to at least time 10 without hurting anything? What's keeping the model from doing that? | `model.b_delay = Constraint(expr=model.start['B'] >= 10)` | 17.0 |
| WHY-NOT/constraint_rule | Job F sits idle until quite late in the schedule. Couldn't we just start F by time 10 at the latest? What's the model seeing that I'm not? | `model.f_early = Constraint(expr=model.start['F'] <= 10)` | 17.0 |
| WHY-NOT/constraint_rule | On the shared machine the plan runs job A ahead of job B. Is there a reason we couldn't flip that and let B go first? Walk me through what that ordering costs. | `model.flip_ab = Constraint(expr=model.y['A', 'B'] <= 0)` | 15.0 |

### mws_mip  (6)  — `testing_library/feas_test/mws_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The transport team thinks out-of-vehicle time is being underweighted. We're evaluating pinning its coefficient to at least 1.5 — what does the classification count come back as under that floor? | `model.dovtt_floor = Constraint(expr=model.beta['DOVTT'] >= 1.5)` | 764.0 |
| WHAT-IF/new_constraint | There's a proposal to drop in-vehicle travel time from the specification entirely — force beta[DIVTT] to zero. How many households can the trimmed model still classify correctly? | `model.drop_divtt = Constraint(expr=model.beta['DIVTT'] == 0)` | 763.0 |
| WHAT-IF/new_constraint | Household 3 is a case we have ground-truth on and want the model to get right. If we require z[3] to be classified correctly, what does that do to the overall score? | `model.pin_h3 = Constraint(expr=model.z[3] == 1)` | 752.0 |
| WHY-NOT/constraint_rule | That car-ownership coefficient of about 3.66 looks like it's dominating the whole score. Shouldn't a sensible fit keep beta[CARS] down to 3 or under? What's the estimator seeing that makes it lean so hard on car ownership? | `model.cap_cars = Constraint(expr=model.beta['CARS'] <= 3.0)` | 764.0 |
| WHY-NOT/constraint_rule | Household 10 looks like an easy call, yet the fit leaves it on the wrong side. Shouldn't the model just classify z[10] correctly? What's the trade-off pulling it the other way? | `model.want_h10 = Constraint(expr=model.z[10] == 1)` | 758.0 |
| WHY-NOT/constraint_rule | Out-of-vehicle time feels like it should weigh more heavily on mode choice than the fit gives it. Wouldn't it be obvious to push beta[DOVTT] up to at least 2? What's keeping the estimator from valuing it that much? | `model.push_dovtt = Constraint(expr=model.beta['DOVTT'] >= 2.0)` | 763.0 |

### nebrazil_lp  (8)  — `testing_library/feas_test/nebrazil_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're considering a ceiling on the heaviest activity in the plan — holding variable x[350] to no more than 120000 units. What does the optimizer return for total surplus under that cap? | `model.cap_x350 = Constraint(expr=model.x[350] <= 120000)` | 7569.39673735677 |
| WHAT-IF/new_constraint | Say we add a side limit holding activity x[384] to at most 80000. We're just curious where the plan's surplus comes out with that in place. | `model.cap_x384 = Constraint(expr=model.x[384] <= 80000)` | 7566.826116033713 |
| WHAT-IF/new_constraint | We'd like to see what happens if activity x[378] is restricted to 70000 or below. What total surplus does the model report then? | `model.cap_x378 = Constraint(expr=model.x[378] <= 70000)` | 7562.008352742679 |
| WHAT-IF/new_constraint | Looking at a throttle on variable x[360] — capping it at 60000. Where does farm income settle if we run with that restriction? | `model.cap_x360 = Constraint(expr=model.x[360] <= 60000)` | 7574.821798540314 |
| WHY-NOT/constraint_rule | That x[352] activity is barely being used — shouldn't we be leaning on it a lot harder, say running it at least 120000? What is the model seeing that keeps it dialed back? | `model.floor_x352 = Constraint(expr=model.x[352] >= 120000)` | 7570.62819144948 |
| WHY-NOT/constraint_rule | Couldn't we just push variable x[388] up to 80000 at minimum? It looks underworked in the plan. What's the tradeoff the optimizer is making by holding it lower? | `model.floor_x388 = Constraint(expr=model.x[388] >= 80000)` | 7576.188974401748 |
| WHY-NOT/constraint_rule | The accounting activity x[400] sits at a modest level — shouldn't it be carrying at least 800? Pin it there and show me what the plan gives up, because I don't see why it stays so low. | `model.floor_x400 = Constraint(expr=model.x[400] >= 800)` | 7547.4291478754185 |
| WHY-NOT/constraint_rule | I'd have expected variable x[401] to carry more weight — why not require it to hit at least 300? What's the model trading off by keeping it where it is? | `model.floor_x401 = Constraint(expr=model.x[401] >= 300)` | 7509.784786424028 |

### netgen_lp  (6)  — `testing_library/feas_test/netgen_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We want to test de-risking hub 34's reliance on the 23-34 trunk — hold that single lane to 20000 units and see the cost impact. | `model.trunk_2334 = Constraint(expr=model.x[23, 34] <= 20000)` | 14292987.0 |
| WHAT-IF/new_constraint | If we limited the 21-to-29 lane to 5000 units to spread the load, what would the routing cost come to? | `model.lane_2129 = Constraint(expr=model.x[21, 29] <= 5000)` | 14309591.0 |
| WHY-NOT/constraint_rule | Node 25 sits right next to sink 50 yet the plan never uses that direct lane. Shouldn't we route at least 2000 units straight from 25 to 50? What's steering the model away from it? | `model.serve_2550 = Constraint(expr=model.x[25, 50] >= 2000)` | 14295471.0 |
| WHY-NOT/constraint_rule | The plan piles over 10000 units onto the 21-47 lane — that feels like too many eggs in one basket. Couldn't we hold it under 6000? What is the optimizer seeing that makes it lean on that lane so hard? | `model.cap_2147 = Constraint(expr=model.x[21, 47] <= 6000)` | 14267059.0 |
| WHY-NOT/constraint_rule | Node 7 has a huge supply and a clean line to hub 49, so shouldn't it be carrying at least 18000 units on the 7-49 lane? Why is the plan holding it lower than that? | `model.push_749 = Constraint(expr=model.x[7, 49] >= 18000)` | 14309447.0 |
| WHY-NOT/constraint_rule | The 23-34 trunk is carrying an enormous share of hub 34's intake. That concentration worries me — shouldn't we trim it to 22000 and lean on other routes? What's pulling the model toward overusing it? | `model.trim_2334 = Constraint(expr=model.x[23, 34] <= 22000)` | 14248096.0 |

### nonsharp_mip  (8)  — `testing_library/feas_test/nonsharp_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating committing to the second candidate column — pin col-2 into the build. What master cost does the optimizer return for that configuration? | `model.build_col2 = Constraint(expr=model.y['col-2'] == 1)` | 1.4126401296929427 |
| WHAT-IF/new_constraint | There's a proposal to hold the master bound to at least 1.0 as a hurdle for the synthesis. What does mu come back as under that floor? | `model.hurdle = Constraint(expr=model.mu >= 1.0)` | 1.0 |
| WHAT-IF/new_constraint | Let's see what happens if the master estimate is required to clear 1.5 before we accept the design. What master value results? | `model.hurdle = Constraint(expr=model.mu >= 1.5)` | 1.5 |
| WHAT-IF/new_constraint | Suppose the design review insists the master bound sit at 2.0 or above. What does the optimizer report for mu? | `model.hurdle = Constraint(expr=model.mu >= 2.0)` | 2.0 |
| WHY-NOT/constraint_rule | The master bound comes in under 1.1, which feels optimistic given the subproblem costs. Shouldn't mu be sitting at 1.1 at the very least? What's keeping the optimizer that low? | `model.why_mu11 = Constraint(expr=model.mu >= 1.1)` | 1.1 |
| WHY-NOT/constraint_rule | Couldn't we just insist the master estimate hold at 1.2 or better? What's the tradeoff the model is making by letting mu drop below that? | `model.why_mu12 = Constraint(expr=model.mu >= 1.2)` | 1.2 |
| WHY-NOT/constraint_rule | Is there a reason the synthesis doesn't carry the master bound up to 1.6? Wouldn't a sturdier 1.6 floor be the safer call here? | `model.why_mu16 = Constraint(expr=model.mu >= 1.6)` | 1.6 |
| WHY-NOT/constraint_rule | Wouldn't it be more defensible to require the master bound to clear 1.8? What's pulling the optimizer to settle so much lower than that? | `model.why_mu18 = Constraint(expr=model.mu >= 1.8)` | 1.8 |

### nurses_mip  (1)  — `testing_library/feas_test/nurses_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The board is pitching a richer coverage target for the week — they want the roster to land at least 345 total shift assignments. Run it and let me see the resulting cost. | `model.coverage_target = Constraint(expr=model.totalAssignments >= 345)` | 53556.0 |

### openpit_mip  (3)  — `testing_library/feas_test/openpit_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Pit p1 sits idle in the opening period under the current plan. We're curious what it costs to get it producing right away — say we make p1 put out at least 5 units in t1. What total discounted income does the model report? | `model.p1_early = Constraint(expr=model.pout['p1', 't1'] >= 5)` | 52.10101565018757 |
| WHY-NOT/constraint_rule | The plan dumps pit p4 entirely in the first two periods and then walks away from it. That feels lopsided — shouldn't p4 keep some output going into period t3, say at least 5 units, rather than going dark? What's pulling the optimizer toward front-loading it so hard? | `model.why_p4_t3 = Constraint(expr=model.pout['p4', 't3'] >= 5)` | 51.43596239559823 |
| WHY-NOT/constraint_rule | I don't get why pit p1 just sits there in period t1 doing nothing while we're scrambling to meet demand. Shouldn't it be pulling its weight from the start — couldn't we have it produce at least 8 units in t1? What's the model's reasoning for keeping it parked early? | `model.why_p1_t1 = Constraint(expr=model.pout['p1', 't1'] >= 8)` | 51.00874684420462 |

### pak_lp  (2)  — `testing_library/feas_test/pak_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The IMF mission is rolling out an aid-dependency cap — total discounted foreign aid `fb` over the planning horizon should not exceed 10 billion rupees, so the country isn't leaning on capital inflows for the whole growth path. How does that aid-dependency cap reshape the development plan and the total welfare? | `model.aid_cap = Constraint(expr=model.fb <= 10.0)` | 913.119392607074 |
| WHAT-IF/new_constraint | We're evaluating an import-restraint target for the terminal year to protect reserves — keep traditional imports `m[1985]` at or below 24. How does holding 1985 imports under that line affect the welfare the plan achieves? | `model.import_cap_1985 = Constraint(expr=model.m[1985] <= 24.0)` | 1069.9075932009769 |

### pdi_lp  (8)  — `testing_library/feas_test/pdi_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Sales thinks zone 1 is overserved relative to margin — let's see what happens to profit if we hold zone 1's demand to 2000. | `model.z1_cap = Constraint(expr=model.dm[1] <= 2000)` | 281870.0 |
| WHAT-IF/new_constraint | We're considering throttling facility 'one' in January for a maintenance window — hold its normal production to 4000. What does the optimizer return for profit? | `model.one_jan_cap = Constraint(expr=model.pn['one', 'january'] <= 4000)` | 285123.333333333 |
| WHAT-IF/new_constraint | There's a proposal to pre-run some overtime at facility 'one' in January — require at least 100 units of overtime there. How does profit shift? | `model.one_jan_ot = Constraint(expr=model.po['one', 'january'] >= 100)` | 293575.0 |
| WHAT-IF/new_constraint | Marketing wants a stronger push into zone 5 — guarantee we serve at least 2900 there. Run it and tell me the profit impact. | `model.z5_push = Constraint(expr=model.dm[5] >= 2900)` | 293830.0 |
| WHY-NOT/constraint_rule | Zone 2 barely gets served in this plan. Shouldn't we be pushing at least 1000 units of demand there? What's keeping the model from doing that? | `model.z2_floor = Constraint(expr=model.dm[2] >= 1000)` | 293770.0 |
| WHY-NOT/constraint_rule | The south center carries almost no buffer into April. Wouldn't it be safer to keep at least 400 units of storage there at month end? Walk me through the tradeoff. | `model.south_buffer = Constraint(expr=model.s['south', 'april'] >= 400)` | 282360.0 |
| WHY-NOT/constraint_rule | Zone 4 looks over-served to me given the freight involved. Is there a reason we couldn't hold zone 4 demand to 1500? What's the model seeing that I'm not? | `model.z4_cap = Constraint(expr=model.dm[4] <= 1500)` | 285790.0 |
| WHY-NOT/constraint_rule | The east center runs lean through February. Couldn't we just hold at least 500 units of storage there that month for resilience? What's pulling the plan the other way? | `model.east_feb = Constraint(expr=model.s['east', 'february'] >= 500)` | 292080.0 |

### pg_mip  (3)  — `testing_library/feas_test/pg_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Grid code may limit how much solar we can inject at the midday solar peak. There's a proposal to hold PV output at hour 13 to no more than 50. What's the new total cost? | `model.pv13_cap = Constraint(expr=model.pv[13] <= 50)` | 2083.5 |
| WHY-NOT/constraint_rule | The fuel cell is the priciest source we run, yet it's pinned at full output during the hour-21 peak. Couldn't we just keep the fuel cell off at hour 21 and lean on the cheaper sources? What's keeping the model from doing that? | `model.no_fuel_21 = Constraint(expr=model.fuel[21] <= 0)` | 2111.5 |
| WHY-NOT/constraint_rule | We're running wind flat-out at 190 during hour 20, which strains the turbines. Shouldn't we be able to hold hour-20 wind output to 150 and still get by? What's pulling it the other way? | `model.wind20_cap = Constraint(expr=model.wind[20] <= 150)` | 2083.5 |

### phosdis_lp  (7)  — `testing_library/feas_test/phosdis_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose congestion limits how much routing we can funnel out of yucatan-ch toward s-gibraltr — say no more than 10 units of downstream flow on that leg. What does the optimizer return for the total route length under that ceiling? | `model.cap_sgib = Constraint(expr=model.x['yucatan-ch', 'yucatan-ch', 's-gibraltr'] <= 10.0)` | 965569.0 |
| WHAT-IF/new_constraint | We're looking at a scenario where veracruz must push at least 30 units of its routing directly onto the panama arc, to keep that lane busy. What total distance does the model come back with? | `model.force_vp = Constraint(expr=model.x['veracruz', 'veracruz', 'panama'] >= 30.0)` | 962055.0 |
| WHAT-IF/new_constraint | If we set a floor on the overall mileage budget at 980000 nautical miles — say to reflect a guaranteed-minimum-haul contract — what total route length does the optimizer settle on? | `model.cost_floor = Constraint(expr=model.cost >= 980000.0)` | 980000.0 |
| WHY-NOT/constraint_rule | The plan dumps 27 units of yucatan-ch's tree onto the single s-gibraltr leg — that feels like everything is being shoved through one chokepoint. Couldn't we hold that arc to 10 at most? What's the model seeing that makes it lean on that one leg so hard? | `model.cr_sgib = Constraint(expr=model.x['yucatan-ch', 'yucatan-ch', 's-gibraltr'] <= 10.0)` | 965569.0 |
| WHY-NOT/constraint_rule | More than half of veracruz's routing — 54 units — runs first through yucatan-ch. Shouldn't we spread it out and cap that hand-off at 20? What's the tradeoff that's pushing so much through that single hop? | `model.cr_vy = Constraint(expr=model.x['veracruz', 'veracruz', 'yucatan-ch'] <= 20.0)` | 970282.0 |
| WHY-NOT/constraint_rule | Why route 6 units of yucatan-ch's tree out through tampa at all — couldn't we just keep that leg empty and reach those ports another way? What's keeping the optimizer on the tampa arc? | `model.cr_tampa = Constraint(expr=model.x['yucatan-ch', 'yucatan-ch', 'tampa'] <= 0.0)` | 961336.0 |
| WHY-NOT/constraint_rule | The plan barely funnels anything from yucatan-ch out toward panama relative to s-gibraltr. Couldn't we just hold the panama leg down to 5 and lean on the other lanes? What's the model seeing that has it loading panama as heavily as it does? | `model.cr_pan = Constraint(expr=model.x['yucatan-ch', 'yucatan-ch', 'panama'] <= 5.0)` | 964537.0 |

### port_lp  (7)  — `testing_library/feas_test/port_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Risk wants to test a single-name concentration limit — no more than 1.0 in municip-a. Plug it in and tell me where the after-tax return lands. | `model.muniA_cap = Constraint(expr=model.investment['municip-a'] <= 1.0)` | 0.283 |
| WHAT-IF/new_constraint | Treasury's thinking about holding back some cash — say we only deploy 8 of the 10 total. What's the return picture if total investment is capped at 8? | `model.budget_cap = Constraint(expr=model.tinvest <= 8.0)` | 0.2386909090909091 |
| WHAT-IF/new_constraint | There's a proposal to keep a minimum 1.5 stake in the us-ser-f series-F bond for liquidity. Run it and let me know the resulting return. | `model.usF_floor = Constraint(expr=model.investment['us-ser-f'] >= 1.5)` | 0.29740909090909085 |
| WHY-NOT/constraint_rule | The plan sinks almost three-quarters of the book into one bond, us-ser-e. That feels lopsided — shouldn't we hold it to 4 at most? What's the model seeing that makes it concentrate there? | `model.usE_cap = Constraint(expr=model.investment['us-ser-e'] <= 4.0)` | 0.29647999999999997 |
| WHY-NOT/constraint_rule | The corporate bond carries the fattest coupon on the sheet, yet the plan buys none of it. Couldn't we put at least 1 into corporate? What's keeping the model away from it? | `model.corp_floor = Constraint(expr=model.investment['corporate'] >= 1.0)` | 0.2681818181818182 |
| WHY-NOT/constraint_rule | municip-a is the best tax-free name we've got — wouldn't it be obvious to hold at least 3 of it? What's the tradeoff the optimizer is making that holds it lower? | `model.muniA_floor = Constraint(expr=model.investment['municip-a'] >= 3.0)` | 0.2955 |
| WHY-NOT/constraint_rule | Why bother with municip-b at all — it's a high-rating, low-tax-benefit name. Couldn't we just keep it under 0.1? What's pulling the model toward holding it? | `model.muniB_cap = Constraint(expr=model.investment['municip-b'] <= 0.1)` | 0.29265 |

### poutil_mip  (6)  — `testing_library/feas_test/poutil_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Procurement is considering locking in more base-load coverage — at least 100 base-load contracts. What does the day's total cost come to if we commit to that floor? | `model.commit_base = Constraint(expr=model.alpha >= 100)` | 278140.5 |
| WHAT-IF/new_constraint | We're evaluating dropping peak-load contracts entirely this day — set the peak contract count to zero. Where does total cost land when peak coverage comes only from the plant and load-following? | `model.drop_peak = Constraint(expr=model.beta == 0)` | 277000.5 |
| WHAT-IF/new_constraint | There's a proposal to standardize on exactly 95 base-load contracts for the day. Plug that in — what total cost does the rest of the plan settle at around that fixed base position? | `model.fix_base = Constraint(expr=model.alpha == 95)` | 277638.0 |
| WHY-NOT/constraint_rule | Ninety base-load contracts feels like a lot of standing commitment. Shouldn't we trim that to 70 or under and stay nimble? What's the model seeing that makes carrying so much base load worth it? | `model.trim_base = Constraint(expr=model.alpha <= 70)` | 277257.0 |
| WHY-NOT/constraint_rule | We're barely hedging the peaks — only a handful of peak contracts. Wouldn't it be obvious to take at least 10 peak-load contracts to cover the afternoon spikes? What's the trade-off pulling the plan away from that? | `model.hedge_peak = Constraint(expr=model.beta >= 10)` | 276783.0 |
| WHY-NOT/constraint_rule | Even five peak contracts looks like overkill for the spikes we actually see. Couldn't we hold peak-load contracts to two at most? What's keeping the optimizer from running that lean on peak coverage? | `model.lean_peak = Constraint(expr=model.beta <= 2)` | 276736.5 |

### pp_mip  (2)  — `testing_library/feas_test/pp_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Sales is pitching an earlier launch for product G so customers see it sooner. Suppose we require product G to be processed in week 4. Plug that in and walk me through the resulting profit. | `model.g_week4 = Constraint(expr=model.e['G', 4] == 1)` | 9310.7 |
| WHAT-IF/new_constraint | The week-5 supervisor likes finishing the week on product A for cleanup reasons. Let's see the schedule cost if product A is forced to be the last product run in week 5. | `model.a_last_w5 = Constraint(expr=model.l['A', 5] == 1)` | 9435.566666666668 |

### process_mip  (5)  — `testing_library/feas_test/process_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Engineering is pitching a minimum-load policy for the lowest-temperature A/BC column (column 1) so it never runs near-empty. If column 1 has to carry at least 50 units of flow, what does that do to the design cost? | `model.col1_minload = Constraint(expr=model.F[1] >= 50)` | 107772.076 |
| WHAT-IF/new_constraint | The board wants to see what a per-column hydraulic ceiling looks like — say column 3 can take no more than 200 units of flow instead of carrying the whole feed. What's the new total cost under that cap? | `model.col3_cap = Constraint(expr=model.F[3] <= 200)` | 107315.995 |
| WHY-NOT/constraint_rule | Our process engineer keeps asking about column 4 — it's an A/BC cut just one tray-temperature step above the one we picked, and on paper it looks interchangeable. Is there a reason the design leaves column 4 switched off? What's the model seeing that I'm not if we insist on selecting it? | `model.use_col4 = Constraint(expr=model.y[4] >= 1)` | 107324.48 |
| WHY-NOT/constraint_rule | Column 6 gives the widest A/BC split, which intuitively should save reboiler duty downstream. Shouldn't the design lean on it? What's the tradeoff I'm missing that keeps the optimizer from switching column 6 on? | `model.use_col6 = Constraint(expr=model.y[6] >= 1)` | 113152.758 |
| WHY-NOT/constraint_rule | The lowest-temperature A/BC column (column 2) should be the cheapest to run on utilities, yet the plan ignores it. Wouldn't it be obvious to bring column 2 online? What's keeping the model from making that move? | `model.use_col2 = Constraint(expr=model.y[2] >= 1)` | 107315.995 |

### prodmix_lp  (6)  — `testing_library/feas_test/prodmix_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to avoid over-concentrating on the d1 desk — hold its build to 1000 units or fewer. Plug that in and walk me through the profit. | `model.d1_cap = Constraint(expr=model.mix['d1'] <= 1000)` | 18000.0 |
| WHAT-IF/new_constraint | Sales wants the d3 desk kept on the catalog with a minimum run of 30 units. Let's try that and see what it costs us in profit. | `model.d3_floor = Constraint(expr=model.mix['d3'] >= 30)` | 18566.666666666668 |
| WHY-NOT/constraint_rule | The premium d4 desk eats a ton of finishing time. Shouldn't we hold d4 to 50 units and free that capacity for other models? What's keeping the model from making that move? | `model.d4_cap = Constraint(expr=model.mix['d4'] <= 50)` | 18500.0 |
| WHY-NOT/constraint_rule | We're building zero d2 desks, which seems like leaving a product line on the table. Shouldn't we run at least 20 of them? What's the model seeing that I'm not? | `model.d2_floor = Constraint(expr=model.mix['d2'] >= 20)` | 18533.333333333332 |
| WHY-NOT/constraint_rule | Dropping d3 entirely feels like a missed mid-range offering. Wouldn't it be smarter to commit to at least 50 d3 desks? Walk me through what's pulling the plan the other way. | `model.d3_floor50 = Constraint(expr=model.mix['d3'] >= 50)` | 18500.0 |
| WHY-NOT/constraint_rule | The d4 is our flagship and only 67 get built. Couldn't we just commit to at least 80 of them? What's the tradeoff I'm missing? | `model.d4_floor80 = Constraint(expr=model.mix['d4'] >= 80)` | 16000.0 |

### prodplan_mip  (7)  — `testing_library/feas_test/prodplan_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're thinking about a throughput ceiling on the big t3 run so the line isn't slammed in one go. Suppose production in period 3 is held to at most 1000 units — what does the optimizer return for the total cost? | `model.cap_x3 = Constraint(expr=model.x['t3'] <= 1000)` | 737000.0 |
| WHAT-IF/new_constraint | Period 2 sits completely idle in the current schedule. We're curious what happens if we ask the line to put out at least 400 units in t2 instead of leaving it dark — where does the cost land? | `model.run_t2 = Constraint(expr=model.x['t2'] >= 400)` | 739000.0 |
| WHAT-IF/new_constraint | Operations wants a safety buffer carried into the back half of the horizon. If we require at least 200 units of inventory on hand at the end of period 4, what does the total plan cost become? | `model.safety_t4 = Constraint(expr=model.s['t4'] >= 200)` | 738000.0 |
| WHY-NOT/constraint_rule | Period 2 just sits there producing nothing while we pre-build a pile in period 1. Couldn't we smooth that out and run at least 200 units in t2? What's the model seeing that makes leaving it idle the better call? | `model.cr_run_t2 = Constraint(expr=model.x['t2'] >= 200)` | 739000.0 |
| WHY-NOT/constraint_rule | Sitting on 400 units of inventory at the end of period 1 ties up a lot of working capital. Shouldn't we keep that closing stock down to 100 at most? What's pulling the optimizer toward stockpiling that much early? | `model.cr_low_s1 = Constraint(expr=model.s['t1'] <= 100)` | 739000.0 |
| WHY-NOT/constraint_rule | We're paying a 5000 setup in period 6 on top of t5, t7 and t8 right next to it. Why couldn't we just skip the t6 setup entirely and cover that period from a neighboring batch? What's the tradeoff the model is making by keeping it on? | `model.cr_skip_t6 = Constraint(expr=model.y['t6'] <= 0)` | 737000.0 |
| WHY-NOT/constraint_rule | That period-1 run cranks out 600 units just to bankroll period 2. Wouldn't it be cleaner to hold t1 production to its own 400-unit demand instead of over-building? What's keeping the model from doing that? | `model.cr_cap_x1 = Constraint(expr=model.x['t1'] <= 400)` | 739000.0 |

### prodsch_eb1  (2)  — `testing_library/feas_test/prodsch_eb1.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal on the table to carry a heavier buffer into the spring peak — at least 20000 motors on hand at the end of winter. Add that winter floor and walk me through the resulting production plan and total cost. | `model.winter_buffer = Constraint(expr=model.inv['winter'] >= 20000.0)` | 3310.6527573065673 |
| WHY-NOT/constraint_rule | Fall production idles down to 5800 right before we have to build stock for spring. Shouldn't we keep the fall line running at 6000 or more to pre-build instead of scrambling later? What's keeping the model from leaning on fall output? | `model.fall_floor = Constraint(expr=model.p['fall'] >= 6000.0)` | 3267.8185429382 |

### prodsch_eb2  (3)  — `testing_library/feas_test/prodsch_eb2.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Operations wants a winter safety stock of at least 20000 motors heading into spring — they're worried about a peak-season stockout. Add that as a hard requirement on the winter inventory level and tell me what the new schedule and cost come out to. | `model.safety_winter = Constraint(expr=model.inv['winter'] >= 20000.0)` | 3319.0527573065674 |
| WHAT-IF/new_constraint | Engineering is pitching a maintenance window that would hold the spring run to 6000 motors instead of the usual peak push. Cap spring production at 6000 and let me see how the rest of the schedule and the total cost respond. | `model.spring_cap = Constraint(expr=model.p['spring'] <= 6000.0)` | 3258.791471316187 |
| WHY-NOT/constraint_rule | Fall sits idle at 5800 motors and then we hire a wave of people to chase the spring peak. Shouldn't the fall line pre-build at 6000 or more so spring isn't such a scramble? What's the model seeing that keeps fall output down? | `model.fall_prebuild = Constraint(expr=model.p['fall'] >= 6000.0)` | 3264.2185429382002 |

### prodsch_mip  (7)  — `testing_library/feas_test/prodsch_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Sales wants a service-level cushion going into the back half — at least 10000 motors on hand at the end of summer so we're never caught short early. Add that summer floor and tell me what the plan and total cost come out to. | `model.summer_floor = Constraint(expr=model.inv['summer'] >= 10000.0)` | 3333.465459519729 |
| WHAT-IF/new_constraint | Finance is weighing whether to walk away from the overflow-warehouse lease entirely this year. Run the plan with no lease taken at all and tell me what total cost looks like. | `model.no_lease = Constraint(expr=model.lease == 0)` | 3305.87391843455 |
| WHAT-IF/new_constraint | Ops is floating a roll-over buffer so next year doesn't start empty — at least 2000 motors still on hand at the end of spring. Add that closing-stock requirement and tell me how the plan and total cost shift. | `model.closing_buffer = Constraint(expr=model.inv['spring'] >= 2000.0)` | 3526.2479303613804 |
| WHY-NOT/constraint_rule | That summer second shift is the most expensive thing on the calendar — overtime crew, extra fixed overhead. Shouldn't we just run summer on a single shift like every other quarter? What's the model seeing that makes the second shift worth it? | `model.no_summer_second = Constraint(expr=model.shift['summer', 'second'] == 0)` | 3254.662044070266 |
| WHY-NOT/constraint_rule | Winter output idles down to 5800 right before the spring rush hits. Shouldn't we be pushing winter to at least 6500 to pre-build for spring instead of leaning on stock? What's keeping the model from running winter harder? | `model.winter_push = Constraint(expr=model.p['winter'] >= 6500.0)` | 3262.3914713161867 |
| WHY-NOT/constraint_rule | We're sitting on 6600 motors at the end of summer — that's a lot of cash parked in a warehouse mid-year. Shouldn't summer stock stay under 4000 so we're not over-building early? What's the model seeing that justifies carrying that much? | `model.lean_summer = Constraint(expr=model.inv['summer'] <= 4000.0)` | 3285.777499351012 |
| WHY-NOT/constraint_rule | The plan fires more than five people in summer right out of the gate, then hires nobody. Shouldn't we hold summer separations to a couple at most and avoid the disruption? What's pulling the model toward cutting that deep in summer? | `model.summer_sep_cap = Constraint(expr=model.f['summer'] <= 2.0)` | 3259.8735250644277 |

### prodschx_1B_mip  (3)  — `testing_library/feas_test/prodschx_1B_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating handing part of the spring line to a co-production run, which would cap our own spring output at 5000 motors. Plug that in and tell me where total cost lands. | `model.spring_slot_5000 = Constraint(expr=model.p['spring'] <= 5000.0)` | 3273.998162466938 |
| WHY-NOT/constraint_rule | Summer runs the line flat-out at 6600 motors on two shifts while every other quarter sits at 5800 — that lopsided ramp is hard on the floor. Shouldn't summer output be pulled back under 5000 and the load spread across the year? What's the model seeing that makes it lean so hard on summer? | `model.cap_summer = Constraint(expr=model.p['summer'] <= 5000.0)` | 3266.2841952670765 |
| WHY-NOT/constraint_rule | Fall keeps running near full tilt right after the summer push. Shouldn't fall output ease back under 5000 once the summer surge is behind us? What's the model seeing that keeps fall so high? | `model.cap_fall_5000 = Constraint(expr=model.p['fall'] <= 5000.0)` | 3269.058124562461 |

### prodschx_1S1_mip  (4)  — `testing_library/feas_test/prodschx_1S1_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Maintenance wants a planned winter downtime window that would hold winter output to 5000 motors. Work that ceiling in and tell me the schedule and total cost. | `model.cap_winter_5000 = Constraint(expr=model.p['winter'] <= 5000.0)` | 3453.726227848417 |
| WHAT-IF/new_constraint | We may reserve part of the fall line for a side contract, which would cap our fall output at 5000 motors. Run that and tell me the resulting plan and cost. | `model.cap_fall_5000 = Constraint(expr=model.p['fall'] <= 5000.0)` | 3444.5642081546666 |
| WHY-NOT/constraint_rule | We run summer at full output and then warehouse it for three quarters while paying to lease the space the whole time. Shouldn't summer production be pulled back under 4500 and the build shifted closer to the spring delivery? What's the model seeing that makes it front-load like this? | `model.cap_summer = Constraint(expr=model.p['summer'] <= 4500.0)` | 3446.0384194776666 |
| WHY-NOT/constraint_rule | Every quarter sits at a flat 6000 including spring, right when the delivery crunch hits. Shouldn't spring output be pulled under 5000 and the slack built earlier? What's the model seeing that keeps spring loaded? | `model.cap_spring_5000 = Constraint(expr=model.p['spring'] <= 5000.0)` | 3450.2747878735554 |

### prodschx_1S2_mip  (3)  — `testing_library/feas_test/prodschx_1S2_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're weighing handing part of the spring line to a co-production run, capping our own spring output at 5000 motors. Plug that in and tell me total cost. | `model.spring_slot_5000 = Constraint(expr=model.p['spring'] <= 5000.0)` | 3267.2803649574994 |
| WHY-NOT/constraint_rule | Summer runs both shifts flat-out at 6600 motors while every other quarter gets by on a single shift — that lopsided ramp leans hard on one quarter. Shouldn't summer output be pulled back under 4500 and the load spread across the year? What's the model seeing that makes it pile onto summer? | `model.cap_summer = Constraint(expr=model.p['summer'] <= 4500.0)` | 3264.943611456833 |
| WHY-NOT/constraint_rule | Fall runs near full tilt right after the summer push. Shouldn't fall output ease back under 5000 once the summer surge is behind us? What's pulling the model the other way? | `model.cap_fall_5000 = Constraint(expr=model.p['fall'] <= 5000.0)` | 3263.2495491526665 |

### prodschx_2B_mip  (2)  — `testing_library/feas_test/prodschx_2B_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Spring runs both shifts flat-out at 6800 motors right at the deadline while we coast on a single shift the rest of the year. Shouldn't spring output be held under 5000 and the build pulled earlier in the year? What's the model seeing that makes it cram production into spring? | `model.cap_spring = Constraint(expr=model.p['spring'] <= 5000.0)` | 3331.8151556355383 |
| WHY-NOT/constraint_rule | Winter runs flat-out at 5800 building stock we won't ship until spring. Shouldn't winter output ease under 5000 and the build shift closer to the delivery? What's the model seeing that keeps winter so high? | `model.cap_winter_5000 = Constraint(expr=model.p['winter'] <= 5000.0)` | 3322.1512596246152 |

### prodschx_2S1_mip  (4)  — `testing_library/feas_test/prodschx_2S1_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Maintenance wants a planned winter downtime window that would hold winter output to 5000 motors. Work that ceiling in and tell me the schedule and total cost. | `model.cap_winter_5000 = Constraint(expr=model.p['winter'] <= 5000.0)` | 3514.645992078 |
| WHY-NOT/constraint_rule | Summer barely runs at 2000 motors while we slam 7600 into winter and spring right before the deadline. Shouldn't summer carry at least 5000 upfront to ease that late crunch? What's the model seeing that makes it start so slow? | `model.summer_floor = Constraint(expr=model.p['summer'] >= 5000.0)` | 3499.1976687326664 |
| WHY-NOT/constraint_rule | Spring runs both shifts flat-out at 7600 right at the deadline. Shouldn't spring output be held under 5000 and more of the build pulled earlier? What's the model seeing that makes it cram production into spring? | `model.cap_spring_5000 = Constraint(expr=model.p['spring'] <= 5000.0)` | 3516.1036074926665 |
| WHY-NOT/constraint_rule | Fall already jumps to 6800 as we ramp the crew up. Shouldn't fall output stay under 5000 so we're not racing the hiring? What's pushing the model to lean on fall so early? | `model.cap_fall_5000 = Constraint(expr=model.p['fall'] <= 5000.0)` | 3496.5327582896666 |

### prodschx_2S2_mip  (1)  — `testing_library/feas_test/prodschx_2S2_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Spring runs a second shift and pushes 6800 motors right at the deadline while the rest of the year coasts on one shift. Shouldn't spring output be held under 5000 and the build pulled earlier? What's the model seeing that makes it lean so hard on spring? | `model.cap_spring = Constraint(expr=model.p['spring'] <= 5000.0)` | 3325.3927383949995 |

### prodsp_lp  (3)  — `testing_library/feas_test/prodsp_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a single-SKU ceiling for class-1, our commodity workhorse — keep its volume at 1000 units or below so the line doesn't become a single point of failure if that grade's demand softens. With class-1 held at no more than 1000, where does expected profit land? | `model.class1_ceiling = Constraint(expr=model.x['class-1'] <= 1000)` | 17204.67459365325 |
| WHY-NOT/constraint_rule | Class-3 has been completely squeezed out of the plan, but engineering tells me we've got tooling sitting idle that's calibrated specifically for that grade. Couldn't we keep at least 150 units of class-3 on the line so that tooling isn't just gathering dust? What's the model giving up to zero it out? | `model.class3_floor = Constraint(expr=model.x['class-3'] >= 150)` | 17386.15921122067 |
| WHY-NOT/constraint_rule | Class-2 keeps coming back at zero, but the sales team has a handful of accounts that specifically want that grade and they'll walk if we can't supply it. Shouldn't we run at least 100 units of class-2 to keep those accounts? What's making the model so reluctant to schedule any? | `model.class2_floor = Constraint(expr=model.x['class-2'] >= 100)` | 17226.294000993123 |

### qp5_lp  (3)  — `testing_library/feas_test/qp5_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Compliance is uneasy about how much rides on ALU. We're looking at a single-name ceiling that keeps ALU's weight at or below 20% — what tracking deviation does the optimizer return under that cap? | `model.alu_cap = Constraint(expr=model.x['ALU'] <= 0.20)` | 0.4453205633757854 |
| WHY-NOT/constraint_rule | ALU is carrying almost a third of the book — that feels like a lot of single-name risk. Shouldn't we just hold it to 15% and spread the rest around? What's the model seeing that makes it lean on ALU so hard? | `model.alu_limit = Constraint(expr=model.x['ALU'] <= 0.15)` | 0.46799459203537286 |
| WHY-NOT/constraint_rule | GE has a healthy mean return and the plan leaves it out entirely. Couldn't we force at least a 5% stake in GE? Why is the optimizer steering clear of it? | `model.ge_floor = Constraint(expr=model.x['GE'] >= 0.05)` | 0.8557652050810538 |

### queens_mip  (6)  — `testing_library/feas_test/queens_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to nail a queen down on the top-left corner square, row 1 column 1. Lock that in and tell me whether the board still fills out and at what objective. | `model.pin_1_1 = Constraint(expr=model.x['1', '1'] == 1)` | 8.0 |
| WHAT-IF/new_constraint | We're evaluating placing a queen at row 1, column 4. Add that and let me know if a full non-attacking layout still comes back, and the objective. | `model.pin_1_4 = Constraint(expr=model.x['1', '4'] == 1)` | 8.0 |
| WHAT-IF/new_constraint | Let's try keeping the central square at row 4, column 4 clear of any queen. Run it and see whether the board still completes and at what objective. | `model.block_4_4 = Constraint(expr=model.x['4', '4'] == 0)` | 8.0 |
| WHY-NOT/constraint_rule | Square (2,2) sits there wide open near the top-left. Shouldn't a queen just claim it? Why does the layout leave that one empty — what's it weighing? | `model.want_2_2 = Constraint(expr=model.x['2', '2'] == 1)` | 8.0 |
| WHY-NOT/constraint_rule | The bottom row's square at column 4 looks like a natural spot, yet the plan skips it. Wouldn't it be obvious to drop a queen at row 8, column 4? What's keeping it off that square? | `model.want_8_4 = Constraint(expr=model.x['8', '4'] == 1)` | 8.0 |
| WHY-NOT/constraint_rule | Couldn't we just anchor a queen on the left edge at row 4, column 1? It seems like an easy, uncontested square. What's the trade-off pulling the queen away from there? | `model.want_4_1 = Constraint(expr=model.x['4', '1'] == 1)` | 8.0 |

### railcirc_mip  (2)  — `testing_library/feas_test/railcirc_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Rotterdam keeps three big tu2 units overnight in the plan. Shouldn't we be able to trim that to a single tu2 sitting at Rotterdam and route the rest of that coverage from elsewhere? What's keeping the model from thinning out the Rotterdam stabling? | `model.thin_rtd = Constraint(expr=model.f['tu2', 'Rtd', 2358, 'Rtd', 531] <= 1)` | 80.0 |
| WHY-NOT/constraint_rule | We're holding only one tu1 at Roosendaal overnight. Couldn't we beef that up to at least three small units stabled at Roosendaal for resilience? What's the tradeoff the model is making by keeping Roosendaal so lean on tu1s? | `model.beef_rsd = Constraint(expr=model.f['tu1', 'Rsd', 2354, 'Rsd', 529] >= 3)` | 80.0 |

### rdata_mip  (5)  — `testing_library/feas_test/rdata_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating bringing the Machinists (IAM) into the labor agreement up front. If IAM is in the mix, what does the total union count come to? | `model.iam_in = Constraint(expr=model.up['iam'] == 1)` | 4.0 |
| WHAT-IF/new_constraint | There's a proposal to fold the Electrical Workers (IBEW) into the plan as well. Run that and tell me how many unions we're up to. | `model.ibew_in = Constraint(expr=model.up['ibew'] == 1)` | 4.0 |
| WHY-NOT/constraint_rule | We've got a perfectly good blast furnace sitting at Sparrows, yet the plan funnels all the iron-making through Inland. Shouldn't we run at least some pig iron at Sparrows to spread the risk? What's the optimizer seeing that keeps it off that mill? | `model.want_pigiron_sparrows = Constraint(expr=model.z['pig-iron', 'sparrows'] >= 0.3)` | 4.0 |
| WHY-NOT/constraint_rule | Rockdale has an aluminum line that's just sitting idle while we make every bit of aluminum at Comfort. Wouldn't it make sense to put a little aluminum through Rockdale? What's the trade-off pulling the plan away from using it? | `model.want_alum_rockdale = Constraint(expr=model.z['aluminum', 'rockdale'] >= 0.05)` | 4.0 |
| WHY-NOT/constraint_rule | The scrap-steel route could clearly run at Sparrows too, but the plan parks all of it elsewhere. Couldn't we push at least some scrap-steel through Sparrows? What's keeping the model from making that call? | `model.want_stlscrap_sparrows = Constraint(expr=model.z['stl-scrap', 'sparrows'] >= 0.3)` | 4.0 |

### reaction_mip  (10)  — `testing_library/feas_test/reaction_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Our supplier for raw material y10 just flagged an outage. If y10 can't be sourced, is acetone still synthesizable? Run it and tell me where producibility lands. | `model.y['y10'].unfix() model.lose_y10 = Constraint(expr=model.y['y10'] == 0)` | 0.0 |
| WHAT-IF/new_constraint | We're evaluating a stretch where reagent y12 is off the market. Does acetone stay producible without it? | `model.y['y12'].unfix() model.lose_y12 = Constraint(expr=model.y['y12'] == 0)` | 0.0 |
| WHAT-IF/new_constraint | There's a proposal to phase y22 out of our inventory. Plug that in and let me see whether acetone can still be made. | `model.y['y22'].unfix() model.lose_y22 = Constraint(expr=model.y['y22'] == 0)` | 0.0 |
| WHAT-IF/new_constraint | Say we run short on y28 for a while. Where does that leave acetone production — can we still get there? | `model.y['y28'].unfix() model.lose_y28 = Constraint(expr=model.y['y28'] == 0)` | 1.0 |
| WHAT-IF/new_constraint | Let's check the impact if catalyst y03 is unavailable — does the synthesis still go through? | `model.y['y03'].unfix() model.lose_y03 = Constraint(expr=model.y['y03'] == 0)` | 1.0 |
| WHY-NOT/constraint_rule | The pathway insists on keeping y25 in the mix. Do we genuinely need it to make acetone, or is the model just being conservative? What's it seeing if we try to do without? | `model.y['y25'].unfix() model.drop_y25 = Constraint(expr=model.y['y25'] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | Y26 keeps showing up as a must-have. Is it really load-bearing for acetone, or could we just leave it out? What's the trade-off? | `model.y['y26'].unfix() model.drop_y26 = Constraint(expr=model.y['y26'] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | Why does the solution keep hanging on to y31? Couldn't we make acetone without it and simplify the material list? | `model.y['y31'].unfix() model.drop_y31 = Constraint(expr=model.y['y31'] == 0)` | 0.0 |
| WHY-NOT/constraint_rule | We keep stocking y17 for this process — do we actually need it on the acetone route, or is it just along for the ride? What's the model seeing if we drop it? | `model.y['y17'].unfix() model.drop_y17 = Constraint(expr=model.y['y17'] == 0)` | 1.0 |
| WHY-NOT/constraint_rule | Is y05 truly necessary here, or is it dead weight on the material list? Could acetone be made without it? | `model.y['y05'].unfix() model.drop_y05 = Constraint(expr=model.y['y05'] == 0)` | 1.0 |

### recovery_mip  (5)  — `testing_library/feas_test/recovery_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're weighing whether to keep recovery site 0 in play for redundancy. If we require recovery center 0 to be opened, what's the resulting cost? | `model.open_z0 = Constraint(expr=model.Z[0] >= 1)` | 13713604.627792547 |
| WHY-NOT/constraint_rule | The neighborhood near recovery site 2 is pushing back hard on new construction there, and frankly we'd rather not fight that battle. What's keeping the model from just skipping recovery center 2 — would dropping it really cost us much? | `model.no_z2 = Constraint(expr=model.Z[2] <= 0)` | 13712761.196400752 |
| WHY-NOT/constraint_rule | I keep coming back to collection center 2 — it feels like an odd pick for a site we have to commit to. Couldn't we just leave it closed and route around it? What's the model seeing that I'm not? | `model.no_y2 = Constraint(expr=model.Y[2] <= 0)` | 14230568.871946895 |
| WHY-NOT/constraint_rule | The plan leans entirely on redistribution center 4 and that worries me for resilience. Is there a real reason we couldn't close center 4 and spread the redistribution elsewhere? Walk me through the tradeoff. | `model.no_w4 = Constraint(expr=model.W[4] <= 0)` | 13734085.379695984 |
| WHY-NOT/constraint_rule | We built out redistribution capacity but left site 0 completely idle. That seems wasteful — shouldn't we be putting center 0 to use? What's pulling the plan away from opening it? | `model.open_w0 = Constraint(expr=model.W[0] >= 1)` | 13734002.160700643 |

### relief_mip  (4)  — `testing_library/feas_test/relief_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a logistics argument for keeping a drop physically near the village at H6 in the far south. If we commit to opening a drop right on cell H6, where does the total walking distance settle? | `model.open_h6 = Constraint(expr=model.drop['H', 6] >= 1)` | 57.21341007249996 |
| WHY-NOT/constraint_rule | The village at H6 sits way down south and the nearest open drop is well away from it. Couldn't we just put a drop right on H6 to spare those folks the walk? What's the model seeing that makes that a bad call? | `model.why_h6 = Constraint(expr=model.drop['H', 6] >= 1)` | 57.21341007249996 |
| WHY-NOT/constraint_rule | The far-south village at J10 is being made to walk all the way to D8. There's a perfectly good grid cell J8 right next to it — why doesn't the plan just serve J10 from a drop at J8 instead? Force that and show me what it costs. | `model.why_j10 = Constraint(expr=model.walk['J', 10, 'J', 8] >= 1)` | 61.572964221099994 |
| WHY-NOT/constraint_rule | Why is the D8 drop completely shut out of the plan as an option I'd think about closing? Suppose we couldn't use cell D8 at all — say it's flooded — and had to open the drop somewhere else. How much worse does the total walk get? | `model.no_d8 = Constraint(expr=model.drop['D', 8] <= 0)` | 51.820637859799994 |

### ridesharing_miqcp  (4)  — `testing_library/feas_test/ridesharing_miqcp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | Vehicle v2 is sitting right next to request 1 and could clearly take it on path C, yet the plan routes it elsewhere. Shouldn't v2 just grab request 1 on that path? What's the model seeing that I'm not? | `model.want = Constraint(expr=model.x['v2', 1, 'C'] == 1)` | 70.0 |
| WHY-NOT/constraint_rule | The plan has vehicle v1 covering request 5 but it picked path C, while path A looked like the natural lane for that pair. Wouldn't it be obvious to send v1 down path A for request 5? What's pulling it the other way? | `model.want = Constraint(expr=model.x['v1', 5, 'A'] == 1)` | 60.0 |
| WHY-NOT/constraint_rule | Request 17 goes to vehicle v1 on path C in the plan, but path B seemed like the more direct option for it. Couldn't we just put v1 on path B for request 17 instead? What's the trade-off I'm missing? | `model.want = Constraint(expr=model.x['v1', 17, 'B'] == 1)` | 66.0 |
| WHY-NOT/constraint_rule | Request 19 ended up on v8, but v2 is one of its eligible vehicles and path A for that pair looks perfectly reasonable. Is there a reason the plan doesn't just give request 19 to v2 on path A? Walk me through what's keeping it from making that move. | `model.want = Constraint(expr=model.x['v2', 19, 'A'] == 1)` | 55.0 |

### robert_lp  (2)  — `testing_library/feas_test/robert_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a residual-inventory target: hold at least 200 units of new material in stock at the close of the long horizon, to seed the next cycle's run. With that end-of-horizon floor in place, what does the optimizer return for profit? | `model.new_residual_floor = Constraint(expr=model.s['new', 4] >= 200)` | 10875.0 |
| WHY-NOT/constraint_rule | We're sitting on a fat scrap crib all the way to the end of the horizon — it never gets drawn down. Shouldn't we cap the end-of-horizon scrap stock at 300 units and actually put that material to work? What's the model seeing that keeps it hoarding scrap? | `model.scrap_drawdown = Constraint(expr=model.s['scrap', 4] <= 300)` | 10791.666667 |

### rotdk_mip  (6)  — `testing_library/feas_test/rotdk_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating diversifying away from a single component — require at least 2 units of the small component C001 in the first period. What's the resulting cost? | `model.seed_c001 = Constraint(expr=model.x['C001', 't1'] >= 2)` | 2128.2960582782853 |
| WHAT-IF/new_constraint | There's a proposal to put a unit of the large component C010 in early — at least one in period 1. Where does the total land? | `model.seed_c010 = Constraint(expr=model.x['C010', 't1'] >= 1)` | 1990.2745942782856 |
| WHAT-IF/new_constraint | Let's look at front-loading C008 harder — require 3 of them in the very first period. What total cost does that give? | `model.front_c008 = Constraint(expr=model.x['C008', 't1'] >= 3)` | 1981.4695942782846 |
| WHY-NOT/constraint_rule | The plan leans entirely on C008 and never touches the mid-size C005. Shouldn't we be seeding at least one C005 up front for resilience? What's the model seeing that keeps it out? | `model.why_c005 = Constraint(expr=model.x['C005', 't1'] >= 1)` | 2009.776058278286 |
| WHY-NOT/constraint_rule | Period 6 looks light on new capacity. Couldn't we just push 3 more C008 units in then to stay ahead of demand? What's the tradeoff the optimizer is weighing? | `model.why_c008_t6 = Constraint(expr=model.x['C008', 't6'] >= 3)` | 1967.1802149042696 |
| WHY-NOT/constraint_rule | Is there a reason the small component C003 never gets used? Wouldn't seeding one in period 1 be a cheap hedge? What's pulling the plan away from it? | `model.why_c003 = Constraint(expr=model.x['C003', 't1'] >= 1)` | 1996.3345942782853 |

### sarf_lp  (1)  — `testing_library/feas_test/sarf_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A contract with the regional gin commits us to deliver more cotton. We're evaluating a floor that requires at least 4500 tons of cotton sales. Where does farm profit land? | `model.floor_cotton = Constraint(expr=model.sales['cotton'] >= 4500)` | 181394.57079977606 |

### sddp_lp  (4)  — `testing_library/feas_test/sddp_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose we required the reservoir to be drawn down to no more than 50 million MW by hour t100 to make room for an expected freshet. What total cost does that produce? | `model.res_drawdown_t100 = Constraint(expr=model.RES['t100'] <= 50000000.0)` | 8988863483.696545 |
| WHY-NOT/constraint_rule | The plan leans hard on the dam in the opening hour, pulling over 14 GW of hydro at t1. That seems like a lot to spend out of storage so early — couldn't we hold hydro at t1 down to at most 5000? What's the model seeing that makes it run the reservoir that hard up front? | `model.hydro_cap_t1 = Constraint(expr=model.X['t1', 'Hydro'] <= 5000.0)` | 6742154925.5077305 |
| WHY-NOT/constraint_rule | The schedule runs the nuclear unit close to flat out at the week-1 peak hour t168. Shouldn't we keep nuclear at t168 below 5000 to leave it some headroom? What's the tradeoff the optimizer is making by pinning it so high? | `model.nuc_cap_t168 = Constraint(expr=model.X['t168', 'Nuclear'] <= 5000.0)` | 6733688268.888214 |
| WHY-NOT/constraint_rule | The plan spills almost nothing in the first hour. Wouldn't a bit of precautionary release make sense — couldn't we spill at least 20000 at t1 to de-risk the storage? What's keeping the model from releasing more water early? | `model.spill_floor_t1 = Constraint(expr=model.SPILL['t1'] >= 20000.0)` | 6734608504.870391 |

### senstran_lp  (2)  — `testing_library/feas_test/senstran_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to keep Seattle directly engaged with the New York market for service-coverage reasons — route at least 100 cases straight from Seattle to New York. What does the optimizer return for total cost once that's in place? | `model.seattle_ny_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 100)` | 164.52 |
| WHAT-IF/new_constraint | We're evaluating a dual-sourcing rule for Chicago so it isn't fed by a single plant — have San Diego carry at least 100 of Chicago's cases alongside Seattle. Where does total cost land if we hold to that? | `model.chicago_dual_source = Constraint(expr=model.x['san-diego', 'chicago'] >= 100)` | 164.7 |

### shale_lp  (4)  — `testing_library/feas_test/shale_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Suppose offtake agreements cap how much syncrude we can sell in the last period — no more than 300 units delivered in 2005-09. Plug that in and tell me where profit lands. | `model.sync_ceiling = Constraint(expr=model.x['syncrude', '2005-09'] <= 300.0)` | 8870.619553969158 |
| WHAT-IF/new_constraint | If the upgrader is throughput-limited in the final period — say it can't run above 350 units of upgrading in 2005-09 — how does the optimal profit shift? | `model.upgrader_cap = Constraint(expr=model.z['upgrading', '2005-09'] <= 350.0)` | 8808.059348922885 |
| WHY-NOT/constraint_rule | We seem to be pushing final-period syncrude right to the ceiling at 346.5. Shouldn't we throttle that back a little — hold 2005-09 syncrude under 320 — to leave operating margin? What's driving the model to max it out? | `model.sync_pullback = Constraint(expr=model.x['syncrude', '2005-09'] <= 320.0)` | 9079.153570790062 |
| WHY-NOT/constraint_rule | The plan drip-feeds the upgrader investment instead of building it out up front. Wouldn't it be smarter to commit at least 120 units of upgrader capacity in the first 1985-89 build period? What's the model trading off by deferring it? | `model.upgrader_front_load = Constraint(expr=model.h['upgrader', '1985-89'] >= 120.0)` | 8925.280612050581 |

### solmpool_mip  (4)  — `testing_library/feas_test/solmpool_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Strategy wants to keep a physical presence in warehouse 3's corridor regardless of the math. We're just sizing the cost of that commitment — if we force w3 open, what does the network end up running us? | `model.use_w3 = Constraint(expr=model.ow['w3'] == 1)` | 512.0 |
| WHAT-IF/new_constraint | We're evaluating a service realignment that would route region 8's deliveries through warehouse 1. Pin that assignment in as a scenario and tell me what it does to the bottom line. | `model.route_r8_w1 = Constraint(expr=model.oa['w1', 'r8'] == 1)` | 509.0 |
| WHY-NOT/constraint_rule | Region 8's cheapest freight by a wide margin is to warehouse 4 — roughly half the per-unit cost of anywhere else. Yet the plan ships it from a pricier site. Shouldn't r8 just come out of w4? What's the model seeing that I'm not? | `model.r8_from_w4 = Constraint(expr=model.oa['w4', 'r8'] == 1)` | 522.0 |
| WHY-NOT/constraint_rule | Region 9 sits practically next door to warehouse 2, but the plan hauls it all the way back to warehouse 1. Couldn't we just serve r9 out of w2 and save the long leg? What's the tradeoff pulling it the other way? | `model.r9_from_w2 = Constraint(expr=model.oa['w2', 'r9'] == 1)` | 509.0 |

### solnpool_mip  (4)  — `testing_library/feas_test/solnpool_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The board likes the idea of keeping warehouse 3 active so we've got a foothold in that corridor. There's a proposal on the table to bring it online. Switch w3 on in the model and tell me what the network ends up costing. | `model.use_w3 = Constraint(expr=model.ow['w3'] == 1)` | 512.0 |
| WHAT-IF/new_constraint | Logistics is weighing a routing change that would put region 8's deliveries through warehouse 1. We're just evaluating it — pin that assignment in and tell me what it does to the total cost. | `model.route_r8_w1 = Constraint(expr=model.oa['w1', 'r8'] == 1)` | 509.0 |
| WHY-NOT/constraint_rule | Region 8's cheapest connection by a mile is to warehouse 4 — the per-unit freight there is half what it is from anywhere else. Yet the plan ships it from somewhere pricier. Shouldn't r8 just be served out of w4? What's the model seeing that I'm not? | `model.r8_from_w4 = Constraint(expr=model.oa['w4', 'r8'] == 1)` | 522.0 |
| WHY-NOT/constraint_rule | Region 9 sits right in warehouse 2's backyard, yet the plan threads it all the way back to warehouse 1. Wouldn't it be obvious to just serve r9 from w2? What's the tradeoff pulling it the other way? | `model.r9_from_w2 = Constraint(expr=model.oa['w2', 'r9'] == 1)` | 509.0 |

### sparta_lp  (8)  — `testing_library/feas_test/sparta_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Command wants a stronger presence in year 5 — let's see the cost if we carry at least 8 troops on strength that year. | `model.yr5_floor = Constraint(expr=model.e[5] >= 8)` | 3590.99 |
| WHAT-IF/new_constraint | There's a proposal to lock in some long-service recruits early — require at least 3 four-year enlistments in year 1. What does the optimizer return for cost? | `model.yr1_long = Constraint(expr=model.x[1, 4] >= 3)` | 3494.38 |
| WHAT-IF/new_constraint | We're evaluating a year-10 readiness target of at least 6 troops on strength. Run it and tell me the cost impact. | `model.yr10_floor = Constraint(expr=model.e[10] >= 6)` | 3676.4 |
| WHAT-IF/new_constraint | Suppose a force-structure review sets a year-7 floor of at least 10 troops on strength. How does that change the plan's cost? | `model.yr7_floor = Constraint(expr=model.e[7] >= 10)` | 3631.12 |
| WHY-NOT/constraint_rule | Year 1 leans on longer enlistments but barely uses cheap one-year recruits. Shouldn't we sign at least 5 one-year enlistments in year 1? What's keeping the model from doing that? | `model.yr1_short = Constraint(expr=model.x[1, 1] >= 5)` | 3578.04 |
| WHY-NOT/constraint_rule | Committing recruits to four-year terms in year 1 feels inflexible. Couldn't we just avoid any 4-year enlistments in year 1? Walk me through what that costs us. | `model.no_yr1_long = Constraint(expr=model.x[1, 4] <= 0)` | 3483.79 |
| WHY-NOT/constraint_rule | Year 3 only carries the bare minimum. Wouldn't it be prudent to hold at least 10 troops on strength that year for depth? What's the tradeoff the model is making? | `model.yr3_depth = Constraint(expr=model.e[3] >= 10)` | 3563.13 |
| WHY-NOT/constraint_rule | Year 6 is already our peak need, yet we keep it right at the line. Is there a reason we couldn't push year-6 strength to 11 for a buffer? What's the model seeing that I'm not? | `model.yr6_buffer = Constraint(expr=model.e[6] >= 11)` | 3656.38 |

### spbenders1_lp  (7)  — `testing_library/feas_test/spbenders1_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a lane-capacity guideline that holds the f1-to-d5 shipment to 400 units or under. What does the optimizer return for expected profit? | `model.f1d5_cap = Constraint(expr=model.ship['f1', 'd5'] <= 400)` | 10562.85 |
| WHAT-IF/new_constraint | There's a proposal to keep factory f3 busy — at least 550 units of production there. Plug it in and walk me through the profit. | `model.f3_floor = Constraint(expr=model.product['f3'] >= 550)` | 10736.05 |
| WHAT-IF/new_constraint | Let's try a storage rule that limits how much d5 can take in — cap the quantity sent to d5 at 500 units. What does that do to expected profit? | `model.d5_cap = Constraint(expr=model.received['d5'] <= 500)` | 10238.0 |
| WHY-NOT/constraint_rule | Factory f2 is hauling a big load to d4. Shouldn't we hold that f2-to-d4 lane to 200 units and spread the shipment? What's keeping the model from doing that? | `model.f2d4_cap = Constraint(expr=model.ship['f2', 'd4'] <= 200)` | 10687.7 |
| WHY-NOT/constraint_rule | Distribution center d3 looks underserved. Wouldn't it be smarter to guarantee it at least 290 units? What's the model seeing that I'm not? | `model.d3_floor = Constraint(expr=model.received['d3'] >= 290)` | 10521.0 |
| WHY-NOT/constraint_rule | Factory f1 is running flat out. Couldn't we just hold its production to 400 units and lean on the others? What's the tradeoff I'm missing? | `model.f1_cap = Constraint(expr=model.product['f1'] <= 400)` | 10555.0 |
| WHY-NOT/constraint_rule | It seems odd that f3 sends so much to the far d5. Shouldn't the f3-to-d5 lane be capped at 50 units? Walk me through what's pulling the plan the other way. | `model.f3d5_cap = Constraint(expr=model.ship['f3', 'd5'] <= 50)` | 10687.5 |

### spbenders2_lp  (7)  — `testing_library/feas_test/spbenders2_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at a truck-fleet guideline that holds the f2-to-d4 run to 250 crates or fewer. What does the optimizer return for expected profit? | `model.f2d4_cap = Constraint(expr=model.ship['f2', 'd4'] <= 250)` | 10744.2 |
| WHAT-IF/new_constraint | There's a proposal to rest farm f2's fields by holding its harvest to 400 crates. Plug it in and walk me through the profit. | `model.f2_cap = Constraint(expr=model.product['f2'] <= 400)` | 10703.0 |
| WHAT-IF/new_constraint | Depot d4 has limited cold storage. Let's try capping what it can receive at 275 crates and see the profit impact. | `model.d4_cap = Constraint(expr=model.received['d4'] <= 275)` | 10616.45 |
| WHY-NOT/constraint_rule | Farm f2 is sending a lot of crates to the nearby depot d1. Shouldn't we hold that f2-to-d1 lane under 100 and free up trucks? What's keeping the model from doing that? | `model.f2d1_cap = Constraint(expr=model.ship['f2', 'd1'] <= 100)` | 10750.75 |
| WHY-NOT/constraint_rule | Farm f3 looks underused. Wouldn't it be smarter to keep it producing at least 520 crates? What's the model seeing that I'm not? | `model.f3_floor = Constraint(expr=model.product['f3'] >= 520)` | 10775.6 |
| WHY-NOT/constraint_rule | Depot d4 is taking a big load that risks spoilage. Couldn't we just hold what it receives to 250 crates? What's the tradeoff I'm missing? | `model.d4_cap = Constraint(expr=model.received['d4'] <= 250)` | 10432.2 |
| WHY-NOT/constraint_rule | Farm f3 hauls a heavy run to depot d3. Shouldn't that f3-to-d3 lane be held under 200 crates? Walk me through what's pulling the plan the other way. | `model.f3d3_cap = Constraint(expr=model.ship['f3', 'd3'] <= 200)` | 10733.5 |

### spbenders3_lp  (2)  — `testing_library/feas_test/spbenders3_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to guarantee d5 — our flagship market — at least 650 units received each cycle so the big retail account never sees a shortfall. If we hold received at d5 to a 650-unit floor, what does the optimizer return for the plan? | `model.d5_service_floor = Constraint(expr=model.received['d5'] >= 650)` | 10720.5 |
| WHAT-IF/new_constraint | We're evaluating a lane-balancing rule that keeps the long f3-to-d5 haul light — cap shipments on the f3-to-d5 lane at 50 units so we don't lean on that expensive route. Drop that in and tell me where expected profit lands. | `model.f3_d5_lane_cap = Constraint(expr=model.ship['f3', 'd5'] <= 50)` | 10687.5 |

### spbenders4_lp  (6)  — `testing_library/feas_test/spbenders4_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a cold-chain limit that holds the f1-to-d5 shipment to 350 doses or under. What does the optimizer return for expected profit? | `model.f1d5_cap = Constraint(expr=model.ship['f1', 'd5'] <= 350)` | 10443.85 |
| WHAT-IF/new_constraint | There's a proposal to keep plant f1 below 450 doses to reserve line time for another product. Plug it in and walk me through the profit. | `model.f1_cap = Constraint(expr=model.product['f1'] <= 450)` | 10674.0 |
| WHAT-IF/new_constraint | Clinic d3 serves a high-risk area, so we'd like it guaranteed at least 280 doses. Let's see what that does to expected profit. | `model.d3_floor = Constraint(expr=model.received['d3'] >= 280)` | 10657.0 |
| WHY-NOT/constraint_rule | Plant f1 trucks a huge run to the far clinic d5. Shouldn't we hold that f1-to-d5 lane to 450 doses and shorten the cold-chain exposure? What's keeping the model from doing that? | `model.f1d5_cap = Constraint(expr=model.ship['f1', 'd5'] <= 450)` | 10681.85 |
| WHY-NOT/constraint_rule | Plant f3 sends a big load to clinic d3. Wouldn't holding that f3-to-d3 lane under 230 doses balance the network better? What's the model seeing that I'm not? | `model.f3d3_cap = Constraint(expr=model.ship['f3', 'd3'] <= 230)` | 10764.4 |
| WHY-NOT/constraint_rule | Plant f2 runs hot. Couldn't we just hold its production to 420 doses to keep some line slack? What's the tradeoff I'm missing? | `model.f2_cap = Constraint(expr=model.product['f2'] <= 420)` | 10739.0 |

### spbenders5_lp  (5)  — `testing_library/feas_test/spbenders5_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a route-balancing guideline that holds the f2-to-d1 delivery to 120 copies or under. What does the optimizer return for expected profit? | `model.f2d1_cap = Constraint(expr=model.ship['f2', 'd1'] <= 120)` | 10771.35 |
| WHAT-IF/new_constraint | There's a proposal to keep press f3 running at least 500 copies to hold the union shift. Plug it in and walk me through the profit. | `model.f3_floor = Constraint(expr=model.product['f3'] >= 500)` | 10788.8 |
| WHAT-IF/new_constraint | Newsstand d5 has limited rack space. Let's try capping what it receives at 550 copies and see the profit impact. | `model.d5_cap = Constraint(expr=model.received['d5'] <= 550)` | 10515.5 |
| WHY-NOT/constraint_rule | Press f3 sends a small trickle to newsstand d2. Shouldn't that f3-to-d2 lane be held under 60 copies and consolidated elsewhere? What's keeping the model from doing that? | `model.f3d2_cap = Constraint(expr=model.ship['f3', 'd2'] <= 60)` | 10742.6 |
| WHY-NOT/constraint_rule | Newsstand d1 is a flagship location. Wouldn't it make sense to guarantee it at least 200 copies? What's the model seeing that I'm not? | `model.d1_floor = Constraint(expr=model.received['d1'] >= 200)` | 10010.0 |

### srkandw_lp  (5)  — `testing_library/feas_test/srkandw_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We want to keep the raw-1 ingredient line moving in the second run for freshness — at least 12 units bought then. What does the optimizer return for total cost? | `model.raw1_t2_floor = Constraint(expr=model.x['raw-1', 'time-2'] >= 12)` | 2927.4 |
| WHAT-IF/new_constraint | There's a proposal to smooth our first-run intake by holding raw-2 buying to 12 units in run one. Plug it in and walk me through the cost. | `model.raw2_t1_cap = Constraint(expr=model.x['raw-2', 'time-1'] <= 12)` | 2807.4 |
| WHY-NOT/constraint_rule | We're loading 30 units of raw-2 into the second run, which feels heavy. Shouldn't we hold second-run raw-2 to 22 units? What's keeping the model from doing that? | `model.raw2_t2_cap = Constraint(expr=model.x['raw-2', 'time-2'] <= 22)` | 2801.4 |
| WHY-NOT/constraint_rule | Raw-1 sits at zero in the first run, which seems like an underused ingredient. Shouldn't we commit at least 15 units of raw-1 up front? What's the model seeing that I'm not? | `model.raw1_t1_floor = Constraint(expr=model.x['raw-1', 'time-1'] >= 15)` | 3090.0 |
| WHY-NOT/constraint_rule | Leaving raw-1 out of the second run too looks risky for blend flexibility. Wouldn't it be smarter to run at least 20 units of raw-1 in run two? Walk me through what's pulling the plan the other way. | `model.raw1_t2_floor20 = Constraint(expr=model.x['raw-1', 'time-2'] >= 20)` | 3137.0 |

### sroute_lp  (9)  — `testing_library/feas_test/sroute_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | The Boston-to-Chicago link is going down for maintenance. Let's see what the routing costs if we can't send any Boston traffic over that leg. | `model.no_bos_chi = Constraint(expr=model.x['boston', 'boston', 'chicago'] <= 0)` | 6548.0 |
| WHAT-IF/new_constraint | Suppose the Chicago-to-Kansas-City arc is closed to the Chicago shipment. What does the optimizer return for total cost? | `model.no_chi_kc = Constraint(expr=model.x['chicago', 'chicago', 'kansas-cty'] <= 0)` | 6500.0 |
| WHAT-IF/new_constraint | There's a proposal to take the Dallas-to-Kansas-City link off the table for Dallas flow. Run it and tell me the cost. | `model.no_dal_kc = Constraint(expr=model.x['dallas', 'dallas', 'kansas-cty'] <= 0)` | 6496.0 |
| WHAT-IF/new_constraint | We're evaluating dropping the Chicago-to-Salt-Lake hop from the Boston routing. What's the resulting cost? | `model.no_bos_chi_slc = Constraint(expr=model.x['boston', 'chicago', 'salt-lake'] <= 0)` | 6483.0 |
| WHAT-IF/new_constraint | Leadership wants to understand a worst-case routing budget. If we force the plan to spend at least 7000 in total, what mix does the optimizer settle on? | `model.cost_floor = Constraint(expr=model.cost >= 7000)` | 7000.0 |
| WHY-NOT/constraint_rule | Sending Boston traffic down to Washington feels like a detour. Is there a reason we couldn't just avoid the Boston-to-Washington leg entirely? What's the model seeing that I'm not? | `model.no_bos_wdc = Constraint(expr=model.x['boston', 'boston', 'wash-dc'] <= 0)` | 6608.0 |
| WHY-NOT/constraint_rule | Routing Memphis flow back up through Chicago looks backward to me. Couldn't we just keep Memphis off the Memphis-to-Chicago arc? Walk me through the tradeoff. | `model.no_mem_chi = Constraint(expr=model.x['memphis', 'memphis', 'chicago'] <= 0)` | 6492.0 |
| WHY-NOT/constraint_rule | The LA-to-Dallas corridor is a natural trunk — shouldn't we be pushing at least 5 units of LA traffic onto it? What's keeping the model from leaning on it more? | `model.la_dal_trunk = Constraint(expr=model.x['losangeles', 'losangeles', 'dallas'] >= 5)` | 6478.0 |
| WHY-NOT/constraint_rule | Dallas leaning so hard on the Memphis leg seems lopsided. Wouldn't it be better to keep Dallas off the Dallas-to-Memphis arc? What's pulling the plan that way? | `model.no_dal_mem = Constraint(expr=model.x['dallas', 'dallas', 'memphis'] <= 0)` | 6516.0 |

### stablem_mip  (8)  — `testing_library/feas_test/stablem_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Cindy and Carl mentioned they'd rather not be paired off this round for personal reasons. If we take that pairing off the table entirely, what total preference score does the optimizer return? | `model.no_cindy_carl = Constraint(expr=model.match['Cindy', 'Carl'] == 0)` | 10.0 |
| WHAT-IF/new_constraint | We're curious how the matching reshuffles if Debbie is committed to Carl up front. Suppose we lock Debbie in with Carl — what does the optimizer report for the overall preference score? | `model.fix_debbie_carl = Constraint(expr=model.match['Debbie', 'Carl'] == 1)` | 10.0 |
| WHAT-IF/new_constraint | Say Alice has her heart set on Bob and wants that pairing guaranteed. If we hold Alice-and-Bob fixed in the plan, what's the total preference score the model comes back with? | `model.fix_alice_bob = Constraint(expr=model.match['Alice', 'Bob'] == 1)` | 12.0 |
| WHAT-IF/new_constraint | We want to look at the scenario where Debbie definitely isn't paired with Bob this cycle. If we rule out the Debbie-Bob match, what total preference score does the network settle on? | `model.no_debbie_bob = Constraint(expr=model.match['Debbie', 'Bob'] == 0)` | 10.0 |
| WHY-NOT/constraint_rule | Cindy rates Carl as her absolute top choice, yet I keep wondering why we don't try her elsewhere. Couldn't we just hand Cindy to Bob instead and see if it holds together? What's the model seeing that makes Carl the call? | `model.cindy_to_bob = Constraint(expr=model.match['Cindy', 'Bob'] == 1)` | 10.0 |
| WHY-NOT/constraint_rule | Alice winds up with Alan, but Alan isn't anywhere near her favorite. Shouldn't we be able to pair Cindy with Alan and free Alice up? What's pulling the optimizer away from putting Cindy and Alan together? | `model.cindy_alan = Constraint(expr=model.match['Cindy', 'Alan'] == 1)` | 12.0 |
| WHY-NOT/constraint_rule | I don't get why Alice is locked onto Alan at all — that lane never seems to move. Wouldn't taking Alice-Alan off the board open up something better overall? What's the tradeoff the model is protecting by keeping them together? | `model.drop_alice_alan = Constraint(expr=model.match['Alice', 'Alan'] == 0)` | 12.0 |
| WHY-NOT/constraint_rule | Debbie ends up with Bob, but on paper Carl looks like a perfectly reasonable partner for her. Why couldn't we just commit Debbie to Carl from the start? What's the model weighing that rules that out as the better plan? | `model.debbie_carl = Constraint(expr=model.match['Debbie', 'Carl'] == 1)` | 10.0 |

### stockcc_easy_mip  (5)  — `testing_library/feas_test/stockcc_easy_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to pin item 21 onto reorder schedule i4. We're just evaluating it — lock that assignment in and tell me the resulting total cost. | `model.fix_n21 = Constraint(expr=model.z['n21', 'i4'] == 1)` | 123479.78499999996 |
| WHAT-IF/new_constraint | We're looking at bumping item 30 up to reorder schedule i5 to tighten its stock. Put that in the model and let me see what it does to total cost. | `model.fix_n30 = Constraint(expr=model.z['n30', 'i5'] == 1)` | 124624.52166666664 |
| WHY-NOT/constraint_rule | Item 27 carries real value, yet the plan leaves it on the bare-minimum reorder schedule. Shouldn't a SKU like that be replenished far more often — say schedule i5? What's the model seeing that keeps it pinned at the floor? | `model.want_n27 = Constraint(expr=model.z['n27', 'i5'] == 1)` | 125356.62166666662 |
| WHY-NOT/constraint_rule | Item 22 is also sitting at the minimum reorder frequency even though it's not a trivial SKU. Wouldn't it be obvious to move it up to schedule i4? What's the tradeoff pulling the plan the other way? | `model.want_n22 = Constraint(expr=model.z['n22', 'i4'] == 1)` | 123293.52249999995 |
| WHY-NOT/constraint_rule | Item 48 is our single most valuable SKU. Shouldn't we be reordering it as aggressively as the system allows — right up at the top i9 schedule? What's keeping the plan from maxing out its replenishment? | `model.want_n48 = Constraint(expr=model.z['n48', 'i9'] == 1)` | 357714.33192307694 |

### swath_mip  (3)  — `testing_library/feas_test/swath_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Operations wants to try forcing the mission to swing over to the far cluster early — specifically having the aircraft head straight from swath s0 into swath s5. If we require that s5 is scanned immediately after s0, what's the resulting total flight distance? | `model.link_s0s5 = Constraint(expr=model.y['s0', 's5'] >= 1)` | 342.412068 |
| WHAT-IF/new_constraint | We're checking the sensitivity of the route to one specific ordering choice: what happens to the total distance if we don't allow s17 to be flown directly after s19 — forcing the model to find another way to weave those two in? | `model.no_s19s17 = Constraint(expr=model.y['s19', 's17'] <= 0)` | 336.65536999999995 |
| WHY-NOT/constraint_rule | These swaths split into a near cluster and a far cluster, and the plan never actually bridges them in one sweep — it just makes little loops inside each. Couldn't we force a real crossover, say require the aircraft to fly straight from s4 over to s10 to stitch the two regions together? What's keeping the optimizer from connecting them like that? | `model.bridge_s4s10 = Constraint(expr=model.y['s4', 's10'] >= 1)` | 449.04398999999995 |

### tablelayout_mip  (4)  — `testing_library/feas_test/tablelayout_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Column 2 holds a wide header that the designers want to give some breathing room. If we insist column 2 be at least 90 units wide, what total height does the layout work out to? | `model.col2_wide = Constraint(expr=model.xCw[2] >= 90)` | 150.0 |
| WHY-NOT/constraint_rule | The header row, row 0, is sitting at 30 units but it really should stand out more. Couldn't we just give it the 40-unit band? What's the tradeoff the optimizer is making by keeping it shorter? | `model.r0_tall = Constraint(expr=model.bRH[0, 40] == 1)` | 140.0 |
| WHY-NOT/constraint_rule | Row 3 keeps landing on a short band, but its longest cell looks like it needs room. Wouldn't it be cleaner to just lock row 3 onto the 40-unit band outright? What's keeping the model from doing that on its own? | `model.r3_tall = Constraint(expr=model.bRH[3, 40] == 1)` | 150.0 |
| WHY-NOT/constraint_rule | Column 3 comes out at 62 units, which feels tight for what's in it. Surely we could widen it to at least 80 without hurting anything? What's the optimizer weighing that keeps it that narrow? | `model.col3_wide = Constraint(expr=model.xCw[3] >= 80)` | 130.0 |

### tabora_lp  (2)  — `testing_library/feas_test/tabora_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at limiting the maize-after-tobacco rotation in year one to 150 hectares, to keep the rotation manageable for the families. What does discounted income become with that in place? | `model.mat_y01_cap = Constraint(expr=model.mat[1] <= 150)` | 8421.349431811926 |
| WHY-NOT/constraint_rule | The plan throws a lot of tobacco at the fields in the first year. Couldn't we dial that back and hold year-one tobacco under 180 hectares? What's the model seeing that makes it want to push tobacco so hard up front? | `model.tobacco_y01_cap = Constraint(expr=model.x[1, 'tobacco'] <= 180)` | 8330.138513535308 |

### tba_mip  (2)  — `testing_library/feas_test/tba_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at not filling the last lot this cycle — leave l4 unallocated. What does that do to the profit on the trade? | `model.drop_l4 = Constraint(expr=model.w[20580252, 'l4'] == 0)` | 27.719999999999743 |
| WHY-NOT/constraint_rule | We're stretching to fill all four lots, and l4 looks like the thin one. Wouldn't it be cleaner to just let l4 fail and not chase it? What's the desk getting out of filling that last lot? | `model.want_drop_l4 = Constraint(expr=model.w[20580252, 'l4'] == 0)` | 27.719999999999743 |

### tfordy_lp  (3)  — `testing_library/feas_test/tfordy_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | The plan leans awfully hard on the main pulp line right at the end of the horizon. Couldn't we hold the pulp-pl process in period-9 under 5 and spread things out? What's the model seeing that makes it run it flat out there? | `model.late_pulp_cap = Constraint(expr=model.z['pulp-pl', 'period-9'] <= 5.0)` | 102.0221797634531 |
| WHY-NOT/constraint_rule | It looks like we're slamming the pulplog harvest in the very last period of the extended horizon. Shouldn't we keep that final-period pulplog supply under 9 to be gentler on the forest? What's the tradeoff the model is making? | `model.last_harvest_cap = Constraint(expr=model.r['pulplogs', 'period-12'] <= 9.0)` | 99.94665842435336 |
| WHY-NOT/constraint_rule | There's a big lumpy pulp-mill investment landing in period-7. Couldn't we just keep that single-period build under 2.5 and avoid the spike? What's pushing the model to put so much in at once? | `model.lumpy_build_cap = Constraint(expr=model.h['pulp-mill', 'period-7'] <= 2.5)` | 102.02962697547781 |

### tforss_lp  (3)  — `testing_library/feas_test/tforss_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're evaluating a commissioning floor for the pulp mill: the build has to stand up a pulp-mill line of at least 800 thousand m3/year of throughput capacity so it clears the minimum economic scale. With that floor in place, where does the total benefit land? | `model.pulpmill_min_scale = Constraint(expr=model.h['pulp-mill'] >= 800.0)` | 2013.767173523538 |
| WHAT-IF/new_constraint | There's a long-term supply contract on the table that would commit us to shipping at least 160 thousand units of pulp a year. If we lock that pulp delivery floor in, what does the optimizer return for total benefit? | `model.pulp_supply_floor = Constraint(expr=model.x['pulp'] >= 160.0)` | 2058.336062519271 |
| WHAT-IF/new_constraint | There's a proposal to stand up a small sawnwood line to serve a regional builder — they want us to commit to at least 50 thousand units of sawnwood shipments a year. Plug that in and tell me where total benefit ends up. | `model.sawnwood_floor = Constraint(expr=model.x['sawnwood'] >= 50.0)` | 564.3520885971666 |

### thai_mip  (7)  — `testing_library/feas_test/thai_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Command wants the combined Chumphon-Surat run (voyage v-05) exercised at least once for coordination. Let's see what requiring one large-ship v-05 sailing does to the plan. | `model.use_v05 = Constraint(expr=model.z['v-05', 'large'] >= 1)` | 214.961 |
| WHAT-IF/new_constraint | There's a proposal to keep voyage v-11 in rotation — require at least one large-ship v-11 sailing. What does the optimizer return for the objective? | `model.use_v11 = Constraint(expr=model.z['v-11', 'large'] >= 1)` | 217.887 |
| WHAT-IF/new_constraint | We're evaluating forcing the longer voyage v-12 into the schedule for coverage. If we require one large-ship v-12 sailing, what's the resulting objective? | `model.use_v12 = Constraint(expr=model.z['v-12', 'large'] >= 1)` | 224.41000000000003 |
| WHAT-IF/new_constraint | Suppose the v-09 sailing must also pick up at least 200 men from Surat on its way. How does that requirement change the objective? | `model.v09_surat = Constraint(expr=model.y['v-09', 'large', 'surat'] >= 200)` | 225.461 |
| WHY-NOT/constraint_rule | We're running the medium-ship v-01 voyage twice. Shouldn't a single v-01 sailing be enough? What's keeping the model from cutting it to one? | `model.cap_v01 = Constraint(expr=model.z['v-01', 'medium'] <= 1)` | 215.32850000000002 |
| WHY-NOT/constraint_rule | Sending the v-09 large-ship voyage out twice looks heavy. Wouldn't a single v-09 sailing do? Walk me through what's pulling the plan toward two. | `model.cap_v09 = Constraint(expr=model.z['v-09', 'large'] <= 1)` | 216.90800000000002 |
| WHY-NOT/constraint_rule | Is the direct Nakon run (v-03 large) really necessary? Couldn't we just drop it and cover Nakon another way? What's the model seeing that I'm not? | `model.drop_v03 = Constraint(expr=model.z['v-03', 'large'] <= 0)` | 212.711 |

### thaix_mip  (7)  — `testing_library/feas_test/thaix_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at spreading the Songkhla lift so we're not leaning so hard on a single voyage. Suppose we hold the men carried on voyage v-09 into Songkhla to at most 900 and let the rest of the roster pick up the slack — what total man-miles does the optimizer return? | `model.cap_v09_song = Constraint(expr=model.y['v-09', 'large', 'songkhla'] <= 900)` | 1687460.0 |
| WHAT-IF/new_constraint | There's interest in keeping voyage v-13 in regular rotation to Songkhla for redundancy. If we commit at least 200 men to ride v-13 into Songkhla each cycle, where do the total man-miles land? | `model.use_v13_song = Constraint(expr=model.y['v-13', 'large', 'songkhla'] >= 200)` | 1734530.0 |
| WHAT-IF/new_constraint | We're curious what happens if we bring the multi-stop voyage v-05 into play. Say we require at least one large-ship sailing of v-05 — what's the resulting man-miles total? | `model.open_v05 = Constraint(expr=model.z['v-05', 'large'] >= 1)` | 1665005.0 |
| WHY-NOT/constraint_rule | Songkhla has its own dedicated direct run, voyage v-04, yet the plan never sails it — everything goes through the shared v-09. Shouldn't we be putting v-04 to work, say at least one sailing? What's the model seeing that makes leaving it idle the better call? | `model.force_v04 = Constraint(expr=model.z['v-04', 'large'] >= 1)` | 1687460.0 |
| WHY-NOT/constraint_rule | We're leaning awfully hard on voyage v-09 — it's doing two sailings and carrying the whole Songkhla load. Couldn't we just take it out of the rotation entirely and let the other voyages cover the ground? What's pulling the optimizer toward depending on it? | `model.ban_v09 = Constraint(expr=model.z['v-09', 'large'] == 0)` | 1738460.0 |
| WHY-NOT/constraint_rule | Loading 1123 men onto a single voyage's sailings feels like all our eggs in one basket. Shouldn't we cap what v-09 carries into Songkhla at 600 and split the rest across other runs? What's the trade-off the model is making by concentrating it? | `model.cap_v09_600 = Constraint(expr=model.y['v-09', 'large', 'songkhla'] <= 600)` | 1687460.0 |
| WHY-NOT/constraint_rule | Chumphon is the closest port and the plan only touches it with small and medium hulls. Wouldn't it be worth pushing a large ship through there too — say lift at least 200 of Chumphon's men on the large-ship voyage v-07? What's keeping the model from doing that? | `model.chum_large = Constraint(expr=model.y['v-07', 'large', 'chumphon'] >= 200)` | 1815490.0 |

### trip_mip  (1)  — `testing_library/feas_test/trip_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHY-NOT/constraint_rule | The plan keeps leaning on that node-2 start link out to node 4 at period 3, and it looks like a detour to me. Shouldn't we just leave that link inactive and route around it? What's keeping the model from making that move? | `model.no_2043 = Constraint(expr=model.delta[2, 0, 4, 3] == 0)` | 3440.944466431542 |

### trnsgrid_lp  (6)  — `testing_library/feas_test/trnsgrid_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to ease the long San Diego-to-Topeka haul by holding it to 175 pallets. Plug it in and walk me through the cost. | `model.sd_top_cap = Constraint(expr=model.x['san-diego', 'topeka'] <= 175)` | 157.725 |
| WHAT-IF/new_constraint | We'd like Seattle to carry a solid share of the New York shelter — at least 175 pallets on that lane. Let's see the cost impact. | `model.sea_ny_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 175)` | 154.8 |
| WHY-NOT/constraint_rule | San Diego is hauling a big load all the way to New York. Shouldn't we hold that lane under 175 pallets and let Seattle pick up more of New York? What's keeping the model from doing that? | `model.sd_ny_cap = Constraint(expr=model.x['san-diego', 'new-york'] <= 175)` | 154.575 |
| WHY-NOT/constraint_rule | The Seattle-to-Chicago lane is carrying a lot. Wouldn't holding it to 225 pallets spread our trucks more evenly? What's the model seeing that I'm not? | `model.sea_chi_cap = Constraint(expr=model.x['seattle', 'chicago'] <= 225)` | 154.35 |
| WHY-NOT/constraint_rule | Seattle never trucks to Topeka, leaving a northern route idle. Shouldn't Seattle run at least 75 pallets to Topeka for coverage? Walk me through what's pulling the plan the other way. | `model.sea_top_floor = Constraint(expr=model.x['seattle', 'topeka'] >= 75)` | 156.6 |
| WHY-NOT/constraint_rule | San Diego sits idle on the Chicago shelter even with spare stock. Couldn't it just cover at least 75 pallets of Chicago for backup? What's the tradeoff I'm missing? | `model.sd_chi_floor = Constraint(expr=model.x['san-diego', 'chicago'] >= 75)` | 154.35 |

### trnsindic_mip  (7)  — `testing_library/feas_test/trnsindic_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're stress-testing our reliance on the San Diego-to-New-York pipe in case that corridor gets congested. Suppose we hold that single lane to at most 250 cases and let the network make up the rest elsewhere — what total cost does the optimizer come back with? | `model.cap_sdny = Constraint(expr=model.x['san-diego', 'new-york'] <= 250)` | 154.674 |
| WHAT-IF/new_constraint | The Topeka receiving dock can only take so much from one source. Let's look at the case where San Diego's deliveries into Topeka are capped at 200 cases — what does that scenario cost overall? | `model.cap_sdtop = Constraint(expr=model.x['san-diego', 'topeka'] <= 200)` | 158.267 |
| WHAT-IF/new_constraint | Sales wants a standing presence on the San Diego-Chicago route for service reasons. If we commit San Diego to put at least 100 cases into Chicago every cycle, where does the total cost land? | `model.sd_chi_base = Constraint(expr=model.x['san-diego', 'chicago'] >= 100)` | 154.674 |
| WHY-NOT/constraint_rule | Topeka sits closer to Seattle on the map, yet the plan never ships there from Seattle at all — it's all San Diego. Shouldn't Seattle be carrying at least a chunk of Topeka, say 100 cases? What's the model seeing that makes that a bad idea? | `model.sea_top = Constraint(expr=model.x['seattle', 'topeka'] >= 100)` | 158.267 |
| WHY-NOT/constraint_rule | New York is the biggest market and we're sourcing the whole thing from San Diego. Couldn't Seattle pitch in even 50 cases to spread the risk? What's pulling the optimizer away from splitting that? | `model.sea_ny = Constraint(expr=model.x['seattle', 'new-york'] >= 50)` | 154.674 |
| WHY-NOT/constraint_rule | I notice the Seattle-to-Topeka lane is sitting completely shut in the plan. Is there a reason we couldn't just open that arc and route something over it? What's the tradeoff the model is making by keeping it dark? | `model.open_seatop = Constraint(expr=model.use['seattle', 'topeka'] >= 1)` | 158.267 |
| WHY-NOT/constraint_rule | Wouldn't it be more resilient to have Seattle wired into the New York market too, instead of leaving that arc switched off entirely? What's keeping the model from opening the Seattle-to-New-York lane? | `model.open_seany = Constraint(expr=model.use['seattle', 'new-york'] >= 1)` | 154.674 |

### trnsport_lp  (6)  — `testing_library/feas_test/trnsport_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal on the table to keep the Seattle-to-Chicago lane from getting too concentrated — hold it at 250 cases or under. Plug that in and walk me through the resulting cost and shipment mix. | `model.sea_chi_cap = Constraint(expr=model.x['seattle', 'chicago'] <= 250)` | 154.125 |
| WHAT-IF/new_constraint | Logistics wants to keep the northern Seattle-to-Topeka corridor active for service-continuity reasons — say at least 100 cases on it. Let's try that and see what it does to the total bill. | `model.sea_top_floor = Constraint(expr=model.x['seattle', 'topeka'] >= 100)` | 157.725 |
| WHY-NOT/constraint_rule | San Diego is hauling a big load all the way up to New York while it's also our southern supplier. Shouldn't we keep San Diego's New York shipment under 200 cases and let Seattle carry more of that eastern demand? What's keeping the model from doing that? | `model.sd_ny_cap = Constraint(expr=model.x['san-diego', 'new-york'] <= 200)` | 154.35 |
| WHY-NOT/constraint_rule | It looks odd that Topeka leans entirely on San Diego. Wouldn't it be more resilient to hold San Diego's Topeka shipment under 200 cases so the supply is shared? What's the model seeing that I'm not? | `model.sd_top_cap = Constraint(expr=model.x['san-diego', 'topeka'] <= 200)` | 156.6 |
| WHY-NOT/constraint_rule | Seattle is our closer plant to the east, yet it barely touches New York. Shouldn't Seattle be pulling at least 150 cases of the New York demand? Walk me through what's pulling it the other way. | `model.sea_ny_floor = Constraint(expr=model.x['seattle', 'new-york'] >= 150)` | 154.575 |
| WHY-NOT/constraint_rule | San Diego is sending 275 cases to far-off New York. Couldn't we just hold that lane to 250 and route the rest more sensibly? What's the tradeoff I'm missing? | `model.sd_ny_cap250 = Constraint(expr=model.x['san-diego', 'new-york'] <= 250)` | 153.9 |

### trnspwl_mip  (8)  — `testing_library/feas_test/trnspwl_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to open up a Seattle-to-New-York lane and route at least 100 cases over it. Plug that in — what does it do to the total shipping cost? | `model.open_sea_ny = Constraint(expr=model.x['seattle', 'new-york'] >= 100)` | 8.942471957048319 |
| WHAT-IF/new_constraint | We're evaluating having Seattle cover part of Topeka — say at least 100 cases out of Seattle to Topeka. What's the resulting cost? | `model.sea_top = Constraint(expr=model.x['seattle', 'topeka'] >= 100)` | 9.961530244472991 |
| WHAT-IF/new_constraint | Suppose the Seattle-to-Chicago corridor gets throttled to no more than 150 cases. Run it and tell me the new total cost. | `model.cap_sea_chi = Constraint(expr=model.x['seattle', 'chicago'] <= 150)` | 8.942471957048319 |
| WHAT-IF/new_constraint | Let's try having San Diego pick up at least 150 cases of the Chicago demand. What does the optimizer return for total cost? | `model.sd_chi = Constraint(expr=model.x['san-diego', 'chicago'] >= 150)` | 8.942471957048319 |
| WHAT-IF/new_constraint | There's a plan on the table to take San Diego off the New York route entirely. Add that and let me see the cost impact. | `model.no_sd_ny = Constraint(expr=model.x['san-diego', 'new-york'] == 0)` | 8.942471957048319 |
| WHY-NOT/constraint_rule | Topeka feels like it ought to lean on Seattle, yet the plan ships every last case of it out of San Diego. Shouldn't Seattle be carrying all of Topeka's demand? What's the model seeing that keeps it off that lane? | `model.want_sea_top = Constraint(expr=model.x['seattle', 'topeka'] >= 275)` | 9.961530244472991 |
| WHY-NOT/constraint_rule | Seattle sits completely idle on the New York lane while San Diego hauls the whole 325 cases out there. Shouldn't Seattle be pulling at least 200 of that load? What's the trade-off pushing it all onto San Diego? | `model.want_sea_ny = Constraint(expr=model.x['seattle', 'new-york'] >= 200)` | 8.942471957048319 |
| WHY-NOT/constraint_rule | Seattle hogs the entire Chicago order. Couldn't San Diego just handle all of Chicago instead and free Seattle up? What's keeping the optimizer from routing Chicago through San Diego? | `model.want_sd_chi = Constraint(expr=model.x['san-diego', 'chicago'] >= 300)` | 8.942471957048319 |

### trnspwlx_mip  (8)  — `testing_library/feas_test/trnspwlx_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to open a Seattle-to-New-York lane carrying at least 100 cases. Plug it in — what does it do to the total cost? | `model.open_sea_ny = Constraint(expr=model.x['seattle', 'new-york'] >= 100)` | 9.16098091496113 |
| WHAT-IF/new_constraint | We're evaluating having Seattle take on part of Topeka — at least 100 cases out of Seattle. What's the resulting cost? | `model.sea_top = Constraint(expr=model.x['seattle', 'topeka'] >= 100)` | 10.168759124337159 |
| WHAT-IF/new_constraint | Suppose the Seattle-to-Chicago corridor is capped at 150 cases. Run it and tell me the new total cost. | `model.cap_sea_chi = Constraint(expr=model.x['seattle', 'chicago'] <= 150)` | 9.16098091496113 |
| WHAT-IF/new_constraint | Let's try having San Diego cover at least 150 cases of the Chicago demand. What does the optimizer return for total cost? | `model.sd_chi = Constraint(expr=model.x['san-diego', 'chicago'] >= 150)` | 9.16098091496113 |
| WHAT-IF/new_constraint | There's a plan to take San Diego off the New York lane completely. Add that and let me see the cost impact. | `model.no_sd_ny = Constraint(expr=model.x['san-diego', 'new-york'] == 0)` | 9.16098091496113 |
| WHY-NOT/constraint_rule | Topeka looks like Seattle's natural territory, yet the plan ships all of it from San Diego. Shouldn't Seattle be carrying Topeka's whole demand? What's the model seeing that keeps it off that route? | `model.want_sea_top = Constraint(expr=model.x['seattle', 'topeka'] >= 275)` | 10.168759124337159 |
| WHY-NOT/constraint_rule | Seattle barely touches the New York lane while San Diego runs the whole load out there. Shouldn't Seattle be pulling at least 200 cases of New York? What's the trade-off pushing it all onto San Diego? | `model.want_sea_ny = Constraint(expr=model.x['seattle', 'new-york'] >= 200)` | 9.16098091496113 |
| WHY-NOT/constraint_rule | Seattle runs the entire Chicago order. Couldn't San Diego just take all of Chicago and free Seattle up? What's keeping the optimizer from routing Chicago through San Diego? | `model.want_sd_chi = Constraint(expr=model.x['san-diego', 'chicago'] >= 300)` | 9.16098091496113 |

### tsp1_mip  (3)  — `testing_library/feas_test/tsp1_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A customer in city 4 wants their stop served on the leg immediately after city 3, so the route has to run straight from 3 into 4. Pin that leg in and tell me the resulting route distance. | `model.direct_34 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 92.0 |
| WHAT-IF/new_constraint | There's a proposal to route the truck straight from city 6 to city 3 as part of the loop. Put that leg in and let me see what the tour distance becomes. | `model.direct_63 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 110.0 |
| WHY-NOT/constraint_rule | Cities 3 and 4 sit close together, yet the plan never runs a leg straight from 4 into 3 — it detours instead. Shouldn't there be a direct 4-to-3 hop? What's pulling the route the other way? | `model.want_43 = Constraint(expr=model.x['i4', 'i3'] == 1)` | 94.0 |

### tsp2_mip  (4)  — `testing_library/feas_test/tsp2_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're scoping a delivery agreement that would commit the driver to running the city 1 to city 4 leg directly every run. If we pin that arc into the route, what total cost does the optimizer come back with? | `model.frc_i1i4 = Constraint(expr=model.x['i1', 'i4'] == 1)` | 75.0 |
| WHAT-IF/new_constraint | A customer at city 4 wants their pickup to come straight off the city 2 stop. Suppose we require the route to run the city 2 to city 4 leg — what's the resulting total cost of the loop? | `model.frc_i2i4 = Constraint(expr=model.x['i2', 'i4'] == 1)` | 75.0 |
| WHY-NOT/constraint_rule | City 3 sits way out on its own, and the plan tiptoes in and out of it on the cheap city-10 and city-1 hops. Shouldn't the driver just barrel in from city 6 directly and be done with it? If we made the route enter city 3 from city 6, what is the model seeing that makes that a bad call? | `model.why_i6i3 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 79.0 |
| WHY-NOT/constraint_rule | I keep looking at the map and city 3 to city 4 looks like the obvious way to leave that corner of the network. Why isn't the optimizer running the city 3 to city 4 leg? Force it in and show me what it actually costs us. | `model.why_i3i4 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 97.0 |

### tsp3_subt1_mip  (3)  — `testing_library/feas_test/tsp3_subt1_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A customer in city 4 wants their stop served on the leg immediately after city 3, so the route has to run straight from 3 into 4. Pin that leg in and tell me the resulting route distance. | `model.direct_34 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 92.0 |
| WHAT-IF/new_constraint | There's a proposal to route the truck straight from city 6 to city 3 as part of the loop. Put that leg in and let me see what the tour distance becomes. | `model.direct_63 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 110.0 |
| WHY-NOT/constraint_rule | Cities 3 and 4 sit close together, yet the plan never runs a leg straight from 4 into 3 — it detours instead. Shouldn't there be a direct 4-to-3 hop? What's pulling the route the other way? | `model.want_43 = Constraint(expr=model.x['i4', 'i3'] == 1)` | 94.0 |

### tsp3_subt2_mip  (3)  — `testing_library/feas_test/tsp3_subt2_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A customer in city 4 wants their stop served on the leg immediately after city 3, so the route has to run straight from 3 into 4. Pin that leg in and tell me the resulting route distance. | `model.direct_34 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 92.0 |
| WHAT-IF/new_constraint | There's a proposal to route the truck straight from city 6 to city 3 as part of the loop. Put that leg in and let me see what the tour distance becomes. | `model.direct_63 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 110.0 |
| WHY-NOT/constraint_rule | Cities 3 and 4 sit close together, yet the plan never runs a leg straight from 4 into 3 — it detours instead. Shouldn't there be a direct 4-to-3 hop? What's pulling the route the other way? | `model.want_43 = Constraint(expr=model.x['i4', 'i3'] == 1)` | 94.0 |

### tsp42_match_mip  (5)  — `testing_library/feas_test/tsp42_match_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to wire stop 1 directly to stop 42 with a dedicated link. Force that edge into the plan and tell me what the total routing length becomes. | `model.use_1_42 = Constraint(expr=model.x['c42', 'c1'] == 1)` | 647.0 |
| WHAT-IF/new_constraint | We're evaluating a fixed link between stop 5 and stop 25 to serve a new contract. Pin that edge in and let me see the resulting routing length. | `model.use_5_25 = Constraint(expr=model.x['c25', 'c5'] == 1)` | 677.0 |
| WHAT-IF/new_constraint | Suppose the link between stop 1 and stop 2 is taken out of service. Drop that edge from the available connections and tell me how the total length shifts. | `model.drop_1_2 = Constraint(expr=model.x['c2', 'c1'] == 0)` | 648.0 |
| WHAT-IF/new_constraint | There's a plan to commit to a long cross-network link between stop 1 and stop 21. Force that edge in and tell me what it does to the total routing length. | `model.use_1_21 = Constraint(expr=model.x['c21', 'c1'] == 1)` | 785.0 |
| WHAT-IF/new_constraint | We're looking at a scenario where stop 10 must be wired straight to stop 30. Add that link and let me see the new total length. | `model.use_10_30 = Constraint(expr=model.x['c30', 'c10'] == 1)` | 686.0 |

### tsp42_tsp_mip  (8)  — `testing_library/feas_test/tsp42_tsp_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A customer at stop 11 wants their delivery on the leg right after the depot at stop 1, so the route has to run straight from 1 into 11. Lock that leg in and tell me what the full tour ends up costing. | `model.direct_1_11 = Constraint(expr=model.x['c1', 'c11'] == 1)` | 774.0 |
| WHAT-IF/new_constraint | There's a proposal to send the truck straight from stop 1 over to stop 21 as part of the loop. Put that leg in and let me see the resulting tour distance. | `model.direct_1_21 = Constraint(expr=model.x['c1', 'c21'] == 1)` | 800.0 |
| WHAT-IF/new_constraint | We're evaluating committing the truck to a direct hop from stop 1 across to stop 25. Force that leg in and tell me what it does to the total tour distance. | `model.direct_1_25 = Constraint(expr=model.x['c1', 'c25'] == 1)` | 754.0 |
| WHAT-IF/new_constraint | Suppose dispatch wants stop 2 served straight into stop 12 on the next leg. Add that connection and let me see the new tour cost. | `model.direct_2_12 = Constraint(expr=model.x['c2', 'c12'] == 1)` | 781.0 |
| WHAT-IF/new_constraint | There's a plan on the table to route stop 2 directly over to stop 30. Pin that leg in and tell me what the tour distance becomes. | `model.direct_2_30 = Constraint(expr=model.x['c2', 'c30'] == 1)` | 763.0 |
| WHY-NOT/constraint_rule | The route loops stop 1 all the way around before getting anywhere near stop 31. Stop 31 looks like it should be an easy reach from the depot — shouldn't the truck just run from 1 straight into 31? What's the model seeing that keeps it from doing that? | `model.want_1_31 = Constraint(expr=model.x['c1', 'c31'] == 1)` | 764.0 |
| WHY-NOT/constraint_rule | Stop 2 and stop 22 both sit on the route, yet the plan never connects them directly — it threads a long way between them instead. Wouldn't a direct 2-to-22 leg tidy things up? What's the trade-off pulling the route the other way? | `model.want_2_22 = Constraint(expr=model.x['c2', 'c22'] == 1)` | 781.0 |
| WHY-NOT/constraint_rule | It seems wasteful that the truck never runs straight from stop 2 to stop 32. Shouldn't there be a direct 2-to-32 leg somewhere in the loop? What's keeping the model from making that move? | `model.want_2_32 = Constraint(expr=model.x['c2', 'c32'] == 1)` | 764.0 |

### tsp4_assign_mip  (3)  — `testing_library/feas_test/tsp4_assign_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A dispatcher wants city 3 hooked straight out to city 4 regardless of cost. Force that link in and tell me what the assignment total becomes. | `model.link_34 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 89.0 |
| WHAT-IF/new_constraint | There's a proposal to route city 3 straight out to the city-6 depot. Put that link in and tell me what the assignment ends up costing. | `model.link_36 = Constraint(expr=model.x['i3', 'i6'] == 1)` | 59.0 |
| WHAT-IF/new_constraint | The depot at city 6 is being told to feed city 3 directly on its outgoing link. Pin that in and let me see the resulting assignment total. | `model.link_63 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 61.0 |

### tsp4_tspcut_mip  (4)  — `testing_library/feas_test/tsp4_tspcut_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A customer at city 4 wants their stop served on the leg right after city 3, so the route has to run straight from 3 into 4. Lock that leg in and tell me what the full tour ends up costing. | `model.direct_34 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 97.0 |
| WHAT-IF/new_constraint | There's a proposal to route the truck straight from city 3 over to the city-6 depot as part of the loop. Put that leg in and let me see the resulting tour distance. | `model.direct_36 = Constraint(expr=model.x['i3', 'i6'] == 1)` | 77.0 |
| WHY-NOT/constraint_rule | The route sends city 3 the long way round through the 1-2 neighbourhood. The city-6 depot sits right there as a natural hub — shouldn't the truck just run from 6 straight into 3? What's the model seeing that keeps it from doing that? | `model.want_63 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 79.0 |
| WHY-NOT/constraint_rule | City 4 and city 3 are both on the agenda, yet the plan never runs a leg straight from 4 back into 3. Shouldn't there be a direct 4-to-3 hop somewhere in the loop? What's pulling the route away from it? | `model.want_43 = Constraint(expr=model.x['i4', 'i3'] == 1)` | 99.0 |

### tsp5_MTZ_mip  (6)  — `testing_library/feas_test/tsp5_MTZ_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | A customer at city 4 wants their stop served on the leg right after city 3, so the route must run straight from 3 into 4. Lock that leg in and tell me what the full tour ends up costing. | `model.direct_34 = Constraint(expr=model.x['i3', 'i4'] == 1)` | 97.0 |
| WHAT-IF/new_constraint | There's a proposal to route the truck straight from city 3 over to the city-6 hub as part of the loop. Put that leg in and let me see the resulting tour distance. | `model.direct_36 = Constraint(expr=model.x['i3', 'i6'] == 1)` | 77.0 |
| WHAT-IF/new_constraint | We're evaluating committing the truck to a direct hop from city 1 over to city 4. Force that leg in and tell me what it does to the total tour distance. | `model.direct_14 = Constraint(expr=model.x['i1', 'i4'] == 1)` | 75.0 |
| WHY-NOT/constraint_rule | City 4 and city 3 are both on the route, yet the plan never runs a leg straight from 4 back into 3 — it takes the long way instead. Shouldn't there be a direct 4-to-3 hop somewhere in the loop? What's pulling the route away from it? | `model.want_43 = Constraint(expr=model.x['i4', 'i3'] == 1)` | 99.0 |
| WHY-NOT/constraint_rule | The city-6 hub sits right beside the route, but the plan loops city 3 all the way around instead of feeding it from 6. Shouldn't the truck just run from 6 straight into 3? What's the model seeing that keeps it from doing that? | `model.want_63 = Constraint(expr=model.x['i6', 'i3'] == 1)` | 79.0 |
| WHY-NOT/constraint_rule | City 8 isn't all that far from city 3, but the route never links them directly. Wouldn't a straight 8-to-3 leg tidy up the loop? What's the trade-off that keeps the plan detouring around it? | `model.want_83 = Constraint(expr=model.x['i8', 'i3'] == 1)` | 58.0 |

### turkpow_lp  (6)  — `testing_library/feas_test/turkpow_lp.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | We're looking at a softer line on nuclear — suppose we hold total new nuclear capacity to no more than 20,000 MW over the whole horizon. What does the optimizer return for total cost under that ceiling? | `model.nuclear_cap = Constraint(expr=model.htt['nuclear'] <= 20000)` | 12935.337075449375 |
| WHAT-IF/new_constraint | Oil-fired plant is something we'd rather not lean on too heavily. If we limited total new oil capacity to 15,000 MW across the plan, what does the cost picture look like? | `model.oil_cap = Constraint(expr=model.htt['oil'] <= 15000)` | 12685.622665716463 |
| WHY-NOT/constraint_rule | The plan leans awfully hard on nuclear by the end. Shouldn't we keep total nuclear build under 30,000 MW rather than letting it run up to where it is? What's the model seeing that makes it push nuclear that far? | `model.nuclear_limit = Constraint(expr=model.htt['nuclear'] <= 30000)` | 12792.807119025585 |
| WHY-NOT/constraint_rule | Oil is the expensive fuel to run — couldn't we just trim total new oil capacity down to 18,000 MW? Why does the plan keep building oil out past that? | `model.oil_limit = Constraint(expr=model.htt['oil'] <= 18000)` | 12666.37481473284 |
| WHY-NOT/constraint_rule | Standing up a nuclear program as early as 1993 seems aggressive on lead times. Why not just hold off — no nuclear additions in the 1993 round at all? What's the tradeoff the model is weighing there? | `model.no_early_nuclear = Constraint(expr=model.ht['nuclear', 1993] <= 0)` | 12794.67996660242 |
| WHY-NOT/constraint_rule | That last 2005 oil expansion looks enormous. Couldn't we cap the new oil capacity added in 2005 at 10,000 MW and lean on something else? What keeps the plan from doing that on its own? | `model.oil_2005_limit = Constraint(expr=model.ht['oil', 2005] <= 10000)` | 12665.779782328145 |

### tvcsched_mip  (1)  — `testing_library/feas_test/tvcsched_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal on the table to anchor one of the green spots right in the lead-off slot. Pin a green to slot 1 and tell me what the spacing score comes to. | `model.lead_green = Constraint(expr=model.p['G', '1'] == 1)` | 7.5 |

### vietman_vietmip_mip  (4)  — `testing_library/feas_test/vietman_vietmip_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to bring the fertilizer plant at site 3 online — the regional authority wants production capacity in that area. Require plant 3's fertilizer line to be built and tell me what the new plan costs. | `model.open_z3 = Constraint(expr=model.z[3] == 1)` | 65680.46 |
| WHAT-IF/new_constraint | We're evaluating activating the northern ammonia plant at site 1 to shorten supply lines. With ammonia plant 1 switched on, what does the total cost come out to? | `model.open_w1 = Constraint(expr=model.w[1] == 1)` | 65936.18 |
| WHY-NOT/constraint_rule | The whole network leans on the single plant at site 2 — that's a lot of eggs in one basket. What if plant 2's fertilizer line went down? Shouldn't the plan avoid relying on it? Force fertilizer plant 2 offline and show me what it costs to serve demand without it. | `model.close_z2 = Constraint(expr=model.z[2] == 0)` | 65960.35 |
| WHY-NOT/constraint_rule | Plant 2 ships all 344 units of center 5's demand on its own. Wouldn't it be safer to cap any single plant's delivery to center 5 at 200 and bring a second source into that market? What's the tradeoff keeping it all on plant 2? | `model.split_c5 = Constraint(expr=model.y[2, 5] <= 200)` | 65960.35 |

### vietman_viettag_mip  (3)  — `testing_library/feas_test/vietman_viettag_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to bring the fertilizer plant at site 3 online for regional coverage. Require plant 3's fertilizer line to be built and tell me what the tagged plan costs. | `model.open_z3 = Constraint(expr=model.z[3] == 1)` | 65680.46 |
| WHAT-IF/new_constraint | We're evaluating switching on the northern ammonia plant at site 1 to shorten supply lines. With ammonia plant 1 active, what does the total cost come out to? | `model.open_w1 = Constraint(expr=model.w[1] == 1)` | 65936.18 |
| WHY-NOT/constraint_rule | The whole tagged network funnels through the single plant at site 2 — that's a real exposure if it goes offline. Shouldn't the plan avoid leaning entirely on plant 2's fertilizer line? Force it shut and show me what serving demand without it costs. | `model.close_z2 = Constraint(expr=model.z[2] == 0)` | 65960.35 |

### westmip_mip  (5)  — `testing_library/feas_test/westmip_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | There's a proposal to add a normal intermediate-goods capacity unit in period 3. Plug it in and tell me what happens to welfare. | `model.wf_force_f3 = Constraint(expr=model.f['3', 'intermed', 'normal'] == 1)` | 2890.248407212074 |
| WHAT-IF/new_constraint | We're evaluating holding finished-goods output in period 9 to no more than 150 units. What does the optimizer return for welfare? | `model.wf_cap_x9 = Constraint(expr=model.x['9', 'finished'] <= 150)` | 2865.645923398783 |
| WHAT-IF/new_constraint | Suppose the overhead capacity unit slated for period 6 gets pulled from the plan. Add that restriction and tell me the new welfare. | `model.wf_drop_f6 = Constraint(expr=model.f['6', 'overhead', 'normal'] == 0)` | 2890.2484072120906 |
| WHY-NOT/constraint_rule | We lean hard on imports for intermediate goods. That dependence makes me uneasy — shouldn't we just build intermediate capacity right away in period 1? What's the model weighing that keeps it from investing early? | `model.want_f1_intermed = Constraint(expr=model.f['1', 'intermed', 'normal'] == 1)` | 2847.406433931227 |
| WHY-NOT/constraint_rule | Why does the plan commit to a fresh intermediate capacity unit in period 2 at all? Couldn't we just skip that build and lean on what we've got? What's keeping the optimizer on it? | `model.want_skip_f2 = Constraint(expr=model.f['2', 'intermed', 'normal'] == 0)` | 2890.2484072120888 |

### yemcem_mip  (5)  — `testing_library/feas_test/yemcem_mip.txt`

| type/subtype | query (verbatim OptiChat Q) | constraint | expected_obj |
|---|---|---|---|
| WHAT-IF/new_constraint | Engineering is floating a medium wet-kiln at Amran in the 1986-88 window. We're evaluating it — lock that investment in and tell me the resulting total cost. | `model.force_wet_amran = Constraint(expr=model.y['wet-kiln', 'amran', 'medium', '1986-88'] == 1)` | 1672.0592477376563 |
| WHAT-IF/new_constraint | There's a proposal to stand up a small dry-kiln at Baijil right away, in 1986-88. Put that in the plan and let me see what it costs. | `model.force_baijil_86 = Constraint(expr=model.y['dry-kiln', 'baijil', 'small', '1986-88'] == 1)` | 1666.679319305726 |
| WHY-NOT/constraint_rule | Taizz is being fed partly by imported cement, yet we've got plants in-country. Shouldn't Taizz just be supplied from our own kilns instead of buying imports? What's the model seeing that makes importing worth it? | `model.no_import_taizz = Constraint(expr=model.v['cement', 'taizz', '1983-85'] == 0)` | 1624.86228930338 |
| WHY-NOT/constraint_rule | The plan waits until the very last window to put a large dry-kiln in Amran. Wouldn't it make more sense to build that big capacity earlier, in 1989-91, so it's working for us sooner? What's the trade-off pulling against that? | `model.early_amran = Constraint(expr=model.y['dry-kiln', 'amran', 'large', '1989-91'] == 1)` | 1625.590824030829 |
| WHY-NOT/constraint_rule | Hodeideh leans entirely on imported cement in the first period. That sits wrong with me — shouldn't we be serving a coastal market like that from domestic production? What's keeping the plan from doing that? | `model.no_import_hodeideh = Constraint(expr=model.v['cement', 'hodeideh', '1983-85'] == 0)` | 1641.812691208321 |

---


## 2. Quarantined — built but FAILED Z3 grading (need full-instance grading)

> **RESOLVED 2026-06-10:** all of these were rescued by grading on the FULL instance with a 90s/record timeout (these simple added constraints grade fast even on full data, contrary to expectation). 0 complex records remain quarantined; they now live in `datasets/<model>_optichat_query.jsonl`. Section kept for provenance.

These are complex what-if/why-not constraints whose query references a FULL-instance index that is absent from the model's REDUCED grading instance (so selfcheck KeyErrors), or an invalid-expression edge case. They are real and dataset-worthy; they need grading on full data (or a full-instance build) rather than the reduced one. Quarantined out of the shipped dataset for now.


### ccoil_mip  (1)  — `testing_library/feas_test/ccoil_mip.txt`

- Why fuss over sizing each segment individually? Just slap th  ->  `model.heur6 = Constraint(model.arc, rule=lambda m, i, j: m.bk[i, j, '6'] == m.b[i, j]) mod`  | reason: generated_exec_error:KeyError: "Index '('1', '2', '6')' is not valid for indexed component

### coex_mip  (3)  — `testing_library/feas_test/coex_mip.txt`

- We'd like to see the armies cross territory rather than sit  ->  `model.b_bottomrow = Constraint(expr=sum(model.b[8, j] for j in model.i) >= 1) model.w_topr`  | reason: generated_exec_error:KeyError: "Index '(8, 1)' is not valid for indexed component 'b'"
- The black army is sprawling all over the upper board. Couldn  ->  `model.b_quadrant = Constraint(expr=sum(model.b[i, j] for i in model.i for j in model.i if`  | reason: generated_exec_error:ValueError: Invalid constraint expression. The constraint expression
- I keep looking at the black queens fanned out across the boa  ->  `model.b_3x3 = Constraint(expr=sum(model.b[i, j] for i in model.i for j in model.i if not (`  | reason: generated_exec_error:ValueError: Invalid constraint expression. The constraint expression

### copper_mip  (2)  — `testing_library/feas_test/copper_mip.txt`

- China's wire market is strategically important and we want a  ->  `model.floor_wire_china = Constraint(expr=sum(model.xfs['wire', jp, 'china'] for jp in mode`  | reason: generated_exec_error:KeyError: "Index '('wire', 'canada', 'china')' is not valid for index
- China is the fastest-growing market on the board, but the pl  ->  `model.refined_china = Constraint(expr=sum(model.xfr[i, 'china'] for i in model.i) >= 300)`  | reason: generated_exec_error:KeyError: "Index '('western-us', 'china')' is not valid for indexed c

### cvrp_mip  (5)  — `testing_library/feas_test/cvrp_mip.txt`

- We're toying with a direct express run: have one of the truc  ->  `model.force_n1n16 = Constraint(expr=sum(model.X['n1', 'n16', k] for k in model.vehicle) >=`  | reason: generated_exec_error:KeyError: "Index '('n1', 'n16', 'k1')' is not valid for indexed compo
- Suppose a vehicle has to set off from the depot directly to  ->  `model.force_n1n9 = Constraint(expr=sum(model.X['n1', 'n9', k] for k in model.vehicle) >= 1`  | reason: generated_exec_error:KeyError: "Index '('n1', 'n9', 'k1')' is not valid for indexed compon
- We're curious what happens if a truck is sent out of the dep  ->  `model.force_n1n12 = Constraint(expr=sum(model.X['n1', 'n12', k] for k in model.vehicle) >=`  | reason: generated_exec_error:KeyError: "Index '('n1', 'n12', 'k1')' is not valid for indexed compo
- The plan sends a whole truck out to n13 and straight back, w  ->  `model.ban_n1n13 = Constraint(expr=sum(model.X['n1', 'n13', k] for k in model.vehicle) == 0`  | reason: generated_exec_error:KeyError: "Index '('n1', 'n13', 'k1')' is not valid for indexed compo
- Node n5 is fairly far out, so wouldn't it make sense to give  ->  `model.force_n1n5 = Constraint(expr=sum(model.X['n1', 'n5', k] for k in model.vehicle) >= 1`  | reason: generated_exec_error:KeyError: "Index '('n1', 'n5', 'k1')' is not valid for indexed compon

### fertd_mip  (1)  — `testing_library/feas_test/fertd_mip.txt`

- We're looking at a foreign-exchange squeeze in the back end  ->  `model.cap_import = Constraint(expr=sum(model.vf[c, j, '1985-87'] for (c, j, t) in model.vf`  | reason: generated_exec_error:ValueError: Invalid constraint expression. The constraint expression

### marilyn_mip  (2)  — `testing_library/feas_test/marilyn_mip.txt`

- We want to test an ordering preference between two specific  ->  `model.c1_le_c5 = Constraint(expr=model.x['c1'] <= model.x['c5'])`  | reason: generated_exec_error:KeyError: "Index 'c5' is not valid for indexed component 'x'"
- The two corner circles c3 and c8 end up about as far apart i  ->  `model.c8_ge_c3 = Constraint(expr=model.x['c8'] >= model.x['c3'])`  | reason: generated_exec_error:KeyError: "Index 'c8' is not valid for indexed component 'x'"

### maxcut_mip  (6)  — `testing_library/feas_test/maxcut_mip.txt`

- There's a hard requirement that nodes 45 and 46 sit in oppos  ->  `model.split4546 = Constraint(expr=model.x['45'] + model.x['46'] == 1)`  | reason: generated_exec_error:KeyError: "Index '45' is not valid for indexed component 'x'"
- Nodes 187 and 188 are mirrored backups of each other and pol  ->  `model.same187 = Constraint(expr=model.x['187'] == model.x['188'])`  | reason: generated_exec_error:KeyError: "Index '187' is not valid for indexed component 'x'"
- The edge between nodes 102 and 122 is the single heaviest li  ->  `model.same102 = Constraint(expr=model.x['102'] == model.x['122'])`  | reason: generated_exec_error:KeyError: "Index '102' is not valid for indexed component 'x'"
- Nodes 32 and 52 sit at the ends of one of the strongest link  ->  `model.same32 = Constraint(expr=model.x['32'] == model.x['52'])`  | reason: generated_exec_error:KeyError: "Index '32' is not valid for indexed component 'x'"
- The link between nodes 177 and 197 carries the most negative  ->  `model.split177 = Constraint(expr=model.x['177'] + model.x['197'] == 1)`  | reason: generated_exec_error:KeyError: "Index '177' is not valid for indexed component 'x'"
- Nodes 376 and 377 are joined by a very heavy edge, and the p  ->  `model.same376 = Constraint(expr=model.x['376'] == model.x['377'])`  | reason: generated_exec_error:KeyError: "Index '376' is not valid for indexed component 'x'"

### openpit_mip  (1)  — `testing_library/feas_test/openpit_mip.txt`

- We're looking at a haul-fleet limit on pit p4 — its trucks c  ->  `model.cap_p4 = Constraint(expr=sum(model.pout['p4', t] for t in model.t) <= 20)`  | reason: generated_exec_error:KeyError: "Index '('p4', 't1')' is not valid for indexed component 'p

### pp_mip  (2)  — `testing_library/feas_test/pp_mip.txt`

- Products E, F and H carry the heaviest demand, yet the plan  ->  `model.efh_front = Constraint(expr=model.e['E', 1] + model.e['F', 2] + model.e['H', 3] == 3`  | reason: generated_exec_error:KeyError: "Index '('E', 1)' is not valid for indexed component 'e'"
- The warehouse is choking on product E stock - it sits well a  ->  `def _rule(model, w):     return model.v['E', w] <= 200 model.cap_e_inv = Constraint(model.`  | reason: generated_exec_error:KeyError: "Index '('E', 1)' is not valid for indexed component 'v'"

### rcpsp_mip  (1)  — `testing_library/feas_test/rcpsp_mip.txt`

- Activity j23 hands off directly into j24's crew, and the for  ->  `model.gap_j23_j22 = Constraint(expr=sum(int(t[1:]) * model.x['j23', t] for t in model.t if`  | reason: generated_exec_error:ValueError: Invalid constraint expression. The constraint expression

### relief_mip  (2)  — `testing_library/feas_test/relief_mip.txt`

- The D8 drop is doing a lot of the heavy lifting and we worry  ->  `model.cap_d8 = Constraint(expr=sum(model.walk[hr, hc, 'D', 8] for (hr, hc) in model.hut) <`  | reason: generated_exec_error:KeyError: "Index '('A', 1, 'D', 8)' is not valid for indexed componen
- Field teams want coverage pushed toward the southern edge of  ->  `model.south_drop = Constraint(expr=sum(model.drop[r, c] for r in ['I', 'J'] for c in model`  | reason: generated_exec_error:KeyError: "Index '('I', 1)' is not valid for indexed component 'drop'

### rotdk_mip  (2)  — `testing_library/feas_test/rotdk_mip.txt`

- Suppose we cap lifetime reliance on C008 — no more than 10 u  ->  `model.cap_c008 = Constraint(expr=sum(model.x['C008', t] for t in model.t) <= 10)`  | reason: generated_exec_error:KeyError: "Index '('C008', 't1')' is not valid for indexed component
- We end up leaning on C008 about twenty times total. Wouldn't  ->  `model.why_c008_heavy = Constraint(expr=sum(model.x['C008', t] for t in model.t) >= 22)`  | reason: generated_exec_error:KeyError: "Index '('C008', 't1')' is not valid for indexed component

### swath_mip  (5)  — `testing_library/feas_test/swath_mip.txt`

- We're curious how tied the plan is to bouncing straight back  ->  `model.no2cyc_s2s4 = Constraint(expr=model.y['s2', 's4'] + model.y['s4', 's2'] <= 1)`  | reason: generated_exec_error:KeyError: "Index '('s2', 's4')' is not valid for indexed component 'y
- Let's look at the s5 / s7 pair the same way — what does the  ->  `model.no2cyc_s5s7 = Constraint(expr=model.y['s5', 's7'] + model.y['s7', 's5'] <= 1)`  | reason: generated_exec_error:KeyError: "Index '('s5', 's7')' is not valid for indexed component 'y
- I'm looking at this plan and the aircraft just ping-pongs be  ->  `model.no_loop_s6s8 = Constraint(expr=model.y['s6', 's8'] + model.y['s8', 's6'] <= 1)`  | reason: generated_exec_error:KeyError: "Index '('s6', 's8')' is not valid for indexed component 'y
- Same complaint over at s9 and s11 — the route closes a tiny  ->  `model.no_loop_s9s11 = Constraint(expr=model.y['s9', 's11'] + model.y['s11', 's9'] <= 1)`  | reason: generated_exec_error:KeyError: "Index '('s9', 's11')' is not valid for indexed component '
- The s18 / s20 pairing is yet another of these closed two-swa  ->  `model.no_loop_s18s20 = Constraint(expr=model.y['s18', 's20'] + model.y['s20', 's18'] <= 1)`  | reason: generated_exec_error:KeyError: "Index '('s18', 's20')' is not valid for indexed component

---


## 3. Tangled heuristics — need manual extraction (loops / computed fixes / multi-statement)

### bidpwl_mip (1) — `testing_library/feas_test/bidpwl_mip.txt` [added 2026-06-10]
- **WHY_NOT/heuristic** — Q: cheapest-slope single-tier vendor ladder. SKIPPED: computes the fixed segb pattern algorithmically from price data (greedy: sort vendors by cheapest slope, activate tiers until demand covered), so no fixed numbers to write as constraints. Materialize the computed pattern or hand-write if we want it later.


### RTN_mip  (1)  — `testing_library/feas_test/RTN_mip.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just run every reaction at the full 60-unit batch and keep operations uniform? What would that simple full-batch rule give us? | obj: 3.0
  - raw: `model = load_model('RTN_mip', models_dictionary) # Heuristic: run each reaction at its full 60-unit batch (at its scheduled firing) model.E['Rx1', 5].`

### STN_mip  (1)  — `testing_library/feas_test/STN_mip.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just keep it simple and run all the reactions on a single reactor — leave Reactor_2 idle the whole time? What net value would that give us? | obj: 491.8333333333333
  - raw: `model = load_model('STN_mip', models_dictionary) # Heuristic: leave Reactor_2 idle - run everything on Reactor_1 for k in model.W:     if k[1] == 'Rea`

### absmip_mip  (1)  — `testing_library/feas_test/absmip_mip.txt`

- **WHY-NOT/heuristic** — Q: A simple desk rule: just book half of the available downside — set the negative part to half the magnitude of the floor and call it done. How far off the model's answer is that? | obj: -2.5
  - raw: `model = load_model('absmip_mip', models_dictionary) # Heuristic 'half-the-floor': recognize a negative part equal to half the magnitude of # the lower`

### agreste_lp293  (1)  — `testing_library/feas_test/agreste_lp293.txt`

- **WHY-NOT/heuristic** — Q: Good land is the best ground we've got, so shouldn't we just work it the hardest first — commit the whole good-land block up front to our top cash crop, sugar-cane, fill all 8.775 hectares with it, and let the solver sort out the medium land, the labor and the herd around that? Wouldn't planting the prime ground to our most valuable crop already hold a competitive farm income? | obj: 14913.741
  - raw: `model = load_model('agreste_lp293', models_dictionary) # Heuristic land-priority rule: commit the prime (good) land class first, to a single # high-va`

### agreste_lp297  (1)  — `testing_library/feas_test/agreste_lp297.txt`

- **WHY-NOT/heuristic** — Q: We always say work the best ground hardest first — good land is our scarcest, most valuable class. Crop-10 is already the activity the plan trusts most on that ground, so shouldn't we just commit the entire good-land block to crop-10 up front, lock everything else off the good land, and let the solver fill in medium and pasture around that? Dedicating our prime acreage to the one crop that earns it ought to beat the optimizer's scattered good-land mix. | obj: 15693.57
  - raw: `model = load_model('agreste_lp297', models_dictionary) # Land-priority heuristic: commit the prime (good) land class to a single dedicated # crop (cro`

### aircraft_lp  (1)  — `testing_library/feas_test/aircraft_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just spread our ten type-a jets evenly — two on every route — instead of dumping them all on one? What would that simple split cost us? | obj: 5647.200000000001
  - raw: `model = load_model('aircraft_lp', models_dictionary) # Heuristic: spread the type-a fleet evenly, 2 aircraft on each route for j in model.j:     model`

### airsp2_lp134  (2)  — `testing_library/feas_test/airsp2_lp134.txt`

- **WHAT-IF/new_constraint** — Q: Operations is pushing back on the current fleet mix — they want the deployed small-capacity types (a and d) across the network to be at least as many airframes as the deployed large-capacity types (b and c) combined, otherwise we're too exposed if a wide-body goes down for maintenance. Run the numbers under that constraint and tell me what total cost looks like. | obj: 2291.360343
  - raw: `model = load_model('airsp2_lp134', models_dictionary) model.fleet_mix = Constraint(     expr=sum(model.x['a', j] for j in model.j) + sum(model.x['d',`
- **WHY-NOT/heuristic** — Q: These mixed-type route assignments make crewing and ground handling a headache. Wouldn't a clean tiered plan run smoother — put the small-capacity types a and d only on the short runs route-1 and route-2, and keep the wide-bodies b and c on the trunk routes 3, 4 and 5 — and just let the solver settle the exact counts inside that layout? Shouldn't that tidier structure still hold a competitive cost? | obj: 2064.335733
  - raw: `model = load_model('airsp2_lp134', models_dictionary) # Heuristic: a fixed fleet-tiering plan set in advance, then solve the residual. # small-capacit`

### airsp2_lp87  (2)  — `testing_library/feas_test/airsp2_lp87.txt`

- **WHAT-IF/new_constraint** — Q: Our chief ops officer is worried we lean too hard on the large-capacity fleet — she wants the small-capacity types (a and d) combined deployment across the network to be at least as many airframes as the large-capacity types (b and c) combined. What does that restriction do to total operating cost? | obj: 1452.455
  - raw: `model = load_model('airsp2_lp87', models_dictionary) model.fleet_mix = Constraint(     expr=sum(model.x['a', j] for j in model.j) + sum(model.x['d', j`
- **WHY-NOT/heuristic** — Q: All this spreading every aircraft type thin across five routes feels like it just multiplies the operating headaches. Wouldn't a clean home-route plan run smoother — make type-a the home fleet for route-1, type-b for routes 3 and 4, and type-c for routes 2 and 5 — assign each route one home aircraft type up front, keep every other type off it, and let the solver settle the exact counts and soak up whatever's left as bumping? Shouldn't that tidy dedicated layout still hold a competitive cost? | obj: 2456.714
  - raw: `model = load_model('airsp2_lp87', models_dictionary) # Heuristic: a fixed route-dedication plan set in advance, then solve the residual. # Each route`

### airsp_lp121  (4)  — `testing_library/feas_test/airsp_lp121.txt`

- **WHAT-IF/new_constraint** — Q: Our compliance officer just flagged that we lean heavily on type-b and type-c — regulators want to see the small-fleet types pulling their weight. The new rule: total deployed type-a-and-d aircraft across the network has to be at least as large as total deployed type-b-and-c. What does this do to expected cost? | obj: 1989.2045454545455
  - raw: `model = load_model('airsp_lp121', models_dictionary) model.fleet_balance = Constraint(     expr=sum(model.x['a', j] for j in model.j if ('a', j) in mo`
- **WHAT-IF/new_constraint** — Q: There's a proposal to guarantee a minimum presence on the long-haul run for crew-rostering reasons — keep at least 28 aircraft (any type) deployed on route-5. If we put that floor in, where does expected cost land? | obj: 1891.9064171122996
  - raw: `model = load_model('airsp_lp121', models_dictionary) model.route5_min = Constraint(     expr=sum(model.x[i, 'route-5'] for i in model.i if (i, 'route-`
- **WHY-NOT/constraint_rule** — Q: The plan concentrates 20.69 type-c aircraft on route-5 while route-2 gets just 4.31 — a heavy lean for a single aircraft type. Is there a reason the plan doesn't require that no single aircraft-type / route pairing carries more than 50% of that aircraft type's total availability? Wouldn't more cross-route deployment of each type improve resilience? | obj: 2337.609354413702
  - raw: `model = load_model('airsp_lp121', models_dictionary) def half_cap_rule(model, i, j):     if (i, j) not in model.ij:         return Constraint.Skip`
- **WHY-NOT/heuristic** — Q: Wouldn't a route-5-only strategy beat the current diversified plan? Route-5 has the lowest c[i,j]/p[i,j] ratio across all aircraft types here, so it's clearly the cheapest-per-passenger run. Pin x[i, route-5] = aa[i] for every type i and let the solver fill in bumping. Shouldn't this concentrated plan outperform the current diversified allocation? | obj: 7303.5
  - raw: `model = load_model('airsp_lp121', models_dictionary) # Heuristic: a cheapest-per-seat route-dedication plan set in advance, then solve the residual. #`

### airsp_lp165  (5)  — `testing_library/feas_test/airsp_lp165.txt`

- **WHAT-IF/new_constraint** — Q: Our compliance officer keeps pushing back on type-c concentration — they want type-c usage capped so it doesn't exceed 1.5× total type-d usage on the network. How does that hit expected cost? | obj: 2260.635
  - raw: `model = load_model('airsp_lp165', models_dictionary) model.type_c_cap = Constraint(     expr=sum(model.x['c', j] for j in model.j if ('c', j) in model`
- **WHY-NOT/constraint_rule** — Q: Type-c aircraft are concentrated 23.39 on route-2 and just 4.61 on route-5 — heavy lean on a single route for one aircraft type. Is there a reason the plan doesn't require that no aircraft type assigns more than 60% of its availability to any single route? Wouldn't more balanced cross-route deployment beat the current plan? | obj: 2770.662
  - raw: `model = load_model('airsp_lp165', models_dictionary) def cap60_rule(model, i, j):     if (i, j) not in model.ij:         return Constraint.Skip     re`
- **WHY-NOT/constraint_rule** — Q: The whole type-c fleet is piled onto route-2 in this plan. Couldn't we keep any one type from parking more than half its airframes on a single route — say, no type-c above 50% of its availability on any route? Shouldn't a more spread-out type-c deployment still come in at a workable cost? What's keeping the model from doing that? | obj: 2140.082
  - raw: `model = load_model('airsp_lp165', models_dictionary) def c_spread_rule(model, j):     if ('c', j) not in model.ij:         return Constraint.Skip`
- **WHY-NOT/constraint_rule** — Q: Route-5 takes a brutal hit on bumping — hundreds of passengers denied in its busy states while we run plenty of spare seats elsewhere. Shouldn't the plan have to serve at least 40% of route-5's booked demand in every state, capping bumping there at 60% of demand? What's stopping the model from protecting the long-haul like that? | obj: 2137.962
  - raw: `model = load_model('airsp_lp165', models_dictionary) def r5_service_rule(model, h):     if value(model.dd['route-5', h]) <= 0:         return Constrai`
- **WHY-NOT/heuristic** — Q: All these mixed-type route assignments make crewing and ground handling a nightmare. Wouldn't a clean dedication plan run smoother — assign each aircraft type to its single cheapest route by operating cost and pour the whole sub-fleet onto that one run, then let the solver settle the bumping? Shouldn't that tidy each-type-to-one-route layout still hold a competitive cost? | obj: 7936.752500000001
  - raw: `model = load_model('airsp_lp165', models_dictionary) # Heuristic: a fixed each-type-to-cheapest-route dedication plan set in advance, then solve the r`

### ajax_lp  (2)  — `testing_library/feas_test/ajax_lp.txt`

- **WHAT-IF/new_constraint** — Q: Plant management's been pushing back that machine-1 keeps running underutilized while machine-3 is hammered. They want machine-1's running hours locked at no less than 85% of machine-3's running hours from now on, however the shift schedule shakes out. How does that hit the profit? | obj: 438489.961
  - raw: `model = load_model('ajax_lp', models_dictionary) model.run_balance = Constraint(     expr=sum(model.outp[g, 'machine-1'] / model.prate[g, 'machine-1']`
- **WHY-NOT/heuristic** — Q: Grade changeovers on these machines eat hours we never recover. Wouldn't a clean one-grade-per-line plan run smoother — dedicate machine-1 to 20-bond-wt, machine-2 to 25-bond-wt, and let machine-3 carry both c-bond-ext and tissue-wrp — and just let the solver settle the exact tonnages from there? Shouldn't that specialized layout still hold a competitive profit? | obj: 414000.0
  - raw: `model = load_model('ajax_lp', models_dictionary) # Heuristic: a fixed line-dedication plan set in advance, then solve the residual. # machine-1 -> 20-`

### allbases_mip  (2)  — `testing_library/feas_test/allbases_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we really need the solver here? Our ops lead just loads the bigger cannery first — fill San Diego with its cheapest runs up to capacity, then let Seattle mop up the rest. How much does that simple rule actually cost us? | obj: 156.375
  - raw: `model = load_model('allbases_mip', models_dictionary) # Heuristic: load the bigger plant (San Diego) first on its cheapest lanes, Seattle takes overfl`
- **WHY-NOT/heuristic** — Q: One of the old dispatchers swears by cross-hauling to keep both plants busy — northern plant takes the southern orders and the southern plant takes the northern ones. Seattle runs Topeka, San Diego runs Chicago, and they split New York. What does that habit really cost compared to the plan? | obj: 166.275
  - raw: `model = load_model('allbases_mip', models_dictionary) # Heuristic: cross-haul -- north plant serves south market and vice versa assign = {     ('seatt`

### alphamet_mip  (1)  — `testing_library/feas_test/alphamet_mip.txt`

- **WHY-NOT/heuristic** — Q: Honestly, can't we skip the search and just hand the solver the digit assignment a human puzzler would write down — G=8, E=4, O=6, R=5, I=0, A=2, N=3, V=1, M=9, T=7 — and let it confirm the carries? If we nail down every letter to that guess, how does the carry total compare with what the optimizer found on its own? | obj: 9.0
  - raw: `model = load_model('alphamet_mip', models_dictionary) # Heuristic 'hand-solved guess': fix every letter to the digit a human solver would write, # the`

### alum_mip  (1)  — `testing_library/feas_test/alum_mip.txt`

- **WHY-NOT/heuristic** — Q: Our planners like a blunt capital rule: only ever invest in expanding the mines that sit on the biggest known bauxite reserves, and freeze expansion everywhere else. If we lock the model to expanding only the eleven largest-reserve deposits, how much worse is the total cost than the optimizer's own pick of where to invest? | obj: 49694.182262178445
  - raw: `model = load_model('alum_mip', models_dictionary) # Heuristic 'expand-the-richest-mines': permit a fixed-segment mine expansion ONLY at the K # deposi`

### ampl_lp  (5)  — `testing_library/feas_test/ampl_lp.txt`

- **WHAT-IF/new_constraint** — Q: Sales is locking down a long-running channel partner — the deal hinges on us guaranteeing at least 10 nuts produced across the four-period horizon. We're evaluating that commitment; plug the floor in and tell me what the optimizer returns for profit. | obj: 78.965848
  - raw: `model = load_model('ampl_lp', models_dictionary) model.nuts_floor = Constraint(     expr=sum(model.x['nuts', t] for t in model.t) >= 10 ) description`
- **WHAT-IF/new_constraint** — Q: There's a proposal on the table to commit to a washers volume for a distributor — at least 20 washers across the whole horizon. We're costing it out; if we hold total washers to 20 or more, what does the optimizer return for profit? | obj: 70.0167493670886
  - raw: `model = load_model('ampl_lp', models_dictionary) model.washers_floor = Constraint(     expr=sum(model.x['washers', t] for t in model.t) >= 20 ) descri`
- **WHAT-IF/new_constraint** — Q: We're evaluating a warm-start rule that keeps the lines busy from day one: produce at least 30 units total in period 1 rather than letting the plan idle the opening period. With that period-1 floor in place, where does profit land? | obj: 77.81579244444444
  - raw: `model = load_model('ampl_lp', models_dictionary) model.period1_floor = Constraint(     expr=sum(model.x[p, 1] for p in model.p) >= 30 ) description =`
- **WHY-NOT/constraint_rule** — Q: Production swings sharply between periods — period 2 is busy, periods 1 and 3 are nearly empty. Couldn't we require that the total production in any period stays within 30 units of the previous period's total? Shouldn't a smoother schedule still be at least competitive on profit? | obj: 79.00327692307692
  - raw: `model = load_model('ampl_lp', models_dictionary) def smooth_up_rule(model, t):     if t == 1: return Constraint.Skip     return sum(model.x[p, t] for`
- **WHY-NOT/heuristic** — Q: Switching products mid-period costs us changeover time we never get back. Wouldn't a clean one-product-per-period campaign run smoother — dedicate period 1 to nuts, period 2 to bolts, period 3 to washers, and period 4 back to nuts — and just let the solver settle the exact tonnages from there? Shouldn't that disciplined campaign still hold a competitive profit? | obj: 79.30080177777776
  - raw: `model = load_model('ampl_lp', models_dictionary) # Heuristic: a fixed one-product-per-period campaign set in advance, then solve the residual tonnages`

### ampl_lp2  (2)  — `testing_library/feas_test/ampl_lp2.txt`

- **WHY-NOT/constraint_rule** — Q: Production swings sharply between periods — period 4 is hammering nuts while periods 1, 2, and 3 sit idle. Couldn't we require that the total production in any active period stays within 30 units of the previous period's total? Shouldn't a smoother schedule still be at least competitive on profit? | obj: 96.73620253164557
  - raw: `model = load_model('ampl_lp2', models_dictionary) def smooth_up_rule(model, t):     if t == 1: return Constraint.Skip     return sum(model.x[p, t] for`
- **WHY-NOT/heuristic** — Q: Honestly the current schedule looks chaotic to the planners. Why not run a clean one-product-per-period rotation — nuts in period 1, bolts in period 2, washers in period 3, nuts again in period 4, a steady 8-unit batch each time, well inside what the raw stock can carry? Shouldn't that tidy rotation still hold its own on profit? | obj: 53.96387999999999
  - raw: `model = load_model('ampl_lp2', models_dictionary) # Heuristic planning strategy: dedicate each active period to a single product on a # fixed rotation`

### andean_fixed  (2)  — `testing_library/feas_test/andean_fixed.txt`

- **WHY-NOT/heuristic** — Q: Some on the council argue for a fully inward-looking plan — produce only for the regional market and export nothing at all. How badly does that no-export stance hurt the bottom line? | obj: 2548.2474194039673
  - raw: `model = load_model('andean_fixed', models_dictionary) # Heuristic: autarky -- no exports of anything for idx in model.e:     model.e[idx].fix(0) descr`
- **WHY-NOT/heuristic** — Q: What if we treated urea as strictly a domestic product and exported none of it region-wide, leaning on the other fertilizers for export earnings? Where does the plan's cost land under that rule? | obj: -2246.8749098713315
  - raw: `model = load_model('andean_fixed', models_dictionary) # Heuristic: no urea exports anywhere for (c, i, t) in model.e:     if c == 'urea':         mode`

### asyncincbi_mip  (1)  — `testing_library/feas_test/asyncincbi_mip.txt`

- **WHY-NOT/heuristic** — Q: What if we don't bother optimizing the switches at all and just leave every binary off — let the continuous parts do all the work? How far off the optimum is that lazy configuration? | obj: 731.0
  - raw: `model = load_model('asyncincbi_mip', models_dictionary) # Heuristic 'all-off': switch every binary off and let the free continuous xlo/xhi # absorb th`

### asyncloop_lp  (3)  — `testing_library/feas_test/asyncloop_lp.txt`

- **WHAT-IF/new_constraint** — Q: Cost-cutting just dropped from corporate — they want our combined monthly shipments capped at 800 cases going forward, down from the 900 we ship today. Plug that in and tell me where the cost lands. | obj: 100131.175
  - raw: `model = load_model('asyncloop_lp', models_dictionary) model.total_shipment_cap = Constraint(     expr=sum(model.x[i, j] for i in model.i for j in mode`
- **WHY-NOT/constraint_rule** — Q: Seattle's running flat out at 100% utilization while San Diego's only at 92%. Couldn't we require both plants run within 5 percentage points of each other on capacity utilization? Wouldn't load-balancing keep us competitive on cost? | obj: 153.675
  - raw: `model = load_model('asyncloop_lp', models_dictionary) # Utilization = total shipments from plant / plant capacity (a is fixed at base values). _util =`
- **WHY-NOT/heuristic** — Q: Our ops lead keeps pushing a load-balanced shipping plan — spread each market's order across the plants in proportion to nameplate capacity, so Seattle takes its 350/950 share of every market and San Diego takes its 600/950 share. Wouldn't that even split come out ahead of the current lopsided one on freight cost? What's the model seeing that pushes it the other way? | obj: 159.028
  - raw: `model = load_model('asyncloop_lp', models_dictionary) # Heuristic: a capacity-proportional split set in advance, then solve the residual. # Every mark`

### awktsp_mip_assign  (4)  — `testing_library/feas_test/awktsp_mip_assign.txt`

- **WHY-NOT/constraint_rule** — Q: This isn't a real tour — it's just a pile of little loops, cities bouncing back and forth between paired partners. Shouldn't we ban those reciprocal back-and-forth pairs outright? What's the model seeing that makes it lean on them? | obj: 78.0
  - raw: `model = load_model('awktsp_mip_assign', models_dictionary) model.no_2cyc = ConstraintList() cities = list(model.i) for a in cities:     for b in citie`
- **WHY-NOT/constraint_rule** — Q: Cities 2, 3 and 4 just curl into their own sealed three-city loop, cut off from everything else. Wouldn't it be better to break that closed triangle so they connect into the wider plan? What's the trade-off keeping them sealed together? | obj: 32.0
  - raw: `model = load_model('awktsp_mip_assign', models_dictionary) S = ['i2', 'i3', 'i4'] model.break_tri = Constraint(expr=sum(model.x[a, b] for a in S for b`
- **WHY-NOT/heuristic** — Q: Why run an optimizer at all — couldn't we just send everything round in one big loop, city 1 to 2 to 3 and on through 7 and back to 1? Wouldn't that simple round-trip be good enough? | obj: 162.0
  - raw: `model = load_model('awktsp_mip_assign', models_dictionary) # Heuristic: one big numbered-order loop route = ['i1', 'i2', 'i3', 'i4', 'i5', 'i6', 'i7']`
- **WHY-NOT/heuristic** — Q: Couldn't we just eyeball a sensible loop — run 1 over to its cheap partner 5, then through the 2-3-4 group, and finish via 6 and 7 before heading home? Wouldn't that hand-drawn route be good enough? | obj: 116.0
  - raw: `model = load_model('awktsp_mip_assign', models_dictionary) # Heuristic: hand-drawn loop 1-5-2-3-4-6-7 route = ['i1', 'i5', 'i2', 'i3', 'i4', 'i6', 'i7`

### awktsp_mip_cut  (4)  — `testing_library/feas_test/awktsp_mip_cut.txt`

- **WHY-NOT/constraint_rule** — Q: This isn't a real tour — it's just a pile of little loops, cities bouncing back and forth between paired partners. Shouldn't we ban those reciprocal back-and-forth pairs outright? What's the model seeing that makes it lean on them? | obj: 78.0
  - raw: `model = load_model('awktsp_mip_cut', models_dictionary) model.no_2cyc = ConstraintList() cities = list(model.i) for a in cities:     for b in cities:`
- **WHY-NOT/constraint_rule** — Q: Cities 2, 3 and 4 just curl into their own sealed three-city loop, cut off from everything else. Wouldn't it be better to break that closed triangle so they connect into the wider plan? What's the trade-off keeping them sealed together? | obj: 32.0
  - raw: `model = load_model('awktsp_mip_cut', models_dictionary) S = ['i2', 'i3', 'i4'] model.break_tri = Constraint(expr=sum(model.x[a, b] for a in S for b in`
- **WHY-NOT/heuristic** — Q: Why run an optimizer at all — couldn't we just send everything round in one big loop, city 1 to 2 to 3 and on through 7 and back to 1? Wouldn't that simple round-trip be good enough? | obj: 162.0
  - raw: `model = load_model('awktsp_mip_cut', models_dictionary) # Heuristic: one big numbered-order loop route = ['i1', 'i2', 'i3', 'i4', 'i5', 'i6', 'i7'] fo`
- **WHY-NOT/heuristic** — Q: Couldn't we just eyeball a sensible loop — run 1 over to its cheap partner 5, then through the 2-3-4 group, and finish via 6 and 7 before heading home? Wouldn't that hand-drawn route be good enough? | obj: 116.0
  - raw: `model = load_model('awktsp_mip_cut', models_dictionary) # Heuristic: hand-drawn loop 1-5-2-3-4-6-7 route = ['i1', 'i5', 'i2', 'i3', 'i4', 'i6', 'i7']`

### bchfcnet_mip  (1)  — `testing_library/feas_test/bchfcnet_mip.txt`

- **WHY-NOT/heuristic** — Q: Our planners like a no-fuss rule: give every delivery point its own dedicated line straight from the depot — open one direct n1-to-sink arc per customer and ship each its order on that. If we lock the network into that hub-and-spoke pattern, how much more does the build cost than the optimizer's relayed tree? | obj: 1952.0
  - raw: `model = load_model('bchfcnet_mip', models_dictionary) # Heuristic 'direct hub-and-spoke': give every demand node its own dedicated arc # straight from`

### bchmknap_mip  (1)  — `testing_library/feas_test/bchmknap_mip.txt`

- **WHY-NOT/heuristic** — Q: Our investment committee likes a dead-simple rule: grab the most valuable column first, then keep adding the next-most-valuable one as long as it still fits every resource budget. If we lock the program to that greedy most-valuable-first pick, how much value do we leave on the table versus the optimizer's plan? | obj: 2400.0
  - raw: `model = load_model('bchmknap_mip', models_dictionary) # Heuristic 'most-valuable-first': sort columns by raw value descending and take each one # if i`

### bchstock_mip  (1)  — `testing_library/feas_test/bchstock_mip.txt`

- **WHY-NOT/heuristic** — Q: The schedulers would much rather keep it simple: one dedicated pattern per product, each roll cut into just a single width, no fiddly mixed layouts. If we ran the line that way — only the single-width patterns p1 through p4 and none of the combination cuts — how many more rolls would it cost us versus the optimizer's mixed plan? | obj: 517.0
  - raw: `model = load_model('bchstock_mip', models_dictionary) # Heuristic 'one-pattern-per-width': cut each product on its own dedicated single-width # patter`

### bchtsp_mip  (1)  — `testing_library/feas_test/bchtsp_mip.txt`

- **WHY-NOT/heuristic** — Q: Our dispatchers don't trust the fancy routing — they'd rather just run the obvious greedy rule: start at the first city and always drive to the nearest stop you haven't hit yet, then loop back home. If we lock the route to that nearest-neighbor pattern, how much longer is the trip than the optimizer's plan? | obj: 116.0
  - raw: `model = load_model('bchtsp_mip', models_dictionary) # Heuristic 'nearest-neighbour': start at the first city; at each step drive to the # cheapest not`

### bid_mip  (1)  — `testing_library/feas_test/bid_mip.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just give every vendor their entry-level deal — take each supplier's first-segment bid — and be done with it? What would that simple even-handed split cost? | obj: 15258406.347520001
  - raw: `model = load_model('bid_mip', models_dictionary) # Heuristic: award every vendor its first-segment (entry-level) deal for v in model.v:     if (v, 1)`

### bidpwl_mip  (1)  — `testing_library/feas_test/bidpwl_mip.txt`

- **WHY-NOT/heuristic** — Q: Our category managers prefer a dead-simple sourcing rule: rank vendors by their cheapest marginal price and award each one its whole cheapest tier, cheapest vendor first, until the requirement is covered — anyone not needed gets nothing. If we lock the award to that single-tier ladder, how much worse is the procurement bill than the optimizer's blended plan? | obj: 15633690.5312
  - raw: `model = load_model('bidpwl_mip', models_dictionary) # Heuristic 'cheapest-slope single-tier ladder': for each vendor take its lowest-slope real # (pl>`

### bidsos_mip  (1)  — `testing_library/feas_test/bidsos_mip.txt`

- **WHY-NOT/heuristic** — Q: Our category managers prefer a dead-simple sourcing principle: for supply-security reasons no vendor should walk away empty-handed — every supplier carries at least some real bid rather than 'nodeal'. If we lock the plan to that no-walk-away rule, how much more does the total purchase bill come to than the optimizer's concentrated plan? | obj: 15429764.5112
  - raw: `model = load_model('bidsos_mip', models_dictionary) # Heuristic 'no walk-aways': for supply-security reasons procurement forbids the 'nodeal' # segmen`

### binpacking_mip  (2)  — `testing_library/feas_test/binpacking_mip.txt`

- **WHAT-IF/new_constraint** — Q: Engineering flagged that items i1 and i2 react badly and can't ride in the same bin. If we enforce that they're always kept apart, does the bin count go up? | obj: 20.0
  - raw: `model = load_model('binpacking_mip', models_dictionary) model.incompatible = ConstraintList() for j in model.J:     model.incompatible.add(model.y['i1`
- **WHY-NOT/heuristic** — Q: The optimizer's assignment looks like it's scattering items all over the place. These items practically come in natural groups — couldn't we just drop the first three into bin 1, the next three into bin 2, and so on for the opening stretch, then let the solver clean up whatever's left? Wouldn't that simple sequential fill get us there without costing any extra bins? | obj: 20.0
  - raw: `model = load_model('binpacking_mip', models_dictionary) items = list(model.I) bins = list(model.J) # Heuristic: seed the first ten bins by dropping co`

### blend_lp54  (1)  — `testing_library/feas_test/blend_lp54.txt`

- **WHY-NOT/heuristic** — Q: Vendor onboarding and QC are a headache for the premium alloys, so we'd rather just deal with our four lowest-priced suppliers — alloys a, b, c and d — and let the optimizer settle the exact split among those four. Shouldn't sticking to the value tier still hit the spec at a competitive cost? What's keeping that restricted-sourcing plan from being the cheapest? | obj: 4.98
  - raw: `model = load_model('blend_lp54', models_dictionary) # Heuristic: a value-tier sourcing plan set in advance, then solve the residual. # Restrict procur`

### blend_lp57  (1)  — `testing_library/feas_test/blend_lp57.txt`

- **WHY-NOT/heuristic** — Q: Our purchasing folks would rather not juggle nine different alloy suppliers. Their instinct is to dedicate the whole blend to the three lead-rich workhorses we already qualify in volume — a, b and d — and just let the proportions settle from there. Shouldn't a tidy three-supplier plan like that hold up on cost? | obj: 5.7986
  - raw: `model = load_model('blend_lp57', models_dictionary) # Heuristic strategy: dedicate the blend to the three lead-rich workhorse alloys a, b, d; # forbid`

### boxpacking_mip  (2)  — `testing_library/feas_test/boxpacking_mip.txt`

- **WHY-NOT/constraint_rule** — Q: The plan stows all fourteen of the smallest cartons, but our handlers find them fiddly. Couldn't we just leave at least five of those little ones behind and not lose much? Cap the small-carton count at nine and tell me what it actually costs us in volume. | obj: 11.561850000000003
  - raw: `model = load_model('boxpacking_mip', models_dictionary) small = ['b17','b18','b19','b20','b21','b22','b23','b24','b25','b26','b27','b28','b29','b30']`
- **WHY-NOT/heuristic** — Q: Our loaders prefer a no-brainer rule: only bother stowing the bigger cartons and leave every one of the smallest half-size boxes off this run. If we lock the load to that 'mid-and-large only' rule, how much packed volume do we give up versus the optimizer's pack-everything plan? | obj: 10.4976
  - raw: `model = load_model('boxpacking_mip', models_dictionary) # Heuristic 'mid-and-large only': stow every carton at or above the mid volume class # (>= 0.2`

### cbenders_mip  (1)  — `testing_library/feas_test/cbenders_mip.txt`

- **WHY-NOT/heuristic** — Q: Our planners want a dead-simple sourcing rule: hand each region to a single warehouse — the cheapest-haul one that still has room for that region's full order, taking the biggest regions first. If we lock the network to that one-region-one-warehouse pattern, how much more does the freight-plus-fixed bill come to than the optimizer's mixed plan? | obj: 12605.0
  - raw: `model = load_model('cbenders_mip', models_dictionary) # Heuristic 'capacity-aware sole-source': process regions by descending total demand; # assign e`

### chance_lp  (1)  — `testing_library/feas_test/chance_lp.txt`

- **WHY-NOT/heuristic** — Q: Our purchasing team would rather lean on the two cheapest grains and let the solver patch the rest. Couldn't we anchor the blend on a fixed base of 40% barley and 20% oats up front, then fill in whatever sesame and ground meal it takes to hit the spec? Shouldn't that cheap-staples-first plan stay close to the current cost — what's keeping the model from leaning that way on its own? | obj: 30.77
  - raw: `model = load_model('chance_lp', models_dictionary) # Heuristic: a cheap-staples-first base plan set in advance, then solve the residual. # Commit the`

### china_lp  (6)  — `testing_library/feas_test/china_lp.txt`

- **WHAT-IF/new_constraint** — Q: The county is rolling out a soil-rotation rule next cycle — no single cropping sequence should exceed 30% of the paddy land planted in any cycle. How does that anti-monoculture rule shift brigade income and the sequence mix? | obj: 39557.619
  - raw: `model = load_model('china_lp', models_dictionary) total_xcrop = sum(model.xcrop[s, f] for (s, f) in model.ss) seqs = sorted(set(s for (s, _) in model.`
- **WHAT-IF/new_constraint** — Q: There's a proposal to keep the high-fertilizer rotations from dominating the paddy — hold all the high-fertilizer sequences together to no more than 40% of the paddy planted each cycle. What does the optimizer return for brigade income and the plan under that ceiling? | obj: 39434.6502
  - raw: `model = load_model('china_lp', models_dictionary) total_xcrop = sum(model.xcrop[s, f] for (s, f) in model.ss) high_total = sum(model.xcrop[s, f] for (`
- **WHY-NOT/constraint_rule** — Q: Upland is a small sliver of the brigade's land — and the plan still keeps a tight ratio between fodder and vegetable. Couldn't we require that no upland crop ever exceed 60% of total upland area? What's the model seeing that I'm not? | obj: 40546.255
  - raw: `model = load_model('china_lp', models_dictionary) total_upland = sum(model.xupland[c] for c in model.cu) model.upland_cap = ConstraintList() for c in`
- **WHY-NOT/constraint_rule** — Q: The plan barely touches barley, yet barley is our hardiest grain and the cadres want it kept in the rotation. Shouldn't the barley sequences carry at least a quarter of the paddy we plant? What's keeping the model from leaning on barley like that? | obj: 38365.1172
  - raw: `model = load_model('china_lp', models_dictionary) total_xcrop = sum(model.xcrop[s, f] for (s, f) in model.ss) barley_total = sum(model.xcrop[s, f] for`
- **WHY-NOT/constraint_rule** — Q: Green-manure-rice-rice on high fertilizer is taking a huge slice of the paddy on its own. Couldn't we hold any single high-fertilizer sequence to no more than 20% of the paddy planted so the plan isn't betting the cycle on one rotation? What's the model seeing that makes it concentrate like that? | obj: 39240.1783
  - raw: `model = load_model('china_lp', models_dictionary) total_xcrop = sum(model.xcrop[s, f] for (s, f) in model.ss) model.high_seq_cap = ConstraintList() fo`
- **WHY-NOT/heuristic** — Q: Chopping and changing the fertilizer regime on each rotation makes the field-work plan a mess. Wouldn't it be cleaner to just dedicate each rotation to one fertility band up front — run the barley and wheat sequences on high fertilizer and keep the green-manure, rape and fallow sequences on normal — and let the solver settle the exact mu from there? What's the tradeoff the model's flagging that I'm not seeing? | obj: 38886.2547
  - raw: `model = load_model('china_lp', models_dictionary) # Heuristic: a fixed fertility-band dedication plan set in advance, then solve the residual mu. # ba`

### clad_mip  (1)  — `testing_library/feas_test/clad_mip.txt`

- **WHY-NOT/heuristic** — Q: Some analysts would just skip the fancy estimator and report a null model — set every regression coefficient to zero so the prediction is the same censored constant for everyone, and let the residuals fall where they may. If we lock the fit to that no-covariates rule, how much worse is the total absolute deviation than the full CLAD estimate? | obj: 407.4957083671306
  - raw: `model = load_model('clad_mip', models_dictionary) # Heuristic 'null model': ignore every regressor by fixing all beta coefficients to zero, # so each`

### cmo_mip  (2)  — `testing_library/feas_test/cmo_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we need to optimize the tranche selection at all? A desk could just take the first three normal tranches in order — n1, n2, n3 — and call it a day. How much does that lazy pick cost in proceeds? | obj: 96.74591209901305
  - raw: `model = load_model('cmo_mip', models_dictionary) # Heuristic: use the first three normal tranches n1, n2, n3 use = {'n1': 1, 'n2': 1, 'n3': 1, 'n4': 0`
- **WHY-NOT/heuristic** — Q: What if we just throw every normal tranche into the structure — all six, kitchen-sink style? Where does that leave the proceeds? | obj: 97.31483452770294
  - raw: `model = load_model('cmo_mip', models_dictionary) # Heuristic: include all six normal tranches for n in model.N:     model.tin[n].fix(1) description =`

### coex_mip  (2)  — `testing_library/feas_test/coex_mip.txt`

- **WHAT-IF/new_constraint** — Q: Suppose the black army has to spread out one-per-rank for visibility — no more than a single black queen in any given row. With that dispersion rule in place, what's the biggest each army can be? | obj: 6.0
  - raw: `model = load_model('coex_mip', models_dictionary) model.b_one_per_row = ConstraintList() for r in model.i:     model.b_one_per_row.add(sum(model.b[r,`
- **WHY-NOT/heuristic** — Q: Our planners like a dead-simple territorial rule: keep the two armies completely off each other's turf by banding them — black only in the top two rows, white only in the bottom two rows — and let the solver fill those bands. How many queens per side does that tidy banded layout actually buy us versus the optimizer's nine? | obj: 7.0
  - raw: `model = load_model('coex_mip', models_dictionary) # Heuristic 'banded segregation': confine the black army to the top band (rows 1-2) # and the white`

### copper_mip  (1)  — `testing_library/feas_test/copper_mip.txt`

- **WHY-NOT/heuristic** — Q: Our investment committee likes a blunt rule: just build out the richest deposits. Take the five locations with the largest total ore reserves and green-light a mine, smelter and refinery expansion at every one of them, then let the solver size and route the rest. How much more does that 'build at the richest deposits' plan cost than the optimizer's selective build? | obj: 71971.5551752503
  - raw: `model = load_model('copper_mip', models_dictionary) # Heuristic 'build at the richest deposits': rank locations by total (high+med) ore reserves, # fo`

### csp_mip  (5)  — `testing_library/feas_test/csp_mip.txt`

- **WHAT-IF/new_constraint** — Q: There's a proposal on the table to standardize the output so the template matches reference string s2 exactly at every position. If we lock it to s2's pattern, what worst-case distance does that leave us with? | obj: 6.0
  - raw: `model = load_model('csp_mip', models_dictionary) s2_pattern = {'c1': 'a13', 'c2': 'a5', 'c3': 'a4', 'c4': 'a9', 'c5': 'a1', 'c6': 'a14'} model.lock_s2`
- **WHY-NOT/constraint_rule** — Q: The optimizer builds a brand-new template character by character, but we already have four perfectly good strings on hand. Couldn't we just reuse one of them — say s1 — as the template instead of synthesizing a new one? What's the model seeing that makes the custom template worth it? | obj: 6.0
  - raw: `model = load_model('csp_mip', models_dictionary) s1_pattern = {'c1': 'a4', 'c2': 'a9', 'c3': 'a6', 'c4': 'a6', 'c5': 'a5', 'c6': 'a18'} model.reuse_s1`
- **WHY-NOT/heuristic** — Q: Instead of all that optimization, couldn't we just take the most common character at each position across the four strings and call that our template? Wouldn't that majority-vote string land about as close as the optimized one? | obj: 5.0
  - raw: `model = load_model('csp_mip', models_dictionary) # Heuristic: per-position majority vote across the four strings majority = {'c1': 'a13', 'c2': 'a5',`
- **WHY-NOT/constraint_rule** — Q: String s4 already overlaps heavily with the rest — it shares its first four characters with s2. Couldn't we just adopt s4 as the template and skip synthesizing a new one? What's the optimizer seeing that rules that out? | obj: 6.0
  - raw: `model = load_model('csp_mip', models_dictionary) s4_pattern = {'c1': 'a13', 'c2': 'a5', 'c3': 'a4', 'c4': 'a9', 'c5': 'a21', 'c6': 'a13'} model.reuse_`
- **WHY-NOT/heuristic** — Q: Rather than synthesizing a template from scratch, couldn't we just take the string that looks most central — say s2 — and adopt it wholesale? Wouldn't reusing one of our own samples be close enough to bother optimizing? | obj: 6.0
  - raw: `model = load_model('csp_mip', models_dictionary) # Heuristic: adopt existing string s2 verbatim as the template s2_pattern = {'c1': 'a13', 'c2': 'a5',`

### cta_mip  (9)  — `testing_library/feas_test/cta_mip.txt`

- **WHAT-IF/new_constraint** — Q: The statistical office is piloting a per-cell magnitude rule — no single published cell should move by more than 15% of its original value, to keep downstream data utility intact. Bake that in and report the optimal total adjustment cost. | obj: 2500.6
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.cell_mag_cap = ConstraintList() for (i, j, k) in model`
- **WHAT-IF/new_constraint** — Q: We're evaluating a cap on collateral damage: every non-sensitive cell's combined adjustment held to at most 70 units. What total adjustment cost does the optimizer return under that rule? | obj: 2456.0
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.nonsens_cap70 = ConstraintList() for (i, j, k) in mode`
- **WHAT-IF/new_constraint** — Q: There's a proposal on the table to spread the protection load — no single plane should carry more than 28% of the table's total adjustment volume. Plug that in and walk me through the resulting cost. | obj: 3007.142857142857
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.plane_cap28 = ConstraintList() total_adj = sum(model.a`
- **WHAT-IF/new_constraint** — Q: The methods team is testing a column-stability rule where each column's total adjustment stays within 22% of the table-wide total. What's the optimal adjustment cost with that constraint active? | obj: 2972.7272727272725
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.col_cap22 = ConstraintList() total_adj = sum(model.adj`
- **WHY-NOT/constraint_rule** — Q: The adjustment burden looks lopsided across planes. Shouldn't each plane carry no more than 30% of the total adjustment volume, so the protection load is spread evenly across the published cube? What's the model seeing that makes the current concentrated split look cheaper? | obj: 2806.6666666666665
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.plane_share_cap = ConstraintList() total_adj = sum(mod`
- **WHY-NOT/constraint_rule** — Q: Non-sensitive cells are absorbing perturbations they didn't need to. Shouldn't every non-sensitive cell's combined adjustment stay below 50 units, so the bulk of the protection lives where it actually belongs — on the sensitive cells? What's pulling the optimizer to spread it the way it does? | obj: 2582.0
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.nonsens_cap = ConstraintList() for (i, j, k) in model.`
- **WHY-NOT/constraint_rule** — Q: Some published cells are getting moved a lot relative to their size. Couldn't we hold every cell's combined adjustment to under 12% of its original value? What's keeping the model from staying inside that band? | obj: 2569.2799999999934
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.cell_mag_12 = ConstraintList() for (i, j, k) in model.`
- **WHY-NOT/constraint_rule** — Q: One or two columns seem to be soaking up most of the adjustment. Wouldn't it be more defensible to keep each column's share of the total adjustment under 25%? What's the tradeoff that pushes the optimizer to concentrate it the way it does? | obj: 2616.0
  - raw: `model = load_model('cta_mip', models_dictionary) from pyomo.environ import ConstraintList model.col_share_cap = ConstraintList() total_adj = sum(model`
- **WHY-NOT/heuristic** — Q: Auditors want a predictable disclosure pattern they can defend in review. Wouldn't a directional policy — push every protected cell in the front plane (p1) upward and every protected cell in the back plane (p3) downward, then let the solver settle the rest — give a defensible plan at a comparable total cost? | obj: 2829.0
  - raw: `model = load_model('cta_mip', models_dictionary) for (i, j, k) in model.s:     if k == 'p1':         model.b[i, j, k].fix(1)     elif k == 'p3':`

### cube_mip  (2)  — `testing_library/feas_test/cube_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of the solver's scattered placement, couldn't we just fill the entire bottom layer solid and stack the leftover balls in a tidy row above it? Wouldn't that obvious packing be about as balanced as the optimizer's layout? | obj: 18.0
  - raw: `model = load_model('cube_mip', models_dictionary) # Heuristic 'solid base': fill the whole bottom a-layer (9 cells), then stack the # remaining 4 ball`
- **WHY-NOT/heuristic** — Q: What if we go with a simple base-plus-spine pattern — fill the whole bottom layer, then run the four leftover balls straight up the central column? Isn't that cleaner arrangement roughly as good as the optimizer's spread-out plan? | obj: 16.0
  - raw: `model = load_model('cube_mip', models_dictionary) # Heuristic 'base plus spine': fill the whole bottom a-layer (9 cells), then put the # remaining 4 b`

### cubesoln_mip  (2)  — `testing_library/feas_test/cubesoln_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of the optimizer's scattered layout, couldn't we just use the obvious symmetric pattern — fill the center plus all eight corners and let it round out from there? Wouldn't that tidy arrangement be about as balanced? | obj: 13.0
  - raw: `model = load_model('cubesoln_mip', models_dictionary) # Heuristic: seed the symmetric center + eight corners pattern seed = [(2, 2, 2), (1, 1, 1), (1,`
- **WHY-NOT/heuristic** — Q: Couldn't we just pack a solid quarter-block — fill the whole 2-by-2 column running up one edge and cap it off with a single far cell? Wouldn't a compact chunk like that be simpler than the spread-out optimal layout? | obj: 16.0
  - raw: `model = load_model('cubesoln_mip', models_dictionary) # Heuristic: pack a solid 2x2x3 block (12 cells) plus one far corner cell for i in [1, 2]:     f`

### cutstock_mip  (1)  — `testing_library/feas_test/cutstock_mip.txt`

- **WHY-NOT/heuristic** — Q: Our floor crew would rather keep it simple: give each finished width its own dedicated pattern — the one that yields the most of that width — and just run that pattern enough times to cover its order, never mixing widths across patterns. If we lock the schedule to that one-pattern-per-product rule, how much worse is the roll count than the optimizer's mixed plan? | obj: 517.0
  - raw: `import math model = load_model('cutstock_mip', models_dictionary) # Heuristic 'one dedicated pattern per width': for each finished width pick the sing`

### cvrp_mip  (3)  — `testing_library/feas_test/cvrp_mip.txt`

- **WHAT-IF/new_constraint** — Q: Nodes n13 and n16 are both bulky drops, and the dispatcher wants to know what it costs to put them on the same truck. If we require whichever vehicle serves n13 to also be the one serving n16, what total distance does that scenario produce? | obj: 572.1396570868906
  - raw: `model = load_model('cvrp_mip', models_dictionary) model.same_truck_1316 = ConstraintList() for k in model.vehicle:     model.same_truck_1316.add(`
- **WHY-NOT/constraint_rule** — Q: It seems odd that n13 and n16 — two of our biggest single drops — end up on different trucks. Couldn't we just keep them together on one vehicle for simpler dispatching? What's the tradeoff the model is making by splitting them? | obj: 572.1396570868906
  - raw: `model = load_model('cvrp_mip', models_dictionary) model.pair_1316 = ConstraintList() for k in model.vehicle:     model.pair_1316.add(         sum(mode`
- **WHY-NOT/heuristic** — Q: Our planners like a no-frills loading rule: take the customers heaviest-order-first and drop each into the first truck that still has room, then let routing fill in the driving. If we lock the fleet to that first-fit-by-size assignment, how much worse is the total distance than the optimizer's plan? | obj: 728.1125854363039
  - raw: `model = load_model('cvrp_mip', models_dictionary) # Heuristic 'first-fit-decreasing': sort customers by demand (largest first) and assign # each to th`

### danwolfe_lp  (6)  — `testing_library/feas_test/danwolfe_lp.txt`

- **WHAT-IF/new_constraint** — Q: Risk management is pitching a single-point-of-failure rule: no individual (commodity, edge) flow should be allowed to exceed 50 units, period. Plug that rule in and tell me what the routing and total cost land at. | obj: 4195.935495
  - raw: `model = load_model('danwolfe_lp', models_dictionary) model.flow_cap_50 = ConstraintList() for k in model.k:     for (i, j) in model.e:         model.f`
- **WHAT-IF/new_constraint** — Q: We're evaluating a utilization-headroom policy: keep every edge's combined flow at or below 70% of its rated capacity so there's always slack for a surge. Plug it in and tell me where total cost lands. | obj: 3301.98906
  - raw: `model = load_model('danwolfe_lp', models_dictionary) model.edge_util_70 = ConstraintList() for (i, j) in model.e:     model.edge_util_70.add(sum(model`
- **WHY-NOT/constraint_rule** — Q: A handful of links are carrying enormous single-edge loads while most arcs sit nearly empty. Couldn't we just cap each edge's combined flow at 100 units so no single link becomes a chokepoint? Shouldn't a more spread-out routing still come in at a workable cost? | obj: 3243.184027
  - raw: `model = load_model('danwolfe_lp', models_dictionary) model.edge_total_cap_100 = ConstraintList() for (i, j) in model.e:     model.edge_total_cap_100.a`
- **WHY-NOT/constraint_rule** — Q: The plan is dumping the entire k2 demand onto the n14 to n8 link as a single shot. Couldn't we require that no single (commodity, edge) flow ever exceed 50 units to avoid that kind of concentration? What's keeping the model from making that move? | obj: 4195.935495
  - raw: `model = load_model('danwolfe_lp', models_dictionary) model.no_single_flow_concentration = ConstraintList() for k in model.k:     for (i, j) in model.e`
- **WHY-NOT/constraint_rule** — Q: Some corridors are running flat-out at the rated limit while others barely move. Couldn't we hold every edge to 70% of its capacity so we're never riding the redline? Shouldn't a routing with that much headroom still hold a sensible cost? | obj: 3301.98906
  - raw: `model = load_model('danwolfe_lp', models_dictionary) model.edge_util_70 = ConstraintList() for (i, j) in model.e:     model.edge_util_70.add(sum(model`
- **WHY-NOT/heuristic** — Q: All this criss-crossing through far-flung transit nodes looks like a handling nightmare on the ground. Couldn't we just commit up front to a single-transfer discipline — every commodity only allowed to touch links that connect directly to its own origin or its own destination, no wandering through unrelated hubs — and let the solver settle the tonnages from there? What's the model seeing that makes the sprawling routing worth it on cost? | obj: 3094.343121
  - raw: `model = load_model('danwolfe_lp', models_dictionary) # Heuristic: a single-transfer routing discipline set in advance, then solve the residual. # Each`

### dea_lp  (4)  — `testing_library/feas_test/dea_lp.txt`

- **WHAT-IF/new_constraint** — Q: The audit committee is pitching a tighter peer-selection rule for the assessment: no single benchmark depot should ever carry more than 30% of the total reference weight when we evaluate Depot 18. What does Depot 18's efficiency score come out to under that rule? | obj: 43.438199
  - raw: `model = load_model('dea_lp', models_dictionary) model.peer_cap_30 = ConstraintList() for i in model.I:     model.peer_cap_30.add(model.lam[i] <= 0.30`
- **WHY-NOT/constraint_rule** — Q: The output slacks come out lopsided — issues is carrying a healthy slack while receipts and reqs are clean. Wouldn't a fair efficiency reading insist that any single output's slack stays at or below twice the average slack across the three outputs? What's the tradeoff that's pulling the plan toward this uneven profile? | obj: 42.130352
  - raw: `model = load_model('dea_lp', models_dictionary) n_out = len(model.Jo) model.us_balance = ConstraintList() for j in model.Jo:     model.us_balance.add(`
- **WHY-NOT/constraint_rule** — Q: Looking at the benchmark blend, Depot 19 is doing most of the heavy lifting at over 30% of the reference weight. Couldn't we require that no single peer ever carries more than 40% of the total weight? Walk me through what's pulling the optimizer toward such a concentrated blend. | obj: 42.301304
  - raw: `model = load_model('dea_lp', models_dictionary) model.peer_cap_40 = ConstraintList() for i in model.I:     model.peer_cap_40.add(model.lam[i] <= 0.40`
- **WHY-NOT/heuristic** — Q: Operations only trusts a curated panel of comparable mid-size sites as legitimate benchmarks for Depot 18 — Depot 2, Depot 5, Depot 8, Depot 12, and Depot 15 — and doesn't want the assessment leaning on anything outside that panel. Let's dedicate the comparison to just those five: hold every depot outside the panel at zero weight up front, then let the model build the best blend it can from the panel alone. Where does Depot 18's efficiency land under that fixed reference panel, and what was the unrestricted model seeing in the off-panel sites that this gives up? | obj: 47.01125
  - raw: `model = load_model('dea_lp', models_dictionary) panel = ['Depot2', 'Depot5', 'Depot8', 'Depot12', 'Depot15'] for i in model.I:     if i not in panel:`

### decomp_lp97  (5)  — `testing_library/feas_test/decomp_lp97.txt`

- **WHAT-IF/new_constraint** — Q: Sales just signed a long-term contract promising every terminal that plant-1 will source at least 40% of their intake going forward — no one wants any single terminal feeling locked into plant-2. What does that obligation do to our shipping cost? | obj: 66.6
  - raw: `model = load_model('decomp_lp97', models_dictionary) model.plant1_min40 = ConstraintList() for j in model.j:     model.plant1_min40.add(model.x['plant`
- **WHY-NOT/constraint_rule** — Q: Right now plant-2 is doing all the heavy lifting on terminal 2 while plant-1 sends nothing there. Couldn't we require both plants to carry at least 25% of every terminal's demand? Wouldn't that more balanced sourcing leave us with a reasonable shipping bill? | obj: 65.5
  - raw: `model = load_model('decomp_lp97', models_dictionary) model.both_min25 = ConstraintList() for i in model.i:     for j in model.j:         model.both_mi`
- **WHY-NOT/constraint_rule** — Q: Operations is uncomfortable with how concentrated the volume is on a single lane — plant-2 to terminal 2 alone is carrying nearly half the network's flow. Couldn't we require that no individual plant-terminal route carry more than 40% of the network's total throughput? What's the tradeoff that's pulling the model toward such a lopsided plan? | obj: 53.4
  - raw: `model = load_model('decomp_lp97', models_dictionary) model.route_cap_40 = ConstraintList() for i in model.i:     for j in model.j:         model.route`
- **WHY-NOT/constraint_rule** — Q: The plant-2-to-terminal-2 lane still dominates even with a loose cap. Couldn't we tighten the rule so no single route exceeds 30% of the network's total throughput? I'd like to understand what that extra diversification really costs us. | obj: 56.8
  - raw: `model = load_model('decomp_lp97', models_dictionary) model.route_cap_30 = ConstraintList() for i in model.i:     for j in model.j:         model.route`
- **WHY-NOT/heuristic** — Q: Couldn't we just run a simple primary-carrier rule instead of this lane-by-lane optimization? Make plant-1 our lead carrier — have it fill terminals 1 and 2 to their full requirement first, since those are the ones it picks up on the way out, then let plant-2 mop up whatever's left at terminals 3 and 4. Wouldn't that kind of straightforward dispatch rule give us a perfectly workable plan? | obj: 87.0
  - raw: `model = load_model('decomp_lp97', models_dictionary) # Heuristic planning strategy: plant-1 is the primary carrier. Following a fixed # dispatch seque`

### demo1_lp  (6)  — `testing_library/feas_test/demo1_lp.txt`

- **WHAT-IF/new_constraint** — Q: The cooperative is rolling out a labor-equity rule next season — temporary labor in any single month can't exceed 40% of the total labor used that month. Plug that fairness constraint in and tell me where farm income and the cropping mix land. | obj: 1692.361181
  - raw: `model = load_model('demo1_lp', models_dictionary) model.temp_cap_40 = ConstraintList() for t in model.t:     model.temp_cap_40.add(model.tlab[t] <= 0.`
- **WHY-NOT/constraint_rule** — Q: Hiring out family labor in the slack months feels wasteful when we're still pulling in temporary workers during peak. Couldn't we require that the family hours we lend out in any given month never exceed the temp labor we bring in that same month? What's pulling the plan toward this hire-out-while-hiring-in pattern? | obj: 1694.680349
  - raw: `model = load_model('demo1_lp', models_dictionary) model.own_labor_first = ConstraintList() for t in model.t:     model.own_labor_first.add(model.fout[`
- **WHY-NOT/constraint_rule** — Q: Three crops are doing all the work and four aren't grown at all — that's a soil-rotation red flag if I've ever seen one. Couldn't we require that no single crop's acreage exceed 30% of the total cultivated area? Walk me through what's pulling the optimizer toward such a concentrated rotation. | obj: 1869.046154
  - raw: `model = load_model('demo1_lp', models_dictionary) model.crop_diversity = ConstraintList() for c in model.c:     model.crop_diversity.add(model.xcrop[c`
- **WHY-NOT/constraint_rule** — Q: Our temp crews are stretched paper-thin in the busy months and the quality shows. Shouldn't we hold each month's temporary hires to 20 days at the very most? What's driving the plan to lean on temp labor that hard in the peak? | obj: 1732.626432
  - raw: `model = load_model('demo1_lp', models_dictionary) model.temp_month_cap = ConstraintList() for t in model.t:     model.temp_month_cap.add(model.tlab[t]`
- **WHY-NOT/constraint_rule** — Q: The agronomist keeps warning that leaving four crops out of the ground entirely will wreck our soil over a few seasons. Shouldn't every crop get at least a quarter-hectare in the rotation? What's the optimizer seeing that makes it skip them altogether? | obj: 1838.59
  - raw: `model = load_model('demo1_lp', models_dictionary) model.min_rotation = ConstraintList() for c in model.c:     model.min_rotation.add(model.xcrop[c] >=`
- **WHY-NOT/heuristic** — Q: Cotton, onions, and tomato carry the fattest margins on this farm by a mile. Why not just pre-allocate by that pecking order — hand cotton its two hectares first, give onions and tomato a hectare each, and skip the low-margin crops entirely? Wouldn't that margin-first plan come out ahead of the model's fussy spread? | obj: 1659.26
  - raw: `model = load_model('demo1_lp', models_dictionary) priority_plan = {'cotton': 2.0, 'onions': 1.0, 'tomato': 1.0} for c in model.c:     model.xcrop[c].f`

### dice_mip  (3)  — `testing_library/feas_test/dice_mip.txt`

- **WHAT-IF/new_constraint** — Q: What if the first die had to be more evenly spread instead of clustering its faces? We're curious about requiring each consecutive face on die1 to jump by at least 2 pips over the previous one — what win count does that give? | obj: 20.0
  - raw: `model = load_model('dice_mip', models_dictionary) model.spread_d1 = ConstraintList() faces = list(model.f) for k in range(1, len(faces)):     model.sp`
- **WHY-NOT/heuristic** — Q: Honestly, why not just hand each die a clean block of consecutive numbers — die1 gets 1 through 6, die2 gets 7 through 12, die3 gets 13 through 18? That's the obvious way to lay out three dice. Lock the faces to that block layout and tell me how it stacks up against the optimizer's win count. | obj: 0.0
  - raw: `model = load_model('dice_mip', models_dictionary) # Heuristic 'consecutive blocks': give each die a contiguous run of integers # (die1 = flo..flo+5, d`
- **WHY-NOT/heuristic** — Q: A simpler rule of thumb: take the numbers 1 through 18 in order and just deal them round-robin onto the three dice, like dealing cards. Die1 gets 1,4,7,10,13,16; die2 gets 2,5,8,11,14,17; die3 gets 3,6,9,12,15,18. If we fix the faces to that dealt pattern, how many wins per die does it manage versus the optimizer? | obj: 15.0
  - raw: `model = load_model('dice_mip', models_dictionary) # Heuristic 'round-robin deal': sort flo..flo+17 and deal cyclically onto the dice, # so each die ge`

### dicegrid_mip  (3)  — `testing_library/feas_test/dicegrid_mip.txt`

- **WHAT-IF/new_constraint** — Q: Here's a variant worth a grid run: make die1's faces more spread out by demanding each successive face jump at least 2 pips past the one before it. What win count does the design hit under that spacing rule? | obj: 20.0
  - raw: `model = load_model('dicegrid_mip', models_dictionary) model.spread_d1 = ConstraintList() faces = list(model.f) for k in range(1, len(faces)):     mode`
- **WHY-NOT/heuristic** — Q: Skip the heavy grid search for a second — why not just give each die a straight block of consecutive numbers, die1 with 1 to 6, die2 with 7 to 12, die3 with 13 to 18? That's the most natural partition. Lock the faces into that block layout and tell me how it compares to the optimizer's win count. | obj: 0.0
  - raw: `model = load_model('dicegrid_mip', models_dictionary) # Heuristic 'consecutive blocks': give each die a contiguous run of integers # (die1 = flo..flo+`
- **WHY-NOT/heuristic** — Q: Here's a dead-simple alternative to the parallel search: take 1 through 18 in order and deal them round-robin across the three dice, like dealing a deck. Die1 gets 1,4,7,10,13,16; die2 gets 2,5,8,11,14,17; die3 gets 3,6,9,12,15,18. Fix the faces to that dealt pattern — how many wins per die does it land versus the full optimization? | obj: 15.0
  - raw: `model = load_model('dicegrid_mip', models_dictionary) # Heuristic 'round-robin deal': sort flo..flo+17 and deal cyclically onto the dice, # so each di`

### dicex_mip  (1)  — `testing_library/feas_test/dicex_mip.txt`

- **WHY-NOT/heuristic** — Q: Our product team likes a dead-simple rule for laying out the pips: sort the eighteen values and deal them out round-robin, so each die gets every third value (die 1 the smallest of each triple, die 2 the middle, die 3 the largest), then sort each die's six faces. If we lock the dice to that striped pattern, how many wins per die does it actually deliver versus the optimizer's tailored design? | obj: 15.0
  - raw: `model = load_model('dicex_mip', models_dictionary) # Heuristic 'striped deal': sort the 18-value pool, deal it round-robin across the # three dice (di`

### dinam_lp  (1)  — `testing_library/feas_test/dinam_lp.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole export schedule sector by sector? Couldn't we just ship every merchandize line at its minimum legal export floor and be done with it — how much does that cost us on initial consumption? | obj: 251.03476663036128
  - raw: `model = load_model('dinam_lp', models_dictionary) # Heuristic export policy: run every merchandize commodity at its lower export bound # (elo) in ever`

### egypt_lp  (1)  — `testing_library/feas_test/egypt_lp.txt`

- **WHY-NOT/heuristic** — Q: Why run the whole optimization? Couldn't we just plant the high-value perennials and cash crops — cotton, citrus and sugarcane — flat out to their regional land ceilings everywhere they're allowed, and let the rest fall where it may? | obj: 4115551.941837235
  - raw: `model = load_model('egypt_lp', models_dictionary) # Heuristic cash-crop policy: plant the high-value perennials/cash crops (cotton, # citrus, sugarcan`

### embmiex1_lp  (1)  — `testing_library/feas_test/embmiex1_lp.txt`

- **WHY-NOT/heuristic** — Q: Here's a dead-simple dispatch rule: lean on our biggest brewery first. Push every hub's keg order through San Diego until it's tapped out, and only spill the leftover onto Seattle. Wouldn't running the big house flat-out before touching the small one already hold a competitive distribution cost? | obj: 166.05
  - raw: `model = load_model('embmiex1_lp', models_dictionary) # Heuristic big-hub-first policy: fill the largest brewery (by capacity) across every # hub up to`

### epscm_lp  (1)  — `testing_library/feas_test/epscm_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over the dispatch at all? Couldn't we just lean green — run the renewables flat out first, then backfill whatever's left with the cheapest conventional units in order? | obj: 3225000.0
  - raw: `model = load_model('epscm_lp', models_dictionary) # Heuristic renewables-first policy: run the RES units to full capacity on the loads they # can serv`

### epscmmip_mip  (1)  — `testing_library/feas_test/epscmmip_mip.txt`

- **WHY-NOT/heuristic** — Q: Our planners would rather skip the solver and use a simple rule of thumb: rank items by their combined primary-plus-secondary value per unit of resource, grab them top-down while both budgets hold, and if the secondary floor isn't met yet, swap in the highest secondary-value leftovers until it is. If we lock the basket to that greedy recipe, how far does the primary score fall short of the optimizer's plan? | obj: 1871.0
  - raw: `model = load_model('epscmmip_mip', models_dictionary) # Heuristic 'balanced-density greedy with floor repair': pack items greedily by combined # value`

### farm_lp86  (3)  — `testing_library/feas_test/farm_lp86.txt`

- **WHY-NOT/constraint_rule** — Q: Sugar beets are grabbing 60% of the field — that's a soil-health red flag if I've ever seen one. Couldn't we require that no single crop's acreage exceed half the total cultivated land? Walk me through what's pulling the optimizer toward such a concentrated rotation. | obj: 109350.0
  - raw: `model = load_model('farm_lp86', models_dictionary) model.crop_diversity_50 = ConstraintList() for c in model.crop:     model.crop_diversity_50.add(mod`
- **WHY-NOT/constraint_rule** — Q: The whole field is leaning on sugar beets while wheat and corn sit on token plots. Shouldn't every crop be carrying real ground — say at least 100 acres each — so we're not one bad beet season away from disaster? What's keeping the model from spreading the acreage out like that? | obj: 117500.0
  - raw: `model = load_model('farm_lp86', models_dictionary) model.acreage_floor = ConstraintList() for c in model.crop:     model.acreage_floor.add(model.x[c]`
- **WHY-NOT/heuristic** — Q: Sugar beets are clearly the moneymaker per acre, so couldn't we run the field on a dead-simple priority rule: plant just enough wheat and corn to clear the feed minimums and pour every remaining acre into sugar beets? Lock that allocation in and let the solver settle the sell-and-buy side. Shouldn't that beat whatever the model is doing — what's it seeing that pushes it off the beets? | obj: 105200.0
  - raw: `model = load_model('farm_lp86', models_dictionary) # Heuristic: a fixed priority plan set in advance, then solve the residual. # Cover each feed minim`

### fawley_lp  (3)  — `testing_library/feas_test/fawley_lp.txt`

- **WHAT-IF/new_constraint** — Q: Trading desk wants to de-risk crude concentration — they're floating a sourcing rule that no single crude should ever exceed 50% of total crude purchased on a given cycle. How does that diversification mandate shift profit and the crude mix? | obj: 2614.571009128741
  - raw: `model = load_model('fawley_lp', models_dictionary) model.crude_diversity_50 = ConstraintList() for c in model.cr:     model.crude_diversity_50.add(mod`
- **WHY-NOT/constraint_rule** — Q: Pipestill is sitting around 90% utilization and reformer's at 89% while c-cracker's pegged at the wall. Couldn't we require that every productive unit run at least 95% of its nameplate every cycle to squeeze more value out of the existing kit? What's keeping the model from pushing them harder? | obj: -47.75021573892718
  - raw: `model = load_model('fawley_lp', models_dictionary) model.min_util_95 = ConstraintList() for k in model.k:     model.min_util_95.add(model.cap[k] >= 0.`
- **WHY-NOT/heuristic** — Q: Our blenders keep asking why we juggle three different recipes for the distillate products when a simpler standing playbook would be easier to run. Couldn't we just dedicate jet-fuel to recipe-3 and run all heat-oil on recipe-1, shut the other recipe slots, and let the rest of the plant settle around that fixed blending plan? Wouldn't that streamlined recipe discipline hold the margin? | obj: -340.3908185466162
  - raw: `model = load_model('fawley_lp', models_dictionary) recipe_plan = {'jet-fuel': 'recipe-3', 'heat-oil': 'recipe-1'} for cf in model.cfr:     keep = reci`

### feasopt1_lp  (1)  — `testing_library/feas_test/feasopt1_lp.txt`

- **WHY-NOT/heuristic** — Q: Why grind through an optimizer for routing? Couldn't we just send each plant's whole output to its single cheapest market on the freight sheet and let the relaxation cover whatever's left short? | obj: 400.0
  - raw: `model = load_model('feasopt1_lp', models_dictionary) # Heuristic single-source policy: send each plant's entire capacity to the one market # where its`

### fertd_mip  (1)  — `testing_library/feas_test/fertd_mip.txt`

- **WHY-NOT/heuristic** — Q: Treasury would love a blunt self-reliance rule: in every period, don't let imported final products exceed a small slice of that period's total nutrient demand, so domestic plants carry the load. If we hold imports to at most 6.5 percent of each period's combined nitrogen-plus-phosphate demand, how much more does the program cost than the optimizer's free-import plan? | obj: 173.864930901972
  - raw: `model = load_model('fertd_mip', models_dictionary) # Heuristic 'self-reliance ceiling': in each period cap total final-product imports at # 6.5% of th`

### ferts_lp  (1)  — `testing_library/feas_test/ferts_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over which superphosphate plant runs flat out? The three SSP plants have the same capacity — couldn't we just split total SSP-155 production evenly across them and call it a balanced plan? | obj: 58844.31595763
  - raw: `model = load_model('ferts_lp', models_dictionary) # Heuristic balanced-load policy: rather than let the optimizer pick which SSP plant # runs flat-out`

### flowshop_mip  (2)  — `testing_library/feas_test/flowshop_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we really need the solver for this? Couldn't we just push the parts through in plain catalog order — i1, then i2, all the way to i6? How much longer does that simple rule actually run? | obj: 40.0
  - raw: `model = load_model('flowshop_mip', models_dictionary) # Heuristic: run the parts in natural catalog order i1..i6 order = ['i1', 'i2', 'i3', 'i4', 'i5'`
- **WHY-NOT/heuristic** — Q: A scheduler I trust swears by tackling the longest jobs first. Let's try that dispatch rule here — sequence the parts heaviest total processing time down to lightest — and see how it stacks up. | obj: 38.0
  - raw: `model = load_model('flowshop_mip', models_dictionary) # Heuristic: longest-processing-time-first dispatch order = ['i6', 'i4', 'i1', 'i2', 'i5', 'i3']`

### food_mip  (1)  — `testing_library/feas_test/food_mip.txt`

- **WHY-NOT/heuristic** — Q: Our plant operators would much rather run one fixed recipe all year than re-tune the blend every month. Take the three oils whose hardness sits closest to the middle of the allowed [3,6] window and lock the blend to exactly those same three oils every month. How much profit do we give up versus the optimizer's month-by-month mix? | obj: 88150.0
  - raw: `model = load_model('food_mip', models_dictionary) # Heuristic 'single fixed recipe': pick the maxnusep oils whose hardness is closest to the # midpoin`

### gapmin_mip  (1)  — `testing_library/feas_test/gapmin_mip.txt`

- **WHY-NOT/heuristic** — Q: Our planners want a no-brainer dispatch rule instead of the solver's bespoke plan: take the bulkiest items first — the ones that eat the most capacity wherever they go — and drop each onto whichever resource can still hold it at the cheapest placement cost. If we lock the assignment to that greedy rule, how much more does the total cost run versus the optimizer's plan? | obj: 266.0
  - raw: `model = load_model('gapmin_mip', models_dictionary) # Heuristic 'heaviest-first cheapest-feasible': order items by descending minimum usage (the # bul`

### gussex1_lp  (6)  — `testing_library/feas_test/gussex1_lp.txt`

- **WHAT-IF/new_constraint** — Q: Compliance is uneasy about how much we lean on a single plant for each market — they want every market dual-sourced. There's a proposal on the table that no single plant should ever cover more than 75% of any single market's demand. What does the optimizer come back with for the cost and the new shipping plan under that rule? | obj: 120.20625
  - raw: `model = load_model('gussex1_lp', models_dictionary) model.dual_source_cap = Constraint(     model.i, model.j,     rule=lambda m, i, j: m.x[i, j] <= 0.`
- **WHAT-IF/new_constraint** — Q: There's a proposal to cap how much any one plant pushes down a single lane to keep the trucking contracts balanced — no plant-market route would carry more than 250 cases. Run it and tell me what the optimizer returns for the total cost and the routing. | obj: 115.42499999999998
  - raw: `model = load_model('gussex1_lp', models_dictionary) model.lane_cap = Constraint(     model.i, model.j,     rule=lambda m, i, j: m.x[i, j] <= 250, ) de`
- **WHY-NOT/constraint_rule** — Q: Right now Seattle isn't shipping to Chicago or Topeka at all, and barely shows up at New York. Shouldn't we require both plants to keep at least 20% participation on every market? Wouldn't a more balanced sourcing plan still come in close to today's cost? | obj: 117.675
  - raw: `model = load_model('gussex1_lp', models_dictionary) model.min_participation = Constraint(     model.i, model.j,     rule=lambda m, i, j: m.x[i, j] >=`
- **WHY-NOT/constraint_rule** — Q: Operations is uncomfortable with how concentrated the volume is on the San Diego-to-Chicago lane and the Seattle-to-New York lane. Shouldn't no single plant-market route carry more than 30% of the network's total throughput? What's keeping the model from picking a more balanced plan? | obj: 112.005
  - raw: `model = load_model('gussex1_lp', models_dictionary) model.lane_share_cap = Constraint(     model.i, model.j,     rule=lambda m, i, j: m.x[i, j] <= 0.3`
- **WHY-NOT/constraint_rule** — Q: It bugs me that Seattle is sitting nearly idle on two of our three markets. Couldn't we insist Seattle pull at least 30% of every market's demand so we aren't single-threaded on San Diego? What's stopping the model from leaning on Seattle that much? | obj: 122.7375
  - raw: `model = load_model('gussex1_lp', models_dictionary) model.seattle_floor = Constraint(     model.j,     rule=lambda m, j: m.x['seattle', j] >= 0.30 * m`
- **WHY-NOT/heuristic** — Q: Honestly, the obvious move is just to split every market between the two plants in proportion to their capacity — Seattle is 350 out of 950 total cases, San Diego is 600 out of 950, so each market draws 350/950 from Seattle and 600/950 from San Diego. Wouldn't that even-handed proportional split come in cheaper than the lopsided routing the model picked? | obj: 126.48552631578947
  - raw: `model = load_model('gussex1_lp', models_dictionary) # Capacity-proportional heuristic: assign in advance a uniform sourcing rule where each # market i`

### gussgrid_lp  (1)  — `testing_library/feas_test/gussgrid_lp.txt`

- **WHY-NOT/heuristic** — Q: Why not keep dispatch dead simple — load up our Seattle plant first, run its whole output across the lines before we even touch San Diego, and let San Diego just mop up whatever's left? Wouldn't filling the near plant before the far one hold a competitive logistics cost? | obj: 156.14999999999998
  - raw: `model = load_model('gussgrid_lp', models_dictionary) # Heuristic small-hub-first policy: exhaust the smaller plant (by capacity) across the # assembly`

### ibm1_lp  (2)  — `testing_library/feas_test/ibm1_lp.txt`

- **WHY-NOT/constraint_rule** — Q: Pure aluminum and pure silicon are the priciest line items in the recipe. Shouldn't scrap streams cover at least 85% of the total blend weight? What's the model seeing that's pushing it to lean on the pure stock so hard? | obj: 297.8586956521738
  - raw: `model = load_model('ibm1_lp', models_dictionary) scrap = ['bin-1','bin-2','bin-3','bin-4','bin-5'] model.scrap_floor_85 = Constraint(expr=sum(model.x[`
- **WHY-NOT/heuristic** — Q: We keep buying expensive pure aluminum to hit the 1500-lb aluminum minimum. Couldn't we just commit up front to leaning on our aluminum-richest scrap — run bin-3 at 500 lb and bin-5 at 300 lb, the two 80%-aluminum streams — and let the solver settle the rest of the recipe around that? Wouldn't sourcing the aluminum from scrap first come out cheaper than topping up with pure stock? | obj: 311.67055931161644
  - raw: `model = load_model('ibm1_lp', models_dictionary) # Heuristic planning strategy: aluminum-rich-scrap-first dedication, set in advance, then solve the r`

### icut_mip  (2)  — `testing_library/feas_test/icut_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need to optimize this? Just set every adjustable dial to the middle value of 3 and be done. What reading does that simple rule give? | obj: 3333.0
  - raw: `model = load_model('icut_mip', models_dictionary) # Heuristic: set every free dial to 3 for i in model.I:     if not model.x[i].fixed:         model.x`
- **WHY-NOT/heuristic** — Q: What if we just crank every dial to the top of whatever range it's allowed? Max them all out and tell me how high the index climbs. | obj: 4343.0
  - raw: `model = load_model('icut_mip', models_dictionary) # Heuristic: pin every free dial to its own upper bound for i in model.I:     if not model.x[i].fixe`

### imsl_lp  (4)  — `testing_library/feas_test/imsl_lp.txt`

- **WHAT-IF/new_constraint** — Q: Our QA team is on edge about the approximation overshooting the measured peak — the data tops out at 1.0 and we'd like to make sure no approximation node ever climbs above that. Treat it as a hard rule across every node and tell me what the fit looks like under that cap. | obj: 0.1505725111111114
  - raw: `model = load_model('imsl_lp', models_dictionary) model.ym_unity_cap = Constraint(     model.m,     rule=lambda mm, k: mm.ym[k] <= 1.0, ) description =`
- **WHY-NOT/constraint_rule** — Q: Looking at the approximation, consecutive node values jump around more than I'd expect for a smooth physical curve. Shouldn't we require neighboring approximation values to differ by no more than 0.25? What's keeping the model from picking a smoother fit? | obj: 0.8714366666666671
  - raw: `model = load_model('imsl_lp', models_dictionary) m_list = list(model.m) def _smooth_up(mm, idx, _ml=m_list):     if idx == len(_ml) - 1:         retur`
- **WHY-NOT/constraint_rule** — Q: Our QA team is uneasy with how the approximation overshoots above 1.0 at the peak. Shouldn't every node sit comfortably below 0.95, leaving a margin under the data maximum? Wouldn't a more conservative fit serve us better than this one that bumps right up against the ceiling? | obj: 0.5160011111111122
  - raw: `model = load_model('imsl_lp', models_dictionary) model.ym_margin_cap = Constraint(     model.m,     rule=lambda mm, k: mm.ym[k] <= 0.95, ) description`
- **WHY-NOT/heuristic** — Q: Why bother optimizing every node freely? The physics gives us three landmarks for free — the signal starts at 0, peaks at 1, and returns to 0 — so couldn't we just pin those three anchor nodes a-00, a-05 and a-10 to that known geometry and let the fit sort out only the in-between nodes? Wouldn't that landmark-first plan be good enough? | obj: 0.15159629166666705
  - raw: `model = load_model('imsl_lp', models_dictionary) # Heuristic plan: pin the three landmark nodes to the known sine geometry # (start=0, peak=1, return=`

### indus89_lp  (1)  — `testing_library/feas_test/indus89_lp.txt`

- **WHY-NOT/heuristic** — Q: Do we really need to grind through the full optimization? Couldn't we just pick our ten highest-value activities and agree up front to run them at no more than half their combined capacity, and let the rest of the plan fill in around that? | obj: 113972.70483583832
  - raw: `model = load_model('indus89_lp', models_dictionary) # Heuristic 'half-the-headline-capacity': take the ten activities with the largest # positive surp`

### indus_lp  (1)  — `testing_library/feas_test/indus_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over the wheat acreage in each polygon? Couldn't we just peg wheat to a fixed quarter of each polygon's irrigated land base and let everything else fill in around it? | obj: 881.6264154694308
  - raw: `model = load_model('indus_lp', models_dictionary) # Heuristic wheat policy: fix each polygon's wheat acreage to one quarter of its # irrigated land ba`

### iswnm_lp  (2)  — `testing_library/feas_test/iswnm_lp.txt`

- **WHY-NOT/constraint_rule** — Q: Reservoir contents swing widely month to month — Tarbela alone draws down to barely an eighth of capacity at certain points. Shouldn't every reservoir stay above 13% of its live capacity in every month, as a drought-resilience floor? What's the model trading away by drawing them down so deep? | obj: 114.03973
  - raw: `model = load_model('iswnm_lp', models_dictionary) res_nodes = [n for n in model.n if value(model.rcap[n]) > 0] model.storage_floor_13pct = Constraint(`
- **WHY-NOT/heuristic** — Q: Irrigation keeps pushing for an aggressive drawdown on Tarbela through the dry season to free up water downstream. Couldn't we just run Tarbela right down on its lower rule curve through March, April and June — drain it to the drought floor on a fixed schedule — and let the solver settle the rest of the system around it? How close to today's total volume would that leave us? | obj: 106.49254
  - raw: `model = load_model('iswnm_lp', models_dictionary) # Heuristic: a fixed dry-season drawdown schedule for Tarbela set in advance, then solve the residua`

### job_mip  (1)  — `testing_library/feas_test/job_mip.txt`

- **WHY-NOT/heuristic** — Q: All this fine-tuning of durations feels overengineered. Couldn't we just run every job at its minimum required number of days and call it done? What would that simple rush-everything plan cost us? | obj: 16800.0
  - raw: `model = load_model('job_mip', models_dictionary) # Heuristic: pin every job to its minimum required duration min_days = {1: 6, 2: 8, 3: 16, 4: 14, 5:`

### jobt_lp  (8)  — `testing_library/feas_test/jobt_lp.txt`

- **WHAT-IF/new_constraint** — Q: Warehouse is being repurposed and we lose all the buffer-storage racks next quarter — we'll have nowhere to park finished goods between weeks. Treat that as a hard rule that no inventory carries from one week to the next, and tell me what the production plan looks like under that lean setup. | obj: 21632.65306122449
  - raw: `model = load_model('jobt_lp', models_dictionary) model.no_carryover = Constraint(     model.t,     rule=lambda mm, t: mm.s[t] <= 0, ) description = 'W`
- **WHAT-IF/new_constraint** — Q: HR is floating a stability commitment for the union talks: keep at least 30 people on payroll every single week of the horizon, no dipping below that floor even in the lighter weeks. We're evaluating it — what does total cost come to if we hold a 30-worker floor throughout? | obj: 22536.363636363636
  - raw: `model = load_model('jobt_lp', models_dictionary) model.headcount_floor = Constraint(     model.t,     rule=lambda mm, t: mm.w[t] >= 30, ) description`
- **WHAT-IF/new_constraint** — Q: There's a proposal to lock in a single-shift line limit so the floor never runs more than 300 units in a week regardless of the order book. Run the plan with a 300-unit weekly production ceiling in place and tell me where total cost lands. | obj: 21961.11111111111
  - raw: `model = load_model('jobt_lp', models_dictionary) model.prod_cap = Constraint(     model.t,     rule=lambda mm, t: mm.p[t] <= 300, ) description = 'Wha`
- **WHY-NOT/constraint_rule** — Q: The current plan dumps 18.75 workers in a single week at the end of the horizon — that's a brutal offboarding cliff. Shouldn't we require that workers fired in any single week never exceed 25% of the headcount carried that week? What's keeping the model from picking a smoother ramp-down? | obj: 22761.46788990826
  - raw: `model = load_model('jobt_lp', models_dictionary) model.firing_cap = Constraint(     model.t,     rule=lambda mm, t: mm.f[t] <= 0.25 * mm.w[t], ) descr`
- **WHY-NOT/constraint_rule** — Q: The plan piles all the new hires into week 2 and runs flat for the rest of the horizon. Shouldn't hires in any single week stay under 30% of the headcount carried that week? What's keeping the model from picking a more measured ramp-up? | obj: 21583.673469387755
  - raw: `model = load_model('jobt_lp', models_dictionary) model.hiring_cap = Constraint(     model.t,     rule=lambda mm, t: mm.h[t] <= 0.30 * mm.w[t], ) descr`
- **WHY-NOT/constraint_rule** — Q: Finance keeps flagging the early-horizon stockpile — week 1 alone is sitting on close to 70 units of finished goods just to smooth things out later. Couldn't we hold inventory to no more than 40 units in any week and stop tying up that much working capital? What's stopping the model from running leaner on stock? | obj: 21412.244897959183
  - raw: `model = load_model('jobt_lp', models_dictionary) model.storage_cap = Constraint(     model.t,     rule=lambda mm, t: mm.s[t] <= 40, ) description = 'W`
- **WHY-NOT/constraint_rule** — Q: Right now we hire people up only to lay most of them off in the last week — it looks wasteful. Shouldn't we keep at least 35 workers on staff through the final week so we're not gutting the crew? What's keeping the model from carrying that headcount to the end? | obj: 23343.055555555555
  - raw: `model = load_model('jobt_lp', models_dictionary) model.end_headcount = Constraint(     expr=model.w[5] >= 35, ) description = 'Why-not: keep at least`
- **WHY-NOT/heuristic** — Q: Why are we letting the optimizer churn the headcount around so much? Couldn't we just commit to a flat staffing plan up front — bring the crew up to about 44 people for the busy middle weeks, hold it steady, and trim to 25 for the final week — and then let production and inventory fall out from that? Wouldn't that simple fixed-roster plan come out fine? | obj: 21440.0
  - raw: `model = load_model('jobt_lp', models_dictionary) # Planning-strategy heuristic: commit to a fixed staffing schedule up front # (week-1 incoming crew o`

### kand_lp  (1)  — `testing_library/feas_test/kand_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we keep procurement simple and just buy whichever raw material is cheapest per ton, split evenly across the two periods up to our storage limit? Chase the lowest sticker price on the input and let outsourcing cover the gaps. Wouldn't that hold a competitive cost? | obj: 4620.0
  - raw: `model = load_model('kand_lp', models_dictionary) # Heuristic cheapest-input policy: buy ONLY the raw material with the lowest unit cost c # (ignoring`

### knapsack_mip  (1)  — `testing_library/feas_test/knapsack_mip.txt`

- **WHY-NOT/heuristic** — Q: Our pickers don't want to run an optimizer every cycle — they'd rather use a back-of-the-envelope rule: rank items by bang-for-the-buck (profit per unit weight) and grab them in that order until the next one won't fit. If we pack the bag that greedy way, how much profit do we give up versus the optimizer's plan? | obj: 294.0
  - raw: `model = load_model('knapsack_mip', models_dictionary) # Heuristic greedy-by-density: rank items by profit-to-weight ratio and take each, in # that ord`

### knights_mip  (2)  — `testing_library/feas_test/knights_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need to optimize this? Everyone knows the trick — drop a knight on every same-color square and you can't have two attacking, since a knight always jumps to the opposite color. Just lay that pattern down and confirm it actually gives the full count. | obj: 32.0
  - raw: `model = load_model('knights_mip', models_dictionary) # Heuristic: the classic 'all one color' rule -- a knight always moves to the # opposite color, s`
- **WHY-NOT/heuristic** — Q: Here's a simpler idea our floor team likes: just crowd all the knights onto the left half of the board, one per same-color square in columns 1 through 4, and leave the right side bare. Slot that in and tell me how many knights it actually seats. | obj: 16.0
  - raw: `model = load_model('knights_mip', models_dictionary) # Heuristic: pack only the left half -- one knight per same-color square in cols 1-4. for i in mo`

### landing_mip  (1)  — `testing_library/feas_test/landing_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of the optimizer's mixed assignment, couldn't ground control just run a simple rule of thumb — keep aircraft 1 and 2 on runway 1 and send 3, 4 and 5 to runway 2? What total delay cost would that clean split give us? | obj: 550.0
  - raw: `model = load_model('landing_mip', models_dictionary) # Heuristic split: aircraft 1,2 on runway 1; aircraft 3,4,5 on runway 2 group_r1 = [1, 2] for i i`

### lands_det_lp  (5)  — `testing_library/feas_test/lands_det_lp.txt`

- **WHAT-IF/new_constraint** — Q: The system operator is rolling out a single-asset concentration rule for grid resilience - no single plant type should ever carry more than 30% of total installed capacity. What does the build mix and total cost look like once that diversification ceiling kicks in? | obj: 293.4
  - raw: `model = load_model('lands_det_lp', models_dictionary) model.diversification_cap = Constraint(     model.i,     rule=lambda mm, i: mm.x[i] <= 0.30 * su`
- **WHAT-IF/new_constraint** — Q: There's a reliability proposal on the table for base-load coverage: no single plant should supply more than half of mode-1 dispatch, so an outage can't strand the whole base load. What does the optimizer return for total cost if we plug that in? | obj: 296.0
  - raw: `model = load_model('lands_det_lp', models_dictionary) model.mode1_share = Constraint(     model.i,     rule=lambda mm, i: mm.y[i, 'mode-1'] <= 0.50 *`
- **WHY-NOT/constraint_rule** — Q: Right now the build leans heavily on plant-4 carrying a third of total capacity while the cheaper plant-2 sits half-utilized. Shouldn't no single plant type exceed a quarter of the total installed capacity, as a resilience floor? What's keeping the model from picking a more balanced portfolio? | obj: 294.0
  - raw: `model = load_model('lands_det_lp', models_dictionary) model.uniform_cap = Constraint(     model.i,     rule=lambda mm, i: mm.x[i] <= 0.25 * sum(mm.x[i`
- **WHY-NOT/constraint_rule** — Q: Plant-4 sits there with four units of capacity built but barely dispatches anything - that's a lot of idle iron. Shouldn't every plant we pay to install actually run at least 40% of its capacity? What's keeping the model from putting that hardware to work? | obj: 294.0
  - raw: `model = load_model('lands_det_lp', models_dictionary) model.utilization_floor = Constraint(     model.i,     rule=lambda mm, i: sum(mm.y[i, j] for j i`
- **WHY-NOT/heuristic** — Q: All this fine-grained spreading of capacity across four plants feels like over-engineering. Couldn't we just run a simple twin-anchor build - split the mandated 12 units evenly, six and six, across the two cheapest plants, plant-2 and plant-4, and let the solver settle the dispatch from there? Shouldn't that clean two-asset plan still come in competitive on cost? | obj: 305.0
  - raw: `model = load_model('lands_det_lp', models_dictionary) # Heuristic: a fixed twin-anchor build plan set in advance, then solve the dispatch residual. #`

### lands_stoc_lp  (6)  — `testing_library/feas_test/lands_stoc_lp.txt`

- **WHAT-IF/new_constraint** — Q: The system operator is rolling out a single-asset concentration rule for resilience - no single plant type should ever account for more than 30 percent of total installed capacity. How does that diversification ceiling move the build plan and expected total cost? | obj: 382.1213333333333
  - raw: `model = load_model('lands_stoc_lp', models_dictionary) model.diversification_cap = Constraint(     model.i,     rule=lambda mm, i: mm.x[i] <= 0.30 * s`
- **WHAT-IF/new_constraint** — Q: There's a reliability proposal on the table for base-load coverage: no single plant should supply more than half of mode-1 dispatch in any scenario, so an outage can't strand the whole base load. We're evaluating that ceiling now; what does the optimizer return for expected total cost? | obj: 384.16
  - raw: `model = load_model('lands_stoc_lp', models_dictionary) model.mode1_share = Constraint(     model.i, model.s,     rule=lambda mm, i, sc: mm.ys[i, 'mode`
- **WHY-NOT/constraint_rule** — Q: The current build leans on plant-2 carrying a third of total capacity while plant-4 sits at minimal headroom. Shouldn't no single plant type exceed a quarter of the total installed capacity, as a resilience floor? What's keeping the model from picking a more balanced portfolio? | obj: 383.4
  - raw: `model = load_model('lands_stoc_lp', models_dictionary) model.uniform_cap = Constraint(     model.i,     rule=lambda mm, i: mm.x[i] <= 0.25 * sum(mm.x[`
- **WHY-NOT/constraint_rule** — Q: Operating levels swing widely from one scenario to the next - the same plant might run flat out under s-3 and idle under s-1. Shouldn't each plant's total dispatch under the high-load scenario stay within 50 percent above its dispatch under the low-load scenario, as a smoothing rule? What's keeping the model from picking a more even cross-scenario mix? | obj: 384.40833333333336
  - raw: `model = load_model('lands_stoc_lp', models_dictionary) model.cross_scenario_smoothing = Constraint(     model.i,     rule=lambda mm, i: sum(mm.ys[i, j`
- **WHY-NOT/constraint_rule** — Q: We're paying to install all this capacity and then a chunk of it barely runs in some scenarios. Shouldn't every installed plant dispatch at least 40 percent of its capacity in each scenario, so we're not sitting on idle iron? What's keeping the model from putting that hardware to work? | obj: 382.46666666666664
  - raw: `model = load_model('lands_stoc_lp', models_dictionary) model.utilization_floor = Constraint(     model.i, model.s,     rule=lambda mm, i, sc: sum(mm.y`
- **WHY-NOT/heuristic** — Q: All this fine-grained spreading of capacity across four plants feels like over-engineering. Couldn't we just run a clean cheap-merit-order build - rank the plants by installed cost and dedicate the mandated 12 units to the three cheapest ones, 5 on plant-4, 4 on plant-2, 3 on plant-1, and skip the pricey plant-3 entirely - then let the solver settle the scenario dispatch from there? Shouldn't that lean three-asset plan still come in competitive on expected cost? | obj: 397.5
  - raw: `model = load_model('lands_stoc_lp', models_dictionary) # Heuristic: a fixed cheap-merit-order build plan set in advance, then solve the scenario-dispa`

### latin_mip  (2)  — `testing_library/feas_test/latin_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need the solver for the first square? Couldn't we just drop in the textbook cyclic pattern — each row shifted one step from the last — and let the second square sort itself out around it? How does that hold up? | obj: 32.0
  - raw: `model = load_model('latin_mip', models_dictionary) # Heuristic: fix square one to the textbook cyclic Latin square (value index = (row+col) mod 4) K =`
- **WHY-NOT/heuristic** — Q: Here's a simple recipe for the first square: step the value forward by three each column instead of one, row over row. Slap that pattern down and let the other square fall in around it — does it still work out? | obj: 32.0
  - raw: `model = load_model('latin_mip', models_dictionary) # Heuristic: fix square one to a shifted Latin square (value index = (row + 3*col) mod 4) K = list(`

### lop_mip  (1)  — `testing_library/feas_test/lop_mip.txt`

- **WHY-NOT/heuristic** — Q: Operations wants a contingency rule: take the single highest-value line out of service — the one whose endpoints together could serve the most direct demand — and let the rest of the network cover the edge requirements around it. If we sideline that one busiest line, how much direct ridership do we give up versus the optimizer's full plan? | obj: 79131.0
  - raw: `model = load_model('lop_mip', models_dictionary) # Heuristic 'sideline the busiest line': score every candidate line by the total OD demand it # could`

### lrs_mip  (1)  — `testing_library/feas_test/lrs_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother solving the recurrence at all — couldn't we just seed it by copying the observed signal over the first 48 bits and let the XOR rule run from there? How much worse does that fit the data? | obj: 149.0
  - raw: `model = load_model('lrs_mip', models_dictionary) # Heuristic 'copy-the-signal': seed the first 48 bits with the observed sequence c(t) # (rounded to 0`

### macro_lp  (1)  — `testing_library/feas_test/macro_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just keep it simple and buy a flat 45 barrels from each crude supplier, mid-continent and West Texas alike? What would that even-handed sourcing rule do to income? | obj: -62.57867490550616
  - raw: `model = load_model('macro_lp', models_dictionary) # Heuristic: buy a flat 45 barrels from each crude supplier model.u['mid-c'].fix(45) model.u['w-tex'`

### magic_mip  (1)  — `testing_library/feas_test/magic_mip.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just keep things simple and run a flat five type-1 units in every block, around the clock? What would that steady baseline schedule cost? | obj: 1107500.0
  - raw: `model = load_model('magic_mip', models_dictionary) # Heuristic: run a flat 5 type-1 units in every demand block for t in model.t:     model.n['type-1'`

### maintenance_mip  (2)  — `testing_library/feas_test/maintenance_mip.txt`

- **WHY-NOT/constraint_rule** — Q: The gaps between shutdowns look ragged — three months here, four there. Couldn't we just settle into a steady four-month rhythm, never letting two outages sit closer than four months apart? Walk me through what's pulling it the other way. | obj: 36620.0
  - raw: `model = load_model('maintenance_mip', models_dictionary) def _spacing(model, t):     if t + 3 > len(model.T):         return Constraint.Skip     retur`
- **WHY-NOT/heuristic** — Q: Honestly the cleanest thing for the crews would be a fixed drumbeat — pin an outage to every fourth month, months 4, 8, 12, 16, 20 and 24, and no outages anywhere else, then let the scheduler slot the maintenance around it. What total cost does that simple regular cadence give us? | obj: 36620.0
  - raw: `model = load_model('maintenance_mip', models_dictionary) cadence = {4, 8, 12, 16, 20, 24} for t in model.T:     model.o[t].fix(1 if t in cadence else`

### marilyn_mip  (1)  — `testing_library/feas_test/marilyn_mip.txt`

- **WHY-NOT/heuristic** — Q: Our puzzle-desk has a quick rule of thumb: the two most-connected hub circles are the easiest to keep separated from everything if you nail them to the two extreme digits, so pin the busiest circle to 1 and the next-busiest to 8 and let the rest fall out. If we lock the layout to that hubs-take-the-extremes rule, does the digit total move off what the full optimizer finds? | obj: 36.0
  - raw: `from collections import defaultdict model = load_model('marilyn_mip', models_dictionary) # Heuristic 'hubs take the extremes': rank circles by adjacen`

### markov_lp  (9)  — `testing_library/feas_test/markov_lp.txt`

- **WHAT-IF/new_constraint** — Q: There's a proposal to keep more of the reserve loaded for resilience — push at least 30% of the total steady-state probability mass onto the high-reserve action levels of 12 and above. What does the optimizer return for the present value of expected cost under that? | obj: 2573.074686126781
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) high = [12, 15, 18,`
- **WHAT-IF/new_constraint** — Q: We're evaluating a resilience floor that limits how often the program lets the reserve sit empty — cap the steady-state mass on the empty-reserve state at no more than 10% of the total. Where does the present value of expected cost land if we plug that in? | obj: 2551.4046345677784
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) model.empty_cap = C`
- **WHAT-IF/new_constraint** — Q: DOE is weighing a stronger-stockpile mandate: keep at least 55% of the steady-state probability mass on the mid-to-high action levels of 9 and above. How does that move the present value of expected cost? | obj: 2602.1328741683747
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) mid = [9, 12, 15, 1`
- **WHAT-IF/new_constraint** — Q: There's a proposal to stop the policy leaning so hard on the 3-billion-barrel action — hold the steady-state mass on the 3-level action to at most 20% of the total. What does the optimizer return for the present value of expected cost? | obj: 2405.7432628439847
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) model.action3_cap =`
- **WHY-NOT/constraint_rule** — Q: The current policy lets a handful of action levels carry the whole steady-state distribution while many levels sit at near-zero mass. Couldn't we require that no single action level ever holds more than 35% of the total mass? Wouldn't a more diversified reserve distribution still come in close to today's expected cost? | obj: 2434.1499712403643
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) def level_cap_rule(`
- **WHY-NOT/constraint_rule** — Q: Disruption hedging would seem to argue for keeping a real buffer at the top. Couldn't we require that at least 15% of the total steady-state mass sits on the 21-billion-barrel action? Wouldn't that fuller-reserve posture still leave us reasonably close to today's expected cost? | obj: 2624.758244089633
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) model.full_floor =`
- **WHY-NOT/constraint_rule** — Q: The current policy quietly accepts large drawdowns once a disruption hits, sliding the reserve down hard. Couldn't we require that during the disrupted market, at least 40% of each level's mass holds flat at that level? Wouldn't a stickier disrupted-state policy still leave us close to today's expected cost? | obj: 2473.1231272048994
  - raw: `model = load_model('markov_lp', models_dictionary) def disrupt_hold_rule(model, s):     if s == 'empty':         return Constraint.Skip     return mod`
- **WHY-NOT/constraint_rule** — Q: It looks like the policy leans on running the reserve all the way down to empty as a cheap action. Couldn't we hold the steady-state mass landing on the empty action to at most 5% of the total, so we're not constantly emptying out? Wouldn't a less drain-happy plan still come in close to today's expected cost? | obj: 2600.541899750465
  - raw: `model = load_model('markov_lp', models_dictionary) T = sum(model.z[s, i, sp] for s in model.s for i in model.i for sp in model.sp) model.empty_action_`
- **WHY-NOT/heuristic** — Q: All these tiny mid-level shuffles look like operational noise. Couldn't we just run a clean ladder plan — in a normal market only ever hold the current level or step it up by one, and in a disrupted market always hold flat — and let the solver settle the exact mass from there? Wouldn't that disciplined ladder come out close on expected cost? | obj: 3300.174364220133
  - raw: `model = load_model('markov_lp', models_dictionary) # Heuristic ladder plan set in advance, then solve the residual: # normal market -> hold the level`

### maxcut_mip  (1)  — `testing_library/feas_test/maxcut_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of a full optimization, our operators want a dead-simple rule: walk the nodes in order and drop each one onto whichever side gives the bigger immediate gain against the neighbors already placed. If we lock the partition to that one-pass greedy assignment, how much cut weight do we leave on the table versus the optimizer's plan? | obj: 24803528.0
  - raw: `model = load_model('maxcut_mip', models_dictionary) # Heuristic 'greedy one-pass': visit nodes in index order; place each on whichever side # maximize`

### mesc_lp  (1)  — `testing_library/feas_test/mesc_lp.txt`

- **WHY-NOT/heuristic** — Q: Carrying all that opening stock ties up cash. Couldn't we just start the season empty — pin the initial on-hand inventory to zero at every stage and let backlogs catch up? What would that bare-shelves start actually cost us? | obj: 16.179223254720284
  - raw: `model = load_model('mesc_lp', models_dictionary) # Heuristic: start the season with no on-hand inventory at any stage for s in model.M0:     model.i[0`

### mexls_lp  (1)  — `testing_library/feas_test/mexls_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over which mill exports what? Couldn't we just hand each mill an export quota in proportion to its steelmaking-furnace capacity and let it fill that however it can? | obj: 27587.773828870595
  - raw: `model = load_model('mexls_lp', models_dictionary) # Heuristic export-quota policy: cap each mill's total exports at a share of the # overall export ce`

### mexsd_mip  (2)  — `testing_library/feas_test/mexsd_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need this whole expansion program? Suppose we just freeze capital spending entirely — build nothing new and run on the plants we already have plus imports. How much worse does that come out? | obj: 13951.920609282432
  - raw: `model = load_model('mexsd_mip', models_dictionary) # Heuristic: no new capacity expansion anywhere for me in model.me:     for i in model.i:         f`
- **WHY-NOT/heuristic** — Q: Here's a blunt strategy: just concentrate every new unit at Sicartsa and don't expand anywhere else. Pin all the build-out to that one site and tell me what it costs. | obj: 12933.351958521058
  - raw: `model = load_model('mexsd_mip', models_dictionary) # Heuristic: only Sicartsa may receive new units; forbid expansion elsewhere for me in model.me:`

### mexss_lp  (1)  — `testing_library/feas_test/mexss_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over the export allocation? Couldn't we just hand each mill an export quota in proportion to its steel-furnace capacity and fill the whole export ceiling that way? | obj: 546.773777050096
  - raw: `model = load_model('mexss_lp', models_dictionary) # Heuristic export-quota policy: give each plant a share of the export ceiling eb # in proportion to`

### mine_lp  (8)  — `testing_library/feas_test/mine_lp.txt`

- **WHAT-IF/new_constraint** — Q: Mine planning is rolling out a daily haulage cap to keep trucks on schedule — total extraction across all blocks should not exceed 6 block-equivalents in the steady-state plan. How does that haulage limit move the extraction plan and the total profit? | obj: 7499.999999999999
  - raw: `model = load_model('mine_lp', models_dictionary) model.haulage_cap = Constraint(     expr=sum(model.x[l, i, j] for (l, i, j) in model.D) <= 6.0 ) desc`
- **WHAT-IF/new_constraint** — Q: There's a proposal to ring-fence the surface campaign: the level-1 bench should be worked to no more than 8 block-equivalents this period so the shovels can rotate down to the next bench. What does the optimizer return for the plan and total profit under that level-1 budget? | obj: 15555.555555555553
  - raw: `model = load_model('mine_lp', models_dictionary) model.lvl1_budget = Constraint(     expr=sum(model.x[1, i, j] for i in model.I for j in model.J if (1`
- **WHAT-IF/new_constraint** — Q: We're evaluating a leaner mining campaign this season — pull no more than 10 block-equivalents in total across the whole pit. How does total profit and the extraction plan come out under that throughput ceiling? | obj: 12500.000000000004
  - raw: `model = load_model('mine_lp', models_dictionary) model.total_cap = Constraint(     expr=sum(model.x[l, i, j] for (l, i, j) in model.D) <= 10.0 ) descr`
- **WHAT-IF/new_constraint** — Q: Geotech wants to slow the second-bench advance for wall-stability monitoring: level-2 extraction should be held to at most 2 block-equivalents this period. What does the plan and the total profit look like with that second-bench limit in place? | obj: 9250.0
  - raw: `model = load_model('mine_lp', models_dictionary) model.l2cap = Constraint(     expr=sum(model.x[2, i, j] for i in model.I for j in model.J if (2, i, j`
- **WHY-NOT/constraint_rule** — Q: Surface mining is going in patchy — some level-1 blocks are fully out while others sit at zero, which leaves an uneven pit floor for the crews working below. Shouldn't every level-1 block be extracted at least 40% to keep the floor reasonably flat? What's keeping the model from smoothing that surface pass out? | obj: 12500.0
  - raw: `model = load_model('mine_lp', models_dictionary) def _surface_floor_rule(mm, i, j):     if (1, i, j) not in mm.D:         return Constraint.Skip     r`
- **WHY-NOT/constraint_rule** — Q: The plan hammers the front corner of every bench and barely touches the back corner, which is wearing the haul ramps unevenly. Couldn't we make the back-corner block carry at least a quarter of whatever the front-corner block gets on each level? What's stopping the model from balancing the two corners like that? | obj: 16875.0
  - raw: `model = load_model('mine_lp', models_dictionary) def _corner_parity_rule(mm, l):     if (l, 1, 1) not in mm.D or (l, 4, 4) not in mm.D:         return`
- **WHY-NOT/constraint_rule** — Q: Honestly the surface pass still looks half-done in places — a 40% floor wasn't enough to flatten it. Shouldn't every level-1 block come out at least 50% so the next bench has a clean, level working platform? Why won't the model commit to that on the top bench? | obj: 11250.0
  - raw: `model = load_model('mine_lp', models_dictionary) def _even_surface_rule(mm, i, j):     if (1, i, j) not in mm.D:         return Constraint.Skip     re`
- **WHY-NOT/heuristic** — Q: Mobilizing and demobilizing the fleet twice is what eats us. Couldn't we just run a clean two-bench campaign — take the whole top bench and the whole second bench out at 100%, walk away, and skip the deep stuff entirely? Wouldn't committing to that two-pass plan up front beat all this fractional dithering on profit? | obj: -26000.0
  - raw: `model = load_model('mine_lp', models_dictionary) # Heuristic planning strategy: commit in advance to a two-bench campaign — fully # extract every acce`

### mrp2_mip  (1)  — `testing_library/feas_test/mrp2_mip.txt`

- **WHY-NOT/heuristic** — Q: Our schedulers swear by a build-ahead rule for the finished good: get every AJ8172 run done in the front of the calendar and keep the tail end of the horizon clear as a service buffer. If we lock AJ8172 so none of its production lands in the last three buckets, how much worse does the weighted production total get versus the optimizer's plan? | obj: 7800.0
  - raw: `model = load_model('mrp2_mip', models_dictionary) # Heuristic 'build AJ8172 ahead': schedulers want the finished good produced in the front # of the h`

### msm_lp  (1)  — `testing_library/feas_test/msm_lp.txt`

- **WHY-NOT/heuristic** — Q: Why run a full optimizer for this? Rail is plainly the cheaper mode per km — couldn't we just load everything onto rail at every bagging center and let the routing fall out from there? How much does that simple rule cost us? | obj: 3984.1349999999975
  - raw: `model = load_model('msm_lp', models_dictionary) # Heuristic: force all loading onto the cheapest per-km mode (computed from mrate), # zeroing loading`

### multipleMB_mip  (1)  — `testing_library/feas_test/multipleMB_mip.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just split the work cleanly — put jobs A, B, C on machine A and the rest on machine B — instead of whatever mix the model picked? What makespan would that simple split give? | obj: 21.0
  - raw: `model = load_model('multipleMB_mip', models_dictionary) # Heuristic: jobs A,B,C on machine A; D,E,F,G on machine B group_a = ['A', 'B', 'C'] for j in`

### mws_mip  (1)  — `testing_library/feas_test/mws_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need to estimate the coefficients? Just keep the anchored cost term and zero out every other weight, then count how many households that bare-bones rule happens to get right. How far off the fitted model is that? | obj: 521.0
  - raw: `model = load_model('mws_mip', models_dictionary) # Heuristic: skip estimation -- zero out every free coefficient (beta[DCOST] stays # pinned at 1 for`

### nebrazil_lp  (1)  — `testing_library/feas_test/nebrazil_lp.txt`

- **WHY-NOT/heuristic** — Q: Why optimize every one of the capped activities individually? Couldn't we just run each of the bounded-free activities at a flat 60% of its own upper limit and call it a day? What does that simple rule cost us? | obj: 7477.7130834551
  - raw: `model = load_model('nebrazil_lp', models_dictionary) # Heuristic: instead of optimizing each bounded-free activity, run every one at a # flat 60% of i`

### nemhaus_mip  (2)  — `testing_library/feas_test/nemhaus_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need the layout solver? Just throw every activity into one big facility — fac-1 — and call it done. How much interaction cost does that lazy plan rack up? | obj: 48.0
  - raw: `model = load_model('nemhaus_mip', models_dictionary) # Heuristic: cram every activity into fac-1 for i in model.i:     for j in model.j:         model`
- **WHY-NOT/heuristic** — Q: What about a dead-simple pairing rule — act-1 and act-2 in fac-1, act-3 and act-4 in fac-2, act-5 on its own in fac-3? How does that tidy little layout score on interaction cost? | obj: 7.0
  - raw: `model = load_model('nemhaus_mip', models_dictionary) # Heuristic: pair by index -- (act-1,act-2)->fac-1, (act-3,act-4)->fac-2, act-5->fac-3 place = {'`

### nemhaus_nlp  (2)  — `testing_library/feas_test/nemhaus_nlp.txt`

- **WHY-NOT/heuristic** — Q: Do we even need the layout solver? Just cram every activity into one big facility — fac-1 — and call it done. How much interaction cost does that lazy plan rack up? | obj: 48.0
  - raw: `model = load_model('nemhaus_nlp', models_dictionary) # Heuristic: cram every activity into fac-1 for i in model.i:     for j in model.j:         model`
- **WHY-NOT/heuristic** — Q: What about a dead-simple pairing rule — act-1 and act-2 in fac-1, act-3 and act-4 in fac-2, act-5 on its own in fac-3? How does that tidy little layout score on interaction cost? | obj: 7.0
  - raw: `model = load_model('nemhaus_nlp', models_dictionary) # Heuristic: pair by index -- (act-1,act-2)->fac-1, (act-3,act-4)->fac-2, act-5->fac-3 place = {'`

### netgen_lp  (1)  — `testing_library/feas_test/netgen_lp.txt`

- **WHY-NOT/heuristic** — Q: Why churn through a full network optimization? Couldn't we just pre-commit each market to take half its volume off its single cheapest inbound lane and let the rest sort itself out? | obj: 14572935.5
  - raw: `model = load_model('netgen_lp', models_dictionary) # Heuristic 'half-off-cheapest': pre-commit each market (positive-demand node) to take # half of it`

### nonsharp_mip  (1)  — `testing_library/feas_test/nonsharp_mip.txt`

- **WHY-NOT/heuristic** — Q: A planner's rule of thumb here is to diversify away from the first candidate and just commit to the last column in the superstructure. If we lock the build to that rule, how much more expensive is the master than the optimizer's pick? | obj: 1.4126401296929427
  - raw: `model = load_model('nonsharp_mip', models_dictionary) # Heuristic 'build-the-last-candidate': commit to the highest-indexed candidate column # only, s`

### openpit_mip  (1)  — `testing_library/feas_test/openpit_mip.txt`

- **WHY-NOT/heuristic** — Q: Our mine planners like a blunt rule: dig every pit to the same uniform depth, picking the shallowest common cut-off that still leaves enough rock to cover total demand, and leave everything below that line in the ground. If we lock the plan to that single uniform-depth pattern, how much worse is the discounted net income than the optimizer's tailored schedule? | obj: 8.58678964635662
  - raw: `model = load_model('openpit_mip', models_dictionary) # Heuristic 'uniform extraction depth': cap every pit at the same maximum depth K. # K = the shal`

### pak_lp  (4)  — `testing_library/feas_test/pak_lp.txt`

- **WHAT-IF/new_constraint** — Q: The cabinet wants a smoother investment build-up — total investment in any year should be at least 5% above the previous year's, beyond the existing non-decreasing rule, so the build-out doesn't stagnate mid-plan. How does that minimum-growth floor on investment shift the development plan and the welfare outcome? | obj: 993.1268245683216
  - raw: `model = load_model('pak_lp', models_dictionary) te = list(model.te) def inv_growth_rule(model, i):     if i < len(te) - 1:         return model.ti[te[`
- **WHY-NOT/constraint_rule** — Q: The current plan has consumption crawling in the early years and only catching up later. Couldn't we require that consumption `c[te]` grow at least 5% every single year, as a household-living-standards floor? Wouldn't a steadier, more front-loaded consumption path still land close to today's welfare? | obj: 1067.5231699581575
  - raw: `model = load_model('pak_lp', models_dictionary) te = list(model.te) def cons_growth_rule(model, i):     if i < len(te) - 1:         return model.c[te[`
- **WHY-NOT/constraint_rule** — Q: The plan leans hard on foreign aid early and then lets it taper off. Couldn't we require that net capital inflow `f[t]` in any single year stay within 30% above the horizon average, as a smoothing rule? Wouldn't a more even aid trajectory still come in close to today's welfare? | obj: 1041.2321459242783
  - raw: `model = load_model('pak_lp', models_dictionary) N = len(list(model.t)) def aid_smooth_rule(model, t):     return model.f[t] <= 1.3 * (sum(model.f[tt]`
- **WHY-NOT/heuristic** — Q: The non-traded sector is where most of the country's productive base sits — couldn't we just commit the entire investment build-out to non-traded production and shut the traded sector out of the capital plan entirely? Set that single-sector dedication up front and let the solver settle the rest. Wouldn't that focused strategy still come out ahead on welfare? | obj: 709.3660931112756
  - raw: `model = load_model('pak_lp', models_dictionary) # Heuristic: a non-traded-only investment dedication set in advance, then solve the residual. # Commit`

### paklive_lp  (8)  — `testing_library/feas_test/paklive_lp.txt`

- **WHAT-IF/new_constraint** — Q: The dairy co-op is pushing a herd-expansion rule — the farm has to keep at least 5 head of livestock combined across all the herd types as a milk-supply commitment to the cooperative. How does that herd-expansion rule reshape the farm plan and the net return? | obj: 18902.00537498841
  - raw: `model = load_model('paklive_lp', models_dictionary) model.herd_floor = Constraint(     expr=sum(model.xlivestk[h] for h in model.H) >= 5.0 ) descripti`
- **WHAT-IF/new_constraint** — Q: The cotton federation is rolling out a cropping-mix rule for soil-health reasons — cotton acreage on any one farm can't run above 5 acres for the season. How does that cotton cap reshape the cropping plan and the net return? | obj: 18800.02085395013
  - raw: `model = load_model('paklive_lp', models_dictionary) model.cotton_cap = Constraint(     expr=model.xcrop['cotton'] <= 5.0 ) description = 'What-if: cot`
- **WHAT-IF/new_constraint** — Q: There's a proposal to keep a green-fodder floor on the farm so the livestock side always has feed on hand — at least 2 acres combined across the fodder crops, kharfodder and berseem. If we hold that fodder floor, what does the optimizer return for net return? | obj: 18995.066135204084
  - raw: `model = load_model('paklive_lp', models_dictionary) model.fodder_floor = Constraint(     expr=model.xcrop['kharfodder'] + model.xcrop['berseem'] >= 2.`
- **WHY-NOT/constraint_rule** — Q: The current cropping mix loads everything onto cotton and lets the secondary crops sit underused. Shouldn't no single crop occupy more than 40% of the cultivated acreage, as a soil-health diversification rule? What's keeping the model from picking a more balanced mix? | obj: 19227.156894925334
  - raw: `model = load_model('paklive_lp', models_dictionary) model.diversification = Constraint(     model.C,     rule=lambda mm, c: mm.xcrop[c] <= 0.40 * sum(`
- **WHY-NOT/constraint_rule** — Q: The current plan walks away from buffalo dairy entirely, even though there's good year-round demand from the local mandi. Shouldn't the farm commit at least 2 buffalo cows as a baseline dairy operation? What's keeping the model from running a small dairy alongside the cropping? | obj: 19187.14013831834
  - raw: `model = load_model('paklive_lp', models_dictionary) model.dairy_commit = Constraint(     expr=model.xlivestk['bufflocows'] >= 2.0 ) description = 'Why`
- **WHY-NOT/constraint_rule** — Q: This plan leans hard on one or two crops and leaves the rest of the rotation thin. Couldn't we tighten the diversification rule further and hold every crop under 30% of the cultivated acreage? Shouldn't a genuinely spread-out rotation still clear a workable return? | obj: 18409.05091545894
  - raw: `model = load_model('paklive_lp', models_dictionary) model.crop_cap30 = Constraint(     model.C,     rule=lambda mm, c: mm.xcrop[c] <= 0.30 * sum(mm.xc`
- **WHY-NOT/constraint_rule** — Q: It bothers me that the plan keeps barely any animals on a mixed farm like this — there's manure, draft, and milk value in a herd. Shouldn't we carry at least 3 head of livestock combined across the herd types? What's the model seeing that makes it run the place almost crop-only? | obj: 19182.493499582833
  - raw: `model = load_model('paklive_lp', models_dictionary) model.livestock_floor = Constraint(     expr=sum(model.xlivestk[h] for h in model.H) >= 3.0 ) desc`
- **WHY-NOT/heuristic** — Q: Half the value on a mixed farm is supposed to come off the dairy and draft animals, but this plan keeps the herd almost empty. Suppose we just commit a planned herd up front — two buffalo cows for milk, a cattle cow, and a bullock pair for tillage — and let the solver settle the cropping around it. Shouldn't a real livestock-and-cropping operation hold a competitive return? What's the model seeing that makes it shy away from the herd? | obj: 19033.23306964077
  - raw: `model = load_model('paklive_lp', models_dictionary) # Heuristic: a fixed dairy-and-draft herd plan set in advance, then solve the # residual cropping.`

### paperco_lp  (8)  — `testing_library/feas_test/paperco_lp.txt`

- **WHAT-IF/new_constraint** — Q: Procurement is rolling out a fiber-source rule for sustainable sourcing — chips have to make up at least 60% of the total wood pulped, so the mill doesn't lean too hard on the ground-wood line. How does that fiber-mix rule reshape the production plan and the operating profit? | obj: 3920.205729013253
  - raw: `model = load_model('paperco_lp', models_dictionary) model.fiber_mix = Constraint(     expr=sum(model.xw['chips', p] for p in model.P) >= 0.60 * sum(mo`
- **WHAT-IF/new_constraint** — Q: There's a proposal to throttle total wood throughput at the digesters to 45 units a cycle while we trial a slower, lower-energy cooking schedule. If we hold combined wood shipments to 45 units, what does the optimizer return for the plan and the profit? | obj: 4547.086082474227
  - raw: `model = load_model('paperco_lp', models_dictionary) model.wood_cap = Constraint(     expr=sum(model.xw[w, p] for w in model.W for p in model.P) <= 45.`
- **WHAT-IF/new_constraint** — Q: We're evaluating a finishing-line capacity limit: kraft and newsprint share the same coater, and the coater can only handle 35 units of the two combined per run. If we bind kraft plus newsprint to 35 units, where does profit land? | obj: 4167.551773195876
  - raw: `model = load_model('paperco_lp', models_dictionary) model.coater_cap = Constraint(     expr=model.paper['kraft'] + model.paper['newsprint'] <= 35.0 )`
- **WHY-NOT/constraint_rule** — Q: The current paper mix tilts to whichever grade has the best margin — kraft is taking the biggest share. Shouldn't no single paper grade carry more than 50% of total paper output, as a portfolio-balance rule? What's keeping the model from picking a more even mix? | obj: 4341.279154639176
  - raw: `model = load_model('paperco_lp', models_dictionary) model.grade_cap = Constraint(     model.Q,     rule=lambda mm, q: mm.paper[q] <= 0.50 * sum(mm.pap`
- **WHY-NOT/constraint_rule** — Q: The current plan only sells pulp-2 on the merchant market and leaves pulp-1 entirely off the spot book. Shouldn't any pulp grade we sell on the spot market move at least 5 units, so the trading desk isn't churning buyer relationships on tiny lots? What's keeping the model from leaning more committed on pulp-1 sales? | obj: 4594.372680412372
  - raw: `model = load_model('paperco_lp', models_dictionary) model.sales_commit = Constraint(     model.P,     rule=lambda mm, p: mm.sales[p] >= 5.0 ) descript`
- **WHY-NOT/constraint_rule** — Q: Printing is our highest-priced grade yet the plan runs barely any of it next to all that kraft. Shouldn't printing run at least a third of whatever kraft runs, so we keep the premium line alive in the mix? What's the model seeing that makes it starve printing like that? | obj: 4249.897463917526
  - raw: `model = load_model('paperco_lp', models_dictionary) model.print_share = Constraint(     expr=model.paper['printing'] >= (1.0 / 3.0) * model.paper['kra`
- **WHY-NOT/constraint_rule** — Q: I don't like that the plan leans on buying pulp in off the spot market — that's supply-chain risk we don't control. Couldn't the mill just supply all its own pulp and buy nothing externally? What's keeping the model from running fully self-sufficient on pulp? | obj: 4590.162371134021
  - raw: `model = load_model('paperco_lp', models_dictionary) model.no_purchase = Constraint(     model.P,     rule=lambda mm, p: mm.purchase[p] <= 0.0 ) descri`
- **WHY-NOT/heuristic** — Q: Kraft is the highest-priced grade we make, so couldn't we just run a margin-tiered contract plan — pin the whole paper book to its tiers in advance: kraft pushed to its contractual ceiling, newsprint and printing held at their contractual floors — and let the solver settle the upstream pulp and wood flows from there? That leans as hard on the best-margin grade as the contracts allow. What's the tradeoff the model is seeing that I'm not? | obj: 3484.1373195876286
  - raw: `model = load_model('paperco_lp', models_dictionary) # Heuristic planning strategy: a margin-tiered contract plan fixed in advance, then solve the resi`

### pdi_lp  (1)  — `testing_library/feas_test/pdi_lp.txt`

- **WHY-NOT/heuristic** — Q: Overtime always feels expensive. Couldn't we just run no overtime at all, anywhere, and keep things simple? What would a no-overtime plan earn? | obj: 280470.0
  - raw: `model = load_model('pdi_lp', models_dictionary) # Heuristic: no overtime production at any facility in any month for p in model.p:     for mo in model`

### pg_mip  (1)  — `testing_library/feas_test/pg_mip.txt`

- **WHY-NOT/heuristic** — Q: All this battery scheduling feels like overkill. Couldn't we just keep it simple and never put the battery into discharge mode in any hour, treating it purely as a charge-only buffer? What would that flat rule cost us? | obj: 2123.5
  - raw: `model = load_model('pg_mip', models_dictionary) # Heuristic: pin the discharge-commitment binary off in every hour (battery never discharges) for t in`

### phosdis_lp  (1)  — `testing_library/feas_test/phosdis_lp.txt`

- **WHY-NOT/heuristic** — Q: Do we really need to optimize a whole branching route tree? Couldn't each source just funnel its entire downstream flow through its single nearest gateway port and let the legs cascade from there? Run that simple one-gateway-per-source rule and tell me what mileage it costs us. | obj: 1006544.0
  - raw: `model = load_model('phosdis_lp', models_dictionary) # Heuristic single-gateway policy: each source must reach all (N-1) other nodes, so push its # ent`

### port_lp  (1)  — `testing_library/feas_test/port_lp.txt`

- **WHY-NOT/heuristic** — Q: Why grind through an optimizer for this? Couldn't we just play it safe and put the whole book into the two lowest-rated government bonds, us-ser-e and us-ser-f, splitting between them in proportion to their after-tax yield? | obj: 0.23595744680851066
  - raw: `model = load_model('port_lp', models_dictionary) # Heuristic risk-averse policy: hold only the two lowest-rated (safest) government bonds, # us-ser-e`

### pp_mip  (1)  — `testing_library/feas_test/pp_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of all this sequencing optimization, what if we just ran a dead-simple rule and processed product E every single week, then let the solver fill in the rest? Pin product E into every week's run and tell me where profit lands. | obj: -1838.066666666662
  - raw: `model = load_model('pp_mip', models_dictionary) for w in model.W:     model.e['E', w].fix(1) new_version = 'pp_mip__heuristic_E_every_week' models_dic`

### process_mip  (1)  — `testing_library/feas_test/process_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of letting the solver hand-pick which columns run, our operators would rather just commit the first column of every separation family — one A/BC, one AB/C, one A/B and one B/C, i.e. pin columns 1, 7, 13 and 19 on — and let it size the flows. How much does running that simple one-per-family rule cost us versus the optimized design? | obj: 131921.682
  - raw: `model = load_model('process_mip', models_dictionary) for j in [1, 7, 13, 19]:     model.y[j].fix(1) new_version = 'process_mip__heuristic_one_per_fami`

### prodmix_lp  (1)  — `testing_library/feas_test/prodmix_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just run a simple margin-per-hour rule? Rank the desks by profit per labor-hour, pour everything into the best one until a shop runs out of hours, and skip the rest. Wouldn't chasing the highest-yield product first already hold a strong profit? | obj: 18000.0
  - raw: `model = load_model('prodmix_lp', models_dictionary) # Heuristic greedy margin-per-labor-hour policy: rank desks by price / total labor hours, # build`

### prodplan_mip  (1)  — `testing_library/feas_test/prodplan_mip.txt`

- **WHY-NOT/heuristic** — Q: The schedulers would honestly rather just run a batch every single period and never carry stock between them — a clean lot-for-lot rule. If we lock the plan to a setup in every period, how much more expensive is it than the optimizer's mixed schedule? | obj: 740000.0
  - raw: `model = load_model('prodplan_mip', models_dictionary) # Heuristic 'lot-for-lot': run a production setup in every period so nothing is # pre-built and`

### prodsch_eb1  (6)  — `testing_library/feas_test/prodsch_eb1.txt`

- **WHAT-IF/new_constraint** — Q: The board is putting workforce-volatility costs under a single line item this year — total firings across all four quarters combined can't exceed 15 employees. Layer that cap into the model and tell me what the new schedule and total cost look like. | obj: 3448.6487
  - raw: `model = load_model('prodsch_eb1', models_dictionary) model.total_firings_cap = Constraint(     expr=sum(model.f[q] for q in model.Q) <= 15.0 ) descrip`
- **WHAT-IF/new_constraint** — Q: Operations is looking at a uniform line-rate ceiling — no quarter would run more than 6300 motors, to keep the floor from over-revving during the summer push. Plug that cap in across all four quarters and tell me what the schedule and total cost come out to. | obj: 3320.8831471876533
  - raw: `model = load_model('prodsch_eb1', models_dictionary) model.line_ceiling = ConstraintList() for q in model.Q:     model.line_ceiling.add(model.p[q] <=`
- **WHY-NOT/constraint_rule** — Q: Every quarter the plan either fires people or carries idle headcount — there's a lot of churn. Shouldn't hires plus firings in any single quarter stay under 10 employees? What's keeping the model from smoothing the workforce that way? | obj: 3390.077
  - raw: `model = load_model('prodsch_eb1', models_dictionary) model.churn_perq = ConstraintList() for q in model.Q:     model.churn_perq.add(model.h[q] + model`
- **WHY-NOT/constraint_rule** — Q: Inventory builds up through the off-season — fall and winter the warehouse is full of motors that just sit there earning rental cost. Shouldn't end-of-quarter inventory stay under 15000 motors in every quarter? What's the model seeing that pulls it the other way? | obj: 3286.532
  - raw: `model = load_model('prodsch_eb1', models_dictionary) model.lean_inv = ConstraintList() for q in model.Q:     model.lean_inv.add(model.inv[q] <= 15000.`
- **WHY-NOT/constraint_rule** — Q: Summer runs hot at 6600 motors while every other quarter sits at 5800 — that uneven push is what drives the extra summer shift. Shouldn't no single quarter top 6100 so the line stays level year-round? What's the model seeing that makes the summer spike worth it? | obj: 3386.996517083477
  - raw: `model = load_model('prodsch_eb1', models_dictionary) model.level_line = ConstraintList() for q in model.Q:     model.level_line.add(model.p[q] <= 6100`
- **WHY-NOT/heuristic** — Q: A workforce-stability approach would just freeze the workforce — no hiring and no firing across any quarter, holding the starting summer headcount through the year. Pin h[q] and f[q] to zero for every quarter and let the rest of the plan adjust. Wouldn't that be cleaner than the hire-fire churn we have now? | obj: 3843.6114
  - raw: `model = load_model('prodsch_eb1', models_dictionary) # Heuristic: zero out every hire and fire (frozen workforce across the year) for q in model.Q:`

### prodsch_eb2  (3)  — `testing_library/feas_test/prodsch_eb2.txt`

- **WHAT-IF/new_constraint** — Q: Procurement is sizing a smaller storage contract and wants to know the impact — suppose end-of-quarter inventory can't exceed 16000 motors in any quarter. Apply that ceiling and tell me what the cyclic schedule and total cost come out to. | obj: 3275.3562824791693
  - raw: `model = load_model('prodsch_eb2', models_dictionary) model.storage_ceiling = ConstraintList() for q in model.Q:     model.storage_ceiling.add(model.in`
- **WHY-NOT/constraint_rule** — Q: We bring on a big batch of people in spring and then shed them again the next cycle — that hire-and-release churn looks expensive. Shouldn't hiring in any single quarter stay under 12 employees? What's keeping the optimizer from spreading the ramp out? | obj: 3321.284792239261
  - raw: `model = load_model('prodsch_eb2', models_dictionary) model.hire_cap = ConstraintList() for q in model.Q:     model.hire_cap.add(model.h[q] <= 12.0) de`
- **WHY-NOT/heuristic** — Q: The current schedule sawtooths production across quarters — wouldn't a level-output policy that runs the line at the same pace every quarter, 6000 motors each, end up cheaper than building inventory up and drawing it down for the spring peak? | obj: 3447.202825380201
  - raw: `model = load_model('prodsch_eb2', models_dictionary) for q in model.Q:     model.p[q].fix(6000.0) description = 'Why-not heuristic: level production a`

### prodsch_mip  (1)  — `testing_library/feas_test/prodsch_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we really need a different output every quarter? A simpler line plan would just hold the rate flat — run exactly 6000 motors every quarter and let inventory absorb the rest. Pin production to 6000 across the board and see how that lands. | obj: 3448.7259023032775
  - raw: `model = load_model('prodsch_mip', models_dictionary) # Heuristic: hold production flat at 6000 motors every quarter for q in model.q:     model.p[q].f`

### prodschx_1B_mip  (5)  — `testing_library/feas_test/prodschx_1B_mip.txt`

- **WHAT-IF/new_constraint** — Q: Facilities has a smaller warehouse on the table that would hold at most 15000 motors at the close of any quarter. We're weighing it — layer that ceiling into the model and tell me the resulting schedule and total cost. | obj: 3286.5320385200002
  - raw: `model = load_model('prodschx_1B_mip', models_dictionary) model.inv_cap = ConstraintList() for q in model.q:     model.inv_cap.add(model.inv[q] <= 1500`
- **WHAT-IF/new_constraint** — Q: Operations is scoping a uniform line-capacity ceiling of 6500 motors a quarter across the plant. Fold that cap into every quarter and tell me the schedule and total cost. | obj: 3320.8522637923074
  - raw: `model = load_model('prodschx_1B_mip', models_dictionary) model.line_cap_6500 = ConstraintList() for q in model.q:     model.line_cap_6500.add(model.p[`
- **WHY-NOT/constraint_rule** — Q: Every quarter the plan is either hiring or firing — fall alone sheds 18 people right after summer staffs up. Shouldn't the combined hiring and firing in any single quarter stay under 8? What's keeping the model from smoothing the workforce out that way? | obj: 3393.5346926873535
  - raw: `model = load_model('prodschx_1B_mip', models_dictionary) model.churn_cap = ConstraintList() for q in model.q:     model.churn_cap.add(model.h[q] + mod`
- **WHY-NOT/constraint_rule** — Q: We let stock balloon toward 18000 motors by winter, and carrying it isn't free. Shouldn't end-of-quarter inventory stay under 14000 the whole way? What's keeping the model from holding less? | obj: 3288.911451573846
  - raw: `model = load_model('prodschx_1B_mip', models_dictionary) model.stock_cap_14000 = ConstraintList() for q in model.q:     model.stock_cap_14000.add(mode`
- **WHY-NOT/heuristic** — Q: The line keeps shuffling between production tiers quarter to quarter — summer gets pushed up to a higher setting while the rest sit lower. That's a lot of reconfiguring on the floor. Couldn't we just run every shift at the standard level-2 setting all year and leave it there? Wouldn't that single steady setting come out at least as cheap as all the tier-switching? | obj: 3576.2085610799995
  - raw: `model = load_model('prodschx_1B_mip', models_dictionary) for q in model.q:     for s in model.s:         model.ss[q, s, 2].fix(1) description = 'Why-n`

### prodschx_1S1_mip  (4)  — `testing_library/feas_test/prodschx_1S1_mip.txt`

- **WHAT-IF/new_constraint** — Q: Facilities is weighing a smaller warehouse that would hold at most 15000 motors at the close of any quarter. We're evaluating it — fold that ceiling into the model and tell me the resulting schedule and total cost. | obj: 3456.8936182979996
  - raw: `model = load_model('prodschx_1S1_mip', models_dictionary) model.inv_cap = ConstraintList() for q in model.q:     model.inv_cap.add(model.inv[q] <= 150`
- **WHY-NOT/constraint_rule** — Q: Summer alone sheds more than ten people right as the plan kicks off, then headcount just sits flat the rest of the year. Shouldn't the combined hiring and firing in any single quarter stay under 8 so we're not whipsawing the floor? What's keeping the model from spreading that adjustment out? | obj: 3444.4101138378664
  - raw: `model = load_model('prodschx_1S1_mip', models_dictionary) model.churn_cap = ConstraintList() for q in model.q:     model.churn_cap.add(model.h[q] + mo`
- **WHY-NOT/constraint_rule** — Q: We stockpile all the way to 18000 motors by winter and pay to lease the space for it. Shouldn't end-of-quarter inventory stay under 14000? What's keeping the model from carrying less? | obj: 3463.4128227813326
  - raw: `model = load_model('prodschx_1S1_mip', models_dictionary) model.stock_cap_14000 = ConstraintList() for q in model.q:     model.stock_cap_14000.add(mod`
- **WHY-NOT/heuristic** — Q: To hit each shift's motor target the schedule splits the run between the bottom and the top production tiers — that constant juggling is a headache on the floor. Couldn't we just lock every shift to the standard level-2 setting, the one that already matches the output we need, instead of mixing tiers? Wouldn't that simpler single-setting plan come out at least as cheap? | obj: 3576.2085610799995
  - raw: `model = load_model('prodschx_1S1_mip', models_dictionary) for q in model.q:     for s in model.s:         model.ss[q, s, 2].fix(1) description = 'Why-`

### prodschx_1S2_mip  (5)  — `testing_library/feas_test/prodschx_1S2_mip.txt`

- **WHAT-IF/new_constraint** — Q: Facilities floated a smaller warehouse that would hold at most 15000 motors at the close of any quarter. We're weighing it — work that ceiling into the model and tell me the resulting schedule and total cost. | obj: 3268.8767604199998
  - raw: `model = load_model('prodschx_1S2_mip', models_dictionary) model.inv_cap = ConstraintList() for q in model.q:     model.inv_cap.add(model.inv[q] <= 150`
- **WHAT-IF/new_constraint** — Q: Operations is scoping a uniform line-capacity ceiling of 6500 motors a quarter. Fold that cap into every quarter and tell me the schedule and total cost. | obj: 3318.07150677
  - raw: `model = load_model('prodschx_1S2_mip', models_dictionary) model.line_cap_6500 = ConstraintList() for q in model.q:     model.line_cap_6500.add(model.p`
- **WHY-NOT/constraint_rule** — Q: We staff up for summer's double shift and then shed more than 18 people in fall the moment the second shift stands down. Shouldn't the combined hiring and firing in any single quarter stay under 8 instead of that big swing? What's keeping the model from smoothing the workforce out? | obj: 3386.494407479833
  - raw: `model = load_model('prodschx_1S2_mip', models_dictionary) model.churn_cap = ConstraintList() for q in model.q:     model.churn_cap.add(model.h[q] + mo`
- **WHY-NOT/constraint_rule** — Q: Stock climbs toward 18000 motors by winter and the lease isn't cheap. Shouldn't end-of-quarter inventory stay under 14000 the whole way? What's keeping the model from holding less? | obj: 3275.3959649033327
  - raw: `model = load_model('prodschx_1S2_mip', models_dictionary) model.stock_cap_14000 = ConstraintList() for q in model.q:     model.stock_cap_14000.add(mod`
- **WHY-NOT/heuristic** — Q: To hit each shift's motor target the schedule splits the run between the bottom and the top production tiers — that constant juggling is a headache on the floor. Couldn't we just lock every shift to the standard level-2 setting, the one that already matches the output we need, instead of mixing tiers? Wouldn't that simpler single-setting plan come out at least as cheap? | obj: 3576.2085610799995
  - raw: `model = load_model('prodschx_1S2_mip', models_dictionary) for q in model.q:     for s in model.s:         model.ss[q, s, 2].fix(1) description = 'Why-`

### prodschx_2B_mip  (6)  — `testing_library/feas_test/prodschx_2B_mip.txt`

- **WHAT-IF/new_constraint** — Q: Facilities floated a smaller warehouse that would hold at most 13000 motors at the close of any quarter. We're weighing it — work that ceiling into the model and tell me the resulting schedule and total cost. | obj: 3305.4650840252307
  - raw: `model = load_model('prodschx_2B_mip', models_dictionary) model.inv_cap = ConstraintList() for q in model.q:     model.inv_cap.add(model.inv[q] <= 1300`
- **WHAT-IF/new_constraint** — Q: Operations is scoping a uniform line-capacity ceiling of 6500 motors a quarter. Fold that into every quarter and tell me the schedule and total cost. | obj: 3367.7183883264615
  - raw: `model = load_model('prodschx_2B_mip', models_dictionary) model.line_cap_6500 = ConstraintList() for q in model.q:     model.line_cap_6500.add(model.p[`
- **WHAT-IF/new_constraint** — Q: Supply chain is proposing a changeover policy that limits how fast we ramp — production couldn't rise by more than 500 motors from one quarter to the next. Evaluate that and tell me the resulting plan and cost. | obj: 3323.8084275919996
  - raw: `model = load_model('prodschx_2B_mip', models_dictionary) model.ramp_cap_500 = ConstraintList() qlist = list(model.q) for i in range(1, len(qlist)):`
- **WHY-NOT/constraint_rule** — Q: We bring nearly 60 people on in a single summer quarter just to stand the line up — that's a brutal one-shot hire. Shouldn't the combined hiring and firing in any single quarter stay under 30 so we phase the crew in more gradually? What's keeping the model from ramping up that way? | obj: 3372.759346022869
  - raw: `model = load_model('prodschx_2B_mip', models_dictionary) model.churn_cap = ConstraintList() for q in model.q:     model.churn_cap.add(model.h[q] + mod`
- **WHY-NOT/constraint_rule** — Q: Output drifts up to 6800 in spring and leans on the second shift right at the deadline. Shouldn't no single quarter run above 6000 so the load sits evenly on one shift? What's keeping the model from leveling it out? | obj: 3513.6643648326153
  - raw: `model = load_model('prodschx_2B_mip', models_dictionary) model.level_cap_6000 = ConstraintList() for q in model.q:     model.level_cap_6000.add(model.`
- **WHY-NOT/heuristic** — Q: To hit each shift's motor target the schedule splits the run between the bottom and the top production tiers — that constant juggling is a headache on the floor. Couldn't we just lock every shift to the standard level-2 setting, the one that already matches the output we need, instead of mixing tiers? Wouldn't that simpler single-setting plan come out at least as cheap? | obj: 3647.6085610799996
  - raw: `model = load_model('prodschx_2B_mip', models_dictionary) for q in model.q:     for s in model.s:         model.ss[q, s, 2].fix(1) description = 'Why-n`

### prodschx_2S1_mip  (4)  — `testing_library/feas_test/prodschx_2S1_mip.txt`

- **WHAT-IF/new_constraint** — Q: Facilities floated a smaller warehouse that would hold at most 13000 motors at the close of any quarter. We're weighing it — work that ceiling into the model and tell me the resulting schedule and total cost. | obj: 3504.8116789036662
  - raw: `model = load_model('prodschx_2S1_mip', models_dictionary) model.inv_cap = ConstraintList() for q in model.q:     model.inv_cap.add(model.inv[q] <= 130`
- **WHAT-IF/new_constraint** — Q: Supply chain is proposing a changeover policy limiting how fast we ramp — production couldn't rise more than 500 motors quarter to quarter. Evaluate it and tell me the resulting plan and cost. | obj: 3502.179460986333
  - raw: `model = load_model('prodschx_2S1_mip', models_dictionary) model.ramp_cap_500 = ConstraintList() qlist = list(model.q) for i in range(1, len(qlist)):`
- **WHY-NOT/constraint_rule** — Q: Output swings from a crawl of 2000 motors in summer up to 7600 by winter — that's a steep ramp to run on the floor. Shouldn't no single quarter run above 6000 so the load is spread more evenly? What's keeping the model from leveling production out? | obj: 3506.3309598346664
  - raw: `model = load_model('prodschx_2S1_mip', models_dictionary) model.level_cap = ConstraintList() for q in model.q:     model.level_cap.add(model.p[q] <= 6`
- **WHY-NOT/heuristic** — Q: To hit each shift's motor target the schedule splits the run between the bottom and the top production tiers — that constant juggling is a headache on the floor. Couldn't we just lock every shift to the standard level-2 setting, the one that already matches the output we need, instead of mixing tiers? Wouldn't that simpler single-setting plan come out at least as cheap? | obj: 3647.6085610799996
  - raw: `model = load_model('prodschx_2S1_mip', models_dictionary) for q in model.q:     for s in model.s:         model.ss[q, s, 2].fix(1) description = 'Why-`

### prodschx_2S2_mip  (5)  — `testing_library/feas_test/prodschx_2S2_mip.txt`

- **WHAT-IF/new_constraint** — Q: Facilities floated a smaller warehouse that would hold at most 13000 motors at the close of any quarter. We're weighing it — work that ceiling into the model and tell me the resulting schedule and total cost. | obj: 3304.7744726646665
  - raw: `model = load_model('prodschx_2S2_mip', models_dictionary) model.inv_cap = ConstraintList() for q in model.q:     model.inv_cap.add(model.inv[q] <= 130`
- **WHY-NOT/constraint_rule** — Q: We bring nearly 60 people on in a single summer quarter just to stand the line up — that's a brutal one-shot hire. Shouldn't the combined hiring and firing in any single quarter stay under 30 so we phase the crew in more gradually? What's keeping the model from ramping up that way? | obj: 3358.4805542219997
  - raw: `model = load_model('prodschx_2S2_mip', models_dictionary) model.churn_cap = ConstraintList() for q in model.q:     model.churn_cap.add(model.h[q] + mo`
- **WHY-NOT/constraint_rule** — Q: Output drifts from 5600 up to 6800 across the year and leans on the spring double shift. Shouldn't no single quarter run above 6000 so the load sits evenly on one shift all year? What's keeping the model from leveling it out? | obj: 3506.3309598346664
  - raw: `model = load_model('prodschx_2S2_mip', models_dictionary) model.level_cap = ConstraintList() for q in model.q:     model.level_cap.add(model.p[q] <= 6`
- **WHY-NOT/constraint_rule** — Q: Production sits flat through winter and then jumps a thousand units into spring all at once — that abrupt step is hard on the floor and the supply chain. Shouldn't quarter-to-quarter output move by no more than 500 so the ramp is gradual? What's pushing the model to spike it at the end? | obj: 3323.2256543781664
  - raw: `model = load_model('prodschx_2S2_mip', models_dictionary) model.ramp_cap = ConstraintList() qlist = list(model.q) for i in range(1, len(qlist)):     m`
- **WHY-NOT/heuristic** — Q: To hit each shift's motor target the schedule splits the run between the bottom and the top production tiers — that constant juggling is a headache on the floor. Couldn't we just lock every shift to the standard level-2 setting, the one that already matches the output we need, instead of mixing tiers? Wouldn't that simpler single-setting plan come out at least as cheap? | obj: 3647.6085610799996
  - raw: `model = load_model('prodschx_2S2_mip', models_dictionary) for q in model.q:     for s in model.s:         model.ss[q, s, 2].fix(1) description = 'Why-`

### prodsp_lp  (4)  — `testing_library/feas_test/prodsp_lp.txt`

- **WHAT-IF/new_constraint** — Q: Operations is floating a diversification rule for the catalog — no single product class should account for more than 60% of total production volume, so we're not over-concentrated on one SKU. Plug that in and walk me through the new production mix and expected profit. | obj: 16564.330219639625
  - raw: `model = load_model('prodsp_lp', models_dictionary) model.class_cap = Constraint(     model.i,     rule=lambda m, i: m.x[i] <= 0.60 * sum(m.x[k] for k`
- **WHY-NOT/constraint_rule** — Q: Most of the catalog is sitting at zero in the plan — only class-1 and class-4 actually show up. Shouldn't every product class carry at least 5% of total production so we don't gut the rest of the catalog mid-quarter? What's the model trading off against keeping every class on the line? | obj: 17014.307914232915
  - raw: `model = load_model('prodsp_lp', models_dictionary) model.class_floor = Constraint(     model.i,     rule=lambda m, i: m.x[i] >= 0.05 * sum(m.x[k] for`
- **WHY-NOT/constraint_rule** — Q: The mid-tier (class-2 and class-3) shows up at zero volume in the plan, but those grades have committed buyers we can't just drop. Shouldn't combined class-2 plus class-3 production stay at or above 200 units to honor the standing orders? What's keeping the model from supporting that floor? | obj: 17250.736245066902
  - raw: `model = load_model('prodsp_lp', models_dictionary) model.midtier_floor = Constraint(     expr=model.x['class-2'] + model.x['class-3'] >= 200, ) descri`
- **WHY-NOT/heuristic** — Q: Running four grades through these workstations means constant setup churn. Couldn't we just rank the catalog by unit margin and commit the lines to the top two earners — class-4 at $40 and class-2 at $20 — and shelve the two thin grades, class-1 and class-3, then let the solver settle the exact volumes? Wouldn't that lean margin-first plan hold up against the spread-everything-thin mix? | obj: 13974.863182723007
  - raw: `model = load_model('prodsp_lp', models_dictionary) # Margin-priority heuristic: rank the catalog by unit margin (class-4=40, class-2=20, # class-3=18,`

### qp5_lp  (1)  — `testing_library/feas_test/qp5_lp.txt`

- **WHY-NOT/heuristic** — Q: Why grind through the optimization at all? Couldn't we just weight each stock in proportion to its mean return — load up on the higher-return names and skip the negative ones — and call it a day? | obj: 13.129345878584656
  - raw: `model = load_model('qp5_lp', models_dictionary) # Heuristic: weight each stock in proportion to its (non-negative) mean return, # normalized so the we`

### queens_mip  (2)  — `testing_library/feas_test/queens_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we even need to optimize this? I've got a textbook eight-queens layout memorized — columns 1, 5, 8, 6, 3, 7, 2, 4 reading down the rows. Just drop that in and confirm it actually holds up. | obj: 8.0
  - raw: `model = load_model('queens_mip', models_dictionary) # Heuristic: lay down a known valid eight-queens placement (row -> column) cols = {'1': '1', '2':`
- **WHY-NOT/heuristic** — Q: Here's another off-the-shelf layout a friend swears by — columns 2, 4, 6, 8, 3, 1, 7, 5 down the rows. Slot that in and tell me whether it's a legal full board. | obj: 8.0
  - raw: `model = load_model('queens_mip', models_dictionary) # Heuristic: a second known valid eight-queens placement (row -> column) cols = {'1': '2', '2': '4`

### railcirc_mip  (1)  — `testing_library/feas_test/railcirc_mip.txt`

- **WHY-NOT/heuristic** — Q: Our depot dispatchers like a dead-simple flexibility rule: keep at least two of the small tu1 units stabled overnight at every depot, no matter what, so each yard has a couple of nimble units ready in the morning. If we lock the plan to that rule, how much more does the overnight stabling cost than the optimizer's leaner mix? | obj: 81.0
  - raw: `model = load_model('railcirc_mip', models_dictionary) # Heuristic 'two-tu1-per-depot flex reserve': insist on at least two small tu1 units stabled # o`

### rcpsp_mip  (9)  — `testing_library/feas_test/rcpsp_mip.txt`

- **WHAT-IF/new_constraint** — Q: We're sketching out a milestone where activity j2 has to be wrapped up early in the cycle. Say we require j2 to finish no later than period t11 — what makespan does the optimizer settle on then? | obj: 49.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) <= 11] model.j2_by_t11 = Constraint(expr=sum(model.x['j`
- **WHAT-IF/new_constraint** — Q: Activity j6 is a long one and it currently finishes deep into the schedule. Out of curiosity, if we insisted j6 be completed by period t36, where does the total project duration land? | obj: 49.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) <= 36] model.j6_by_t36 = Constraint(expr=sum(model.x['j`
- **WHAT-IF/new_constraint** — Q: Suppose a permit holds up activity j16 so it can't possibly finish before period t26. We'd like to see what the optimizer returns for the makespan under that delay. | obj: 45.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) >= 26] model.j16_from_t26 = Constraint(expr=sum(model.x`
- **WHAT-IF/new_constraint** — Q: There's a scenario where activity j11 needs to clear an inspection window early — finished by period t20. What does the resulting end-to-end duration come out to? | obj: 49.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) <= 20] model.j11_by_t20 = Constraint(expr=sum(model.x['`
- **WHY-NOT/constraint_rule** — Q: Activity j17 is sitting late in the plan and it gates a few downstream tasks. Couldn't we just push it to wrap up a notch earlier, say finished by period t29? What's the model seeing that makes pulling j17 forward a bad trade? | obj: 48.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) <= 29] model.j17_by_t29 = Constraint(expr=sum(model.x['`
- **WHY-NOT/constraint_rule** — Q: Activity j27 has a heavy r4 draw and it lingers in the plan. Shouldn't the optimizer be getting it out of the way sooner — finished by period t22 at the latest? What's pulling it back? | obj: 46.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) <= 22] model.j27_by_t22 = Constraint(expr=sum(model.x['`
- **WHY-NOT/constraint_rule** — Q: I'd have expected activity j27 to be held until the r4 crew is free, not crammed in early. If we deliberately keep j27 from finishing before period t26, the plan should be fine, right? What's the makespan cost the model is dodging by starting it sooner? | obj: 45.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) >= 26] model.j27_from_t26 = Constraint(expr=sum(model.x`
- **WHY-NOT/constraint_rule** — Q: Activity j28 finishes pretty early relative to its successors, which feels like wasted slack. Wouldn't it be cleaner to let j28 drift to finish no sooner than period t41 and free the resources up front? What's the model trading away if we do that? | obj: 45.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) allowed = [t for t in model.t if int(t[1:]) >= 41] model.j28_from_t41 = Constraint(expr=sum(model.x`
- **WHY-NOT/heuristic** — Q: Our planners don't trust the black-box schedule — they'd rather run the textbook serial rule: take the activities in their listed order and drop each one in at the earliest period where its predecessors are done and no resource is over its per-period cap. If we lock the project to that hand-built schedule, how much longer does the project run than the optimizer's plan? | obj: 49.0
  - raw: `model = load_model('rcpsp_mip', models_dictionary) import pyomo.environ as pe jobs = list(model.j) periods = list(model.t) dur = {j: int(round(pe.valu`

### rdata_mip  (2)  — `testing_library/feas_test/rdata_mip.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over which unions to involve? Labor relations would rather we just sign agreements with all five up front and be done with it. How many unions does that blanket approach saddle us with? | obj: 5.0
  - raw: `model = load_model('rdata_mip', models_dictionary) # Heuristic: sign all five unions for u in model.union:     model.up[u].fix(1) description = 'Why-n`
- **WHY-NOT/heuristic** — Q: Here's a simple rule of thumb the labor team likes: keep the three core unions and add the Machinists to cover the heavy-fab plants, ignore the rest. How does that fixed lineup stack up on the union count? | obj: 4.0
  - raw: `model = load_model('rdata_mip', models_dictionary) # Heuristic: core three (IBT, UAW, USA) plus IAM, drop IBEW on = {'ibt', 'uaw', 'usa', 'iam'} for u`

### recovery_mip  (1)  — `testing_library/feas_test/recovery_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of agonizing over which collection sites to commit to, couldn't we just stand up all five collection/inspection centers and keep our options open? What would that all-in approach actually cost? | obj: 16451445.915920231
  - raw: `model = load_model('recovery_mip', models_dictionary) # Heuristic: open every collection/inspection center for i in range(5):     model.Y[i].fix(1) de`

### relief_mip  (1)  — `testing_library/feas_test/relief_mip.txt`

- **WHY-NOT/heuristic** — Q: Our dispatchers like a dead-simple siting rule: figure out the single best cell to put one drop if everybody had to use it, then the second-best such cell, and just open drops on those two. If we lock the two drops to that pair, how much worse is the total walk than the optimizer's mixed plan? | obj: 67.8407012891
  - raw: `model = load_model('relief_mip', models_dictionary) # Heuristic 'two best standalone hubs': for every grid cell total the distance if ALL huts # walke`

### ridesharing_miqcp  (1)  — `testing_library/feas_test/ridesharing_miqcp.txt`

- **WHY-NOT/heuristic** — Q: Honestly, do we even need the matching solver? Just run every single ride on path C and let it sort out who serves whom — pin every trip to path C across the board. How much does that one-lane plan cost us on the total? | obj: 64.0
  - raw: `model = load_model('ridesharing_miqcp', models_dictionary) # Heuristic: every ride on path C -- pin paths A and B off for all eligible trips for r in`

### robert_lp  (6)  — `testing_library/feas_test/robert_lp.txt`

- **WHAT-IF/new_constraint** — Q: Operations is floating a smoothing rule for the production schedule — each short-horizon period should carry at least 25% of total short-horizon volume, so the line doesn't go cold mid-quarter. How does that smoothing rule reshape the schedule and total profit? | obj: 10915.0
  - raw: `model = load_model('robert_lp', models_dictionary) model.smoothing = Constraint(     model.t,     rule=lambda m, t: sum(m.x[p, t] for p in m.p)`
- **WHAT-IF/new_constraint** — Q: There's a proposal to keep the line warm — run at least 15 units of total output in every short-horizon period rather than letting it idle until the end. Plug that minimum-run rule in and tell me where profit lands. | obj: 10942.5
  - raw: `model = load_model('robert_lp', models_dictionary) model.min_run = Constraint(     model.t,     rule=lambda m, t: sum(m.x[p, t] for p in m.p) >= 15, )`
- **WHY-NOT/constraint_rule** — Q: The plan runs the raw-material cribs down to 30%-50% of their max by the end of the horizon. Shouldn't we hold every crib at no less than 75% of its max-stock level across the whole horizon so we never get caught short for a rush order? What's the model trading off against that buffer rule? | obj: 10854.166667
  - raw: `model = load_model('robert_lp', models_dictionary) model.stock_floor = Constraint(     model.r, model.tt,     rule=lambda m, r, t: m.s[r, t] >= 0.75 *`
- **WHY-NOT/constraint_rule** — Q: The line sits idle for most of the quarter and then dumps everything into the final period. Shouldn't every short-horizon period pull its weight — say each one carrying at least 20% of total volume? What's keeping the model from leveling the run out like that? | obj: 10951.666667
  - raw: `model = load_model('robert_lp', models_dictionary) model.period_balance = Constraint(     model.t,     rule=lambda m, t: sum(m.x[p, t] for p in m.p)`
- **WHY-NOT/constraint_rule** — Q: The mix is tilted entirely toward the high grade — medium never gets a look despite having buyers on contract. Shouldn't medium carry at least 30% of total horizon volume so we don't hollow out that part of the catalog? What's the trade the model is making against keeping medium in the rotation? | obj: 10625.0
  - raw: `model = load_model('robert_lp', models_dictionary) model.medium_floor = Constraint(     expr=sum(model.x['medium', t] for t in model.t)          >= 0.`
- **WHY-NOT/heuristic** — Q: Slamming the whole run into the final period strands the line cold for two periods and back-loads all the risk. Wouldn't a gentle ramp on the high grade — 10 units in the first short period, 20 in the second, 30 in the third, nothing held for the residual slot — run smoother and still hold a competitive profit? What's the model trading away by waiting until the end? | obj: 10835.0
  - raw: `model = load_model('robert_lp', models_dictionary) # Heuristic: a fixed ramp-up operating rule set in advance, then solve the residual. # Ease the hig`

### rotdk_mip  (1)  — `testing_library/feas_test/rotdk_mip.txt`

- **WHY-NOT/heuristic** — Q: A simple capacity rule: just slap 2 units of the biggest component into every single period and stop optimizing the timing. How much does that overbuild cost us versus the model's plan? | obj: 2182.773410829267
  - raw: `model = load_model('rotdk_mip', models_dictionary) # Heuristic 'biggest-every-period': install 2 units of the largest-capacity component # in every pe`

### sarf_lp  (2)  — `testing_library/feas_test/sarf_lp.txt`

- **WHY-NOT/constraint_rule** — Q: I'd expect a more diversified plan — no single crop should grab more than 800 hectares of the farm. Couldn't we require that across the board and still pull a comparable profit? What's keeping the model from spreading the land out? | obj: 134545.81525307408
  - raw: `model = load_model('sarf_lp', models_dictionary) model.diversify = ConstraintList() for c in model.c:     model.diversify.add(sum(model.xcrop[c, s] fo`
- **WHY-NOT/heuristic** — Q: Why not just commit the farm up front to a balanced staple block — 800 hectares each of wheat, cotton, and sugar-beet on schedule 8 — and let soy-beans and the rest fill in around it? Wouldn't that simple dedication plan come out close to the optimized mix? | obj: 182784.1362849095
  - raw: `model = load_model('sarf_lp', models_dictionary) # Heuristic: dedicate a balanced staple block of 800 ha each on schedule 8, # then let the optimizer`

### sddp_lp  (1)  — `testing_library/feas_test/sddp_lp.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the dispatch hour by hour? Couldn't we just run both thermal units — coal and nuclear — flat out at their weekly capacity every hour and let the dam and the gap balance the rest? | obj: 10446859060.935265
  - raw: `model = load_model('sddp_lp', models_dictionary) # Heuristic merit-blind policy: pin coal and nuclear to their full weekly capacity # every hour (comp`

### senstran_lp  (6)  — `testing_library/feas_test/senstran_lp.txt`

- **WHAT-IF/new_constraint** — Q: Operations is floating a diversification rule for the lane mix — they want each plant's outbound to spread out so no single market draws more than 50% of any plant's volume. Plug that in and tell me what the cost lands at and how shipments rebalance. | obj: 164.97
  - raw: `model = load_model('senstran_lp', models_dictionary) model.diversification = Constraint(     model.i, model.j,     rule=lambda m, i, j: m.x[i, j] <= 0`
- **WHY-NOT/constraint_rule** — Q: San Diego is hauling a huge load all the way to New York — that's the longest lane on the board. Shouldn't we cap that long-haul at 100 cases to keep transit risk under control? What's keeping the model from pulling that back? | obj: 165.645
  - raw: `model = load_model('senstran_lp', models_dictionary) model.long_haul_cap = Constraint(     expr=model.x['san-diego', 'new-york'] <= 100, ) description`
- **WHY-NOT/constraint_rule** — Q: Two of the six origin-destination lanes get zero shipments in the current plan — that hollows out our distribution network and leaves us exposed if any lane needs to flex. Shouldn't every plant-market pair carry at least 50 cases so we have full network coverage? What's the model trading off against that? | obj: 164.43
  - raw: `model = load_model('senstran_lp', models_dictionary) model.coverage_floor = Constraint(     model.i, model.j,     rule=lambda m, i, j: m.x[i, j] >= 50`
- **WHY-NOT/constraint_rule** — Q: Seattle barely touches the New York market right now, which leaves that big account single-sourced out of San Diego. Couldn't Seattle pick up at least 150 of New York's cases so we're not so exposed on one plant? What's the model weighing against that? | obj: 164.97
  - raw: `model = load_model('senstran_lp', models_dictionary) model.seattle_ny_floor = Constraint(     expr=model.x['seattle', 'new-york'] >= 150, ) descriptio`
- **WHY-NOT/constraint_rule** — Q: San Diego is supplying a lopsided share of several markets on its own. Shouldn't we keep San Diego under 70% of any single market's demand so no one market leans entirely on that one plant? What's the model trading off to lean on it so hard? | obj: 165.0915
  - raw: `model = load_model('senstran_lp', models_dictionary) model.sd_market_share = Constraint(     model.j,     rule=lambda m, j: m.x['san-diego', j] <= 0.7`
- **WHY-NOT/heuristic** — Q: All this cross-shipping makes the lanes hard to manage. Wouldn't a clean single-source plan run smoother — dedicate Seattle to Chicago, and have San Diego carry both New York and Topeka — and just let the solver settle the exact tonnages from there? Shouldn't that tidy regional split still come in close on transportation cost? | obj: 164.07
  - raw: `model = load_model('senstran_lp', models_dictionary) # Heuristic: a fixed single-source assignment plan set in advance, then solve the residual. # sea`

### shale_lp  (1)  — `testing_library/feas_test/shale_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over which shale grade to retort? Couldn't we just spread retorting evenly across the three grades each period — run the same level of 25-, 30-, and 35-gallon retorting — and call it a balanced resource plan? | obj: 7928.155207506433
  - raw: `model = load_model('shale_lp', models_dictionary) # Heuristic balanced-grade policy: in every period run the 25- and 30-gallon # retorts at the same l`

### solmpool_mip  (2)  — `testing_library/feas_test/solmpool_mip.txt`

- **WHY-NOT/heuristic** — Q: Warehouse 4 alone has the room to cover all nine regions. Couldn't we keep things dead simple and run everything out of w4? Surely a single-site setup comes out no worse than juggling two warehouses? | obj: 535.0
  - raw: `model = load_model('solmpool_mip', models_dictionary) # Heuristic: serve every region from warehouse 4 only for i in model.i:     for j in model.j:`
- **WHY-NOT/heuristic** — Q: Why run a full optimization at all — couldn't we just hand each region to whichever warehouse is cheapest to ship from and be done? Wouldn't that nearest-warehouse rule be good enough? | obj: 799.0
  - raw: `model = load_model('solmpool_mip', models_dictionary) # Heuristic: assign each region to its lowest-freight warehouse near = {'r1': 'w1', 'r2': 'w1',`

### solnpool_mip  (2)  — `testing_library/feas_test/solnpool_mip.txt`

- **WHY-NOT/heuristic** — Q: Warehouse 4 on its own has enough capacity to cover our entire demand. Couldn't we keep operations dead simple and just run everything out of w4? Wouldn't that one-site setup come out at least as cheap as juggling multiple warehouses? | obj: 535.0
  - raw: `model = load_model('solnpool_mip', models_dictionary) # Heuristic: serve every region from warehouse 4 only for i in model.i:     for j in model.j:`
- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole network — couldn't we just assign each region to whichever warehouse is cheapest to ship from and call it a day? Wouldn't that nearest-warehouse rule be good enough? | obj: 799.0
  - raw: `model = load_model('solnpool_mip', models_dictionary) # Heuristic: assign each region to its lowest-freight warehouse near = {'r1': 'w1', 'r2': 'w1',`

### sparta_lp  (1)  — `testing_library/feas_test/sparta_lp.txt`

- **WHY-NOT/heuristic** — Q: Four-year commitments always feel like a gamble on future needs. Couldn't we just run the whole program on shorter terms — no 4-year enlistments at all? What would that cost? | obj: 3963.8
  - raw: `model = load_model('sparta_lp', models_dictionary) # Heuristic: no four-year enlistments in any year for i in model.t:     model.x[i, 4].fix(0) descri`

### spbenders1_lp  (1)  — `testing_library/feas_test/spbenders1_lp.txt`

- **WHY-NOT/heuristic** — Q: Why over-think the routing? Couldn't we just run every factory flat out at capacity and split each one's output across the distribution centers in proportion to expected demand? Wouldn't that simple full-throttle rule hold a competitive profit? | obj: 8777.19984
  - raw: `model = load_model('spbenders1_lp', models_dictionary) # Heuristic full-capacity policy: run every factory at capacity and split its output # across t`

### spbenders2_lp  (1)  — `testing_library/feas_test/spbenders2_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we keep it simple — just grow enough to cover expected demand at each depot and split each depot's supply across the farms in proportion to farm size? Wouldn't that demand-matching rule hold a competitive profit? | obj: 9102.18672
  - raw: `model = load_model('spbenders2_lp', models_dictionary) # Heuristic demand-matching policy: serve each depot's expected (probability-weighted) # demand`

### spbenders3_lp  (6)  — `testing_library/feas_test/spbenders3_lp.txt`

- **WHAT-IF/new_constraint** — Q: Operations is floating a diversification rule for the factory network so no single site dominates the supply chain — they want each factory's production capped at 35% of total network output. Plug that in and walk me through what the plan looks like. | obj: 10792.314286
  - raw: `model = load_model('spbenders3_lp', models_dictionary) model.diversification = Constraint(     model.I,     rule=lambda m, i: m.product[i] <= 0.35 * s`
- **WHY-NOT/constraint_rule** — Q: Looking at the plan, f3 is sitting nearly 30% below its capacity while the other two plants are pinned at 100%. Shouldn't every factory be required to run at least 80% of its rated capacity to keep the unit economics reasonable across the network? What's keeping the model from making that move? | obj: 10775.6
  - raw: `model = load_model('spbenders3_lp', models_dictionary) model.min_utilization = Constraint(     model.I,     rule=lambda m, i: m.product[i] >= 0.80 * m`
- **WHY-NOT/constraint_rule** — Q: Distribution centers d2 and d5 are routinely under-served versus their base demand book. Shouldn't every market receive at least 90% of its base demand so we're not chronically failing on service levels? What's the tradeoff the model is making against that? | obj: 10748.86
  - raw: `model = load_model('spbenders3_lp', models_dictionary) demand_base = {'d1': 160.0, 'd2': 120.0, 'd3': 270.0, 'd4': 325.0, 'd5': 700.0} model.service_f`
- **WHY-NOT/constraint_rule** — Q: The whole network is leaning on two plants while f3 idles — that concentration makes me nervous. Shouldn't we cap any single factory at roughly a third of total output so no one site carries the plant? What's keeping the model from spreading production out like that? | obj: 10735.4375
  - raw: `model = load_model('spbenders3_lp', models_dictionary) model.balance_share = Constraint(     model.I,     rule=lambda m, i: m.product[i] <= 0.34 * sum`
- **WHY-NOT/constraint_rule** — Q: A few fat lanes are doing almost all the work in this plan and that worries me operationally — one disruption and we're exposed. Couldn't we cap every factory-to-DC lane at 250 units so the flow is spread across more routes? What's the model seeing that makes it pile so much onto a handful of lanes? | obj: 10020.4
  - raw: `model = load_model('spbenders3_lp', models_dictionary) model.lane_cap = Constraint(     model.I, model.J,     rule=lambda m, i, j: m.ship[i, j] <= 250`
- **WHY-NOT/heuristic** — Q: Each distribution center has a clearly cheapest factory by transport cost — d1 through d4 are cheapest out of f2, and d5 is cheapest out of f1. Wouldn't routing each DC exclusively from its single lowest-cost factory and idling f3 entirely give us a comparable expected profit? | obj: 7695.5
  - raw: `model = load_model('spbenders3_lp', models_dictionary) # Lowest-cost routing heuristic: pin each DC to its single cheapest factory, # idle f3 entirely`

### spbenders4_lp  (1)  — `testing_library/feas_test/spbenders4_lp.txt`

- **WHY-NOT/heuristic** — Q: Why optimize the routing at all? Couldn't each plant just run flat out and ship its entire output to whichever single clinic is cheapest to reach? Wouldn't that dead-simple nearest-clinic rule hold a competitive profit? | obj: -6072.0
  - raw: `model = load_model('spbenders4_lp', models_dictionary) # Heuristic nearest-clinic rule: each plant runs at full capacity and ships everything # to the`

### spbenders5_lp  (1)  — `testing_library/feas_test/spbenders5_lp.txt`

- **WHY-NOT/heuristic** — Q: Why fuss over the delivery split? Couldn't each press just run flat out and spread its copies evenly across all five newsstands? Wouldn't that simple equal-split rule hold a competitive profit? | obj: -773.0
  - raw: `model = load_model('spbenders5_lp', models_dictionary) # Heuristic equal-split policy: each press runs at full capacity and divides its copies # evenl`

### srkandw_lp  (1)  — `testing_library/feas_test/srkandw_lp.txt`

- **WHY-NOT/heuristic** — Q: Why not just stock up front? Fill the whole silo in the first run with our best-yielding ingredient and buy nothing in the second run — one big early purchase, then ride it out. Wouldn't front-loading the workhorse ingredient like that hold a competitive cost? | obj: 4401.0
  - raw: `model = load_model('srkandw_lp', models_dictionary) # Heuristic front-load policy: buy the entire silo's worth of the best-yielding ingredient # (high`

### sroute_lp  (1)  — `testing_library/feas_test/sroute_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just commit a flat 6 units of the LA flow straight onto the LA-to-Salt-Lake leg and route around that? What would that fixed choice cost? | obj: 6496.0
  - raw: `model = load_model('sroute_lp', models_dictionary) # Heuristic: pin 6 units of LA traffic onto the LA-Salt Lake leg model.x['losangeles', 'losangeles'`

### stablem_mip  (1)  — `testing_library/feas_test/stablem_mip.txt`

- **WHY-NOT/heuristic** — Q: Our matchmakers prefer to run the classic men-propose routine: each man asks down his own list, every woman just holds onto the best suitor she's gotten so far, and we let it settle. If we lock the matching to whatever that men-first process produces, how much worse is the total woman preference score than the optimizer's plan? | obj: 12.0
  - raw: `model = load_model('stablem_mip', models_dictionary) # Heuristic 'man-proposing Gale-Shapley': run classic deferred acceptance with the MEN # proposin`

### stockcc_easy_mip  (2)  — `testing_library/feas_test/stockcc_easy_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother tuning a reorder schedule for every SKU — couldn't we just put everything on the minimum cadence and keep it dead simple? Wouldn't that be good enough? | obj: 436419.13
  - raw: `model = load_model('stockcc_easy_mip', models_dictionary) # Heuristic: every SKU on the minimum (i1) reorder schedule for n in model.nn:     for mm in`
- **WHY-NOT/heuristic** — Q: Couldn't we just put every SKU on the same uniform cadence — say six reorders a period across the board — instead of fine-tuning each one? Wouldn't one standard schedule be easier to run and come out at least as cheap? | obj: 218209.565
  - raw: `model = load_model('stockcc_easy_mip', models_dictionary) # Heuristic: every SKU on a uniform i2 (6 orders/period) schedule for n in model.nn:     for`

### swath_mip  (1)  — `testing_library/feas_test/swath_mip.txt`

- **WHY-NOT/heuristic** — Q: Our mission planners floated a dead-simple rule: just scan the swaths in numerical order — s0, then s1, then s2, all the way to s20, then close the loop back to s0 — and let the system only pick which node to enter and leave each swath. If we lock the visit sequence to that straight index order, how much longer is the total flight than the optimizer's clustered plan? | obj: 607.120947
  - raw: `model = load_model('swath_mip', models_dictionary) # Heuristic 'scan in index order': fix the swath visit sequence to the single tour # s0 -> s1 -> ..`

### tablelayout_mip  (1)  — `testing_library/feas_test/tablelayout_mip.txt`

- **WHY-NOT/heuristic** — Q: Our layout team likes a no-fuss rule of thumb: give every row the shortest height band whose widest cell still fits within an even per-column share of the page, and only go taller if nothing fits that share. If we lock the table to that simple rule instead of the optimizer's mix, how much taller does the table end up? | obj: 170.0
  - raw: `model = load_model('tablelayout_mip', models_dictionary) # Heuristic 'shortest-row-within-an-even-budget': allow each column an equal share of the # p`

### tabora_lp  (1)  — `testing_library/feas_test/tabora_lp.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the food side at all? Couldn't the village just grow enough straight maize each year to cover the families' grain needs and skip the maize-after-tobacco rotation entirely? How much does that simple rule actually cost us? | obj: 7140.85843462315
  - raw: `model = load_model('tabora_lp', models_dictionary) # Heuristic: meet the village's domestic maize demand with direct maize cropping # alone each year`

### tba_mip  (2)  — `testing_library/feas_test/tba_mip.txt`

- **WHY-NOT/heuristic** — Q: Do we really need to optimize the whole thing? A cautious desk would just fill the first two lots and let the back half go. How much profit does that leave on the table? | obj: 18.47999999999983
  - raw: `model = load_model('tba_mip', models_dictionary) # Heuristic: fill only the first two lots, fail the rest passed = {'l1', 'l2'} for i in model.i:`
- **WHY-NOT/heuristic** — Q: Here's the compliance-first playbook: pass every lot but never let a class-3 high-risk pool into the deal. Lock that in and tell me what profit that conservative rule produces. | obj: 34.53999999999969
  - raw: `model = load_model('tba_mip', models_dictionary) # Heuristic: pass all lots, never allocate class-3 pools for i in model.i:     for l in model.l:`

### tfordy_lp  (1)  — `testing_library/feas_test/tfordy_lp.txt`

- **WHY-NOT/heuristic** — Q: Why agonize over the investment timing? Couldn't we just build both mills on a flat, even schedule sized to the steady-state log volume the forest can deliver, and split it by how much capacity each mill draws per unit? | obj: 58.36419923610163
  - raw: `model = load_model('tfordy_lp', models_dictionary) # Heuristic flat-build policy: replace optimized lumpy investment with an even capacity-build # sch`

### tforss_lp  (6)  — `testing_library/feas_test/tforss_lp.txt`

- **WHAT-IF/new_constraint** — Q: Forest authorities are pushing a biodiversity rule that brutia must stay the dominant species across the region — they want total brutia plantings to remain at least 1.5x the size of total nigra plantings going forward. What does the plan look like under that rule? | obj: 802.3546074360165
  - raw: `model = load_model('tforss_lp', models_dictionary) model.biodiversity = Constraint(     expr=sum(model.v['brutia', k, at] for k in model.k for at in m`
- **WHY-NOT/constraint_rule** — Q: The whole plan is funnelled into a single age-class — every hectare we manage gets harvested at the same rotation. Shouldn't we spread plantings across rotations so no single age class holds more than half of any species' total managed area? Wouldn't a more diversified rotation still come in at a comparable benefit? | obj: 698.5869479225867
  - raw: `model = load_model('tforss_lp', models_dictionary) model.rotation_diversification = Constraint(     model.s, model.at,     rule=lambda m, s, at: sum(m`
- **WHY-NOT/constraint_rule** — Q: Sawnwood barely shows up in final shipments — almost everything we sell is pulp. Shouldn't we require sawnwood to come in at least 30% of pulp shipments so downstream processors get a balanced wood-product mix? What's keeping the model from doing that? | obj: 1102.0798393140094
  - raw: `model = load_model('tforss_lp', models_dictionary) model.sawnwood_ratio = Constraint(     expr=model.x['sawnwood'] >= 0.30 * model.x['pulp'], ) descri`
- **WHY-NOT/constraint_rule** — Q: Brutia is basically benched in this plan — nigra carries nearly all the planting. Shouldn't brutia pull at least a fifth of the total managed area so we're not betting the whole forest on one species? What's stopping the model from spreading the plantings out that way? | obj: 1980.1473672575157
  - raw: `model = load_model('tforss_lp', models_dictionary) model.brutia_min_share = Constraint(     expr=sum(model.v['brutia', k, at] for k in model.k for at`
- **WHY-NOT/constraint_rule** — Q: The poor-quality sites are sitting almost completely fallow while the model crowds everything onto the better land. Shouldn't every species put at least 15% of its poor-site allowance to work so we're actually using the land we're holding? What's keeping the model from doing that? | obj: 1964.2831569879017
  - raw: `model = load_model('tforss_lp', models_dictionary) model.poor_site_use = Constraint(     model.s,     rule=lambda m, s: sum(m.v[s, 'poor', at] * m.age`
- **WHY-NOT/heuristic** — Q: Looking at the yield tables, pulplogs peak at age 20 across both species and across every site class — sawlogs don't really show up until much later rotations. Wouldn't managing every hectare on a clean 20-year rotation, routing the whole harvest through pulp and mothballing the saw-mill, give us a comparable total benefit? | obj: 2177.79603841318
  - raw: `model = load_model('tforss_lp', models_dictionary) # Heuristic planning strategy set in advance, then solve the residual: # put EVERY stand on one uni`

### tgridmix_lp  (8)  — `testing_library/feas_test/tgridmix_lp.txt`

- **WHAT-IF/new_constraint** — Q: Our regional distribution agreement is being renegotiated and the counterparty wants each plant's outbound volume kept more diversified — no single market should pull more than 50% of any plant's total shipments. There's a proposal on the table to bake that rule in; what does the optimizer return for the cost and the new shipping mix? | obj: 154.8
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.diversification = Constraint(     model.I, model.J,     rule=lambda m, i, j: m.x[i, j] <= 0`
- **WHAT-IF/new_constraint** — Q: We're sizing the lanes for a new fleet contract that prices in tranches of 200 cases. There's a proposal to hold every plant-to-market lane to at most 200 cases so each one fits a single tranche. Plug that in and tell me where the total cost and the shipping plan land. | obj: 157.725
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.lane_cap = Constraint(     model.I, model.J,     rule=lambda m, i, j: m.x[i, j] <= 200, ) d`
- **WHAT-IF/new_constraint** — Q: The New York account is asking for a second-source guarantee so they're never single-sourced. We're evaluating a rule that keeps at least 30% of New York's demand coming off the Seattle plant. What does the optimizer return for total cost under that condition? | obj: 154.1025
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.ny_second_source = Constraint(     expr=model.x['seattle', 'new-york'] >= 0.30 * model.b['n`
- **WHY-NOT/constraint_rule** — Q: Operations is uneasy with how concentrated some of these lanes look — San Diego pours its whole feasible volume onto Topeka and New York while only thin slivers go elsewhere. Shouldn't no single plant cover more than 80% of any one market's demand so we're not single-sourced? What's keeping the model from spreading the load more evenly? | obj: 156.285
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.market_share_cap = Constraint(     model.I, model.J,     rule=lambda m, i, j: m.x[i, j] <=`
- **WHY-NOT/constraint_rule** — Q: Looking at the route mix, each plant is leaning hard on one or two markets and starving the rest. Shouldn't each plant spread its outbound so no single market draws more than 50% of any plant's total shipments? Wouldn't a more balanced plan still come in at a comparable cost? | obj: 154.8
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.lane_diversification = Constraint(     model.I, model.J,     rule=lambda m, i, j: m.x[i, j]`
- **WHY-NOT/constraint_rule** — Q: The Seattle-to-Chicago lane is carrying a full 300 cases on its own and it's getting congested at the rail head. Couldn't we hold that single lane to 250 cases and let the rest of the network pick up the slack? Shouldn't that still land at a sensible cost? | obj: 154.125
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.seattle_chicago_cap = Constraint(     expr=model.x['seattle', 'chicago'] <= 250, ) descript`
- **WHY-NOT/constraint_rule** — Q: Some markets end up sitting on a single supplier in this plan, which makes us nervous about outages. Shouldn't every market draw at least a quarter of its demand from each plant so the supply base is genuinely split? What's the model seeing that makes it lean so hard on one source per market? | obj: 157.05
  - raw: `model = load_model('tgridmix_lp', models_dictionary) model.dual_source = Constraint(     model.I, model.J,     rule=lambda m, i, j: m.x[i, j] >= 0.25`
- **WHY-NOT/heuristic** — Q: All this lane-by-lane optimizing feels overcooked. San Diego is the big plant — couldn't we just dedicate it to fill Topeka and New York to the brim, which exactly uses up its capacity, and let Seattle handle Chicago? Settle the rest with the solver. Shouldn't that clean asset-dedication plan hold a competitive cost? | obj: 153.675
  - raw: `model = load_model('tgridmix_lp', models_dictionary) # Heuristic: an asset-dedication plan set in advance, then solve the residual. # San Diego (cap 6`

### thai_mip  (1)  — `testing_library/feas_test/thai_mip.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we just commit two sailings of the big multi-port voyage v-15 up front and route around that? What would that fixed choice cost on the objective? | obj: 243.79100000000003
  - raw: `model = load_model('thai_mip', models_dictionary) # Heuristic: pin two large-ship sailings on voyage v-15 model.z['v-15', 'large'].fix(2) description`

### thaix_mip  (1)  — `testing_library/feas_test/thaix_mip.txt`

- **WHY-NOT/heuristic** — Q: Our schedulers like a clean rule of thumb: take the single biggest port and haul all of it on its own dedicated direct voyage, no piggy-backing on shared multi-stop runs. If we lock Songkhla to its direct voyage v-04 that way, how much worse does the man-miles bill get versus the optimizer's mixed plan? | obj: 1738460.0
  - raw: `model = load_model('thaix_mip', models_dictionary) # Heuristic 'direct-haul the biggest port': the largest-demand port (Songkhla) is carried # only on`

### trip_mip  (1)  — `testing_library/feas_test/trip_mip.txt`

- **WHY-NOT/heuristic** — Q: Instead of fine-tuning every relay, couldn't we keep the schedule simple and just ban the long-haul links — pin every mid-horizon link that spans three or more periods to off, leaving only short hops? What would that short-hop-only rule do to total travel time? | obj: 3992.633257920958
  - raw: `model = load_model('trip_mip', models_dictionary) # Heuristic: ban long-haul links (span >= 3 periods, not arriving at the horizon) -- short hops only`

### trnsgrid_lp  (1)  — `testing_library/feas_test/trnsgrid_lp.txt`

- **WHY-NOT/heuristic** — Q: Couldn't we run a simple standing split — every shelter gets a third of its pallets from the Seattle warehouse and two-thirds from the bigger San Diego warehouse? Same one-third / two-thirds rule on every lane, no case-by-case routing. Wouldn't that hold a competitive trucking cost? | obj: 158.775
  - raw: `model = load_model('trnsgrid_lp', models_dictionary) # Heuristic fixed-split policy: serve every shelter one-third from Seattle and # two-thirds from`

### trnsindic_mip  (1)  — `testing_library/feas_test/trnsindic_mip.txt`

- **WHY-NOT/heuristic** — Q: Our dispatchers like a dead-simple rule: hand each market entirely to one plant, taking the markets biggest-first and giving each to whichever plant it fits into most snugly on remaining capacity. If we lock the network to that single-source pattern, how much worse is the freight bill than the optimizer's mixed plan? | obj: 156.43200000000002
  - raw: `model = load_model('trnsindic_mip', models_dictionary) # Heuristic 'best-fit sole-source': handle markets largest-demand-first, assigning each # entir`

### trnsport_lp  (1)  — `testing_library/feas_test/trnsport_lp.txt`

- **WHY-NOT/heuristic** — Q: Forget the cost-juggling for a second — couldn't we just split each market's order between the two plants in proportion to how big each plant is? Seattle's the smaller cannery, San Diego the bigger, so every city draws from each in that capacity ratio. Wouldn't that simple fair-share rule hold a competitive shipping bill? | obj: 159.02763157894736
  - raw: `model = load_model('trnsport_lp', models_dictionary) # Heuristic capacity fair-share policy: allocate each market's demand across the # plants in prop`

### trnspwl_mip  (2)  — `testing_library/feas_test/trnspwl_mip.txt`

- **WHY-NOT/heuristic** — Q: Why not just run Seattle flat out to its capacity and let San Diego mop up the rest? Pin Seattle at 300 to Chicago plus 50 to Topeka, and have San Diego cover 325 to New York and 225 to Topeka. How much does that cost us? | obj: 9.729798899440468
  - raw: `model = load_model('trnspwl_mip', models_dictionary) # Heuristic: max Seattle out, San Diego absorbs the remainder pattern = {('seattle', 'chicago'):`
- **WHY-NOT/heuristic** — Q: Here's a simple split to try: keep Seattle on Chicago but also have it chip 50 cases into New York, then let San Diego handle 275 of New York and all 275 of Topeka. Where does that land on cost? | obj: 10.049763021663836
  - raw: `model = load_model('trnspwl_mip', models_dictionary) # Heuristic: Seattle helps on New York, San Diego splits the rest pattern = {('seattle', 'chicago`

### trnspwlx_mip  (2)  — `testing_library/feas_test/trnspwlx_mip.txt`

- **WHY-NOT/heuristic** — Q: Why not just run Seattle flat out and have San Diego absorb the rest? Pin Seattle at 300 to Chicago plus 50 to Topeka, and put San Diego on 325 to New York and 225 to Topeka. What's that cost? | obj: 10.297761965984964
  - raw: `model = load_model('trnspwlx_mip', models_dictionary) # Heuristic: max Seattle out, San Diego absorbs the remainder pattern = {('seattle', 'chicago'):`
- **WHY-NOT/heuristic** — Q: Try this simple split: keep Seattle on Chicago but have it also push 50 cases into New York, then let San Diego handle 275 of New York and all 275 of Topeka. Where does the cost land? | obj: 10.302356260960684
  - raw: `model = load_model('trnspwlx_mip', models_dictionary) # Heuristic: Seattle helps on New York, San Diego splits the rest pattern = {('seattle', 'chicag`

### tsp1_mip  (2)  — `testing_library/feas_test/tsp1_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole loop — couldn't we just run a greedy nearest-neighbour route, starting at city 1 and always hopping to the cheapest next stop (1, 2, 3, 6, 4, 5, back to 1)? Wouldn't that be good enough? | obj: 108.0
  - raw: `model = load_model('tsp1_mip', models_dictionary) # Heuristic: greedy nearest-neighbour tour 1->2->3->6->4->5->1 route = ['i1', 'i2', 'i3', 'i6', 'i4'`
- **WHY-NOT/heuristic** — Q: Couldn't we keep dispatch simple and just visit the cities in numbered order — 1, 2, 3, 4, 5, 6 and back to 1? Wouldn't running them in sequence be easier to manage? | obj: 92.0
  - raw: `model = load_model('tsp1_mip', models_dictionary) # Heuristic: visit cities in numbered order 1->2->3->4->5->6->1 route = ['i1', 'i2', 'i3', 'i4', 'i5`

### tsp2_mip  (3)  — `testing_library/feas_test/tsp2_mip.txt`

- **WHAT-IF/new_constraint** — Q: Let's look at a scenario where the tour is forced to take at least one of the long-haul legs — any leg costing 48 or more. If we require a minimum of one such long leg in the route, what does the optimizer report for total cost? | obj: 75.0
  - raw: `model = load_model('tsp2_mip', models_dictionary) longhaul = [(i, j) for i in model.ii for j in model.ii if i != j and value(model.c[i, j]) >= 48] mod`
- **WHY-NOT/heuristic** — Q: Our dispatcher doesn't trust the fancy routing — he just runs the old greedy rule: start at the depot (city 1) and always drive to the nearest stop you haven't hit yet, then loop home at the end. If we lock the tour to that nearest-neighbor route, how much more does it cost than the optimizer's plan? | obj: 92.0
  - raw: `model = load_model('tsp2_mip', models_dictionary) # Heuristic 'nearest neighbor': from the depot, repeatedly hop to the closest # unvisited city, then`
- **WHY-NOT/heuristic** — Q: Someone suggested we just visit the cities in plain numerical order — city 1, then 2, 3, all the way to 10, then back home. It's the simplest possible plan to explain to the crew. If we pin the tour to that straight-through ordering, what's the cost penalty versus the optimized loop? | obj: 100.0
  - raw: `model = load_model('tsp2_mip', models_dictionary) # Heuristic 'in-order': visit cities in their natural index order, then return home. seq = list(mode`

### tsp3_subt1_mip  (2)  — `testing_library/feas_test/tsp3_subt1_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole loop — couldn't we just run a greedy nearest-neighbour route, starting at city 1 and always hopping to the cheapest next stop (1, 2, 3, 6, 4, 5, back to 1)? Wouldn't that be good enough? | obj: 108.0
  - raw: `model = load_model('tsp3_subt1_mip', models_dictionary) # Heuristic: greedy nearest-neighbour tour 1->2->3->6->4->5->1 route = ['i1', 'i2', 'i3', 'i6'`
- **WHY-NOT/heuristic** — Q: Couldn't we keep dispatch simple and just visit the cities in numbered order — 1, 2, 3, 4, 5, 6 and back to 1? Wouldn't running them in sequence be easier to manage? | obj: 92.0
  - raw: `model = load_model('tsp3_subt1_mip', models_dictionary) # Heuristic: visit cities in numbered order 1->2->3->4->5->6->1 route = ['i1', 'i2', 'i3', 'i4`

### tsp3_subt2_mip  (2)  — `testing_library/feas_test/tsp3_subt2_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole loop — couldn't we just run a greedy nearest-neighbour route, starting at city 1 and always hopping to the cheapest next stop (1, 2, 3, 6, 4, 5, back to 1)? Wouldn't that be good enough? | obj: 108.0
  - raw: `model = load_model('tsp3_subt2_mip', models_dictionary) # Heuristic: greedy nearest-neighbour tour 1->2->3->6->4->5->1 route = ['i1', 'i2', 'i3', 'i6'`
- **WHY-NOT/heuristic** — Q: Couldn't we keep dispatch simple and just visit the cities in numbered order — 1, 2, 3, 4, 5, 6 and back to 1? Wouldn't running them in sequence be easier to manage? | obj: 92.0
  - raw: `model = load_model('tsp3_subt2_mip', models_dictionary) # Heuristic: visit cities in numbered order 1->2->3->4->5->6->1 route = ['i1', 'i2', 'i3', 'i4`

### tsp42_match_mip  (5)  — `testing_library/feas_test/tsp42_match_mip.txt`

- **WHY-NOT/constraint_rule** — Q: This plan isn't one connected route — stops 1, 2, 41 and 42 just close off into their own little loop, sealed away from the rest. Shouldn't we force that cluster to link out to the wider network instead of curling in on itself? What's the model seeing that makes it prefer the closed loop? | obj: 686.0
  - raw: `model = load_model('tsp42_match_mip', models_dictionary) S = ['c1', 'c2', 'c41', 'c42'] model.connect_S1 = Constraint(expr=sum(model.x[i, j] for i in`
- **WHY-NOT/constraint_rule** — Q: Stops 10, 11 and 12 just form a tight little triangle among themselves, completely cut off. Wouldn't it be better to break that closed three-stop loop so they feed into the main route? What's the trade-off keeping them sealed together? | obj: 648.0
  - raw: `model = load_model('tsp42_match_mip', models_dictionary) S = ['c10', 'c11', 'c12'] model.break_tri = Constraint(expr=sum(model.x[i, j] for i in S for`
- **WHY-NOT/constraint_rule** — Q: Stops 38, 39 and 40 are stuck in their own closed loop again. Couldn't the plan open that cluster up and weave it into the rest of the network? What's pulling it into an isolated little cycle? | obj: 647.0
  - raw: `model = load_model('tsp42_match_mip', models_dictionary) S = ['c38', 'c39', 'c40'] model.connect_S3 = Constraint(expr=sum(model.x[i, j] for i in S for`
- **WHY-NOT/heuristic** — Q: Why run a matching at all — couldn't we just string every stop into one big loop in numbered order, 1 through 42 and back to 1? Wouldn't that single round-trip be good enough? | obj: 699.0
  - raw: `model = load_model('tsp42_match_mip', models_dictionary) # Heuristic: one big loop in numbered order cs = ['c{}'.format(k) for k in range(1, 43)] for`
- **WHY-NOT/heuristic** — Q: Couldn't we just split the network into two regional loops — one circuit for stops 1 through 21 and a second for stops 22 through 42 — and run them independently? Wouldn't two tidy regional circuits be easier to manage? | obj: 934.0
  - raw: `model = load_model('tsp42_match_mip', models_dictionary) # Heuristic: two regional loops, [1..21] and [22..42] def close_loop(cs):     for a, b in zip`

### tsp42_tsp_mip  (2)  — `testing_library/feas_test/tsp42_tsp_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole loop — couldn't we just run the first 21 stops in order, then sweep back through the rest from 42 down to 22 before heading home? Wouldn't that out-and-back pattern be good enough? | obj: 930.0
  - raw: `model = load_model('tsp42_tsp_mip', models_dictionary) # Heuristic: out through 1..21, back through 42..22 route = ['c{}'.format(k) for k in range(1,`
- **WHY-NOT/heuristic** — Q: Couldn't we keep dispatch simple and just do all the odd-numbered stops first, then come back through all the even-numbered ones? Wouldn't splitting it odds-then-evens be easy enough to run? | obj: 1213.0
  - raw: `model = load_model('tsp42_tsp_mip', models_dictionary) # Heuristic: all odd stops then all even stops route = ['c{}'.format(k) for k in range(1, 43, 2`

### tsp4_assign_mip  (3)  — `testing_library/feas_test/tsp4_assign_mip.txt`

- **WHY-NOT/constraint_rule** — Q: This plan isn't a real tour at all — it's just a pile of two-city loops bouncing back and forth between paired cities. Shouldn't we ban those reciprocal back-and-forth pairs outright? What's the model seeing that makes it lean on them? | obj: 28.0
  - raw: `model = load_model('tsp4_assign_mip', models_dictionary) model.no_2cyc = ConstraintList() cities = list(model.I) for a in cities:     for b in cities:`
- **WHY-NOT/heuristic** — Q: Why run an optimizer at all — couldn't we just pair the cities off in order, 1 with 2, 3 with 4, 5 with 6 and so on down the list? Wouldn't that simple pairing be good enough? | obj: 196.0
  - raw: `model = load_model('tsp4_assign_mip', models_dictionary) # Heuristic: pair cities consecutively into two-city loops pairs = [('i1', 'i2'), ('i3', 'i4'`
- **WHY-NOT/heuristic** — Q: Instead of all these little back-and-forth pairs, couldn't we just commit to one big round-trip — send the route through every city in numbered order and straight back to the start? Wouldn't a single loop be cleaner to run? | obj: 100.0
  - raw: `model = load_model('tsp4_assign_mip', models_dictionary) # Heuristic: force one big round-trip in numbered order route = ['i1', 'i2', 'i3', 'i4', 'i5'`

### tsp4_tspcut_mip  (2)  — `testing_library/feas_test/tsp4_tspcut_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole loop — couldn't we just send the truck through the cities in numbered order, 1 through 12 and back to 1? Wouldn't that be simple enough? | obj: 100.0
  - raw: `model = load_model('tsp4_tspcut_mip', models_dictionary) # Heuristic: visit cities in numbered order 1->2->...->12->1 route = ['i1', 'i2', 'i3', 'i4',`
- **WHY-NOT/heuristic** — Q: Couldn't we just eyeball the clusters and string them together — run the 1/12 pair, then the 8/9 pair, the 6/7 and 4/5 depots, then the 2/10/11 group and finally city 3 before heading home? Wouldn't grouping the obvious neighbours be good enough? | obj: 75.0
  - raw: `model = load_model('tsp4_tspcut_mip', models_dictionary) # Heuristic: walk the visually-obvious clusters in sequence route = ['i1', 'i12', 'i8', 'i9',`

### tsp5_MTZ_mip  (2)  — `testing_library/feas_test/tsp5_MTZ_mip.txt`

- **WHY-NOT/heuristic** — Q: Why bother optimizing the whole loop — couldn't we just send the truck through the cities in numbered order, 1 through 17 and back to 1? Wouldn't that be simple enough? | obj: 167.0
  - raw: `model = load_model('tsp5_MTZ_mip', models_dictionary) # Heuristic: visit cities in numbered order 1->2->...->17->1 route = ['i{}'.format(k) for k in r`
- **WHY-NOT/heuristic** — Q: Couldn't we just eyeball the clusters and string them together — run the 1/12 group, then the 2/10/11/13 cluster, the 3/14 pair, the 8/9/17 group, and finish through the 4/5 and 6/7/15/16 depots before heading home? Wouldn't grouping the obvious neighbours be good enough? | obj: 56.0
  - raw: `model = load_model('tsp5_MTZ_mip', models_dictionary) # Heuristic: walk the visually-obvious clusters in sequence route = ['i1', 'i12', 'i2', 'i10', '`

### turkpow_lp  (1)  — `testing_library/feas_test/turkpow_lp.txt`

- **WHY-NOT/heuristic** — Q: Why fuss over the exact timing of nuclear? Couldn't we just take whatever total nuclear the plan wants and spread it evenly across the periods nuclear is allowed — 1993, 1998 and 2005? What does an even-build schedule like that cost us? | obj: 13819.630179450052
  - raw: `model = load_model('turkpow_lp', models_dictionary) # Heuristic nuclear-timing rule: take the total nuclear capacity the optimal plan # builds and spr`

### tvcsched_mip  (2)  — `testing_library/feas_test/tvcsched_mip.txt`

- **WHY-NOT/heuristic** — Q: Honestly, couldn't we skip the fancy optimization and just run each color in one solid block — all the reds, then the blues, then whites, then greens? How much worse does that tidy little layout actually spread things? | obj: 41.97619047619048
  - raw: `model = load_model('tvcsched_mip', models_dictionary) # Heuristic: lay each color down in one contiguous block (R \| B \| W \| G) slots = sorted(model.S,`
- **WHY-NOT/heuristic** — Q: What if we just used a dead-simple rule for the dominant red spots — drop one on every other slot across the front half (1, 3, 5, and so on up to 15) and let the rest fall in around them? Where does the spacing land? | obj: 11.45238095238095
  - raw: `model = load_model('tvcsched_mip', models_dictionary) # Heuristic: pin the reds onto every other slot across 1..15 red_slots = {1, 3, 5, 7, 9, 11, 13,`

### uimp_profit_lp  (8)  — `testing_library/feas_test/uimp_profit_lp.txt`

- **WHAT-IF/new_constraint** — Q: Plant engineering is pitching an early-spring maintenance window that needs machine time freed up across the winter run — they want total winter production (every machine, every shift, every product combined) capped at 80 units. What does the optimizer return for profit under that winter cap? | obj: 1412.0476190476193
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) model.winter_prod_cap = Constraint(     expr=sum(model.x['winter', j, k, l] for j in model.j f`
- **WHAT-IF/new_constraint** — Q: There's a proposal to free up summer floor space for a paint-line trial, which means holding the summer build back. We're evaluating capping total summer production — across every machine, shift, and product — at 90 units. What does the optimizer return for profit under that summer cap? | obj: 1398.3809523809523
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) model.summer_prod_cap = Constraint(     expr=sum(model.x['summer', j, k, l] for j in model.j f`
- **WHAT-IF/new_constraint** — Q: Finance wants to test a leaner overtime budget — the premium hours are eating into margin. We're evaluating a hard ceiling of 100 units on total overtime output, summed across both seasons, all machines and all products. What does the optimizer return for profit under that overtime cap? | obj: 1485.8809523809523
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) model.overtime_cap = Constraint(     expr=sum(model.x[i, 'overtime', k, l] for i in model.i fo`
- **WHY-NOT/constraint_rule** — Q: Looking at the revenue mix, one SKU is carrying way more than half of topline and it's a concentration risk the board is uncomfortable with. Shouldn't no single product clear more than 50% of total revenue, so we're not over-reliant on one line? What's keeping the model from picking a more balanced revenue mix? | obj: 1569.6147186147186
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) model.product_revenue_cap = ConstraintList() for k in model.k:     model.product_revenue_cap.a`
- **WHY-NOT/constraint_rule** — Q: Looking across the machines, m3 looks like it's barely pulling its weight while m1 and m2 do most of the work — the standing labor cost on m3 should buy us more of the line. Shouldn't each machine carry at least 30% of total production units, so we're getting the operator headcount we're paying for? What's making the model dump so little on m3? | obj: 1523.65873015873
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) total_prod = sum(model.x[i, j, k, l] for i in model.i for j in model.j for k in model.k for l`
- **WHY-NOT/constraint_rule** — Q: m3 sits idle on bolts and washers since it can only run nuts, yet we keep it staffed all year. If it's only good for nuts, shouldn't it at least be turning out a real share of them — say a quarter of total output as nut volume off m3? What's holding the model back from leaning on m3 for the nut work? | obj: 1566.047619047619
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) total_prod = sum(model.x[i, j, k, l] for i in model.i for j in model.j for k in model.k for l`
- **WHY-NOT/constraint_rule** — Q: The nut work looks lopsided — one line is hammering out nuts while the others barely touch them, and that single-point reliance worries me if a machine goes down mid-quarter. Shouldn't every machine that can run nuts carry at least a fifth of the total nut volume? What's the model seeing that makes it concentrate the nuts like that? | obj: 1468.6967592592591
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) total_nuts = sum(model.x[i, j, 'nuts', l] for i in model.i for j in model.j for l in model.l)`
- **WHY-NOT/heuristic** — Q: All this overtime juggling across the floor feels like more coordination than it's worth — every machine chasing every product on the premium shift. Wouldn't it run cleaner to fix an overtime lane per line up front — m1's overtime goes to bolts, m2's to washers, m3's to nuts — and just let the solver settle the normal-shift tonnages around it? Shouldn't that tidy overtime plan still hold a competitive profit? | obj: 1564.8333333333335
  - raw: `model = load_model('uimp_profit_lp', models_dictionary) # Heuristic: an overtime-line dedication plan set in advance, then solve the residual. # Each`

### uimp_revenue_lp  (7)  — `testing_library/feas_test/uimp_revenue_lp.txt`

- **WHAT-IF/new_constraint** — Q: HR is proposing an overtime ceiling for the winter run — they want total winter overtime production (every machine, every product combined) capped at 30 units to keep the holiday-season shift premium under control. What does the optimizer return for revenue under that overtime cap? | obj: 2003.6904761904761
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) model.winter_overtime_cap = Constraint(     expr=sum(model.x['winter', 'overtime', k, l] for`
- **WHAT-IF/new_constraint** — Q: Plant engineering wants an early-spring maintenance window that frees up machine time across the winter run — they're proposing to cap total winter production (every machine, every shift, every product combined) at 70 units. What does the optimizer return for revenue under that winter cap? | obj: 1891.3333333333333
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) model.winter_prod_cap = Constraint(     expr=sum(model.x['winter', j, k, l] for j in model.j`
- **WHAT-IF/new_constraint** — Q: Facilities is repartitioning the warehouse and there's a proposal to hold end-of-summer carryover inventory — bolts and nuts combined — to no more than 25 units, so the freed bins can go to another line. What does the optimizer return for revenue under that storage limit? | obj: 2246.5238095238096
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) model.summer_storage_cap = Constraint(     expr=sum(model.y['summer', k] for k in model.k) <=`
- **WHY-NOT/constraint_rule** — Q: Looking across the machines, m3 looks like it's barely pulling its weight while m1 and m2 do most of the work — the standing labor cost on m3 should buy us more of the line. Shouldn't each machine carry at least 30% of total production units, so we're getting the operator headcount we're paying for? What's making the model dump so little on m3? | obj: 2176.722222222222
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) total_prod = sum(model.x[i, j, k, l] for i in model.i for j in model.j for k in model.k for l`
- **WHY-NOT/constraint_rule** — Q: Winter overtime is running hot — the holiday-season shift premium adds up fast and the floor managers are pushing back on the schedule. Shouldn't winter overtime production stay under 40 units total across every machine and product, so we're not stacking premium hours on top of premium hours? What's keeping the model from trimming back the winter overtime push? | obj: 2113.690476190476
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) model.winter_overtime_cap = Constraint(     expr=sum(model.x['winter', 'overtime', k, l] for`
- **WHY-NOT/constraint_rule** — Q: Across both seasons the plan leans hard on overtime, and that premium time is the most expensive way we make anything. Shouldn't total overtime production across the whole year stay under 70 units so we're not so reliant on premium hours? What's keeping the model from leaning more on normal-shift capacity? | obj: 1787.357142857143
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) model.total_overtime_cap = Constraint(     expr=sum(model.x[i, 'overtime', k, l] for i in mod`
- **WHY-NOT/heuristic** — Q: Sales-ops is pushing a make-to-order discipline — set the plan up front to sell exactly the contracted demand in each season, no over-production and no inventory build, and let the solver settle the rest. Wouldn't that be simpler to run and roughly as strong on the topline? What's the model seeing that pulls it the other way? | obj: 1675.0
  - raw: `model = load_model('uimp_revenue_lp', models_dictionary) # Heuristic: a make-to-order plan set in advance — pin every season's sales to that # season'`

### vietman_vietmip_mip  (2)  — `testing_library/feas_test/vietman_vietmip_mip.txt`

- **WHY-NOT/heuristic** — Q: Why not just build out every plant and never worry about capacity — switch on all the ammonia and fertilizer sites and let shipping sort itself out? Wouldn't full coverage be worth it? | obj: 72733.32
  - raw: `model = load_model('vietman_vietmip_mip', models_dictionary) # Heuristic: build out every plant (all fertilizer and ammonia sites open) for j in model`
- **WHY-NOT/heuristic** — Q: Couldn't we just standardize on site 1 — run the whole operation out of the ammonia and fertilizer plants at site 1 and close the rest? Wouldn't a single consolidated location be simpler to manage? | obj: 70802.17
  - raw: `model = load_model('vietman_vietmip_mip', models_dictionary) # Heuristic: consolidate everything at site 1 for j in model.jd:     model.z[j].fix(1 if`

### vietman_viettag_mip  (2)  — `testing_library/feas_test/vietman_viettag_mip.txt`

- **WHY-NOT/heuristic** — Q: Why not just build out every plant and stop worrying about coverage — switch on all the ammonia and fertilizer sites and let the tagged routing fall where it may? Wouldn't full build-out be worth it? | obj: 72733.32
  - raw: `model = load_model('vietman_viettag_mip', models_dictionary) # Heuristic: build out every plant (all fertilizer and ammonia sites open) for j in model`
- **WHY-NOT/heuristic** — Q: Couldn't we just consolidate on site 1 — run all ammonia and fertilizer out of the site-1 plants and close everything else? Wouldn't a single hub be simpler to operate? | obj: 70802.17
  - raw: `model = load_model('vietman_viettag_mip', models_dictionary) # Heuristic: consolidate everything at site 1 for j in model.jd:     model.z[j].fix(1 if`

### westmip_mip  (2)  — `testing_library/feas_test/westmip_mip.txt`

- **WHY-NOT/heuristic** — Q: What if we went fully self-sufficient on finished goods — no imports of them at all, everything made at home? How much does that autarky stance cost us in welfare? | obj: 2659.006030357941
  - raw: `model = load_model('westmip_mip', models_dictionary) # Heuristic: no imports of the finished good in any period for te in model.te:     model.m[te, 'f`
- **WHY-NOT/heuristic** — Q: Here's a blunt import-substitution play: cut off intermediate-goods imports entirely and force the economy to make them domestically. Where does welfare end up under that rule? | obj: 2609.7416364819705
  - raw: `model = load_model('westmip_mip', models_dictionary) # Heuristic: no imports of intermediate goods in any period for te in model.te:     model.m[te, '`

### whouse_lp  (8)  — `testing_library/feas_test/whouse_lp.txt`

- **WHAT-IF/new_constraint** — Q: Treasury is putting an annual purchasing cap on the warehouse line — total buys across all four quarters combined can't exceed 30 units this year. Layer that cap into the plan and tell me where the total cost lands. | obj: -580.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.annual_buy_cap = Constraint(     expr=sum(model.buy[t] for t in model.t) <= 30.0 ) descriptio`
- **WHAT-IF/new_constraint** — Q: Operations wants a year-end safety buffer carried in the building — at least 20 units of stock still on hand at the close of quarter 4. We're evaluating that as a standing rule; plug it in and tell me where total cost ends up. | obj: -400.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.year_end_buffer = Constraint(     expr=model.stock['q-4'] >= 20.0 ) description = 'What-if: c`
- **WHAT-IF/new_constraint** — Q: There's a proposal to bridge inventory into the back half of the year — hold at least 30 units of stock at the end of quarter 2. What does the optimizer return for total cost if we layer that in? | obj: -450.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.q2_bridge_stock = Constraint(     expr=model.stock['q-2'] >= 30.0 ) description = 'What-if: b`
- **WHY-NOT/constraint_rule** — Q: Procurement's purchasing pattern leans hard on a single quarter, which makes supplier negotiation lopsided. Shouldn't no single quarter's purchase volume exceed 25 units, so we spread the supplier engagement across the year? What's keeping the model from picking that more diversified procurement schedule? | obj: -575.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.per_quarter_buy_cap = ConstraintList() for t in model.t:     model.per_quarter_buy_cap.add(mo`
- **WHY-NOT/constraint_rule** — Q: Single-quarter sell volume looks lumpy under the current plan, which strains the fulfillment team's pick-pack capacity. Shouldn't any quarter's sales stay under 40 units to give customer-ops a smoother pipeline? What's the model seeing that pulls it toward the lumpy plan? | obj: -540.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.per_quarter_sell_cap = ConstraintList() for t in model.t:     model.per_quarter_sell_cap.add(`
- **WHY-NOT/constraint_rule** — Q: The fulfillment floor keeps complaining the sell plan spikes too hard in one quarter. Couldn't we hold every quarter's sales to 30 units or under so the pick-pack crew isn't slammed? What's driving the model to lean on that one big quarter instead? | obj: -530.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.per_quarter_sell_cap30 = ConstraintList() for t in model.t:     model.per_quarter_sell_cap30.`
- **WHY-NOT/constraint_rule** — Q: Receiving keeps getting hammered when the plan dumps a big purchase into one quarter. Couldn't we hold each quarter's buy to 15 units at most, so the dock load stays manageable week to week? What's keeping the model from smoothing the buying out like that? | obj: -565.0
  - raw: `model = load_model('whouse_lp', models_dictionary) model.per_quarter_buy_cap15 = ConstraintList() for t in model.t:     model.per_quarter_buy_cap15.ad`
- **WHY-NOT/heuristic** — Q: I keep thinking we're overcomplicating this. Quarter 3 has the cheapest selling price ($8) and quarter 2 the dearest ($12) — so why not just run it as a plain buy-low, sell-high play: do all our purchasing in q-3, do all our selling in q-2, and leave q-1 and q-4 out of the trading entirely? Let the solver size the q-3 buy and the q-2 sell however it likes. Wouldn't that simple dedicated schedule be about as good as anything fancier? | obj: -550.0
  - raw: `model = load_model('whouse_lp', models_dictionary) # Heuristic planning strategy: dedicate the cheapest-price quarter (q-3) as the sole # buying windo`

### yemcem_mip  (2)  — `testing_library/feas_test/yemcem_mip.txt`

- **WHY-NOT/heuristic** — Q: Why pour money into kiln expansions at all — couldn't we just run the plant capacity we already have and cover the rest with imports? Wouldn't keeping the existing kilns and skipping all the new builds come out cheaper? | obj: 1664.5908591326263
  - raw: `model = load_model('yemcem_mip', models_dictionary) # Heuristic: no new kiln investment beyond the pre-committed Mafrak unit for idx in model.y:     i`
- **WHY-NOT/heuristic** — Q: Big kilns feel risky to commit to. Couldn't we just keep things incremental and only ever build small kilns? Wouldn't a small-units-only program be good enough? | obj: 1632.8989641040992
  - raw: `model = load_model('yemcem_mip', models_dictionary) # Heuristic: only ever build small kilns (forbid medium and large) for idx in model.y:     if idx[`

---


## 4. Deferred — complex but model has no per-constraint dataset (dedup-skip / excluded NLP)

Map to the equivalent model (e.g. agreste_lp297->agreste_lp293, spbenders4/5->spbenders3, thaix->thai) later.


### agreste_lp297  (4)  — `testing_library/feas_test/agreste_lp297.txt`

- **WHAT-IF/new_constraint** — Q: Our HR director has been pushing back hard on the temp-heavy summer schedule — she wants total temporary labor across the whole year held to no more than 40 man-days so temps stay a real supplement and not the workhorse. How does that change farm income? -> `model.tlab_annual_cap = Constraint(expr=sum(model.tlab[tm] for tm in model.tm) <= 40)` (obj 16987.565)
- **WHY-NOT/constraint_rule** — Q: Looking at the schedule, temporary labor concentrates in peak months — over 50 man-days in July alone — while family labor stays pinned at full capacity. Couldn't we require that in every month temporary labor never makes up more than 25% of the total labor used that month (family plus temporary)? Shouldn't a smoother labor distribution beat the current plan? -> `def temp_share_rule(model, tm):     return model.tlab[tm] <= 0.25 * (model.tlab[tm] + model.flab[tm]) model.temp_share = Constraint(model.tm, rule=temp_share_rule)` (obj 17121.496)
- **WHY-NOT/constraint_rule** — Q: Labor cost looks heavy relative to what the farm earns — eating roughly a third of revenue right now. Wouldn't tying labor spend to a tighter ratio, say no more than 30% of revenue, give us a leaner plan? -> `model.labcost_cap = Constraint(expr=model.labcost <= 0.30 * model.revenue)` (obj 16640.954)
- **WHY-NOT/constraint_rule** — Q: The model is cramming nearly all of the good land with crops and leaving the livestock no room there. We'd like to keep some of our best ground in reserve — couldn't we hold cropping on good land to at most 6 hectares so there's slack for grazing or a fallow rotation? What's stopping the model from leaving that buffer? -> `model.good_crop_cap = Constraint(expr=sum(model.a[p] * model.xcrop[p, 'good'] for (p, s) in model.ps if s == 'good') <= 6.0)` (obj 16261.33)

### awktsp_mip_cut  (3)  — `testing_library/feas_test/awktsp_mip_cut.txt`

- **WHAT-IF/new_constraint** — Q: Suppose the link between city 1 and city 5 is unavailable in both directions. Drop that connection and let me see the new assignment cost. -> `model.block_15 = Constraint(expr=model.x['i1', 'i5'] + model.x['i5', 'i1'] == 0)` (obj 124.0)
- **WHAT-IF/new_constraint** — Q: We're looking at a scenario where cities 6 and 7 can't be linked directly to each other either way. Remove that pairing and tell me how the total cost shifts. -> `model.block_67 = Constraint(expr=model.x['i6', 'i7'] + model.x['i7', 'i6'] == 0)` (obj 44.0)
- **WHY-NOT/constraint_rule** — Q: Cities 1 and 5 just ping-pong straight off each other in this plan. Couldn't we stop them forming that closed pair and route through them as part of a longer chain? What's pulling them into a two-city loop? -> `model.no_2cyc_15 = Constraint(expr=model.x['i1', 'i5'] + model.x['i5', 'i1'] <= 1)` (obj 72.0)

### dicegrid_mip  (2)  — `testing_library/feas_test/dicegrid_mip.txt`

- **WHAT-IF/new_constraint** — Q: Suppose the manufacturing template wants every die to share the same maximum face number. If we tie the top faces of all three dice to one common value and re-submit, where does the win count come out? -> `model.equal_tops_12 = Constraint(expr=model.fval['dice1', 'face6'] == model.fval['dice2', 'face6']) model.equal_tops_23 = Constraint(expr=model.fval['dice2', 'face6'] == model.fval['dice3', 'face6'])` (obj 20.0)
- **WHY-NOT/constraint_rule** — Q: The three dice peak at 16, 13, and 18 — three different ceilings, which seems untidy. Why couldn't they all just top out at the same value without losing wins? Pin every die's highest face to a single shared number and show me the penalty. -> `model.why_eq_tops_12 = Constraint(expr=model.fval['dice1', 'face6'] == model.fval['dice2', 'face6']) model.why_eq_tops_23 = Constraint(expr=model.fval['dice2', 'face6'] == model.fval['dice3', 'face6'])` (obj 20.0)

### nemhaus_nlp  (8)  — `testing_library/feas_test/nemhaus_nlp.txt`

- **WHAT-IF/new_constraint** — Q: We're weighing whether to put activities act-2 and act-3 in the same building — fac-1 — so they can share a line. What interaction cost does that pairing run us? -> `model.colo_a = Constraint(expr=model.x['act-2', 'fac-1'] == 1) model.colo_b = Constraint(expr=model.x['act-3', 'fac-1'] == 1)` (obj 8.0)
- **WHAT-IF/new_constraint** — Q: Suppose act-3 and act-4 are housed together over in fac-1. Run it and tell me the interaction cost that comes with that. -> `model.colo_a = Constraint(expr=model.x['act-3', 'fac-1'] == 1) model.colo_b = Constraint(expr=model.x['act-4', 'fac-1'] == 1)` (obj 7.0)
- **WHAT-IF/new_constraint** — Q: There's a proposal on the table to share one site between act-1 and act-4, both in fac-1. What's the resulting interaction cost? -> `model.colo_a = Constraint(expr=model.x['act-1', 'fac-1'] == 1) model.colo_b = Constraint(expr=model.x['act-4', 'fac-1'] == 1)` (obj 4.0)
- **WHAT-IF/new_constraint** — Q: Let's try sitting act-1 and act-3 together in fac-1. Where does the interaction cost land? -> `model.colo_a = Constraint(expr=model.x['act-1', 'fac-1'] == 1) model.colo_b = Constraint(expr=model.x['act-3', 'fac-1'] == 1)` (obj 2.0)
- **WHAT-IF/new_constraint** — Q: We're looking at co-locating act-1 and act-5 in the same facility, fac-1. What interaction cost does that bring? -> `model.colo_a = Constraint(expr=model.x['act-1', 'fac-1'] == 1) model.colo_b = Constraint(expr=model.x['act-5', 'fac-1'] == 1)` (obj 3.0)
- **WHY-NOT/constraint_rule** — Q: Activities act-2 and act-4 trade a fair bit of work back and forth, yet the layout scatters them to separate buildings. Wouldn't it be obvious to house them together in fac-1? What's the model seeing that keeps them apart? -> `model.want_a = Constraint(expr=model.x['act-2', 'fac-1'] == 1) model.want_b = Constraint(expr=model.x['act-4', 'fac-1'] == 1)` (obj 6.0)
- **WHY-NOT/constraint_rule** — Q: Act-4 and act-5 feel like they belong side by side given how much they hand off to each other. Shouldn't the plan just drop them both in fac-1? What's the trade-off pulling them to separate sites? -> `model.want_a = Constraint(expr=model.x['act-4', 'fac-1'] == 1) model.want_b = Constraint(expr=model.x['act-5', 'fac-1'] == 1)` (obj 6.0)
- **WHY-NOT/constraint_rule** — Q: Act-3 and act-5 keep handing material to one another, but the optimal layout splits them up. Couldn't we just keep the two in the same building, fac-1? What's keeping the optimizer from doing that? -> `model.want_a = Constraint(expr=model.x['act-3', 'fac-1'] == 1) model.want_b = Constraint(expr=model.x['act-5', 'fac-1'] == 1)` (obj 6.0)

### spbenders4_lp  (1)  — `testing_library/feas_test/spbenders4_lp.txt`

- **WHY-NOT/constraint_rule** — Q: Some lanes are carrying very large dose volumes. Shouldn't we cap every plant-to-clinic lane at 300 doses for a more even, lower-risk network? Walk me through what's pulling the plan the other way. -> `def lane_cap_rule(model, i, j):     return model.ship[i, j] <= 300 model.lane_cap = Constraint(model.I, model.J, rule=lane_cap_rule)` (obj 10316.9)

### spbenders5_lp  (2)  — `testing_library/feas_test/spbenders5_lp.txt`

- **WHY-NOT/constraint_rule** — Q: A few delivery lanes carry huge volumes. Couldn't we just cap every press-to-newsstand lane at 250 copies for a more even fleet load? What's the tradeoff I'm missing? -> `def lane_cap_rule(model, i, j):     return model.ship[i, j] <= 250 model.lane_cap = Constraint(model.I, model.J, rule=lane_cap_rule)` (obj 10020.4)
- **WHY-NOT/constraint_rule** — Q: Even 250 feels high. Shouldn't we tighten every lane to 200 copies for a leaner delivery network? Walk me through what's pulling the plan the other way. -> `def lane_cap200_rule(model, i, j):     return model.ship[i, j] <= 200 model.lane_cap200 = Constraint(model.I, model.J, rule=lane_cap200_rule)` (obj 9708.1)

### thaix_mip  (1)  — `testing_library/feas_test/thaix_mip.txt`

- **WHAT-IF/new_constraint** — Q: Suppose we want a stronger medium-ship presence on the Nakon run for crew-rotation reasons. If we require the medium hulls to lift at least 400 of Nakon's men, what total man-miles does the model come back with? -> `model.nakon_med = Constraint(expr=sum(model.y[vv, 'medium', 'nakon'] for (vv, kk, qq) in model.vkp if kk == 'medium' and qq == 'nakon') >= 400)` (obj 1672110.0)

### tsp4_tspcut_mip  (4)  — `testing_library/feas_test/tsp4_tspcut_mip.txt`

- **WHAT-IF/new_constraint** — Q: Roadworks are closing the link between city 4 and city 5 in both directions this season. With that connection gone, what does the best tour come to? -> `model.close_45 = Constraint(expr=model.x['i4', 'i5'] + model.x['i5', 'i4'] == 0)` (obj 51.0)
- **WHAT-IF/new_constraint** — Q: We're evaluating a corridor restriction: no direct legs allowed between the 6/7 depot pair and the 4/5 pair, in either direction. Block that corridor off and tell me how the tour cost shifts. -> `model.block_corridor = Constraint(expr=sum(model.x[a, b] + model.x[b, a] for a in ['i6', 'i7'] for b in ['i4', 'i5']) == 0)` (obj 53.0)
- **WHAT-IF/new_constraint** — Q: Suppose the direct connector between city 1 and city 12 is taken out of service both ways. Drop it and tell me what the new best tour costs. -> `model.close_1_12 = Constraint(expr=model.x['i1', 'i12'] + model.x['i12', 'i1'] == 0)` (obj 42.0)
- **WHY-NOT/constraint_rule** — Q: Cities 6 and 7 get visited back to back, like a little twin stop glued together. Wouldn't it be more sensible to split them so each anchors a different stretch of the loop? What's the trade-off that keeps them paired? -> `model.split_67 = Constraint(expr=model.x['i6', 'i7'] + model.x['i7', 'i6'] == 0)` (obj 41.0)

### uimp_revenue_lp  (1)  — `testing_library/feas_test/uimp_revenue_lp.txt`

- **WHY-NOT/constraint_rule** — Q: The plan is building a big stack of summer inventory just to sell it down in winter, and that ties up bins and working capital we'd rather not carry. Shouldn't we hold end-of-summer carryover to no more than 5 units of each product, instead of building ahead like this? What's the model seeing that makes the build-ahead worth it? -> `def carry_cap_rule(model, k):     return model.y['summer', k] <= 5.0 model.summer_carry_cap = Constraint(model.k, rule=carry_cap_rule)` (obj 2231.5238095238096)

---

## Manually reviewed & finalized models (what-if/why-not)
- **bidpwl_mip — DONE 2026-06-10.** Hsuan-Han hand-edited its queries; 8 records in `datasets/bidpwl_mip_optichat_query.jsonl` (ac_combined_cap / lead_tier_excl / vendor_cap[idx] / c_cap+b_commit / cr_e_half_c / cr_bd_floor / cr_min_slice[idx] / cr_c_implies_b), all selfcheck PASS. The 1 cheapest-slope-ladder heuristic SKIPPED -> section 3 (computed pattern, can't auto-convert).
- **allbases_mip — DONE 2026-06-10.** Hsuan-Han hand-edited its testing_library queries; 8 records built into `datasets/allbases_mip_optichat_query.jsonl` (6 constraints: lane_exclusive / se_ny_anchor+se_top_toe / sd_east_floor / want_ny_balance / want_se_inland / want_topeka_split, + 2 heuristics converted from multi-variable .fix() loops to equality-constraint sets). All 8 selfcheck PASS.
