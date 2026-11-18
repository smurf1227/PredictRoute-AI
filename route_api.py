"""Validated routing endpoints for the existing FastAPI application."""
from copy import deepcopy
from math import isclose
from threading import BoundedSemaphore
from typing import Annotated

from fastapi import APIRouter, HTTPException
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from route_data import DRIVING_FACTOR, SIMULATION_LABEL, distance_matrix, load_scenarios
from route_optimizer import EXACT_LIMIT, GAConfig, REFERENCES, compare_routes

router = APIRouter(prefix="/route", tags=["Route optimization"])
scenarios = load_scenarios()
slots = BoundedSemaphore(2)
MatrixRow = Annotated[list[FiniteFloat], Field(max_length=16)]


class RouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Location(RouteModel):
    id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=100)
    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, le=180)


class Destination(Location):
    demand: int = Field(gt=0, le=1_000_000, strict=True)
    priority: str = Field(default="standard", min_length=1, max_length=30)


class Parameters(RouteModel):
    population_size: int = Field(default=100, ge=2, le=200, strict=True)
    generations: int = Field(default=200, ge=1, le=400, strict=True)
    mutation_probability: FiniteFloat = Field(default=0.10, ge=0, le=1)
    crossover_probability: FiniteFloat = Field(default=0.80, ge=0, le=1)
    elite_count: int = Field(default=5, ge=1, le=199, strict=True)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)

    @model_validator(mode="after")
    def validate_budget(self):
        if self.elite_count >= self.population_size:
            raise ValueError("Elite count must be smaller than population size")
        if self.population_size * self.generations > 40_000:
            raise ValueError("Population size × generations must be at most 40,000")
        return self


class Weights(RouteModel):
    distance: FiniteFloat = Field(default=0.45, ge=0, le=1)
    time: FiniteFloat = Field(default=0.35, ge=0, le=1)
    cost: FiniteFloat = Field(default=0.20, ge=0, le=1)

    @model_validator(mode="after")
    def validate_sum(self):
        if not isclose(self.distance + self.time + self.cost, 1, abs_tol=1e-9):
            raise ValueError("Distance, time and cost weights must sum to 1")
        return self


class RouteRequest(RouteModel):
    warehouse: Location
    destinations: list[Destination] = Field(min_length=3, max_length=15)
    capacity: int = Field(gt=0, le=1_000_000, strict=True)
    cost_per_km: FiniteFloat = Field(ge=0, le=100_000)
    speed_kph: FiniteFloat = Field(ge=1, le=200)
    parameters: Parameters = Field(default_factory=Parameters)
    weights: Weights = Field(default_factory=Weights)
    original_sequence: list[str] | None = Field(default=None, max_length=15)
    road_distance_km: list[MatrixRow] | None = Field(default=None, max_length=16)
    travel_time_hours: list[MatrixRow] | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def validate_problem(self):
        ids = {stop.id for stop in self.destinations}
        if len(ids) != len(self.destinations) or self.warehouse.id in ids:
            raise ValueError("Warehouse and destination IDs must be unique")
        if sum(stop.demand for stop in self.destinations) > self.capacity:
            raise ValueError("Total delivery demand exceeds vehicle capacity")
        if self.original_sequence is not None and (
            len(self.original_sequence) != len(ids) or set(self.original_sequence) != ids
        ):
            raise ValueError("Original sequence must contain every destination ID exactly once")
        size = len(ids) + 1
        for name in ("road_distance_km", "travel_time_hours"):
            matrix = getattr(self, name)
            if matrix is None:
                continue
            if len(matrix) != size or any(len(row) != size for row in matrix):
                raise ValueError(f"{name} must be {size} × {size} in warehouse/input order")
            for i, row in enumerate(matrix):
                if row[i] != 0 or any(value < 0 or value > 1_000_000 for value in row):
                    raise ValueError(f"{name} requires a zero diagonal and values in [0, 1000000]")
        return self


@router.get("/health")
def health():
    return {"status": "ok", "scenario_count": len(scenarios)}


@router.get("/config")
def config():
    return {
        "parameters": Parameters().model_dump(), "weights": Weights().model_dump(),
        "scenarios": [
            {"id": key, "warehouse": value["warehouse"], "destination_count": len(value["destinations"])}
            for key, value in scenarios.items()
        ],
        "min_destinations": 3, "max_destinations": 15, "exact_limit": EXACT_LIMIT,
        "references": dict(zip(("distance_km", "travel_hours", "cost_inr"), REFERENCES)),
        "driving_factor": DRIVING_FACTOR,
    }


@router.get("/sample", response_model=RouteRequest)
def sample(scenario: str = "central-5"):
    if scenario not in scenarios:
        raise HTTPException(404, "Unknown sample scenario")
    return deepcopy(scenarios[scenario])


def solve(request):
    points = [request.warehouse, *request.destinations]
    locations = [point.model_dump() for point in points]
    geographic = request.road_distance_km is None
    if geographic:
        distance = DRIVING_FACTOR * distance_matrix([(point.latitude, point.longitude) for point in points])
    else:
        distance = np.asarray(request.road_distance_km)
    supplied_time = request.travel_time_hours is not None
    time = np.asarray(request.travel_time_hours) if supplied_time else distance / request.speed_kph
    ids = {point.id: index for index, point in enumerate(points)}
    sequence = request.original_sequence or [point.id for point in request.destinations]
    result = compare_routes(
        distance, time, request.cost_per_km,
        (request.weights.distance, request.weights.time, request.weights.cost),
        [ids[stop] for stop in sequence], GAConfig(**request.parameters.model_dump()),
    )
    result.update(
        locations=locations,
        model={
            "label": SIMULATION_LABEL if geographic else "Supplied road-distance matrix",
            "distance_mode": "scaled_haversine" if geographic else "supplied_matrix",
            "time_mode": "supplied_matrix" if supplied_time else "constant_speed",
            "map_geometry": "Straight-line connections between stops",
            "driving_factor": DRIVING_FACTOR if geographic else None,
            "currency": "INR",
        },
        demand=sum(point.demand for point in request.destinations), capacity=request.capacity,
        parameters=request.parameters.model_dump(), weights=request.weights.model_dump(),
        vehicle={"cost_per_km": request.cost_per_km, "speed_kph": request.speed_kph},
    )
    return result


@router.post("/optimize")
@router.post("/compare")
def optimize(request: RouteRequest):
    if not slots.acquire(blocking=False):
        raise HTTPException(503, "Routing is busy. Try again shortly.")
    try:
        return solve(request)
    finally:
        slots.release()
