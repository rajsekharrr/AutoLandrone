# AutoLandrone: Smart Emergency Landing Assistant

## Project Overview

AutoLandrone is a smart emergency landing assistant for drones designed to address the problem of low-cost drone crashes during critical battery situations. The system monitors drone battery status, detects obstacles below the drone, and uses a **2D grid simulation** to intelligently find the nearest safe landing zone.

This project aligns with **SDG 9: Industry, Innovation and Infrastructure** by proposing a low-cost safety add-on that can improve reliability for drone-based delivery, agriculture, surveillance, and other industrial applications.

## Problem Statement

Many low-cost drones crash when the battery becomes critically low and the drone cannot identify a safe landing zone in time. While most drone projects focus on obstacle avoidance during normal flight, this project specifically addresses emergency landing safety during descent.

## Current Implementation (Review 1)

This Review 1 demonstration focuses on the **software implementation** through simulation, logic demonstration, and clean module structure. Real drone hardware integration will come in later phases after the software logic is validated.

### What's Implemented

- Battery monitoring logic using simulated telemetry data
- Obstacle distance monitoring using simulated sensor readings
- **2D Grid-based landing zone simulation** with visual representation
- **Nearest safe cell selection** using Euclidean distance algorithm
- Emergency decision engine with critical battery and obstacle detection
- Safe landing state machine: monitor, hover, scan, alert, land or hold
- Decision logging for demonstration and debugging
- Interactive Streamlit dashboard with dual simulation modes
- Comprehensive automated tests using pytest (39 tests)

### Key Features: 2D Landing Zone Grid Simulation

The new grid simulation provides:

- **Visual 7x7 grid representation** of the landing area around the drone
- **Deterministic obstacle placement** and detection
- **Automatic scanning** of nearby cells (2-cell radius) when battery ≤ 20% and obstacle < 1.5m
- **Nearest safe cell calculation** using Euclidean distance
- **Smart decision logic**: 
  - Lands at nearest safe cell if available
  - Holds position and alerts if all nearby cells are blocked
- **Real-time visualization** showing:
  - 🚁 Drone position
  - ❌ Obstacle cells
  - 🔍 Scanned cells
  - ⭐ Nearest safe landing cell
  - ⬜ Empty cells

### What's Not Implemented (Future Work)

- Real-world autonomous flight testing
- Physical drone hardware integration (Pixhawk, ultrasonic sensors)
- Advanced computer vision or AI-based landing zone detection
- Production-level safety certification
- Real-time MAVLink telemetry integration

## Tech Stack

- **Language**: Python 3.11+
- **UI Framework**: Streamlit (free, open-source)
- **Testing**: pytest (free, open-source)
- **Data Processing**: pandas
- **Future Integration**: pymavlink (for drone communication)

All technologies used are free and open-source, suitable for student development with no paid services required.

## System Architecture

```
AutoLandrone Software
│
├── Telemetry Input Layer (simulated battery data)
├── Sensor Input Layer (simulated obstacle distance)
├── Safety Decision Engine (threshold checks and action selection)
├── Landing Controller (state machine management)
├── Alert Module (emergency notifications)
└── Logger (decision history tracking)
```

## Decision Rules

The system implements the following emergency landing logic:

- **Battery > 20%**: Continue normal monitoring
- **Battery ≤ 20% AND obstacle distance ≥ 1.5m**: Execute safe landing
- **Battery ≤ 20% AND obstacle distance < 1.5m**: Hover and scan nearby cells in grid
- **Scan finds safe cell**: Land at nearest safe cell (selected by minimum Euclidean distance)
- **Scan finds no safe cell**: Hold position and alert operator

### Grid Simulation Behavior

When critical conditions are met (battery ≤ 20% and obstacle < 1.5m):

1. **Hover**: Drone maintains current position
2. **Scan**: System scans all cells within 2-cell radius (24 cells in 7x7 grid)
3. **Analyze**: Identifies all safe (non-obstacle) cells
4. **Select**: Chooses nearest safe cell using Euclidean distance
5. **Land**: Navigates to selected cell, OR
6. **Hold & Alert**: If all cells blocked, holds position and alerts operator

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. Clone or navigate to the project directory:
```bash
cd D:\AutoLandrone
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Interactive Dashboard

Launch the presentation-ready dashboard:
```bash
streamlit run app.py
```

The dashboard will open in your default web browser (typically at `http://localhost:8501`).

