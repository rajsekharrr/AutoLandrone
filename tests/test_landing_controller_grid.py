import pytest
from src.landing_controller import LandingController
from src.config import DroneState, DroneAction

@pytest.fixture
def controller_with_grid():
    """Create a landing controller with grid simulation enabled."""
    return LandingController(use_grid_simulation=True, grid_size=7)

@pytest.fixture
def controller_without_grid():
    """Create a landing controller without grid simulation."""
    return LandingController(use_grid_simulation=False)

def test_controller_grid_initialization(controller_with_grid):
    """Test that controller initializes grid correctly."""
    assert controller_with_grid.use_grid_simulation is True
    assert controller_with_grid.grid is not None
    assert controller_with_grid.grid.grid_size == 7

def test_controller_without_grid_initialization(controller_without_grid):
    """Test that controller works without grid."""
    assert controller_without_grid.use_grid_simulation is False
    assert controller_without_grid.grid is None

def test_normal_operation_with_grid(controller_with_grid):
    """Test normal monitoring when battery is sufficient."""
    state, action, reason = controller_with_grid.process_telemetry(50.0, 5.0)

    assert state == DroneState.MONITORING
    assert action == DroneAction.CONTINUE_MONITORING

def test_critical_battery_clear_zone_with_grid(controller_with_grid):
    """Test landing when battery critical but zone is clear."""
    state, action, reason = controller_with_grid.process_telemetry(15.0, 2.5)

    assert state == DroneState.LANDING
    assert action == DroneAction.SAFE_LANDING

def test_critical_battery_obstacle_finds_safe_cell(controller_with_grid):
    """Test that grid scan finds a safe landing cell when obstacle detected."""
    # Don't set any obstacles - all cells are safe
    state, action, reason = controller_with_grid.process_telemetry(15.0, 0.8)

    # First call should trigger hover/scan
    # The grid should find a safe cell
    assert state == DroneState.LANDING
    assert action == DroneAction.LAND_AT_CLEAR_ZONE
    assert "grid cell" in reason

def test_critical_battery_all_cells_blocked(controller_with_grid):
    """Test hold and alert when all nearby cells are blocked."""
    # Block all cells around drone (3,3) within radius 2
    obstacles = []
    for row in range(1, 6):
        for col in range(1, 6):
            if (row, col) != (3, 3):  # Don't block drone position
                obstacles.append((row, col))

    controller_with_grid.set_grid_obstacles(obstacles)

    # Now process telemetry with critical battery and obstacle
    state, action, reason = controller_with_grid.process_telemetry(15.0, 0.8)

    # Should hold position and alert since no safe cells found
    assert state == DroneState.HOLD_AND_ALERT
    assert action == DroneAction.HOLD_POSITION_ALERT

def test_nearest_safe_cell_selection(controller_with_grid):
    """Test that the nearest safe cell is selected from multiple options."""
    # Block some cells but leave nearest ones open
    controller_with_grid.set_grid_obstacles([
        (1, 1), (1, 3), (1, 5),  # Block some distant cells
        (5, 1), (5, 3), (5, 5)
    ])

    state, action, reason = controller_with_grid.process_telemetry(15.0, 0.8)

    # Should find a safe cell (many adjacent cells are still free)
    assert state == DroneState.LANDING
    assert action == DroneAction.LAND_AT_CLEAR_ZONE

    # Verify that grid has identified a nearest safe cell
    grid_state = controller_with_grid.get_grid_state()
    assert grid_state['nearest_safe_cell'] is not None

def test_grid_ignores_obstacle_cells(controller_with_grid):
    """Test that obstacle cells are never selected as landing zones."""
    # Set obstacles in a pattern
    obstacles = [(2, 3), (3, 2)]
    controller_with_grid.set_grid_obstacles(obstacles)

    state, action, reason = controller_with_grid.process_telemetry(15.0, 0.8)

    # Get the selected safe cell
    grid_state = controller_with_grid.get_grid_state()
    nearest = grid_state['nearest_safe_cell']

    if nearest is not None:
        # Verify the selected cell is NOT an obstacle
        assert nearest not in obstacles
        assert controller_with_grid.grid.is_cell_safe(*nearest)

