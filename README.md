# Smart Demand Forecasting and Shipment Delay Prediction

A local web application for inventory demand forecasting and shipment-delay prediction. The project combines a static HTML dashboard with a FastAPI backend that reads CSV data, forecasts product demand, and classifies whether a shipment is likely to be delayed.

## Features

- Product history and summary statistics
- Daily demand forecasting with SARIMAX/ARIMA
- Optional Prophet forecasting when `prophet` is installed
- Forecast confidence intervals and CSV/PNG exports
- Shipment-delay model training with a Random Forest classifier
- Shipment-delay prediction with categorical and numeric features
- Interactive API documentation through FastAPI Swagger UI
- PredictRoute AI for single-vehicle route planning, with a Genetic Algorithm, greedy baseline and exact comparison on small tours

## Project Files

| File | Purpose |
| --- | --- |
| `index.html` | Forecast, shipment-delay and route optimization dashboard |
| `DeliveryRoutes.csv` | Three synthetic Delhi NCR routing scenarios |
| `route_api.py`, `route_optimizer.py`, `route_data.py` | Routing API, algorithms and data model |
| `landing.html` | Application landing page |
| `login.html` | Dashboard login page |
| `ml_backend.py` | FastAPI backend and machine-learning endpoints |
| `ProjectMLDataSet.csv` | Product demand history |
| `ShipmentDelays.csv` | Shipment-delay training data |
| `ML_ProjectPPT.pdf` | Project presentation |
| `Project_report.pdf` | Project report |

## Requirements

- Python 3.10 or newer
- A modern web browser
- Git

The backend uses FastAPI, Uvicorn, pandas, NumPy, statsmodels, scikit-learn, and matplotlib. Prophet is optional and is required only for the Prophet forecast option.

## Clone and Run

Select **Code → Download ZIP** on GitHub and extract it, or copy the HTTPS clone URL from **Code** and run these commands. Open a terminal in the extracted project folder if you downloaded the ZIP.

```bash
git clone "https://github.com/smurf1227/PredictRoute-AI.git" PredictRoute-AI
cd PredictRoute-AI
```

Create and activate a virtual environment.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, allow it for the current terminal session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the backend in the first terminal:

```bash
python -m uvicorn ml_backend:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in a second terminal. Activate the virtual environment in that terminal first, then run:

```bash
python -m http.server 5500 --bind 127.0.0.1
```

Open the application at [http://127.0.0.1:5500/landing.html](http://127.0.0.1:5500/landing.html). The dashboard is available at [http://127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html), and API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Stop either server with `Ctrl+C`.

## Quick Start (Existing Checkout)

For a fresh Windows checkout, install Python and run the following from PowerShell. The launcher uses the project directory and the local virtual environment automatically.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\start_backend.bat
```

In another window, run `.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1`.

Open PowerShell in the project directory:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn ml_backend:app --host 127.0.0.1 --port 8000 --reload
```

In a second PowerShell window, serve the frontend:

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Open the application at [http://127.0.0.1:5500/landing.html](http://127.0.0.1:5500/landing.html). The dashboard is available at [http://127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html), and API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

On first use, select **Create Account** on the login page to create a local demo account. The HTML dashboard expects the API at `http://127.0.0.1:8000`.

## Troubleshooting

### `No module named uvicorn`

This usually means the virtual environment is not active or dependencies were installed into a different Python installation. Activate `.venv` and install/run Uvicorn through the same interpreter:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install uvicorn
python -m uvicorn ml_backend:app --host 127.0.0.1 --port 8000
```

### PowerShell activation is blocked

Run this once in the current PowerShell window, then activate `.venv`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## API Endpoints

### Demand forecasting

- `GET /products` - list available products and categories
- `GET /history?product=<name>` - return historical daily demand
- `GET /summary?product=<name>` - return average, minimum, maximum, and trend
- `GET /forecast?product=<name>&model=arima&steps=7` - generate a forecast
- `GET /export/forecast_csv` - download forecast data as CSV
- `GET /export/plot_png` - download a forecast plot as PNG
- `POST /retrain?product=<name>` - clear the cached model for a product

### Shipment-delay prediction

- `GET /delay/schema` - view required fields and examples
- `GET /delay/sample` - return sample shipment records
- `POST /delay/train` - train the Random Forest model
- `POST /delay/predict` - predict delay probability for one shipment
- `GET /delay/metrics` - view trained-model feature importance
- `POST /delay/upload` - append shipment records to the CSV dataset

The shipment dataset uses these fields:

`Origin`, `Destination`, `Carrier`, `WeatherCondition`, `DistanceKM`, `ExpectedDeliveryDays`, `Holiday`, `CustomsClearanceTime`, `HandlingTimeWarehouse`, and `Delay`.

## Configuration

### PredictRoute AI

Log in, open **Route Optimization**, pick a warehouse/scenario, click **Load Sample Scenario**, and click **Optimize Route**. Editable stop rows define the original order. Compare distance, estimated time and cost, weighted fitness and runtime. Open a map marker to see its visit order, view convergence and download CSV or JSON. The map and charts use external Leaflet, OpenStreetMap and Chart.js assets.

The three examples are synthetic. This geographic simulation estimates driving distance as 1.25 × Haversine and draws straight lines between stops. At constant speed and INR/km, the default fitness is equivalent to minimizing distance.

- `GET /route/config` and `GET /route/health` expose defaults, scenario metadata and router status.
- `GET /route/sample?scenario=central-5` returns a ready-to-submit request. Other scenarios are `west-8` and `ncr-15`.
- `POST /route/optimize` and `POST /route/compare` accept the route request and return the comparison, sequences, convergence and exact gap when available.

Run `python -m pytest -q` and `python benchmark_routes.py` in the activated environment. See [routing documentation](ROUTE_OPTIMIZATION_DOCUMENTATION.md) for the model and benchmark method, and [viva preparation](VIVA_PREPARATION.md) for a walkthrough.

### Existing dataset settings

The backend reads these environment variables when provided:

- `CSV_PATH` - path to the demand dataset; defaults to `ProjectMLDataSet.csv`
- `DELAY_CSV_PATH` - path to the shipment dataset; defaults to `ShipmentDelays.csv`

Example:

```powershell
$env:CSV_PATH = "ProjectMLDataSet.csv"
$env:DELAY_CSV_PATH = "ShipmentDelays.csv"
```

## Notes

- Train the shipment-delay model with `POST /delay/train` before calling `POST /delay/predict`.
- The backend enables CORS for local frontend access.
- Login and user authentication are currently handled by the static frontend and are not backed by a database or authentication service.

## Project origin

PredictRoute AI extends the [Smart Demand Forecasting and Shipment Delay Prediction project](https://github.com/Sanchitk99/Smart-Demand-Forecasting-and-Shipment-Delay-Prediction).
