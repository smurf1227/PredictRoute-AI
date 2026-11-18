"""Permutation GA and baselines for a single closed delivery tour."""
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

import numpy as np

REFERENCES = (100.0, 4.0, 2000.0)  # km, hours, INR
EXACT_LIMIT = 10


@dataclass(frozen=True)
class GAConfig:
    population_size: int = 100
    generations: int = 200
    mutation_probability: float = 0.10
    crossover_probability: float = 0.80
    elite_count: int = 5
    seed: int = 42


def tournament(population, fitness, rng):
    competitors = rng.choice(len(population), min(3, len(population)), replace=False)
    return population[competitors[np.argmin(fitness[competitors])]]


def order_crossover(first, second, rng):
    start, end = sorted(rng.choice(len(first), 2, replace=False))
    end += 1
    child = np.empty_like(first)
    child[start:end] = first[start:end]
    retained = set(first[start:end])
    remainder = [gene for gene in np.concatenate((second[end:], second[:end])) if gene not in retained]
    child[end:] = remainder[:len(first) - end]
    child[:start] = remainder[len(first) - end:]
    return child


def swap_mutation(chromosome, rng):
    first, second = rng.choice(len(chromosome), 2, replace=False)
    chromosome[first], chromosome[second] = chromosome[second], chromosome[first]


def next_generation(population, fitness, config, rng):
    ranking = np.argsort(fitness, kind="stable")
    children = [population[i].copy() for i in ranking[:config.elite_count]]
    while len(children) < config.population_size:
        first = tournament(population, fitness, rng)
        if rng.random() < config.crossover_probability:
            child = order_crossover(first, tournament(population, fitness, rng), rng)
        else:
            child = first.copy()
        if rng.random() < config.mutation_probability:
            swap_mutation(child, rng)
        children.append(child)
    return np.asarray(children)


def route_totals(matrix, chromosomes):
    chromosomes = np.atleast_2d(chromosomes)
    closed = np.pad(chromosomes, ((0, 0), (1, 1)))
    return matrix[closed[:, :-1], closed[:, 1:]].sum(axis=1)


def nearest_neighbour(distance):
    remaining = set(range(1, len(distance)))
    order = [0]
    while remaining:
        current = order[-1]
        stop = min(remaining, key=lambda i: (distance[current, i], i))
        order.append(stop)
        remaining.remove(stop)
    return np.asarray(order[1:])


def exact_route(edge_fitness):
    """Held–Karp dynamic programming, including the edge back to the depot."""
    count = len(edge_fitness) - 1

    @lru_cache(maxsize=None)
    def best(mask, current):
        if mask == 0:
            return edge_fitness[current, 0], 0
        return min(
            (edge_fitness[current, stop] + best(mask ^ bit, stop)[0], stop)
            for stop in range(1, count + 1)
            if mask & (bit := 1 << (stop - 1))
        )

    mask = (1 << count) - 1
    order = [0]
    while mask:
        _, stop = best(mask, order[-1])
        order.append(stop)
        mask ^= 1 << (stop - 1)
    return np.asarray(order[1:])


def genetic_algorithm(edge_fitness, seeds, config):
    rng = np.random.default_rng(config.seed)
    population = np.asarray([*seeds, *(
        rng.permutation(seeds[0]) for _ in range(config.population_size - len(seeds))
    )])
    convergence = []
    best_score = float("inf")
    for generation in range(config.generations + 1):
        fitness = route_totals(edge_fitness, population)
        index = int(np.argmin(fitness))
        if fitness[index] < best_score:
            best_score = fitness[index]
            best_order = population[index].copy()
        convergence.append({
            "generation": generation, "best": float(best_score), "average": float(fitness.mean()),
        })
        if generation < config.generations:
            population = next_generation(population, fitness, config, rng)
    return best_order, convergence


def compare_routes(distance, time, rate, weights, original, config):
    edge_fitness = (
        distance * weights[0] / REFERENCES[0]
        + time * weights[1] / REFERENCES[1]
        + distance * rate * weights[2] / REFERENCES[2]
    )

    def describe(order, start):
        km = float(route_totals(distance, order)[0])
        return {
            "sequence": [0, *order.tolist(), 0],
            "distance_km": km,
            "travel_hours": float(route_totals(time, order)[0]),
            "cost": km * rate,
            "fitness": float(route_totals(edge_fitness, order)[0]),
            "runtime_ms": (perf_counter() - start) * 1000,
        }

    start = perf_counter()
    original = np.asarray(original, dtype=int)
    original_result = describe(original, start)
    start = perf_counter()
    greedy = nearest_neighbour(distance)
    greedy_result = describe(greedy, start)
    start = perf_counter()
    order, history = genetic_algorithm(edge_fitness, (original, greedy), config)
    ga = describe(order, start)
    exact = gap = None
    if len(original) <= EXACT_LIMIT:
        start = perf_counter()
        exact = describe(exact_route(edge_fitness), start)
        if exact["fitness"] > 0:
            gap = max(0.0, (ga["fitness"] / exact["fitness"] - 1) * 100)
        elif ga["fitness"] == 0:
            gap = 0.0

    saved = original_result["distance_km"] - ga["distance_km"]
    return {
        "original": original_result, "nearest_neighbour": greedy_result,
        "genetic_algorithm": ga, "exact": exact, "optimality_gap_pct": gap,
        "convergence": history,
        "savings": {
            "distance_km": saved,
            "distance_pct": 100 * saved / original_result["distance_km"] if original_result["distance_km"] else None,
            "travel_hours": original_result["travel_hours"] - ga["travel_hours"],
            "cost": original_result["cost"] - ga["cost"],
        },
    }
