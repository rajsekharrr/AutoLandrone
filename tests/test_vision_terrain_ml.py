"""
Tests for ML-based vision terrain classification system.

Validates feature extraction, synthetic data generation, RandomForest training,
risk mapping, and obstacle inflation buffering.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
import tempfile
import os

from src.vision_terrain_ml import (
    TerrainConfig,
    TerrainFeatureExtractor,
    SyntheticTerrainGenerator,
    TerrainClassifier,
    RiskMapper,
    create_and_train_model,
    load_or_create_classifier
)


@pytest.fixture
def config():
    """Create default terrain configuration."""
    return TerrainConfig(grid_size=7, random_state=42)


@pytest.fixture
def feature_extractor(config):
    """Create feature extractor."""
    return TerrainFeatureExtractor(config)


@pytest.fixture
def terrain_generator(config):
    """Create synthetic terrain generator."""
    return SyntheticTerrainGenerator(config)


@pytest.fixture
def trained_classifier(config):
    """Create and train a classifier with small dataset for testing."""
    generator = SyntheticTerrainGenerator(config)
    features, labels = generator.generate_training_dataset(n_samples=200)

    classifier = TerrainClassifier(config)
    classifier.train(features, labels)

    return classifier


class TestTerrainConfig:
    """Test terrain configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TerrainConfig()

        assert config.grid_size == 7
        assert config.image_size == (700, 700)
        assert config.canny_low == 50
        assert config.canny_high == 150
        assert config.inflation_radius == 1
        assert config.risk_threshold == 0.5
        assert config.n_estimators == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = TerrainConfig(
            grid_size=10,
            image_size=(1000, 1000),
            inflation_radius=2,
            n_estimators=50
        )

        assert config.grid_size == 10
        assert config.image_size == (1000, 1000)
        assert config.inflation_radius == 2
        assert config.n_estimators == 50


class TestTerrainFeatureExtractor:
    """Test feature extraction."""

    def test_extract_features_shape(self, feature_extractor):
        """Test that feature extraction produces 10D vector."""
        # Create dummy image patch
        patch = np.random.randint(0, 255, size=(100, 100, 3), dtype=np.uint8)

        features = feature_extractor.extract_features(patch)

        assert features.shape == (10,)
        assert features.dtype == np.float32

    def test_extract_features_from_safe_patch(self, feature_extractor, terrain_generator):
        """Test feature extraction from safe terrain."""
        patch = terrain_generator._generate_safe_patch()

        features = feature_extractor.extract_features(patch)

        # Safe patches should have low edge density and variance
        edge_density = features[0]
        laplacian_var = features[1]

        assert 0.0 <= edge_density <= 1.0
        assert laplacian_var >= 0.0

    def test_extract_features_from_obstacle_patch(self, feature_extractor, terrain_generator):
        """Test feature extraction from obstacle terrain."""
        patch = terrain_generator._generate_obstacle_patch()

        features = feature_extractor.extract_features(patch)

        # Verify all features are in reasonable ranges
        assert len(features) == 10
        assert np.all(np.isfinite(features))

    def test_extract_grid_features(self, feature_extractor):
        """Test grid-based feature extraction."""
        # Create dummy terrain image
        image = np.random.randint(0, 255, size=(700, 700, 3), dtype=np.uint8)
        grid_size = 7

        features_grid = feature_extractor.extract_grid_features(image, grid_size)

        assert features_grid.shape == (7, 7, 10)
        assert features_grid.dtype == np.float32

    def test_feature_consistency(self, feature_extractor):
        """Test that same patch produces same features."""
        patch = np.random.randint(0, 255, size=(100, 100, 3), dtype=np.uint8)

        features1 = feature_extractor.extract_features(patch)
        features2 = feature_extractor.extract_features(patch)

        np.testing.assert_array_equal(features1, features2)


