import sys
import types
# --- Mock GPIO as a module (must be before any imports) ---
MockGPIOModule = types.ModuleType('RPi.GPIO')
setattr(MockGPIOModule, 'BCM', 'BCM')
setattr(MockGPIOModule, 'OUT', 'OUT')
setattr(MockGPIOModule, 'HIGH', 1)
setattr(MockGPIOModule, 'LOW', 0)
setattr(MockGPIOModule, 'setmode', lambda mode: None)
setattr(MockGPIOModule, 'setup', lambda pin, mode: None)
setattr(MockGPIOModule, 'output', lambda pin, value: None)
setattr(MockGPIOModule, 'cleanup', lambda: None)
sys.modules['RPi.GPIO'] = MockGPIOModule

import logging
import random
import time
import threading
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from enum import Enum

# Mock Camera
class MockVideoCapture:
    def __init__(self, port):
        self.port = port
        self.opened = True
    def isOpened(self):
        return self.opened
    def read(self):
        return True, f"frame_from_camera_{self.port}"
    def release(self):
        self.opened = False

cv2 = types.SimpleNamespace()
cv2.VideoCapture = MockVideoCapture

# Mock VisionModelClient
class MockVisionModelClient:
    def __init__(self, api_key):
        self.api_key = api_key
    def analyze_frame(self, frame, direction):
        responses = [
            f"5 cars, no emergency vehicles, light traffic, no accident",
            f"12 vehicles, ambulance detected, heavy traffic, no accident",
            f"3 cars, no emergency vehicles, moderate traffic, accident detected: collision",
            f"15 vehicles, no emergency vehicles, heavy traffic, no accident",
        ]
        return random.choice(responses)

from logic.direction import Direction
from components.traffic_lights import TrafficLight
from detection.vehicle_counter import VehicleCounter
from detection.accident import AccidentDetector
from detection.emergency import EmergencyDetector
from logic.alert_system import AlertSystem
from logic.decision import DecisionModule

class MockTrafficLight(TrafficLight):
    def setup(self):
        pass
    def set_red(self):
        pass
    def set_yellow(self):
        pass
    def set_green(self):
        pass
    def turn_off(self):
        pass

# Thread-safe storage for simulation logs
from collections import deque
simulation_logs = deque(maxlen=100)

class SimulatedTrafficSystem:
    def __init__(self):
        self.traffic_lights = {
            Direction.NORTH: MockTrafficLight(2, 3, 4),
            Direction.EAST: MockTrafficLight(17, 27, 22),
            Direction.SOUTH: MockTrafficLight(10, 9, 11),
            Direction.WEST: MockTrafficLight(5, 6, 13)
        }
        for light in self.traffic_lights.values():
            light.setup()
        self.vision_client = MockVisionModelClient(api_key="test")
        self.vehicle_counter = VehicleCounter()
        self.emergency_detector = EmergencyDetector()
        self.accident_detector = AccidentDetector()
        self.decision_module = DecisionModule(self.traffic_lights)
        self.alert_system = None

    def simulate_event(self, direction):
        frame = f"dummy_frame_{direction.name}"
        vision_response = self.vision_client.analyze_frame(frame, direction)
        log = {
            "direction": direction.name,
            "vision_response": vision_response,
            "alerts": [],
            "vehicle_count": None
        }
        if self.accident_detector.detect_accident(frame, vision_response):
            log["alerts"].append(f"Accident detected in {direction.name}")
        if self.emergency_detector.detect_emergency_vehicle(frame, vision_response):
            log["alerts"].append(f"Emergency vehicle detected in {direction.name}")
        vehicle_count = self.vehicle_counter.extract_count(vision_response)
        log["vehicle_count"] = vehicle_count
        if vehicle_count >= 10:
            log["alerts"].append(f"Congestion detected in {direction.name}")
        return log

    def run_simulation(self, cycles=100, delay=1):
        for i in range(cycles):
            for direction in Direction:
                log = self.simulate_event(direction)
                simulation_logs.appendleft({"cycle": i+1, **log})
            time.sleep(delay)

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/logs')
def logs():
    return jsonify({"logs": list(simulation_logs)})

# Start simulation in background thread
def start_simulation():
    sim = SimulatedTrafficSystem()
    t = threading.Thread(target=sim.run_simulation, kwargs={"cycles":1000, "delay":1}, daemon=True)
    t.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_simulation()
    app.run(debug=True, port=8000) 