"""
Power Grid Optimizer
Implements constrained load allocation and minimum-cost recovery.
Lexicographic decision order:
1. Maximize service to consumers according to priorities (1 = highest).
2. Maximize total demand served among equivalent priority outcomes.
3. Minimize total connection installation cost (edges with flow > 0).
4. Prefer fewer unnecessary changes when costs and service outcomes are equivalent.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
import heapq
from collections import defaultdict
from graph import PowerGridGraph, Node, Connection


class FlowNetwork:
    """
    Internal residual flow network with node splitting for throughput enforcement.
    Node types in residual network:
    - SUPER_SOURCE
    - SUPER_SINK
    - Generator: 'g_id'
    - Transformer: 't_id_in' and 't_id_out'
    - Consumer: 'c_id'
    """
    def __init__(self):
        self.adj = defaultdict(list)  # u -> list of edge dicts
        self.edges = []               # list of all edge dicts

    def add_edge(self, u: str, v: str, cap: float, conn_id: Optional[str] = None):
        forward = {
            "u": u,
            "v": v,
            "cap": float(cap),
            "flow": 0.0,
            "conn_id": conn_id,
            "is_reverse": False,
            "rev_idx": -1
        }
        backward = {
            "u": v,
            "v": u,
            "cap": 0.0,
            "flow": 0.0,
            "conn_id": conn_id,
            "is_reverse": True,
            "rev_idx": -1
        }
        f_idx = len(self.edges)
        b_idx = f_idx + 1
        forward["rev_idx"] = b_idx
        backward["rev_idx"] = f_idx
        
        self.edges.append(forward)
        self.edges.append(backward)
        self.adj[u].append(f_idx)
        self.adj[v].append(b_idx)


def build_flow_network(
    grid: PowerGridGraph,
    allowed_connections: Optional[Set[str]] = None
) -> Tuple[FlowNetwork, Dict[str, str], Dict[str, str]]:
    """
    Builds residual network enforcing generator capacities, transformer throughputs,
    and connection transmission limits.
    """
    fn = FlowNetwork()
    in_node_map = {}
    out_node_map = {}

    for nid, node in grid.nodes.items():
        if node.status != "active":
            continue
        if node.is_generator():
            in_node_map[nid] = nid
            out_node_map[nid] = nid
            # Edge from SUPER_SOURCE to generator bounded by generator capacity
            fn.add_edge("SUPER_SOURCE", nid, node.capacity)
        elif node.is_transformer():
            in_name = f"{nid}_in"
            out_name = f"{nid}_out"
            in_node_map[nid] = in_name
            out_node_map[nid] = out_name
            # Node splitting: throughput capacity constraint
            fn.add_edge(in_name, out_name, node.capacity)
        elif node.is_consumer():
            in_node_map[nid] = nid
            out_node_map[nid] = nid

    for cid, conn in grid.connections.items():
        if conn.status != "active":
            continue
        if allowed_connections is not None and cid not in allowed_connections:
            continue
        
        src_node = grid.nodes.get(conn.source)
        dst_node = grid.nodes.get(conn.destination)
        if not src_node or not dst_node:
            continue
        if src_node.status != "active" or dst_node.status != "active":
            continue

        u = out_node_map[conn.source]
        v = in_node_map[conn.destination]
        fn.add_edge(u, v, conn.capacity, conn_id=cid)

    return fn, in_node_map, out_node_map


def find_min_cost_augmenting_path(
    fn: FlowNetwork,
    grid: PowerGridGraph,
    active_used_conns: Set[str]
) -> Optional[Tuple[List[int], float]]:
    """
    Finds the shortest / lowest marginal installation cost path from SUPER_SOURCE to SUPER_SINK.
    Marginal cost calculation:
    - If connection is already activated in this configuration: marginal cost = 0.
    - If connection is newly activated: marginal cost = connection.cost.
    - +0.001 per hop to break ties with fewer edges.
    """
    dist = {}
    parent_edge_idx = {}
    pq = []
    
    start_node = "SUPER_SOURCE"
    target_node = "SUPER_SINK"
    
    dist[start_node] = 0.0
    heapq.heappush(pq, (0.0, start_node))
    
    while pq:
        curr_d, curr_u = heapq.heappop(pq)
        if curr_d > dist.get(curr_u, float('inf')):
            continue
        if curr_u == target_node:
            break

        for e_idx in fn.adj.get(curr_u, []):
            edge = fn.edges[e_idx]
            rem_cap = edge["cap"] - edge["flow"]
            if rem_cap <= 1e-9:
                continue
            
            v = edge["v"]
            # Determine edge traversal cost
            edge_cost = 0.001  # hop cost
            cid = edge["conn_id"]
            if cid is not None and not edge["is_reverse"]:
                # If connection is not yet carrying any flow, adding it costs installation cost
                if cid not in active_used_conns:
                    edge_cost += grid.connections[cid].cost

            new_d = curr_d + edge_cost
            if new_d < dist.get(v, float('inf')):
                dist[v] = new_d
                parent_edge_idx[v] = e_idx
                heapq.heappush(pq, (new_d, v))

    if target_node not in parent_edge_idx:
        return None

    # Reconstruct path and find bottleneck capacity
    path = []
    curr = target_node
    bottle = float('inf')
    while curr != start_node:
        e_idx = parent_edge_idx[curr]
        edge = fn.edges[e_idx]
        rem = edge["cap"] - edge["flow"]
        if rem < bottle:
            bottle = rem
        path.append(e_idx)
        curr = edge["u"]

    path.reverse()
    return path, bottle


def run_priority_flow(
    grid: PowerGridGraph,
    allowed_connections: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Solves capacity-constrained flow allocation by consumer priority tiers.
    """
    fn, in_map, out_map = build_flow_network(grid, allowed_connections)
    active_used_conns = set()

    # Group active consumers by priority rank
    consumers = [
        n for n in grid.nodes.values()
        if n.is_consumer() and n.status == "active" and n.demand > 0
    ]
    # Sort distinct priority values (1 = highest)
    priorities = sorted(list(set(c.priority for c in consumers if c.priority is not None)))

    consumer_supplied = {c.id: 0.0 for c in consumers}

    for prio in priorities:
        tier_consumers = [c for c in consumers if c.priority == prio]
        
        # Add sink edges for this tier
        sink_edge_indices = []
        for c in tier_consumers:
            rem_demand = c.demand - consumer_supplied[c.id]
            if rem_demand > 1e-9:
                e_fwd = len(fn.edges)
                fn.add_edge(c.id, "SUPER_SINK", rem_demand)
                sink_edge_indices.append((c.id, e_fwd))

        # Augment flow for this tier
        while True:
            res = find_min_cost_augmenting_path(fn, grid, active_used_conns)
            if res is None:
                break
            path, bottle = res
            if bottle <= 1e-9:
                break

            for e_idx in path:
                fn.edges[e_idx]["flow"] += bottle
                rev_idx = fn.edges[e_idx]["rev_idx"]
                fn.edges[rev_idx]["flow"] -= bottle
                
                cid = fn.edges[e_idx]["conn_id"]
                if cid and not fn.edges[e_idx]["is_reverse"]:
                    active_used_conns.add(cid)

        # Record supplied power for this tier
        for cid_node, e_fwd in sink_edge_indices:
            flow_val = fn.edges[e_fwd]["flow"]
            consumer_supplied[cid_node] += flow_val
            
            # Close the sink edge to freeze allocation
            fn.edges[e_fwd]["cap"] = flow_val

    # Aggregate connection flows
    conn_flows = {cid: 0.0 for cid in grid.connections}
    for edge in fn.edges:
        if edge["conn_id"] and not edge["is_reverse"] and edge["flow"] > 1e-9:
            conn_flows[edge["conn_id"]] += edge["flow"]

    # Calculate installation cost for selected connections (flow > 0)
    selected_conns = [cid for cid, f in conn_flows.items() if f > 1e-9]
    total_cost = sum(grid.connections[cid].cost for cid in selected_conns)
    total_served = sum(consumer_supplied.values())

    return {
        "conn_flows": conn_flows,
        "consumer_supplied": consumer_supplied,
        "selected_conns": selected_conns,
        "total_cost": total_cost,
        "total_served": total_served,
        "priorities": priorities
    }


