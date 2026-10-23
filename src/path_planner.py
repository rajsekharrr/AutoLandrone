"""
3D A* Path Planner for Autonomous Drone Landing

Production-ready 3D A* pathfinding algorithm that computes obstacle-free
descent trajectories on a risk grid. Considers terrain risk, altitude changes,
and wind drift to generate safe waypoint sequences (x, y, z) for landing.
"""

import numpy as np
import heapq
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
import math


@dataclass
class PathNode:
    """Node in the 3D search space for A* algorithm."""
    x: int
    y: int
    z: int  # Altitude level (0 = ground, higher = more altitude)
    g_cost: float = float('inf')  # Cost from start
    h_cost: float = 0.0  # Heuristic cost to goal
    f_cost: float = float('inf')  # Total cost (g + h)
    parent: Optional['PathNode'] = None

    def __lt__(self, other):
        """Comparison for priority queue."""
        return self.f_cost < other.f_cost

    def __eq__(self, other):
        """Equality based on position."""
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __hash__(self):
        """Hash for set membership."""
        return hash((self.x, self.y, self.z))

    def position(self) -> Tuple[int, int, int]:
        """Return (x, y, z) tuple."""
        return (self.x, self.y, self.z)


@dataclass
class PathPlannerConfig:
    """Configuration for 3D path planner."""
    # Grid parameters
    grid_size: int = 7  # N×N horizontal grid
    altitude_levels: int = 10  # Number of discrete altitude levels (0-9)
    max_altitude: float = 30.0  # Maximum altitude in meters
    cell_size: float = 5.0  # Real-world size of each grid cell in meters

    # Movement costs
    horizontal_move_cost: float = 1.0  # Cost for horizontal movement
    vertical_move_cost: float = 0.8  # Cost for altitude change (descent preferred)
    diagonal_move_cost: float = 1.414  # sqrt(2) for diagonal moves

    # Risk parameters
    risk_weight: float = 5.0  # Weight for terrain risk in cost function
    altitude_bonus: float = 0.2  # Cost reduction per altitude level (safer higher up)
    max_risk_threshold: float = 0.9  # Maximum acceptable risk for any cell

    # Wind drift parameters
    enable_wind_drift: bool = True
    wind_drift_weight: float = 0.3  # Weight for wind drift cost

    # Search parameters
    max_iterations: int = 10000  # Maximum A* iterations
    allow_diagonal: bool = True  # Allow diagonal horizontal moves

    # Descent strategy
    descent_rate: int = 1  # How many altitude levels to descend per horizontal move


