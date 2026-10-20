import streamlit as st
import time
import pandas as pd
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
        st.session_state.processed = False
        st.session_state.animation_complete = False
        st.rerun()

# Run animation if button was clicked
if "animation_complete" in st.session_state and not st.session_state.animation_complete and not st.session_state.processed:
    st.divider()
    st.subheader("🎬 Simulation in Progress...")

    # Create placeholders for animation
    status_placeholder = st.empty()
    chart_placeholder = st.empty()
    grid_placeholder = st.empty()
    metrics_placeholder = st.empty()

    # Initialize simulation data
    simulation_steps = []
    battery = scenario["battery"]
    distance = scenario["distance"]
    is_critical = battery <= BATTERY_CRITICAL_THRESHOLD
    has_obstacle = distance < OBSTACLE_SAFE_DISTANCE
    needs_scan = is_critical and has_obstacle

    # Step 1: Battery Check
    status_placeholder.info("**Step 1/5:** 🔋 Checking battery level...")
    simulation_steps.append({"Step": "Start", "Battery %": battery, "Status": "Monitoring"})
    chart_placeholder.line_chart(pd.DataFrame(simulation_steps).set_index("Step"))
    time.sleep(0.6)

    simulation_steps.append({"Step": "Battery Check", "Battery %": battery, "Status": "Critical" if is_critical else "Normal"})
    chart_placeholder.line_chart(pd.DataFrame(simulation_steps).set_index("Step"))

    if is_critical:
        status_placeholder.warning(f"**Step 1/5:** 🔋 Battery at {battery}% - CRITICAL!")
    else:
        status_placeholder.success(f"**Step 1/5:** 🔋 Battery at {battery}% - Normal")
    time.sleep(0.6)

    # Step 2: Obstacle Detection
    status_placeholder.info("**Step 2/5:** 📏 Detecting obstacles below drone...")
    time.sleep(0.6)

    simulation_steps.append({"Step": "Obstacle Check", "Battery %": battery, "Status": "Obstacle" if has_obstacle else "Clear"})
    chart_placeholder.line_chart(pd.DataFrame(simulation_steps).set_index("Step"))

    if has_obstacle:
        status_placeholder.warning(f"**Step 2/5:** 📏 Obstacle detected at {distance}m - UNSAFE!")
    else:
        status_placeholder.success(f"**Step 2/5:** 📏 Distance {distance}m - Clear for landing")
    time.sleep(0.6)

    # Create controller with grid simulation enabled
    controller = LandingController(use_grid_simulation=True, grid_size=7)
    controller.set_grid_obstacles(scenario["obstacles"])

    # Step 3: Hover and Scan (if needed)
    if needs_scan:
        status_placeholder.info("**Step 3/5:** 🚁 Hovering and initiating grid scan...")
        simulation_steps.append({"Step": "Hovering", "Battery %": battery - 0.5, "Status": "Scanning"})
        chart_placeholder.line_chart(pd.DataFrame(simulation_steps).set_index("Step"))
        time.sleep(0.7)

        # Get grid state for visualization
        grid_state_temp = controller.get_grid_state()
        grid = grid_state_temp['grid']
        drone_pos = grid_state_temp['drone_position']
        grid_size = grid_state_temp['grid_size']

        # Show initial grid
        status_placeholder.info("**Step 4/5:** 🔍 Scanning nearby cells...")

        # Calculate cells to scan
        scan_radius = 2
        cells_to_scan = []
        for row in range(max(0, drone_pos[0] - scan_radius), min(grid_size, drone_pos[0] + scan_radius + 1)):
            for col in range(max(0, drone_pos[1] - scan_radius), min(grid_size, drone_pos[1] + scan_radius + 1)):
                if (row, col) != drone_pos:
                    cells_to_scan.append((row, col))

        # Animate scanning process
        scanned_cells = set()
        safe_cells = []
        blocked_cells = []

        for idx, cell in enumerate(cells_to_scan):
            scanned_cells.add(cell)

            # Check if cell is safe or blocked
            if grid[cell[0]][cell[1]] == 'obstacle':
                blocked_cells.append(cell)
            else:
                safe_cells.append(cell)

            # Update grid visualization every few cells for performance
            if idx % 4 == 0 or idx == len(cells_to_scan) - 1:
                grid_html = "<div style='text-align: center;'>"
                for row in range(grid_size):
                    for col in range(grid_size):
                        if (row, col) == drone_pos:
                            grid_html += "<span class='grid-cell' style='background-color: #28a745; color: white;'>🚁</span>"
                        elif grid[row][col] == 'obstacle':
                            grid_html += "<span class='grid-cell' style='background-color: #dc3545; color: white;'>❌</span>"
                        elif (row, col) in scanned_cells:
                            grid_html += "<span class='grid-cell' style='background-color: #007bff; color: white;'>🔍</span>"
                        else:
                            grid_html += "<span class='grid-cell' style='background-color: #e9ecef; color: #6c757d;'>⬜</span>"
                    grid_html += "<br>"
                grid_html += "</div>"

                grid_placeholder.markdown(grid_html, unsafe_allow_html=True)

                # Update metrics
                with metrics_placeholder.container():
                    met_col1, met_col2, met_col3 = st.columns(3)
                    with met_col1:
                        st.metric("🔍 Cells Scanned", f"{len(scanned_cells)}/{len(cells_to_scan)}")
                    with met_col2:
                        st.metric("✅ Safe Cells Found", len(safe_cells))
                    with met_col3:
                        st.metric("❌ Blocked Cells", len(blocked_cells))

                time.sleep(0.15)

        # Process and find nearest safe cell
        state, action, reason = controller.process_telemetry(battery, distance, scan_result=None)
        grid_state = controller.get_grid_state()
        nearest = grid_state['nearest_safe_cell']

        simulation_steps.append({"Step": "Scan Complete", "Battery %": battery - 1.0, "Status": "Analyzed"})
        chart_placeholder.line_chart(pd.DataFrame(simulation_steps).set_index("Step"))

        if nearest:
            status_placeholder.success(f"**Step 4/5:** ✅ Safe landing cell found at ({nearest[0]}, {nearest[1]})!")

            # Show final grid with selected cell
            grid_html = "<div style='text-align: center;'>"
            for row in range(grid_size):
                for col in range(grid_size):
                    if (row, col) == drone_pos:
                        grid_html += "<span class='grid-cell' style='background-color: #28a745; color: white;'>🚁</span>"
                    elif (row, col) == nearest:
                        grid_html += "<span class='grid-cell' style='background-color: #ffc107; color: white;'>⭐</span>"
                    elif grid[row][col] == 'obstacle':
                        grid_html += "<span class='grid-cell' style='background-color: #dc3545; color: white;'>❌</span>"
                    elif (row, col) in scanned_cells:
                        grid_html += "<span class='grid-cell' style='background-color: #007bff; color: white;'>🔍</span>"
                    else:
                        grid_html += "<span class='grid-cell' style='background-color: #e9ecef; color: #6c757d;'>⬜</span>"
                grid_html += "<br>"
            grid_html += "</div>"
            grid_placeholder.markdown(grid_html, unsafe_allow_html=True)
        else:
            status_placeholder.error("**Step 4/5:** ⚠️ No safe landing cell available - all cells blocked!")

        time.sleep(0.8)

    else:
        # No scan needed
        status_placeholder.info("**Step 3/5:** 🚁 Hover & Scan - SKIPPED (not needed)")
        time.sleep(0.5)
        status_placeholder.info("**Step 4/5:** 🔍 Find Safe Cell - SKIPPED (not needed)")
        time.sleep(0.5)

        # Process without scanning
        state, action, reason = controller.process_telemetry(battery, distance, scan_result=None)
        grid_state = controller.get_grid_state()

    # Step 5: Final Action
    simulation_steps.append({"Step": "Decision", "Battery %": battery - 1.5, "Status": "Complete"})
    chart_placeholder.line_chart(pd.DataFrame(simulation_steps).set_index("Step"))

    if "LAND" in action:
        status_placeholder.success(f"**Step 5/5:** 🛬 Executing landing procedure - {action.replace('_', ' ')}")
    else:
        status_placeholder.error(f"**Step 5/5:** ⏸️ Holding position - {action.replace('_', ' ')}")

    time.sleep(0.8)

    # Store results and complete animation
    st.session_state.logger.log_decision(1, battery, distance, state, action, reason, None)
    st.session_state.grid_state = grid_state
    st.session_state.final_state = state
    st.session_state.final_action = action
    st.session_state.final_reason = reason
    st.session_state.animation_complete = True
    st.session_state.processed = True

    status_placeholder.success("✅ **Simulation Complete!** - Scroll down for detailed results")
    time.sleep(1.5)
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

        # Calculate scan summary statistics
        total_scanned = len(scanned)
        safe_count = 0
        blocked_count = 0

        for cell in scanned:
            if grid[cell[0]][cell[1]] == 'obstacle':
                blocked_count += 1
            else:
                safe_count += 1

        # Scan Summary Box (only if scanning occurred)
        if total_scanned > 0:
            scan_summary_col1, scan_summary_col2, scan_summary_col3, scan_summary_col4 = st.columns(4)

            with scan_summary_col1:
                st.markdown("""
                <div class="status-safe" style="text-align: center;">
                    <h3 style="margin: 0;">📊 Scan Summary</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;"><strong>{}</strong> cells scanned</p>
                </div>
                """.format(total_scanned), unsafe_allow_html=True)

            with scan_summary_col2:
                st.markdown("""
                <div class="status-safe" style="text-align: center;">
                    <h3 style="margin: 0;">✅ Safe Cells</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;"><strong>{}</strong> available</p>
                </div>
                """.format(safe_count), unsafe_allow_html=True)

            with scan_summary_col3:
                st.markdown("""
                <div class="status-danger" style="text-align: center;">
                    <h3 style="margin: 0;">❌ Blocked</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;"><strong>{}</strong> obstacles</p>
                </div>
                """.format(blocked_count), unsafe_allow_html=True)

            with scan_summary_col4:
                success_rate = (safe_count / total_scanned * 100) if total_scanned > 0 else 0
                st.markdown("""
                <div class="status-warning" style="text-align: center;">
                    <h3 style="margin: 0;">📈 Success Rate</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;"><strong>{:.1f}%</strong> safe</p>
                </div>
                """.format(success_rate), unsafe_allow_html=True)

            st.write("")  # Spacing

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

        # Detailed Grid Metrics
        st.markdown("### 📍 Grid Details")
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        with detail_col1:
            st.metric("🚁 Drone Position (Grid Coordinates)", f"({drone_pos[0]}, {drone_pos[1]})")
        with detail_col2:
            if nearest:
                st.metric("⭐ Selected Landing Cell", f"({nearest[0]}, {nearest[1]})")
                # Calculate distance
                if nearest:
                    distance_to_landing = ((nearest[0] - drone_pos[0])**2 + (nearest[1] - drone_pos[1])**2)**0.5
                    st.caption(f"Distance: {distance_to_landing:.2f} cells")
            else:
                st.metric("⭐ Selected Landing Cell", "None Available", delta="🔴 Critical")
        with detail_col3:
            st.metric("🔍 Total Cells Scanned", f"{len(scanned)} cells" if len(scanned) > 0 else "No scan performed")
            if len(scanned) > 0:
                st.caption(f"Scan radius: 2 cells")

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