class TestSyntheticTerrainGenerator:
    """Test synthetic terrain generation."""

    def test_generate_safe_patch(self, terrain_generator):
        """Test safe patch generation."""
        patch = terrain_generator._generate_safe_patch(size=100)

        assert patch.shape == (100, 100, 3)
        assert patch.dtype == np.uint8
        assert np.all(patch >= 0) and np.all(patch <= 255)

    def test_generate_obstacle_patch(self, terrain_generator):
        """Test obstacle patch generation."""
        patch = terrain_generator._generate_obstacle_patch(size=100)

        assert patch.shape == (100, 100, 3)
        assert patch.dtype == np.uint8

    def test_generate_training_dataset(self, terrain_generator):
        """Test training dataset generation."""
        n_samples = 100
        features, labels = terrain_generator.generate_training_dataset(n_samples)

        assert features.shape == (n_samples, 10)
        assert labels.shape == (n_samples,)
        assert set(labels) == {0, 1}  # Binary labels

        # Check label balance (roughly 50/50)
        safe_count = np.sum(labels == 0)
        obstacle_count = np.sum(labels == 1)
        assert 40 <= safe_count <= 60  # Allow some variance

    def test_generate_full_terrain_image(self, terrain_generator):
        """Test full terrain image generation."""
        grid_size = 7
        obstacle_cells = [(1, 1), (3, 3), (5, 5)]

        image = terrain_generator.generate_full_terrain_image(grid_size, obstacle_cells)

        # Image size should match config
        cell_size = terrain_generator.config.image_size[0] // grid_size
        expected_size = cell_size * grid_size

        assert image.shape == (expected_size, expected_size, 3)
        assert image.dtype == np.uint8

    def test_random_terrain_generation(self, terrain_generator):
        """Test random terrain generation (no specified obstacles)."""
        grid_size = 5
        image = terrain_generator.generate_full_terrain_image(grid_size)

        assert image.shape[0] == image.shape[1]
        assert image.shape[2] == 3


