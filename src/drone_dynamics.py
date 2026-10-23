"""
Drone Dynamics Simulator

Production-ready 10Hz PID kinematic drone simulator with wind disturbances.
Models 3DOF position control (x, y, z) with realistic constraints and noise.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, Optional, List
import time


@dataclass
class DroneConfig:
    """Configuration for drone dynamics and PID controllers."""
    # Physical limits
    max_velocity: float = 10.0  # m/s
    max_acceleration: float = 5.0  # m/s^2
    max_tilt_angle: float = 30.0  # degrees

    # PID gains for position control (X, Y, Z)
    pid_p: Tuple[float, float, float] = (1.2, 1.2, 1.5)
    pid_i: Tuple[float, float, float] = (0.1, 0.1, 0.15)
    pid_d: Tuple[float, float, float] = (0.8, 0.8, 1.0)

    # Physical parameters
    mass: float = 2.5  # kg
    drag_coefficient: float = 0.1

    # Simulation
    update_rate: float = 10.0  # Hz

    # Noise and disturbances
    position_noise_std: float = 0.05  # meters
    velocity_noise_std: float = 0.02  # m/s
    wind_gust_probability: float = 0.05  # 5% chance per timestep


@dataclass
class DroneState:
    """Complete drone state representation."""
    # Position (m)
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Velocity (m/s)
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Target waypoint
    target: Optional[np.ndarray] = None

    # PID controller state
    integral_error: np.ndarray = field(default_factory=lambda: np.zeros(3))
    previous_error: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Wind disturbance
    wind_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Timestamps
    last_update_time: float = field(default_factory=time.time)

    # Mission state
    is_landed: bool = False
    waypoint_reached: bool = False


class PIDController:
    """3-axis PID controller for position tracking."""

    def __init__(self, kp: Tuple[float, float, float],
                 ki: Tuple[float, float, float],
                 kd: Tuple[float, float, float]):
        """
        Initialize PID controller.

        Args:
            kp: Proportional gains (x, y, z)
            ki: Integral gains (x, y, z)
            kd: Derivative gains (x, y, z)
        """
        self.kp = np.array(kp)
        self.ki = np.array(ki)
        self.kd = np.array(kd)

        self.integral = np.zeros(3)
        self.prev_error = np.zeros(3)

        # Anti-windup limits
        self.integral_limit = 10.0

    def compute(self, error: np.ndarray, dt: float) -> np.ndarray:
        """
        Compute PID control output.

        Args:
            error: Position error (target - current)
            dt: Time step

        Returns:
            Control command (acceleration)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
        i_term = self.ki * self.integral

        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else np.zeros(3)
        d_term = self.kd * derivative

        self.prev_error = error.copy()

        # Total control output
        output = p_term + i_term + d_term

        return output

    def reset(self):
        """Reset controller state."""
        self.integral = np.zeros(3)
        self.prev_error = np.zeros(3)


class DroneDynamics:
    """
    Kinematic drone simulator with PID control and wind disturbances.

    Simulates 3DOF position control at 10Hz with realistic constraints.
    """

    def __init__(self, config: Optional[DroneConfig] = None):
        """
        Initialize drone dynamics simulator.

        Args:
            config: Drone configuration (uses default if None)
        """
        self.config = config or DroneConfig()
        self.state = DroneState()

        # Initialize PID controller
        self.pid = PIDController(
            self.config.pid_p,
            self.config.pid_i,
            self.config.pid_d
        )

        # Random number generator for reproducibility
        self.rng = np.random.RandomState(42)

        # Telemetry history
        self.position_history: List[np.ndarray] = []
        self.velocity_history: List[np.ndarray] = []
        self.target_history: List[np.ndarray] = []
        self.time_history: List[float] = []

    def set_position(self, position: np.ndarray):
        """Set current position."""
        self.state.position = np.array(position, dtype=float)

    def set_target(self, target: np.ndarray):
        """Set target waypoint."""
        self.state.target = np.array(target, dtype=float)
        self.state.waypoint_reached = False

    def set_wind(self, wind_velocity: np.ndarray):
        """Set persistent wind velocity."""
        self.state.wind_velocity = np.array(wind_velocity, dtype=float)

    def update(self, dt: Optional[float] = None) -> DroneState:
        """
        Update drone dynamics for one timestep.

        Args:
            dt: Time step (uses config update_rate if None)

        Returns:
            Updated drone state
        """
        if dt is None:
            dt = 1.0 / self.config.update_rate

        # Check if we have a target
        if self.state.target is None or self.state.is_landed:
            return self.state

        # Calculate position error
        error = self.state.target - self.state.position
        distance = np.linalg.norm(error)

        # Check if waypoint reached (threshold: 0.3m)
        if distance < 0.3:
            self.state.waypoint_reached = True
            self.state.velocity = np.zeros(3)

            # Check if landed (altitude near zero)
            if self.state.position[2] < 0.5:
                self.state.is_landed = True
                self.state.position[2] = 0.0

            return self.state

        # PID control
        control_acceleration = self.pid.compute(error, dt)

        # Apply physical limits
        control_acceleration = np.clip(
            control_acceleration,
            -self.config.max_acceleration,
            self.config.max_acceleration
        )

        # Wind disturbances
        wind_force = self.state.wind_velocity * self.config.drag_coefficient

        # Random wind gusts
        if self.rng.rand() < self.config.wind_gust_probability:
            gust = self.rng.randn(3) * 2.0
            wind_force += gust

        # Total acceleration
        total_acceleration = control_acceleration + wind_force / self.config.mass

        # Update velocity
        self.state.velocity += total_acceleration * dt

        # Apply velocity limits
        velocity_magnitude = np.linalg.norm(self.state.velocity)
        if velocity_magnitude > self.config.max_velocity:
            self.state.velocity = (self.state.velocity / velocity_magnitude) * self.config.max_velocity

        # Update position
        self.state.position += self.state.velocity * dt

        # Add sensor noise
        position_noise = self.rng.randn(3) * self.config.position_noise_std
        self.state.position += position_noise

        # Enforce ground constraint
        if self.state.position[2] < 0:
            self.state.position[2] = 0.0
            self.state.velocity[2] = 0.0
            self.state.is_landed = True

        # Record telemetry
        self.position_history.append(self.state.position.copy())
        self.velocity_history.append(self.state.velocity.copy())
        self.target_history.append(self.state.target.copy())
        self.time_history.append(time.time())

        self.state.last_update_time = time.time()

        return self.state

    def get_state(self) -> DroneState:
        """Get current drone state."""
        return self.state

    def get_telemetry(self) -> dict:
        """
        Get complete telemetry data.

        Returns:
            Dictionary with position, velocity, and target histories
        """
        return {
            'position': np.array(self.position_history),
            'velocity': np.array(self.velocity_history),
            'target': np.array(self.target_history),
            'time': np.array(self.time_history)
        }

    def reset(self):
        """Reset simulator to initial state."""
        self.state = DroneState()
        self.pid.reset()
        self.position_history.clear()
        self.velocity_history.clear()
        self.target_history.clear()
        self.time_history.clear()

    def get_position_error(self) -> float:
        """Get current position error magnitude."""
        if self.state.target is None:
            return 0.0
        return float(np.linalg.norm(self.state.target - self.state.position))

    def get_velocity_magnitude(self) -> float:
        """Get current velocity magnitude."""
        return float(np.linalg.norm(self.state.velocity))


