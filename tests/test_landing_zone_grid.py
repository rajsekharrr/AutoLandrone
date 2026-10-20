import pytest
from src.landing_zone_grid import LandingZoneGrid

@pytest.fixture
def grid():
    """Create a 7x7 grid with drone at center (3,3)."""
    return LandingZoneGrid(grid_size=7)

def test_grid_initialization(grid):
    """Test that grid initializes correctly."""
    assert grid.grid_size == 7
    assert grid.drone_position == (3, 3)
    assert len(grid.grid) == 7
    assert len(grid.grid[0]) == 7
    assert grid.nearest_safe_cell is None

def test_set_single_obstacle(grid):
    """Test setting a single obstacle."""
    grid.set_obstacle(2, 2)
    assert grid.grid[2][2] == 'obstacle'
    assert not grid.is_cell_safe(2, 2)

def test_set_multiple_obstacles(grid):
    """Test setting multiple obstacles at once."""
    obstacles = [(1, 1), (2, 2), (4, 4)]
    grid.set_obstacles(obstacles)

    for row, col in obstacles:
        assert grid.grid[row][col] == 'obstacle'
        assert not grid.is_cell_safe(row, col)

def test_safe_cell_detection(grid):
    """Test that empty cells are detected as safe."""
    grid.set_obstacle(2, 2)
    assert grid.is_cell_safe(1, 1)
    assert grid.is_cell_safe(3, 3)
    assert not grid.is_cell_safe(2, 2)

def test_out_of_bounds_cells_not_safe(grid):
    """Test that out-of-bounds cells are not safe."""
    assert not grid.is_cell_safe(-1, 0)
    assert not grid.is_cell_safe(0, -1)
    assert not grid.is_cell_safe(7, 0)
    assert not grid.is_cell_safe(0, 7)

def test_distance_calculation(grid):
    """Test distance calculation from drone to cells."""
    # Drone at (3,3)
    assert grid.get_distance_to_cell(3, 3) == 0.0  # Same position
    assert grid.get_distance_to_cell(3, 4) == 1.0  # One cell right
    assert grid.get_distance_to_cell(4, 3) == 1.0  # One cell down
    assert pytest.approx(grid.get_distance_to_cell(4, 4), 0.01) == 1.414  # Diagonal

def test_scan_nearby_cells(grid):
    """Test scanning nearby cells within radius."""
    scanned = grid.scan_nearby_cells(scan_radius=1)

    # Should scan 8 cells around drone (3x3 - 1 for drone position)
    assert len(scanned) == 8
    assert (3, 3) not in scanned  # Drone position not included
    assert (2, 2) in scanned
    assert (2, 3) in scanned
    assert (2, 4) in scanned
    assert (3, 2) in scanned
    assert (3, 4) in scanned
    assert (4, 2) in scanned
    assert (4, 3) in scanned
    assert (4, 4) in scanned

def test_find_nearest_safe_cell_no_obstacles(grid):
    """Test finding nearest safe cell when no obstacles present."""
    nearest = grid.find_nearest_safe_cell(scan_radius=2)

    # Should find a cell (any adjacent cell is safe)
    assert nearest is not None
    row, col = nearest

    # Should be adjacent to drone (distance = 1)
    distance = grid.get_distance_to_cell(row, col)
    assert distance == 1.0

def test_find_nearest_safe_cell_with_obstacles(grid):
    """Test finding nearest safe cell when some obstacles present."""
    # Block cells immediately around drone
    grid.set_obstacles([(2, 3), (3, 2), (3, 4), (4, 3)])

    # Should find a diagonal cell (distance ≈ 1.414)
    nearest = grid.find_nearest_safe_cell(scan_radius=2)
    assert nearest is not None

    # Should be one of the diagonal cells
    assert nearest in [(2, 2), (2, 4), (4, 2), (4, 4)]

