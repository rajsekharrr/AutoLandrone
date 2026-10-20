from src.config import (
    BATTERY_CRITICAL_THRESHOLD,
    OBSTACLE_SAFE_DISTANCE,
    DroneState,
    DroneAction
)

class DecisionEngine:
    def evaluate(self, battery_percent, obstacle_distance, scan_result=None):
        if battery_percent > BATTERY_CRITICAL_THRESHOLD:
            return (
                DroneState.MONITORING,
                DroneAction.CONTINUE_MONITORING,
                f"Battery at {battery_percent}% - above critical threshold"
            )

        if scan_result == "clear_zone_found":
            return (
                DroneState.LANDING,
                DroneAction.LAND_AT_CLEAR_ZONE,
                "Scan found clear landing zone"
            )

        if scan_result == "no_clear_zone":
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
