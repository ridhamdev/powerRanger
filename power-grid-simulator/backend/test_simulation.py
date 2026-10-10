"""
Comprehensive Unit and Algorithmic Tests for Power Grid Simulator
Verifies capacity constraints, priority enforcement, autonomous recovery,
cycle/reverse flow integrity, and validation.
"""

import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from graph import PowerGridGraph, Node, Connection
from optimizer import optimize_grid
from simulation import SimulationManager


def test_valid_initial_network_satisfies_capacity_constraints():
    """Test 1: Valid initial network satisfies all capacity constraints."""
    sim = SimulationManager()
    sim.reset()
    grid = sim.grid

    # Check connection flow constraints: 0 <= flow <= capacity
    for conn in grid.connections.values():
        assert 0.0 <= conn.flow <= conn.capacity + 1e-6, f"Connection {conn.id} exceeded capacity!"

    # Check generator output <= capacity
    for nid, node in grid.nodes.items():
        if node.is_generator():
            out_flow = sum(c.flow for c in grid.connections.values() if c.source == nid)
            assert out_flow <= node.capacity + 1e-6, f"Generator {nid} exceeded output limit!"

    # Check transformer conservation & throughput <= capacity
    for nid, node in grid.nodes.items():
        if node.is_transformer():
            in_flow = sum(c.flow for c in grid.connections.values() if c.destination == nid)
            out_flow = sum(c.flow for c in grid.connections.values() if c.source == nid)
            assert abs(in_flow - out_flow) < 1e-4, f"Transformer {nid} violated flow conservation!"
            assert in_flow <= node.capacity + 1e-6, f"Transformer {nid} exceeded throughput capacity!"


def test_connection_flow_never_exceeds_capacity():
    """Test 2: A connection's allocated flow never exceeds its capacity."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=100.0)
    grid.add_node("H", "Hospital", "hospital", demand=100.0, priority=1)
    # Connection capacity only 40
    grid.add_connection("C1", "G", "H", capacity=40.0, cost=10.0)

    optimize_grid(grid)
    assert grid.connections["C1"].flow == pytest.approx(40.0, 0.01)
    assert grid.nodes["H"].supplied == pytest.approx(40.0, 0.01)


def test_transformer_never_exceeds_throughput():
    """Test 3: A transformer never exceeds its throughput."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=100.0)
    # Transformer with throughput limit 25
    grid.add_node("T", "Trans", "transformer", capacity=25.0)
    grid.add_node("H", "Hospital", "hospital", demand=50.0, priority=1)

    grid.add_connection("C1", "G", "T", capacity=100.0, cost=10.0)
    grid.add_connection("C2", "T", "H", capacity=100.0, cost=10.0)

    optimize_grid(grid)
    assert grid.connections["C1"].flow == pytest.approx(25.0, 0.01)
    assert grid.connections["C2"].flow == pytest.approx(25.0, 0.01)
    assert grid.nodes["H"].supplied == pytest.approx(25.0, 0.01)


