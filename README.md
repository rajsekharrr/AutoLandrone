# AutoLandrone: Smart Emergency Landing Assistant

## Project Overview

AutoLandrone is a smart emergency landing assistant for drones designed to address the problem of low-cost drone crashes during critical battery situations. The system monitors drone battery status and detects obstacles below the drone to make intelligent emergency landing decisions.

This project aligns with **SDG 9: Industry, Innovation and Infrastructure** by proposing a low-cost safety add-on that can improve reliability for drone-based delivery, agriculture, surveillance, and other industrial applications.

## Problem Statement

Many low-cost drones crash when the battery becomes critically low and the drone cannot identify a safe landing zone in time. While most drone projects focus on obstacle avoidance during normal flight, this project specifically addresses emergency landing safety during descent.

## Current Implementation (Review 1)

This Review 1 demonstration focuses on the **software implementation** through simulation, logic demonstration, and clean module structure. Real drone hardware integration will come in later phases after the software logic is validated.

### What's Implemented

- Battery monitoring logic using simulated telemetry data
- Obstacle distance monitoring using simulated sensor readings
- Emergency decision engine with critical battery and obstacle detection
- Safe landing state machine: monitor, hover, scan, alert, land or hold
- Decision logging for demonstration and debugging
- Interactive Streamlit dashboard for scenario demonstration
- Automated tests using pytest

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
- **Battery ≤ 20% AND obstacle distance < 1.5m**: Hover and scan for clear zone
- **Scan finds clear zone**: Land at identified clear zone
- **Scan finds no clear zone**: Hold position and alert operator

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. Clone or download the project:
```bash
cd D:\AutoLandrone
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Streamlit Demo

Launch the interactive dashboard:
```bash
streamlit run app.py
```

The dashboard will open in your default web browser (typically at `http://localhost:8501`).

### Using the Demo

1. Select one of the 5 predefined scenarios from the dropdown
2. Click "Run Scenario" to execute the emergency landing logic
3. Observe the system status, selected actions, and decision log
4. Try different scenarios to see how the system responds

### Available Scenarios

1. **Normal Operation** - Battery at 50%, demonstrating monitoring state
2. **Low Battery with Clear Zone** - Battery at 15% with safe landing distance
3. **Low Battery with Obstacle** - Battery at 15% with obstacle detected
4. **Obstacle → Clear Zone Found** - Multi-step scenario with successful scan
5. **Obstacle → No Clear Zone** - Multi-step scenario requiring hold and alert

### Running Tests

Execute the test suite:
```bash
pytest tests/
```

Run tests with verbose output:
```bash
pytest tests/ -v
```

## Project Structure

```
D:\AutoLandrone\
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── app.py                            # Streamlit application
├── src/
│   ├── config.py                     # System configuration and constants
│   ├── telemetry.py                  # Battery telemetry simulation
│   ├── obstacle_sensor.py            # Obstacle distance simulation
│   ├── decision_engine.py            # Core emergency landing logic
│   ├── landing_controller.py         # State machine controller
│   ├── alert.py                      # Alert generation system
│   └── logger.py                     # Decision logging
└── tests/
    └── test_decision_engine.py       # Automated tests
```

## Review 1 Demonstration

This software prototype demonstrates:

1. **Modular Architecture** - Clean separation of concerns with well-defined modules
2. **Configurable Thresholds** - Battery (20%) and obstacle distance (1.5m) easily adjustable
3. **Decision Logic Validation** - Multiple test scenarios prove the logic works correctly
4. **Visual Demonstration** - Streamlit UI for clear presentation to reviewers
5. **Test Coverage** - Automated tests verify core functionality
6. **Documentation** - Clear explanation of how software maps to proposed hardware system

## Configuration

Key system parameters are defined in `src/config.py`:

- `BATTERY_CRITICAL_THRESHOLD = 20.0` (percentage)
- `OBSTACLE_SAFE_DISTANCE = 1.5` (meters)

Modify these values to test different threshold scenarios.

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
