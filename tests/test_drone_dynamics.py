"""
Tests for Drone Dynamics Simulator

Validates PID control, waypoint tracking, and wind disturbances.
"""

import pytest
import numpy as np
from src.drone_dynamics import (
    DroneConfig, DroneState, DroneDynamics, PIDController,
    WaypointTracker, simulate_trajectory
)


class TestPIDController:
    """Test PID controller."""

    def test_initialization(self):
        """Test PID controller initialization."""
        pid = PIDController((1.0, 1.0, 1.0), (0.1, 0.1, 0.1), (0.5, 0.5, 0.5))
        assert np.allclose(pid.kp, [1.0, 1.0, 1.0])
        assert np.allclose(pid.ki, [0.1, 0.1, 0.1])
        assert np.allclose(pid.kd, [0.5, 0.5, 0.5])

    def test_compute(self):
        """Test PID computation."""
        pid = PIDController((1.0, 1.0, 1.0), (0.1, 0.1, 0.1), (0.5, 0.5, 0.5))
        error = np.array([1.0, 0.0, -1.0])
        output = pid.compute(error, dt=0.1)

        assert output.shape == (3,)
        # P term should dominate
        assert abs(output[0]) > 0
        assert abs(output[2]) > 0

    def test_reset(self):
        """Test PID reset."""
        pid = PIDController((1.0, 1.0, 1.0), (0.1, 0.1, 0.1), (0.5, 0.5, 0.5))
        pid.compute(np.array([1.0, 1.0, 1.0]), 0.1)

        pid.reset()
        assert np.allclose(pid.integral, [0, 0, 0])
        assert np.allclose(pid.prev_error, [0, 0, 0])


class TestDroneDynamics:
    """Test drone dynamics simulator."""

    @pytest.fixture
    def dynamics(self):
        """Create drone dynamics instance."""
        return DroneDynamics()

    def test_initialization(self, dynamics):
        """Test initialization."""
        assert dynamics.state.position is not None
        assert np.allclose(dynamics.state.position, [0, 0, 0])

    def test_set_position(self, dynamics):
        """Test setting position."""
        dynamics.set_position(np.array([1.0, 2.0, 3.0]))
        assert np.allclose(dynamics.state.position, [1.0, 2.0, 3.0])

    def test_set_target(self, dynamics):
        """Test setting target."""
        dynamics.set_target(np.array([5.0, 5.0, 5.0]))
        assert np.allclose(dynamics.state.target, [5.0, 5.0, 5.0])
        assert not dynamics.state.waypoint_reached

    def test_update_no_target(self, dynamics):
        """Test update with no target."""
        dynamics.set_position(np.array([1.0, 1.0, 1.0]))
        state = dynamics.update(dt=0.1)

        # Should not move without target
        assert np.allclose(state.position, [1.0, 1.0, 1.0])

    def test_update_towards_target(self, dynamics):
        """Test movement towards target."""
        dynamics.set_position(np.array([0.0, 0.0, 1.0]))
        dynamics.set_target(np.array([5.0, 0.0, 1.0]))

        # Run several updates
        for _ in range(10):
            dynamics.update(dt=0.1)

        # Should have moved closer
        assert dynamics.state.position[0] > 0.0
        assert dynamics.state.position[0] < 5.0

    def test_waypoint_reached(self, dynamics):
        """Test waypoint reached detection."""
        dynamics.set_position(np.array([1.0, 1.0, 1.0]))
        dynamics.set_target(np.array([1.1, 1.1, 1.1]))

        # Run updates until reached
        for _ in range(20):
            dynamics.update(dt=0.1)
            if dynamics.state.waypoint_reached:
                break

        assert dynamics.state.waypoint_reached

    def test_wind_disturbance(self, dynamics):
        """Test wind affects trajectory."""
        dynamics.set_position(np.array([0.0, 0.0, 5.0]))
        dynamics.set_target(np.array([10.0, 0.0, 5.0]))
        dynamics.set_wind(np.array([0.0, 5.0, 0.0]))  # Side wind

        for _ in range(20):
            dynamics.update(dt=0.1)

        # Wind should cause drift in Y direction
        assert abs(dynamics.state.position[1]) > 0.1

    def test_ground_constraint(self, dynamics):
        """Test ground constraint."""
        dynamics.set_position(np.array([0.0, 0.0, 0.5]))
        dynamics.set_target(np.array([0.0, 0.0, -1.0]))

        dynamics.update(dt=0.1)

        # Should not go below ground
        assert dynamics.state.position[2] >= 0.0

    def test_reset(self, dynamics):
        """Test reset."""
        dynamics.set_position(np.array([5.0, 5.0, 5.0]))
        dynamics.set_target(np.array([10.0, 10.0, 10.0]))
        dynamics.update(dt=0.1)

        dynamics.reset()

        assert np.allclose(dynamics.state.position, [0, 0, 0])
        assert len(dynamics.position_history) == 0


