from src.config import (
    BATTERY_CRITICAL_THRESHOLD,
    OBSTACLE_SAFE_DISTANCE,
    DroneState,
    DroneAction
)
from typing import Optional, Tuple

class DecisionEngine:
    def evaluate(self, battery_percent, obstacle_distance, scan_result=None, nearest_safe_cell=None):
        """
        Evaluate the current situation and determine the appropriate action.

        Args:
            battery_percent: Current battery percentage
            obstacle_distance: Distance to obstacle below (meters)
            scan_result: Legacy scan result ("clear_zone_found", "no_clear_zone", or None)
            nearest_safe_cell: Tuple (row, col) of nearest safe landing cell from grid simulation

        Returns:
            Tuple of (state, action, reason)
        """
        if battery_percent > BATTERY_CRITICAL_THRESHOLD:
            return (
                DroneState.MONITORING,
                DroneAction.CONTINUE_MONITORING,
                f"Battery at {battery_percent}% - above critical threshold"
            )

        # Handle grid-based scan results (new approach)
        if nearest_safe_cell is not None:
            return (
                DroneState.LANDING,
                DroneAction.LAND_AT_CLEAR_ZONE,
                f"Scan found clear landing zone at grid cell {nearest_safe_cell}"
            )

        # Handle legacy scan results (for backward compatibility)
        if scan_result == "clear_zone_found":
            return (
                DroneState.LANDING,
                DroneAction.LAND_AT_CLEAR_ZONE,
                "Scan found clear landing zone"
            )

        if scan_result == "no_clear_zone" or (scan_result is False):
            return (
                DroneState.HOLD_AND_ALERT,
                DroneAction.HOLD_POSITION_ALERT,
                "No clear landing zone found - holding position"
            )

        if obstacle_distance >= OBSTACLE_SAFE_DISTANCE:
            return (
                DroneState.LANDING,
                DroneAction.SAFE_LANDING,
                f"Battery critical ({battery_percent}%) and landing zone clear ({obstacle_distance}m)"
            )

        return (
            DroneState.HOVERING,
            DroneAction.OBSTACLE_DETECTED_ALERT,
            f"Battery critical ({battery_percent}%) but obstacle detected at {obstacle_distance}m"
        )