class WaypointTracker:
    """
    Tracks progress through a sequence of waypoints.

    Manages waypoint switching and mission completion.
    """

    def __init__(self, waypoints: List[np.ndarray], arrival_threshold: float = 0.3):
        """
        Initialize waypoint tracker.

        Args:
            waypoints: List of waypoint positions
            arrival_threshold: Distance threshold for waypoint arrival (meters)
        """
        self.waypoints = [np.array(wp, dtype=float) for wp in waypoints]
        self.arrival_threshold = arrival_threshold
        self.current_index = 0
        self.mission_complete = False

    def update(self, current_position: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        """
        Update tracker and get current target waypoint.

        Args:
            current_position: Current drone position

        Returns:
            (current_target_waypoint, mission_complete)
        """
        if self.mission_complete or len(self.waypoints) == 0:
            return None, True

        # Get current target
        current_target = self.waypoints[self.current_index]

        # Check if waypoint reached
        distance = np.linalg.norm(current_position - current_target)

        if distance < self.arrival_threshold:
            # Move to next waypoint
            self.current_index += 1

            if self.current_index >= len(self.waypoints):
                self.mission_complete = True
                return None, True

            # Return next waypoint
            return self.waypoints[self.current_index], False

        return current_target, False

    def get_current_waypoint(self) -> Optional[np.ndarray]:
        """Get current target waypoint without updating."""
        if self.mission_complete or self.current_index >= len(self.waypoints):
            return None
        return self.waypoints[self.current_index]

    def get_progress(self) -> float:
        """Get mission progress (0.0 to 1.0)."""
        if len(self.waypoints) == 0:
            return 1.0
        return min(1.0, self.current_index / len(self.waypoints))

    def get_remaining_waypoints(self) -> List[np.ndarray]:
        """Get list of remaining waypoints."""
        if self.mission_complete:
            return []
        return self.waypoints[self.current_index:]

    def insert_waypoint(self, waypoint: np.ndarray, index: Optional[int] = None):
        """
        Insert a new waypoint into the mission.

        Args:
            waypoint: New waypoint position
            index: Insert position (None = insert after current)
        """
        if index is None:
            index = self.current_index + 1

        self.waypoints.insert(index, np.array(waypoint, dtype=float))

    def replace_remaining_waypoints(self, new_waypoints: List[np.ndarray]):
        """
        Replace all remaining waypoints (for re-planning).

        Args:
            new_waypoints: New waypoint sequence
        """
        # Keep waypoints up to current, replace the rest
        self.waypoints = self.waypoints[:self.current_index] + [
            np.array(wp, dtype=float) for wp in new_waypoints
        ]
        self.mission_complete = False


def simulate_trajectory(waypoints: List[np.ndarray],
                       wind_velocity: np.ndarray = np.zeros(3),
                       config: Optional[DroneConfig] = None,
                       max_steps: int = 10000) -> dict:
    """
    Simulate complete trajectory through waypoints.

    Args:
        waypoints: List of waypoint positions
        wind_velocity: Wind disturbance vector
        config: Drone configuration
        max_steps: Maximum simulation steps

    Returns:
        Dictionary with simulation results
    """
    # Initialize dynamics and tracker
    dynamics = DroneDynamics(config)
    tracker = WaypointTracker(waypoints)

    # Set initial position (first waypoint)
    if len(waypoints) > 0:
        dynamics.set_position(waypoints[0])

    dynamics.set_wind(wind_velocity)

    # Simulation loop
    step = 0
    while step < max_steps and not tracker.mission_complete:
        # Get current target
        current_target, complete = tracker.update(dynamics.state.position)

        if complete:
            break

        # Update drone target
        if current_target is not None:
            dynamics.set_target(current_target)

        # Step dynamics
        dynamics.update()
        step += 1

    # Return results
    telemetry = dynamics.get_telemetry()

    return {
        'telemetry': telemetry,
        'mission_complete': tracker.mission_complete,
        'steps': step,
        'final_position': dynamics.state.position.copy(),
        'waypoints_reached': tracker.current_index
    }
