#!/usr/bin/env python3
"""
ML Vision Terrain Classification Demo

Demonstrates the complete ML-based aerial terrain classifier including:
- Synthetic terrain generation
- 10D feature extraction (Canny, Laplacian, HSV, entropy, contrast)
- RandomForest training with joblib caching
- Continuous risk scoring (0.0-1.0) via predict_proba()
- Obstacle inflation buffering
- Integration with LandingZoneGrid

Usage:
    python demo_ml_vision.py
"""

import sys
import numpy as np
import cv2
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_terrain_ml import (
    TerrainConfig,
    TerrainFeatureExtractor,
    SyntheticTerrainGenerator,
    TerrainClassifier,
    RiskMapper,
    create_and_train_model,
    load_or_create_classifier
)
from src.landing_zone_grid import LandingZoneGrid


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_feature_extraction():
    """Demonstrate 10D feature extraction."""
    print_section("1. Feature Extraction (10D Vector)")

    config = TerrainConfig()
    extractor = TerrainFeatureExtractor(config)
    generator = SyntheticTerrainGenerator(config)

    # Generate sample patches
    safe_patch = generator._generate_safe_patch(100)
    obstacle_patch = generator._generate_obstacle_patch(100)

    # Extract features
    safe_features = extractor.extract_features(safe_patch)
    obstacle_features = extractor.extract_features(obstacle_patch)

    print("\nFeature Vector Components:")
    print("  1. Canny edge density")
    print("  2. Laplacian variance (roughness)")
    print("  3-8. HSV mean/std (H_mean, H_std, S_mean, S_std, V_mean, V_std)")
    print("  9. Local entropy")
    print("  10. Local contrast")

    print(f"\nSafe Patch Features:")
    print(f"  Edge Density:    {safe_features[0]:.4f}")
    print(f"  Laplacian Var:   {safe_features[1]:.4f}")
    print(f"  HSV H mean/std:  {safe_features[2]:.2f} / {safe_features[3]:.2f}")
    print(f"  HSV S mean/std:  {safe_features[4]:.2f} / {safe_features[5]:.2f}")
    print(f"  HSV V mean/std:  {safe_features[6]:.2f} / {safe_features[7]:.2f}")
    print(f"  Entropy:         {safe_features[8]:.4f}")
    print(f"  Contrast:        {safe_features[9]:.4f}")

    print(f"\nObstacle Patch Features:")
    print(f"  Edge Density:    {obstacle_features[0]:.4f}")
    print(f"  Laplacian Var:   {obstacle_features[1]:.4f}")
    print(f"  HSV H mean/std:  {obstacle_features[2]:.2f} / {obstacle_features[3]:.2f}")
    print(f"  HSV S mean/std:  {obstacle_features[4]:.2f} / {obstacle_features[5]:.2f}")
    print(f"  HSV V mean/std:  {obstacle_features[6]:.2f} / {obstacle_features[7]:.2f}")
    print(f"  Entropy:         {obstacle_features[8]:.4f}")
    print(f"  Contrast:        {obstacle_features[9]:.4f}")

    print("\n✓ Feature extraction complete")

    return safe_patch, obstacle_patch


def demo_synthetic_terrain_generation():
    """Demonstrate synthetic terrain generation."""
    print_section("2. Synthetic Terrain Generation")

    config = TerrainConfig(grid_size=7)
    generator = SyntheticTerrainGenerator(config)

    print("\nGenerating training dataset...")
    n_samples = 1000
    features, labels = generator.generate_training_dataset(n_samples)

    safe_count = np.sum(labels == 0)
    obstacle_count = np.sum(labels == 1)

    print(f"  Total samples:    {n_samples}")
    print(f"  Safe patches:     {safe_count} ({safe_count/n_samples*100:.1f}%)")
    print(f"  Obstacle patches: {obstacle_count} ({obstacle_count/n_samples*100:.1f}%)")
    print(f"  Feature dims:     {features.shape[1]}D")

    print("\nGenerating full 7×7 terrain image...")
    obstacle_cells = [(1, 1), (2, 2), (3, 5), (5, 5)]
    terrain_image = generator.generate_full_terrain_image(7, obstacle_cells)

    print(f"  Image shape:      {terrain_image.shape}")
    print(f"  Obstacle cells:   {obstacle_cells}")
    print(f"  Cell size:        {terrain_image.shape[0] // 7}×{terrain_image.shape[1] // 7} pixels")

    print("\n✓ Synthetic terrain generation complete")

    return features, labels, terrain_image


