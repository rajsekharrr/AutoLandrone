"""
Tests for ML vision integration with LandingZoneGrid.

Validates that ML-based terrain analysis integrates correctly with the
grid system while maintaining backward compatibility.
"""

import pytest
import numpy as np
from src.landing_zone_grid import LandingZoneGrid
from src.vision_terrain_ml import TerrainConfig, SyntheticTerrainGenerator


@pytest.fixture
def ml_config():
    """Create terrain config for testing."""
    return TerrainConfig(grid_size=7, random_state=42)


@pytest.fixture
def terrain_image(ml_config):
    """Generate synthetic terrain image for testing."""
    generator = SyntheticTerrainGenerator(ml_config)
    obstacle_cells = [(1, 1), (2, 2), (5, 5)]
    return generator.generate_full_terrain_image(ml_config.grid_size, obstacle_cells)


class TestBackwardCompatibility:
    """Ensure ML changes don't break existing functionality."""

    def test_default_initialization_without_ml(self):
        """Test that grid works without ML (backward compatible)."""
        grid = LandingZoneGrid(grid_size=7)

        assert grid.grid_size == 7
        assert not grid.use_ml_vision
        assert grid.ml_risk_grid is None

    def test_set_obstacle_without_ml(self):
        """Test obstacle setting without ML."""
        grid = LandingZoneGrid(grid_size=7)
        grid.set_obstacle(2, 2)

        assert grid.grid[2][2] == 'obstacle'
        assert not grid.is_cell_safe(2, 2)

    def test_find_nearest_safe_cell_without_ml(self):
        """Test finding safe cells without ML."""
        grid = LandingZoneGrid(grid_size=7)
        grid.set_obstacles([(2, 3), (3, 2), (3, 4), (4, 3)])

        nearest = grid.find_nearest_safe_cell(scan_radius=2)

        assert nearest is not None
        assert grid.is_cell_safe(*nearest)


class TestMLInitialization:
    """Test ML vision initialization."""

    def test_initialize_with_ml_vision(self, ml_config):
        """Test grid initialization with ML vision enabled."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        assert grid.use_ml_vision
        assert grid.ml_classifier is not None
        assert grid.ml_risk_mapper is not None

    def test_initialize_with_ml_default_config(self):
        """Test ML initialization with default config."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True)

        assert grid.use_ml_vision
        assert grid.ml_classifier is not None

    def test_ml_methods_raise_error_without_initialization(self):
        """Test that ML methods fail gracefully without ML enabled."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=False)

        dummy_image = np.random.randint(0, 255, size=(700, 700, 3), dtype=np.uint8)

        with pytest.raises(RuntimeError, match="ML vision not enabled"):
            grid.analyze_terrain_from_image(dummy_image)


class TestMLTerrainAnalysis:
    """Test ML-based terrain analysis."""

    def test_analyze_terrain_from_image(self, ml_config, terrain_image):
        """Test terrain analysis from aerial image."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        risk_grid = grid.analyze_terrain_from_image(terrain_image)

        assert risk_grid.shape == (7, 7)
        assert np.all((risk_grid >= 0.0) & (risk_grid <= 1.0))
        assert grid.ml_risk_grid is not None

    def test_analyze_terrain_updates_discrete_grid(self, ml_config, terrain_image):
        """Test that ML analysis updates discrete obstacle grid."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        # Analyze terrain
        grid.analyze_terrain_from_image(terrain_image)

        # Check that high-risk cells are marked as obstacles
        obstacle_count = sum(
            1 for row in range(7) for col in range(7)
            if grid.grid[row][col] == 'obstacle'
        )

        # Should have some obstacles detected
        assert obstacle_count > 0

    def test_analyze_with_inflation(self, ml_config, terrain_image):
        """Test terrain analysis with obstacle inflation."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        risk_grid_no_inflation = grid.analyze_terrain_from_image(
            terrain_image, apply_inflation=False
        )

        # Reset grid
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        risk_grid_with_inflation = grid.analyze_terrain_from_image(
            terrain_image, apply_inflation=True, inflation_radius=1
        )

        # Inflated grid should have more or equal high-risk cells
        high_risk_no_inflation = np.sum(risk_grid_no_inflation > 0.5)
        high_risk_with_inflation = np.sum(risk_grid_with_inflation > 0.5)

        assert high_risk_with_inflation >= high_risk_no_inflation

    def test_analyze_custom_inflation_radius(self, ml_config, terrain_image):
        """Test custom inflation radius."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        # Test with different radii
        risk_grid_r1 = grid.analyze_terrain_from_image(
            terrain_image, apply_inflation=True, inflation_radius=1
        )

        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        risk_grid_r2 = grid.analyze_terrain_from_image(
            terrain_image, apply_inflation=True, inflation_radius=2
        )

        # Larger radius should generally create more high-risk areas
        assert risk_grid_r1.shape == risk_grid_r2.shape


class TestMLRiskScores:
    """Test continuous risk score functionality."""

    def test_get_cell_risk_score_with_ml(self, ml_config, terrain_image):
        """Test getting continuous risk scores."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        # Get risk scores for various cells
        for row in range(7):
            for col in range(7):
                risk = grid.get_cell_risk_score(row, col)
                assert 0.0 <= risk <= 1.0

    def test_get_cell_risk_score_without_ml(self):
        """Test risk scores fallback to discrete values without ML."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=False)
        grid.set_obstacle(2, 2)

        # Obstacle should return 1.0
        assert grid.get_cell_risk_score(2, 2) == 1.0

        # Safe cell should return 0.0
        assert grid.get_cell_risk_score(3, 3) == 0.0

    def test_get_cell_risk_score_out_of_bounds(self, ml_config, terrain_image):
        """Test out-of-bounds cells return max risk."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        assert grid.get_cell_risk_score(-1, 0) == 1.0
        assert grid.get_cell_risk_score(0, -1) == 1.0
        assert grid.get_cell_risk_score(7, 0) == 1.0
        assert grid.get_cell_risk_score(0, 7) == 1.0


