from src.decision_engine import DecisionEngine
from src.landing_zone_grid import LandingZoneGrid
from typing import Optional, Tuple

class LandingController:
    def __init__(self, use_grid_simulation: bool = False, grid_size: int = 7):
        """
        Initialize the landing controller.

        Args:
            use_grid_simulation: Enable 2D grid-based landing zone simulation
            grid_size: Size of the landing zone grid (default 7x7)
        """
        self.decision_engine = DecisionEngine()
        self.current_state = None
        self.current_action = None
        self.use_grid_simulation = use_grid_simulation
        self.grid = LandingZoneGrid(grid_size=grid_size) if use_grid_simulation else None

    def set_grid_obstacles(self, obstacle_positions):
        """Set obstacle positions in the grid simulation."""
        if self.grid:
            self.grid.set_obstacles(obstacle_positions)

    def process_telemetry(self, battery_percent, obstacle_distance, scan_result=None):
        """
        Process telemetry and determine landing action.

        Args:
            battery_percent: Current battery percentage
            obstacle_distance: Distance to obstacle below (meters)
            scan_result: Legacy scan result for backward compatibility

        Returns:
            Tuple of (state, action, reason)
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
                # If nearest_safe_cell exists, pass it directly

        state, action, reason = self.decision_engine.evaluate(
            battery_percent,
            obstacle_distance,
            scan_result,
            nearest_safe_cell
        )

        self.current_state = state
        self.current_action = action

        return state, action, reason

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
