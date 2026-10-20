class ObstacleSensor:
    def __init__(self, distance=10.0):
        self._distance = distance

    def get_distance(self):
        return self._distance

    def set_distance(self, value):
        self._distance = max(0.0, value)
