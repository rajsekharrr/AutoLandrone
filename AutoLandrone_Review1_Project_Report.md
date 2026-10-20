# AutoLandrone
## Smart Emergency Landing Assistant

### Review 1 Project Report

## 1. Project Summary

AutoLandrone is a software prototype for a Smart Emergency Landing Assistant for drones. The project addresses a safety problem: a drone may reach a critically low battery level while the area below it is unsafe for landing because of an obstacle.

The prototype monitors two simulated inputs:

- Battery percentage from simulated drone telemetry
- Obstacle distance below the drone from a simulated distance sensor

When the battery is low, the system checks whether the landing area is safe. If an obstacle is detected, the software scans a nearby two-dimensional landing grid, rejects blocked cells, and selects the nearest safe cell. If the system cannot find a safe cell, it holds the drone position and raises an alert.

The current implementation is software-only. It demonstrates the decision-making and landing-zone search logic through a Streamlit dashboard. It does not send commands to a real drone.

## 2. Problem Statement

Low-cost drones can crash when their battery becomes critically low and they cannot identify a safe landing location. A normal obstacle-avoidance system is mainly concerned with avoiding objects during flight. AutoLandrone focuses on the emergency descent situation, where the drone must decide whether to land immediately, hover and search, or hold position and alert the operator.

An emergency landing assistant can reduce the chance of:

- Damage to the drone and its components
- Injury to people near the landing area
- Property damage
- Loss of confidence in autonomous drone systems

## 3. Project Objectives

1. Monitor battery status using a simulated telemetry input.
2. Detect whether the area below the drone is safe using a simulated obstacle-distance input.
3. Trigger emergency behavior when the battery reaches a critical level.
4. Search a nearby landing area when an obstacle blocks the direct landing location.
5. Select the nearest available safe landing cell.
6. Hold position and alert the operator when no safe location is available.
7. Present the result through a clear interactive dashboard.
8. Validate the software through automated tests.

## 4. Current Scope

The current Review 1 scope is the software implementation and simulation.

### Included

- Simulated battery telemetry
- Simulated obstacle-distance readings
- Battery and obstacle threshold logic
- Emergency landing decision engine
- Landing controller
- 7 x 7 landing-zone grid
- Obstacle placement and filtering
- Nearby-cell scanning
- Nearest-safe-cell selection
- Hold-and-alert behavior when all nearby cells are blocked
- Streamlit dashboard
- Decision log
- Automated unit and integration tests
- ASCII grid rendering for debugging and testing

### Not Included Yet

- Real Pixhawk communication
- Real MAVLink telemetry
- Physical HC-SR04 ultrasonic sensor integration
- ESP32 or Arduino hardware control
- Real drone movement or flight commands
- GPS-based coordinates
- Camera-based obstacle detection
- Computer vision or machine learning
- Real flight testing
- Safety certification for production use

## 5. Requirements Implemented From The Proposal

The original proposal requires a low-cost emergency landing module that can:

- Monitor battery information from Pixhawk telemetry in a future hardware version.
- Detect obstacles below the drone using an ultrasonic sensor in a future hardware version.
- Trigger hover and alert behavior when emergency thresholds are reached.
- Search for a safer nearby landing location when the direct landing area is blocked.
- Land at a safe location when one is available.
- Hold position and alert the operator when a safe location cannot be found.

The current software prototype represents the future hardware inputs with simulated values so that the decision logic can be developed and tested before hardware integration.

## 6. Decision Rules

The thresholds are defined in src/config.py:

| Parameter | Value | Meaning |
|---|---:|---|
| Critical battery threshold | 20.0% | Battery at or below this value triggers emergency landing logic |
| Safe obstacle distance | 1.5 m | Distance at or above this value is treated as clear for direct landing |