### Presentation Instructions for Review 1

The dashboard is designed for easy demonstration to professors and reviewers. Follow these steps:

#### **Quick 5-Minute Demo**

1. **Launch the Dashboard**
   ```bash
   streamlit run app.py
   ```

2. **Explain the Project Context** (30 seconds)
   - Point to the blue banner explaining this is a software simulation
   - Mention hardware integration is planned for future phases

3. **Demonstrate Scenario 1: Normal Monitoring** (1 minute)
   - Select "1. ✅ Normal Monitoring (Battery OK)"
   - Click "▶️ RUN SCENARIO"
   - Show: Battery is 50% (green), system continues monitoring
   - Point out: 5-step process flow at top

4. **Demonstrate Scenario 3: Safe Location Found** (2 minutes) ⭐ **Best Demo**
   - Select "3. 🟡 Obstacle Detected - Safe Location Found"
   - Click "▶️ RUN SCENARIO"
   - Walk through the decision process:
     - Battery: 15% (Critical - red)
     - Obstacle: 0.8m (Unsafe - red)
     - System: Hovers and scans grid
     - Result: Finds nearest safe landing cell
   - Show the **visual 7×7 grid** with:
     - 🚁 Drone position (center)
     - ❌ Obstacles (red cells)
     - 🔍 Scanned cells (blue)
     - ⭐ Selected landing zone (yellow)
   - Explain: System calculated distances and selected nearest safe cell

5. **Demonstrate Scenario 4: No Safe Location** (1 minute)
   - Select "4. 🔴 Obstacle Detected - No Safe Location"
   - Click "▶️ RUN SCENARIO"
   - Show: All cells blocked, system holds position and alerts
   - Point out: Red alert message at top

6. **Wrap Up** (30 seconds)
   - Expand "⚙️ System Configuration" to show thresholds
   - Mention: 39 automated tests all passing

#### **Extended 10-Minute Demo (If Time Permits)**

Follow the 5-minute demo above, then add:

7. **Show All 5 Scenarios** - Run through each scenario quickly
8. **Explain the Algorithm** - Open configuration panel, explain decision rules
9. **Show Test Results**
   ```bash
   pytest tests/ -v
   ```
   - Demonstrate: 39 tests, all passing
   - Explain: Tests cover nearest cell selection, obstacle filtering, edge cases

#### **Key Points to Emphasize**

✅ **Software-first approach** - Validates logic before hardware integration  
✅ **Visual demonstration** - Easy to understand 7×7 grid with clear symbols  
✅ **Intelligent decision-making** - Selects nearest safe cell using Euclidean distance  
✅ **Safety-critical** - Holds position when no safe landing available  
✅ **Well-tested** - 39 comprehensive automated tests  
✅ **SDG 9 alignment** - Low-cost safety enhancement for drone operations  

#### **Recommended Scenario Order**

1. Start with **Scenario 1** (Normal) - Shows baseline monitoring
2. Demo **Scenario 3** (Safe location found) - Shows grid algorithm ⭐
3. Demo **Scenario 4** (No safe location) - Shows safety fallback
4. Optional: **Scenario 2** (Direct landing) - Shows clear area behavior
5. Optional: **Scenario 5** (Direct safe landing) - Shows no-scan path

#### **If Questions Arise**

- **"How does it select the landing zone?"**  
  → Show grid, explain Euclidean distance calculation: `sqrt((Δrow)² + (Δcol)²)`

- **"What about hardware?"**  
  → Explain: Software prototype first, then integrate with Pixhawk (MAVLink) and ultrasonic sensors

- **"Is this tested?"**  
  → Run `pytest tests/ -v` to show 39 passing tests

- **"What if battery dies during scan?"**  
  → Good question! Future work: battery consumption modeling during hover

### Dashboard Features

The presentation-ready dashboard includes:

- **🎨 Color-coded status indicators**
  - 🟢 Green: Safe/Normal conditions
  - 🟡 Yellow: Warning/Processing
  - 🔴 Red: Critical/Danger

