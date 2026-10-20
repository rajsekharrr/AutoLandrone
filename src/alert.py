from src.config import DroneAction

class AlertSystem:
    def generate_alert(self, action):
        alert_messages = {
            DroneAction.OBSTACLE_DETECTED_ALERT: "⚠️ ALERT: Obstacle detected! Hovering and scanning for clear zone.",
            DroneAction.HOLD_POSITION_ALERT: "🚨 CRITICAL: No clear landing zone found! Holding position and alerting operator.",
        }

        return alert_messages.get(action, None)