class TestMLSafeLandingZones:
    """Test ML-based safe landing zone detection."""

    def test_get_safe_landing_zones_ml(self, ml_config, terrain_image):
        """Test getting safe landing zones with ML."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        safe_zones = grid.get_safe_landing_zones_ml(risk_threshold=0.5)

        # Should return list of (row, col, risk) tuples
        assert isinstance(safe_zones, list)

        for row, col, risk in safe_zones:
            assert 0 <= row < 7
            assert 0 <= col < 7
            assert 0.0 <= risk < 0.5  # Below threshold

        # Should be sorted by risk (lowest first)
        if len(safe_zones) > 1:
            for i in range(len(safe_zones) - 1):
                assert safe_zones[i][2] <= safe_zones[i + 1][2]

    def test_get_safe_landing_zones_ml_no_analysis_raises_error(self, ml_config):
        """Test that getting safe zones without analysis raises error."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        with pytest.raises(RuntimeError, match="ML terrain analysis required"):
            grid.get_safe_landing_zones_ml()

    def test_get_safe_landing_zones_ml_custom_threshold(self, ml_config, terrain_image):
        """Test safe zones with custom risk threshold."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        # Stricter threshold
        safe_zones_strict = grid.get_safe_landing_zones_ml(risk_threshold=0.3)

        # Looser threshold
        safe_zones_loose = grid.get_safe_landing_zones_ml(risk_threshold=0.7)

        # Looser threshold should yield more or equal safe zones
        assert len(safe_zones_loose) >= len(safe_zones_strict)


class TestMLIntegrationWithExistingMethods:
    """Test that ML integrates smoothly with existing grid methods."""

    def test_is_cell_safe_with_ml(self, ml_config, terrain_image):
        """Test is_cell_safe with ML risk scores."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        # Test with default threshold (0.5)
        for row in range(7):
            for col in range(7):
                safe = grid.is_cell_safe(row, col)
                risk = grid.get_cell_risk_score(row, col)

                if safe:
                    assert risk < 0.5
                else:
                    assert risk >= 0.5 or grid.grid[row][col] == 'obstacle'

    def test_is_cell_safe_custom_threshold(self, ml_config, terrain_image):
        """Test is_cell_safe with custom risk threshold."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        # Test with stricter threshold
        safe_default = grid.is_cell_safe(3, 3, risk_threshold=0.5)
        safe_strict = grid.is_cell_safe(3, 3, risk_threshold=0.3)

        # If cell passes stricter threshold, should also pass default
        if safe_strict:
            assert safe_default

    def test_find_nearest_safe_cell_with_ml(self, ml_config, terrain_image):
        """Test find_nearest_safe_cell with ML vision."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        nearest = grid.find_nearest_safe_cell(scan_radius=3, risk_threshold=0.5)

        if nearest is not None:
            row, col = nearest
            # Should be safe according to ML
            assert grid.is_cell_safe(row, col, risk_threshold=0.5)
            # Should be within scan radius
            distance = grid.get_distance_to_cell(row, col)
            assert distance <= 3.0 * 1.5  # Allow for diagonal

    def test_manual_obstacles_override_ml(self, ml_config, terrain_image):
        """Test that manually set obstacles override ML predictions."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        # Set manual obstacle
        grid.set_obstacle(0, 0)

        # Analyze terrain
        grid.analyze_terrain_from_image(terrain_image)

        # Cell (0, 0) should still be an obstacle
        assert grid.grid[0][0] == 'obstacle'
        assert not grid.is_cell_safe(0, 0)


class TestMLVisualization:
    """Test visualization features with ML."""

    def test_render_grid_ascii_with_risk_scores(self, ml_config, terrain_image):
        """Test ASCII rendering with risk scores."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        ascii_grid = grid.render_grid_ascii(show_risk_scores=True)

        # Should contain drone marker
        assert 'D' in ascii_grid

        # Should contain risk scores (0.XX format)
        assert '0.' in ascii_grid or '1.' in ascii_grid

    def test_render_grid_ascii_standard_with_ml(self, ml_config, terrain_image):
        """Test standard ASCII rendering with ML enabled."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        ascii_grid = grid.render_grid_ascii(show_risk_scores=False)

        # Should use standard symbols
        assert 'D' in ascii_grid  # Drone
        # May contain X (obstacles) if ML detected any

    def test_get_grid_state_with_ml(self, ml_config, terrain_image):
        """Test grid state export includes ML data."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)
        grid.analyze_terrain_from_image(terrain_image)

        state = grid.get_grid_state()

        assert state['use_ml_vision'] is True
        assert 'ml_risk_grid' in state
        assert len(state['ml_risk_grid']) == 7
        assert len(state['ml_risk_grid'][0]) == 7

    def test_get_grid_state_without_ml(self):
        """Test grid state without ML has appropriate flags."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=False)

        state = grid.get_grid_state()

        assert state['use_ml_vision'] is False
        assert 'ml_risk_grid' not in state or state.get('ml_risk_grid') is None


class TestMLEdgeCases:
    """Test edge cases with ML vision."""

    def test_ml_with_small_grid(self):
        """Test ML with small 3×3 grid."""
        config = TerrainConfig(grid_size=3, random_state=42)
        grid = LandingZoneGrid(grid_size=3, use_ml_vision=True, ml_config=config)

        generator = SyntheticTerrainGenerator(config)
        image = generator.generate_full_terrain_image(3)

        risk_grid = grid.analyze_terrain_from_image(image)

        assert risk_grid.shape == (3, 3)

    def test_ml_with_large_grid(self):
        """Test ML with larger 10×10 grid."""
        config = TerrainConfig(grid_size=10, random_state=42)
        grid = LandingZoneGrid(grid_size=10, use_ml_vision=True, ml_config=config)

        generator = SyntheticTerrainGenerator(config)
        image = generator.generate_full_terrain_image(10)

        risk_grid = grid.analyze_terrain_from_image(image)

        assert risk_grid.shape == (10, 10)

    def test_ml_sync_preserves_manual_obstacles(self, ml_config, terrain_image):
        """Test that ML sync preserves manually set obstacles."""
        grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=ml_config)

        # Set manual obstacles
        manual_obstacles = [(0, 0), (0, 1), (6, 6)]
        grid.set_obstacles(manual_obstacles)

        # Analyze terrain (which syncs)
        grid.analyze_terrain_from_image(terrain_image)

        # Manual obstacles should still be marked
        for row, col in manual_obstacles:
            assert grid.grid[row][col] == 'obstacle'


class TestMLPerformance:
    """Test performance characteristics of ML integration."""

    def test_ml_caching_works(self, ml_config):
        """Test that model caching works correctly."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Set cache directory
            config = TerrainConfig(grid_size=7, model_cache_dir=tmpdir, random_state=42)

            # First initialization (trains model)
            grid1 = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=config)

            # Check that model was cached
            cache_files = os.listdir(tmpdir)
            assert len(cache_files) > 0

            # Second initialization (loads from cache)
            grid2 = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=config)

            # Both should have trained classifiers
            assert grid1.ml_classifier.is_trained
            assert grid2.ml_classifier.is_trained


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
