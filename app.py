import streamlit as st
from src.landing_controller import LandingController
from src.alert import AlertSystem
from src.logger import DecisionLogger
from src.config import BATTERY_CRITICAL_THRESHOLD, OBSTACLE_SAFE_DISTANCE

st.set_page_config(page_title="AutoLandrone - Emergency Landing System", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for presentation-ready styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .status-safe {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .status-warning {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .status-danger {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .step-box {
        background: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .step-active {
        border-color: #007bff;
        background: #e7f3ff;
        font-weight: bold;
    }
    .step-complete {
        border-color: #28a745;
        background: #d4edda;
    }
    .grid-cell {
        display: inline-block;
        width: 45px;
        height: 45px;
        text-align: center;
        line-height: 45px;
        margin: 3px;
        border-radius: 8px;
        font-size: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🚁 AutoLandrone: Smart Emergency Landing Assistant</h1>
    <p style="font-size: 1.1rem; margin-top: 1rem;">
        <strong>Review 1 Demonstration</strong> - Software Prototype for Safe Drone Emergency Landing
    </p>
</div>
""", unsafe_allow_html=True)

# Project Context Banner
st.info("""
📘 **About This Demo**: This is a **software simulation** demonstrating the emergency landing decision logic.
The system monitors battery levels and obstacle distances to intelligently select safe landing zones.
**Hardware integration** (Pixhawk autopilot, ultrasonic sensors) is planned for future phases after validating the software logic.
""")

st.divider()

# Simplified scenario selection
st.subheader("🎯 Select Demonstration Scenario")

scenarios = {
    "1. ✅ Normal Monitoring (Battery OK)": {
        "battery": 50.0,
        "distance": 5.0,
        "obstacles": [],
        "description": "Normal operation with sufficient battery"
    },
    "2. 🟢 Low Battery - Clear Area (Direct Landing)": {
        "battery": 15.0,
        "distance": 2.5,
        "obstacles": [],
        "description": "Critical battery but landing zone is clear"
    },
    "3. 🟡 Obstacle Detected - Safe Location Found": {
        "battery": 15.0,
        "distance": 0.8,
        "obstacles": [(2, 3), (3, 2), (4, 3)],
        "description": "Obstacle below, system finds nearest safe landing cell"
    },
    "4. 🔴 Obstacle Detected - No Safe Location": {
        "battery": 15.0,
        "distance": 0.8,
        "obstacles": [(row, col) for row in range(1, 6) for col in range(1, 6) if (row, col) != (3, 3)],
        "description": "All nearby cells blocked, system holds position and alerts"
    },
    "5. 🟢 Direct Safe Landing (No Scan Needed)": {
        "battery": 15.0,
        "distance": 1.8,
        "obstacles": [],
        "description": "Critical battery with safe distance for immediate landing"
    }
}

scenario_name = st.selectbox(
    "Choose a scenario to demonstrate:",
    list(scenarios.keys()),
    help="Each scenario demonstrates different emergency landing behaviors"
)
scenario = scenarios[scenario_name]

# Display scenario description
st.markdown(f"**Scenario Description:** {scenario['description']}")

# Initialize session state
if "logger" not in st.session_state or st.session_state.get("last_scenario") != scenario_name:
    st.session_state.logger = DecisionLogger()
    st.session_state.last_scenario = scenario_name
    st.session_state.processed = False
    st.session_state.grid_state = None
    st.session_state.final_state = None
    st.session_state.final_action = None
    st.session_state.final_reason = None

st.divider()

# Two-column layout for telemetry and run button
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Current Telemetry & Status")

    battery = scenario["battery"]
    distance = scenario["distance"]

    # Battery status with color coding
    battery_status = "🟢 NORMAL" if battery > BATTERY_CRITICAL_THRESHOLD else "🔴 CRITICAL"
    battery_color = "status-safe" if battery > BATTERY_CRITICAL_THRESHOLD else "status-danger"

    st.markdown(f"""
    <div class="{battery_color}">
        <h3 style="margin: 0;">🔋 Battery: {battery}% - {battery_status}</h3>
        <p style="margin: 0.5rem 0 0 0;">Critical Threshold: {BATTERY_CRITICAL_THRESHOLD}%</p>
    </div>
    """, unsafe_allow_html=True)

    # Obstacle status with color coding
    obstacle_status = "🟢 SAFE" if distance >= OBSTACLE_SAFE_DISTANCE else "🔴 UNSAFE"
    obstacle_color = "status-safe" if distance >= OBSTACLE_SAFE_DISTANCE else "status-danger"

    st.markdown(f"""
    <div class="{obstacle_color}">
        <h3 style="margin: 0;">📏 Obstacle Distance: {distance}m - {obstacle_status}</h3>
        <p style="margin: 0.5rem 0 0 0;">Safe Distance Threshold: {OBSTACLE_SAFE_DISTANCE}m</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.subheader("🎬 Run Simulation")
    st.write("")  # Spacing
    st.write("")  # Spacing
    if st.button("▶️ RUN SCENARIO", type="primary", use_container_width=True):
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

        # Store results
        st.session_state.grid_state = controller.get_grid_state()
        st.session_state.final_state = state
        st.session_state.final_action = action
        st.session_state.final_reason = reason
        st.session_state.processed = True
        st.rerun()

# Show results if processed
if st.session_state.processed:
    st.divider()

    # Step-by-step process visualization
    st.subheader("🔄 Decision Process Flow")

    battery = scenario["battery"]
    distance = scenario["distance"]

    # Determine which steps are active
    is_critical = battery <= BATTERY_CRITICAL_THRESHOLD
    has_obstacle = distance < OBSTACLE_SAFE_DISTANCE
    needs_scan = is_critical and has_obstacle

    step_cols = st.columns(5)

    with step_cols[0]:
        step_class = "step-complete" if is_critical else "step-active"
        st.markdown(f"""
        <div class="step-box {step_class}">
            <div style="font-size: 2rem;">🔋</div>
            <div><strong>1. Battery Check</strong></div>
            <div style="font-size: 0.9rem;">{'✓ Critical' if is_critical else 'Normal'}</div>
        </div>
        """, unsafe_allow_html=True)

    with step_cols[1]:
        step_class = "step-complete" if is_critical else "step-box"
        st.markdown(f"""
        <div class="step-box {step_class}">
            <div style="font-size: 2rem;">📏</div>
            <div><strong>2. Obstacle Check</strong></div>
            <div style="font-size: 0.9rem;">{'✓ Detected' if has_obstacle else 'Clear'}</div>
        </div>
        """, unsafe_allow_html=True)

    with step_cols[2]:
        step_class = "step-complete" if needs_scan else "step-box"
        st.markdown(f"""
        <div class="step-box {step_class}">
            <div style="font-size: 2rem;">🚁</div>
            <div><strong>3. Hover & Scan</strong></div>
            <div style="font-size: 0.9rem;">{'✓ Scanning' if needs_scan else 'Skipped'}</div>
        </div>
        """, unsafe_allow_html=True)

    with step_cols[3]:
        has_safe_cell = st.session_state.grid_state and st.session_state.grid_state['nearest_safe_cell'] is not None
        step_class = "step-complete" if (needs_scan and has_safe_cell) else "step-box"
        st.markdown(f"""
        <div class="step-box {step_class}">
            <div style="font-size: 2rem;">🔍</div>
            <div><strong>4. Find Safe Cell</strong></div>
            <div style="font-size: 0.9rem;">{'✓ Found' if has_safe_cell else ('No safe cell' if needs_scan else 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    with step_cols[4]:
        step_class = "step-complete step-active"
        action_emoji = "🛬" if "LAND" in st.session_state.final_action else "⏸️"
        st.markdown(f"""
        <div class="step-box {step_class}">
            <div style="font-size: 2rem;">{action_emoji}</div>
            <div><strong>5. Final Action</strong></div>
            <div style="font-size: 0.9rem;">{'Land' if "LAND" in st.session_state.final_action else 'Hold'}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Decision result display
    st.subheader("✅ Decision Result")

    result_col1, result_col2 = st.columns(2)

    with result_col1:
        state_color = "status-safe"
        if st.session_state.final_state == "HOLD_AND_ALERT":
            state_color = "status-danger"
        elif st.session_state.final_state == "HOVERING":
            state_color = "status-warning"

        st.markdown(f"""
        <div class="{state_color}">
            <h3 style="margin: 0;">🎯 System State</h3>
            <h2 style="margin: 0.5rem 0;">{st.session_state.final_state}</h2>
        </div>
        """, unsafe_allow_html=True)

    with result_col2:
        action_color = "status-safe"
        if "ALERT" in st.session_state.final_action:
            action_color = "status-danger"
        elif "OBSTACLE" in st.session_state.final_action:
            action_color = "status-warning"

        st.markdown(f"""
        <div class="{action_color}">
            <h3 style="margin: 0;">⚙️ Selected Action</h3>
            <h2 style="margin: 0.5rem 0;">{st.session_state.final_action.replace('_', ' ')}</h2>
        </div>
        """, unsafe_allow_html=True)

    # Decision explanation
    st.markdown(f"""
    <div class="status-warning">
        <h4 style="margin: 0;">📝 Decision Explanation</h4>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">{st.session_state.final_reason}</p>
    </div>
    """, unsafe_allow_html=True)

    # Alert message if critical
    alert_system = AlertSystem()
    alert_msg = alert_system.generate_alert(st.session_state.final_action)
    if alert_msg:
        st.error(f"🚨 **ALERT:** {alert_msg}")

    # Grid visualization
    if st.session_state.grid_state:
        st.divider()
        st.subheader("🗺️ Visual Landing Zone Grid (7×7)")

        grid_state = st.session_state.grid_state
        grid = grid_state['grid']
        drone_pos = grid_state['drone_position']
        scanned = set(grid_state['scanned_cells'])
        nearest = grid_state['nearest_safe_cell']

        # Legend
        legend_cols = st.columns(5)
        with legend_cols[0]:
            st.markdown("🚁 **Drone Position**")
        with legend_cols[1]:
            st.markdown("❌ **Obstacle**")
        with legend_cols[2]:
            st.markdown("🔍 **Scanned Cell**")
        with legend_cols[3]:
            st.markdown("⭐ **Safe Landing Zone**")
        with legend_cols[4]:
            st.markdown("⬜ **Empty Cell**")

        st.write("")  # Spacing

        # Grid display
        grid_html = "<div style='text-align: center;'>"
        for row in range(grid_state['grid_size']):
            for col in range(grid_state['grid_size']):
                if (row, col) == drone_pos:
                    grid_html += "<span class='grid-cell' style='background-color: #28a745; color: white;'>🚁</span>"
                elif (row, col) == nearest:
                    grid_html += "<span class='grid-cell' style='background-color: #ffc107; color: white;'>⭐</span>"
                elif grid[row][col] == 'obstacle':
                    grid_html += "<span class='grid-cell' style='background-color: #dc3545; color: white;'>❌</span>"
                elif (row, col) in scanned:
                    grid_html += "<span class='grid-cell' style='background-color: #007bff; color: white;'>🔍</span>"
                else:
                    grid_html += "<span class='grid-cell' style='background-color: #e9ecef; color: #6c757d;'>⬜</span>"
            grid_html += "<br>"
        grid_html += "</div>"

        st.markdown(grid_html, unsafe_allow_html=True)

        st.write("")  # Spacing

        # Grid statistics
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("🚁 Drone Position (Grid Coordinates)", f"({drone_pos[0]}, {drone_pos[1]})")
        with stat_col2:
            st.metric("🔍 Cells Scanned (within radius 2)", f"{len(scanned)} cells")
        with stat_col3:
            if nearest:
                st.metric("⭐ Nearest Safe Landing Cell", f"({nearest[0]}, {nearest[1]})")
            else:
                st.metric("⭐ Nearest Safe Landing Cell", "None Available", delta="🔴 Critical")

    st.divider()

    # Decision log table
    with st.expander("📋 View Detailed Decision Log", expanded=False):
        df = st.session_state.logger.get_dataframe()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# System configuration
with st.expander("⚙️ System Configuration & Technical Details"):
    config_col1, config_col2 = st.columns(2)

    with config_col1:
        st.markdown("### 🔧 Operating Parameters")
        st.write(f"**Battery Critical Threshold:** {BATTERY_CRITICAL_THRESHOLD}%")
        st.write(f"**Obstacle Safe Distance:** {OBSTACLE_SAFE_DISTANCE} meters")
        st.write(f"**Grid Size:** 7×7 cells (49 total)")
        st.write(f"**Scan Radius:** 2 cells in each direction")
        st.write(f"**Distance Algorithm:** Euclidean distance")

    with config_col2:
        st.markdown("### 📐 Decision Rules")
        st.markdown("""
        1. **Battery > 20%** → Continue monitoring
        2. **Battery ≤ 20% AND distance ≥ 1.5m** → Safe landing
        3. **Battery ≤ 20% AND distance < 1.5m** → Hover and scan
        4. **Safe cell found** → Land at nearest safe cell
        5. **No safe cell** → Hold position and alert operator
        """)

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <p><strong>AutoLandrone</strong> - Smart Emergency Landing Assistant | SDG 9: Industry, Innovation and Infrastructure</p>
    <p style="font-size: 0.9rem;">Review 1 Software Prototype | Hardware integration planned for future phases</p>
</div>
""", unsafe_allow_html=True)