def demo_classifier_training():
    """Demonstrate RandomForest classifier training."""
    print_section("3. RandomForest Classifier Training")

    config = TerrainConfig(n_estimators=100, random_state=42)

    print("\nTraining RandomForest classifier...")
    print(f"  Trees (n_estimators):  {config.n_estimators}")
    print(f"  CPU-friendly:          Yes (scikit-learn, n_jobs=-1)")

    classifier, metrics = create_and_train_model(config, n_training_samples=1000)

    print(f"\nTraining Results:")
    print(f"  Training samples:   {metrics['n_train']}")
    print(f"  Validation samples: {metrics['n_val']}")
    print(f"  Train accuracy:     {metrics['train_accuracy']:.4f} ({metrics['train_accuracy']*100:.2f}%)")
    print(f"  Val accuracy:       {metrics['val_accuracy']:.4f} ({metrics['val_accuracy']*100:.2f}%)")

    print("\n✓ Classifier training complete")

    return classifier


def demo_model_caching(classifier):
    """Demonstrate model caching with joblib."""
    print_section("4. Model Caching (joblib)")

    print("\nSaving model to disk...")
    model_path = Path("models") / "terrain_classifier_demo.joblib"
    model_path.parent.mkdir(exist_ok=True)

    saved_path = classifier.save_model(str(model_path))
    print(f"  Model saved:  {saved_path}")

    # Check file size
    file_size = model_path.stat().st_size / 1024  # KB
    print(f"  File size:    {file_size:.2f} KB")

    print("\nLoading model from cache...")
    config = TerrainConfig()
    loaded_classifier = TerrainClassifier(config)
    loaded_classifier.load_model(str(model_path))

    print(f"  Model loaded: {saved_path}")
    print(f"  Trained:      {loaded_classifier.is_trained}")

    print("\n✓ Model caching complete")


def demo_risk_prediction(classifier, terrain_image):
    """Demonstrate continuous risk scoring."""
    print_section("5. Continuous Risk Scoring (0.0-1.0)")

    config = TerrainConfig(grid_size=7)
    risk_mapper = RiskMapper(config, classifier)

    print("\nComputing risk grid from terrain image...")
    risk_grid = risk_mapper.compute_risk_grid(terrain_image, grid_size=7)

    print(f"  Risk grid shape: {risk_grid.shape}")
    print(f"  Min risk:        {np.min(risk_grid):.4f}")
    print(f"  Max risk:        {np.max(risk_grid):.4f}")
    print(f"  Mean risk:       {np.mean(risk_grid):.4f}")

    print("\nRisk Grid (7×7):")
    print("  (0.0 = safe, 1.0 = obstacle)\n")

    # Print risk grid
    for row in range(7):
        row_str = "  "
        for col in range(7):
            risk = risk_grid[row, col]
            row_str += f"{risk:.2f} "
        print(row_str)

    # Count safe vs unsafe
    threshold = 0.5
    safe_cells = np.sum(risk_grid < threshold)
    unsafe_cells = np.sum(risk_grid >= threshold)

    print(f"\nAt threshold {threshold}:")
    print(f"  Safe cells:      {safe_cells}/{49} ({safe_cells/49*100:.1f}%)")
    print(f"  Unsafe cells:    {unsafe_cells}/{49} ({unsafe_cells/49*100:.1f}%)")

    print("\n✓ Risk scoring complete")

    return risk_grid