def test_backward_compatibility_legacy_scan(controller_without_grid):
    """Test that legacy scan_result still works without grid."""
    state, action, reason = controller_without_grid.process_telemetry(
        15.0, 0.8, scan_result="clear_zone_found"
    )

    assert state == DroneState.LANDING
    assert action == DroneAction.LAND_AT_CLEAR_ZONE

def test_grid_state_retrieval(controller_with_grid):
    """Test retrieving grid state for visualization."""
    controller_with_grid.set_grid_obstacles([(2, 2), (4, 4)])
    controller_with_grid.process_telemetry(15.0, 0.8)

    grid_state = controller_with_grid.get_grid_state()

    assert grid_state is not None
    assert 'grid' in grid_state
    assert 'drone_position' in grid_state
    assert 'scanned_cells' in grid_state
    assert 'nearest_safe_cell' in grid_state

def test_ascii_rendering_through_controller(controller_with_grid):
    """Test ASCII rendering through controller interface."""
    controller_with_grid.set_grid_obstacles([(2, 2)])
    controller_with_grid.process_telemetry(15.0, 0.8)

    ascii_output = controller_with_grid.render_grid_ascii()

    assert isinstance(ascii_output, str)
    assert len(ascii_output) > 0
    assert 'D' in ascii_output  # Drone marker should be present

def test_multiple_scan_cycles(controller_with_grid):
    """Test multiple telemetry processing cycles."""
    # First cycle - normal
    state1, action1, reason1 = controller_with_grid.process_telemetry(50.0, 5.0)
    assert state1 == DroneState.MONITORING

    # Second cycle - critical with obstacle
    state2, action2, reason2 = controller_with_grid.process_telemetry(15.0, 0.8)
    assert state2 in [DroneState.LANDING, DroneState.HOLD_AND_ALERT]

def test_scan_radius_coverage(controller_with_grid):
    """Test that scan radius properly covers expected area."""
    # Process with critical conditions to trigger scan
    controller_with_grid.process_telemetry(15.0, 0.8)

    grid_state = controller_with_grid.get_grid_state()
    scanned_cells = grid_state['scanned_cells']

    # With radius 2 from center (3,3), should scan 24 cells (5x5 - 1 for drone)
    assert len(scanned_cells) == 24

def test_no_safe_landing_scenario(controller_with_grid):
    """Integration test: no available landing location."""
    # Create worst-case scenario: all nearby cells blocked
    all_obstacles = []
    for row in range(7):
        for col in range(7):
            if (row, col) != (3, 3):  # Keep drone position clear
                if abs(row - 3) <= 2 and abs(col - 3) <= 2:  # Within scan radius
                    all_obstacles.append((row, col))

    controller_with_grid.set_grid_obstacles(all_obstacles)

    state, action, reason = controller_with_grid.process_telemetry(15.0, 0.8)

    # Must hold position and alert
    assert state == DroneState.HOLD_AND_ALERT
    assert action == DroneAction.HOLD_POSITION_ALERT
    assert "No clear landing zone" in reason

def test_partial_blockage_finds_opening(controller_with_grid):
    """Test finding an opening when only partially blocked."""
    # Block 3 sides, leave one side open
    controller_with_grid.set_grid_obstacles([
        (2, 2), (2, 3), (2, 4),  # Top
        (3, 2),                   # Left
        (4, 2), (4, 3), (4, 4),  # Bottom
        # Right side (3,4) is open
    ])

    state, action, reason = controller_with_grid.process_telemetry(15.0, 0.8)

    # Should find the open cell
    assert state == DroneState.LANDING
    assert action == DroneAction.LAND_AT_CLEAR_ZONE

    grid_state = controller_with_grid.get_grid_state()
    nearest = grid_state['nearest_safe_cell']

    # The nearest safe cell should be on the open side
    assert nearest is not None
    assert controller_with_grid.grid.is_cell_safe(*nearest)
