import streamlit as st
from src.telemetry import BatteryTelemetry
from src.obstacle_sensor import ObstacleSensor
from src.landing_controller import LandingController
from src.alert import AlertSystem
from src.logger import DecisionLogger
from src.config import BATTERY_CRITICAL_THRESHOLD, OBSTACLE_SAFE_DISTANCE
import pandas as pd

st.set_page_config(page_title="AutoLandrone", layout="wide")

st.title("🚁 AutoLandrone Smart Emergency Landing Assistant")
st.markdown("""
**Review 1 Demo with 2D Grid Simulation** - This software demonstrates intelligent emergency landing decision-making for drones.
The system monitors battery levels, detects obstacles, and uses a 2D grid simulation to find the nearest safe landing zone.
""")

st.divider()

# Simulation mode selector
sim_mode = st.radio(
    "Simulation Mode",
    ["Legacy Scenarios", "2D Grid Simulation"],
    horizontal=True,
    help="Legacy: Simple scenarios. Grid: Visual 2D landing zone with obstacles"
)

st.divider()

scenarios = {
    "1. Normal Operation - Battery Sufficient": {
        "battery": 50.0,
        "distance": 5.0,
        "steps": [
            {"battery": 50.0, "distance": 5.0, "scan": None}
        ],
        "obstacles": []
    },
    "2. Low Battery with Clear Landing Zone": {
        "battery": 15.0,
        "distance": 2.5,
        "steps": [
            {"battery": 15.0, "distance": 2.5, "scan": None}
        ],
        "obstacles": []
    },
    "3. Low Battery with Obstacle Detected": {
        "battery": 15.0,
        "distance": 0.8,
        "steps": [
            {"battery": 15.0, "distance": 0.8, "scan": None}
        ],
        "obstacles": []
    },
    "4. Obstacle Detected, Clear Zone Found After Scan": {
        "battery": 15.0,
        "distance": 0.8,
        "steps": [
            {"battery": 15.0, "distance": 0.8, "scan": None},
            {"battery": 14.5, "distance": 0.8, "scan": "clear_zone_found"}
        ],
        "obstacles": []
    },
    "5. Obstacle Detected, No Clear Zone Found": {
        "battery": 15.0,
        "distance": 0.8,
        "steps": [
            {"battery": 15.0, "distance": 0.8, "scan": None},
            {"battery": 14.5, "distance": 0.8, "scan": "no_clear_zone"}
        ],
        "obstacles": []
    }
}

# Grid simulation scenarios
grid_scenarios = {
    "1. Grid: Normal Operation": {
        "battery": 50.0,
        "distance": 5.0,
        "obstacles": []
    },
    "2. Grid: Low Battery, Clear Zone": {
        "battery": 15.0,
        "distance": 2.5,
        "obstacles": []
    },
    "3. Grid: Obstacle Below, Safe Cell Found": {
        "battery": 15.0,
        "distance": 0.8,
        "obstacles": [(1, 1), (5, 5)]  # Some obstacles but not blocking all
    },
    "4. Grid: Obstacle Below, Nearest Safe Cell Selected": {
        "battery": 15.0,
        "distance": 0.8,
        "obstacles": [(2, 3), (3, 2), (4, 3)]  # Block some adjacent cells
    },
    "5. Grid: All Cells Blocked - Hold Alert": {
        "battery": 15.0,
        "distance": 0.8,
        "obstacles": [(row, col) for row in range(1, 6) for col in range(1, 6) if (row, col) != (3, 3)]
    },
    "6. Grid: Partial Blockage - Find Opening": {
        "battery": 15.0,
        "distance": 0.8,
        "obstacles": [(2, 2), (2, 3), (2, 4), (3, 2), (4, 2), (4, 3), (4, 4)]  # 3 sides blocked
    }
}

if sim_mode == "Legacy Scenarios":
    # Legacy scenario mode
    scenario_name = st.selectbox("Select Scenario", list(scenarios.keys()))
    scenario = scenarios[scenario_name]

    if "logger" not in st.session_state or st.session_state.get("last_scenario") != scenario_name:
        st.session_state.logger = DecisionLogger()
        st.session_state.last_scenario = scenario_name
        st.session_state.processed = False

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Current Telemetry")
        battery = scenario["steps"][-1]["battery"]
        distance = scenario["steps"][-1]["distance"]

        st.metric("Battery Percentage", f"{battery}%",
                  delta=None if battery > BATTERY_CRITICAL_THRESHOLD else f"{battery - BATTERY_CRITICAL_THRESHOLD}% (Critical)")
        st.metric("Obstacle Distance", f"{distance} m",
                  delta=None if distance >= OBSTACLE_SAFE_DISTANCE else f"{distance - OBSTACLE_SAFE_DISTANCE:.1f}m (Unsafe)")

    with col2:
        st.subheader("🎯 System Status")
        if st.button("Run Scenario", type="primary"):
            st.session_state.logger.clear()
            controller = LandingController()
            alert_system = AlertSystem()

            for idx, step in enumerate(scenario["steps"], 1):
                state, action, reason = controller.process_telemetry(
                    step["battery"],
                    step["distance"],
                    step["scan"]
                )

                st.session_state.logger.log_decision(
                    idx,
                    step["battery"],
                    step["distance"],
                    state,
                    action,
                    reason,
                    step["scan"]
                )

            st.session_state.processed = True
            st.rerun()

