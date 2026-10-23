"""
2D Landing Zone Grid Simulation

Provides a deterministic grid-based representation of the landing area
with obstacle detection, scanning, and nearest safe cell selection.

Now with optional ML-based vision terrain analysis for continuous risk scoring.
"""

from typing import Tuple, List, Optional, Dict, Any
import math
import numpy as np

class LandingZoneGrid:
    """
    Simulates a 2D grid of landing cells around the drone's position.

    Grid coordinates: (0,0) is top-left, drone typically starts at center.
    Cell states: 'empty', 'obstacle', 'scanned', 'safe_landing'

    Supports optional ML-based vision terrain analysis with continuous risk scores.
    """

    def __init__(self, grid_size: int = 7, drone_position: Optional[Tuple[int, int]] = None,
                 use_ml_vision: bool = False, ml_config: Optional[Any] = None):
        """
        Initialize the landing zone grid.

        Args:
            grid_size: Size of the square grid (default 7x7)
            drone_position: Initial drone position (row, col). Defaults to center.
            use_ml_vision: Enable ML-based vision terrain analysis
            ml_config: Optional TerrainConfig for ML vision (uses default if None)
        """
        self.grid_size = grid_size
        self.drone_position = drone_position or (grid_size // 2, grid_size // 2)

        # Initialize empty grid
        self.grid = [['empty' for _ in range(grid_size)] for _ in range(grid_size)]

        # Track which cells have been scanned
        self.scanned_cells = set()

        # Nearest safe landing position
        self.nearest_safe_cell = None

        # ML Vision Integration (optional)
        self.use_ml_vision = use_ml_vision
        self.ml_risk_grid: Optional[np.ndarray] = None
        self.ml_classifier = None
        self.ml_risk_mapper = None

        if use_ml_vision:
            self._initialize_ml_vision(ml_config)

    def _initialize_ml_vision(self, ml_config: Optional[Any] = None):
        """
        Initialize ML vision components (lazy import to avoid dependency issues).

        Args:
            ml_config: Optional TerrainConfig
        """
        try:
            from src.vision_terrain_ml import (
                TerrainConfig, load_or_create_classifier, RiskMapper
            )

            # Use provided config or create default
            if ml_config is None:
                ml_config = TerrainConfig(grid_size=self.grid_size)
            elif not hasattr(ml_config, 'grid_size'):
                # If partial config, ensure grid_size matches
                ml_config.grid_size = self.grid_size

            # Load or create classifier
            self.ml_classifier = load_or_create_classifier(config=ml_config)

            # Create risk mapper
            self.ml_risk_mapper = RiskMapper(ml_config, self.ml_classifier)

        except ImportError as e:
            raise ImportError(
                f"ML vision requires additional dependencies. "
                f"Install with: pip install opencv-python scikit-learn joblib\n"
                f"Error: {e}"
            )

    def set_obstacle(self, row: int, col: int):
        """Mark a cell as containing an obstacle."""
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            self.grid[row][col] = 'obstacle'
            # Update ML risk grid if active
            if self.use_ml_vision and self.ml_risk_grid is not None:
                self.ml_risk_grid[row, col] = 1.0

    def set_obstacles(self, obstacle_positions: List[Tuple[int, int]]):
        """Set multiple obstacles at once."""
        for row, col in obstacle_positions:
            self.set_obstacle(row, col)

    def is_cell_safe(self, row: int, col: int, risk_threshold: float = 0.5) -> bool:
        """
        Check if a cell is safe for landing.

        Args:
            row: Cell row index
            col: Cell column index
            risk_threshold: Risk threshold for ML vision (0.0-1.0)

        Returns:
            True if cell is safe, False otherwise
        """
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return False

        # Check discrete obstacle grid (always checked for backward compatibility)
        if self.grid[row][col] == 'obstacle':
            return False

        # If ML vision is enabled, also check risk score
        if self.use_ml_vision and self.ml_risk_grid is not None:
            return self.ml_risk_grid[row, col] < risk_threshold

        return True

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

    def find_nearest_safe_cell(self, scan_radius: int = 2,
                              risk_threshold: float = 0.5) -> Optional[Tuple[int, int]]:
        """
        Find the nearest safe landing cell within scan radius.

        Args:
            scan_radius: How many cells to consider
            risk_threshold: Risk threshold for ML vision (0.0-1.0)

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

                if self.is_cell_safe(row, col, risk_threshold):
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
        state = {
            'grid': self.grid,
            'grid_size': self.grid_size,
            'drone_position': self.drone_position,
            'scanned_cells': list(self.scanned_cells),
            'nearest_safe_cell': self.nearest_safe_cell
        }

        # Include ML risk data if available
        if self.use_ml_vision and self.ml_risk_grid is not None:
            state['ml_risk_grid'] = self.ml_risk_grid.tolist()
            state['use_ml_vision'] = True
        else:
            state['use_ml_vision'] = False

        return state

    def analyze_terrain_from_image(self, aerial_image: np.ndarray,
                                   apply_inflation: bool = True,
                                   inflation_radius: Optional[int] = None) -> np.ndarray:
        """
        Analyze terrain from aerial image using ML vision.

        Args:
            aerial_image: Aerial image (H×W×3 BGR format)
            apply_inflation: Apply obstacle inflation buffering
            inflation_radius: Override inflation radius (uses config default if None)

        Returns:
            Risk grid (grid_size × grid_size) with continuous scores 0.0-1.0

        Raises:
            RuntimeError: If ML vision is not enabled
        """
        if not self.use_ml_vision:
            raise RuntimeError("ML vision not enabled. Initialize with use_ml_vision=True")

        # Compute risk grid from image
        risk_grid = self.ml_risk_mapper.compute_risk_grid(aerial_image, self.grid_size)

        # Apply obstacle inflation if requested
        if apply_inflation:
            risk_grid = self.ml_risk_mapper.apply_obstacle_inflation(
                risk_grid, inflation_radius
            )

        # Store risk grid
        self.ml_risk_grid = risk_grid

        # Sync with discrete grid (update obstacles based on risk threshold)
        self._sync_ml_to_discrete_grid()

        return risk_grid

    def _sync_ml_to_discrete_grid(self, risk_threshold: float = 0.5):
        """
        Synchronize ML risk grid to discrete obstacle grid.

        Updates discrete grid cells to 'obstacle' where ML risk exceeds threshold.

        Args:
            risk_threshold: Risk threshold for marking obstacles
        """
        if self.ml_risk_grid is None:
            return

        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.ml_risk_grid[row, col] >= risk_threshold:
                    self.grid[row][col] = 'obstacle'
                elif self.grid[row][col] != 'obstacle':
                    # Don't override manually set obstacles
                    self.grid[row][col] = 'empty'

    def get_cell_risk_score(self, row: int, col: int) -> float:
        """
        Get continuous risk score for a specific cell.

        Args:
            row: Cell row index
            col: Cell column index

        Returns:
            Risk score (0.0-1.0), or 1.0 for discrete obstacles when ML not used
        """
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return 1.0  # Out of bounds = max risk

        # Return ML risk if available
        if self.use_ml_vision and self.ml_risk_grid is not None:
            return float(self.ml_risk_grid[row, col])

        # Fallback to discrete grid
        return 1.0 if self.grid[row][col] == 'obstacle' else 0.0

    def get_safe_landing_zones_ml(self, risk_threshold: float = 0.5) -> List[Tuple[int, int, float]]:
        """
        Get all safe landing zones with their risk scores using ML vision.

        Args:
            risk_threshold: Maximum acceptable risk (0.0-1.0)

        Returns:
            List of (row, col, risk_score) tuples for safe cells, sorted by risk

        Raises:
            RuntimeError: If ML vision is not enabled or no terrain analyzed
        """
        if not self.use_ml_vision or self.ml_risk_grid is None:
            raise RuntimeError("ML terrain analysis required. Call analyze_terrain_from_image() first")

        safe_zones = []

        for row in range(self.grid_size):
            for col in range(self.grid_size):
                risk = self.ml_risk_grid[row, col]
                if risk < risk_threshold:
                    safe_zones.append((row, col, float(risk)))

        # Sort by risk (lowest risk first)
        safe_zones.sort(key=lambda x: x[2])

        return safe_zones

    def render_grid_ascii(self, show_risk_scores: bool = False) -> str:
        """
        Render the grid as ASCII art for debugging/testing.

        Legend:
        D = Drone position
        X = Obstacle
        . = Empty cell
        S = Scanned cell
        * = Nearest safe landing cell
        0.XX = Risk score (if show_risk_scores=True and ML enabled)

        Args:
            show_risk_scores: Show continuous risk scores instead of symbols

        Returns:
            ASCII grid representation
        """
        if show_risk_scores and self.use_ml_vision and self.ml_risk_grid is not None:
            # Render with risk scores
            lines = []
            for row in range(self.grid_size):
                line = []
                for col in range(self.grid_size):
                    if (row, col) == self.drone_position:
                        line.append(' D  ')
                    else:
                        risk = self.ml_risk_grid[row, col]
                        line.append(f'{risk:.2f}')
                lines.append(' '.join(line))
            return '\n'.join(lines)

        # Standard symbolic rendering
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