def demo_obstacle_inflation(classifier, risk_grid):
    """Demonstrate obstacle inflation buffering."""
    print_section("6. Obstacle Inflation Buffering")

    config = TerrainConfig(grid_size=7, inflation_radius=1)
    risk_mapper = RiskMapper(config, classifier)

    print(f"\nApplying obstacle inflation (radius={config.inflation_radius})...")

    inflated_grid = risk_mapper.apply_obstacle_inflation(risk_grid, inflation_radius=1)

    print("\nInflated Risk Grid (7×7):")
    print("  (High-risk cells propagate to neighbors)\n")

    for row in range(7):
        row_str = "  "
        for col in range(7):
            risk = inflated_grid[row, col]
            row_str += f"{risk:.2f} "
        print(row_str)

    # Compare before/after
    threshold = 0.5
    safe_before = np.sum(risk_grid < threshold)
    safe_after = np.sum(inflated_grid < threshold)

    print(f"\nInflation Effect (threshold={threshold}):")
    print(f"  Safe cells before: {safe_before}")
    print(f"  Safe cells after:  {safe_after}")
    print(f"  Buffer created:    {safe_before - safe_after} cells marked unsafe")

    print("\n✓ Obstacle inflation complete")

    return inflated_grid


def demo_safe_zone_detection(classifier, inflated_grid):
    """Demonstrate safe landing zone detection."""
    print_section("7. Safe Landing Zone Detection")

    config = TerrainConfig(grid_size=7)
    risk_mapper = RiskMapper(config, classifier)

    threshold = 0.5
    safe_zones = risk_mapper.get_safe_landing_zones(inflated_grid, threshold=threshold)

    print(f"\nDetecting safe landing zones (threshold={threshold})...")
    print(f"  Safe zones found: {len(safe_zones)}")

    if safe_zones:
        print("\nSafe Landing Zones:")
        for i, (row, col) in enumerate(safe_zones[:10], 1):
            risk = inflated_grid[row, col]
            print(f"  {i}. Cell ({row}, {col}) - Risk: {risk:.4f}")

        if len(safe_zones) > 10:
            print(f"  ... and {len(safe_zones) - 10} more")

    print("\n✓ Safe zone detection complete")


def demo_landing_zone_grid_integration(terrain_image):
    """Demonstrate integration with LandingZoneGrid."""
    print_section("8. LandingZoneGrid Integration")

    config = TerrainConfig(grid_size=7, random_state=42)

    print("\nInitializing LandingZoneGrid with ML vision...")
    grid = LandingZoneGrid(grid_size=7, use_ml_vision=True, ml_config=config)

    print(f"  Grid size:        {grid.grid_size}×{grid.grid_size}")
    print(f"  ML vision:        {grid.use_ml_vision}")
    print(f"  Drone position:   {grid.drone_position}")

    print("\nAnalyzing terrain from aerial image...")
    risk_grid = grid.analyze_terrain_from_image(terrain_image, apply_inflation=True)

    print(f"  Risk grid shape:  {risk_grid.shape}")
    print(f"  Mean risk:        {np.mean(risk_grid):.4f}")

    print("\nFinding nearest safe landing cell...")
    nearest = grid.find_nearest_safe_cell(scan_radius=3, risk_threshold=0.5)

    if nearest:
        row, col = nearest
        risk = grid.get_cell_risk_score(row, col)
        distance = grid.get_distance_to_cell(row, col)

        print(f"  Nearest safe:     ({row}, {col})")
        print(f"  Risk score:       {risk:.4f}")
        print(f"  Distance:         {distance:.2f} cells")

    print("\nGetting all safe landing zones with ML...")
    safe_zones_ml = grid.get_safe_landing_zones_ml(risk_threshold=0.5)

    print(f"  Safe zones:       {len(safe_zones_ml)}")

    if safe_zones_ml:
        print("\n  Top 5 safest zones:")
        for i, (row, col, risk) in enumerate(safe_zones_ml[:5], 1):
            distance = grid.get_distance_to_cell(row, col)
            print(f"    {i}. ({row}, {col}) - Risk: {risk:.4f}, Distance: {distance:.2f}")

    print("\nASCII Grid Visualization (with risk scores):")
    print(grid.render_grid_ascii(show_risk_scores=True))

    print("\nASCII Grid Visualization (symbolic):")
    print(grid.render_grid_ascii(show_risk_scores=False))
    print("\n  Legend: D=Drone, X=Obstacle, *=Nearest safe, S=Scanned, .=Empty")

    print("\n✓ LandingZoneGrid integration complete")


