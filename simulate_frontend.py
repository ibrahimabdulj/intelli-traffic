import sys
import types
import logging
import random
import time
import threading
import math
from flask import Flask, jsonify
from flask_cors import CORS
from enum import Enum
from collections import deque

# --- Mock GPIO as a module ---
# This part remains the same to avoid errors with RPi.GPIO imports
MockGPIOModule = types.ModuleType('RPi.GPIO')
sys.modules['RPi.GPIO'] = MockGPIOModule

# --- Mock Dependencies (Not used in the new dynamic simulation but kept for context) ---
from logic.direction import Direction
from components.traffic_lights import TrafficLight
# The following imports are now effectively replaced by the new simulation logic
# from detection.vehicle_counter import VehicleCounter
# from detection.accident import AccidentDetector
# from detection.emergency import EmergencyDetector
# from logic.alert_system import AlertSystem
# from logic.decision import DecisionModule

# A simplified mock to stand in for the real TrafficLight class
class MockTrafficLight(TrafficLight):
    def setup(self): pass
    def set_red(self): pass
    def set_yellow(self): pass
    def set_green(self): pass
    def turn_off(self): pass

# Thread-safe storage for simulation logs
simulation_logs = deque(maxlen=200) # Increased maxlen for better history

# --- New Dynamic Simulation Core ---

class LaneState:
    """Holds the dynamic state for a single traffic lane."""
    def __init__(self, direction):
        self.direction = direction
        self.vehicle_count = 0
        self.has_accident = False
        self.accident_timer = 0  # How many cycles the accident lasts
        self.has_emergency = False
        self.emergency_timer = 0 # How many cycles the emergency vehicle is present

class SimulatedTrafficSystem:
    """
    A more dynamic and realistic traffic simulation backend.
    """
    # --- Simulation Tuning Parameters ---
    # Probabilities are per-cycle, per-lane
    ACCIDENT_PROBABILITY = 0.005  # 0.5% chance of an accident
    EMERGENCY_PROBABILITY = 0.01 # 1% chance of an emergency vehicle
    
    # Durations are in simulation cycles
    ACCIDENT_DURATION = 25      # An accident blocks a lane for 25 cycles
    EMERGENCY_DURATION = 5      # An emergency vehicle passes in 5 cycles
    
    # Traffic flow parameters
    MAX_VEHICLES_NORMAL = 40    # The peak number of cars during "rush hour"
    MAX_VEHICLES_ACCIDENT = 60  # The number of cars during an accident jam
    SIMULATION_DELAY_SECONDS = 2 # Slower simulation for more realistic pacing

    def __init__(self):
        # Initialize a state for each direction
        self.lanes = {direction: LaneState(direction) for direction in Direction}
        self.cycle_count = 0

    def _update_lane_state(self, lane: LaneState):
        """Calculates the state of a lane for the current cycle."""
        # 1. Handle event timers (count down and clear events)
        if lane.accident_timer > 0:
            lane.accident_timer -= 1
            if lane.accident_timer == 0:
                lane.has_accident = False
        
        if lane.emergency_timer > 0:
            lane.emergency_timer -= 1
            if lane.emergency_timer == 0:
                lane.has_emergency = False

        # 2. Probabilistically start new events
        # An accident can only happen if there isn't one already
        if not lane.has_accident and random.random() < self.ACCIDENT_PROBABILITY:
            lane.has_accident = True
            lane.accident_timer = self.ACCIDENT_DURATION
            logging.warning(f"New accident generated in {lane.direction.name}!")

        # An emergency vehicle can appear anytime
        if not lane.has_emergency and random.random() < self.EMERGENCY_PROBABILITY:
            lane.has_emergency = True
            lane.emergency_timer = self.EMERGENCY_DURATION

        # 3. Calculate base traffic volume
        if lane.has_accident:
            # If there's an accident, traffic piles up dramatically
            lane.vehicle_count = random.randint(self.MAX_VEHICLES_ACCIDENT - 10, self.MAX_VEHICLES_ACCIDENT)
        else:
            # Simulate a "time of day" traffic flow using a sine wave
            # The sine wave creates a smooth peak and trough (e.g., rush hour)
            # We add some random noise to make it less predictable
            base_traffic_wave = (math.sin(self.cycle_count / 50 + lane.direction.value) + 1) / 2 # a value between 0 and 1
            vehicle_target = int(base_traffic_wave * self.MAX_VEHICLES_NORMAL)
            noise = random.randint(-3, 3)
            lane.vehicle_count = max(0, vehicle_target + noise)
            
    def _generate_vision_response(self, lane: LaneState) -> str:
        """Creates a descriptive string based on the current lane state."""
        parts = []
        
        # Vehicle count and traffic level
        count_str = f"{lane.vehicle_count} vehicles"
        if lane.vehicle_count > self.MAX_VEHICLES_NORMAL * 0.75:
            traffic_level = "heavy traffic"
        elif lane.vehicle_count > self.MAX_VEHICLES_NORMAL * 0.4:
            traffic_level = "moderate traffic"
        else:
            traffic_level = "light traffic"
        parts.extend([count_str, traffic_level])

        # Emergency vehicle status
        parts.append("ambulance detected" if lane.has_emergency else "no emergency vehicles")
        
        # Accident status
        parts.append("accident detected" if lane.has_accident else "no accident")
        
        return ", ".join(parts)

    def run_simulation(self):
        """The main simulation loop."""
        logging.info("Starting dynamic traffic simulation...")
        while True:
            self.cycle_count += 1
            all_logs_for_cycle = []
            
            for direction in Direction:
                lane = self.lanes[direction]
                
                # Update the state of the lane based on our dynamic rules
                self._update_lane_state(lane)
                
                # Generate a descriptive response string from that state
                vision_response = self._generate_vision_response(lane)

                # Generate alerts based on the state
                alerts = []
                if lane.has_accident:
                    alerts.append(f"Accident detected in {direction.name}")
                if lane.has_emergency:
                    alerts.append(f"Emergency vehicle detected in {direction.name}")
                if lane.vehicle_count > self.MAX_VEHICLES_NORMAL * 0.8:
                     alerts.append(f"Congestion detected in {direction.name}")
                
                # Create the log entry
                log = {
                    "cycle": self.cycle_count,
                    "direction": direction.name,
                    "vision_response": vision_response,
                    "vehicle_count": lane.vehicle_count,
                    "alerts": alerts,
                    "is_accident": lane.has_accident,
                    "is_emergency": lane.has_emergency
                }
                simulation_logs.appendleft(log)
            
            time.sleep(self.SIMULATION_DELAY_SECONDS)

# --- Flask App ---
app = Flask(__name__)
CORS(app)

@app.route('/logs')
def logs():
    return jsonify({"logs": list(simulation_logs)})

@app.route('/')
def index():
    # A simple status page to confirm the server is running
    return "<h1>Traffic Simulation Backend is Running</h1><p>Access logs at the <a href='/logs'>/logs</a> endpoint.</p>"

def start_simulation():
    sim = SimulatedTrafficSystem()
    # Run the simulation in a daemon thread so it stops when the main app stops
    t = threading.Thread(target=sim.run_simulation, daemon=True)
    t.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    start_simulation()
    # Set use_reloader=False to prevent the simulation from running twice in debug mode
    app.run(debug=True, port=8000, use_reloader=False)