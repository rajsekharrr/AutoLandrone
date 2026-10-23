"""
Vision-Based Terrain ML Classification

Production-ready scikit-learn RandomForest terrain classifier for aerial image analysis.
Extracts 10-dimensional feature vectors (Canny edge density, Laplacian variance,
HSV statistics, entropy, and contrast) to generate continuous risk scores (0.0-1.0)
across configurable N×N grids with obstacle inflation buffering.
"""

import numpy as np
import cv2
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List, Optional, Dict, Any
import joblib
import os
from pathlib import Path
from dataclasses import dataclass
import warnings


@dataclass
class TerrainConfig:
    """Configuration for terrain analysis."""
    grid_size: int = 7
    image_size: Tuple[int, int] = (700, 700)  # 100 pixels per cell for 7×7
    canny_low: int = 50
    canny_high: int = 150
    entropy_kernel_size: int = 9
    contrast_kernel_size: int = 9
    inflation_radius: int = 1  # Obstacle buffer cells
    risk_threshold: float = 0.5  # Threshold for binary obstacle classification
    model_cache_dir: str = "models"
    n_estimators: int = 100  # RandomForest trees
    random_state: int = 42


class TerrainFeatureExtractor:
    """
    Extracts 10-dimensional feature vectors from image patches.

    Features:
    1. Canny edge density
    2. Laplacian variance (roughness)
    3-8. HSV mean and std (H_mean, H_std, S_mean, S_std, V_mean, V_std)
    9. Local entropy
    10. Local contrast
    """

    def __init__(self, config: TerrainConfig):
        self.config = config

    def extract_features(self, image_patch: np.ndarray) -> np.ndarray:
        """
        Extract 10D feature vector from an image patch.

        Args:
            image_patch: BGR image patch (H×W×3)

        Returns:
            10-dimensional feature vector
        """
        features = []

        # Convert to grayscale for some features
        gray = cv2.cvtColor(image_patch, cv2.COLOR_BGR2GRAY)

        # Feature 1: Canny edge density
        edges = cv2.Canny(gray, self.config.canny_low, self.config.canny_high)
        edge_density = np.sum(edges > 0) / edges.size
        features.append(edge_density)

        # Feature 2: Laplacian variance (roughness measure)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_var = np.var(laplacian)
        features.append(laplacian_var)

        # Features 3-8: HSV mean and std
        hsv = cv2.cvtColor(image_patch, cv2.COLOR_BGR2HSV)
        for channel in range(3):
            features.append(np.mean(hsv[:, :, channel]))
            features.append(np.std(hsv[:, :, channel]))

        # Feature 9: Local entropy
        entropy = self._calculate_entropy(gray, self.config.entropy_kernel_size)
        features.append(entropy)

        # Feature 10: Local contrast (std of local region)
        contrast = self._calculate_contrast(gray, self.config.contrast_kernel_size)
        features.append(contrast)

        return np.array(features, dtype=np.float32)

    def _calculate_entropy(self, image: np.ndarray, kernel_size: int) -> float:
        """Calculate Shannon entropy of image."""
        # Calculate histogram
        hist, _ = np.histogram(image.flatten(), bins=256, range=(0, 256), density=True)
        # Remove zero entries
        hist = hist[hist > 0]
        # Calculate entropy
        entropy = -np.sum(hist * np.log2(hist))
        return entropy

    def _calculate_contrast(self, image: np.ndarray, kernel_size: int) -> float:
        """Calculate local contrast using standard deviation."""
        # Use blurred difference as contrast measure
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        contrast = np.std(image.astype(float) - blurred.astype(float))
        return contrast

    def extract_grid_features(self, image: np.ndarray, grid_size: int) -> np.ndarray:
        """
        Extract features for each cell in an N×N grid.

        Args:
            image: Full aerial image (H×W×3)
            grid_size: Number of cells per dimension

        Returns:
            Array of shape (grid_size, grid_size, 10) with features per cell
        """
        h, w = image.shape[:2]
        cell_h = h // grid_size
        cell_w = w // grid_size

        features_grid = np.zeros((grid_size, grid_size, 10), dtype=np.float32)

        for row in range(grid_size):
            for col in range(grid_size):
                # Extract cell patch
                y_start = row * cell_h
                y_end = (row + 1) * cell_h
                x_start = col * cell_w
                x_end = (col + 1) * cell_w

                patch = image[y_start:y_end, x_start:x_end]

                # Extract features
                features_grid[row, col] = self.extract_features(patch)

        return features_grid


