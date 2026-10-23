"""
Tests for Advanced Decision Engine

Validates multi-criteria scoring, ML integration, and legacy compatibility.
"""

import pytest
import numpy as np
from src.decision_engine import LandingZoneScorer, DecisionEngine
from src.config import DroneState, DroneAction


class TestLandingZoneScorer:
    """Test multi-criteria landing zone scoring."""

    @pytest.fixture
    def simple_risk_grid(self):
        """Create a simple 7×7 risk grid."""
        grid = np.zeros((7, 7), dtype=np.float32)
        grid[3, 3] = 0.8  # One obstacle
        grid[2, 2] = 0.6  # Medium risk
        return grid

    @pytest.fixture
    def scorer(self):
        """Create default scorer."""
        return LandingZoneScorer()

    def test_score_cell_basic(self, scorer, simple_risk_grid):
        """Test basic cell scoring."""
        score = scorer.score_cell(
            cell_row=0, cell_col=0,
            drone_row=3, drone_col=3,
            risk_grid=simple_risk_grid
        )

        assert 'total_cost' in score
        assert 'distance_cost' in score
        assert 'risk_cost' in score
        assert 'obstacle_cost' in score
        assert 'wind_cost' in score
        assert score['total_cost'] > 0.0

    def test_score_cell_nearby_vs_far(self, scorer, simple_risk_grid):
        """Test that distance affects cost."""
        drone_pos = (3, 3)

        # Nearby cell
        score_near = scorer.score_cell(
            cell_row=3, cell_col=4,
            drone_row=drone_pos[0], drone_col=drone_pos[1],
            risk_grid=simple_risk_grid
        )

        # Far cell
        score_far = scorer.score_cell(
            cell_row=0, cell_col=0,
            drone_row=drone_pos[0], drone_col=drone_pos[1],
            risk_grid=simple_risk_grid
        )

        # Far cell should have higher distance cost
        assert score_far['distance_cost'] > score_near['distance_cost']

    def test_score_cell_high_risk(self, scorer, simple_risk_grid):
        """Test that high-risk cells cost more."""
        drone_pos = (3, 3)

        # Low risk cell
        score_safe = scorer.score_cell(
            cell_row=0, cell_col=0,
            drone_row=drone_pos[0], drone_col=drone_pos[1],
            risk_grid=simple_risk_grid
        )

        # High risk cell
        score_risky = scorer.score_cell(
            cell_row=3, cell_col=3,
            drone_row=drone_pos[0], drone_col=drone_pos[1],
            risk_grid=simple_risk_grid
        )

        # High-risk cell should have higher risk cost
        assert score_risky['risk_cost'] > score_safe['risk_cost']

    def test_obstacle_proximity(self, scorer, simple_risk_grid):
        """Test obstacle proximity calculation."""
        proximity = scorer._calculate_obstacle_proximity(
            row=3, col=2,  # Next to obstacle at (3,3)
            risk_grid=simple_risk_grid
        )

        # Should detect nearby obstacle
        assert proximity > 0.0

    def test_wind_drift_cost(self, scorer, simple_risk_grid):
        """Test wind drift affects cost."""
        wind_vector = (5.0, 0.0)  # East wind

        # Moving east (with wind)
        score_with_wind = scorer.score_cell(
            cell_row=3, cell_col=4,
            drone_row=3, drone_col=3,
            risk_grid=simple_risk_grid,
            wind_vector=wind_vector
        )

        # Moving west (against wind)
        score_against_wind = scorer.score_cell(
            cell_row=3, cell_col=2,
            drone_row=3, drone_col=3,
            risk_grid=simple_risk_grid,
            wind_vector=wind_vector
        )

        # Against wind should cost more
        assert score_against_wind['wind_cost'] > score_with_wind['wind_cost']

    def test_feature_contributions(self, scorer, simple_risk_grid):
        """Test feature contribution percentages."""
        score = scorer.score_cell(
            cell_row=0, cell_col=0,
            drone_row=3, drone_col=3,
            risk_grid=simple_risk_grid
        )

        contributions = score['feature_contributions']

        # All contributions should be percentages
        for key, value in contributions.items():
            assert '%' in value
            percentage = float(value.rstrip('%'))
            assert 0.0 <= percentage <= 100.0

    def test_rank_landing_zones(self, scorer, simple_risk_grid):
        """Test ranking multiple landing zones."""
        drone_position = (3, 3)

        ranked = scorer.rank_landing_zones(
            drone_position=drone_position,
            risk_grid=simple_risk_grid,
            top_k=5
        )

        assert len(ranked) > 0
        assert len(ranked) <= 5

        # Should be sorted by cost (lowest first)
        costs = [zone['total_cost'] for zone in ranked]
        assert costs == sorted(costs)

        # Best zone should have low risk
        best = ranked[0]
        assert best['terrain_risk'] < 0.5