def demo_backward_compatibility():
    """Demonstrate backward compatibility."""
    print_section("9. Backward Compatibility")

    print("\nTesting grid WITHOUT ML vision (original functionality)...")
    grid_classic = LandingZoneGrid(grid_size=7)

    print(f"  ML vision:        {grid_classic.use_ml_vision}")
    print(f"  Grid initialized: ✓")

    # Set obstacles the classic way
    grid_classic.set_obstacles([(2, 2), (3, 3), (4, 4)])

    print("\nClassic obstacle detection:")
    for row, col in [(2, 2), (3, 3), (5, 5)]:
        safe = grid_classic.is_cell_safe(row, col)
        print(f"  Cell ({row}, {col}): {'Safe' if safe else 'Obstacle'}")

    # Find nearest safe cell
    nearest = grid_classic.find_nearest_safe_cell(scan_radius=2)
    print(f"\n  Nearest safe:     {nearest}")

    print("\nASCII Grid (classic mode):")
    print(grid_classic.render_grid_ascii())

    print("\n✓ All original functionality preserved")


def demo_different_grid_sizes():
    """Demonstrate different grid sizes."""
    print_section("10. Configurable Grid Sizes")

    print("\nTesting different N×N grid configurations...\n")

    for grid_size in [5, 7, 10]:
        config = TerrainConfig(grid_size=grid_size, random_state=42)
        generator = SyntheticTerrainGenerator(config)

        # Generate terrain
        terrain_image = generator.generate_full_terrain_image(grid_size)

        # Create grid with ML
        grid = LandingZoneGrid(grid_size=grid_size, use_ml_vision=True, ml_config=config)

        # Analyze
        risk_grid = grid.analyze_terrain_from_image(terrain_image)

        safe_count = np.sum(risk_grid < 0.5)
        total_cells = grid_size * grid_size

        print(f"  {grid_size}×{grid_size} Grid:")
        print(f"    Total cells:  {total_cells}")
        print(f"    Safe cells:   {safe_count} ({safe_count/total_cells*100:.1f}%)")
        print(f"    Image size:   {terrain_image.shape[0]}×{terrain_image.shape[1]}")
        print()

    print("✓ Multi-size grid support verified")


def main():
    """Run complete demonstration."""
    print("\n" + "=" * 70)
    print("  AutoLandrone ML Vision Terrain Classification Demo")
    print("  Production-Ready RandomForest Aerial Terrain Analyzer")
    print("=" * 70)

    try:
        # Run demos
        safe_patch, obstacle_patch = demo_feature_extraction()
        features, labels, terrain_image = demo_synthetic_terrain_generation()
        classifier = demo_classifier_training()
        demo_model_caching(classifier)
        risk_grid = demo_risk_prediction(classifier, terrain_image)
        inflated_grid = demo_obstacle_inflation(classifier, risk_grid)
        demo_safe_zone_detection(classifier, inflated_grid)
        demo_landing_zone_grid_integration(terrain_image)
        demo_backward_compatibility()
        demo_different_grid_sizes()

        # Summary
        print_section("Summary")
        print("\n✓ All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✓ 10D feature extraction (Canny, Laplacian, HSV, entropy, contrast)")
        print("  ✓ Synthetic procedural terrain generation")
        print("  ✓ RandomForest training with scikit-learn (CPU-friendly)")
        print("  ✓ Model caching with joblib")
        print("  ✓ Continuous risk scores (0.0-1.0) via predict_proba()")
        print("  ✓ Obstacle inflation buffering")
        print("  ✓ LandingZoneGrid integration")
        print("  ✓ Complete backward compatibility")
        print("  ✓ Configurable N×N grids")
        print("\nSystem Status: OPERATIONAL ✓")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
