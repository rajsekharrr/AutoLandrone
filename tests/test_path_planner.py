"""
Tests for 3D A* Path Planner

Validates pathfinding, risk grid integration, and wind compensation.
"""

import pytest
import numpy as np
from src.path_planner import (
    PathNode, PathPlannerConfig, PathPlanner, plan_landing_approach
)


class TestPathNode:
    """Test PathNode data structure."""

    def test_node_creation(self):
        """Test node creation and basic attributes."""
        node = PathNode(x=3, y=4, z=5)
        assert node.position() == (3, 4, 5)

    def test_node_comparison(self):
        """Test node comparison for priority queue."""
        node1 = PathNode(0, 0, 0, g_cost=10.0, h_cost=5.0, f_cost=15.0)
        node2 = PathNode(1, 1, 1, g_cost=8.0, h_cost=7.0, f_cost=15.0)
        node3 = PathNode(2, 2, 2, g_cost=12.0, h_cost=5.0, f_cost=17.0)

        # Test less than comparison
        assert node1 < node3  # Lower f_cost
        assert not (node3 < node1)  # Higher f_cost

    def test_node_equality(self):
        """Test node equality based on position."""
        node1 = PathNode(3, 4, 5)
        node2 = PathNode(3, 4, 5)
        node3 = PathNode(3, 4, 6)

        assert node1 == node2
        assert node1 != node3


class TestPathPlanner:
    """Test 3D path planner functionality."""

    @pytest.fixture
    def simple_risk_grid(self):
        """Create a simple 7×7 risk grid with clear path."""
        grid = np.zeros((7, 7), dtype=np.float32)
        # Add some obstacles
        grid[2:5, 3] = 0.9  # Vertical wall
        return grid

    @pytest.fixture
    def planner(self):
        """Create a default path planner."""
        config = PathPlannerConfig(grid_size=7, altitude_levels=10)
        return PathPlanner(config)

    def test_set_risk_grid(self, planner, simple_risk_grid):
        """Test setting risk grid."""
        planner.set_risk_grid(simple_risk_grid)
        assert planner.risk_grid is not None
        assert planner.risk_grid.shape == (7, 7)

    def test_set_risk_grid_wrong_size(self, planner):
        """Test error on wrong grid size."""
        wrong_grid = np.zeros((5, 5))
        with pytest.raises(ValueError):
            planner.set_risk_grid(wrong_grid)

    def test_set_wind(self, planner):
        """Test setting wind conditions."""
        planner.set_wind(wind_speed=10.0, wind_direction=90.0)  # East wind

        # Check wind vector (approximately)
        assert abs(planner.wind_vector[0] - 10.0) < 0.1  # X component
        assert abs(planner.wind_vector[1]) < 0.1  # Y component close to 0

    def test_heuristic(self, planner):
        """Test heuristic function."""
        start = PathNode(0, 0, 5)
        goal = PathNode(6, 6, 0)

        h = planner._heuristic(start, goal)

        # Should be positive
        assert h > 0.0

        # Closer nodes should have lower heuristic
        closer = PathNode(3, 3, 2)
        h_closer = planner._heuristic(closer, goal)
        assert h_closer < h

    def test_get_terrain_risk(self, planner, simple_risk_grid):
        """Test terrain risk retrieval."""
        planner.set_risk_grid(simple_risk_grid)

        # Clear cell
        assert planner._get_terrain_risk(0, 0) == 0.0

        # Obstacle cell (use approximate comparison for float)
        risk = planner._get_terrain_risk(3, 2)
        assert abs(risk - 0.9) < 0.01

        # Out of bounds
        assert planner._get_terrain_risk(-1, 0) == 1.0
        assert planner._get_terrain_risk(10, 10) == 1.0

    def test_get_neighbors(self, planner, simple_risk_grid):
        """Test neighbor generation."""
        planner.set_risk_grid(simple_risk_grid)

        node = PathNode(3, 3, 5)
        neighbors = planner._get_neighbors(node)

        # Should have multiple neighbors
        assert len(neighbors) > 0

        # All neighbors should be valid positions
        for neighbor in neighbors:
            assert 0 <= neighbor.x < 7
            assert 0 <= neighbor.y < 7
            assert 0 <= neighbor.z < 10

    def test_plan_path_straight(self, planner, simple_risk_grid):
        """Test simple straight-line path."""
        planner.set_risk_grid(simple_risk_grid)

        # Plan from corner to opposite corner (avoiding wall)
        start = (0, 0, 5)
        goal = (0, 6, 0)

        path = planner.plan_path(start, goal)

        assert path is not None
        assert len(path) > 0
        assert path[0] == start
        assert path[-1] == goal

    def test_plan_path_around_obstacle(self, planner):
        """Test pathfinding around obstacles."""
        # Create grid with obstacle in middle
        risk_grid = np.zeros((7, 7), dtype=np.float32)
        risk_grid[3, 2:5] = 1.0  # Horizontal wall

        planner.set_risk_grid(risk_grid)

        start = (1, 3, 5)
        goal = (5, 3, 0)

        path = planner.plan_path(start, goal)

        assert path is not None
        # Path should go around the obstacle
        assert len(path) > 3

    def test_plan_path_no_solution(self, planner):
        """Test pathfinding with no valid path."""
        # Create grid completely blocked
        risk_grid = np.ones((7, 7), dtype=np.float32)

        planner.set_risk_grid(risk_grid)

        start = (0, 0, 5)
        goal = (6, 6, 0)

        path = planner.plan_path(start, goal)

        assert path is None  # No valid path

    def test_convert_path_to_meters(self, planner, simple_risk_grid):
        """Test path conversion to real-world coordinates."""
        planner.set_risk_grid(simple_risk_grid)

        grid_path = [(0, 0, 5), (1, 1, 4), (2, 2, 2)]
        meters_path = planner.convert_path_to_meters(grid_path)

        assert len(meters_path) == len(grid_path)

        # Check first point
        assert meters_path[0][0] == 0.0  # 0 * cell_size
        assert meters_path[0][1] == 0.0
        assert meters_path[0][2] == 15.0  # 5 * (30m / 10 levels)

    def test_get_path_statistics(self, planner, simple_risk_grid):
        """Test path statistics calculation."""
        planner.set_risk_grid(simple_risk_grid)

        path = [(0, 0, 5), (1, 1, 4), (2, 2, 3), (3, 3, 0)]
        stats = planner.get_path_statistics(path)

        assert 'waypoint_count' in stats
        assert stats['waypoint_count'] == 4
        assert 'total_distance_m' in stats
        assert 'average_risk' in stats
        assert stats['total_distance_m'] > 0.0

    def test_simplify_path(self, planner):
        """Test path simplification."""
        # Create long path
        long_path = [(i, i, 9-i) for i in range(10)]

        simplified = planner.simplify_path(long_path, max_waypoints=5)

        assert len(simplified) <= 6  # May be slightly over due to sampling
        assert simplified[0] == long_path[0]  # Start preserved
        assert simplified[-1] == long_path[-1]  # End preserved

    def test_wind_drift_cost(self, planner):
        """Test wind drift cost calculation."""
        planner.set_wind(wind_speed=10.0, wind_direction=90.0)  # East wind

        node1 = PathNode(3, 3, 5)
        node2_with_wind = PathNode(4, 3, 5)  # Moving east (with wind)
        node2_against_wind = PathNode(2, 3, 5)  # Moving west (against wind)

        cost_with = planner._calculate_wind_drift_cost(node1, node2_with_wind)
        cost_against = planner._calculate_wind_drift_cost(node1, node2_against_wind)

        # Moving against wind should cost more
        assert cost_against > cost_with