def optimize_grid(grid: PowerGridGraph) -> Dict[str, Any]:
    """
    Main optimization routine enforcing lexicographic decision order:
    1. Maximize priority service.
    2. Maximize total demand served.
    3. Minimize installation cost of selected connections.
    4. Minimize changes.
    """
    # 1. Base solution using all active connections
    best_solution = run_priority_flow(grid)
    
    # Priority satisfaction vector for comparison
    def get_prio_vector(sol):
        p_vec = []
        for p in sorted(list(set(n.priority for n in grid.nodes.values() if n.is_consumer() and n.priority is not None))):
            p_served = sum(
                sol["consumer_supplied"].get(n.id, 0.0)
                for n in grid.nodes.values() if n.is_consumer() and n.priority == p
            )
            p_vec.append(round(p_served, 4))
        return p_vec

    best_prio_vector = get_prio_vector(best_solution)

    # 2. Backward edge-pruning to eliminate unnecessary expensive lines
    # Sort selected connections by cost descending to test if high-cost lines can be omitted
    used_conns = sorted(
        best_solution["selected_conns"],
        key=lambda cid: grid.connections[cid].cost,
        reverse=True
    )

    current_allowed = set(grid.connections.keys())

    for cid in used_conns:
        test_allowed = set(current_allowed)
        test_allowed.remove(cid)
        candidate_sol = run_priority_flow(grid, allowed_connections=test_allowed)
        cand_prio_vector = get_prio_vector(candidate_sol)

        # Lexicographic check:
        # Must match or beat priority vector
        if cand_prio_vector >= best_prio_vector:
            # If priority outcomes are identical, check if cost is lower
            if candidate_sol["total_cost"] < best_solution["total_cost"] or (
                abs(candidate_sol["total_cost"] - best_solution["total_cost"]) < 1e-6 and
                len(candidate_sol["selected_conns"]) <= len(best_solution["selected_conns"])
            ):
                best_solution = candidate_sol
                best_prio_vector = cand_prio_vector
                current_allowed = test_allowed

    # Apply solution to grid
    for cid, conn in grid.connections.items():
        conn.flow = round(best_solution["conn_flows"].get(cid, 0.0), 2)

    for nid, node in grid.nodes.items():
        if node.is_consumer():
            node.supplied = round(best_solution["consumer_supplied"].get(nid, 0.0), 2)
            node.update_service_status()

    # Analyze bottlenecks and service delivery
    full_served = []
    partial_served = []
    no_served = []
    total_demand = 0.0
    total_unmet = 0.0

    for nid, node in grid.nodes.items():
        if node.is_consumer() and node.status == "active":
            total_demand += node.demand
            unmet = max(0.0, node.demand - node.supplied)
            total_unmet += unmet
            if node.demand > 0:
                if node.supplied >= (node.demand - 1e-4):
                    full_served.append(nid)
                elif node.supplied > 1e-4:
                    partial_served.append(nid)
                else:
                    no_served.append(nid)

    # Identify network bottlenecks
    bottlenecks = []
    for cid, conn in grid.connections.items():
        if conn.status == "active" and conn.capacity > 0:
            if abs(conn.flow - conn.capacity) < 1e-4:
                bottlenecks.append(f"Connection {cid} ({conn.source} -> {conn.destination}) at 100% capacity ({conn.capacity} units)")

    for nid, node in grid.nodes.items():
        if node.status == "active":
            if node.is_generator():
                out_flow = sum(c.flow for c in grid.connections.values() if c.source == nid)
                if abs(out_flow - node.capacity) < 1e-4 and node.capacity > 0:
                    bottlenecks.append(f"Generator {node.name} ({nid}) operating at max output ({node.capacity} units)")
            elif node.is_transformer():
                in_flow = sum(c.flow for c in grid.connections.values() if c.destination == nid)
                if abs(in_flow - node.capacity) < 1e-4 and node.capacity > 0:
                    bottlenecks.append(f"Transformer {node.name} ({nid}) operating at max throughput ({node.capacity} units)")

    failed_components = [
        nid for nid, node in grid.nodes.items() if node.status == "failed"
    ] + [
        cid for cid, conn in grid.connections.items() if conn.status == "failed"
    ]

    report = {
        "status": "success",
        "total_demand": round(total_demand, 2),
        "total_supplied": round(best_solution["total_served"], 2),
        "total_unmet": round(total_unmet, 2),
        "installation_cost": round(best_solution["total_cost"], 2),
        "selected_connections": best_solution["selected_conns"],
        "full_supply_consumers": full_served,
        "partial_supply_consumers": partial_served,
        "no_supply_consumers": no_served,
        "failed_components": failed_components,
        "bottlenecks": bottlenecks,
        "algorithm_notes": (
            "Priority-staged augmenting flow with marginal installation cost bias "
            "and backward elimination pruning. Heuristic guarantees capacity safety and "
            "deterministic priority protection; global minimum installation cost on arbitrary "
            "fixed-charge networks is NP-hard."
        )
    }

    return report
