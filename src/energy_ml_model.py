"""
Energy ML Model - Dynamic Battery & Point-of-No-Return Predictor

Production-ready scikit-learn regressor that predicts remaining flight time
and critical return thresholds based on battery percentage, voltage sag,
altitude, wind speed, payload, and distance to target.

Uses GradientBoostingRegressor for high-accuracy time-to-exhaustion prediction
with synthetic training data generation and model caching.
"""

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from typing import Dict, Tuple, Optional, Any
import joblib
import warnings
from pathlib import Path
from dataclasses import dataclass
import os


@dataclass
class EnergyConfig:
    """Configuration for energy prediction model."""
    # Model parameters
    model_type: str = "gradient_boosting"  # "gradient_boosting" or "random_forest"
    n_estimators: int = 150
    max_depth: int = 8
    learning_rate: float = 0.1
    random_state: int = 42

    # Physical constants (based on typical multirotor drone)
    base_hover_current: float = 8.0  # Amps at hover
    current_per_meter_altitude: float = 0.15  # Additional current per meter altitude
    current_per_ms_wind: float = 0.3  # Additional current per m/s wind speed
    current_per_kg_payload: float = 2.5  # Additional current per kg payload
    current_per_ms_velocity: float = 0.4  # Additional current for horizontal flight

    # Battery parameters
    nominal_voltage: float = 22.2  # Volts (6S LiPo)
    nominal_capacity: float = 5.0  # Amp-hours
    voltage_sag_factor: float = 0.8  # Effective capacity reduction at high load
    cutoff_voltage: float = 19.8  # Minimum safe voltage (3.3V per cell)

    # Safety margins
    reserve_margin: float = 0.15  # 15% reserve for point-of-no-return
    emergency_reserve: float = 0.05  # 5% absolute minimum reserve

    # Model cache
    model_cache_dir: str = "models"


class EnergyPhysicsModel:
    """
    Physics-based energy consumption model for synthetic data generation.

    Models realistic multirotor energy consumption based on drone characteristics
    and environmental conditions.
    """

    def __init__(self, config: EnergyConfig):
        self.config = config
        self.rng = np.random.RandomState(config.random_state)

    def calculate_current_draw(self, altitude: float, wind_speed: float,
                               payload: float, velocity: float = 0.0) -> float:
        """
        Calculate instantaneous current draw based on flight conditions.

        Args:
            altitude: Current altitude in meters
            wind_speed: Wind speed in m/s
            payload: Payload mass in kg
            velocity: Horizontal velocity in m/s

        Returns:
            Current draw in Amps
        """
        current = self.config.base_hover_current
        current += self.config.current_per_meter_altitude * altitude
        current += self.config.current_per_ms_wind * wind_speed
        current += self.config.current_per_kg_payload * payload
        current += self.config.current_per_ms_velocity * velocity

        # Add some realistic noise (±5%)
        noise_factor = 1.0 + self.rng.uniform(-0.05, 0.05)
        return current * noise_factor

    def calculate_effective_capacity(self, voltage_sag: float) -> float:
        """
        Calculate effective battery capacity accounting for voltage sag.

        Args:
            voltage_sag: Voltage sag in volts (nominal - actual)

        Returns:
            Effective capacity in Amp-hours
        """
        # Higher voltage sag indicates higher load -> reduced effective capacity
        sag_ratio = voltage_sag / self.config.nominal_voltage
        capacity_factor = 1.0 - (sag_ratio * (1.0 - self.config.voltage_sag_factor))
        return self.config.nominal_capacity * max(0.5, capacity_factor)

    def calculate_remaining_time(self, battery_percent: float, voltage_sag: float,
                                altitude: float, wind_speed: float, payload: float,
                                distance: float = 0.0) -> float:
        """
        Calculate remaining flight time in minutes.

        Args:
            battery_percent: Current battery percentage (0-100)
            voltage_sag: Voltage sag in volts
            altitude: Current altitude in meters
            wind_speed: Wind speed in m/s
            payload: Payload mass in kg
            distance: Distance to travel in meters (if planning a flight)

        Returns:
            Remaining flight time in minutes
        """
        # Calculate remaining capacity
        effective_capacity = self.calculate_effective_capacity(voltage_sag)
        remaining_capacity = effective_capacity * (battery_percent / 100.0)

        # Calculate current draw for current conditions
        # If distance > 0, assume some horizontal velocity
        velocity = min(distance / 60.0, 10.0) if distance > 0 else 0.0  # Cap at 10 m/s
        current_draw = self.calculate_current_draw(altitude, wind_speed, payload, velocity)

        # Time = Capacity / Current (in hours), convert to minutes
        remaining_time = (remaining_capacity / current_draw) * 60.0

        return max(0.0, remaining_time)

    def calculate_point_of_no_return(self, current_altitude: float, home_distance: float,
                                    wind_speed: float, payload: float,
                                    voltage_sag: float) -> float:
        """
        Calculate battery percentage at point-of-no-return.

        This is the minimum battery level needed to safely return home and land.

        Args:
            current_altitude: Current altitude in meters
            home_distance: Distance to home in meters
            wind_speed: Wind speed in m/s
            payload: Payload mass in kg
            voltage_sag: Current voltage sag in volts

        Returns:
            Point-of-no-return battery percentage (0-100)
        """
        # Calculate return flight requirements
        return_velocity = 8.0  # Conservative return speed m/s
        return_time_horizontal = home_distance / return_velocity  # seconds
        descent_rate = 2.0  # m/s descent rate
        return_time_vertical = current_altitude / descent_rate  # seconds
        total_return_time = (return_time_horizontal + return_time_vertical) / 60.0  # minutes

        # Calculate average current during return
        avg_altitude = current_altitude / 2.0  # Average altitude during descent
        return_current = self.calculate_current_draw(avg_altitude, wind_speed, payload, return_velocity)

        # Required capacity for return
        required_capacity = (return_current * total_return_time / 60.0)  # Amp-hours

        # Add safety margin
        required_capacity *= (1.0 + self.config.reserve_margin)

        # Convert to percentage
        effective_capacity = self.calculate_effective_capacity(voltage_sag)
        required_percent = (required_capacity / effective_capacity) * 100.0

        # Ensure minimum reserve
        min_percent = self.config.emergency_reserve * 100.0
        return max(min_percent, min(required_percent, 95.0))


