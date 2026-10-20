"""
2D Landing Zone Grid Simulation

Provides a deterministic grid-based representation of the landing area
with obstacle detection, scanning, and nearest safe cell selection.
"""

from typing import Tuple, List, Optional
import math

class LandingZoneGrid:
    """
    Simulates a 2D grid of landing cells around the drone's position.

    Grid coordinates: (0,0) is top-left, drone typically starts at center.
    Cell states: 'empty', 'obstacle', 'scanned', 'safe_landing'
    """

    def __init__(self, grid_size: int = 7, drone_position: Optional[Tuple[int, int]] = None):
        """
        Initialize the landing zone grid.

        Args:
            grid_size: Size of the square grid (default 7x7)
            drone_position: Initial drone position (row, col). Defaults to center.
        """
        self.grid_size = grid_size
        self.drone_position = drone_position or (grid_size // 2, grid_size // 2)

        # Initialize empty grid
        self.grid = [['empty' for _ in range(grid_size)] for _ in range(grid_size)]

        # Track which cells have been scanned
        self.scanned_cells = set()

        # Nearest safe landing position
        self.nearest_safe_cell = None

    def set_obstacle(self, row: int, col: int):
        """Mark a cell as containing an obstacle."""
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            self.grid[row][col] = 'obstacle'

    def set_obstacles(self, obstacle_positions: List[Tuple[int, int]]):
        """Set multiple obstacles at once."""
        for row, col in obstacle_positions:
            self.set_obstacle(row, col)

    def is_cell_safe(self, row: int, col: int) -> bool:
        """Check if a cell is safe for landing (no obstacle)."""
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return False
        return self.grid[row][col] != 'obstacle'

    def get_distance_to_cell(self, row: int, col: int) -> float:
        """Calculate Euclidean distance from drone to a cell."""
        drone_row, drone_col = self.drone_position
        return math.sqrt((row - drone_row) ** 2 + (col - drone_col) ** 2)

    def scan_nearby_cells(self, scan_radius: int = 2) -> List[Tuple[int, int]]:
        """
        Scan cells within a radius of the drone position.

        Args:
            scan_radius: How many cells to scan in each direction

        Returns:
            List of scanned cell positions
        """
        drone_row, drone_col = self.drone_position
        scanned = []

        for row in range(max(0, drone_row - scan_radius),
                        min(self.grid_size, drone_row + scan_radius + 1)):
            for col in range(max(0, drone_col - scan_radius),
                           min(self.grid_size, drone_col + scan_radius + 1)):
                # Skip the drone's current position
                if (row, col) == self.drone_position:
                    continue

                self.scanned_cells.add((row, col))
                scanned.append((row, col))

        return scanned

    def find_nearest_safe_cell(self, scan_radius: int = 2) -> Optional[Tuple[int, int]]:
        """
        Find the nearest safe landing cell within scan radius.

        Args:
            scan_radius: How many cells to consider

        Returns:
            (row, col) of nearest safe cell, or None if all cells are blocked
        """
        # First scan the area
        self.scan_nearby_cells(scan_radius)

        drone_row, drone_col = self.drone_position
        safe_cells = []

        # Find all safe cells within scan radius
        for row in range(max(0, drone_row - scan_radius),
                        min(self.grid_size, drone_row + scan_radius + 1)):
            for col in range(max(0, drone_col - scan_radius),
                           min(self.grid_size, drone_col + scan_radius + 1)):
                # Skip the drone's current position
                if (row, col) == self.drone_position:
                    continue

                if self.is_cell_safe(row, col):
                    distance = self.get_distance_to_cell(row, col)
                    safe_cells.append((distance, row, col))

        if not safe_cells:
            self.nearest_safe_cell = None
            return None

        # Sort by distance and return the nearest
        safe_cells.sort(key=lambda x: x[0])
        _, nearest_row, nearest_col = safe_cells[0]
        self.nearest_safe_cell = (nearest_row, nearest_col)

        return self.nearest_safe_cell

    def get_grid_state(self) -> dict:
        """
        Get the current state of the grid for visualization.

        Returns:
            Dictionary with grid information
        """
        return {
            'grid': self.grid,
            'grid_size': self.grid_size,
            'drone_position': self.drone_position,
            'scanned_cells': list(self.scanned_cells),
            'nearest_safe_cell': self.nearest_safe_cell
        }

    def render_grid_ascii(self) -> str:
        """
        Render the grid as ASCII art for debugging/testing.

        Legend:
        D = Drone position
        X = Obstacle
        . = Empty cell
        S = Scanned cell
        * = Nearest safe landing cell
        """
        lines = []
        for row in range(self.grid_size):
            line = []
            for col in range(self.grid_size):
                if (row, col) == self.drone_position:
                    line.append('D')
                elif (row, col) == self.nearest_safe_cell:
                    line.append('*')
                elif self.grid[row][col] == 'obstacle':
                    line.append('X')
                elif (row, col) in self.scanned_cells:
                    line.append('S')
                else:
                    line.append('.')
            lines.append(' '.join(line))

        return '\n'.join(lines)
