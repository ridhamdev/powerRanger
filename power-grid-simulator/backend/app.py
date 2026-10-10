"""
Flask REST API for Power Grid Failure, Load Redistribution & Recovery Simulator
"""

import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from flask import Flask, request, jsonify
from flask_cors import CORS
from simulation import manager

app = Flask(__name__)
CORS(app)  # Enable CORS for local React frontend communication


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(e):
    return jsonify({"error": str(e)}), getattr(e, "code", 500)


@app.route("/api/network", methods=["GET"])
def get_network():
    """Returns nodes, connections, current statuses, allocated flows, and simulation state."""
    return jsonify(manager.get_state()), 200


@app.route("/api/elements", methods=["POST"])
def add_element():
    """Adds a new node to the grid."""
    data = request.get_json(silent=True) or {}
    node_id_val = data.get("id")
    node_type_val = data.get("type")
    
    if not node_id_val or not node_type_val:
        return jsonify({"error": "Fields 'id' and 'type' are required."}), 400

    node_id = str(node_id_val)
    node_type = str(node_type_val)
    name = str(data.get("name") or node_id)

    try:
        capacity = float(data.get("capacity", 0.0))
        demand = float(data.get("demand", 0.0))
        priority = data.get("priority")
        if priority is not None:
            priority = int(priority)
        x = float(data.get("x", 200.0))
        y = float(data.get("y", 200.0))

        node = manager.grid.add_node(
            node_id=node_id,
            name=name,
            node_type=node_type,
            capacity=capacity,
            demand=demand,
            priority=priority,
            x=x,
            y=y
        )
        # Re-run optimization with new element
        manager.optimize()
        return jsonify({"message": f"Node '{node.id}' added.", "state": manager.get_state()}), 201
    except (ValueError, KeyError) as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/elements/<string:node_id>", methods=["PATCH"])
def update_element(node_id):
    """Updates editable properties of an existing node."""
    data = request.get_json(silent=True) or {}
    try:
        manager.grid.update_node(node_id, **data)
        manager.optimize()
        return jsonify({"message": f"Node '{node_id}' updated.", "state": manager.get_state()}), 200
    except KeyError:
        return jsonify({"error": f"Node '{node_id}' not found."}), 404
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/elements/<string:node_id>", methods=["DELETE"])
def delete_element(node_id):
    """Deletes a node and its incident connections."""
    try:
        manager.grid.delete_node(node_id)
        manager.optimize()
        return jsonify({"message": f"Node '{node_id}' and incident connections deleted.", "state": manager.get_state()}), 200
    except KeyError:
        return jsonify({"error": f"Node '{node_id}' not found."}), 404


@app.route("/api/connections", methods=["POST"])
def add_connection():
    """Adds a directed connection between two existing nodes."""
    data = request.get_json(silent=True) or {}
    conn_id = data.get("id")
    source = data.get("source")
    destination = data.get("destination")

    if not conn_id or not source or not destination:
        return jsonify({"error": "Fields 'id', 'source', and 'destination' are required."}), 400

    try:
        capacity = float(data.get("capacity", 0.0))
        cost = float(data.get("cost", 0.0))

        conn = manager.grid.add_connection(
            conn_id=conn_id,
            source=source,
            destination=destination,
            capacity=capacity,
            cost=cost
        )
        manager.optimize()
        return jsonify({"message": f"Connection '{conn.id}' added.", "state": manager.get_state()}), 201
    except KeyError as err:
        return jsonify({"error": str(err)}), 404
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/connections/<string:conn_id>", methods=["PATCH"])
def update_connection(conn_id):
    """Updates properties of an existing connection."""
    data = request.get_json(silent=True) or {}
    try:
        manager.grid.update_connection(conn_id, **data)
        manager.optimize()
        return jsonify({"message": f"Connection '{conn_id}' updated.", "state": manager.get_state()}), 200
    except KeyError:
        return jsonify({"error": f"Connection '{conn_id}' not found."}), 404
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/connections/<string:conn_id>", methods=["DELETE"])
def delete_connection(conn_id):
    """Deletes a connection."""
    try:
        manager.grid.delete_connection(conn_id)
        manager.optimize()
        return jsonify({"message": f"Connection '{conn_id}' deleted.", "state": manager.get_state()}), 200
    except KeyError:
        return jsonify({"error": f"Connection '{conn_id}' not found."}), 404


@app.route("/api/simulate/optimize", methods=["POST"])
def simulate_optimize():
    """Executes fresh optimization on current topology."""
    state = manager.optimize()
    return jsonify(state), 200


@app.route("/api/simulate/failure", methods=["POST"])
def simulate_failure():
    """Simulates component failure and executes autonomous recovery."""
    data = request.get_json(silent=True) or {}
    comp_id = data.get("id")
    comp_type = data.get("type", "node")  # 'node' or 'connection'

    if not comp_id:
        return jsonify({"error": "Field 'id' is required."}), 400

    try:
        state = manager.handle_failure(comp_id, comp_type)
        return jsonify(state), 200
    except KeyError as err:
        return jsonify({"error": str(err)}), 404
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/simulate/restore", methods=["POST"])
def simulate_restore():
    """Restores a failed component and recalculates optimal routing."""
    data = request.get_json(silent=True) or {}
    comp_id = data.get("id")
    comp_type = data.get("type", "node")

    if not comp_id:
        return jsonify({"error": "Field 'id' is required."}), 400

    try:
        state = manager.handle_restore(comp_id, comp_type)
        return jsonify(state), 200
    except KeyError as err:
        return jsonify({"error": str(err)}), 404
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/simulate/reset", methods=["POST"])
def simulate_reset():
    """Restores the reference example network and resets history."""
    state = manager.reset()
    return jsonify(state), 200


@app.route("/api/mst", methods=["GET"])
def get_kruskal_mst():
    """Academic Kruskal's algorithm demonstration endpoint."""
    return jsonify(manager.grid.kruskal_mst()), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