class TestDecisionEngine:
    """Test advanced decision engine."""

    @pytest.fixture
    def basic_engine(self):
        """Create basic decision engine without ML."""
        return DecisionEngine()

    @pytest.fixture
    def risk_grid(self):
        """Create test risk grid."""
        grid = np.zeros((7, 7), dtype=np.float32)
        grid[2, 2] = 0.7
        grid[4, 4] = 0.8
        return grid

    def test_legacy_continue_monitoring(self, basic_engine):
        """Test legacy behavior - continue monitoring."""
        state, action, reason = basic_engine.evaluate(
            battery_percent=80.0,
            obstacle_distance=2.0
        )

        assert state == DroneState.MONITORING
        assert action == DroneAction.CONTINUE_MONITORING

    def test_legacy_safe_landing(self, basic_engine):
        """Test legacy behavior - safe landing."""
        state, action, reason = basic_engine.evaluate(
            battery_percent=15.0,
            obstacle_distance=5.0
        )

        assert state == DroneState.LANDING
        assert action == DroneAction.SAFE_LANDING

    def test_legacy_obstacle_detected(self, basic_engine):
        """Test legacy behavior - obstacle detected."""
        state, action, reason = basic_engine.evaluate(
            battery_percent=15.0,
            obstacle_distance=0.5
        )

        assert state == DroneState.HOVERING
        assert action == DroneAction.OBSTACLE_DETECTED_ALERT

    def test_grid_based_landing(self, basic_engine):
        """Test grid-based landing decision."""
        state, action, reason = basic_engine.evaluate(
            battery_percent=15.0,
            obstacle_distance=2.0,
            nearest_safe_cell=(2, 3)
        )

        assert state == DroneState.LANDING
        assert action == DroneAction.LAND_AT_CLEAR_ZONE
        assert "(2, 3)" in reason

    def test_grid_with_scoring(self, basic_engine, risk_grid):
        """Test grid-based landing with multi-criteria scoring."""
        state, action, reason = basic_engine.evaluate(
            battery_percent=15.0,
            obstacle_distance=2.0,
            nearest_safe_cell=(1, 1),
            drone_position=(3, 3),
            risk_grid=risk_grid
        )

        assert state == DroneState.LANDING
        assert "cost:" in reason
        assert "dist:" in reason
        assert "risk:" in reason

    def test_evaluate_multiple_candidates(self, basic_engine, risk_grid):
        """Test evaluating multiple landing candidates."""
        candidates = [(0, 0), (1, 1), (5, 5)]

        ranked = basic_engine.evaluate_multiple_candidates(
            drone_position=(3, 3),
            risk_grid=risk_grid,
            candidate_cells=candidates,
            wind_speed=5.0,
            wind_direction=90.0
        )

        assert len(ranked) == len(candidates)
        # Should be sorted by cost
        costs = [r['total_cost'] for r in ranked]
        assert costs == sorted(costs)

    def test_landing_zone_report(self, basic_engine, risk_grid):
        """Test landing zone report generation."""
        scorer = LandingZoneScorer()
        score = scorer.score_cell(
            cell_row=1, cell_col=1,
            drone_row=3, drone_col=3,
            risk_grid=risk_grid
        )

        report = basic_engine.get_landing_zone_report(score)

        assert "Landing Zone Analysis" in report
        assert "Total Cost:" in report
        assert "Feature Breakdown:" in report
        assert "Distance:" in report
        assert "Terrain Risk:" in report

    def test_no_clear_zone_legacy(self, basic_engine):
        """Test no clear zone found - legacy."""
        state, action, reason = basic_engine.evaluate(
            battery_percent=15.0,
            obstacle_distance=2.0,
            scan_result="no_clear_zone"
        )

        assert state == DroneState.HOLD_AND_ALERT
        assert action == DroneAction.HOLD_POSITION_ALERT