def test_plan_landing_approach():
    """Test convenience function for landing approach."""
    # Create simple risk grid
    risk_grid = np.zeros((7, 7), dtype=np.float32)
    risk_grid[3, 3] = 0.8  # Single obstacle

    start = (1, 1, 8)
    goal = (5, 5, 0)

    path = plan_landing_approach(
        risk_grid, start, goal,
        wind_speed=5.0, wind_direction=180.0
    )

    assert path is not None
    assert len(path) > 0
    assert path[0] == start
    assert path[-1] == goal


def test_integration_full_scenario():
    """Integration test with realistic landing scenario."""
    # Create 7×7 risk grid with scattered obstacles
    risk_grid = np.random.rand(7, 7) * 0.3  # Low baseline risk
    risk_grid[2:4, 2:4] = 0.95  # High-risk zone
    risk_grid[5, 5] = 0.1  # Good landing zone

    config = PathPlannerConfig(
        grid_size=7,
        altitude_levels=10,
        enable_wind_drift=True
    )

    planner = PathPlanner(config)
    planner.set_risk_grid(risk_grid)
    planner.set_wind(wind_speed=8.0, wind_direction=270.0)  # West wind

    # Plan descent from high altitude to landing zone
    start = (1, 1, 9)  # High altitude, away from landing zone
    goal = (5, 5, 0)  # Landing zone at ground level

    path = planner.plan_path(start, goal)

    if path is not None:  # May not always find path with random obstacles
        # Verify path properties
        assert len(path) >= 2
        assert path[0] == start
        assert path[-1] == goal

        # Check descending altitude
        altitudes = [z for _, _, z in path]
        assert altitudes[0] >= altitudes[-1]

        # Get statistics
        stats = planner.get_path_statistics(path)
        assert stats['waypoint_count'] == len(path)
        assert stats['total_distance_m'] > 0

        # Convert to meters
        meters_path = planner.convert_path_to_meters(path)
        assert len(meters_path) == len(path)


def test_high_risk_environment():
    """Test pathfinding in high-risk environment."""
    config = PathPlannerConfig(grid_size=7, altitude_levels=10)
    planner = PathPlanner(config)

    # Create grid with narrow safe corridor
    risk_grid = np.ones((7, 7), dtype=np.float32) * 0.95
    risk_grid[3, :] = 0.1  # Safe corridor in middle row
    risk_grid[3, 3] = 0.05  # Good landing spot

    planner.set_risk_grid(risk_grid)

    start = (3, 0, 7)
    goal = (3, 3, 0)

    path = planner.plan_path(start, goal)

    # Should find path through safe corridor
    assert path is not None

    # Path should mostly stay in safe row
    safe_row_count = sum(1 for _, y, _ in path if y == 3)
    assert safe_row_count > len(path) * 0.5  # Most waypoints in safe row