class SyntheticEnergyDataGenerator:
    """
    Generates synthetic training data for energy prediction model.

    Creates realistic flight scenarios with varied conditions and corresponding
    remaining flight times and point-of-no-return thresholds.
    """

    def __init__(self, config: EnergyConfig):
        self.config = config
        self.physics = EnergyPhysicsModel(config)
        self.rng = np.random.RandomState(config.random_state)

    def generate_training_dataset(self, n_samples: int = 5000) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate synthetic training dataset.

        Args:
            n_samples: Number of training samples

        Returns:
            features: (n_samples, 6) - [battery%, voltage_sag, altitude, wind, payload, distance]
            time_labels: (n_samples,) - remaining flight time in minutes
            pnr_labels: (n_samples,) - point-of-no-return battery %
        """
        features = []
        time_labels = []
        pnr_labels = []

        for _ in range(n_samples):
            # Generate random flight conditions
            battery_percent = self.rng.uniform(10.0, 100.0)
            voltage_sag = self.rng.uniform(0.0, 2.5)  # 0-2.5V sag
            altitude = self.rng.uniform(2.0, 120.0)  # 2-120m altitude
            wind_speed = self.rng.uniform(0.0, 15.0)  # 0-15 m/s wind
            payload = self.rng.uniform(0.0, 3.0)  # 0-3 kg payload
            distance = self.rng.uniform(0.0, 500.0)  # 0-500m distance to travel

            # Calculate labels using physics model
            remaining_time = self.physics.calculate_remaining_time(
                battery_percent, voltage_sag, altitude, wind_speed, payload, distance
            )

            pnr_threshold = self.physics.calculate_point_of_no_return(
                altitude, distance, wind_speed, payload, voltage_sag
            )

            features.append([battery_percent, voltage_sag, altitude, wind_speed, payload, distance])
            time_labels.append(remaining_time)
            pnr_labels.append(pnr_threshold)

        return np.array(features, dtype=np.float32), np.array(time_labels, dtype=np.float32), np.array(pnr_labels, dtype=np.float32)


class EnergyPredictor:
    """
    ML-based energy predictor using scikit-learn regressors.

    Predicts:
    1. Remaining flight time (minutes)
    2. Point-of-no-return battery threshold (%)

    Features: [battery_percent, voltage_sag, altitude, wind_speed, payload, distance]
    """

    def __init__(self, config: EnergyConfig):
        self.config = config

        # Create models
        if config.model_type == "gradient_boosting":
            self.time_model = GradientBoostingRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                learning_rate=config.learning_rate,
                random_state=config.random_state,
                subsample=0.8
            )
            self.pnr_model = GradientBoostingRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                learning_rate=config.learning_rate,
                random_state=config.random_state,
                subsample=0.8
            )
        else:  # random_forest
            self.time_model = RandomForestRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                random_state=config.random_state,
                n_jobs=-1
            )
            self.pnr_model = RandomForestRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                random_state=config.random_state,
                n_jobs=-1
            )

        self.scaler = StandardScaler()
        self.is_trained = False

        # Feature names for interpretability
        self.feature_names = [
            "battery_percent", "voltage_sag", "altitude",
            "wind_speed", "payload", "distance"
        ]

    def train(self, features: np.ndarray, time_labels: np.ndarray,
              pnr_labels: np.ndarray, validation_split: float = 0.2) -> Dict[str, float]:
        """
        Train both time and PNR prediction models.

        Args:
            features: (n_samples, 6) feature array
            time_labels: (n_samples,) remaining time labels
            pnr_labels: (n_samples,) point-of-no-return labels
            validation_split: Fraction for validation

        Returns:
            Training metrics dictionary
        """
        # Split data
        indices = np.arange(len(features))
        train_idx, val_idx = train_test_split(
            indices, test_size=validation_split, random_state=self.config.random_state
        )

        X_train, X_val = features[train_idx], features[val_idx]
        y_time_train, y_time_val = time_labels[train_idx], time_labels[val_idx]
        y_pnr_train, y_pnr_val = pnr_labels[train_idx], pnr_labels[val_idx]

        # Standardize features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Train time prediction model
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.time_model.fit(X_train_scaled, y_time_train)
            self.pnr_model.fit(X_train_scaled, y_pnr_train)

        self.is_trained = True

        # Calculate metrics
        time_train_r2 = self.time_model.score(X_train_scaled, y_time_train)
        time_val_r2 = self.time_model.score(X_val_scaled, y_time_val)
        pnr_train_r2 = self.pnr_model.score(X_train_scaled, y_pnr_train)
        pnr_val_r2 = self.pnr_model.score(X_val_scaled, y_pnr_val)

        # Calculate MAE for interpretability
        time_val_pred = self.time_model.predict(X_val_scaled)
        pnr_val_pred = self.pnr_model.predict(X_val_scaled)
        time_mae = np.mean(np.abs(time_val_pred - y_time_val))
        pnr_mae = np.mean(np.abs(pnr_val_pred - y_pnr_val))

        return {
            'time_train_r2': time_train_r2,
            'time_val_r2': time_val_r2,
            'time_val_mae': time_mae,
            'pnr_train_r2': pnr_train_r2,
            'pnr_val_r2': pnr_val_r2,
            'pnr_val_mae': pnr_mae,
            'n_train': len(X_train),
            'n_val': len(X_val)
        }

    def predict_remaining_time(self, battery_percent: float, voltage_sag: float,
                              altitude: float, wind_speed: float, payload: float,
                              distance: float = 0.0) -> float:
        """
        Predict remaining flight time in minutes.

        Args:
            battery_percent: Current battery percentage (0-100)
            voltage_sag: Voltage sag in volts (nominal - actual)
            altitude: Current altitude in meters
            wind_speed: Wind speed in m/s
            payload: Payload mass in kg
            distance: Distance to travel in meters

        Returns:
            Predicted remaining flight time in minutes
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        features = np.array([[battery_percent, voltage_sag, altitude, wind_speed, payload, distance]])
        features_scaled = self.scaler.transform(features)

        remaining_time = self.time_model.predict(features_scaled)[0]
        return max(0.0, float(remaining_time))

    def predict_point_of_no_return(self, altitude: float, home_distance: float,
                                   wind_speed: float, payload: float,
                                   voltage_sag: float) -> float:
        """
        Predict point-of-no-return battery threshold.

        Args:
            altitude: Current altitude in meters
            home_distance: Distance to home in meters
            wind_speed: Wind speed in m/s
            payload: Payload mass in kg
            voltage_sag: Current voltage sag in volts

        Returns:
            Point-of-no-return battery percentage (0-100)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        # For PNR, we use distance as home_distance
        features = np.array([[50.0, voltage_sag, altitude, wind_speed, payload, home_distance]])
        features_scaled = self.scaler.transform(features)

        pnr_threshold = self.pnr_model.predict(features_scaled)[0]
        return float(np.clip(pnr_threshold, 5.0, 95.0))

    def get_feature_importance(self, model_type: str = "time") -> Dict[str, float]:
        """
        Get feature importance scores.

        Args:
            model_type: "time" or "pnr"

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        model = self.time_model if model_type == "time" else self.pnr_model

        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        else:
            raise ValueError(f"Model {type(model)} does not support feature importance")

        return dict(zip(self.feature_names, importances))

    def is_critical_battery(self, battery_percent: float, altitude: float,
                           home_distance: float, wind_speed: float,
                           payload: float, voltage_sag: float) -> Tuple[bool, str]:
        """
        Check if battery is at critical level requiring immediate action.

        Args:
            battery_percent: Current battery percentage
            altitude: Current altitude in meters
            home_distance: Distance to home in meters
            wind_speed: Wind speed in m/s
            payload: Payload mass in kg
            voltage_sag: Voltage sag in volts

        Returns:
            (is_critical, reason) tuple
        """
        if not self.is_trained:
            return False, "Model not trained"

        # Calculate PNR threshold
        pnr = self.predict_point_of_no_return(altitude, home_distance, wind_speed, payload, voltage_sag)

        # Calculate remaining time
        remaining_time = self.predict_remaining_time(
            battery_percent, voltage_sag, altitude, wind_speed, payload, home_distance
        )

        # Critical conditions
        if battery_percent <= pnr:
            return True, f"Battery {battery_percent:.1f}% at/below point-of-no-return ({pnr:.1f}%)"

        if remaining_time < 2.0:
            return True, f"Only {remaining_time:.1f} minutes remaining"

        # Calculate time needed to return
        time_to_return = self._estimate_return_time(altitude, home_distance, wind_speed)
        if remaining_time < time_to_return * 1.2:  # 20% safety margin
            return True, f"Remaining time {remaining_time:.1f}min insufficient for return (need {time_to_return:.1f}min)"

        return False, f"Battery safe: {battery_percent:.1f}%, {remaining_time:.1f}min remaining"

    def _estimate_return_time(self, altitude: float, distance: float, wind_speed: float) -> float:
        """Estimate time needed to return home (simple calculation)."""
        horizontal_time = distance / 8.0  # 8 m/s return speed
        vertical_time = altitude / 2.0  # 2 m/s descent
        # Add wind penalty
        wind_penalty = 1.0 + (wind_speed / 20.0)
        return ((horizontal_time + vertical_time) / 60.0) * wind_penalty

    def save_model(self, filepath: Optional[str] = None) -> str:
        """
        Save trained models to disk.

        Args:
            filepath: Path to save model (auto-generated if None)

        Returns:
            Path where models were saved
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        if filepath is None:
            cache_dir = Path(self.config.model_cache_dir)
            cache_dir.mkdir(exist_ok=True)
            filepath = cache_dir / "energy_predictor.joblib"

        model_data = {
            'time_model': self.time_model,
            'pnr_model': self.pnr_model,
            'scaler': self.scaler,
            'config': self.config,
            'is_trained': self.is_trained,
            'feature_names': self.feature_names
        }

        joblib.dump(model_data, filepath)
        return str(filepath)

    def load_model(self, filepath: str) -> None:
        """
        Load trained models from disk.

        Args:
            filepath: Path to saved model
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")

        model_data = joblib.load(filepath)

        self.time_model = model_data['time_model']
        self.pnr_model = model_data['pnr_model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']
        self.feature_names = model_data.get('feature_names', self.feature_names)


