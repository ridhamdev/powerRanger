"""
Simulation Manager
Coordinates power grid state, failure events, autonomous recovery,
and historical telemetry.
"""

from typing import Dict, Any, Optional
from graph import PowerGridGraph
from optimizer import optimize_grid


class SimulationManager:
    """
    In-memory manager controlling the grid simulation lifecycle.
    """
    def __init__(self):
        self.grid = PowerGridGraph()
        self.history = []
        self.last_report = {}
        self.reset()

    def reset(self) -> Dict[str, Any]:
        """Resets the network to the default reference example network."""
        self.grid = PowerGridGraph()
        self.history = []

        # 1. Generators
        self.grid.add_node("G1", "Hydro Generator 1", "generator", capacity=80.0, x=100, y=180)
        self.grid.add_node("G2", "Solar Farm 2", "generator", capacity=50.0, x=100, y=380)

        # 2. Transformers
        self.grid.add_node("T1", "Main Substation", "transformer", capacity=90.0, x=350, y=180)
        self.grid.add_node("T2", "Backup Substation", "transformer", capacity=60.0, x=350, y=380)

        # 3. Consumers (Hospital=1, Factory=2, School=3, House=4)
        self.grid.add_node("H1", "City Hospital", "hospital", demand=25.0, priority=1, x=650, y=100)
        self.grid.add_node("F1", "Industrial Plant", "factory", demand=35.0, priority=2, x=650, y=220)
        self.grid.add_node("S1", "Central High School", "school", demand=15.0, priority=3, x=650, y=340)
        self.grid.add_node("R1", "North Residential Block", "house", demand=20.0, priority=4, x=650, y=440)
        self.grid.add_node("R2", "South Residential Block", "house", demand=15.0, priority=4, x=650, y=540)

        # 4. Connections (Demonstrating primary + alternative redundant routes)
        # G1 primary to T1, alternate to T2
        self.grid.add_connection("C1", "G1", "T1", capacity=70.0, cost=100.0)
        self.grid.add_connection("C2", "G1", "T2", capacity=30.0, cost=120.0)

        # G2 to T2
        self.grid.add_connection("C3", "G2", "T2", capacity=50.0, cost=100.0)

        # Inter-substation tie-line (T1 -> T2)
        self.grid.add_connection("C4", "T1", "T2", capacity=25.0, cost=120.0)

        # T1 to consumers
        self.grid.add_connection("C5", "T1", "H1", capacity=30.0, cost=80.0)   # Primary line to Hospital
        self.grid.add_connection("C6", "T1", "F1", capacity=40.0, cost=110.0)  # Primary line to Factory
        self.grid.add_connection("C7", "T1", "S1", capacity=20.0, cost=70.0)   # Line to School

        # T2 to consumers (including backup redundant line to Hospital)
        self.grid.add_connection("C8", "T2", "H1", capacity=25.0, cost=150.0)  # Backup hospital line
        self.grid.add_connection("C9", "T2", "R1", capacity=25.0, cost=65.0)   # Line to North House
        self.grid.add_connection("C10", "T2", "R2", capacity=20.0, cost=55.0)  # Line to South House

        # Run initial optimization
        self.last_report = optimize_grid(self.grid)
        self._record_event("RESET", "Network initialized to default reference state", self.last_report)
        return self.get_state()

    def optimize(self) -> Dict[str, Any]:
        """Runs optimization on the current graph state."""
        self.grid.reset_flows()
        self.last_report = optimize_grid(self.grid)
        self._record_event("OPTIMIZE", "Manual optimization triggered", self.last_report)
        return self.get_state()

    def handle_failure(self, comp_id: str, comp_type: str = "node") -> Dict[str, Any]:
        """
        Autonomous Failure & Recovery:
        1. Mark component disabled.
        2. Identify affected consumers via BFS reachability.
        3. Exclude failed components and clear stale flows.
        4. Re-run optimization on surviving network to find best feasible alternative.
        5. Return comprehensive before/after recovery metrics.
        """
        if comp_type == "node":
            if comp_id not in self.grid.nodes:
                raise KeyError(f"Node '{comp_id}' not found.")
            target = self.grid.nodes[comp_id]
            if target.status == "failed":
                return self.get_state()
            target.status = "failed"
            affected_consumers = self.grid.find_affected_consumers(comp_id, is_node=True)
            desc = f"Failure of node {target.name} ({comp_id})"
        elif comp_type == "connection":
            if comp_id not in self.grid.connections:
                raise KeyError(f"Connection '{comp_id}' not found.")
            target = self.grid.connections[comp_id]
            if target.status == "failed":
                return self.get_state()
            target.status = "failed"
            affected_consumers = self.grid.find_affected_consumers(comp_id, is_node=False)
            desc = f"Failure of connection {comp_id} ({target.source} -> {target.destination})"
        else:
            raise ValueError(f"Invalid component type: {comp_type}")

        # Clear stale flows and re-optimize surviving topology
        self.grid.reset_flows()
        self.last_report = optimize_grid(self.grid)
        self.last_report["affected_consumers"] = affected_consumers
        self.last_report["failed_target"] = comp_id

        self._record_event("FAILURE", desc, self.last_report)
        return self.get_state()

    def handle_restore(self, comp_id: str, comp_type: str = "node") -> Dict[str, Any]:
        """
        Restores failed component and reruns fresh optimization without assuming
        old flow values remain optimal.
        """
        if comp_type == "node":
            if comp_id not in self.grid.nodes:
                raise KeyError(f"Node '{comp_id}' not found.")
            self.grid.nodes[comp_id].status = "active"
            desc = f"Restored node {comp_id}"
        elif comp_type == "connection":
            if comp_id not in self.grid.connections:
                raise KeyError(f"Connection '{comp_id}' not found.")
            self.grid.connections[comp_id].status = "active"
            desc = f"Restored connection {comp_id}"
        else:
            raise ValueError(f"Invalid component type: {comp_type}")

        self.grid.reset_flows()
        self.last_report = optimize_grid(self.grid)
        self._record_event("RESTORE", desc, self.last_report)
        return self.get_state()

    def _record_event(self, event_type: str, message: str, report: Dict[str, Any]):
        self.history.append({
            "step": len(self.history) + 1,
            "type": event_type,
            "message": message,
            "total_supplied": report.get("total_supplied", 0.0),
            "total_unmet": report.get("total_unmet", 0.0),
            "cost": report.get("installation_cost", 0.0)
        })

    def get_state(self) -> Dict[str, Any]:
        """Serializes complete network state and latest simulation report."""
        return {
            "network": self.grid.to_dict(),
            "report": self.last_report,
            "history": self.history[-10:]  # latest 10 events
        }


# Global singleton simulation manager
manager = SimulationManager()