- **📊 Real-time telemetry display**
  - Battery percentage with threshold comparison
  - Obstacle distance with safety assessment

- **🔄 Step-by-step process visualization**
  - Battery Check → Obstacle Check → Hover & Scan → Find Safe Cell → Final Action

- **🗺️ Visual 7×7 landing zone grid**
  - Clear emoji-based representation
  - Color-coded cells for easy understanding

- **✅ Decision result summary**
  - Current system state
  - Selected action
  - Detailed explanation

### Using the Dashboard

1. **Select Simulation Mode**: Choose between "Legacy Scenarios" or "2D Grid Simulation"
2. **Choose a Scenario**: Select from the dropdown menu
3. **Run Simulation**: Click "Run Scenario" or "Run Grid Simulation"
4. **View Results**: Observe the system status, grid visualization (if applicable), and decision log
5. **Try Different Scenarios**: Experiment with various battery levels and obstacle configurations

### Simulation Modes

#### Legacy Scenarios (5 scenarios)
- Simple step-by-step decision demonstrations
- Good for understanding basic decision logic
- Text-based scan results

#### 2D Grid Simulation (6 scenarios)
- Visual grid representation of landing area
- Real-time obstacle and safe cell visualization
- Demonstrates nearest safe cell selection algorithm
- Interactive grid showing drone position, obstacles, scanned cells, and landing zone

### Available Grid Scenarios

1. **Grid: Normal Operation** - Battery sufficient, no emergency
2. **Grid: Low Battery, Clear Zone** - Critical battery with clear landing
3. **Grid: Obstacle Below, Safe Cell Found** - Few obstacles, safe cells available
4. **Grid: Obstacle Below, Nearest Safe Cell Selected** - Multiple obstacles, algorithm selects closest safe cell
5. **Grid: All Cells Blocked - Hold Alert** - Worst case: no safe landing zones available
6. **Grid: Partial Blockage - Find Opening** - Three sides blocked, finds the one opening

### Running Tests

Execute the complete test suite:
```bash
pytest tests/
```

Run tests with verbose output:
```bash
pytest tests/ -v
```

Run specific test files:
```bash
pytest tests/test_landing_zone_grid.py -v
pytest tests/test_landing_controller_grid.py -v
pytest tests/test_decision_engine.py -v
```

### Test Coverage

The project includes 39 comprehensive tests covering:
- Decision engine logic (7 tests)
- Landing zone grid functionality (18 tests)
- Landing controller integration (14 tests)

Key test scenarios:
- ✅ Selecting nearest safe cell from multiple options
- ✅ Ignoring obstacle cells when finding safe landing zones
- ✅ Handling no available landing location (all cells blocked)
- ✅ Distance calculation and nearest cell selection
- ✅ Backward compatibility with legacy scenarios
- ✅ Grid state visualization and export

## Project Structure

```
D:\AutoLandrone\
├── README.md                                # This file
├── requirements.txt                         # Python dependencies
├── app.py                                  # Streamlit application with grid visualization
├── AutoLandrone_Claude_Code_Reference.md   # Project reference document
├── src/
│   ├── config.py                           # System configuration and constants
│   ├── telemetry.py                        # Battery telemetry simulation
│   ├── obstacle_sensor.py                  # Obstacle distance simulation
│   ├── decision_engine.py                  # Core emergency landing logic
│   ├── landing_controller.py               # State machine controller with grid integration
│   ├── landing_zone_grid.py                # 2D grid simulation and nearest cell selection
│   ├── alert.py                            # Alert generation system
│   └── logger.py                           # Decision logging
└── tests/
    ├── test_decision_engine.py             # Decision engine tests (7 tests)
    ├── test_landing_zone_grid.py           # Grid simulation tests (18 tests)
    └── test_landing_controller_grid.py     # Integration tests (14 tests)
```

## Review 1 Demonstration

This software prototype demonstrates:

