# Vacuous-control records in the what-if/why-not dataset (2026-06-10)

40 records across 21 models where the constraint self-grades EQUIVALENT but the relation-flip control is NOT caught (faithful-but-non-discriminating — the oracle-vacuity / A-layer-feasibility-contrast failure: a syntactic flip the oracle can't distinguish). Use as the empirical anchor for 小白's contrast-liveness section.

Typical pattern: a binary fix-to-zero (e.g. ban a link x[i,j] <= 0); flipping <= to >= is vacuous because x is already NonNegative/binary.


## awktsp_mip_assign (2)
- `block_15` — Q: Suppose the link between city 1 and city 5 is unavailable in both directions. Drop that co
    model.block_15 = Constraint(expr=model.x['i1', 'i5'] + model.x['i5', 'i1'] == 0)
- `block_67` — Q: We're looking at a scenario where cities 6 and 7 can't be linked directly to each other ei
    model.block_67 = Constraint(expr=model.x['i6', 'i7'] + model.x['i7', 'i6'] == 0)

## bchtsp_mip (2)
- `no_15_link` — Q: City 1 and city 5 are getting a permanent road closure between them this season, so the tr
    model.no_15_link = Constraint(expr=model.x['i1', 'i5'] + model.x['i5', 'i1'] == 0)
- `no_67_link` — Q: We want to test what happens if city 6 and city 7 can't be served back-to-back — say their
    model.no_67_link = Constraint(expr=model.x['i6', 'i7'] + model.x['i7', 'i6'] == 0)

## boxpacking_mip (1)
- `pull_b1_b2` — Q: Two specific cartons, b1 and b2, are being rerouted to a different lane. If neither of the
    model.pull_b1_b2 = Constraint(expr=model.OMEGA['b1'] + model.OMEGA['b2'] == 0)

## coex_mip (2)
- `b_front_only` — Q: Imagine the black army is confined to a forward staging area only — the first two rows of 
    model.b_front_only = Constraint(expr=sum(model.b[i, j] for i in model.i for j in model.i if i > 2) == 0)
- `w_corner` — Q: Why does the white army need to be smeared across the whole lower board? It seems like it 
    model.w_corner = Constraint(expr=sum(model.w[i, j] for i in model.i for j in model.i if not (i >= 6 and j >= 6)) == 0)

## cross_mip (2)
- `delay89` — Q: Suppose the crossing can't be wrapped up until period 10 — nothing all-across at period 8 
    model.delay89 = Constraint(expr=model.done['t8'] + model.done['t9'] == 0)
- `never_done` — Q: What if the crossing simply never gets completed within the ten periods — nothing all-acro
    model.never_done = Constraint(expr=model.done['t8'] + model.done['t9'] + model.done['t10'] == 0)

## cube_mip (2)
- `no_corners` — Q: We want to see the layout when the eight cube corners are all left empty — none of the (a/
    model.no_corners = Constraint(expr=sum(model.core[i, j, k] for i in ['a', 'c'] for j in ['a', 'c'] for k in ['a', 'c']) 
- `spine_empty` — Q: The plan keeps planting balls right down the dead-center column — the cells where the firs
    model.spine_empty = Constraint(expr=sum(model.core['b', 'b', k] for k in model.x) == 0)

## cubesoln_mip (1)
- `no_corners` — Q: The eight corner positions are being reserved for mounting hardware, so they have to stay 
    model.no_corners = Constraint(expr=sum(model.core[i, j, k] for i in [1, 3] for j in [1, 3] for k in [1, 3]) == 0)

## knights_mip (1)
- `empty_col1` — Q: The whole of column 1 is sitting half-used. Why not just leave that entire leftmost file e
    model.empty_col1 = Constraint(expr=sum(model.x[i, '1'] for i in model.i) == 0)

## korpet_mip (1)
- `no_inchon` — Q: Inchon is our smallest, most expensive site. Why sink any investment there at all — couldn
    model.no_inchon = Constraint(model.m, model.te, rule=lambda m, unit, te: m.y[unit, 'inchon', te] == 0)

## mexsd_mip (1)
- `no_sicartsa` — Q: There's a scenario where Sicartsa is taken off the table for any new investment at all. Ru
    model.no_sicartsa = Constraint(expr=sum(model.y[me, 'sicartsa', te] for me in model.me for te in model.te) == 0)

## poutil_mip (1)
- `no_contracts` — Q: Why are we tied into spot-market contracts at all? Surely the on-site plant plus load-foll
    model.no_contracts = Constraint(expr=model.alpha + model.beta == 0)

## queens_mip (1)
- `no_corners` — Q: Suppose the board's design rules out all four corner squares entirely. Plug that in — does
    model.no_corners = Constraint(expr=model.x['1', '1'] + model.x['1', '8'] + model.x['8', '1'] + model.x['8', '8'] == 0)

## ridesharing_miqcp (1)
- `no_C` — Q: Path C is closed for maintenance next week, so the dispatch team is looking at a scenario 
    model.no_C = Constraint(expr=sum(model.x[v, r, 'C'] for r in model.R for v in model.Vr[r].value) == 0)

## stockcc_easy_mip (1)
- `min_service` — Q: Procurement is pitching a minimum service level: every SKU should be reordered at least si
    model.min_service = Constraint(expr=sum(model.z[n, 'i1'] for n in model.nn) == 0)

## tablelayout_mip (2)
- `r1_min40` — Q: Row 1 carries some dense content and we're curious about giving it more vertical room. Sup
    model.r1_min40 = Constraint(expr=model.bRH[1, 10] + model.bRH[1, 20] + model.bRH[1, 30] == 0)
- `r3_min30` — Q: Row 3 came out at just 20 units tall, the same short band as row 1, even though it's holdi
    model.r3_min30 = Constraint(expr=model.bRH[3, 10] + model.bRH[3, 20] == 0)

## tba_mip (3)
- `drop_l3_l4` — Q: Suppose settlement issues mean we can't fill either of the last two lots, l3 and l4. Run t
    model.drop_l3_l4 = Constraint(expr=model.w[20580252, 'l3'] + model.w[20580252, 'l4'] == 0)
- `no_c3` — Q: Compliance is floating a rule to keep the class-3 high-risk pools out of every lot entirel
    model.no_c3 = Constraint(model.l, rule=lambda m, l: sum(m.z[p, 20580252, l] for p in m.c3) == 0)
- `want_no_c3` — Q: The plan keeps reaching for the class-3 high-risk pools to fill lots. Shouldn't we just ke
    model.want_no_c3 = Constraint(model.l, rule=lambda m, l: sum(m.z[p, 20580252, l] for p in m.c3) == 0)

## tsp1_mip (4)
- `close_45` — Q: Roadworks are about to close the link between city 4 and city 5 in both directions for the
    model.close_45 = Constraint(expr=model.x['i4', 'i5'] + model.x['i5', 'i4'] == 0)
- `cut_6_12` — Q: We're looking at a scenario where the depot at city 6 loses its direct connections to both
    model.cut_6_12 = Constraint(expr=model.x['i1', 'i6'] + model.x['i6', 'i1'] + model.x['i2', 'i6'] + model.x['i6', 'i2'] =
- `cut_23` — Q: Suppose the direct road between city 2 and city 3 is taken out of service both ways. Drop 
    model.cut_23 = Constraint(expr=model.x['i2', 'i3'] + model.x['i3', 'i2'] == 0)
- `no_13` — Q: The plan keeps leaning on the direct shortcut between city 1 and city 3. That feels like a
    model.no_13 = Constraint(expr=model.x['i1', 'i3'] + model.x['i3', 'i1'] == 0)

## tsp3_subt1_mip (4)
- `close_45` — Q: Roadworks are about to close the link between city 4 and city 5 in both directions for the
    model.close_45 = Constraint(expr=model.x['i4', 'i5'] + model.x['i5', 'i4'] == 0)
- `cut_6_12` — Q: We're looking at a scenario where the depot at city 6 loses its direct connections to both
    model.cut_6_12 = Constraint(expr=model.x['i1', 'i6'] + model.x['i6', 'i1'] + model.x['i2', 'i6'] + model.x['i6', 'i2'] =
- `cut_23` — Q: Suppose the direct road between city 2 and city 3 is taken out of service both ways. Drop 
    model.cut_23 = Constraint(expr=model.x['i2', 'i3'] + model.x['i3', 'i2'] == 0)
- `no_13` — Q: The plan keeps leaning on the direct shortcut between city 1 and city 3. That feels like a
    model.no_13 = Constraint(expr=model.x['i1', 'i3'] + model.x['i3', 'i1'] == 0)

## tsp3_subt2_mip (4)
- `close_45` — Q: Roadworks are about to close the link between city 4 and city 5 in both directions for the
    model.close_45 = Constraint(expr=model.x['i4', 'i5'] + model.x['i5', 'i4'] == 0)
- `cut_6_12` — Q: We're looking at a scenario where the depot at city 6 loses its direct connections to both
    model.cut_6_12 = Constraint(expr=model.x['i1', 'i6'] + model.x['i6', 'i1'] + model.x['i2', 'i6'] + model.x['i6', 'i2'] =
- `cut_23` — Q: Suppose the direct road between city 2 and city 3 is taken out of service both ways. Drop 
    model.cut_23 = Constraint(expr=model.x['i2', 'i3'] + model.x['i3', 'i2'] == 0)
- `no_13` — Q: The plan keeps leaning on the direct shortcut between city 1 and city 3. That feels like a
    model.no_13 = Constraint(expr=model.x['i1', 'i3'] + model.x['i3', 'i1'] == 0)

## tsp4_assign_mip (2)
- `block_67` — Q: Suppose cities 6 and 7 can no longer be assigned directly to each other in either directio
    model.block_67 = Constraint(expr=model.x['i6', 'i7'] + model.x['i7', 'i6'] == 0)
- `block_89` — Q: We're looking at a scenario where cities 8 and 9 can't be paired directly with each other 
    model.block_89 = Constraint(expr=model.x['i8', 'i9'] + model.x['i9', 'i8'] == 0)

## tsp5_MTZ_mip (2)
- `close_45` — Q: Roadworks are closing the link between city 4 and city 5 in both directions. With that con
    model.close_45 = Constraint(expr=model.x['i4', 'i5'] + model.x['i5', 'i4'] == 0)
- `close_3_14` — Q: Suppose the link between city 3 and city 14 is taken out of service both ways. Drop that c
    model.close_3_14 = Constraint(expr=model.x['i3', 'i14'] + model.x['i14', 'i3'] == 0)