| Condition | State | Action |
|---|---|---|
| Battery above 20% | MONITORING | CONTINUE_MONITORING |
| Battery at or below 20%, distance at least 1.5 m | LANDING | SAFE_LANDING |
| Battery at or below 20%, distance below 1.5 m | HOVERING | OBSTACLE_DETECTED_ALERT |
| Grid scan finds a safe cell | LANDING | LAND_AT_CLEAR_ZONE |
| Grid scan finds no safe cell | HOLD_AND_ALERT | HOLD_POSITION_ALERT |

The boundary values are tested. A battery value of exactly 20% is critical, while an obstacle distance of exactly 1.5 m is safe for direct landing.

## 7. System Architecture

~~~text
Simulated battery and obstacle inputs
                 |
                 v
       +-----------------------+
       | Landing Controller    |
       | Coordinates workflow  |
       +-----------+-----------+
                   |
                   v
       +-----------------------+
       | Decision Engine       |
       | Applies thresholds    |
       +-----+-------------+---+
             |             |
       Clear area     Obstacle during emergency
             |             |
             v             v
       Direct landing   Landing Zone Grid
                              |
                    +---------+---------+
                    |                   |
                    v                   v
             Safe cell found     No safe cell
                    |                   |
                    v                   v
              Land safely       Hold and alert

              Streamlit dashboard
              Decision logger
~~~

## 8. Main Software Components

### app.py

This is the Streamlit application and user-facing demonstration. It displays the project context, presents five scenarios, shows battery and obstacle status, runs the controller, displays the decision process, renders the 7 x 7 grid, and shows the final state, action, reason, and decision log.

### src/config.py

This module stores the project thresholds and the named drone states and actions. Important values are:

- BATTERY_CRITICAL_THRESHOLD = 20.0
- OBSTACLE_SAFE_DISTANCE = 1.5

### src/telemetry.py

BatteryTelemetry simulates a battery telemetry source. It stores a battery percentage, returns the current value, and clamps updates to the range 0% to 100%. A future implementation can replace this source with Pixhawk/MAVLink data.

### src/obstacle_sensor.py

ObstacleSensor simulates a distance sensor. It stores a distance value, returns the current distance, and prevents negative values. A future implementation can replace it with an HC-SR04 or another physical sensor.

### src/decision_engine.py

DecisionEngine contains the safety rules. It receives battery percentage, obstacle distance, and optional scan information. It returns the current state, selected action, and a human-readable explanation. It supports both the original text-based scan results and the newer grid-based safe-cell result.

### src/landing_controller.py

LandingController coordinates telemetry processing and decision-making. Grid simulation can be enabled with use_grid_simulation=True. When the battery is critical and the obstacle distance is unsafe, it asks the grid to scan, passes the result to the decision engine, stores the state and action, and makes the grid state available to the dashboard.

### src/landing_zone_grid.py

LandingZoneGrid creates the landing environment, places obstacles, scans nearby cells, calculates distances, and selects the nearest safe landing cell.

Default configuration:

- Grid size: 7 x 7 cells
- Drone position: center cell (3, 3)
- Scan radius: 2 cells
- Cells scanned from the center: 24, excluding the drone's current cell

### src/alert.py

AlertSystem converts emergency actions into readable warning messages. The current version simulates the alert in software. A future hardware version could use the same logic to activate a buzzer or LED.

### src/logger.py

DecisionLogger records each simulation step, including battery, obstacle distance, state, action, reason, and optional scan result. It returns a pandas DataFrame for display in Streamlit.

## 9. Landing-Zone Grid Algorithm

The algorithm is deterministic, so the same input and obstacle layout always produce the same result.

1. Create a 7 x 7 grid.
2. Place the drone at the center cell (3, 3).
3. Place the scenario's obstacle cells.
4. Check the battery and obstacle thresholds.
5. If the battery is not critical, continue monitoring.
6. If the battery is critical and the downward distance is safe, perform direct landing.
7. If the battery is critical and the downward distance is unsafe, scan cells within radius 2.
8. Exclude the drone's current cell.
9. Reject cells marked as obstacles.
10. Calculate the Euclidean distance of each remaining cell.
11. Sort the safe cells by distance.
12. Select the closest safe cell.
13. Return LAND_AT_CLEAR_ZONE if a cell exists.
14. Return HOLD_POSITION_ALERT if every scanned cell is blocked.

