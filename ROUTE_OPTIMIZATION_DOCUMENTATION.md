# PredictRoute AI

PredictRoute plans an ordered delivery tour for one vehicle. It starts at a warehouse, visits each destination once and returns to the warehouse. It compares the supplied stop order, a greedy route and a Genetic Algorithm (GA) under the same travel model. The intended demonstration is to measure the effect of changing stop order and show how an evolutionary search progresses.

## Architecture and data

The existing dashboard loads scenarios and posts JSON to the routing router mounted in the existing FastAPI application. `route_api.py` validates the problem and compiles travel costs, `route_data.py` reads scenarios and computes geographic distances, and `route_optimizer.py` solves and scores tours. Leaflet displays the stop geometry on OpenStreetMap, and Chart.js uses the computed response for charts. Forecasting and shipment-delay classification use their original endpoints.

`DeliveryRoutes.csv` contains synthetic academic examples in Delhi NCR. The three scenarios start in Okhla (5 stops), Najafgarh (8 stops) and Kashmere Gate (15 stops). There are 15 distinct destination locations across the file. Coordinates represent approximate localities. The delivery IDs, quantities, priorities, capacities, costs and speeds are illustrative. CSV row order within each scenario defines the original tour. Priority is descriptive metadata. Product ID is omitted because the source data provides no defensible destination mapping.

The existing demand data records product/store demand without a delivery-stop mapping. The shipment Random Forest predicts from individual origin/destination shipments and associated features. It has no stop-order, travel-time-by-leg, schedule, or multi-stop outcome labels. Both predictors remain independent of the optimizer. A future integration would need explicit store-to-stop mappings and observed route sequences, arrival timestamps and outcomes before using forecasts or validation-calibrated delay risk.

## Travel and fitness

By default, Haversine computes great-circle distances on a sphere of radius 6,371.0088 km. Its geographic matrix is symmetric. The demo multiplies each distance by 1.25 to obtain an illustrative driving distance in kilometres. Travel hours equal estimated kilometres divided by the configured constant speed. Transportation cost in INR equals kilometres multiplied by the configured INR/km. Map links are straight lines connecting stops. The factor and speed are assumptions for the simulation and have no traffic or road-network calibration.

The API accepts directed or symmetric `road_distance_km` and `travel_time_hours` matrices, independently. Supply full square arrays in warehouse-first, destination-input order. Entries are finite, nonnegative and have zero diagonals. The first index is departure and the second is arrival. Geometry on the map is still a stop-to-stop illustration. The dashboard currently builds geographic scenarios. Matrix submission is through the API.

The objective is minimized:

```text
fitness = w_distance × distance_km / 100
        + w_time     × travel_hours / 4
        + w_cost     × cost_inr / 2000
```

The references are fixed at 100 km, 4 hours and INR 2,000 for every candidate, baseline and scenario. Default weights are 0.45, 0.35 and 0.20 and sum to one. With a constant speed and rate, all three terms are proportional to distance, so the default objective is distance minimization. In a degenerate setup where only the cost term has weight and the rate is zero, fitness is flat. A supplied travel-time matrix can make time a distinct objective. Cost remains proportional to distance and delay risk is disabled. When a weighted trade-off is present, lower fitness can accompany longer distance or higher cost. Savings are signed estimates computed as original minus optimized.

## Algorithms and constraints

- **Original** scores the input ordering. An API caller can override it with a permutation of destination IDs using `original_sequence`.
- **Nearest Neighbour** chooses the shortest outgoing distance to an unvisited stop at each step. Ties choose the earliest input index. It then returns to the warehouse.
- **Genetic Algorithm** represents each chromosome as a permutation of destination indices. The warehouse is implicit in the chromosome and prepended/appended when scoring. Both baseline permutations seed the population. The remaining candidates are random permutations. Three-way tournament selection picks the lowest-fitness sampled parent, or samples the full population when fewer than three candidates exist. Order crossover keeps one parent's slice and fills the remaining places in the other parent's cyclic order. Swap mutation exchanges two positions. Elitism copies the best candidates unchanged. The search retains the best seen and stops after the generation budget. The seed controls all random choices. The returned fitness cannot exceed either baseline's fitness.
- **Exact** uses Held–Karp dynamic programming on the same weighted edge costs for at most 10 destinations. The GA gap is 100 × (GA fitness / exact fitness − 1). If both are zero, the gap is reported as zero. If only the optimum is zero, the relative gap is undefined.

