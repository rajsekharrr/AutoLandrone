import streamlit as st
from src.telemetry import BatteryTelemetry
from src.obstacle_sensor import ObstacleSensor
from src.landing_controller import LandingController
from src.alert import AlertSystem
from src.logger import DecisionLogger
from src.config import BATTERY_CRITICAL_THRESHOLD, OBSTACLE_SAFE_DISTANCE

st.set_page_config(page_title="AutoLandrone", layout="wide")

st.title("🚁 AutoLandrone Smart Emergency Landing Assistant")
st.markdown("""
**Review 1 Demo** - This software demonstrates intelligent emergency landing decision-making for drones.
The system monitors battery levels and obstacle distances to determine safe landing actions.
""")

st.divider()

scenarios = {
    "1. Normal Operation - Battery Sufficient": {
        "battery": 50.0,
        "distance": 5.0,
        "steps": [
            {"battery": 50.0, "distance": 5.0, "scan": None}
        ]
    },
    "2. Low Battery with Clear Landing Zone": {
        "battery": 15.0,
        "distance": 2.5,
        "steps": [
            {"battery": 15.0, "distance": 2.5, "scan": None}
        ]
    },
    "3. Low Battery with Obstacle Detected": {
        "battery": 15.0,
        "distance": 0.8,
        "steps": [
            {"battery": 15.0, "distance": 0.8, "scan": None}
        ]
    },
    "4. Obstacle Detected, Clear Zone Found After Scan": {
        "battery": 15.0,
        "distance": 0.8,
        "steps": [
            {"battery": 15.0, "distance": 0.8, "scan": None},
            {"battery": 14.5, "distance": 0.8, "scan": "clear_zone_found"}
        ]
    },
    "5. Obstacle Detected, No Clear Zone Found": {
        "battery": 15.0,
        "distance": 0.8,
        "steps": [
            {"battery": 15.0, "distance": 0.8, "scan": None},
            {"battery": 14.5, "distance": 0.8, "scan": "no_clear_zone"}
        ]
    }
}

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
        st.info("No decisions logged yet. Click 'Run Scenario' to start.")
else:
    st.info("Click 'Run Scenario' to see the decision-making process.")

st.divider()

with st.expander("ℹ️ System Configuration"):
    st.write(f"**Battery Critical Threshold:** {BATTERY_CRITICAL_THRESHOLD}%")
    st.write(f"**Obstacle Safe Distance:** {OBSTACLE_SAFE_DISTANCE} meters")
    st.write("**Decision Rules:**")
    st.markdown("""
    - Battery > 20%: Continue monitoring
    - Battery ≤ 20% AND distance ≥ 1.5m: Safe landing
    - Battery ≤ 20% AND distance < 1.5m: Hover and scan
    - Scan finds clear zone: Land at clear zone
    - Scan finds no clear zone: Hold position and alert
    """)