# Convenience functions

def create_and_train_energy_model(config: Optional[EnergyConfig] = None,
                                 n_training_samples: int = 5000) -> Tuple[EnergyPredictor, Dict[str, float]]:
    """
    Create and train energy prediction model with synthetic data.

    Args:
        config: Energy configuration (default if None)
        n_training_samples: Number of synthetic samples to generate

    Returns:
        Trained predictor and training metrics
    """
    if config is None:
        config = EnergyConfig()

    # Generate training data
    generator = SyntheticEnergyDataGenerator(config)
    features, time_labels, pnr_labels = generator.generate_training_dataset(n_training_samples)

    # Create and train predictor
    predictor = EnergyPredictor(config)
    metrics = predictor.train(features, time_labels, pnr_labels)

    return predictor, metrics


def load_or_create_energy_model(model_path: Optional[str] = None,
                               config: Optional[EnergyConfig] = None,
                               force_retrain: bool = False) -> EnergyPredictor:
    """
    Load cached model or create and train a new one.

    Args:
        model_path: Path to cached model
        config: Energy configuration
        force_retrain: Force retraining even if cache exists

    Returns:
        Trained energy predictor
    """
    if config is None:
        config = EnergyConfig()

    if model_path is None:
        cache_dir = Path(config.model_cache_dir)
        cache_dir.mkdir(exist_ok=True)
        model_path = cache_dir / "energy_predictor.joblib"

    predictor = EnergyPredictor(config)

    # Try to load cached model
    if not force_retrain and os.path.exists(model_path):
        try:
            predictor.load_model(str(model_path))
            return predictor
        except Exception as e:
            warnings.warn(f"Failed to load cached model: {e}. Training new model.")

    # Train new model
    predictor, metrics = create_and_train_energy_model(config)

    # Cache it
    predictor.save_model(str(model_path))

    return predictor
