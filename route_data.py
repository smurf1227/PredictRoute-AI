"""Synthetic scenarios and geographic travel estimates."""
import csv
from pathlib import Path

import numpy as np

SIMULATION_LABEL = "Geographic distance-based simulation"
EARTH_RADIUS_KM = 6371.0088
DRIVING_FACTOR = 1.25


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2
    a += np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def distance_matrix(coordinates):
    lat, lon = np.asarray(coordinates, dtype=float).T
    matrix = haversine(lat[:, None], lon[:, None], lat, lon)
    np.fill_diagonal(matrix, 0)
    return matrix


def load_scenarios():
    scenarios = {}
    with Path(__file__).with_name("DeliveryRoutes.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            scenario = scenarios.setdefault(row["Scenario ID"], {
                "warehouse": {
                    "id": row["Warehouse ID"], "name": row["Warehouse Name"],
                    "latitude": float(row["Warehouse Latitude"]),
                    "longitude": float(row["Warehouse Longitude"]),
                },
                "capacity": int(row["Vehicle Capacity"]),
                "cost_per_km": float(row["Transportation Cost Per KM"]),
                "speed_kph": float(row["Average Speed KPH"]),
                "destinations": [],
            })
            scenario["destinations"].append({
                "id": row["Destination ID"], "name": row["Destination Name"],
                "latitude": float(row["Destination Latitude"]),
                "longitude": float(row["Destination Longitude"]),
                "demand": int(row["Demand Quantity"]),
                "priority": row["Delivery Priority"],
            })
    return scenarios