def test_reverse_flow_not_allowed():
    """Test 4: Reverse flow is not allowed unless a reverse connection exists."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=50.0)
    grid.add_node("H", "Hospital", "hospital", demand=30.0, priority=1)
    
    # Directed edge H -> G (backward direction)
    grid.add_connection("C_rev", "H", "G", capacity=50.0, cost=10.0)

    report = optimize_grid(grid)
    # Power cannot flow backwards from G to H via H -> G edge!
    assert grid.connections["C_rev"].flow == 0.0
    assert grid.nodes["H"].supplied == 0.0
    assert report["total_supplied"] == 0.0


def test_failed_connection_bypassed_via_alternative_route():
    """Test 5: A failed connection can be bypassed through an alternative directed route."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=50.0)
    grid.add_node("T1", "Sub1", "transformer", capacity=50.0)
    grid.add_node("T2", "Sub2", "transformer", capacity=50.0)
    grid.add_node("H", "Hospital", "hospital", demand=20.0, priority=1)

    # Primary path via T1: cheap (cost 10 + 10 = 20)
    grid.add_connection("C_primary1", "G", "T1", capacity=30.0, cost=10.0)
    grid.add_connection("C_primary2", "T1", "H", capacity=30.0, cost=10.0)

    # Backup path via T2: expensive (cost 50 + 50 = 100)
    grid.add_connection("C_backup1", "G", "T2", capacity=30.0, cost=50.0)
    grid.add_connection("C_backup2", "T2", "H", capacity=30.0, cost=50.0)

    # Initial optimization should use primary path
    rep1 = optimize_grid(grid)
    assert grid.nodes["H"].supplied == pytest.approx(20.0, 0.01)
    assert grid.connections["C_primary1"].flow == pytest.approx(20.0, 0.01)
    assert grid.connections["C_backup1"].flow == 0.0

    # Fail primary line C_primary2
    grid.connections["C_primary2"].status = "failed"
    rep2 = optimize_grid(grid)
    # Bypassed via T2!
    assert grid.nodes["H"].supplied == pytest.approx(20.0, 0.01)
    assert grid.connections["C_backup1"].flow == pytest.approx(20.0, 0.01)
    assert grid.connections["C_backup2"].flow == pytest.approx(20.0, 0.01)


def test_failed_transformer_cannot_carry_power():
    """Test 6: A failed transformer cannot carry power."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=50.0)
    grid.add_node("T", "Sub", "transformer", capacity=50.0)
    grid.add_node("H", "Hospital", "hospital", demand=20.0, priority=1)

    grid.add_connection("C1", "G", "T", capacity=30.0, cost=10.0)
    grid.add_connection("C2", "T", "H", capacity=30.0, cost=10.0)

    # Disable transformer
    grid.nodes["T"].status = "failed"
    report = optimize_grid(grid)

    assert grid.connections["C1"].flow == 0.0
    assert grid.connections["C2"].flow == 0.0
    assert grid.nodes["H"].supplied == 0.0
    assert report["total_unmet"] == pytest.approx(20.0, 0.01)


def test_hospital_priority_when_supply_constrained():
    """Test 7: A hospital receives priority when supply is constrained."""
    grid = PowerGridGraph()
    # Total supply only 30 units
    grid.add_node("G", "Gen", "generator", capacity=30.0)
    # Hospital demands 25 (priority 1), House demands 20 (priority 4)
    grid.add_node("H", "City Hospital", "hospital", demand=25.0, priority=1)
    grid.add_node("R", "Residential House", "house", demand=20.0, priority=4)

    grid.add_connection("C1", "G", "H", capacity=30.0, cost=10.0)
    grid.add_connection("C2", "G", "R", capacity=30.0, cost=10.0)

    report = optimize_grid(grid)
    # Hospital must receive all 25 units!
    assert grid.nodes["H"].supplied == pytest.approx(25.0, 0.01)
    assert grid.nodes["H"].is_fully_served is True
    # House gets remaining 5 units
    assert grid.nodes["R"].supplied == pytest.approx(5.0, 0.01)
    assert grid.nodes["R"].is_fully_served is False
    assert report["total_supplied"] == pytest.approx(30.0, 0.01)
    assert report["total_unmet"] == pytest.approx(15.0, 0.01)


def test_infeasible_network_reports_unmet_demand():
    """Test 8: An infeasible network reports unmet demand honestly."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=15.0)
    grid.add_node("H", "Hospital", "hospital", demand=40.0, priority=1)
    grid.add_connection("C1", "G", "H", capacity=50.0, cost=10.0)

    report = optimize_grid(grid)
    assert report["total_supplied"] == pytest.approx(15.0, 0.01)
    assert report["total_unmet"] == pytest.approx(25.0, 0.01)
    assert "H" in report["partial_supply_consumers"]


