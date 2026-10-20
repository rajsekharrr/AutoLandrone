import pytest
from src.decision_engine import DecisionEngine
from src.config import DroneState, DroneAction

@pytest.fixture
def engine():
    return DecisionEngine()

def test_normal_battery_monitoring(engine):
    state, action, reason = engine.evaluate(50.0, 5.0)
    assert state == DroneState.MONITORING
    assert action == DroneAction.CONTINUE_MONITORING

def test_critical_battery_clear_landing(engine):
    state, action, reason = engine.evaluate(15.0, 2.5)
    assert state == DroneState.LANDING
    assert action == DroneAction.SAFE_LANDING

def test_critical_battery_obstacle_detected(engine):
    state, action, reason = engine.evaluate(15.0, 0.8)
    assert state == DroneState.HOVERING
    assert action == DroneAction.OBSTACLE_DETECTED_ALERT

def test_scan_clear_zone_found(engine):
    state, action, reason = engine.evaluate(15.0, 0.8, scan_result="clear_zone_found")
    assert state == DroneState.LANDING
    assert action == DroneAction.LAND_AT_CLEAR_ZONE

def test_scan_no_clear_zone(engine):
    state, action, reason = engine.evaluate(15.0, 0.8, scan_result="no_clear_zone")
    assert state == DroneState.HOLD_AND_ALERT
    assert action == DroneAction.HOLD_POSITION_ALERT

def test_battery_exactly_at_threshold(engine):
    state, action, reason = engine.evaluate(20.0, 2.0)
    assert state == DroneState.LANDING
    assert action == DroneAction.SAFE_LANDING

def test_distance_exactly_at_threshold(engine):
    state, action, reason = engine.evaluate(15.0, 1.5)
    assert state == DroneState.LANDING
    assert action == DroneAction.SAFE_LANDING