def test_find_nearest_safe_cell_all_blocked(grid):
    """Test when all nearby cells are blocked - critical test case."""
    # Block all cells within radius 2 around drone (3,3)
    obstacles = []
    for row in range(1, 6):  # rows 1-5
        for col in range(1, 6):  # cols 1-5
            if (row, col) != (3, 3):  # Don't block drone position
                obstacles.append((row, col))

    grid.set_obstacles(obstacles)

    # Should return None when all cells blocked
    nearest = grid.find_nearest_safe_cell(scan_radius=2)
    assert nearest is None
    assert grid.nearest_safe_cell is None

def test_find_nearest_safe_cell_selects_closest(grid):
    """Test that nearest cell is selected when multiple safe cells exist."""
    # Block some cells but leave one very close
    grid.set_obstacles([
        (2, 2), (2, 4), (4, 2), (4, 4),  # Block diagonals
        (3, 2), (3, 4)  # Block left and right
    ])

    # Only (2,3) and (4,3) remain safe and adjacent
    nearest = grid.find_nearest_safe_cell(scan_radius=2)
    assert nearest is not None
    assert nearest in [(2, 3), (4, 3)]  # Both have distance 1.0

    # Verify it's actually distance 1
    distance = grid.get_distance_to_cell(*nearest)
    assert distance == 1.0

def test_scanned_cells_tracking(grid):
    """Test that scanned cells are properly tracked."""
    assert len(grid.scanned_cells) == 0

    grid.scan_nearby_cells(scan_radius=1)
    assert len(grid.scanned_cells) == 8

    # Scanning again shouldn't duplicate
    grid.scan_nearby_cells(scan_radius=1)
    assert len(grid.scanned_cells) == 8

def test_grid_state_export(grid):
    """Test exporting grid state for visualization."""
    grid.set_obstacles([(2, 2), (4, 4)])
    grid.find_nearest_safe_cell(scan_radius=1)

    state = grid.get_grid_state()

    assert state['grid_size'] == 7
    assert state['drone_position'] == (3, 3)
    assert len(state['scanned_cells']) > 0
    assert state['nearest_safe_cell'] is not None

def test_ascii_rendering(grid):
    """Test ASCII grid rendering."""
    grid.set_obstacles([(2, 2), (4, 4)])
    grid.find_nearest_safe_cell(scan_radius=1)

    ascii_grid = grid.render_grid_ascii()

    assert 'D' in ascii_grid  # Drone marker
    assert 'X' in ascii_grid  # Obstacle marker
    assert 'S' in ascii_grid  # Scanned cell marker
    assert '*' in ascii_grid  # Nearest safe cell marker

def test_ignore_obstacles_when_selecting_safe_cell(grid):
    """Test that obstacles are correctly ignored when finding safe cells."""
    # Create a pattern where obstacles surround but don't block all cells
    grid.set_obstacles([(2, 2), (2, 3), (2, 4)])  # Block top row

    nearest = grid.find_nearest_safe_cell(scan_radius=2)

    # Should find a safe cell (not an obstacle)
    assert nearest is not None
    assert grid.is_cell_safe(*nearest)

    # Verify the nearest cell is NOT one of the obstacles
    assert nearest not in [(2, 2), (2, 3), (2, 4)]

def test_edge_case_small_grid():
    """Test with a small 3x3 grid."""
    small_grid = LandingZoneGrid(grid_size=3, drone_position=(1, 1))

    assert small_grid.grid_size == 3
    assert small_grid.drone_position == (1, 1)

    # Block all surrounding cells
    small_grid.set_obstacles([(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)])

    nearest = small_grid.find_nearest_safe_cell(scan_radius=1)
    assert nearest is None

def test_partial_scan_radius(grid):
    """Test scanning with different radius values."""
    # Radius 1 should scan 8 cells
    scanned_1 = grid.scan_nearby_cells(scan_radius=1)
    grid.scanned_cells.clear()

    # Radius 2 should scan 24 cells (5x5 - 1 for drone)
    scanned_2 = grid.scan_nearby_cells(scan_radius=2)

    assert len(scanned_1) == 8
    assert len(scanned_2) == 24
    assert len(scanned_2) > len(scanned_1)
