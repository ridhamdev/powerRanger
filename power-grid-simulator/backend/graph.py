"""
Power Grid Graph Model
Defines directed graph representation G = (V, E) for power distribution network.
Supports generators, transformers, consumers, directed connections,
capacity constraints, and discrete graph traversal algorithms.
"""

from typing import Dict, List, Set, Optional, Any


VALID_NODE_TYPES = {
    "generator",
    "transformer",
    "hospital",
    "factory",
    "school",
    "house"
}

DEFAULT_PRIORITIES = {
    "hospital": 1,
    "factory": 2,
    "school": 3,
    "house": 4
}


class Node:
    """Represents a vertex in the power grid network."""
    def __init__(
        self,
        node_id: str,
        name: str,
        node_type: str,
        capacity: float = 0.0,
        demand: float = 0.0,
        priority: Optional[int] = None,
        status: str = "active",
        x: float = 0.0,
        y: float = 0.0
    ):
        if node_type not in VALID_NODE_TYPES:
            raise ValueError(f"Invalid node type: {node_type}. Must be one of {VALID_NODE_TYPES}")
        if capacity < 0:
            raise ValueError("Capacity cannot be negative.")
        if demand < 0:
            raise ValueError("Demand cannot be negative.")

        self.id = node_id
        self.name = name
        self.type = node_type
        self.status = status if status in ("active", "failed") else "active"
        
        # Generator: max generation; Transformer: max throughput
        self.capacity = float(capacity)
        # Consumers: electricity demand
        self.demand = float(demand)
        
        # Priority: smaller number means higher priority
        if self.is_consumer():
            if priority is None:
                self.priority = DEFAULT_PRIORITIES.get(node_type, 4)
            else:
                self.priority = priority
        else:
            self.priority = None

        self.supplied = 0.0
        self.is_fully_served = False
        self.x = float(x)
        self.y = float(y)

    def is_generator(self) -> bool:
        return self.type == "generator"

    def is_transformer(self) -> bool:
        return self.type == "transformer"

    def is_consumer(self) -> bool:
        return self.type in {"hospital", "factory", "school", "house"}

    def update_service_status(self):
        if self.is_consumer():
            if self.demand <= 0:
                self.is_fully_served = True
            else:
                self.is_fully_served = (self.supplied >= (self.demand - 1e-6))
        else:
            self.is_fully_served = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "capacity": self.capacity,
            "demand": self.demand,
            "priority": self.priority,
            "status": self.status,
            "supplied": round(self.supplied, 2),
            "unmet_demand": round(max(0.0, self.demand - self.supplied), 2) if self.is_consumer() else 0.0,
            "is_fully_served": self.is_fully_served,
            "x": self.x,
            "y": self.y
        }


class Connection:
    """
    Represents a directed transmission line A -> B.
    Permits power flow strictly from source to destination.
    """
    def __init__(
        self,
        conn_id: str,
        source: str,
        destination: str,
        capacity: float,
        cost: float,
        status: str = "active"
    ):
        if source == destination:
            raise ValueError(f"Self-connections are rejected: {source} -> {destination}")
        if capacity < 0:
            raise ValueError("Connection capacity cannot be negative.")
        if cost < 0:
            raise ValueError("Connection installation cost cannot be negative.")

        self.id = conn_id
        self.source = source
        self.destination = destination
        self.capacity = float(capacity)
        self.cost = float(cost)
        self.flow = 0.0
        self.status = status if status in ("active", "failed") else "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "destination": self.destination,
            "capacity": self.capacity,
            "flow": round(self.flow, 2),
            "cost": self.cost,
            "status": self.status
        }