The distance formula is:

~~~text
distance = sqrt((candidate_row - drone_row)^2 +
                (candidate_col - drone_col)^2)
~~~

This is a simplified planning model for Review 1. A real drone would also require GPS coordinates, flight dynamics, battery consumption, wind information, sensor reliability, and a certified flight controller.

## 10. Demonstration Scenarios

The current Streamlit dashboard provides five scenarios.

### Scenario 1: Normal Monitoring

- Battery: 50%
- Obstacle distance: 5.0 m
- Result: MONITORING
- Action: CONTINUE_MONITORING

The system remains in normal monitoring because the battery is above the critical threshold.

### Scenario 2: Low Battery, Clear Area

- Battery: 15%
- Obstacle distance: 2.5 m
- Result: LANDING
- Action: SAFE_LANDING

The battery is critical, but the obstacle distance is safe, so the system can land directly.

### Scenario 3: Obstacle Detected, Safe Location Found

- Battery: 15%
- Obstacle distance: 0.8 m
- Several nearby obstacles are placed on the grid.
- Result: LANDING
- Action: LAND_AT_CLEAR_ZONE

The controller scans the grid, rejects obstacle cells, and chooses the nearest available safe cell.

### Scenario 4: Obstacle Detected, No Safe Location

- Battery: 15%
- Obstacle distance: 0.8 m
- All cells in the scan area are blocked.
- Result: HOLD_AND_ALERT
- Action: HOLD_POSITION_ALERT

The system does not choose a blocked cell. It holds position and alerts the operator.

### Scenario 5: Direct Safe Landing

- Battery: 15%
- Obstacle distance: 1.8 m
- Result: LANDING
- Action: SAFE_LANDING

This demonstrates that a critical battery does not require a grid scan when the direct landing distance is safe.

## 11. Streamlit Dashboard

The dashboard is designed for an academic demonstration rather than production flight control. It provides:

- Project title and purpose
- Software-simulation notice
- Scenario selection
- Battery status and critical threshold
- Obstacle-distance status and safe-distance threshold
- Run simulation control
- Step-by-step decision flow
- Color-coded status messages
- Visual 7 x 7 landing grid
- Grid statistics
- Final state, action, and explanation
- Decision log table
- System configuration information

The grid uses visual markers for the drone position, obstacles, scanned cells, the selected landing cell, and empty cells. The dashboard also explains that Pixhawk and physical sensor integration are future work.

## 12. Technology Stack

| Technology | Use | Cost/licensing position |
|---|---|---|
| Python | Application and simulation logic | Free and open-source |
| Streamlit | Interactive local dashboard | Free and open-source |
| pandas | Decision-log table generation | Free and open-source |
| pytest | Automated testing | Free and open-source |
| Markdown | Documentation | Open format |
| Git and GitHub | Version control and repository hosting | Free options available |

The current implementation does not require paid cloud services, paid APIs, or a database. The proposal identifies pymavlink as a future integration library, but the current Review 1 version does not connect to a real Pixhawk.

## 13. Project File Structure

~~~text
AutoLandrone/
├── app.py
├── requirements.txt
├── README.md
├── QUICK_START.md
├── HOW_TO_RUN.md
├── FEATURE_SUMMARY.md
├── AutoLandrone_Claude_Code_Reference.md
├── DA1ProjectProposal.pptx
├── test_grid_demo.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── telemetry.py
│   ├── obstacle_sensor.py
│   ├── decision_engine.py
│   ├── landing_controller.py
│   ├── landing_zone_grid.py
│   ├── alert.py
│   └── logger.py
└── tests/
    ├── test_decision_engine.py
    ├── test_landing_zone_grid.py
    └── test_landing_controller_grid.py
