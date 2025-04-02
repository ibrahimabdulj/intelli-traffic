# Intelligent Traffic Management System - Hardware Design

## System Overview

This document outlines the hardware components and circuit design required to implement the intelligent traffic management system based on computer vision and AI decision-making.

## Core Hardware Components

### 1. Computing Unit

**Raspberry Pi 4 (8GB RAM)** as the central processing unit:
- Provides sufficient computing power for basic image processing and system coordination
- Handles communication with vision model APIs
- Controls traffic lights and interfaces with all sensors
- Runs the Python-based decision module

**Specs:**
- 8GB RAM
- 64GB microSD card with Raspberry Pi OS
- 5V/3A power supply with proper heat management
- Ethernet connection for reliable internet access

### 2. Camera System

Four **Raspberry Pi High Quality Cameras** or equivalent USB cameras:
- Minimum 1080p resolution with good low-light performance
- Wide-angle lens (at least 120°) to capture the entire intersection
- Weather-resistant housing for outdoor deployment
- PoE (Power over Ethernet) capability for simpler wiring

**Camera Placement:**
- Mounted on poles at 3-4 meters height
- One camera for each direction (N, S, E, W)
- Angled to capture approaching traffic lanes
- Weatherproof enclosures with clear visibility

### 3. Traffic Light Control System

For each direction (4 total):
- 3 high-brightness LED arrays (Red, Yellow, Green)
- LED driver circuits with MOSFETs for high current handling
- Weatherproof LED housings
- Optoisolators for electrical isolation between controller and high-power LEDs

### 4. Communication Modules

**Network Communication:**
- Ethernet connection for reliable API communication
- 4G/LTE modem as backup internet connection
- Local Wi-Fi access point for maintenance

**Emergency Alert System:**
- SIM800L GSM/GPRS module
- SMA antenna for improved cellular reception
- SIM card with data plan for sending alerts

### 5. Power System

**Main Power:**
- 110V/220V AC to 12V DC converter (10A capacity)
- 12V to 5V DC-DC converters for Raspberry Pi and logic circuits
- Power distribution board with fuses for each component
- Surge protection on AC input

**Backup Power:**
- 12V, 20Ah deep-cycle battery
- Solar panel (optional, 50W)
- UPS circuit with automatic switchover
- Battery status monitoring circuit

### 6. Additional Sensors (Optional)

- PIR motion sensors for additional vehicle detection
- Acoustic sensors for emergency vehicle siren detection
- Weather sensors (temperature, humidity, rain) for environmental context
- Light sensor for adjusting LED brightness by time of day

## Circuit Design

### 1. Power Supply Circuit

```
AC Mains (110V/220V) → Circuit Breaker → AC-DC Converter (12V, 10A) → 
   ├── Battery Charging Circuit → 12V Battery
   ├── DC-DC Buck Converter (5V, 3A) → Raspberry Pi Power
   ├── LED Driver Circuits (12V)
   └── Sensor Power Distribution (5V/3.3V)
```

**Components:**
- Mean Well LRS-150-12 or equivalent AC-DC converter
- Buck converter module MP1584EN or equivalent
- TP4056 with protection circuit for battery charging
- Power distribution board with PTC fuses

### 2. LED Driver Circuit (Per Traffic Light)

Each direction requires 3 channels (R/Y/G) with the following circuit:

```
GPIO Pin → Optoisolator (4N35) → MOSFET Gate (IRLZ44N) → 
    LED Array → Current Limiting Resistor → Ground
```

**Components (per channel):**
- IRLZ44N Logic-Level MOSFET
- 4N35 Optoisolator
- 1kΩ Resistor (GPIO to Optoisolator input)
- 10kΩ Resistor (MOSFET gate pull-down)
- High-brightness LED array (12V)
- Power resistor for current limiting

### 3. GSM Communication Circuit

```
Raspberry Pi UART (TX/RX) → Level Shifter → SIM800L Module → Antenna
```

**Components:**
- SIM800L GSM/GPRS module
- 3.3V to 2.8V level shifter (if needed)
- Capacitor (1000μF) for stabilizing power spikes
- SMA antenna with cable

### 4. Camera Connection

For Raspberry Pi Camera:
```
Raspberry Pi CSI Port → Camera Module → Weatherproof Enclosure
```

For USB Cameras:
```
Raspberry Pi USB 3.0 Port → USB Extension (if needed) → USB Camera
```

### 5. Main Control Board Connections

The Raspberry Pi connects to peripheral devices as follows:

1. **GPIO Pin Assignments:**
   - Pins 2, 3, 4: North Traffic Light (R, Y, G)
   - Pins 17, 27, 22: East Traffic Light (R, Y, G)
   - Pins 10, 9, 11: South Traffic Light (R, Y, G)
   - Pins 5, 6, 13: West Traffic Light (R, Y, G)
   - Pins 14, 15: UART for GSM module (TX, RX)
   - Pin 23: System status LED
   - Pin 24: Alert buzzer output
   - Pin 25: Manual override button input
   - Pins