Every tour is a single load of deliveries and demand declines after each drop. Checking the sum against vehicle capacity therefore suffices. Over-capacity requests are rejected. The model has no pickups, split delivery, time windows, service times, or multi-vehicle assignment. It supports 3–15 destinations. The maximum population is 200, the maximum generation count is 400, their product is capped at 40,000, and two optimizations can run concurrently per server process.

Distance matrix construction and nearest neighbour each take O(n²) time. GA scoring, crossover and mutation are O(n) per candidate, with an O(P log P) elite sort per generation. With P candidates and G generations, runtime is O(G(Pn + P log P)), and working space is O(Pn + n² + G). Held–Karp uses O(n²2ⁿ) time and O(n2ⁿ) space. Convergence includes generation zero. Best-so-far fitness is nonincreasing. Average fitness describes each generation and may rise after mutation or crossover.

## Run and evaluate

From the project root on Windows, create a virtual environment with `py -m venv .venv`, install `requirements-dev.txt` with `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`, then run `.\start_backend.bat`. In a second terminal, serve the dashboard with `.\.venv\Scripts\python.exe -m http.server 5500` and open `http://127.0.0.1:5500/landing.html`. Log in and select **Route Optimization**. Select a warehouse/scenario, load it, then optimize. Click a numbered marker to see the stop's demand and its positions in both tours. The CSV contains per-algorithm summaries and sequences. JSON includes all locations, metrics, model assumptions and fitness history.

The API exposes GET `/route/health`, `/route/config`, and `/route/sample?scenario=central-5`. POST `/route/optimize` and `/route/compare` return the same comparison contract for a valid sample or custom problem. Sequence entries are zero-based indices into `locations`, with zero for the warehouse. See Swagger at `http://127.0.0.1:8000/docs`.

Run `python -m pytest -q` with the virtual environment activated. Run `python benchmark_routes.py` to evaluate the first 5, 8, 10 and 15 locations of the same NCR scenario with seeds 7, 21, 42, 84 and 123. Runtime measures each algorithm and its metrics in isolation from the HTTP request, matrix generation, and plotting.

## Measured benchmark results

| Stops | Original km | Greedy km | Mean GA km | Mean GA fitness ± SD | Mean GA runtime | Distance saved | Mean exact gap |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 159.87 | 135.76 | 113.38 | 1.0230 ± 0.0000 | 789 ms | 29.08% | 0.00% |
| 8 | 298.78 | 166.97 | 164.66 | 1.4857 ± 0.0000 | 789 ms | 44.89% | 0.00% |
| 10 | 362.22 | 212.21 | 201.98 | 1.8224 ± 0.0993 | 793 ms | 44.24% | 9.33% |
| 15 | 517.61 | 254.23 | 251.59 | 2.2700 ± 0.0194 | 805 ms | 51.39% | — |

The 5- and 8-stop tours reached the exact solution under all five seeds. The 10-stop runs varied across seeds. The best matched the exact fitness at 1.6669, while the mean gap was 9.33%. The greedy route accounts for much of the distance reduction in the 15-stop case. Convergence plots show the mean of the five best-so-far histories and the mean of the five population-average histories. See the [per-run data](results/benchmark_runs.csv), [summary](results/benchmark_summary.csv), [convergence](results/convergence.png), [fitness comparison](results/algorithm_comparison.png), [distance comparison](results/route_distance_comparison.png), and [environment](results/environment.txt).

These are five-seed measurements on one synthetic geometry per stop count. Future work includes measured road networks, time-dependent service models, multi-vehicle capacity routing and evaluation on actual operational data.
