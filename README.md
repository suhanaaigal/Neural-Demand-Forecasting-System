# Demand Intelligence

Demand Intelligence is a Streamlit workspace for demand forecasting, inventory
planning, SKU metadata, portfolio classification, pricing analysis, and reports.
The app uses the existing SQLite sales ledger and FastAPI forecasting service.

## Run locally

Install the Python dependencies if needed:

```powershell
python -m pip install streamlit fastapi uvicorn torch numpy pandas requests reportlab
```

Start the forecasting API in one terminal:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Start the dashboard in a second terminal from the repository root:

```powershell
python -m streamlit run dashboard.py
```

Open the Streamlit URL printed in the terminal (normally
`http://localhost:8501`). The dashboard has a collapsible sidebar with separate
workspaces for overview, forecasting, replenishment, the SKU registry, the
ABC/XYZ portfolio, pricing analytics, and reports/bulk operations.

Inventory balances, purchase orders, and external notification delivery are
not stored or connected by the current database/API; inventory recommendations
use the stock assumptions entered for a planning run.

## Deploy on Render

The root `render.yaml` Blueprint defines two web services: the FastAPI forecast
API and the Streamlit dashboard. In Render, create a Blueprint from this
repository and apply the `render.yaml` configuration. The dashboard service is
named `neural-demand-forecasting-system`, and calls the API service at
`neural-demand-forecasting-api.onrender.com`.

Both services use Render's free plan by default. Free services can sleep when
idle, so the first forecast request may take longer while the API starts. The
SQLite database is included as demo data; changes made to it on Render are not
persistent across service restarts or redeployments.