def test_cheaper_configuration_selected_when_service_equivalent():
    """Test 9: A cheaper configuration is selected when service outcomes are equivalent."""
    grid = PowerGridGraph()
    grid.add_node("G", "Gen", "generator", capacity=50.0)
    grid.add_node("H", "Hospital", "hospital", demand=20.0, priority=1)

    # Line 1: cheap (cost 50)
    grid.add_connection("C_cheap", "G", "H", capacity=25.0, cost=50.0)
    # Line 2: expensive (cost 200)
    # We test with intermediate node so we have 2 distinct paths
    grid.add_node("T", "Sub", "transformer", capacity=50.0)
    grid.add_connection("C_exp1", "G", "T", capacity=25.0, cost=100.0)
    grid.add_connection("C_exp2", "T", "H", capacity=25.0, cost=100.0)

    report = optimize_grid(grid)
    assert grid.nodes["H"].supplied == pytest.approx(20.0, 0.01)
    assert grid.connections["C_cheap"].flow == pytest.approx(20.0, 0.01)
    assert grid.connections["C_exp1"].flow == 0.0
    assert grid.connections["C_exp2"].flow == 0.0
    assert report["installation_cost"] == pytest.approx(50.0, 0.01)


def test_restoring_component_triggers_fresh_optimization():
    """Test 10: Restoring a component triggers a fresh optimization."""
    sim = SimulationManager()
    sim.reset()

    # Fail connection C5 (Main line to Hospital)
    sim.handle_failure("C5", "connection")
    assert sim.grid.connections["C5"].status == "failed"
    assert sim.grid.connections["C5"].flow == 0.0

    # Restore connection C5
    sim.handle_restore("C5", "connection")
    assert sim.grid.connections["C5"].status == "active"
    # Fresh optimization should route power through C5 again because it is cheaper than C8
    assert sim.grid.connections["C5"].flow > 0.0


def test_repeated_failures_do_not_leave_stale_allocations():
    """Test 11: Repeated failures do not leave stale allocations."""
    sim = SimulationManager()
    sim.reset()

    # Repeatedly toggle failures
    sim.handle_failure("G1", "node")
    assert sim.grid.connections["C1"].flow == 0.0
    assert sim.grid.connections["C2"].flow == 0.0

    sim.handle_failure("T2", "node")
    assert sim.grid.connections["C3"].flow == 0.0

    # Restore G1
    sim.handle_restore("G1", "node")
    # T2 is still failed, so G1 can only route to T1
    assert sim.grid.connections["C2"].flow == 0.0
    assert sim.grid.connections["C1"].flow > 0.0


def test_invalid_connections_and_negative_capacities_rejected():
    """Test 12: Invalid connections and negative capacities are rejected."""
    grid = PowerGridGraph()
    grid.add_node("N1", "Node1", "generator", capacity=10.0)
    grid.add_node("N2", "Node2", "house", demand=10.0)

    # Reject self-connection
    with pytest.raises(ValueError):
        grid.add_connection("C_self", "N1", "N1", capacity=10.0, cost=10.0)

    # Reject non-existent endpoints
    with pytest.raises(KeyError):
        grid.add_connection("C_bad", "N1", "UNKNOWN", capacity=10.0, cost=10.0)

    # Reject negative capacity
    with pytest.raises(ValueError):
        grid.add_connection("C_neg", "N1", "N2", capacity=-5.0, cost=10.0)

    # Reject negative cost
    with pytest.raises(ValueError):
        grid.add_connection("C_negcost", "N1", "N2", capacity=5.0, cost=-10.0)

    # Reject negative node capacity
    with pytest.raises(ValueError):
        grid.add_node("N3", "BadNode", "generator", capacity=-10.0)

    # Reject duplicate directed edge
    grid.add_connection("C_valid", "N1", "N2", capacity=10.0, cost=10.0)
    with pytest.raises(ValueError):
        grid.add_connection("C_dup", "N1", "N2", capacity=5.0, cost=5.0)