1. **Modular Architecture** - Clean separation of concerns with well-defined modules
2. **2D Grid Simulation** - Visual, deterministic representation of landing zone
3. **Intelligent Cell Selection** - Nearest safe cell algorithm using Euclidean distance
4. **Configurable Thresholds** - Battery (20%) and obstacle distance (1.5m) easily adjustable
5. **Decision Logic Validation** - Multiple test scenarios prove the logic works correctly
6. **Visual Demonstration** - Interactive Streamlit UI with grid visualization for clear presentation
7. **Comprehensive Test Coverage** - 39 automated tests verify core functionality including:
   - Nearest safe cell selection
   - Obstacle cell filtering
   - No available landing location handling
8. **Documentation** - Clear explanation of how software maps to proposed hardware system

### Grid Simulation Algorithm

The landing zone grid simulation uses the following approach:

1. **Grid Representation**: 7x7 cell grid centered on drone position (3,3)
2. **Obstacle Detection**: Cells marked as obstacles are excluded from landing zone selection
3. **Scanning**: When triggered, scans all cells within radius of 2 cells (24 cells total)
4. **Distance Calculation**: Uses Euclidean distance: `sqrt((row_diff)² + (col_diff)²)`
5. **Selection**: Sorts safe cells by distance and selects the nearest one
6. **Deterministic**: Same inputs always produce same outputs (no randomness)

This approach is:
- **Simple**: Easy to understand and explain for Review 1
- **Deterministic**: Reproducible results for testing
- **Software-only**: No hardware dependencies
- **Free**: Uses only open-source Python libraries
- **Visual**: Clear grid display for demonstration

## Configuration

Key system parameters are defined in `src/config.py`:

- `BATTERY_CRITICAL_THRESHOLD = 20.0` (percentage)
- `OBSTACLE_SAFE_DISTANCE = 1.5` (meters)
- `GRID_SIZE = 7` (7x7 grid, configurable in controller)
- `SCAN_RADIUS = 2` (cells in each direction)

Modify these values to test different threshold scenarios.

## How It Works: Emergency Landing Flow

### Without Grid Simulation (Legacy Mode)
1. Monitor battery and obstacle distance continuously
2. If battery ≤ 20% and distance ≥ 1.5m → Land immediately
3. If battery ≤ 20% and distance < 1.5m → Hover and alert
4. Manual scan result determines next action

### With Grid Simulation (New Mode)
1. Monitor battery and obstacle distance continuously
2. If battery ≤ 20% and distance ≥ 1.5m → Land immediately
3. If battery ≤ 20% and distance < 1.5m → **Trigger grid scan**:
   - Scan all cells within 2-cell radius (24 cells)
   - Calculate distance to each safe (non-obstacle) cell
   - Select nearest safe cell using Euclidean distance
   - If safe cell found → Land at that cell
   - If no safe cell → Hold position and alert

### Example: Grid Decision Process

```
Initial State:
- Battery: 15% (Critical!)
- Obstacle Distance: 0.8m (Unsafe!)
- Drone Position: (3, 3)

Grid Layout (7x7):
. . . . . . .
. X . . . X .
. . X . X . .
. . . D . . .    D = Drone, X = Obstacle, . = Empty
. . X . X . .
. X . . . X .
. . . . . . .

Action: Scan nearby cells (radius = 2)
Found safe cells: (2,3), (3,2), (3,4), (4,3), and others
Distances calculated:
- (2,3): distance = 1.0
- (3,2): distance = 1.0  
- (3,4): distance = 1.0
- (4,3): distance = 1.0

Result: Select one of the nearest cells at distance 1.0
Decision: LAND_AT_CLEAR_ZONE at grid cell (2,3)
```

## Future Enhancements

- Integration with Pixhawk via MAVLink for real telemetry
- Physical ultrasonic sensor (HC-SR04) integration via ESP32/Arduino
- Multi-point scanning pattern for better landing zone detection
- GPS-based safe zone mapping
- Buzzer and LED physical alert system
- Mobile app for remote monitoring
- Real-world flight testing and safety validation

## Team & Academic Context

- **Project Type**: Student engineering project
- **Review Phase**: Review 1 (Software Prototype)
- **SDG Alignment**: SDG 9 - Industry, Innovation and Infrastructure
- **Focus**: Low-cost drone safety enhancement

## License

This is an academic project developed for educational purposes.

## Support

For issues or questions about this project, please contact the development team.

---

**AutoLandrone** - Making drone emergency landings safer, one line of code at a time.
