# AutoLandrone: Smart Emergency Landing Assistant

## Project Overview

AutoLandrone is a student project for building a smart emergency landing assistant for drones. The main problem is that low-cost drones can crash when the battery becomes critically low and the drone does not identify a safe landing zone in time. Many basic drone projects focus on obstacle avoidance during normal flight, but this project focuses on emergency landing safety during descent.

The system should monitor drone battery status from Pixhawk telemetry, detect obstacles below the drone using an ultrasonic sensor, and decide whether the drone can land safely. If the battery is critical and the landing area is blocked, the system should make the drone hover, trigger an alert, and search for a safer nearby landing spot.

This aligns with SDG 9: Industry, Innovation and Infrastructure, because it proposes a low-cost safety add-on that can improve reliability for drone-based delivery, agriculture, surveillance, and other industrial use cases.

## Current Scope

For now, only the software implementation is in scope.

The Review 1 version should focus on building and demonstrating the logic through simulation, test inputs, logs, and clean module structure. Real drone hardware integration can come later after the software logic is stable.

In scope for now:

- Battery monitoring logic using simulated or MAVLink-style telemetry data
- Obstacle distance monitoring using simulated ultrasonic sensor readings
- Emergency decision logic for critical battery and blocked landing zone
- Safe landing state flow: monitor, hover, scan, alert, land or hold
- Basic logging for test results
- Simple command-line or lightweight local dashboard for demonstration

Out of scope for now:

- Full real-world autonomous flight testing
- Paid cloud services
- Advanced computer vision or AI-based landing zone detection
- Production-level safety certification
- Complex mobile app development

## Core Requirements From The PPT

- Monitor battery voltage or battery percentage in real time through Pixhawk telemetry.
- Detect obstacles below the drone using an ultrasonic sensor during descent.
- Trigger automated hover and alert behavior when critical thresholds are reached.
- Use a critical battery threshold of around 20 percent.
- Treat an obstacle closer than around 1.5 meters below the drone as unsafe.
- If an obstacle blocks the landing zone, search for a safer nearby spot.
- If a safe landing zone is found, execute a safe landing action.
- If no safe landing zone is available, hold or hover and continue alerting.
- Keep the system low-cost and suitable for student implementation.

## Suggested Student-Friendly Tech Stack

All technologies below are free or have free/open-source options suitable for student development.

- Language: Python 3.11+
- Drone communication library: pymavlink, open-source
- Simulation and test data: Python scripts with JSON or CSV input files
- Embedded logic reference: Arduino IDE or PlatformIO, both free
- Local dashboard option: Streamlit, free and open-source
- Testing: pytest, free and open-source
- Data logging: CSV or SQLite, both free
- Version control: Git and GitHub free student/public repository
- Documentation: Markdown

Avoid paid cloud APIs, paid databases, proprietary drone SDKs, and services that require a subscription for the Review 1 implementation.

## Simple Project Architecture

```text
AutoLandrone Software
│
├── Telemetry Input Layer
│   ├── Reads battery percentage from simulated data
│   └── Later can connect to Pixhawk through MAVLink
│
├── Sensor Input Layer
│   ├── Reads downward obstacle distance from simulated data
│   └── Later can connect to HC-SR04 through ESP32 or Arduino
│
├── Safety Decision Engine
│   ├── Checks battery threshold
│   ├── Checks obstacle distance threshold
│   ├── Applies simple filtering or hysteresis to avoid false triggers
│   └── Selects the next action
│
├── Landing Controller
│   ├── MONITOR
│   ├── HOVER
│   ├── SCAN_FOR_CLEAR_ZONE
│   ├── LAND
│   └── HOLD_AND_ALERT
│
├── Alert Module
│   ├── Simulates buzzer alert in software
│   └── Later can trigger a physical buzzer
│
├── Logger
│   ├── Records battery, distance, state, and action
│   └── Saves test runs for review/demo evidence
│
└── Demo Interface
    ├── CLI simulation output
    └── Optional Streamlit dashboard
```

## Main Modules

### 1. Telemetry Module

Purpose: Provide battery data to the system.

For Review 1, use simulated battery values from a CSV, JSON file, or generated test sequence. Keep the code structure ready for MAVLink integration later.

Example outputs:

- battery_percent
- voltage
- timestamp

### 2. Obstacle Sensor Module

Purpose: Provide the distance between the drone and the surface or obstacle below it.

For Review 1, simulate ultrasonic sensor readings. The system should treat distance below 1.5 meters as unsafe for landing.

Example outputs:

- distance_meters
- reading_valid
- timestamp

### 3. Safety Decision Engine

Purpose: Decide whether the drone should continue monitoring, hover, scan, land, or hold with alert.

Basic decision rules:

- If battery is above 20 percent, keep monitoring.
- If battery is below 20 percent and distance is clear, start landing.
- If battery is below 20 percent and obstacle distance is below 1.5 meters, hover and scan.
- If scan finds a clear zone, land.
- If scan does not find a clear zone, hold and alert.

### 4. Landing State Controller

Purpose: Manage the emergency landing flow as a simple state machine.

Suggested states:

- MONITOR
- EMERGENCY_TRIGGERED
- HOVER
- SCAN_FOR_CLEAR_ZONE
- LANDING
- HOLD_AND_ALERT

For Review 1, the controller can print or log actions instead of sending real commands to a drone.

### 5. Alert Module

Purpose: Notify that emergency landing mode has started or that no safe landing zone is available.

For Review 1, simulate the buzzer with console output or dashboard status. Hardware buzzer control can be added later.

### 6. Logger and Test Report Module

Purpose: Save evidence for review and debugging.

Log at least:

- timestamp
- battery percentage
- obstacle distance
- current state
- selected action
- reason for action

## Suggested Folder Structure

```text
autolandrone/
│
├── README.md
├── requirements.txt
├── data/
│   └── sample_test_inputs.csv
├── src/
│   ├── main.py
│   ├── config.py
│   ├── telemetry.py
│   ├── obstacle_sensor.py
│   ├── decision_engine.py
│   ├── landing_controller.py
│   ├── alert.py
│   └── logger.py
├── tests/
│   ├── test_decision_engine.py
│   └── test_landing_controller.py
└── docs/
    └── review1_notes.md
```

## Review 1 Implementation Direction

Build the project as a software prototype first.

Start with a Python simulation that runs multiple emergency landing scenarios:

- Normal battery, no emergency
- Battery below 20 percent with clear landing zone
- Battery below 20 percent with obstacle detected
- Obstacle detected first, then clear zone found
- Obstacle detected and no clear zone found

The output should clearly show the system state and selected action for each scenario. A local Streamlit dashboard can be added only if time permits. The command-line simulation and logs are enough for Review 1.

## Expected Review 1 Output

By the end of Review 1, the project should have:

- A working software simulation of the emergency landing logic
- Clean modular code structure
- Configurable thresholds for battery and obstacle distance
- Test scenarios that prove the decision logic works
- Logs or screenshots that can be used in the project review
- Documentation explaining how the software maps to the proposed hardware system

## Claude Code Build Instruction

Use this document as the initial project reference. Build a simple Python-based software prototype for AutoLandrone. Keep the implementation modular and easy to explain. Do not add major features beyond the PPT requirements. Focus on the emergency landing decision flow, simulated telemetry, simulated obstacle readings, state transitions, logs, and basic tests.

The goal is a clean Review 1 prototype, not a production drone system.
