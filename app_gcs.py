"""
AutoLandrone Ground Control Station (GCS) Dashboard

Interactive 3-tab Streamlit dashboard for ML-powered autonomous landing system:
- Tab 1: Live Mission Execution with 2D/3D trajectory plots
- Tab 2: Computer Vision Feature Inspector with Random Forest charts
- Tab 3: ML Energy Threshold Analyzer with comparative benchmarks

Features:
- 10Hz closed-loop PID simulation
- Interactive mid-descent obstacle injection
- Real-time re-planning visualization
- Lightweight, CPU-friendly dependencies
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from typing import Dict, Any, List, Tuple, Optional
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import AutoLandrone components
from src.landing_controller import LandingController
from src.vision_terrain_ml import (
    TerrainConfig, create_and_train_model, SyntheticTerrainGenerator,
    RiskMapper, TerrainFeatureExtractor
)
from src.energy_ml_model import (
    EnergyConfig, create_and_train_energy_model
)
from src.drone_dynamics import DroneConfig
from src.path_planner import PathPlannerConfig


# Page configuration
st.set_page_config(
    page_title="AutoLandrone GCS",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 18px;
        font-weight: bold;
        padding: 10px 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .status-good {
        color: green;
        font-weight: bold;
    }
    .status-warning {
        color: orange;
        font-weight: bold;
    }
    .status-critical {
        color: red;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'controller' not in st.session_state:
        st.session_state.controller = None
    if 'mission_active' not in st.session_state:
        st.session_state.mission_active = False
    if 'mission_data' not in st.session_state:
        st.session_state.mission_data = []
    if 'terrain_classifier' not in st.session_state:
        st.session_state.terrain_classifier = None
    if 'energy_predictor' not in st.session_state:
        st.session_state.energy_predictor = None
    if 'risk_grid' not in st.session_state:
        st.session_state.risk_grid = None
    if 'terrain_image' not in st.session_state:
        st.session_state.terrain_image = None
    if 'obstacle_cells' not in st.session_state:
        st.session_state.obstacle_cells = []
    if 'models_initialized' not in st.session_state:
        st.session_state.models_initialized = False


def initialize_ml_models():
    """Initialize ML models (cached in session state)."""
    if st.session_state.models_initialized:
        return

    with st.spinner("Initializing ML models..."):
        # Terrain classifier
        terrain_config = TerrainConfig(grid_size=7, random_state=42)
        st.session_state.terrain_classifier, _ = create_and_train_model(
            terrain_config, n_training_samples=1000
        )

        # Energy predictor
        energy_config = EnergyConfig(random_state=42, n_estimators=100)
        st.session_state.energy_predictor, _ = create_and_train_energy_model(
            energy_config, n_training_samples=2000
        )

        st.session_state.models_initialized = True


def create_terrain_scenario(obstacle_cells: List[Tuple[int, int]]):
    """Generate terrain image and risk grid."""
    terrain_config = TerrainConfig(grid_size=7, random_state=42)
    generator = SyntheticTerrainGenerator(terrain_config)

    # Generate terrain image
    terrain_image = generator.generate_full_terrain_image(7, obstacle_cells)

    # Compute risk grid
    risk_mapper = RiskMapper(terrain_config, st.session_state.terrain_classifier)
    risk_grid = risk_mapper.compute_risk_grid(terrain_image, grid_size=7)
    risk_grid_inflated = risk_mapper.apply_obstacle_inflation(risk_grid, inflation_radius=1)

    return terrain_image, risk_grid_inflated


def plot_risk_grid_2d(risk_grid: np.ndarray, drone_pos: Optional[Tuple[int, int]] = None,
                      target_pos: Optional[Tuple[int, int]] = None,
                      obstacles: Optional[List[Tuple[int, int]]] = None):
    """Create 2D risk grid heatmap with Plotly."""
    fig = go.Figure()

    # Heatmap
    fig.add_trace(go.Heatmap(
        z=risk_grid,
        colorscale='RdYlGn_r',
        zmin=0,
        zmax=1,
        colorbar=dict(title="Risk Score"),
        hovertemplate='Row: %{y}<br>Col: %{x}<br>Risk: %{z:.3f}<extra></extra>'
    ))

    # Add drone marker
    if drone_pos:
        fig.add_trace(go.Scatter(
            x=[drone_pos[1]],
            y=[drone_pos[0]],
            mode='markers',
            marker=dict(size=20, color='blue', symbol='star', line=dict(width=2, color='white')),
            name='Drone',
            hovertemplate='Drone Position<extra></extra>'
        ))

    # Add target marker
    if target_pos:
        fig.add_trace(go.Scatter(
            x=[target_pos[1]],
            y=[target_pos[0]],
            mode='markers',
            marker=dict(size=15, color='gold', symbol='diamond', line=dict(width=2, color='white')),
            name='Target',
            hovertemplate='Landing Target<extra></extra>'
        ))

    # Add obstacle markers
    if obstacles:
        obs_x = [o[1] for o in obstacles]
        obs_y = [o[0] for o in obstacles]
        fig.add_trace(go.Scatter(
            x=obs_x,
            y=obs_y,
            mode='markers',
            marker=dict(size=12, color='red', symbol='x', line=dict(width=2, color='darkred')),
            name='Obstacles',
            hovertemplate='Obstacle<extra></extra>'
        ))

    fig.update_layout(
        title="Terrain Risk Grid (7x7)",
        xaxis_title="Column",
        yaxis_title="Row",
        height=500,
        yaxis=dict(autorange='reversed'),
        showlegend=True
    )

    return fig


def plot_trajectory_3d(telemetry: List[Dict[str, Any]], waypoints: Optional[List[np.ndarray]] = None):
    """Create 3D trajectory plot with Plotly."""
    if not telemetry:
        return go.Figure()

    positions = np.array([t['position'] for t in telemetry])

    fig = go.Figure()

    # Trajectory trace
    fig.add_trace(go.Scatter3d(
        x=positions[:, 0],
        y=positions[:, 1],
        z=positions[:, 2],
        mode='lines+markers',
        marker=dict(size=3, color=positions[:, 2], colorscale='Viridis', showscale=True,
                   colorbar=dict(title="Altitude (m)")),
        line=dict(width=3, color='blue'),
        name='Trajectory',
        hovertemplate='X: %{x:.2f}m<br>Y: %{y:.2f}m<br>Z: %{z:.2f}m<extra></extra>'
    ))

    # Start marker
    fig.add_trace(go.Scatter3d(
        x=[positions[0, 0]],
        y=[positions[0, 1]],
        z=[positions[0, 2]],
        mode='markers',
        marker=dict(size=10, color='green', symbol='diamond'),
        name='Start',
        hovertemplate='Start Position<extra></extra>'
    ))

    # End marker
    fig.add_trace(go.Scatter3d(
        x=[positions[-1, 0]],
        y=[positions[-1, 1]],
        z=[positions[-1, 2]],
        mode='markers',
        marker=dict(size=10, color='red', symbol='cross'),
        name='Current',
        hovertemplate='Current Position<extra></extra>'
    ))

    # Waypoints (if provided)
    if waypoints:
        wp_array = np.array(waypoints)
        fig.add_trace(go.Scatter3d(
            x=wp_array[:, 0],
            y=wp_array[:, 1],
            z=wp_array[:, 2],
            mode='markers',
            marker=dict(size=5, color='orange', symbol='circle'),
            name='Waypoints',
            hovertemplate='Waypoint<extra></extra>'
        ))

    fig.update_layout(
        title="3D Trajectory",
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Altitude (m)",
            aspectmode='cube'
        ),
        height=600,
        showlegend=True
    )

    return fig


def render_tab1_mission_execution():
    """Tab 1: Live Mission Execution with interactive obstacle injection."""
    st.header("🚁 Live Mission Execution")

    # Sidebar controls
    with st.sidebar:
        st.subheader("Mission Configuration")

        # Initial obstacles
        st.write("**Initial Obstacles**")
        num_obstacles = st.slider("Number of obstacles", 0, 10, 5, key="num_obstacles")

        if st.button("Generate Random Obstacles"):
            rng = np.random.RandomState(int(time.time()))
            st.session_state.obstacle_cells = [
                (rng.randint(0, 7), rng.randint(0, 7)) for _ in range(num_obstacles)
            ]

        # Start position
        st.write("**Start Position**")
        start_x = st.slider("Start X (m)", 0.0, 30.0, 5.0, 1.0, key="start_x")
        start_y = st.slider("Start Y (m)", 0.0, 30.0, 5.0, 1.0, key="start_y")
        start_z = st.slider("Start Altitude (m)", 10.0, 30.0, 24.0, 2.0, key="start_z")

        # Target position
        st.write("**Target Landing Zone**")
        target_row = st.selectbox("Target Row", list(range(7)), index=5, key="target_row")
        target_col = st.selectbox("Target Col", list(range(7)), index=5, key="target_col")

        # Wind settings
        st.write("**Wind Disturbance**")
        wind_speed = st.slider("Wind Speed (m/s)", 0.0, 15.0, 5.0, 0.5, key="wind_speed")
        wind_direction = st.slider("Wind Direction (deg)", 0, 360, 135, 15, key="wind_dir")

        st.divider()

        # Start mission button
        if st.button("🚀 Start Mission", type="primary", disabled=st.session_state.mission_active):
            initialize_ml_models()

            # Create terrain
            terrain_image, risk_grid = create_terrain_scenario(st.session_state.obstacle_cells)
            st.session_state.terrain_image = terrain_image
            st.session_state.risk_grid = risk_grid

            # Initialize controller
            controller = LandingController(
                use_grid_simulation=True,
                grid_size=7,
                enable_ml=True,
                enable_dynamics=True
            )
            controller.grid.ml_risk_grid = risk_grid
            controller.grid.set_obstacles(st.session_state.obstacle_cells)

            # Set wind
            if controller.dynamics:
                wind_rad = np.radians(wind_direction)
                wind_vec = np.array([
                    wind_speed * np.sin(wind_rad),
                    wind_speed * np.cos(wind_rad),
                    0.0
                ])
                controller.dynamics.set_wind(wind_vec)

            # Start mission
            start_pos = np.array([start_x, start_y, start_z])
            target_cell = (target_row, target_col)

            if controller.start_mission(start_pos, target_cell, risk_grid):
                st.session_state.controller = controller
                st.session_state.mission_active = True
                st.session_state.mission_data = []
                st.success("Mission started!")
                st.rerun()
            else:
                st.error("Failed to start mission!")

    # Main content
    if not st.session_state.mission_active:
        st.info("Configure mission parameters in the sidebar and click 'Start Mission'")
        return

    # Mission status
    col1, col2, col3, col4 = st.columns(4)

    controller = st.session_state.controller

    # Update mission (10Hz simulation)
    status = controller.update_mission(dt=0.1)

    if status['active']:
        with col1:
            st.metric("Status", "🟢 ACTIVE")
        with col2:
            st.metric("Progress", f"{status['progress']*100:.1f}%")
        with col3:
            st.metric("Altitude", f"{status['position'][2]:.1f} m")
        with col4:
            st.metric("Re-plans", status['replans'])

        # Obstacle injection
        st.subheader("🎯 Interactive Obstacle Injection")
        col_inject1, col_inject2, col_inject3 = st.columns([2, 2, 1])

        with col_inject1:
            inject_row = st.selectbox("Inject Row", list(range(7)), key="inject_row")
        with col_inject2:
            inject_col = st.selectbox("Inject Col", list(range(7)), key="inject_col")
        with col_inject3:
            if st.button("💥 Drop Obstacle"):
                if controller.inject_obstacle_runtime((inject_row, inject_col)):
                    st.success(f"Obstacle injected at ({inject_row}, {inject_col})! Re-planning...")
                    st.session_state.obstacle_cells.append((inject_row, inject_col))
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.info("Obstacle added (no re-plan needed)")

        # Visualization
        col_vis1, col_vis2 = st.columns(2)

        telemetry = controller.get_mission_telemetry()

        with col_vis1:
            st.plotly_chart(
                plot_risk_grid_2d(
                    st.session_state.risk_grid,
                    drone_pos=(int(status['position'][1]/5), int(status['position'][0]/5)),
                    target_pos=(st.session_state.get('target_row', 5), st.session_state.get('target_col', 5)),
                    obstacles=st.session_state.obstacle_cells
                ),
                use_container_width=True
            )

        with col_vis2:
            if telemetry:
                remaining_wps = controller.waypoint_tracker.get_remaining_waypoints() if controller.waypoint_tracker else []
                st.plotly_chart(
                    plot_trajectory_3d(telemetry, remaining_wps),
                    use_container_width=True
                )

        # Telemetry table
        if telemetry and len(telemetry) > 0:
            st.subheader("📊 Real-Time Telemetry")
            recent_data = telemetry[-5:]  # Last 5 readings
            df = pd.DataFrame([{
                'Time': i,
                'X (m)': t['position'][0],
                'Y (m)': t['position'][1],
                'Z (m)': t['position'][2],
                'Vx (m/s)': t['velocity'][0],
                'Vy (m/s)': t['velocity'][1],
                'Vz (m/s)': t['velocity'][2],
            } for i, t in enumerate(recent_data)])
            st.dataframe(df, use_container_width=True)

        # Auto-refresh
        time.sleep(0.1)
        st.rerun()

    else:
        # Mission complete
        st.success("✅ Mission Complete!")

        summary = controller.get_mission_summary()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Distance", f"{summary.get('total_distance', 0):.2f} m")
        with col2:
            st.metric("Max Velocity", f"{summary.get('max_velocity', 0):.2f} m/s")
        with col3:
            st.metric("Total Re-plans", summary.get('replans', 0))

        # Final trajectory
        telemetry = controller.get_mission_telemetry()
        if telemetry:
            st.plotly_chart(
                plot_trajectory_3d(telemetry),
                use_container_width=True
            )

        if st.button("🔄 Reset Mission"):
            st.session_state.mission_active = False
            st.session_state.controller = None
            st.session_state.mission_data = []
            st.rerun()


def render_tab2_vision_inspector():
    """Tab 2: Computer Vision Feature Inspector."""
    st.header("🎥 Computer Vision Feature Inspector")

    initialize_ml_models()

    st.write("Analyze terrain classification features using Random Forest ML model.")

    # Generate sample terrain
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Terrain Configuration")
        terrain_type = st.selectbox(
            "Sample Terrain Type",
            ["Random Mixed", "Mostly Safe", "High Risk", "Custom Obstacles"]
        )

        if terrain_type == "Custom Obstacles":
            num_obs = st.slider("Number of obstacles", 0, 15, 5)
            obstacle_cells = [(np.random.randint(0, 7), np.random.randint(0, 7)) for _ in range(num_obs)]
        elif terrain_type == "Mostly Safe":
            obstacle_cells = [(2, 2), (5, 5)]
        elif terrain_type == "High Risk":
            obstacle_cells = [(i, j) for i in range(2, 5) for j in range(2, 5)]
        else:
            rng = np.random.RandomState(42)
            obstacle_cells = [(rng.randint(0, 7), rng.randint(0, 7)) for _ in range(7)]

        if st.button("Generate Terrain"):
            terrain_image, risk_grid = create_terrain_scenario(obstacle_cells)
            st.session_state.terrain_image = terrain_image
            st.session_state.risk_grid = risk_grid

    with col2:
        if st.session_state.risk_grid is not None:
            st.plotly_chart(
                plot_risk_grid_2d(st.session_state.risk_grid, obstacles=obstacle_cells),
                use_container_width=True
            )

    # Feature extraction and analysis
    if st.session_state.terrain_image is not None and st.session_state.terrain_classifier is not None:
        st.subheader("📊 Feature Analysis")

        # Extract features for all cells
        terrain_config = TerrainConfig(grid_size=7)
        extractor = TerrainFeatureExtractor(terrain_config)
        features_grid = extractor.extract_grid_features(st.session_state.terrain_image, 7)

        # Feature importance from Random Forest
        feature_importance = st.session_state.terrain_classifier.model.feature_importances_
        feature_names = [
            "Edge Density", "Roughness", "H Mean", "H Std",
            "S Mean", "S Std", "V Mean", "V Std", "Entropy", "Contrast"
        ]

        # Plot feature importance
        fig_importance = go.Figure()
        fig_importance.add_trace(go.Bar(
            x=feature_names,
            y=feature_importance,
            marker_color='steelblue'
        ))
        fig_importance.update_layout(
            title="Random Forest Feature Importance",
            xaxis_title="Feature",
            yaxis_title="Importance",
            height=400
        )
        st.plotly_chart(fig_importance, use_container_width=True)

        # Cell-by-cell feature breakdown
        st.subheader("🔍 Cell Feature Breakdown")

        selected_row = st.selectbox("Select Row", list(range(7)), key="inspect_row")
        selected_col = st.selectbox("Select Col", list(range(7)), key="inspect_col")

        cell_features = features_grid[selected_row, selected_col]
        cell_risk = st.session_state.risk_grid[selected_row, selected_col]

        col_feat1, col_feat2 = st.columns([1, 2])

        with col_feat1:
            st.metric("Risk Score", f"{cell_risk:.3f}")
            st.metric("Classification", "OBSTACLE" if cell_risk > 0.5 else "SAFE")

        with col_feat2:
            # Feature radar chart
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=cell_features,
                theta=feature_names,
                fill='toself',
                name=f'Cell ({selected_row}, {selected_col})'
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                title=f"Feature Vector for Cell ({selected_row}, {selected_col})",
                height=400
            )
            st.plotly_chart(fig_radar, use_container_width=True)


def render_tab3_energy_analyzer():
    """Tab 3: ML Energy Threshold Analyzer."""
    st.header("⚡ ML Energy Threshold Analyzer")

    initialize_ml_models()

    st.write("Analyze energy predictions and point-of-no-return thresholds.")

    # Input parameters
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Flight Parameters")
        battery_percent = st.slider("Battery (%)", 0.0, 100.0, 60.0, 1.0)
        voltage_sag = st.slider("Voltage Sag (V)", 0.0, 3.0, 1.0, 0.1)
        altitude = st.slider("Altitude (m)", 0.0, 120.0, 30.0, 5.0)
        wind_speed_energy = st.slider("Wind Speed (m/s)", 0.0, 20.0, 7.0, 0.5, key="wind_energy")

    with col2:
        st.subheader("Mission Parameters")
        payload = st.slider("Payload (kg)", 0.0, 5.0, 1.5, 0.1)
        home_distance = st.slider("Distance to Home (m)", 0.0, 1000.0, 150.0, 10.0)

    if st.button("🔍 Analyze Energy State"):
        predictor = st.session_state.energy_predictor

        # Predictions
        remaining_time = predictor.predict_remaining_time(
            battery_percent, voltage_sag, altitude, wind_speed_energy, payload, home_distance
        )

        pnr = predictor.predict_point_of_no_return(
            altitude, home_distance, wind_speed_energy, payload, voltage_sag
        )

        is_critical, reason = predictor.is_critical_battery(
            battery_percent, altitude, home_distance, wind_speed_energy, payload, voltage_sag
        )

        # Results
        st.subheader("📈 Prediction Results")

        col_res1, col_res2, col_res3 = st.columns(3)

        with col_res1:
            status_class = "status-critical" if is_critical else "status-good"
            st.markdown(f'<div class="metric-card"><h3>Battery Status</h3>'
                       f'<p class="{status_class}">{"CRITICAL" if is_critical else "SAFE"}</p></div>',
                       unsafe_allow_html=True)

        with col_res2:
            st.markdown(f'<div class="metric-card"><h3>Remaining Time</h3>'
                       f'<p style="font-size: 24px;">{remaining_time:.1f} min</p></div>',
                       unsafe_allow_html=True)

        with col_res3:
            st.markdown(f'<div class="metric-card"><h3>Point-of-No-Return</h3>'
                       f'<p style="font-size: 24px;">{pnr:.1f} %</p></div>',
                       unsafe_allow_html=True)

        st.info(f"**Analysis:** {reason}")

        # Feature importance
        st.subheader("🎯 Feature Contribution Analysis")

        time_importance = predictor.get_feature_importance("time")
        pnr_importance = predictor.get_feature_importance("pnr")

        df_importance = pd.DataFrame({
            'Feature': list(time_importance.keys()),
            'Time Prediction': list(time_importance.values()),
            'PNR Prediction': list(pnr_importance.values())
        })

        fig_comparison = go.Figure()
        fig_comparison.add_trace(go.Bar(
            name='Time Prediction',
            x=df_importance['Feature'],
            y=df_importance['Time Prediction'],
            marker_color='steelblue'
        ))
        fig_comparison.add_trace(go.Bar(
            name='PNR Prediction',
            x=df_importance['Feature'],
            y=df_importance['PNR Prediction'],
            marker_color='orange'
        ))
        fig_comparison.update_layout(
            title="Feature Importance Comparison",
            xaxis_title="Feature",
            yaxis_title="Importance",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig_comparison, use_container_width=True)

        # Comparative benchmark
        st.subheader("📊 Comparative Benchmark")

        # Generate comparison scenarios
        scenarios = [
            {"name": "Current", "battery": battery_percent, "altitude": altitude, "wind": wind_speed_energy},
            {"name": "Low Battery", "battery": 20.0, "altitude": altitude, "wind": wind_speed_energy},
            {"name": "High Altitude", "battery": battery_percent, "altitude": 80.0, "wind": wind_speed_energy},
            {"name": "Strong Wind", "battery": battery_percent, "altitude": altitude, "wind": 15.0},
            {"name": "Ideal", "battery": 80.0, "altitude": 20.0, "wind": 3.0}
        ]

        benchmark_data = []
        for scenario in scenarios:
            time_pred = predictor.predict_remaining_time(
                scenario["battery"], voltage_sag, scenario["altitude"],
                scenario["wind"], payload, home_distance
            )
            pnr_pred = predictor.predict_point_of_no_return(
                scenario["altitude"], home_distance, scenario["wind"], payload, voltage_sag
            )
            benchmark_data.append({
                'Scenario': scenario['name'],
                'Remaining Time (min)': time_pred,
                'PNR Threshold (%)': pnr_pred,
                'Battery (%)': scenario['battery']
            })

        df_benchmark = pd.DataFrame(benchmark_data)

        fig_benchmark = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Remaining Flight Time", "Point-of-No-Return Threshold")
        )

        fig_benchmark.add_trace(
            go.Bar(x=df_benchmark['Scenario'], y=df_benchmark['Remaining Time (min)'],
                  marker_color='steelblue', name='Time'),
            row=1, col=1
        )

        fig_benchmark.add_trace(
            go.Bar(x=df_benchmark['Scenario'], y=df_benchmark['PNR Threshold (%)'],
                  marker_color='orange', name='PNR'),
            row=1, col=2
        )

        fig_benchmark.update_xaxes(tickangle=-45)
        fig_benchmark.update_layout(height=400, showlegend=False)

        st.plotly_chart(fig_benchmark, use_container_width=True)

        # Data table
        st.dataframe(df_benchmark, use_container_width=True)


# Main app
def main():
    """Main Streamlit application."""
    # Header
    st.title("🚁 AutoLandrone Ground Control Station")
    st.markdown("**ML-Powered Autonomous Drone Landing System**")

    # Initialize session state
    init_session_state()

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "🚀 Mission Execution",
        "🎥 Vision Inspector",
        "⚡ Energy Analyzer"
    ])

    with tab1:
        render_tab1_mission_execution()

    with tab2:
        render_tab2_vision_inspector()

    with tab3:
        render_tab3_energy_analyzer()

    # Footer
    st.markdown("---")
    st.markdown("*AutoLandrone GCS Dashboard v1.0 | Powered by Streamlit + Plotly*")


if __name__ == "__main__":
    main()