class TestTerrainClassifier:
    """Test terrain classifier."""

    def test_classifier_initialization(self, config):
        """Test classifier initialization."""
        classifier = TerrainClassifier(config)

        assert not classifier.is_trained
        assert classifier.model is not None
        assert classifier.scaler is not None

    def test_train_classifier(self, config, terrain_generator):
        """Test classifier training."""
        # Generate small training set
        features, labels = terrain_generator.generate_training_dataset(n_samples=100)

        classifier = TerrainClassifier(config)
        metrics = classifier.train(features, labels)

        assert classifier.is_trained
        assert 'train_accuracy' in metrics
        assert 'val_accuracy' in metrics
        assert 0.0 <= metrics['train_accuracy'] <= 1.0
        assert 0.0 <= metrics['val_accuracy'] <= 1.0

    def test_predict_risk_single_sample(self, trained_classifier, terrain_generator):
        """Test risk prediction on single sample."""
        patch = terrain_generator._generate_safe_patch()
        extractor = TerrainFeatureExtractor(trained_classifier.config)
        features = extractor.extract_features(patch)

        risk = trained_classifier.predict_risk(features)

        assert len(risk) == 1
        assert 0.0 <= risk[0] <= 1.0

    def test_predict_risk_batch(self, trained_classifier, terrain_generator):
        """Test risk prediction on batch."""
        features, _ = terrain_generator.generate_training_dataset(n_samples=10)

        risks = trained_classifier.predict_risk(features)

        assert len(risks) == 10
        assert np.all((risks >= 0.0) & (risks <= 1.0))

    def test_predict_without_training_raises_error(self, config):
        """Test that prediction without training raises error."""
        classifier = TerrainClassifier(config)
        features = np.random.randn(1, 10)

        with pytest.raises(ValueError, match="Model must be trained"):
            classifier.predict_risk(features)

    def test_save_and_load_model(self, trained_classifier):
        """Test model saving and loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "test_model.joblib")

            # Save model
            saved_path = trained_classifier.save_model(model_path)
            assert os.path.exists(saved_path)

            # Create new classifier and load
            new_classifier = TerrainClassifier(trained_classifier.config)
            new_classifier.load_model(model_path)

            assert new_classifier.is_trained

            # Verify predictions match
            test_features = np.random.randn(5, 10)
            risk1 = trained_classifier.predict_risk(test_features)
            risk2 = new_classifier.predict_risk(test_features)

            np.testing.assert_array_almost_equal(risk1, risk2)

    def test_load_nonexistent_model_raises_error(self, config):
        """Test loading nonexistent model raises error."""
        classifier = TerrainClassifier(config)

        with pytest.raises(FileNotFoundError):
            classifier.load_model("nonexistent_model.joblib")


class TestRiskMapper:
    """Test risk mapping."""

    def test_compute_risk_grid(self, trained_classifier, terrain_generator):
        """Test risk grid computation."""
        grid_size = 7

        # Generate test terrain
        obstacle_cells = [(1, 1), (5, 5)]
        image = terrain_generator.generate_full_terrain_image(grid_size, obstacle_cells)

        # Create risk mapper
        risk_mapper = RiskMapper(trained_classifier.config, trained_classifier)

        # Compute risk grid
        risk_grid = risk_mapper.compute_risk_grid(image, grid_size)

        assert risk_grid.shape == (7, 7)
        assert np.all((risk_grid >= 0.0) & (risk_grid <= 1.0))

    def test_obstacle_inflation(self, trained_classifier):
        """Test obstacle inflation buffering."""
        # Create simple risk grid with single high-risk cell
        risk_grid = np.zeros((7, 7), dtype=np.float32)
        risk_grid[3, 3] = 1.0  # Center obstacle

        risk_mapper = RiskMapper(trained_classifier.config, trained_classifier)

        # Apply inflation
        inflated = risk_mapper.apply_obstacle_inflation(risk_grid, inflation_radius=1)

        # Check that neighboring cells have increased risk
        assert inflated[3, 3] == 1.0  # Center unchanged
        assert inflated[2, 3] > 0.0  # Top neighbor inflated
        assert inflated[4, 3] > 0.0  # Bottom neighbor inflated
        assert inflated[3, 2] > 0.0  # Left neighbor inflated
        assert inflated[3, 4] > 0.0  # Right neighbor inflated

        # Corner cells should have less inflation (greater distance)
        assert inflated[2, 2] < inflated[2, 3]

    def test_inflation_with_zero_radius(self, trained_classifier):
        """Test that zero inflation radius leaves grid unchanged."""
        risk_grid = np.random.rand(7, 7).astype(np.float32)

        risk_mapper = RiskMapper(trained_classifier.config, trained_classifier)
        inflated = risk_mapper.apply_obstacle_inflation(risk_grid, inflation_radius=0)

        np.testing.assert_array_equal(risk_grid, inflated)

    def test_get_safe_landing_zones(self, trained_classifier):
        """Test safe landing zone extraction."""
        # Create risk grid with known safe zones
        risk_grid = np.ones((7, 7), dtype=np.float32) * 0.8  # High risk everywhere
        risk_grid[0, 0] = 0.1  # Safe
        risk_grid[3, 3] = 0.2  # Safe
        risk_grid[6, 6] = 0.3  # Safe

        risk_mapper = RiskMapper(trained_classifier.config, trained_classifier)

        safe_zones = risk_mapper.get_safe_landing_zones(risk_grid, threshold=0.5)

        assert len(safe_zones) == 3
        assert (0, 0) in safe_zones
        assert (3, 3) in safe_zones
        assert (6, 6) in safe_zones

    def test_no_safe_landing_zones(self, trained_classifier):
        """Test when no safe zones exist."""
        # All high risk
        risk_grid = np.ones((7, 7), dtype=np.float32)

        risk_mapper = RiskMapper(trained_classifier.config, trained_classifier)
        safe_zones = risk_mapper.get_safe_landing_zones(risk_grid, threshold=0.5)

        assert len(safe_zones) == 0


class TestConvenienceFunctions:
    """Test high-level convenience functions."""

    def test_create_and_train_model(self):
        """Test create_and_train_model convenience function."""
        config = TerrainConfig(grid_size=5, random_state=42)

        classifier, metrics = create_and_train_model(config, n_training_samples=200)

        assert classifier.is_trained
        assert 'train_accuracy' in metrics
        assert 'val_accuracy' in metrics

    def test_load_or_create_classifier_creates_new(self):
        """Test that load_or_create_classifier creates new model when cache missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "new_model.joblib")
            config = TerrainConfig(grid_size=5, random_state=42)

            classifier = load_or_create_classifier(model_path, config)

            assert classifier.is_trained
            assert os.path.exists(model_path)

    def test_load_or_create_classifier_loads_existing(self):
        """Test that load_or_create_classifier loads cached model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "cached_model.joblib")
            config = TerrainConfig(grid_size=5, random_state=42)

            # Create and save model
            classifier1 = load_or_create_classifier(model_path, config)

            # Load cached model
            classifier2 = load_or_create_classifier(model_path, config)

            assert classifier2.is_trained

            # Verify it's the same model (same predictions)
            test_features = np.random.randn(5, 10)
            risk1 = classifier1.predict_risk(test_features)
            risk2 = classifier2.predict_risk(test_features)

            np.testing.assert_array_almost_equal(risk1, risk2)

    def test_force_retrain(self):
        """Test force_retrain parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.joblib")
            config = TerrainConfig(grid_size=5, random_state=42)

            # Create initial model
            classifier1 = load_or_create_classifier(model_path, config)
            initial_mtime = os.path.getmtime(model_path)

            # Force retrain
            import time
            time.sleep(0.1)  # Ensure timestamp difference
            classifier2 = load_or_create_classifier(model_path, config, force_retrain=True)
            new_mtime = os.path.getmtime(model_path)

            # File should have been updated
            assert new_mtime > initial_mtime