else:
    # Grid simulation mode
    scenario_name = st.selectbox("Select Grid Scenario", list(grid_scenarios.keys()))
    scenario = grid_scenarios[scenario_name]

    if "logger" not in st.session_state or st.session_state.get("last_scenario") != scenario_name:
        st.session_state.logger = DecisionLogger()
        st.session_state.last_scenario = scenario_name
        st.session_state.processed = False
        st.session_state.grid_state = None

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Current Telemetry")
        battery = scenario["battery"]
        distance = scenario["distance"]

        st.metric("Battery Percentage", f"{battery}%",
                  delta=None if battery > BATTERY_CRITICAL_THRESHOLD else f"{battery - BATTERY_CRITICAL_THRESHOLD}% (Critical)")
        st.metric("Obstacle Distance", f"{distance} m",
                  delta=None if distance >= OBSTACLE_SAFE_DISTANCE else f"{distance - OBSTACLE_SAFE_DISTANCE:.1f}m (Unsafe)")

    with col2:
        st.subheader("🎯 System Status")
        if st.button("Run Grid Simulation", type="primary"):
            st.session_state.logger.clear()

            # Create controller with grid simulation enabled
            controller = LandingController(use_grid_simulation=True, grid_size=7)
            controller.set_grid_obstacles(scenario["obstacles"])

            state, action, reason = controller.process_telemetry(
                battery,
                distance,
                scan_result=None
            )

            st.session_state.logger.log_decision(
                1,
                battery,
                distance,
                state,
                action,
                reason,
                None
            )

            # Store grid state for visualization
            st.session_state.grid_state = controller.get_grid_state()
            st.session_state.processed = True
            st.rerun()

    # Display grid visualization
    if st.session_state.get("grid_state"):
        st.divider()
        st.subheader("🗺️ 2D Landing Zone Grid")

        grid_state = st.session_state.grid_state
        grid = grid_state['grid']
        drone_pos = grid_state['drone_position']
        scanned = set(grid_state['scanned_cells'])
        nearest = grid_state['nearest_safe_cell']

        # Create visual grid
        grid_html = "<div style='font-family: monospace; font-size: 20px; line-height: 1.5;'>"
        grid_html += "<style>.grid-cell { display: inline-block; width: 40px; height: 40px; text-align: center; line-height: 40px; margin: 2px; border-radius: 5px; }</style>"

        legend_col1, legend_col2, legend_col3, legend_col4, legend_col5 = st.columns(5)
        with legend_col1:
            st.markdown("🚁 **Drone**")
        with legend_col2:
            st.markdown("❌ **Obstacle**")
        with legend_col3:
            st.markdown("🔍 **Scanned**")
        with legend_col4:
            st.markdown("⭐ **Safe Landing**")
        with legend_col5:
            st.markdown("⬜ **Empty**")

        for row in range(grid_state['grid_size']):
            for col in range(grid_state['grid_size']):
                if (row, col) == drone_pos:
                    grid_html += "<span class='grid-cell' style='background-color: #4CAF50; color: white;'>🚁</span>"
                elif (row, col) == nearest:
                    grid_html += "<span class='grid-cell' style='background-color: #FFC107; color: white;'>⭐</span>"
                elif grid[row][col] == 'obstacle':
                    grid_html += "<span class='grid-cell' style='background-color: #F44336; color: white;'>❌</span>"
                elif (row, col) in scanned:
                    grid_html += "<span class='grid-cell' style='background-color: #2196F3; color: white;'>🔍</span>"
                else:
                    grid_html += "<span class='grid-cell' style='background-color: #E0E0E0;'>⬜</span>"
            grid_html += "<br>"

        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

        # Grid statistics
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("Drone Position", f"({drone_pos[0]}, {drone_pos[1]})")
        with stat_col2:
            st.metric("Cells Scanned", len(scanned))
        with stat_col3:
            if nearest:
                st.metric("Nearest Safe Cell", f"({nearest[0]}, {nearest[1]})")
            else:
                st.metric("Nearest Safe Cell", "None Found", delta="❌ Critical")

if st.session_state.processed:
    df = st.session_state.logger.get_dataframe()
    if not df.empty:
        last_row = df.iloc[-1]

        state_col, action_col = st.columns(2)
        with state_col:
            st.success(f"**Current State:** {last_row['State']}")
        with action_col:
            st.info(f"**Selected Action:** {last_row['Action']}")

        alert_system = AlertSystem()
        alert_msg = alert_system.generate_alert(last_row['Action'])
        if alert_msg:
            st.warning(alert_msg)

st.divider()

st.subheader("📋 Decision Log")

if st.session_state.processed:
    df = st.session_state.logger.get_dataframe()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No decisions logged yet. Click 'Run Scenario' or 'Run Grid Simulation' to start.")
else:
    st.info("Click 'Run Scenario' or 'Run Grid Simulation' to see the decision-making process.")

st.divider()

with st.expander("ℹ️ System Configuration"):
    st.write(f"**Battery Critical Threshold:** {BATTERY_CRITICAL_THRESHOLD}%")
    st.write(f"**Obstacle Safe Distance:** {OBSTACLE_SAFE_DISTANCE} meters")
    st.write(f"**Grid Size:** 7x7 cells")
    st.write(f"**Scan Radius:** 2 cells in each direction")
    st.write("**Decision Rules:**")
    st.markdown("""
    - Battery > 20%: Continue monitoring
    - Battery ≤ 20% AND distance ≥ 1.5m: Safe landing
    - Battery ≤ 20% AND distance < 1.5m: Hover and scan nearby cells
    - Scan finds safe cell: Land at nearest safe cell
    - Scan finds no safe cell: Hold position and alert

    **Grid Simulation Features:**
    - 2D deterministic grid representation of landing zone
    - Real-time obstacle detection and visualization
    - Nearest safe cell selection using Euclidean distance
    - Visual display of drone position, obstacles, scanned cells, and landing zone
    """)
