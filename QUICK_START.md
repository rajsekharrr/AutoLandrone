# AutoLandrone Quick Start Guide

## How to Run the Project

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Tests (verify everything works)
```bash
pytest tests/ -v
```

Expected output: **39 tests passed** ✓

### Step 3: Launch the Dashboard
```bash
streamlit run app.py
```

The dashboard will automatically open in your browser at `http://localhost:8501`

### Step 4: Try the Grid Simulation

1. Select **"2D Grid Simulation"** mode
2. Choose scenario: **"Grid: Obstacle Below, Nearest Safe Cell Selected"**
3. Click **"Run Grid Simulation"**
4. Observe the visual grid showing:
   - 🚁 Drone position at center (3,3)
   - ❌ Obstacle cells (blocked areas)
   - 🔍 Scanned cells (24 cells within radius 2)
   - ⭐ Nearest safe landing cell (selected by algorithm)
   - Decision log showing the landing action

### Key Features to Demonstrate

**Test Scenario 4**: Shows intelligent nearest cell selection
- Battery: 15% (Critical)
- Obstacle: 0.8m (Unsafe)
- Result: System scans grid, finds nearest safe cell, lands there

**Test Scenario 5**: Shows hold-and-alert behavior
- Battery: 15% (Critical)
- Obstacle: 0.8m (Unsafe)
- All nearby cells blocked
- Result: System holds position and alerts (no safe landing available)

## Testing the Grid Algorithm

Run grid-specific tests:
```bash
pytest tests/test_landing_zone_grid.py -v
```

This runs 18 tests covering:
- Nearest safe cell selection ✓
- Obstacle cell filtering ✓
- No available landing location handling ✓
- Distance calculations ✓
- Grid visualization ✓

## Understanding the Output

### Decision Log Columns
- **Step**: Sequence number
- **Battery (%)**: Current battery percentage
- **Distance (m)**: Obstacle distance in meters
- **State**: Current system state (MONITORING, HOVERING, LANDING, etc.)
- **Action**: Selected action (CONTINUE_MONITORING, LAND_AT_CLEAR_ZONE, etc.)
- **Reason**: Explanation of why this action was chosen

### Grid Visualization
- **Grid Size**: 7×7 cells
- **Drone**: Always starts at center (3,3)
- **Scan Radius**: 2 cells in each direction (24 cells total)
- **Distance Method**: Euclidean distance (sqrt of sum of squared differences)

## Common Commands

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ -v --cov=src

# Run specific test file
pytest tests/test_landing_zone_grid.py -v

# Start dashboard
streamlit run app.py

# Check Python syntax
python -m py_compile app.py
```

## Troubleshooting

**Issue**: Tests fail
- **Solution**: Ensure Python 3.11+ is installed, run `pip install -r requirements.txt`

**Issue**: Streamlit doesn't start
- **Solution**: Check if port 8501 is available, or use `streamlit run app.py --server.port 8502`

**Issue**: Import errors
- **Solution**: Make sure you're in the D:\AutoLandrone directory when running commands

## Project Structure Quick Reference

```
src/
├── landing_zone_grid.py       ← 2D grid simulation (NEW)
├── landing_controller.py      ← Integrates grid with decision logic (UPDATED)
├── decision_engine.py         ← Core decision logic (UPDATED)
├── config.py                  ← Thresholds and constants
├── telemetry.py              ← Battery simulation
├── obstacle_sensor.py        ← Obstacle detection
├── alert.py                  ← Alert generation
└── logger.py                 ← Decision logging

tests/
├── test_landing_zone_grid.py          ← Grid tests (18 tests) (NEW)
├── test_landing_controller_grid.py    ← Integration tests (14 tests) (NEW)
└── test_decision_engine.py            ← Decision tests (7 tests)

app.py                         ← Streamlit dashboard with grid viz (UPDATED)
```

## Review 1 Checklist

- [x] 2D grid simulation implemented
- [x] Nearest safe cell selection algorithm
- [x] Visual grid representation in dashboard
- [x] All existing tests still pass (backward compatible)
- [x] New tests for grid functionality (39 total tests)
- [x] Integration with existing decision engine
- [x] Handle no available landing location scenario
- [x] Deterministic and reproducible results
- [x] Software-only, no hardware dependencies
- [x] Free and open-source tools only
- [x] Documentation updated

---

**Ready for Review 1 Demonstration!** 🚁
