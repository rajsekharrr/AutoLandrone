"""
Refactored Landing Controller with Closed-Loop Trajectory Tracking

Integrates drone dynamics, path planning, decision engine, and real-time
obstacle avoidance with re-planning capabilities.
"""

from src.decision_engine import DecisionEngine
from src.landing_zone_grid import LandingZoneGrid
from src.drone_dynamics import DroneDynamics, DroneConfig, WaypointTracker
from src.path_planner import PathPlanner, PathPlannerConfig
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import time


class LandingController:
    """
    Advanced landing controller with closed-loop trajectory tracking.

    Features:
    - 10Hz PID position control
    - Real-time waypoint tracking
    - Mid-flight obstacle detection and re-planning
    - ML-based energy management
    - Wind disturbance handling
    """

    def __init__(self, use_grid_simulation: bool = False, grid_size: int = 7,
                 enable_ml: bool = False, enable_dynamics: bool = False):
        """
        Initialize the landing controller.

        Args:
            use_grid_simulation: Enable 2D grid-based landing zone simulation
            grid_size: Size of the landing zone grid (default 7x7)
            enable_ml: Enable ML-based energy prediction
            enable_dynamics: Enable drone dynamics simulation
        """
        # Core components
        self.use_grid_simulation = use_grid_simulation
        self.grid = LandingZoneGrid(grid_size=grid_size) if use_grid_simulation else None

        # ML components
        self.enable_ml = enable_ml
        self.energy_predictor = None
        self.path_planner = None

        if enable_ml:
            try:
                from src.energy_ml_model import load_or_create_energy_model
                self.energy_predictor = load_or_create_energy_model()
                self.path_planner = PathPlanner(PathPlannerConfig(grid_size=grid_size))
            except Exception as e:
                print(f"Warning: ML components not available: {e}")
                self.enable_ml = False

        # Decision engine
        self.decision_engine = DecisionEngine(
            enable_ml_energy=self.enable_ml,
            enable_path_planning=self.enable_ml,
            energy_predictor=self.energy_predictor,
            path_planner=self.path_planner
        )

        # Dynamics simulation
        self.enable_dynamics = enable_dynamics
        self.dynamics = DroneDynamics() if enable_dynamics else None
        self.waypoint_tracker: Optional[WaypointTracker] = None

        # Mission state
        self.current_state = None
        self.current_action = None
        self.current_plan = None
        self.mission_active = False
        self.mission_start_time = None

        # Re-planning state
        self.replan_count = 0
        self.obstacles_detected = []

        # Telemetry
        self.telemetry_history = []

    def set_grid_obstacles(self, obstacle_positions: List[Tuple[int, int]]):
        """Set obstacle positions in the grid simulation."""
        if self.grid:
            self.grid.set_obstacles(obstacle_positions)

    def inject_obstacle_runtime(self, obstacle_position: Tuple[int, int]) -> bool:
        """
        Inject obstacle at runtime (mid-flight).

        Triggers re-planning if obstacle blocks current path.

        Args:
            obstacle_position: Grid position (row, col) of new obstacle

        Returns:
            True if re-planning was triggered
        """
        if not self.grid or not self.mission_active:
            return False

        # Add obstacle to grid
        self.grid.set_obstacle(obstacle_position[0], obstacle_position[1])
        self.obstacles_detected.append({
            'position': obstacle_position,
            'time': time.time(),
            'mission_time': time.time() - self.mission_start_time if self.mission_start_time else 0
        })

        # Check if current path is affected
        if self.waypoint_tracker and self.dynamics:
            current_pos = self.dynamics.state.position
            remaining_waypoints = self.waypoint_tracker.get_remaining_waypoints()

            # Convert grid obstacle to meters for comparison
            cell_size = 5.0
            obstacle_meters = np.array([
                obstacle_position[1] * cell_size,
                obstacle_position[0] * cell_size,
                0.0
            ])

            # Check if any remaining waypoint is near the obstacle
            needs_replan = False
            for wp in remaining_waypoints:
                dist = np.linalg.norm(wp[:2] - obstacle_meters[:2])
                if dist < cell_size * 1.5:  # Within 1.5 cells
                    needs_replan = True
                    break

            if needs_replan:
                print(f"\n[OBSTACLE DETECTED] Re-planning required at {obstacle_position}")
                self.replan_trajectory()
                return True

        return False

    def replan_trajectory(self) -> bool:
        """
        Re-plan trajectory to avoid new obstacles.

        Finds next-best safe landing zone and computes new path.

        Returns:
            True if re-planning successful
        """
        if not self.grid or not self.dynamics or not self.waypoint_tracker:
            return False

        self.replan_count += 1
        print(f"[REPLAN #{self.replan_count}] Computing new trajectory...")

        # Get current position in grid coordinates
        current_pos_m = self.dynamics.state.position
        cell_size = 5.0
        current_grid_pos = (
            int(current_pos_m[1] / cell_size),
            int(current_pos_m[0] / cell_size)
        )

        # Get updated risk grid
        risk_grid = self.grid.ml_risk_grid if self.grid.ml_risk_grid is not None else np.zeros((7, 7))

        # Update risk grid with new obstacles
        for row in range(7):
            for col in range(7):
                if self.grid.grid[row][col] == 'obstacle':
                    risk_grid[row, col] = 1.0

        # Find next-best safe landing zone
        scorer = self.decision_engine.scorer
        top_zones = scorer.rank_landing_zones(
            drone_position=current_grid_pos,
            risk_grid=risk_grid,
            max_risk_threshold=0.5,
            top_k=3
        )

        if not top_zones:
            print("[REPLAN] No safe landing zones available!")
            return False

        # Select best alternative zone
        best_zone = top_zones[0]
        target_cell = best_zone['cell']

        print(f"[REPLAN] New target: Cell {target_cell} (cost: {best_zone['total_cost']:.2f})")

        # Compute new path
        if self.path_planner:
            try:
                # Convert positions to path planner coordinates
                current_altitude_level = int(current_pos_m[2] / 3.0)  # Assume 3m per level
                start_pos = (current_grid_pos[1], current_grid_pos[0], current_altitude_level)
                goal_pos = (target_cell[1], target_cell[0], 0)

                self.path_planner.set_risk_grid(risk_grid)
                new_path = self.path_planner.plan_path(start_pos, goal_pos)

                if new_path:
                    # Convert path to waypoints in meters
                    new_waypoints = self.path_planner.convert_path_to_meters(new_path)
                    new_waypoints_array = [np.array(wp) for wp in new_waypoints]

                    # Update waypoint tracker
                    self.waypoint_tracker.replace_remaining_waypoints(new_waypoints_array)

                    print(f"[REPLAN] New path computed: {len(new_waypoints)} waypoints")
                    return True
                else:
                    print("[REPLAN] Path planning failed!")
                    return False

            except Exception as e:
                print(f"[REPLAN] Error: {e}")
                return False

        return False

    def start_mission(self, initial_position: np.ndarray, target_cell: Tuple[int, int],
                     risk_grid: Optional[np.ndarray] = None) -> bool:
        """
        Start autonomous landing mission.

        Args:
            initial_position: Starting position [x, y, z] in meters
            target_cell: Target landing cell (row, col)
            risk_grid: Optional risk grid (uses grid state if None)

        Returns:
            True if mission started successfully
        """
        if not self.enable_dynamics or self.dynamics is None:
            print("Error: Dynamics not enabled")
            return False

        # Initialize dynamics
        self.dynamics.reset()
        self.dynamics.set_position(initial_position)

        # Get or create risk grid
        if risk_grid is None and self.grid:
            if self.grid.ml_risk_grid is not None:
                risk_grid = self.grid.ml_risk_grid
            else:
                risk_grid = np.zeros((7, 7))

        # Plan initial path
        if self.path_planner and risk_grid is not None:
            try:
                # Convert positions
                cell_size = 5.0
                current_grid_pos = (
                    int(initial_position[1] / cell_size),
                    int(initial_position[0] / cell_size)
                )
                current_altitude_level = int(initial_position[2] / 3.0)

                start_pos = (current_grid_pos[1], current_grid_pos[0], current_altitude_level)
                goal_pos = (target_cell[1], target_cell[0], 0)

                self.path_planner.set_risk_grid(risk_grid)
                path = self.path_planner.plan_path(start_pos, goal_pos)

                if path:
                    waypoints = self.path_planner.convert_path_to_meters(path)
                    waypoints_array = [np.array(wp) for wp in waypoints]

                    self.waypoint_tracker = WaypointTracker(waypoints_array)
                    self.current_plan = path

                    self.mission_active = True
                    self.mission_start_time = time.time()
                    self.replan_count = 0
                    self.obstacles_detected.clear()

                    print(f"[MISSION] Started with {len(waypoints)} waypoints")
                    return True
                else:
                    print("[MISSION] Path planning failed")
                    return False

            except Exception as e:
                print(f"[MISSION] Error: {e}")
                return False

        return False

    def update_mission(self, dt: float = 0.1) -> Dict[str, Any]:
        """
        Update mission state (call at 10Hz).

        Args:
            dt: Time step (seconds)

        Returns:
            Mission status dictionary
        """
        if not self.mission_active or not self.dynamics or not self.waypoint_tracker:
            return {'active': False}

        # Get current target from tracker
        current_target, complete = self.waypoint_tracker.update(self.dynamics.state.position)

        if complete:
            self.mission_active = False
            return {
                'active': False,
                'complete': True,
                'final_position': self.dynamics.state.position.copy(),
                'mission_time': time.time() - self.mission_start_time if self.mission_start_time else 0
            }

        # Update dynamics
        if current_target is not None:
            self.dynamics.set_target(current_target)

        self.dynamics.update(dt)

        # Record telemetry
        telemetry = {
            'time': time.time(),
            'position': self.dynamics.state.position.copy(),
            'velocity': self.dynamics.state.velocity.copy(),
            'target': current_target.copy() if current_target is not None else None,
            'waypoint_index': self.waypoint_tracker.current_index,
            'progress': self.waypoint_tracker.get_progress()
        }
        self.telemetry_history.append(telemetry)

        return {
            'active': True,
            'complete': False,
            'position': self.dynamics.state.position.copy(),
            'velocity': self.dynamics.state.velocity.copy(),
            'target': current_target.copy() if current_target is not None else None,
            'progress': self.waypoint_tracker.get_progress(),
            'mission_time': time.time() - self.mission_start_time if self.mission_start_time else 0,
            'replans': self.replan_count
        }

    def process_telemetry(self, battery_percent, obstacle_distance, scan_result=None, **kwargs):
        """
        Process telemetry and determine landing action (legacy compatible).

        Args:
            battery_percent: Current battery percentage
            obstacle_distance: Distance to obstacle below (meters)
            scan_result: Legacy scan result for backward compatibility
            **kwargs: Additional parameters for ML decision engine

        Returns:
            Tuple of (state, action, reason) or extended tuple with extra_data
        """
        nearest_safe_cell = None

        # If using grid simulation and conditions trigger scanning
        if self.use_grid_simulation and self.grid:
            # Trigger grid scan when battery is critical and obstacle detected
            if battery_percent <= 20.0 and obstacle_distance < 1.5:
                nearest_safe_cell = self.grid.find_nearest_safe_cell(scan_radius=2)

                # Convert grid result to scan_result for decision engine
                if nearest_safe_cell is None:
                    scan_result = False  # No safe cell found

        result = self.decision_engine.evaluate(
            battery_percent,
            obstacle_distance,
            scan_result,
            nearest_safe_cell,
            **kwargs
        )

        # Handle both legacy and ML results
        if len(result) >= 3:
            self.current_state = result[0]
            self.current_action = result[1]

        return result

    def get_grid_state(self):
        """Get the current grid state for visualization."""
        if self.grid:
            return self.grid.get_grid_state()
        return None

    def render_grid_ascii(self):
        """Render grid as ASCII for debugging."""
        if self.grid:
            return self.grid.render_grid_ascii()
        return "Grid simulation not enabled"

    def get_mission_telemetry(self) -> List[Dict[str, Any]]:
        """Get complete mission telemetry history."""
        return self.telemetry_history

    def get_mission_summary(self) -> Dict[str, Any]:
        """Get mission summary statistics."""
        if not self.telemetry_history:
            return {}

        positions = np.array([t['position'] for t in self.telemetry_history])
        velocities = np.array([t['velocity'] for t in self.telemetry_history])

        total_distance = 0.0
        for i in range(1, len(positions)):
            total_distance += np.linalg.norm(positions[i] - positions[i-1])

        return {
            'total_distance': total_distance,
            'max_velocity': np.max(np.linalg.norm(velocities, axis=1)),
            'avg_velocity': np.mean(np.linalg.norm(velocities, axis=1)),
            'waypoints_tracked': len(self.telemetry_history),
            'replans': self.replan_count,
            'obstacles_detected': len(self.obstacles_detected)
        }
