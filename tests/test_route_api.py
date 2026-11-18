import pytest
from fastapi.testclient import TestClient

from ml_backend import app

client = TestClient(app)


def sample():
    return client.get("/route/sample").json()


def test_endpoints_and_json_contract():
    config = client.get("/route/config").json()
    assert len(config["scenarios"]) == 3
    assert client.get("/route/health").json()["status"] == "ok"
    assert client.get("/route/sample?scenario=missing").status_code == 404
    for scenario in config["scenarios"]:
        data = client.get("/route/sample", params={"scenario": scenario["id"]}).json()
        data["parameters"]["generations"] = 2
        for endpoint in ("optimize", "compare"):
            response = client.post(f"/route/{endpoint}", json=data)
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["model"]["label"] == "Geographic distance-based simulation"
            assert len(result["locations"]) == scenario["destination_count"] + 1
            assert len(result["convergence"]) == 3
            assert result["demand"] <= result["capacity"]


@pytest.mark.parametrize("change", [
    {"capacity": 1}, {"speed_kph": 0}, {"weights": {"distance": 0}},
    {"original_sequence": ["D1"]}, {"road_distance_km": [[0]]},
    {"parameters": {"population_size": 2}}, {"parameters": {"population_size": 200, "generations": 400}},
    {"destinations": []}, {"warehouse": {"id": "W", "name": "Depot", "latitude": 91, "longitude": 0}},
])
def test_invalid_requests(change):
    assert client.post("/route/optimize", json={**sample(), **change}).status_code == 422


def test_duplicate_and_missing_values():
    data = sample()
    data["destinations"][1]["id"] = data["destinations"][0]["id"]
    assert client.post("/route/optimize", json=data).status_code == 422
    data = sample()
    del data["destinations"][0]["demand"]
    assert client.post("/route/optimize", json=data).status_code == 422


def test_external_matrices_and_explicit_baseline():
    data = sample()
    size = len(data["destinations"]) + 1
    data.update(
        road_distance_km=[[0 if i == j else 1 for j in range(size)] for i in range(size)],
        travel_time_hours=[[0 if i == j else (j - i) % size for j in range(size)] for i in range(size)],
        original_sequence=[stop["id"] for stop in reversed(data["destinations"])],
    )
    response = client.post("/route/optimize", json=data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["original"]["sequence"] == [0, 5, 4, 3, 2, 1, 0]
    assert result["exact"]["travel_hours"] == size
    assert result["original"]["distance_km"] == size


def test_existing_api_compatibility():
    paths = client.get("/openapi.json").json()["paths"]
    for endpoint in (
        "/products", "/history", "/summary", "/forecast", "/delay/schema",
        "/delay/sample", "/delay/upload", "/delay/train", "/delay/predict",
        "/delay/metrics", "/retrain", "/export/forecast_csv", "/export/plot_png",
    ):
        assert endpoint in paths
    assert client.get("/products").status_code == 200
    assert client.get("/history?product=P0001&limit=7").status_code == 200
    forecast = client.get("/forecast?product=P0001&steps=3")
    assert forecast.status_code == 200, forecast.text
    assert len(forecast.json()["dates"]) == 3
    shipments = client.get("/delay/sample?n=1").json()["rows"]
    assert client.post("/delay/train").status_code == 200
    prediction = client.post("/delay/predict", json=shipments[0])
    assert prediction.status_code == 200, prediction.text
