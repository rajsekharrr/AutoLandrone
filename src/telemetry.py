class BatteryTelemetry:
    def __init__(self, battery_percent=100.0):
        self._battery_percent = battery_percent

    def get_battery_percent(self):
        return self._battery_percent

    def set_battery_percent(self, value):
        self._battery_percent = max(0.0, min(100.0, value))
