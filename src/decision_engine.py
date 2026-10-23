"""
Advanced Decision Engine with Multi-Criteria Cost Function

Production-ready decision engine that integrates ML-based energy prediction,
3D path planning, and multi-criteria landing zone scoring to make optimal
landing decisions for autonomous drones.

Evaluates candidate landing cells using:
- Distance to current position
- ML terrain risk scores
- Obstacle proximity with inflation
- Wind drift compensation
- Energy constraints (point-of-no-return)

Provides human-readable feature contribution breakdown for transparency.
"""

from src.config import (
    BATTERY_CRITICAL_THRESHOLD,
    OBSTACLE_SAFE_DISTANCE,
    DroneState,
    DroneAction
)
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import math


class LandingZoneScorer:
    """
    Multi-criteria scoring system for landing zone evaluation.

    Combines distance, terrain risk, obstacle proximity, and wind drift
    into a unified cost metric with interpretable feature contributions.
    """

    def __init__(self, distance_weight: float = 1.0, risk_weight: float = 3.0,
                 obstacle_weight: float = 2.0, wind_weight: float = 0.5):
        """
        Initialize landing zone scorer.

        Args:
            distance_weight: Weight for distance cost (fuel/time)
            risk_weight: Weight for terrain risk cost (safety)
            obstacle_weight: Weight for obstacle proximity cost (collision avoidance)
            wind_weight: Weight for wind drift cost (control)
        """
        self.distance_weight = distance_weight
        self.risk_weight = risk_weight
        self.obstacle_weight = obstacle_weight
        self.wind_weight = wind_weight

    def score_cell(self, cell_row: int, cell_col: int, drone_row: int, drone_col: int,
                   risk_grid: np.ndarray, wind_vector: Tuple[float, float] = (0.0, 0.0),
                   cell_size: float = 5.0) -> Dict[str, Any]:
        """
        Score a candidate landing cell using multi-criteria cost function.

        Args:
            cell_row: Candidate cell row
            cell_col: Candidate cell column
            drone_row: Current drone row
            drone_col: Current drone column
            risk_grid: 2D terrain risk grid (0.0-1.0)
            wind_vector: (wind_x, wind_y) in m/s
            cell_size: Size of each grid cell in meters

        Returns:
            Dictionary with total cost and feature breakdown
        """
        grid_size = risk_grid.shape[0]

        # Feature 1: Distance cost (Euclidean distance from drone to cell)
        dx = cell_col - drone_col
        dy = cell_row - drone_row
        distance = math.sqrt(dx**2 + dy**2) * cell_size  # Convert to meters
        distance_cost = distance * self.distance_weight

        # Feature 2: Terrain risk cost (from ML vision)
        if 0 <= cell_row < grid_size and 0 <= cell_col < grid_size:
            terrain_risk = float(risk_grid[cell_row, cell_col])
        else:
            terrain_risk = 1.0  # Out of bounds = max risk
        risk_cost = terrain_risk * self.risk_weight

        # Feature 3: Obstacle proximity cost (check surrounding cells)
        obstacle_proximity = self._calculate_obstacle_proximity(
            cell_row, cell_col, risk_grid
        )
        obstacle_cost = obstacle_proximity * self.obstacle_weight

        # Feature 4: Wind drift cost (moving against wind is harder)
        if dx != 0 or dy != 0:
            move_dist = math.sqrt(dx**2 + dy**2)
            move_unit = (dx / move_dist, dy / move_dist)
            # Dot product: negative = against wind (higher cost)
            wind_alignment = (move_unit[0] * wind_vector[0] +
                            move_unit[1] * wind_vector[1])
            wind_cost = max(0.0, -wind_alignment) * self.wind_weight
        else:
            wind_cost = 0.0

        # Total cost (lower is better)
        total_cost = distance_cost + risk_cost + obstacle_cost + wind_cost

        return {
            'total_cost': round(total_cost, 3),
            'distance_cost': round(distance_cost, 3),
            'risk_cost': round(risk_cost, 3),
            'obstacle_cost': round(obstacle_cost, 3),
            'wind_cost': round(wind_cost, 3),
            'distance_m': round(distance, 2),
            'terrain_risk': round(terrain_risk, 3),
            'obstacle_proximity': round(obstacle_proximity, 3),
            'cell': (cell_row, cell_col),
            'feature_contributions': {
                'distance': f"{(distance_cost/total_cost*100):.1f}%" if total_cost > 0 else "0%",
                'terrain_risk': f"{(risk_cost/total_cost*100):.1f}%" if total_cost > 0 else "0%",
                'obstacle_proximity': f"{(obstacle_cost/total_cost*100):.1f}%" if total_cost > 0 else "0%",
                'wind_drift': f"{(wind_cost/total_cost*100):.1f}%" if total_cost > 0 else "0%"
            }
        }

    def _calculate_obstacle_proximity(self, row: int, col: int,
                                     risk_grid: np.ndarray, radius: int = 1) -> float:
        """
        Calculate obstacle proximity score for a cell.

        Checks surrounding cells within radius and weights closer obstacles higher.

        Args:
            row: Cell row
            col: Cell column
            risk_grid: 2D terrain risk grid
            radius: Search radius in cells

        Returns:
            Obstacle proximity score (0.0-1.0)
        """
        grid_size = risk_grid.shape[0]
        proximity_score = 0.0
        cell_count = 0

        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if dr == 0 and dc == 0:
                    continue  # Skip center cell

                r, c = row + dr, col + dc
                if 0 <= r < grid_size and 0 <= c < grid_size:
                    distance = math.sqrt(dr**2 + dc**2)
                    # Weight closer cells more heavily
                    weight = 1.0 / (distance + 0.1)
                    proximity_score += risk_grid[r, c] * weight
                    cell_count += weight

        if cell_count > 0:
            return proximity_score / cell_count
        return 0.0

    def rank_landing_zones(self, drone_position: Tuple[int, int],
                          risk_grid: np.ndarray,
                          candidate_cells: Optional[List[Tuple[int, int]]] = None,
                          wind_vector: Tuple[float, float] = (0.0, 0.0),
                          max_risk_threshold: float = 0.5,
                          top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rank all candidate landing zones by cost.

        Args:
            drone_position: Current drone (row, col)
            risk_grid: 2D terrain risk grid
            candidate_cells: List of candidate cells to score (all safe cells if None)
            wind_vector: Wind vector (wind_x, wind_y)
            max_risk_threshold: Maximum acceptable risk
            top_k: Return top K candidates

        Returns:
            List of scored cells, sorted by cost (best first)
        """
        drone_row, drone_col = drone_position

        # If no candidates provided, use all safe cells
        if candidate_cells is None:
            candidate_cells = []
            grid_size = risk_grid.shape[0]
            for r in range(grid_size):
                for c in range(grid_size):
                    if risk_grid[r, c] < max_risk_threshold:
                        candidate_cells.append((r, c))

        # Score all candidates
        scored_cells = []
        for cell_row, cell_col in candidate_cells:
            score = self.score_cell(
                cell_row, cell_col, drone_row, drone_col,
                risk_grid, wind_vector
            )
            scored_cells.append(score)

        # Sort by total cost (lower is better)
        scored_cells.sort(key=lambda x: x['total_cost'])

        return scored_cells[:top_k]


class DecisionEngine:
    """
    Advanced decision engine with ML energy prediction and multi-criteria scoring.

    Integrates:
    - Energy ML model for battery prediction
    - Path planner for trajectory validation
    - Multi-criteria landing zone scorer
    - Legacy compatibility with simple grid-based decisions
    """

    def __init__(self, enable_ml_energy: bool = False, enable_path_planning: bool = False,
                 energy_predictor=None, path_planner=None):
        """
        Initialize decision engine.

        Args:
            enable_ml_energy: Enable ML-based energy prediction
            enable_path_planning: Enable 3D path planning
            energy_predictor: Optional EnergyPredictor instance
            path_planner: Optional PathPlanner instance
        """
        self.enable_ml_energy = enable_ml_energy
        self.enable_path_planning = enable_path_planning
        self.energy_predictor = energy_predictor
        self.path_planner = path_planner
        self.scorer = LandingZoneScorer()

    def evaluate(self, battery_percent, obstacle_distance, scan_result=None,
                nearest_safe_cell=None, **kwargs):
        """
        Evaluate the current situation and determine the appropriate action.

        Args:
            battery_percent: Current battery percentage
            obstacle_distance: Distance to obstacle below (meters)
            scan_result: Legacy scan result ("clear_zone_found", "no_clear_zone", or None)
            nearest_safe_cell: Tuple (row, col) of nearest safe landing cell from grid simulation
            **kwargs: Additional optional arguments:
                - drone_position: (row, col) current position
                - risk_grid: 2D numpy array of terrain risk
                - altitude: Current altitude in meters
                - wind_speed: Wind speed in m/s
                - wind_direction: Wind direction in degrees
                - payload: Payload mass in kg
                - voltage_sag: Battery voltage sag in volts
                - home_distance: Distance to home in meters

        Returns:
            Tuple of (state, action, reason) or enhanced dict if ML enabled
        """
        # Extract advanced parameters if provided
        drone_position = kwargs.get('drone_position')
        risk_grid = kwargs.get('risk_grid')
        altitude = kwargs.get('altitude', 10.0)
        wind_speed = kwargs.get('wind_speed', 0.0)
        wind_direction = kwargs.get('wind_direction', 0.0)
        payload = kwargs.get('payload', 0.5)
        voltage_sag = kwargs.get('voltage_sag', 0.5)
        home_distance = kwargs.get('home_distance', 50.0)

        # ML Energy Check (if enabled)
        if self.enable_ml_energy and self.energy_predictor is not None:
            is_critical, energy_reason = self.energy_predictor.is_critical_battery(
                battery_percent, altitude, home_distance, wind_speed, payload, voltage_sag
            )

            if is_critical:
                # Calculate remaining time and PNR for detailed feedback
                remaining_time = self.energy_predictor.predict_remaining_time(
                    battery_percent, voltage_sag, altitude, wind_speed, payload, home_distance
                )
                pnr = self.energy_predictor.predict_point_of_no_return(
                    altitude, home_distance, wind_speed, payload, voltage_sag
                )

                # Advanced decision with ML scoring
                if risk_grid is not None and drone_position is not None:
                    return self._evaluate_ml_landing(
                        battery_percent, drone_position, risk_grid,
                        wind_speed, wind_direction, remaining_time, pnr, energy_reason
                    )

        # Standard evaluation (legacy compatible)
        if battery_percent > BATTERY_CRITICAL_THRESHOLD:
            return (
                DroneState.MONITORING,
                DroneAction.CONTINUE_MONITORING,
                f"Battery at {battery_percent}% - above critical threshold"
            )

        # Handle grid-based scan results with multi-criteria scoring
        if nearest_safe_cell is not None:
            if risk_grid is not None and drone_position is not None:
                # Score the selected cell
                wind_vector = self._wind_to_vector(wind_speed, wind_direction)
                score = self.scorer.score_cell(
                    nearest_safe_cell[0], nearest_safe_cell[1],
                    drone_position[0], drone_position[1],
                    risk_grid, wind_vector
                )

                reason = (
                    f"Landing at cell {nearest_safe_cell} "
                    f"(cost: {score['total_cost']:.2f}, "
                    f"dist: {score['distance_m']:.1f}m, "
                    f"risk: {score['terrain_risk']:.2f})"
                )
            else:
                reason = f"Scan found clear landing zone at grid cell {nearest_safe_cell}"

            return (
                DroneState.LANDING,
                DroneAction.LAND_AT_CLEAR_ZONE,
                reason
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

    def _evaluate_ml_landing(self, battery_percent: float, drone_position: Tuple[int, int],
                           risk_grid: np.ndarray, wind_speed: float, wind_direction: float,
                           remaining_time: float, pnr_threshold: float,
                           energy_reason: str) -> Tuple[str, str, str, Dict[str, Any]]:
        """
        Evaluate landing with ML-based scoring and path planning.

        Returns:
            Extended tuple with (state, action, reason, extra_data)
        """
        # Get wind vector
        wind_vector = self._wind_to_vector(wind_speed, wind_direction)

        # Rank landing zones
        top_zones = self.scorer.rank_landing_zones(
            drone_position, risk_grid, wind_vector=wind_vector, top_k=3
        )

        if not top_zones:
            return (
                DroneState.HOLD_AND_ALERT,
                DroneAction.HOLD_POSITION_ALERT,
                f"CRITICAL: {energy_reason}, but no safe landing zones available",
                {'remaining_time': remaining_time, 'pnr': pnr_threshold}
            )

        # Select best landing zone
        best_zone = top_zones[0]

        # Path planning validation (if enabled)
        path_valid = True
        path_stats = None
        if self.enable_path_planning and self.path_planner is not None:
            try:
                # Assume drone at altitude level 5, target at ground (0)
                start_pos = (drone_position[1], drone_position[0], 5)
                goal_pos = (best_zone['cell'][1], best_zone['cell'][0], 0)

                self.path_planner.set_risk_grid(risk_grid)
                if wind_speed > 0:
                    self.path_planner.set_wind(wind_speed, wind_direction)

                path = self.path_planner.plan_path(start_pos, goal_pos)
                if path is None:
                    path_valid = False
                else:
                    path_stats = self.path_planner.get_path_statistics(path)
            except Exception:
                path_valid = False

        # Build comprehensive reason
        contributions = best_zone['feature_contributions']
        reason = (
            f"ML LANDING DECISION: {energy_reason} | "
            f"Target: cell {best_zone['cell']} | "
            f"Cost: {best_zone['total_cost']:.2f} "
            f"[Dist:{contributions['distance']}, Risk:{contributions['terrain_risk']}, "
            f"Obst:{contributions['obstacle_proximity']}, Wind:{contributions['wind_drift']}] | "
            f"Distance: {best_zone['distance_m']:.1f}m | "
            f"Terrain risk: {best_zone['terrain_risk']:.2f}"
        )

        if not path_valid:
            reason += " | WARNING: Path planning failed or blocked"

        extra_data = {
            'remaining_time': remaining_time,
            'pnr': pnr_threshold,
            'best_landing_zone': best_zone,
            'alternative_zones': top_zones[1:],
            'path_valid': path_valid,
            'path_stats': path_stats
        }

        if path_valid:
            return (
                DroneState.LANDING,
                DroneAction.LAND_AT_CLEAR_ZONE,
                reason,
                extra_data
            )
        else:
            return (
                DroneState.HOLD_AND_ALERT,
                DroneAction.HOLD_POSITION_ALERT,
                reason,
                extra_data
            )

    def _wind_to_vector(self, wind_speed: float, wind_direction: float) -> Tuple[float, float]:
        """Convert wind speed and direction to vector."""
        wind_rad = math.radians(wind_direction)
        return (
            wind_speed * math.sin(wind_rad),  # X component
            wind_speed * math.cos(wind_rad)   # Y component
        )

    def evaluate_multiple_candidates(self, drone_position: Tuple[int, int],
                                    risk_grid: np.ndarray,
                                    candidate_cells: List[Tuple[int, int]],
                                    wind_speed: float = 0.0,
                                    wind_direction: float = 0.0) -> List[Dict[str, Any]]:
        """
        Evaluate and rank multiple landing zone candidates.

        Args:
            drone_position: Current drone (row, col)
            risk_grid: 2D terrain risk grid
            candidate_cells: List of candidate cells to evaluate
            wind_speed: Wind speed in m/s
            wind_direction: Wind direction in degrees

        Returns:
            List of scored candidates, sorted by cost (best first)
        """
        wind_vector = self._wind_to_vector(wind_speed, wind_direction)

        return self.scorer.rank_landing_zones(
            drone_position, risk_grid, candidate_cells, wind_vector
        )

    def get_landing_zone_report(self, scored_zone: Dict[str, Any]) -> str:
        """
        Generate human-readable report for a scored landing zone.

        Args:
            scored_zone: Scored zone dictionary from scorer

        Returns:
            Formatted report string
        """
        report = [
            f"Landing Zone Analysis for Cell {scored_zone['cell']}",
            f"=" * 50,
            f"Total Cost: {scored_zone['total_cost']:.3f} (lower is better)",
            f"",
            f"Feature Breakdown:",
            f"  Distance: {scored_zone['distance_m']:.1f}m (cost: {scored_zone['distance_cost']:.3f}) - {scored_zone['feature_contributions']['distance']}",
            f"  Terrain Risk: {scored_zone['terrain_risk']:.3f} (cost: {scored_zone['risk_cost']:.3f}) - {scored_zone['feature_contributions']['terrain_risk']}",
            f"  Obstacle Proximity: {scored_zone['obstacle_proximity']:.3f} (cost: {scored_zone['obstacle_cost']:.3f}) - {scored_zone['feature_contributions']['obstacle_proximity']}",
            f"  Wind Drift: (cost: {scored_zone['wind_cost']:.3f}) - {scored_zone['feature_contributions']['wind_drift']}",
            f"",
            f"Feature Contributions:",
            f"  Distance contributes {scored_zone['feature_contributions']['distance']} to total cost",
            f"  Terrain risk contributes {scored_zone['feature_contributions']['terrain_risk']} to total cost",
            f"  Obstacle proximity contributes {scored_zone['feature_contributions']['obstacle_proximity']} to total cost",
            f"  Wind drift contributes {scored_zone['feature_contributions']['wind_drift']} to total cost"
        ]

        return "\n".join(report)
