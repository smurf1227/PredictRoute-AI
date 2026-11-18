from itertools import permutations

import numpy as np
import pytest

from route_data import distance_matrix, haversine, load_scenarios
from route_optimizer import (
    GAConfig, compare_routes, exact_route, nearest_neighbour, next_generation, order_crossover,
    route_totals, swap_mutation, tournament,
)


def test_haversine_and_matrix():
    assert haversine(0, 0, 0, 1) == pytest.approx(111.195, abs=0.001)
    assert haversine(0, 0, 0, 180) == pytest.approx(20015.114, abs=0.001)
    matrix = distance_matrix([(0, 179), (0, -179), (1, 0)])
    np.testing.assert_allclose(matrix, matrix.T)
    np.testing.assert_array_equal(matrix.diagonal(), 0)
    assert matrix[0, 1] == pytest.approx(222.390, abs=0.001)


def test_operators_and_elitism():
    population = np.array([[1, 2, 3, 4], [4, 3, 2, 1], [2, 4, 1, 3]])
    scores = np.array([3, 1, 2])
    rng = np.random.default_rng(9)
    np.testing.assert_array_equal(tournament(population, scores, rng), population[1])
    for _ in range(10):
        child = order_crossover(population[0], population[1], rng)
        assert sorted(child) == [1, 2, 3, 4]
        previous = child.copy()
        swap_mutation(child, rng)
        assert sorted(child) == [1, 2, 3, 4]
        assert np.count_nonzero(previous != child) == 2
    children = next_generation(population, scores, GAConfig(3, 1, 1, 1, 1), rng)
    np.testing.assert_array_equal(children[0], population[1])


@pytest.mark.parametrize("scenario", list(load_scenarios()))
@pytest.mark.parametrize("seed", [0, 42])
def test_comparison_is_reproducible_and_feasible(scenario, seed):
    data = load_scenarios()[scenario]
    points = [data["warehouse"], *data["destinations"]]
    distance = distance_matrix([(p["latitude"], p["longitude"]) for p in points])
    original = list(range(1, len(points)))
    args = distance, distance / 30, 20, (0.45, 0.35, 0.2), original, GAConfig(2, 3, 1, 1, 1, seed)
    result = compare_routes(*args)
    assert result["convergence"] == compare_routes(*args)["convergence"]
    ga = result["genetic_algorithm"]
    for key in ("original", "nearest_neighbour", "genetic_algorithm"):
        sequence = result[key]["sequence"]
        assert sequence[0] == sequence[-1] == 0
        assert sorted(sequence[1:-1]) == original
    assert ga["fitness"] <= min(result["original"]["fitness"], result["nearest_neighbour"]["fitness"])
    km = ga["distance_km"]
    assert ga["fitness"] == pytest.approx(0.45 * km / 100 + 0.35 * km / 30 / 4 + 0.2 * km * 20 / 2000)
    assert len(result["convergence"]) == 4
    assert all(row["best"] <= row["average"] for row in result["convergence"])
    assert result["convergence"][-1]["best"] == ga["fitness"]
    if result["exact"]:
        assert result["optimality_gap_pct"] >= 0
        assert result["exact"]["fitness"] <= ga["fitness"] + 1e-12


def test_exact_matches_brute_force_on_asymmetric_graph():
    matrix = np.random.default_rng(3).integers(1, 90, size=(6, 6))
    routes = list(permutations(range(1, 6)))
    assert route_totals(matrix, exact_route(matrix))[0] == min(route_totals(matrix, routes))


def test_nearest_neighbour_and_flat_fitness():
    matrix = np.array([[0, 9, 1, 3], [1, 0, 4, 9], [3, 5, 0, 1], [4, 2, 5, 0]])
    np.testing.assert_array_equal(nearest_neighbour(matrix), [2, 3, 1])
    zeros = np.zeros((4, 4))
    result = compare_routes(zeros, zeros, 0, (0.45, 0.35, 0.2), [1, 2, 3], GAConfig(2, 1, 0, 0, 1))
    assert result["savings"]["distance_pct"] is None
    assert result["optimality_gap_pct"] == 0
    assert result["genetic_algorithm"]["fitness"] == 0
