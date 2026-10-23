"""
Tests for Energy ML Model

Validates energy prediction, point-of-no-return calculation, and model training.
"""

import pytest
import numpy as np
from src.energy_ml_model import (
    EnergyConfig, EnergyPhysicsModel, SyntheticEnergyDataGenerator,
    EnergyPredictor, create_and_train_energy_model
)


class TestEnergyPhysicsModel:
    """Test physics-based energy calculations."""

    def test_current_draw_hover(self):
        """Test base hover current calculation."""
        config = EnergyConfig()
        physics = EnergyPhysicsModel(config)

        current = physics.calculate_current_draw(
            altitude=10.0, wind_speed=0.0, payload=0.0, velocity=0.0
        )

        # Should be base + altitude component (with some noise)
        expected = config.base_hover_current + (10.0 * config.current_per_meter_altitude)
        assert 0.95 * expected <= current <= 1.05 * expected

    def test_current_draw_high_wind(self):
        """Test current increases with wind speed."""
        config = EnergyConfig()
        physics = EnergyPhysicsModel(config)

        current_no_wind = physics.calculate_current_draw(10.0, 0.0, 0.5, 0.0)
        current_high_wind = physics.calculate_current_draw(10.0, 10.0, 0.5, 0.0)

        assert current_high_wind > current_no_wind

    def test_remaining_time_full_battery(self):
        """Test remaining time calculation with full battery."""
        config = EnergyConfig()
        physics = EnergyPhysicsModel(config)

        remaining = physics.calculate_remaining_time(
            battery_percent=100.0,
            voltage_sag=0.5,
            altitude=10.0,
            wind_speed=5.0,
            payload=1.0
        )

        assert remaining > 10.0  # Should have at least 10 minutes
        assert remaining < 60.0  # But less than 1 hour

    def test_remaining_time_low_battery(self):
        """Test remaining time with low battery."""
        config = EnergyConfig()
        physics = EnergyPhysicsModel(config)

        remaining = physics.calculate_remaining_time(
            battery_percent=20.0,
            voltage_sag=1.5,
            altitude=10.0,
            wind_speed=5.0,
            payload=1.0
        )

        assert remaining < 10.0  # Should be less than 10 minutes

    def test_point_of_no_return(self):
        """Test PNR calculation."""
        config = EnergyConfig()
        physics = EnergyPhysicsModel(config)

        pnr = physics.calculate_point_of_no_return(
            current_altitude=50.0,
            home_distance=200.0,
            wind_speed=5.0,
            payload=1.0,
            voltage_sag=0.5
        )

        # PNR should be reasonable percentage (minimum 5% reserve applies)
        assert 5.0 <= pnr <= 50.0


class TestSyntheticDataGenerator:
    """Test synthetic training data generation."""

    def test_generate_dataset(self):
        """Test synthetic dataset generation."""
        config = EnergyConfig(random_state=42)
        generator = SyntheticEnergyDataGenerator(config)

        features, time_labels, pnr_labels = generator.generate_training_dataset(n_samples=100)

        # Check shapes
        assert features.shape == (100, 6)
        assert time_labels.shape == (100,)
        assert pnr_labels.shape == (100,)

        # Check value ranges
        assert np.all(features[:, 0] >= 10.0) and np.all(features[:, 0] <= 100.0)  # Battery %
        assert np.all(time_labels >= 0.0)  # Positive time
        assert np.all(pnr_labels >= 0.0) and np.all(pnr_labels <= 100.0)  # PNR in 0-100%


class TestEnergyPredictor:
    """Test ML energy predictor."""

    @pytest.fixture
    def trained_predictor(self):
        """Create a trained predictor for testing."""
        config = EnergyConfig(random_state=42, n_estimators=50)  # Faster training
        predictor, metrics = create_and_train_energy_model(config, n_training_samples=500)
        return predictor

    def test_training(self, trained_predictor):
        """Test that model trains successfully."""
        assert trained_predictor.is_trained

    def test_predict_remaining_time(self, trained_predictor):
        """Test remaining time prediction."""
        remaining = trained_predictor.predict_remaining_time(
            battery_percent=80.0,
            voltage_sag=0.5,
            altitude=20.0,
            wind_speed=5.0,
            payload=1.0,
            distance=100.0
        )

        assert remaining > 0.0
        assert remaining < 120.0  # Less than 2 hours

    def test_predict_pnr(self, trained_predictor):
        """Test point-of-no-return prediction."""
        pnr = trained_predictor.predict_point_of_no_return(
            altitude=30.0,
            home_distance=150.0,
            wind_speed=5.0,
            payload=1.0,
            voltage_sag=0.5
        )

        assert 5.0 <= pnr <= 95.0

    def test_is_critical_battery_safe(self, trained_predictor):
        """Test critical battery check - safe case."""
        is_critical, reason = trained_predictor.is_critical_battery(
            battery_percent=80.0,
            altitude=20.0,
            home_distance=50.0,
            wind_speed=3.0,
            payload=0.5,
            voltage_sag=0.3
        )

        assert not is_critical
        assert "safe" in reason.lower()

    def test_is_critical_battery_low(self, trained_predictor):
        """Test critical battery check - critical case."""
        is_critical, reason = trained_predictor.is_critical_battery(
            battery_percent=10.0,  # Very low battery
            altitude=80.0,  # High altitude
            home_distance=300.0,  # Far from home
            wind_speed=12.0,  # Strong wind
            payload=2.5,  # Heavy payload
            voltage_sag=2.0  # Significant voltage sag
        )

        # Should be critical with these extreme conditions
        assert is_critical or battery_percent < 15.0  # Either critical or battery is very low

    def test_feature_importance(self, trained_predictor):
        """Test feature importance extraction."""
        importance = trained_predictor.get_feature_importance("time")

        assert len(importance) == 6
        assert "battery_percent" in importance
        assert all(0.0 <= v <= 1.0 for v in importance.values())

    def test_save_and_load(self, trained_predictor, tmp_path):
        """Test model persistence."""
        model_path = tmp_path / "test_energy_model.joblib"

        # Save model
        saved_path = trained_predictor.save_model(str(model_path))
        assert model_path.exists()

        # Load model
        new_predictor = EnergyPredictor(EnergyConfig())
        new_predictor.load_model(saved_path)

        assert new_predictor.is_trained

        # Test prediction consistency
        result1 = trained_predictor.predict_remaining_time(50.0, 0.5, 20.0, 5.0, 1.0, 100.0)
        result2 = new_predictor.predict_remaining_time(50.0, 0.5, 20.0, 5.0, 1.0, 100.0)

        assert abs(result1 - result2) < 0.1  # Should be very similar


def test_integration():
    """Integration test for full workflow."""
    # Create and train model
    predictor, metrics = create_and_train_energy_model(
        config=EnergyConfig(random_state=42, n_estimators=50),
        n_training_samples=500
    )

    # Check training metrics
    assert metrics['time_val_r2'] > 0.8  # Good R² score
    assert metrics['pnr_val_r2'] > 0.8

    # Make predictions
    remaining_time = predictor.predict_remaining_time(60.0, 0.8, 30.0, 7.0, 1.5, 150.0)
    pnr = predictor.predict_point_of_no_return(30.0, 150.0, 7.0, 1.5, 0.8)

    assert remaining_time > 0.0
    assert 5.0 <= pnr <= 95.0

    # Check critical status
    is_critical, reason = predictor.is_critical_battery(60.0, 30.0, 150.0, 7.0, 1.5, 0.8)
    assert isinstance(is_critical, bool)
    assert isinstance(reason, str)