class TestMLIntegration:
    """Test ML integration (with mock models)."""

    class MockEnergyPredictor:
        """Mock energy predictor for testing."""
        def is_critical_battery(self, *args, **kwargs):
            return False, "Battery safe: 60.0%, 25.0min remaining"

        def predict_remaining_time(self, *args, **kwargs):
            return 25.0

        def predict_point_of_no_return(self, *args, **kwargs):
            return 30.0

    class MockPathPlanner:
        """Mock path planner for testing."""
        def set_risk_grid(self, risk_grid):
            pass

        def set_wind(self, wind_speed, wind_direction):
            pass

        def plan_path(self, start, goal):
            return [(start[0], start[1], start[2]), (goal[0], goal[1], goal[2])]

        def get_path_statistics(self, path):
            return {
                'waypoint_count': len(path),
                'total_distance_m': 20.0,
                'horizontal_distance_m': 15.0,
                'altitude_change_count': 1,
                'average_risk': 0.2
            }

    @pytest.fixture
    def ml_engine(self):
        """Create engine with ML enabled."""
        return DecisionEngine(
            enable_ml_energy=True,
            enable_path_planning=True,
            energy_predictor=self.MockEnergyPredictor(),
            path_planner=self.MockPathPlanner()
        )

    @pytest.fixture
    def risk_grid(self):
        """Create test risk grid."""
        grid = np.zeros((7, 7), dtype=np.float32)
        grid[2, 2] = 0.3
        return grid

    def test_ml_safe_battery(self, ml_engine, risk_grid):
        """Test ML decision with safe battery."""
        result = ml_engine.evaluate(
            battery_percent=60.0,
            obstacle_distance=2.0,
            drone_position=(3, 3),
            risk_grid=risk_grid,
            altitude=20.0,
            wind_speed=5.0,
            wind_direction=90.0
        )

        # Should continue monitoring (battery safe)
        state, action, reason = result[:3]
        assert state == DroneState.MONITORING


def test_integration_full_decision():
    """Integration test for full decision workflow."""
    # Create risk grid
    risk_grid = np.random.rand(7, 7) * 0.4
    risk_grid[5, 5] = 0.05  # Good landing zone

    # Create engine
    engine = DecisionEngine()

    # Test with various scenarios
    scenarios = [
        # (battery, obstacle_dist, nearest_cell, expected_state)
        (80.0, 2.0, None, DroneState.MONITORING),
        (15.0, 3.0, (5, 5), DroneState.LANDING),
        (15.0, 0.5, None, DroneState.HOVERING),
    ]

    for battery, obstacle_dist, cell, expected_state in scenarios:
        result = engine.evaluate(
            battery_percent=battery,
            obstacle_distance=obstacle_dist,
            nearest_safe_cell=cell,
            drone_position=(3, 3) if cell else None,
            risk_grid=risk_grid if cell else None
        )

        state = result[0]
        assert state == expected_state