class TestIntegration:
    """Integration tests for full pipeline."""

    def test_end_to_end_pipeline(self, config):
        """Test complete pipeline from image to safe zones."""
        # 1. Generate synthetic terrain
        generator = SyntheticTerrainGenerator(config)
        obstacle_cells = [(1, 1), (2, 2), (5, 5)]
        image = generator.generate_full_terrain_image(config.grid_size, obstacle_cells)

        # 2. Train classifier
        classifier, _ = create_and_train_model(config, n_training_samples=500)

        # 3. Create risk mapper
        risk_mapper = RiskMapper(config, classifier)

        # 4. Compute risk grid
        risk_grid = risk_mapper.compute_risk_grid(image, config.grid_size)

        # 5. Apply inflation
        inflated_risk = risk_mapper.apply_obstacle_inflation(risk_grid)

        # 6. Get safe zones
        safe_zones = risk_mapper.get_safe_landing_zones(inflated_risk)

        # Verify outputs
        assert risk_grid.shape == (config.grid_size, config.grid_size)
        assert inflated_risk.shape == (config.grid_size, config.grid_size)
        assert isinstance(safe_zones, list)

        # There should be some safe zones
        assert len(safe_zones) > 0

    def test_different_grid_sizes(self):
        """Test pipeline with different grid sizes."""
        for grid_size in [5, 7, 10]:
            config = TerrainConfig(grid_size=grid_size, random_state=42)

            # Generate terrain
            generator = SyntheticTerrainGenerator(config)
            image = generator.generate_full_terrain_image(grid_size)

            # Train classifier
            classifier, _ = create_and_train_model(config, n_training_samples=200)

            # Compute risk
            risk_mapper = RiskMapper(config, classifier)
            risk_grid = risk_mapper.compute_risk_grid(image, grid_size)

            assert risk_grid.shape == (grid_size, grid_size)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