~~~

## 14. Testing and Verification

The project contains 39 automated tests.

### Decision Engine Tests

The seven decision-engine tests verify normal monitoring, direct safe landing, obstacle detection, legacy scan results, and both threshold boundary cases.

### Landing Grid Tests

The grid tests verify initialization, obstacle placement, safe-cell checks, out-of-bounds handling, Euclidean distance, scanning radius, nearest-cell selection, obstacle filtering, all-cells-blocked behavior, small-grid behavior, state export, and ASCII rendering.

### Controller Integration Tests

The controller tests verify grid initialization, direct landing, emergency grid scanning, nearest-cell integration, all-cells-blocked behavior, legacy compatibility, grid-state retrieval, multiple processing cycles, and partial blockage.

### Verified Result

The complete test suite was executed with:

~~~powershell
python -m pytest tests/ -q
~~~

Result:

~~~text
39 passed in 0.07s
~~~

## 15. How To Run The Project

From the project directory:

~~~powershell
cd D:\AutoLandrone
pip install -r requirements.txt
python -m pytest tests/ -v
streamlit run app.py
~~~

The dashboard normally opens at http://localhost:8501.

An optional command-line demonstration is available:

~~~powershell
python test_grid_demo.py
~~~

## 16. Recommended Review Demonstration

1. Explain that the project is a software prototype for emergency drone landing.
2. Run the normal monitoring scenario and show that the system continues monitoring.
3. Run the obstacle-detected scenario with a safe location.
4. Point out the critical battery, unsafe obstacle distance, grid scan, obstacle cells, and selected landing cell.
5. Explain that the nearest safe cell is chosen using Euclidean distance.
6. Run the no-safe-location scenario and show the hold-and-alert result.
7. Run python -m pytest tests/ -v and show that all 39 tests pass.
8. Explain that Pixhawk, ultrasonic sensor, and physical drone integration are future phases.

## 17. Current Strengths

- Simple and explainable safety rules
- Modular software structure
- Deterministic and reproducible grid simulation
- Safe fallback when no landing cell is available
- Visual dashboard instead of console-only output
- Unit and integration test coverage
- Free tools suitable for student development
- Clear separation between current simulation and future hardware integration

## 18. Current Limitations

The grid cell is an abstract simulation location. It is not a GPS coordinate and does not represent a measured physical area on the ground.

The prototype does not currently model drone movement, battery consumption during hovering, wind, drone speed, obstacle height or shape, sensor noise, GPS error, communication delay, telemetry loss, or production safety certification.

Therefore, the current result demonstrates software decision logic and visualization. It should not be described as a validated autonomous flight system.

## 19. Future Development

Possible future work includes:

1. Replace simulated battery values with Pixhawk telemetry through MAVLink.
2. Connect an HC-SR04 or similar sensor through an ESP32 or Arduino.
3. Convert grid locations into GPS-based landing coordinates.
4. Add sensor filtering and sensor-failure handling.
5. Model battery consumption during hovering and scanning.
6. Add path planning instead of selecting only the nearest cell.
7. Add dynamic obstacle updates during scanning.
8. Add a physical buzzer or LED alert.
9. Test first with a bench setup or drone simulator.
10. Perform safety validation before any real-world deployment.

## 20. Conclusion

AutoLandrone Review 1 delivers a complete software prototype for emergency drone landing decisions. It monitors simulated battery and obstacle inputs, applies configurable safety thresholds, scans a deterministic 7 x 7 landing environment, selects the nearest safe landing cell, and holds position when no safe cell exists.

The Streamlit dashboard makes the system behavior visible, while the automated test suite verifies the core decision logic and grid integration. The project provides a clear software foundation for future Pixhawk, sensor, GPS, and real-drone integration.

**Current status:** Software prototype ready for Review 1 demonstration  
**Verification status:** 39 automated tests passing  
**Hardware status:** Planned for a future phase; not included in the current prototype
