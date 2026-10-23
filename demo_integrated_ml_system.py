"""
Comprehensive Demo: ML-Powered Autonomous Drone Landing System

Demonstrates integration of:
1. Energy ML Model - Battery prediction and point-of-no-return
2. Vision Terrain ML - Risk grid generation
3. Path Planner - 3D A* pathfinding
4. Decision Engine - Multi-criteria landing zone selection

This demo simulates a complete landing scenario with ML-based decision making.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import sys

# Import all components
from src.vision_terrain_ml import (
    TerrainConfig, SyntheticTerrainGenerator, create_and_train_model as create_terrain_model
)
from src.energy_ml_model import (
    EnergyConfig, create_and_train_energy_model
)
from src.path_planner import PathPlanner, PathPlannerConfig
from src.decision_engine import DecisionEngine, LandingZoneScorer


def create_demo_scenario():
    """Create a realistic landing scenario with obstacles."""
    print("=" * 70)
    print("ML-POWERED AUTONOMOUS DRONE LANDING SYSTEM - COMPREHENSIVE DEMO")
    print("=" * 70)
    print()

    # 1. Setup Vision Terrain ML
    print("Step 1: Initializing Vision Terrain ML System...")
    terrain_config = TerrainConfig(grid_size=7, random_state=42)
    terrain_classifier, terrain_metrics = create_terrain_model(terrain_config, n_training_samples=1000)
    print(f"  [OK] Terrain classifier trained (Val accuracy: {terrain_metrics['val_accuracy']:.3f})")
    print()

    # 2. Generate synthetic terrain image with obstacles
    print("Step 2: Generating Terrain Image...")
    generator = SyntheticTerrainGenerator(terrain_config)
    obstacle_cells = [(2, 2), (2, 3), (3, 2), (5, 4), (4, 5)]  # Predefined obstacles
    terrain_image = generator.generate_full_terrain_image(7, obstacle_cells)
    print(f"  [OK] Generated 7x7 terrain with {len(obstacle_cells)} obstacles")
    print()

    # 3. Compute risk grid using ML vision
    print("Step 3: Computing ML Risk Grid...")
    from src.vision_terrain_ml import RiskMapper
    risk_mapper = RiskMapper(terrain_config, terrain_classifier)
    risk_grid = risk_mapper.compute_risk_grid(terrain_image, grid_size=7)
    risk_grid_inflated = risk_mapper.apply_obstacle_inflation(risk_grid, inflation_radius=1)
    print(f"  [OK] Risk grid computed with obstacle inflation")
    print(f"  [OK] Safe cells: {np.sum(risk_grid_inflated < 0.5)} / 49")
    print()

    # 4. Setup Energy ML Model
    print("Step 4: Training Energy Prediction Model...")
    energy_config = EnergyConfig(random_state=42, n_estimators=100)
    energy_predictor, energy_metrics = create_and_train_energy_model(energy_config, n_training_samples=2000)
    print(f"  [OK] Energy predictor trained (Time R2: {energy_metrics['time_val_r2']:.3f}, PNR R2: {energy_metrics['pnr_val_r2']:.3f})")
    print()

    # 5. Flight scenario parameters
    print("Step 5: Flight Scenario Parameters")
    print("-" * 70)
    battery_percent = 18.0
    altitude = 30.0
    wind_speed = 7.0
    wind_direction = 135.0  # Southeast wind
    payload = 1.2
    voltage_sag = 1.0
    home_distance = 100.0
    drone_position = (1, 1)  # Starting position

    print(f"  Battery: {battery_percent}%")
    print(f"  Altitude: {altitude}m")
    print(f"  Wind: {wind_speed} m/s @ {wind_direction}°")
    print(f"  Payload: {payload} kg")
    print(f"  Voltage Sag: {voltage_sag}V")
    print(f"  Distance to Home: {home_distance}m")
    print(f"  Drone Position: {drone_position}")
    print()

    # 6. Energy predictions
    print("Step 6: Energy Analysis")
    print("-" * 70)
    remaining_time = energy_predictor.predict_remaining_time(
        battery_percent, voltage_sag, altitude, wind_speed, payload, home_distance
    )
    pnr = energy_predictor.predict_point_of_no_return(
        altitude, home_distance, wind_speed, payload, voltage_sag
    )
    is_critical, energy_reason = energy_predictor.is_critical_battery(
        battery_percent, altitude, home_distance, wind_speed, payload, voltage_sag
    )

    print(f"  Remaining Flight Time: {remaining_time:.1f} minutes")
    print(f"  Point-of-No-Return: {pnr:.1f}%")
    print(f"  Battery Status: {'CRITICAL' if is_critical else 'SAFE'}")
    print(f"  Reason: {energy_reason}")
    print()

    # 7. Multi-criteria landing zone scoring
    print("Step 7: Landing Zone Evaluation (Multi-Criteria Scoring)")
    print("-" * 70)
    scorer = LandingZoneScorer(
        distance_weight=1.0,
        risk_weight=3.0,
        obstacle_weight=2.0,
        wind_weight=0.5
    )

    wind_rad = np.radians(wind_direction)
    wind_vector = (wind_speed * np.sin(wind_rad), wind_speed * np.cos(wind_rad))

    top_zones = scorer.rank_landing_zones(
        drone_position=drone_position,
        risk_grid=risk_grid_inflated,
        wind_vector=wind_vector,
        max_risk_threshold=0.5,
        top_k=3
    )

    print(f"  Found {len(top_zones)} safe landing zones\n")
    for i, zone in enumerate(top_zones, 1):
        print(f"  Option {i}: Cell {zone['cell']}")
        print(f"    Total Cost: {zone['total_cost']:.3f}")
        print(f"    Distance: {zone['distance_m']:.1f}m")
        print(f"    Terrain Risk: {zone['terrain_risk']:.3f}")
        print(f"    Contributions: Distance={zone['feature_contributions']['distance']}, "
              f"Risk={zone['feature_contributions']['terrain_risk']}, "
              f"Obstacle={zone['feature_contributions']['obstacle_proximity']}, "
              f"Wind={zone['feature_contributions']['wind_drift']}")
        print()

    # 8. Path planning to best zone
    best_zone = top_zones[0]
    print("Step 8: 3D Path Planning to Best Landing Zone")
    print("-" * 70)

    path_config = PathPlannerConfig(
        grid_size=7,
        altitude_levels=10,
        max_altitude=30.0,
        enable_wind_drift=True
    )
    planner = PathPlanner(path_config)
    planner.set_risk_grid(risk_grid_inflated)
    planner.set_wind(wind_speed, wind_direction)

    start_pos = (drone_position[1], drone_position[0], 8)  # High altitude
    goal_pos = (best_zone['cell'][1], best_zone['cell'][0], 0)  # Ground level

    path = planner.plan_path(start_pos, goal_pos)

    if path:
        path_stats = planner.get_path_statistics(path)
        print(f"  ✓ Path found: {path_stats['waypoint_count']} waypoints")
        print(f"  Total Distance: {path_stats['total_distance_m']:.1f}m")
        print(f"  Horizontal Distance: {path_stats['horizontal_distance_m']:.1f}m")
        print(f"  Average Risk: {path_stats['average_risk']:.3f}")
        print(f"  Altitude Changes: {path_stats['altitude_change_count']}")
        print()

        # Simplify path for display
        simplified_path = planner.simplify_path(path, max_waypoints=8)
        print(f"  Simplified to {len(simplified_path)} key waypoints:")
        for i, waypoint in enumerate(simplified_path):
            meters = planner.convert_path_to_meters([waypoint])[0]
            print(f"    {i+1}. Grid({waypoint[0]}, {waypoint[1]}, {waypoint[2]}) → "
                  f"Meters({meters[0]:.1f}m, {meters[1]:.1f}m, {meters[2]:.1f}m)")
    else:
        print("  ✗ No valid path found!")
    print()

    # 9. Decision Engine Integration
    print("Step 9: Integrated Decision Engine")
    print("-" * 70)

    decision_engine = DecisionEngine(
        enable_ml_energy=True,
        enable_path_planning=True,
        energy_predictor=energy_predictor,
        path_planner=planner
    )

    decision_result = decision_engine.evaluate(
        battery_percent=battery_percent,
        obstacle_distance=5.0,
        drone_position=drone_position,
        risk_grid=risk_grid_inflated,
        altitude=altitude,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        payload=payload,
        voltage_sag=voltage_sag,
        home_distance=home_distance
    )

    if len(decision_result) == 4:
        state, action, reason, extra_data = decision_result
        print(f"  State: {state}")
        print(f"  Action: {action}")
        print(f"  Reason: {reason}")
        print(f"\n  Extra Data:")
        print(f"    Remaining Time: {extra_data['remaining_time']:.1f} min")
        print(f"    Point-of-No-Return: {extra_data['pnr']:.1f}%")
        print(f"    Path Valid: {extra_data['path_valid']}")
    else:
        state, action, reason = decision_result
        print(f"  State: {state}")
        print(f"  Action: {action}")
        print(f"  Reason: {reason}")
    print()

    # 10. Visualization
    print("Step 10: Generating Visualization...")
    visualize_scenario(
        risk_grid_inflated, drone_position, top_zones, path if path else None,
        battery_percent, remaining_time, pnr, is_critical
    )
    print("  ✓ Visualization complete")
    print()

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


def visualize_scenario(risk_grid, drone_pos, top_zones, path, battery, remaining_time, pnr, is_critical):
    """Create comprehensive visualization of the landing scenario."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # Plot 1: Risk Grid Heatmap
    ax1 = axes[0]
    im1 = ax1.imshow(risk_grid, cmap='RdYlGn_r', vmin=0, vmax=1, origin='upper')
    ax1.set_title('ML Terrain Risk Grid\n(Red=High Risk, Green=Safe)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Column')
    ax1.set_ylabel('Row')

    # Mark drone position
    ax1.plot(drone_pos[1], drone_pos[0], 'b*', markersize=20, label='Drone', markeredgecolor='white', markeredgewidth=2)

    # Mark top landing zones
    colors = ['gold', 'silver', 'brown']
    for i, zone in enumerate(top_zones[:3]):
        ax1.plot(zone['cell'][1], zone['cell'][0], 'o', color=colors[i],
                markersize=15, label=f'Option {i+1}', markeredgecolor='white', markeredgewidth=2)

    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    plt.colorbar(im1, ax=ax1, label='Risk Score')

    # Plot 2: Landing Zone Scores
    ax2 = axes[1]
    zone_labels = [f"Cell {z['cell']}" for z in top_zones]
    costs = [z['total_cost'] for z in top_zones]
    distances = [z['distance_m'] for z in top_zones]
    risks = [z['terrain_risk'] * 10 for z in top_zones]  # Scale for visibility

    x = np.arange(len(zone_labels))
    width = 0.25

    ax2.bar(x - width, costs, width, label='Total Cost', color='steelblue')
    ax2.bar(x, distances, width, label='Distance (m)', color='orange')
    ax2.bar(x + width, risks, width, label='Risk (×10)', color='red')

    ax2.set_xlabel('Landing Zone Options')
    ax2.set_ylabel('Score')
    ax2.set_title('Multi-Criteria Landing Zone Comparison', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(zone_labels)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # Plot 3: 3D Path (Top-Down View)
    ax3 = axes[2]
    ax3.imshow(risk_grid, cmap='RdYlGn_r', vmin=0, vmax=1, alpha=0.3, origin='upper')
    ax3.set_title('3D Flight Path (Top-Down View)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Column')
    ax3.set_ylabel('Row')

    if path:
        # Extract x, y coordinates and altitude for coloring
        path_x = [p[0] for p in path]
        path_y = [p[1] for p in path]
        path_z = [p[2] for p in path]

        # Plot path with altitude color coding
        scatter = ax3.scatter(path_x, path_y, c=path_z, cmap='viridis',
                             s=100, edgecolors='white', linewidths=2, label='Waypoints')

        # Connect waypoints
        ax3.plot(path_x, path_y, 'b-', linewidth=2, alpha=0.6)

        # Mark start and end
        ax3.plot(path_x[0], path_y[0], 'g^', markersize=15, label='Start',
                markeredgecolor='white', markeredgewidth=2)
        ax3.plot(path_x[-1], path_y[-1], 'rv', markersize=15, label='Landing',
                markeredgecolor='white', markeredgewidth=2)

        plt.colorbar(scatter, ax=ax3, label='Altitude Level')
        ax3.legend(loc='upper right')
    else:
        ax3.text(3.5, 3.5, 'No Path Found', ha='center', va='center',
                fontsize=16, color='red', fontweight='bold')

    ax3.grid(True, alpha=0.3)

    # Add status text
    status_color = 'red' if is_critical else 'green'
    status_text = 'CRITICAL' if is_critical else 'SAFE'
    fig.suptitle(
        f'Autonomous Landing System | Battery: {battery:.1f}% ({status_text}) | '
        f'Remaining: {remaining_time:.1f}min | PNR: {pnr:.1f}%',
        fontsize=14, fontweight='bold', color=status_color
    )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig('ml_landing_system_demo.png', dpi=150, bbox_inches='tight')
    print("  ✓ Saved visualization to 'ml_landing_system_demo.png'")
    plt.show()


if __name__ == "__main__":
    try:
        create_demo_scenario()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