class TestWaypointTracker:
    """Test waypoint tracker."""

    def test_initialization(self):
        """Test tracker initialization."""
        waypoints = [np.array([0, 0, 0]), np.array([5, 5, 5]), np.array([10, 10, 0])]
        tracker = WaypointTracker(waypoints)

        assert len(tracker.waypoints) == 3
        assert tracker.current_index == 0
        assert not tracker.mission_complete

    def test_get_current_waypoint(self):
        """Test getting current waypoint."""
        waypoints = [np.array([0, 0, 0]), np.array([5, 5, 5])]
        tracker = WaypointTracker(waypoints)

        wp = tracker.get_current_waypoint()
        assert np.allclose(wp, [0, 0, 0])

    def test_waypoint_progression(self):
        """Test progression through waypoints."""
        waypoints = [np.array([0, 0, 0]), np.array([5, 5, 5]), np.array([10, 10, 0])]
        tracker = WaypointTracker(waypoints, arrival_threshold=0.5)

        # Arrive at first waypoint
        current_target, complete = tracker.update(np.array([0.1, 0.1, 0.1]))
        assert not complete
        assert np.allclose(current_target, [5, 5, 5])

        # Arrive at second waypoint
        current_target, complete = tracker.update(np.array([5.1, 5.1, 5.1]))
        assert not complete
        assert np.allclose(current_target, [10, 10, 0])

        # Arrive at final waypoint
        current_target, complete = tracker.update(np.array([10.1, 10.1, 0.1]))
        assert complete
        assert current_target is None

    def test_progress(self):
        """Test progress calculation."""
        waypoints = [np.array([0, 0, 0]), np.array([5, 5, 5]), np.array([10, 10, 0])]
        tracker = WaypointTracker(waypoints)

        assert tracker.get_progress() == 0.0

        tracker.current_index = 1
        assert tracker.get_progress() == pytest.approx(1/3, rel=0.01)

        tracker.current_index = 3
        assert tracker.get_progress() == 1.0

    def test_insert_waypoint(self):
        """Test inserting waypoint."""
        waypoints = [np.array([0, 0, 0]), np.array([10, 10, 0])]
        tracker = WaypointTracker(waypoints)

        tracker.insert_waypoint(np.array([5, 5, 5]), index=1)

        assert len(tracker.waypoints) == 3
        assert np.allclose(tracker.waypoints[1], [5, 5, 5])

    def test_replace_remaining_waypoints(self):
        """Test replacing remaining waypoints (re-planning)."""
        waypoints = [np.array([0, 0, 0]), np.array([5, 5, 5]), np.array([10, 10, 0])]
        tracker = WaypointTracker(waypoints)

        tracker.current_index = 1

        new_waypoints = [np.array([7, 7, 3]), np.array([12, 12, 0])]
        tracker.replace_remaining_waypoints(new_waypoints)

        assert len(tracker.waypoints) == 3
        assert np.allclose(tracker.waypoints[1], [7, 7, 3])
        assert np.allclose(tracker.waypoints[2], [12, 12, 0])


def test_simulate_trajectory():
    """Test complete trajectory simulation."""
    waypoints = [
        np.array([0.0, 0.0, 10.0]),
        np.array([10.0, 0.0, 10.0]),
        np.array([10.0, 10.0, 5.0]),
        np.array([10.0, 10.0, 0.0])
    ]

    wind = np.array([2.0, 0.0, 0.0])

    result = simulate_trajectory(waypoints, wind_velocity=wind, max_steps=1000)

    assert 'telemetry' in result
    assert 'mission_complete' in result
    assert result['steps'] > 0

    # Check telemetry
    telemetry = result['telemetry']
    assert len(telemetry['position']) > 0
    assert len(telemetry['velocity']) > 0


def test_integration_with_wind():
    """Integration test with wind disturbance."""
    config = DroneConfig(max_velocity=15.0, update_rate=10.0)
    dynamics = DroneDynamics(config)

    # Set initial position and target
    dynamics.set_position(np.array([0.0, 0.0, 20.0]))
    dynamics.set_target(np.array([20.0, 0.0, 0.0]))

    # Strong crosswind
    dynamics.set_wind(np.array([0.0, 8.0, 0.0]))

    # Simulate for 50 steps
    for _ in range(50):
        dynamics.update(dt=0.1)

    # Should have moved forward and been pushed sideways
    assert dynamics.state.position[0] > 5.0  # Forward progress
    assert abs(dynamics.state.position[1]) > 0.1  # Wind drift (some lateral movement)
    assert dynamics.state.position[2] < 20.0  # Descending


def test_landing_scenario():
    """Test realistic landing scenario."""
    dynamics = DroneDynamics()

    # Start at altitude
    dynamics.set_position(np.array([5.0, 5.0, 15.0]))

    # Target ground
    dynamics.set_target(np.array([5.0, 5.0, 0.0]))

    # Simulate until landed
    max_iterations = 500
    for i in range(max_iterations):
        dynamics.update(dt=0.1)
        if dynamics.state.is_landed:
            break

    # Should have landed
    assert dynamics.state.is_landed
    assert dynamics.state.position[2] == 0.0
    assert i < max_iterations  # Should not timeout