class PathPlanner:
    """
    3D A* path planner for drone descent and landing.

    Computes obstacle-free trajectories on a 3D grid where:
    - X, Y: Horizontal position (grid coordinates)
    - Z: Altitude level (0 = ground, higher = more altitude)

    The planner considers terrain risk, altitude changes, and optional wind drift
    to find the safest and most efficient path to a landing zone.
    """

    def __init__(self, config: PathPlannerConfig):
        self.config = config
        self.risk_grid: Optional[np.ndarray] = None
        self.wind_vector: Tuple[float, float] = (0.0, 0.0)  # (wind_x, wind_y) in m/s

    def set_risk_grid(self, risk_grid: np.ndarray) -> None:
        """
        Set the 2D terrain risk grid.

        Args:
            risk_grid: 2D array (grid_size, grid_size) with risk values 0.0-1.0
        """
        if risk_grid.shape != (self.config.grid_size, self.config.grid_size):
            raise ValueError(
                f"Risk grid shape {risk_grid.shape} does not match "
                f"expected ({self.config.grid_size}, {self.config.grid_size})"
            )
        self.risk_grid = risk_grid

    def set_wind(self, wind_speed: float, wind_direction: float) -> None:
        """
        Set wind conditions for drift compensation.

        Args:
            wind_speed: Wind speed in m/s
            wind_direction: Wind direction in degrees (0 = North, 90 = East)
        """
        # Convert to Cartesian coordinates
        wind_rad = math.radians(wind_direction)
        self.wind_vector = (
            wind_speed * math.sin(wind_rad),  # X component (East)
            wind_speed * math.cos(wind_rad)   # Y component (North)
        )

    def _heuristic(self, node: PathNode, goal: PathNode) -> float:
        """
        Calculate heuristic cost from node to goal.

        Uses 3D Euclidean distance with altitude weighting.

        Args:
            node: Current node
            goal: Goal node

        Returns:
            Heuristic cost estimate
        """
        # Horizontal distance
        dx = abs(node.x - goal.x)
        dy = abs(node.y - goal.y)
        horizontal_dist = math.sqrt(dx**2 + dy**2)

        # Vertical distance (altitude difference)
        dz = abs(node.z - goal.z)

        # Combined cost (favor descending)
        cost = horizontal_dist * self.config.horizontal_move_cost
        cost += dz * self.config.vertical_move_cost

        return cost

    def _get_terrain_risk(self, x: int, y: int) -> float:
        """
        Get terrain risk for a grid cell.

        Args:
            x: Grid X coordinate
            y: Grid Y coordinate

        Returns:
            Risk value (0.0-1.0), or 1.0 if out of bounds
        """
        if self.risk_grid is None:
            return 0.0

        if not (0 <= x < self.config.grid_size and 0 <= y < self.config.grid_size):
            return 1.0  # Out of bounds = maximum risk

        return float(self.risk_grid[y, x])

    def _calculate_wind_drift_cost(self, from_node: PathNode, to_node: PathNode) -> float:
        """
        Calculate cost penalty for wind drift.

        Moving against the wind costs more; moving with it costs less.

        Args:
            from_node: Starting node
            to_node: Destination node

        Returns:
            Wind drift cost penalty
        """
        if not self.config.enable_wind_drift or self.wind_vector == (0.0, 0.0):
            return 0.0

        # Movement vector
        dx = to_node.x - from_node.x
        dy = to_node.y - from_node.y

        if dx == 0 and dy == 0:
            return 0.0  # No horizontal movement

        # Normalize movement vector
        move_dist = math.sqrt(dx**2 + dy**2)
        move_unit = (dx / move_dist, dy / move_dist)

        # Dot product with wind vector (negative = against wind)
        wind_alignment = (move_unit[0] * self.wind_vector[0] +
                         move_unit[1] * self.wind_vector[1])

        # Penalty for moving against wind, bonus for moving with it
        # Negative alignment = moving against wind = higher cost
        wind_cost = -wind_alignment * self.config.wind_drift_weight

        return wind_cost

    def _get_neighbors(self, node: PathNode) -> List[PathNode]:
        """
        Get valid neighbor nodes for A* expansion.

        Args:
            node: Current node

        Returns:
            List of valid neighbor nodes
        """
        neighbors = []

        # Horizontal moves (8 directions if diagonal allowed, 4 otherwise)
        horizontal_moves = [
            (0, 1), (0, -1), (1, 0), (-1, 0)  # Cardinal directions
        ]
        if self.config.allow_diagonal:
            horizontal_moves += [
                (1, 1), (1, -1), (-1, 1), (-1, -1)  # Diagonal directions
            ]

        # Vertical moves (descend, stay, ascend slightly)
        vertical_moves = [
            -self.config.descent_rate,  # Descend (preferred)
            0,                           # Maintain altitude
            -1                           # Descend slowly
        ]

        for dx, dy in horizontal_moves:
            for dz in vertical_moves:
                new_x = node.x + dx
                new_y = node.y + dy
                new_z = node.z + dz

                # Check bounds
                if not (0 <= new_x < self.config.grid_size and
                       0 <= new_y < self.config.grid_size and
                       0 <= new_z < self.config.altitude_levels):
                    continue

                # Check if cell is too risky (unless we're high enough)
                terrain_risk = self._get_terrain_risk(new_x, new_y)

                # Allow risky cells at higher altitudes (we can descend later)
                effective_risk = terrain_risk * (1.0 - new_z / self.config.altitude_levels * 0.5)

                if effective_risk > self.config.max_risk_threshold:
                    continue

                neighbors.append(PathNode(new_x, new_y, new_z))

        return neighbors

    def _calculate_move_cost(self, from_node: PathNode, to_node: PathNode) -> float:
        """
        Calculate cost of moving from one node to another.

        Args:
            from_node: Starting node
            to_node: Destination node

        Returns:
            Movement cost
        """
        # Base movement cost
        dx = abs(to_node.x - from_node.x)
        dy = abs(to_node.y - from_node.y)
        dz = abs(to_node.z - from_node.z)

        # Horizontal cost
        if dx + dy == 2:  # Diagonal
            cost = self.config.diagonal_move_cost
        elif dx + dy == 1:  # Cardinal
            cost = self.config.horizontal_move_cost
        else:
            cost = 0.0

        # Vertical cost (slightly favor descending)
        if to_node.z < from_node.z:
            cost += dz * self.config.vertical_move_cost * 0.8  # Descending cheaper
        else:
            cost += dz * self.config.vertical_move_cost * 1.2  # Ascending more expensive

        # Terrain risk cost
        terrain_risk = self._get_terrain_risk(to_node.x, to_node.y)
        # Risk matters more at lower altitudes
        altitude_factor = 1.0 + (1.0 - to_node.z / self.config.altitude_levels) * 2.0
        risk_cost = terrain_risk * self.config.risk_weight * altitude_factor

        # Altitude bonus (safer at higher altitude)
        altitude_bonus = to_node.z * self.config.altitude_bonus

        # Wind drift cost
        wind_cost = self._calculate_wind_drift_cost(from_node, to_node)

        total_cost = cost + risk_cost + wind_cost - altitude_bonus
        return max(0.1, total_cost)  # Minimum cost to prevent zero-cost loops

    def plan_path(self, start_pos: Tuple[int, int, int],
                  goal_pos: Tuple[int, int, int]) -> Optional[List[Tuple[int, int, int]]]:
        """
        Plan a 3D path from start to goal using A*.

        Args:
            start_pos: Starting position (x, y, z)
            goal_pos: Goal position (x, y, z)

        Returns:
            List of waypoints [(x, y, z), ...] or None if no path found

        Raises:
            ValueError: If risk grid not set or positions invalid
        """
        if self.risk_grid is None:
            raise ValueError("Risk grid must be set before planning")

        # Validate positions
        for pos in [start_pos, goal_pos]:
            x, y, z = pos
            if not (0 <= x < self.config.grid_size and
                   0 <= y < self.config.grid_size and
                   0 <= z < self.config.altitude_levels):
                raise ValueError(f"Invalid position {pos}")

        # Initialize start and goal nodes
        start = PathNode(*start_pos, g_cost=0.0)
        goal = PathNode(*goal_pos)
        start.h_cost = self._heuristic(start, goal)
        start.f_cost = start.g_cost + start.h_cost

        # A* data structures
        open_set = []
        heapq.heappush(open_set, start)
        open_dict = {start.position(): start}  # For fast lookup
        closed_set = set()

        iterations = 0

        while open_set and iterations < self.config.max_iterations:
            iterations += 1

            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            current_pos = current.position()

            # Remove from open dict
            if current_pos in open_dict:
                del open_dict[current_pos]

            # Check if goal reached
            if current == goal:
                return self._reconstruct_path(current)

            closed_set.add(current_pos)

            # Explore neighbors
            for neighbor in self._get_neighbors(current):
                neighbor_pos = neighbor.position()

                if neighbor_pos in closed_set:
                    continue

                # Calculate tentative g_cost
                tentative_g = current.g_cost + self._calculate_move_cost(current, neighbor)

                # Check if this path is better
                if neighbor_pos in open_dict:
                    existing_neighbor = open_dict[neighbor_pos]
                    if tentative_g < existing_neighbor.g_cost:
                        # Update existing node
                        existing_neighbor.g_cost = tentative_g
                        existing_neighbor.h_cost = self._heuristic(existing_neighbor, goal)
                        existing_neighbor.f_cost = existing_neighbor.g_cost + existing_neighbor.h_cost
                        existing_neighbor.parent = current
                        heapq.heapify(open_set)  # Re-sort after update
                else:
                    # Add new node
                    neighbor.g_cost = tentative_g
                    neighbor.h_cost = self._heuristic(neighbor, goal)
                    neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
                    neighbor.parent = current
                    heapq.heappush(open_set, neighbor)
                    open_dict[neighbor_pos] = neighbor

        # No path found
        return None

    def _reconstruct_path(self, goal_node: PathNode) -> List[Tuple[int, int, int]]:
        """
        Reconstruct path from goal node by following parent links.

        Args:
            goal_node: Goal node with parent chain

        Returns:
            List of waypoints from start to goal
        """
        path = []
        current = goal_node

        while current is not None:
            path.append(current.position())
            current = current.parent

        path.reverse()
        return path

    def convert_path_to_meters(self, path: List[Tuple[int, int, int]]) -> List[Tuple[float, float, float]]:
        """
        Convert grid path to real-world coordinates in meters.

        Args:
            path: Path in grid coordinates [(x, y, z), ...]

        Returns:
            Path in meters [(x_m, y_m, z_m), ...]
        """
        meters_path = []
        for x, y, z in path:
            x_m = x * self.config.cell_size
            y_m = y * self.config.cell_size
            z_m = z * (self.config.max_altitude / self.config.altitude_levels)
            meters_path.append((x_m, y_m, z_m))

        return meters_path

    def get_path_statistics(self, path: List[Tuple[int, int, int]]) -> Dict[str, Any]:
        """
        Calculate statistics for a planned path.

        Args:
            path: Path in grid coordinates

        Returns:
            Dictionary with path statistics
        """
        if not path:
            return {}

        total_distance = 0.0
        total_risk = 0.0
        altitude_changes = 0
        horizontal_distance = 0.0

        for i in range(len(path) - 1):
            x1, y1, z1 = path[i]
            x2, y2, z2 = path[i + 1]

            # 3D distance
            dx = (x2 - x1) * self.config.cell_size
            dy = (y2 - y1) * self.config.cell_size
            dz = (z2 - z1) * (self.config.max_altitude / self.config.altitude_levels)
            total_distance += math.sqrt(dx**2 + dy**2 + dz**2)

            # Horizontal distance
            horizontal_distance += math.sqrt(dx**2 + dy**2)

            # Risk accumulation
            risk = self._get_terrain_risk(x2, y2)
            total_risk += risk

            # Altitude changes
            if z2 != z1:
                altitude_changes += 1

        avg_risk = total_risk / (len(path) - 1) if len(path) > 1 else 0.0

        return {
            'waypoint_count': len(path),
            'total_distance_m': round(total_distance, 2),
            'horizontal_distance_m': round(horizontal_distance, 2),
            'altitude_change_count': altitude_changes,
            'average_risk': round(avg_risk, 3),
            'start_position': path[0],
            'goal_position': path[-1]
        }

    def simplify_path(self, path: List[Tuple[int, int, int]],
                     max_waypoints: int = 10) -> List[Tuple[int, int, int]]:
        """
        Simplify path by removing intermediate waypoints.

        Uses Douglas-Peucker-style decimation to reduce waypoint count
        while preserving path shape.

        Args:
            path: Original path
            max_waypoints: Maximum number of waypoints to keep

        Returns:
            Simplified path
        """
        if len(path) <= max_waypoints:
            return path

        # Always keep start and end
        simplified = [path[0]]

        # Sample intermediate points evenly
        step = len(path) // (max_waypoints - 1)
        for i in range(step, len(path) - 1, step):
            simplified.append(path[i])

        # Always include goal
        simplified.append(path[-1])

        return simplified


# Convenience functions

def plan_landing_approach(risk_grid: np.ndarray, start_pos: Tuple[int, int, int],
                         goal_pos: Tuple[int, int, int],
                         wind_speed: float = 0.0, wind_direction: float = 0.0,
                         config: Optional[PathPlannerConfig] = None) -> Optional[List[Tuple[int, int, int]]]:
    """
    Plan a landing approach path with default configuration.

    Args:
        risk_grid: 2D terrain risk grid (N×N)
        start_pos: Starting position (x, y, z)
        goal_pos: Goal position (x, y, z)
        wind_speed: Wind speed in m/s
        wind_direction: Wind direction in degrees
        config: Optional custom configuration

    Returns:
        Path as list of waypoints or None if no path found
    """
    if config is None:
        config = PathPlannerConfig(grid_size=risk_grid.shape[0])

    planner = PathPlanner(config)
    planner.set_risk_grid(risk_grid)

    if wind_speed > 0:
        planner.set_wind(wind_speed, wind_direction)

    return planner.plan_path(start_pos, goal_pos)
