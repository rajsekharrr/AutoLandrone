from src.decision_engine import DecisionEngine

class LandingController:
    def __init__(self):
        self.decision_engine = DecisionEngine()
        self.current_state = None
        self.current_action = None

    def process_telemetry(self, battery_percent, obstacle_distance, scan_result=None):
        state, action, reason = self.decision_engine.evaluate(
            battery_percent,
            obstacle_distance,
            scan_result
        )

        self.current_state = state
        self.current_action = action

        return state, action, reason
