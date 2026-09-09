# Agentic CloudOps

An autonomous Site Reliability Engineering (SRE) system that detects anomalies in microservices using machine learning and automatically resolves them using a multi-agent LLM pipeline.

## Features

- **Anomaly Detection:** Uses an **Isolation Forest** model to monitor live telemetry (CPU, Memory, Restarts, Error Rate) and flag anomalies dynamically without rigid static thresholds.
- **Multi-Agent Pipeline:** Built with **LangGraph** and **Google Gemini**, the system routes incidents through a specialized team of AI agents:
  - 🩺 **Diagnosis Agent:** Analyzes telemetry to find the root cause of the incident.
  - 🛠️ **Remediation Agent:** Proposes Kubernetes-style resolutions (e.g., scale up, restart, rollback).
  - ⚖️ **Critic Agent:** Reviews proposals for safety and effectiveness.
- **Loop Controller & Consensus:** Agents debate until consensus is reached or the maximum round cap is hit.
- **Approval Gate (Human-in-the-Loop):** High-risk actions (like rollbacks) or low-confidence decisions are automatically escalated to a human operator for approval.
- **Live React Dashboard:** A beautiful frontend providing real-time telemetry charts, an agent reasoning feed, and a queue for operator escalations.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, LangChain, LangGraph
- **Frontend:** React, TypeScript, Vite, Chart.js
- **Machine Learning:** scikit-learn (Isolation Forest)
- **Data/Cache:** PostgreSQL, Redis
- **LLM:** Google Gemini 

## Prerequisites

- Python 3.10+
- Node.js 18+
- Podman or Docker (for PostgreSQL & Redis)
- A Google Gemini API Key

## Setup

### 1. Environment & Keys
Create a `.env` file in the root directory and add your API key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```
*(You can also provide a comma-separated list of keys as `GEMINI_API_KEYS` to use automatic key rotation if you run into rate limits).*

### 2. Infrastructure Services
Start the required PostgreSQL and Redis containers using Docker or Podman:
```bash
docker-compose up -d
```

### 3. Backend Setup
Set up the Python virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the backend server (this will automatically seed baseline telemetry for the ML model on first run):
```bash
make backend
```
The FastAPI backend will run on `http://localhost:8000`.

### 4. Frontend Setup
In a new terminal window, install the Node dependencies and start the React app:
```bash
cd frontend
npm install
make frontend
```
The frontend will run on `http://localhost:5173`.

## Fault Injection Testing

The project includes a built-in fault injector to simulate production incidents and trigger the AI agents. You can run these using the `Makefile` shortcuts:

- `make inject-cpu` — Simulates a CPU spike.
- `make inject-memory` — Simulates a memory leak.
- `make inject-crash` — Simulates a crash loop (high error rate & restarts).

*By default, faults are injected into `payment-service`. You can target other services like this: `make inject-cpu SERVICE=auth-service`.*

### Cleanup & Reset
- `make clean` — Clears active faults, returning telemetry to normal.
- `make flush-cache` — Clears the Gemini LLM reasoning cache (the system caches LLM outputs for 1 hour to save API quota).
- `make reset` — Fully cleans faults and flushes the cache.

## License
MIT License
