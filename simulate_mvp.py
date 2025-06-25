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
from enum import Enum

# Mock Camera
class MockVideoCapture:
    def __init__(self, port):
        self.port = port
        self.opened = True
    def isOpened(self):
        return self.opened
    def read(self):
        # Return True and a dummy frame (could be any object)
        return True, f"frame_from_camera_{self.port}"
    def release(self):
        self.opened = False

# Patch cv2.VideoCapture
try:
    import cv2
except ImportError:
    cv2 = types.SimpleNamespace()
cv2.VideoCapture = MockVideoCapture

# Mock VisionModelClient
class MockVisionModelClient:
    def __init__(self, api_key):
        self.api_key = api_key
    def analyze_frame(self, frame, direction):
        # Simulate different responses based on random choice
        responses = [
            f"5 cars, no emergency vehicles, light traffic, no accident", # Normal
            f"12 vehicles, ambulance detected, heavy traffic, no accident", # Emergency
            f"3 cars, no emergency vehicles, moderate traffic, accident detected: collision", # Accident
            f"15 vehicles, no emergency vehicles, heavy traffic, no accident", # Congestion
        ]
        return random.choice(responses)

# --- Import/Mock Project Classes ---
from logic.direction import Direction
from components.traffic_lights import TrafficLight
from detection.vehicle_counter import VehicleCounter
from detection.accident import AccidentDetector
from detection.emergency import EmergencyDetector
from logic.alert_system import AlertSystem
from logic.decision import DecisionModule

# --- Patch TrafficLight to log instead of GPIO ---
class MockTrafficLight(TrafficLight):
    def setup(self):
        logging.info(f"[MockTrafficLight] Setup pins: {self.red_pin}, {self.yellow_pin}, {self.green_pin}")
    def set_red(self):
        logging.info(f"[MockTrafficLight] RED ON for pins: {self.red_pin}")
    def set_yellow(self):
        logging.info(f"[MockTrafficLight] YELLOW ON for pins: {self.yellow_pin}")
    def set_green(self):
        logging.info(f"[MockTrafficLight] GREEN ON for pins: {self.green_pin}")
    def turn_off(self):
        logging.info(f"[MockTrafficLight] ALL OFF for pins: {self.red_pin}, {self.yellow_pin}, {self.green_pin}")

# --- Simulation System ---
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
        self.alert_system = None  # Not needed for simulation

    def simulate_event(self, direction):
        # Simulate getting a frame and vision response
        frame = f"dummy_frame_{direction.name}"
        vision_response = self.vision_client.analyze_frame(frame, direction)
        print(f"\n[SIM] Direction: {direction.name}")
        print(f"[SIM] Vision Response: {vision_response}")
        # Accident detection
        if self.accident_detector.detect_accident(frame, vision_response):
            print(f"[ALERT] Accident detected in {direction.name}")
        # Emergency detection
        if self.emergency_detector.detect_emergency_vehicle(frame, vision_response):
            print(f"[ALERT] Emergency vehicle detected in {direction.name}")
        # Vehicle counting and congestion
        vehicle_count = self.vehicle_counter.extract_count(vision_response)
        print(f"[INFO] Vehicle count in {direction.name}: {vehicle_count}")
        if vehicle_count >= 10:
            print(f"[ALERT] Congestion detected in {direction.name}")

    def run_simulation(self, cycles=3):
        for i in range(cycles):
            print(f"\n=== Simulation Cycle {i+1} ===")
            for direction in Direction:
                self.simulate_event(direction)
            time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sim = SimulatedTrafficSystem()
    sim.run_simulation(cycles=5) 