class SyntheticTerrainGenerator:
    """
    Generates synthetic procedural aerial terrain images for training.

    Creates varied terrain types: flat/safe areas, rocky/rough obstacles,
    edges, shadows, and textured regions.
    """

    def __init__(self, config: TerrainConfig):
        self.config = config
        self.rng = np.random.RandomState(config.random_state)

    def generate_training_dataset(self, n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training dataset with labels.

        Args:
            n_samples: Number of training samples to generate

        Returns:
            features: (n_samples, 10) feature array
            labels: (n_samples,) binary labels (0=safe, 1=obstacle)
        """
        features_list = []
        labels_list = []

        extractor = TerrainFeatureExtractor(self.config)

        # Generate roughly balanced dataset
        n_safe = n_samples // 2
        n_obstacle = n_samples - n_safe

        # Generate safe terrain patches
        for _ in range(n_safe):
            patch = self._generate_safe_patch()
            features = extractor.extract_features(patch)
            features_list.append(features)
            labels_list.append(0)

        # Generate obstacle patches
        for _ in range(n_obstacle):
            patch = self._generate_obstacle_patch()
            features = extractor.extract_features(patch)
            features_list.append(features)
            labels_list.append(1)

        return np.array(features_list), np.array(labels_list)

    def _generate_safe_patch(self, size: int = 100) -> np.ndarray:
        """Generate a safe landing zone patch (smooth, low texture)."""
        # Create base color (grass, concrete, etc.)
        base_color = self.rng.randint(60, 200, size=3)
        patch = np.ones((size, size, 3), dtype=np.uint8) * base_color

        # Add subtle noise
        noise = self.rng.normal(0, 10, size=(size, size, 3))
        patch = np.clip(patch.astype(float) + noise, 0, 255).astype(np.uint8)

        # Add gentle gradient
        gradient = np.linspace(0, 20, size)
        patch[:, :, 1] = np.clip(patch[:, :, 1] + gradient[:, None], 0, 255)

        # Smooth it out
        patch = cv2.GaussianBlur(patch, (5, 5), 0)

        return patch

    def _generate_obstacle_patch(self, size: int = 100) -> np.ndarray:
        """Generate an obstacle patch (rough, high texture, edges)."""
        obstacle_type = self.rng.choice(['rocky', 'tree', 'building', 'shadow'])

        if obstacle_type == 'rocky':
            # Rocky terrain with high texture
            patch = self.rng.randint(40, 140, size=(size, size, 3), dtype=np.uint8)
            # Add strong texture
            for _ in range(5):
                noise = self.rng.normal(0, 30, size=(size, size, 3))
                patch = np.clip(patch.astype(float) + noise, 0, 255).astype(np.uint8)

        elif obstacle_type == 'tree':
            # Dark blob representing trees/vegetation
            patch = np.full((size, size, 3), [20, 60, 20], dtype=np.uint8)
            # Add circular blobs
            for _ in range(self.rng.randint(2, 6)):
                center = (self.rng.randint(0, size), self.rng.randint(0, size))
                radius = self.rng.randint(10, 30)
                cv2.circle(patch, center, radius, (10, 40, 10), -1)

        elif obstacle_type == 'building':
            # Rectangular structure with edges
            base_color = np.array([120, 120, 120], dtype=np.uint8)
            patch = np.full((size, size, 3), base_color, dtype=np.uint8)
            # Ensure contiguous array for OpenCV
            patch = np.ascontiguousarray(patch)
            # Add rectangle
            pt1 = (self.rng.randint(5, 20), self.rng.randint(5, 20))
            pt2 = (self.rng.randint(size-20, size-5), self.rng.randint(size-20, size-5))
            cv2.rectangle(patch, pt1, pt2, (80, 80, 80), -1)
            # Add edge
            cv2.rectangle(patch, pt1, pt2, (40, 40, 40), 2)

        else:  # shadow
            # Dark shadow region
            base = self.rng.randint(80, 150, size=3)
            patch = np.full((size, size, 3), base, dtype=np.uint8)
            # Add dark shadow
            shadow = np.zeros((size, size, 3), dtype=np.uint8)
            shadow[:size//2, :] = [20, 20, 25]
            patch = cv2.addWeighted(patch, 0.5, shadow, 0.5, 0)

        return np.ascontiguousarray(patch, dtype=np.uint8)

    def generate_full_terrain_image(self, grid_size: int,
                                    obstacle_cells: Optional[List[Tuple[int, int]]] = None) -> np.ndarray:
        """
        Generate a full terrain image with specified obstacles.

        Args:
            grid_size: Size of grid (N×N)
            obstacle_cells: List of (row, col) positions to place obstacles

        Returns:
            Full terrain image
        """
        if obstacle_cells is None:
            # Random obstacles
            n_obstacles = self.rng.randint(grid_size, grid_size * 2)
            obstacle_cells = [
                (self.rng.randint(0, grid_size), self.rng.randint(0, grid_size))
                for _ in range(n_obstacles)
            ]

        obstacle_set = set(obstacle_cells)

        # Calculate cell size
        cell_size = self.config.image_size[0] // grid_size
        img_size = cell_size * grid_size

        terrain_image = np.zeros((img_size, img_size, 3), dtype=np.uint8)

        for row in range(grid_size):
            for col in range(grid_size):
                y_start = row * cell_size
                y_end = (row + 1) * cell_size
                x_start = col * cell_size
                x_end = (col + 1) * cell_size

                if (row, col) in obstacle_set:
                    patch = self._generate_obstacle_patch(cell_size)
                else:
                    patch = self._generate_safe_patch(cell_size)

                terrain_image[y_start:y_end, x_start:x_end] = patch

        return terrain_image


class TerrainClassifier:
    """
    RandomForest-based terrain classifier with model caching.

    Classifies terrain patches as safe (0) or obstacle (1) and provides
    continuous risk probability scores via predict_proba().
    """

    def __init__(self, config: TerrainConfig):
        self.config = config
        self.model = RandomForestClassifier(
            n_estimators=config.n_estimators,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=config.random_state,
            n_jobs=-1  # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.is_trained = False

    def train(self, features: np.ndarray, labels: np.ndarray,
              validation_split: float = 0.2) -> Dict[str, float]:
        """
        Train the RandomForest classifier.

        Args:
            features: (n_samples, 10) feature array
            labels: (n_samples,) binary labels
            validation_split: Fraction of data for validation

        Returns:
            Dictionary with training metrics
        """
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            features, labels, test_size=validation_split,
            random_state=self.config.random_state, stratify=labels
        )

        # Standardize features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Train model
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model.fit(X_train_scaled, y_train)

        self.is_trained = True

        # Calculate metrics
        train_accuracy = self.model.score(X_train_scaled, y_train)
        val_accuracy = self.model.score(X_val_scaled, y_val)

        return {
            'train_accuracy': train_accuracy,
            'val_accuracy': val_accuracy,
            'n_train': len(X_train),
            'n_val': len(X_val)
        }

    def predict_risk(self, features: np.ndarray) -> np.ndarray:
        """
        Predict continuous risk scores (0.0 = safe, 1.0 = obstacle).

        Args:
            features: (n_samples, 10) or (10,) feature array

        Returns:
            Risk probabilities for obstacle class
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        # Handle single sample
        if features.ndim == 1:
            features = features.reshape(1, -1)

        # Scale features
        features_scaled = self.scaler.transform(features)

        # Get probability of obstacle class (class 1)
        risk_probs = self.model.predict_proba(features_scaled)[:, 1]

        return risk_probs

    def save_model(self, filepath: Optional[str] = None) -> str:
        """
        Save trained model to disk using joblib.

        Args:
            filepath: Path to save model (auto-generated if None)

        Returns:
            Path where model was saved
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        if filepath is None:
            # Auto-generate path
            cache_dir = Path(self.config.model_cache_dir)
            cache_dir.mkdir(exist_ok=True)
            filepath = cache_dir / "terrain_classifier.joblib"

        # Save model and scaler together
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'config': self.config,
            'is_trained': self.is_trained
        }

        joblib.dump(model_data, filepath)
        return str(filepath)

    def load_model(self, filepath: str) -> None:
        """
        Load trained model from disk.

        Args:
            filepath: Path to saved model
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")

        model_data = joblib.load(filepath)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']
        # Config is not overwritten to allow runtime configuration


class RiskMapper:
    """
    Maps aerial images to risk grids with obstacle inflation buffering.

    Combines feature extraction, classification, and spatial processing
    to produce final risk maps for landing zone evaluation.
    """

    def __init__(self, config: TerrainConfig, classifier: TerrainClassifier):
        self.config = config
        self.classifier = classifier
        self.feature_extractor = TerrainFeatureExtractor(config)

    def compute_risk_grid(self, image: np.ndarray, grid_size: Optional[int] = None) -> np.ndarray:
        """
        Compute risk grid from aerial image.

        Args:
            image: Aerial image (H×W×3 BGR)
            grid_size: Override config grid size

        Returns:
            Risk grid (grid_size, grid_size) with values 0.0-1.0
        """
        if grid_size is None:
            grid_size = self.config.grid_size

        # Extract features for each cell
        features_grid = self.feature_extractor.extract_grid_features(image, grid_size)

        # Reshape to (n_cells, 10) for batch prediction
        features_flat = features_grid.reshape(-1, 10)

        # Predict risk scores
        risk_scores = self.classifier.predict_risk(features_flat)

        # Reshape back to grid
        risk_grid = risk_scores.reshape(grid_size, grid_size)

        return risk_grid

    def apply_obstacle_inflation(self, risk_grid: np.ndarray,
                                 inflation_radius: Optional[int] = None) -> np.ndarray:
        """
        Apply obstacle inflation buffering to risk grid.

        High-risk cells inflate their risk to neighboring cells to create
        safety margins around obstacles.

        Args:
            risk_grid: Original risk grid
            inflation_radius: Buffer radius in cells (default from config)

        Returns:
            Inflated risk grid
        """
        if inflation_radius is None:
            inflation_radius = self.config.inflation_radius

        if inflation_radius == 0:
            return risk_grid

        # Create inflated grid
        inflated = risk_grid.copy()
        grid_size = risk_grid.shape[0]

        # For each cell with high risk, inflate to neighbors
        for row in range(grid_size):
            for col in range(grid_size):
                if risk_grid[row, col] > self.config.risk_threshold:
                    # Inflate to neighboring cells
                    for dr in range(-inflation_radius, inflation_radius + 1):
                        for dc in range(-inflation_radius, inflation_radius + 1):
                            r, c = row + dr, col + dc
                            if 0 <= r < grid_size and 0 <= c < grid_size:
                                # Propagate risk (max operation)
                                distance = np.sqrt(dr**2 + dc**2)
                                if distance <= inflation_radius:
                                    # Decay risk with distance
                                    decay_factor = 1.0 - (distance / (inflation_radius + 1))
                                    propagated_risk = risk_grid[row, col] * decay_factor
                                    inflated[r, c] = max(inflated[r, c], propagated_risk)

        return inflated

    def get_safe_landing_zones(self, risk_grid: np.ndarray,
                               threshold: Optional[float] = None) -> List[Tuple[int, int]]:
        """
        Extract safe landing zone cells from risk grid.

        Args:
            risk_grid: Risk grid with values 0.0-1.0
            threshold: Risk threshold for safety (default from config)

        Returns:
            List of (row, col) positions that are safe
        """
        if threshold is None:
            threshold = self.config.risk_threshold

        safe_cells = []
        grid_size = risk_grid.shape[0]

        for row in range(grid_size):
            for col in range(grid_size):
                if risk_grid[row, col] < threshold:
                    safe_cells.append((row, col))

        return safe_cells


# Convenience functions for easy usage

def create_and_train_model(config: Optional[TerrainConfig] = None,
                          n_training_samples: int = 1000) -> Tuple[TerrainClassifier, Dict[str, float]]:
    """
    Create and train a terrain classifier with synthetic data.

    Args:
        config: Terrain configuration (default if None)
        n_training_samples: Number of synthetic samples to generate

    Returns:
        Trained classifier and training metrics
    """
    if config is None:
        config = TerrainConfig()

    # Generate synthetic training data
    generator = SyntheticTerrainGenerator(config)
    features, labels = generator.generate_training_dataset(n_training_samples)

    # Create and train classifier
    classifier = TerrainClassifier(config)
    metrics = classifier.train(features, labels)

    return classifier, metrics


def load_or_create_classifier(model_path: Optional[str] = None,
                              config: Optional[TerrainConfig] = None,
                              force_retrain: bool = False) -> TerrainClassifier:
    """
    Load cached model or create and train a new one.

    Args:
        model_path: Path to cached model
        config: Terrain configuration
        force_retrain: Force retraining even if cache exists

    Returns:
        Trained terrain classifier
    """
    if config is None:
        config = TerrainConfig()

    if model_path is None:
        cache_dir = Path(config.model_cache_dir)
        cache_dir.mkdir(exist_ok=True)
        model_path = cache_dir / "terrain_classifier.joblib"

    classifier = TerrainClassifier(config)

    # Try to load cached model
    if not force_retrain and os.path.exists(model_path):
        try:
            classifier.load_model(str(model_path))
            return classifier
        except Exception as e:
            warnings.warn(f"Failed to load cached model: {e}. Training new model.")

    # Train new model
    classifier, metrics = create_and_train_model(config)

    # Cache it
    classifier.save_model(str(model_path))

    return classifier
