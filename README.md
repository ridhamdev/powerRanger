# Power Grid Simulator

> Power Grid Failure, Load Redistribution and Minimum-Cost Recovery Simulator

---

## Quick Start: Download & Run

### 1. Download / Clone the Code
```bash
git clone <repository-url>
cd power-grid-simulator
```
*(If you downloaded a `.zip` archive, simply extract it and `cd` into the `power-grid-simulator` folder).*

### 2. Run with One Command (Recommended)
Make sure you are inside the `power-grid-simulator` folder, then run:

```bash
./start.sh
```

**That's it!** The script will automatically:
1. Set up the Python virtual environment and start the Flask backend on `http://localhost:5000`.
2. Install frontend dependencies (if not already installed) and launch the React app on `http://localhost:3000`.
3. Open your default web browser to `http://localhost:3000`.
4. Press `Ctrl + C` in that terminal whenever you want to stop both servers cleanly.

---

### Alternative: Running Manually in Two Terminals

If you prefer to run the backend and frontend in separate terminals:

**Terminal 1 — Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```
*(Backend runs at http://localhost:5000)*

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```
*(Frontend runs at http://localhost:3000)*

---

## Project Purpose (In Short)

This is a discrete mathematics and graph theory project simulating a simplified electrical power distribution network as a directed flow network $G = (V, E)$. 

When a generator, substation, or transmission line fails, the backend automatically recalculates power flows across surviving lines, protects critical infrastructure (like hospitals) before lower-priority homes, and chooses alternative connections that minimize total installation cost.

---

## Project Structure

```
power-grid-simulator/
├── start.sh              <-- Single script to run the entire project
├── README.md             <-- Documentation
├── backend/
│   ├── app.py            <-- Flask REST API endpoints
│   ├── graph.py          <-- Graph model G=(V, E), node-splitting, BFS
│   ├── optimizer.py      <-- Lexicographic priority flow & cost optimization
│   ├── simulation.py     <-- Grid state manager & failure/recovery logic
│   ├── test_simulation.py<-- 12 unit tests verifying constraints & recovery
│   └── requirements.txt  <-- Python dependencies (Flask, Flask-CORS, Pytest)
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── NetworkCanvas.jsx     <-- Interactive canvas with draggable blocks
    │   │   ├── PropertiesPanel.jsx   <-- Inspector to view/edit properties and trigger failure
    │   │   ├── ElementPalette.jsx    <-- Add Node & Add Connection dialogs
    │   │   └── SimulationResults.jsx <-- Telemetry, metrics, and consumer status table
    │   ├── App.jsx                   <-- Top toolbar & application layout
    │   ├── api.js                    <-- Fetch client talking to Flask API
    │   └── styles.css                <-- Clean engineering workstation styling
    └── package.json
```

---

## How It Works (Viva & Theory Summary)

### 1. Graph Model
- Network represented as a directed graph $G = (V, E)$.
- Directional edges $A \to B$ mean power strictly flows from $A$ to $B$. Reverse flow is never assumed.
- **Node Types**:
  - **Generator**: Power source with max generation capacity.
  - **Transformer**: Intermediate substation with maximum throughput capacity. Maintained via node splitting ($T_{\text{in}} \to T_{\text{out}}$) to guarantee flow conservation ($\sum \text{in} = \sum \text{out} \le \text{capacity}$).
  - **Consumers**: Hospital (Priority 1), Factory (Priority 2), School (Priority 3), House (Priority 4).

### 2. Capacity vs. Installation Cost
- **Transmission Capacity**: A hard physical limit on an active line. Allocated flow can never exceed capacity.
- **Installation Cost**: A one-time capital cost paid when selecting/activating a connection in the grid. It is an optimization objective, not an ongoing per-unit fee.
- **Rule**: A lower installation cost must **never** justify reducing service to higher-priority consumers or violating capacity constraints.

### 3. Lexicographic Decision Order
When calculating flows or recovering from failures, the optimizer solves in this strict order:
1. Maximize service to higher-priority consumers (protect hospitals first).
2. Maximize total demand served among configurations with equal priority delivery.
3. Minimize total installation cost of the selected connections.
4. Prefer fewer topological changes when costs and service outcomes are identical.

### 4. Autonomous Failure & Recovery
1. When you disable a component, it is flagged as `FAILED`.
2. BFS reachability identifies affected downstream consumers.
3. Stale flows are cleared, surviving capacity is recalculated, and a fresh optimization runs on the remaining topology.
4. If full recovery is impossible, the system reports partial recovery honestly without displaying false success states.

---

## Running Tests

All 12 key algorithmic and constraint requirements are verified using pytest:

```bash
cd backend
pytest test_simulation.py -v
```

### Verified Test Cases:
1. Valid initial network satisfies all capacity constraints.
2. Connection flow never exceeds capacity.
3. Transformer throughput limits and flow conservation are strictly preserved.
4. Reverse flow on directed connections is prohibited.
5. Failed connections are bypassed through alternative directed routes.
6. Failed transformers cannot carry power.
7. Hospitals receive preferential allocation when supply is constrained.
8. Infeasible networks report unmet demand honestly.
9. Cheaper network configurations are selected when service outcomes are identical.
10. Restoring a component triggers fresh, non-cached optimization.
11. Repeated failures do not leave stale allocations.
12. Self-connections, negative capacities, negative costs, and duplicates are rejected.

---

## REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/network` | Returns grid topology, node statuses, flows, and telemetry report. |
| `POST` | `/api/elements` | Adds a network element. |
| `PATCH` | `/api/elements/<id>` | Updates editable properties (`capacity`, `demand`, `priority`, `name`). |
| `DELETE`| `/api/elements/<id>` | Deletes an element and its attached connections. |
| `POST` | `/api/connections` | Adds a directed line ($A \to B$) with capacity and installation cost. |
| `PATCH` | `/api/connections/<id>` | Updates line capacity, cost, or status. |
| `DELETE`| `/api/connections/<id>` | Deletes a connection. |
| `POST` | `/api/simulate/optimize` | Runs fresh optimization on current topology. |
| `POST` | `/api/simulate/failure` | Disables a node or line and runs autonomous recovery. |
| `POST` | `/api/simulate/restore` | Restores a failed component and recalculates optimal flow. |
| `POST` | `/api/simulate/reset` | Resets grid to the reference topology and clears event history. |
| `GET` | `/api/mst` | Demonstrates Kruskal's Minimum Spanning Tree for discrete math viva defense. |

---

## Known Limitations
- Abstract discrete graph simulation (flow conservation, node splitting, integer/float load units). It does not model AC physics (Kirchhoff's voltage laws, phase angles, reactive power, impedance).
- Fixed-charge network flow with discrete activation costs is NP-hard; the solver uses priority-staged capacity-constrained augmenting paths with backward edge elimination, designed for small-to-medium distribution graphs.
