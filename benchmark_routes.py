"""Reproduce the synthetic PredictRoute evaluation and charts."""
import csv
from dataclasses import replace
from pathlib import Path
import platform
from statistics import fmean, pstdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from route_data import DRIVING_FACTOR, distance_matrix, load_scenarios
from route_optimizer import GAConfig, compare_routes

SIZES = (5, 8, 10, 15)
SEEDS = (7, 21, 42, 84, 123)
METHODS = ("original", "nearest_neighbour", "genetic_algorithm")
LABELS = ("Original", "Nearest Neighbour", "Genetic Algorithm")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save(figure, output, filename):
    figure.tight_layout()
    figure.savefig(output / filename, dpi=150)
    plt.close(figure)


def main():
    output = Path(__file__).with_name("results")
    output.mkdir(exist_ok=True)
    scenario = load_scenarios()["ncr-15"]
    runs, summary = [], []
    histories = {}
    for count in SIZES:
        points = [scenario["warehouse"], *scenario["destinations"][:count]]
        assert sum(point["demand"] for point in points[1:]) <= scenario["capacity"]
        distance = DRIVING_FACTOR * distance_matrix([(p["latitude"], p["longitude"]) for p in points])
        results = [
            compare_routes(distance, distance / scenario["speed_kph"], scenario["cost_per_km"],
                           (0.45, 0.35, 0.20), list(range(1, count + 1)), replace(GAConfig(), seed=seed))
            for seed in SEEDS
        ]
        histories[count] = [result["convergence"] for result in results]
        for seed, result in zip(SEEDS, results):
            runs.append({
                "destinations": count, "seed": seed,
                **{f"{key}_{metric}": result[key][metric]
                   for key in METHODS for metric in ("distance_km", "travel_hours", "cost", "fitness", "runtime_ms")},
                "final_population_average_fitness": result["convergence"][-1]["average"],
                "distance_improvement_pct": result["savings"]["distance_pct"],
                "exact_fitness": result["exact"]["fitness"] if result["exact"] else None,
                "ga_optimality_gap_pct": result["optimality_gap_pct"],
            })
        scores = [r["genetic_algorithm"]["fitness"] for r in results]
        summary.append({
            "destinations": count, "runs": len(SEEDS), "best_ga_fitness": min(scores),
            "mean_ga_fitness": fmean(scores), "stddev_ga_fitness": pstdev(scores),
            "mean_final_population_fitness": fmean(h[-1]["average"] for h in histories[count]),
            **{f"mean_{key}_{metric}": fmean(r[key][metric] for r in results)
               for key in METHODS for metric in ("distance_km", "fitness", "runtime_ms")},
            "mean_distance_improvement_pct": fmean(r["savings"]["distance_pct"] for r in results),
            "mean_ga_optimality_gap_pct": fmean(r["optimality_gap_pct"] for r in results) if results[0]["exact"] else None,
        })

    write_csv(output / "benchmark_runs.csv", runs)
    write_csv(output / "benchmark_summary.csv", summary)
    (output / "environment.txt").write_text(
        f"Platform: {platform.platform()}\nCPU: {platform.processor() or 'Unavailable'}\n"
        f"Python: {platform.python_version()}\nNumPy: {np.__version__}\n"
        f"Matplotlib: {matplotlib.__version__}\nSeeds: {SEEDS}\n"
        "One process; wall-clock algorithm times exclude matrix construction and plotting.\n",
        encoding="utf-8",
    )

    figure, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for count, axis in zip(SIZES, axes.flat):
        for key, label in (("best", "Best so far"), ("average", "Population mean")):
            values = [[row[key] for row in history] for history in histories[count]]
            axis.plot(np.mean(values, axis=0), label=label)
        axis.set(title=f"{count} destinations", xlabel="Generation", ylabel="Fitness")
        axis.legend()
    save(figure, output, "convergence.png")

    for metric, title, filename in (
        ("fitness", "Weighted fitness (lower is better)", "algorithm_comparison.png"),
        ("distance_km", "Estimated route distance (km)", "route_distance_comparison.png"),
    ):
        figure, axis = plt.subplots(figsize=(9, 4.5))
        positions = np.arange(len(SIZES))
        for offset, (key, label) in enumerate(zip(METHODS, LABELS), start=-1):
            axis.bar(positions + offset * 0.24, [row[f"mean_{key}_{metric}"] for row in summary],
                     width=0.24, label=label)
        axis.set(xticks=positions, xticklabels=SIZES, xlabel="Destinations", ylabel=title)
        axis.legend()
        save(figure, output, filename)


if __name__ == "__main__":
    main()
