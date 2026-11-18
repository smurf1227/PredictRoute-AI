# PredictRoute AI viva preparation

## Live demonstration

Open **Route Optimization**, load the five-stop Okhla scenario, and select **Optimize Route**. Compare the three routes, click a marker, show the convergence chart, and export CSV or JSON. With the default seed, the demo reduced estimated distance from 156.21 km to 119.10 km and matched the exact objective. Load the 15-stop scenario to show a run above the exact-solver limit.

## Questions and answers

1. **What problem does the module solve?** It orders delivery stops for a single vehicle that departs from and returns to one warehouse.
2. **How does this relate to the travelling salesperson problem?** Every feasible tour visits all destinations once and returns to the depot.
3. **Why use a separate dataset?** The forecasting and delay data lack the linked warehouse, stop coordinates, demand and vehicle data required for a delivery tour.
4. **What is synthetic?** Coordinates approximate Delhi NCR localities. Delivery quantities, vehicle parameters and priorities are illustrative.
5. **How is a chromosome represented?** It is a permutation of destination indices. The depot is implicit at both ends.
6. **How is capacity enforced?** Total demand must fit at departure. Each delivery reduces the vehicle load.
7. **Why use a GA?** It explores a factorial search space under a fixed budget and can evaluate additive route objectives.
8. **Is this supervised learning?** The GA searches candidates using a specified fitness function. A supervised model learns from labelled examples.
9. **What does the existing Random Forest do?** It predicts shipment delay using labelled individual shipments and their features.
10. **Why omit delay risk?** The shipment data do not validate how changing stop order affects multi-stop route delay.
11. **Can forecasts set demand quantities?** Yes, once an explicit, validated mapping from stores and products to delivery stops exists.
12. **What does Haversine compute?** It estimates great-circle distance between latitude and longitude points.
13. **Why use a 1.25 factor?** It is an illustrative driving-distance multiplier for the simulation.
14. **What does the map show?** Straight links between stops in route order. Marker numbers show the GA visit order.
15. **How are time and cost estimated?** Divide estimated distance by speed and multiply estimated distance by cost per kilometre, respectively.
16. **Why normalize fitness?** Fixed reference units make distance, time and cost dimensionless before weighting.
17. **Are the default objectives independent?** No. At constant speed and rate, all three rank candidates by distance.
18. **When can time conflict with distance?** A supplied travel-time matrix can describe a shorter but slower leg.
19. **What is tournament selection?** Sample up to three candidates and select the lowest-fitness candidate as a parent.
20. **How does order crossover work?** Keep one parent's slice and fill remaining positions in the other parent's cyclic order, skipping clients already present.
21. **What is swap mutation?** Exchange two stops while preserving the full set of destinations.
22. **What is elitism?** Copy the fittest candidates into the next generation unchanged.
23. **Why seed both baselines?** It guarantees the saved GA result is at least as good as either baseline in weighted fitness.
24. **How does Nearest Neighbour work?** Choose the closest unvisited stop repeatedly, then return to the depot.
25. **How is exact fitness obtained?** Held–Karp dynamic programming solves the weighted cycle for up to ten destinations.
26. **What is the optimality gap?** Divide GA fitness minus exact fitness by the exact fitness and multiply by 100 when the optimum is positive.
27. **Can the average fitness get worse?** Yes. The best-so-far record remains nonincreasing while generations explore new candidates.
28. **What does the seed reproduce?** The random search sequence, route and fitness history under the same inputs and software.
29. **What would make evaluation more realistic?** Calibrated road and travel-time data, observed schedules, service durations and realistic fleet constraints.
