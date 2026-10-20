import pandas as pd
from datetime import datetime

class DecisionLogger:
    def __init__(self):
        self.logs = []

    def log_decision(self, step, battery, distance, state, action, reason, scan_result=None):
        entry = {
            "Step": step,
            "Battery (%)": f"{battery:.1f}",
            "Distance (m)": f"{distance:.1f}",
            "State": state,
            "Action": action,
            "Reason": reason
        }
        if scan_result:
            entry["Scan Result"] = scan_result
        self.logs.append(entry)

    def get_dataframe(self):
        return pd.DataFrame(self.logs)

    def clear(self):
        self.logs = []