class PowerGridGraph:
    """
    Directed Graph G = (V, E) representing the power distribution network.
    Maintains adjacency lists and enforces graph integrity.
    """
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.connections: Dict[str, Connection] = {}

    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: str,
        capacity: float = 0.0,
        demand: float = 0.0,
        priority: Optional[int] = None,
        status: str = "active",
        x: float = 0.0,
        y: float = 0.0
    ) -> Node:
        if node_id in self.nodes:
            raise ValueError(f"Node ID '{node_id}' already exists.")
        
        node = Node(node_id, name, node_type, capacity, demand, priority, status, x, y)
        self.nodes[node_id] = node
        return node

    def update_node(self, node_id: str, **kwargs) -> Node:
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found.")
        node = self.nodes[node_id]

        if "name" in kwargs:
            node.name = str(kwargs["name"])
        if "capacity" in kwargs:
            val = float(kwargs["capacity"])
            if val < 0:
                raise ValueError("Capacity cannot be negative.")
            node.capacity = val
        if "demand" in kwargs and node.is_consumer():
            val = float(kwargs["demand"])
            if val < 0:
                raise ValueError("Demand cannot be negative.")
            node.demand = val
        if "priority" in kwargs and node.is_consumer():
            node.priority = int(kwargs["priority"])
        if "status" in kwargs:
            status_val = kwargs["status"]
            if status_val in ("active", "failed"):
                node.status = status_val
        if "x" in kwargs:
            node.x = float(kwargs["x"])
        if "y" in kwargs:
            node.y = float(kwargs["y"])

        node.update_service_status()
        return node

    def delete_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found.")
        
        # Remove incident connections
        conns_to_remove = [
            cid for cid, conn in self.connections.items()
            if conn.source == node_id or conn.destination == node_id
        ]
        for cid in conns_to_remove:
            del self.connections[cid]

        del self.nodes[node_id]

    def add_connection(
        self,
        conn_id: str,
        source: str,
        destination: str,
        capacity: float,
        cost: float,
        status: str = "active"
    ) -> Connection:
        if conn_id in self.connections:
            raise ValueError(f"Connection ID '{conn_id}' already exists.")
        if source not in self.nodes:
            raise KeyError(f"Source node '{source}' does not exist.")
        if destination not in self.nodes:
            raise KeyError(f"Destination node '{destination}' does not exist.")
        if source == destination:
            raise ValueError("Self-connections are rejected.")

        # Reject duplicate directed line with the same source and destination
        for c in self.connections.values():
            if c.source == source and c.destination == destination:
                raise ValueError(f"Duplicate connection between {source} and {destination} already exists.")

        conn = Connection(conn_id, source, destination, capacity, cost, status)
        self.connections[conn_id] = conn
        return conn

    def update_connection(self, conn_id: str, **kwargs) -> Connection:
        if conn_id not in self.connections:
            raise KeyError(f"Connection '{conn_id}' not found.")
        conn = self.connections[conn_id]

        if "capacity" in kwargs:
            val = float(kwargs["capacity"])
            if val < 0:
                raise ValueError("Capacity cannot be negative.")
            conn.capacity = val
        if "cost" in kwargs:
            val = float(kwargs["cost"])
            if val < 0:
                raise ValueError("Installation cost cannot be negative.")
            conn.cost = val
        if "status" in kwargs:
            s = kwargs["status"]
            if s in ("active", "failed"):
                conn.status = s

        return conn

    def delete_connection(self, conn_id: str) -> None:
        if conn_id not in self.connections:
            raise KeyError(f"Connection '{conn_id}' not found.")
        del self.connections[conn_id]

    def reset_flows(self) -> None:
        """Reset all allocated flows and supplied demands to zero."""
        for conn in self.connections.values():
            conn.flow = 0.0
        for node in self.nodes.values():
            node.supplied = 0.0
            node.update_service_status()

    def get_adjacency(self, active_only: bool = False) -> Dict[str, List[Connection]]:
        """Returns directed adjacency list: u -> list of outgoing connections."""
        adj: Dict[str, List[Connection]] = {nid: [] for nid in self.nodes}
        for conn in self.connections.values():
            if active_only:
                if conn.status != "active":
                    continue
                if self.nodes[conn.source].status != "active" or self.nodes[conn.destination].status != "active":
                    continue
            adj[conn.source].append(conn)
        return adj

    def get_reverse_adjacency(self, active_only: bool = False) -> Dict[str, List[Connection]]:
        """Returns reverse directed adjacency list: v -> list of incoming connections."""
        rev: Dict[str, List[Connection]] = {nid: [] for nid in self.nodes}
        for conn in self.connections.values():
            if active_only:
                if conn.status != "active":
                    continue
                if self.nodes[conn.source].status != "active" or self.nodes[conn.destination].status != "active":
                    continue
            rev[conn.destination].append(conn)
        return rev

    def bfs_reachable_from(self, start_id: str, active_only: bool = True) -> Set[str]:
        """Returns set of node IDs reachable from start_id via directed paths."""
        if start_id not in self.nodes:
            return set()
        adj = self.get_adjacency(active_only=active_only)
        visited = set()
        queue = [start_id]
        visited.add(start_id)

        while queue:
            curr = queue.pop(0)
            for conn in adj.get(curr, []):
                nxt = conn.destination
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return visited

    def find_affected_consumers(self, failed_id: str, is_node: bool = True) -> List[str]:
        """
        BFS/Reachability analysis to identify consumers affected by the failure.
        Compares consumers reachable from active generators before vs after failure.
        """
        # Active generators excluding failed components
        active_gens = [
            nid for nid, node in self.nodes.items()
            if node.is_generator() and node.status == "active"
        ]
        
        # Find all consumers currently reachable from any active generator
        reachable_consumers = set()
        for gid in active_gens:
            for target_id in self.bfs_reachable_from(gid, active_only=True):
                if self.nodes[target_id].is_consumer():
                    reachable_consumers.add(target_id)

        # Consumers that were receiving flow but may now be cut off or compromised
        affected = []
        for nid, node in self.nodes.items():
            if node.is_consumer() and node.status == "active":
                if nid not in reachable_consumers:
                    affected.append(nid)
                elif node.supplied < node.demand and node.demand > 0:
                    affected.append(nid)

        return affected

    def kruskal_mst(self) -> Dict[str, Any]:
        """
        Demonstration of Kruskal's Algorithm on the undirected projection of the network.
        Used for academic MST comparison and discrete mathematics defense.
        """
        # Collect unique undirected edges with their minimum cost
        edge_map = {}
        for conn in self.connections.values():
            u, v = sorted([conn.source, conn.destination])
            key = (u, v)
            if key not in edge_map or conn.cost < edge_map[key]["cost"]:
                edge_map[key] = {
                    "id": conn.id,
                    "u": u,
                    "v": v,
                    "cost": conn.cost,
                    "capacity": conn.capacity
                }

        edges = list(edge_map.values())
        edges.sort(key=lambda e: e["cost"])

        # Disjoint Set Union (DSU)
        parent = {nid: nid for nid in self.nodes}

        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j
                return True
            return False

        mst_edges = []
        total_cost = 0.0

        for e in edges:
            if union(e["u"], e["v"]):
                mst_edges.append(e)
                total_cost += e["cost"]

        return {
            "mst_edges": mst_edges,
            "total_cost": total_cost,
            "num_edges": len(mst_edges),
            "note": "Undirected MST minimizes total connection installation cost without capacity or priority constraints."
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [c.to_dict() for c in self.connections.values()]
        }
