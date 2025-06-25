import time
import logging
from enum import Enum  # If Direction enum is used here
from components.traffic_light import TrafficLight
from logic.direction import Direction
# from detection.direction import Direction  # Assuming you defined Direction enum elsewhere

logger = logging.getLogger(__name__)



class DecisionModule:
    """
    Processes perception data and makes traffic control decisions
    """
    def __init__(self, traffic_lights):
        self.traffic_lights = traffic_lights  # Dictionary of direction -> TrafficLight
        self.current_green = Direction.NORTH  # Start with North as green
        self.min_green_time = 20  # Minimum green time in seconds
        self.yellow_time = 3  # Yellow light duration in seconds
        self.last_switch_time = time.time()
        self.emergency_override = False
        self.emergency_direction = None
        self.accident_detected = False
        self.accident_location = None
        self.max_green_time = 120  # Maximum green time in seconds
        
    def process_perception_data(self, vehicle_counts, emergency_detected, emergency_direction, 
                               accident_detected, accident_location):
        """
        Process perception data and decide on traffic light changes
        """
        current_time = time.time()
        time_since_switch = current_time - self.last_switch_time
        
        # Update internal state
        if emergency_detected:
            self.emergency_override = True
            self.emergency_direction = emergency_direction
            logger.warning(f"Emergency vehicle detected in {emergency_direction.name} direction")
            
        if accident_detected:
            self.accident_detected = True
            self.accident_location = accident_location
            logger.critical(f"Accident detected in {accident_location.name} direction")
        
        # Decision logic
        should_switch = False
        next_green = self.current_green
        
        # Handle emergency vehicle with highest priority
        if self.emergency_override:
            if self.current_green != self.emergency_direction:
                should_switch = True
                next_green = self.emergency_direction
            # Reset after emergency vehicle has likely passed
            if time_since_switch > 60:  # 1 minute timeout for emergency
                self.emergency_override = False
                self.emergency_direction = None
                
        # Regular traffic flow logic
        elif not should_switch and time_since_switch >= self.min_green_time:
            # Find direction with highest vehicle count that isn't current green
            max_count = -1
            max_direction = None
            
            for direction, count in vehicle_counts.items():
                if direction != self.current_green and count > max_count:
                    max_count = count
                    max_direction = direction
            
            # Switch if another direction has significantly more vehicles
            # or if maximum green time exceeded
            current_count = vehicle_counts[self.current_green]
            if (max_count > current_count * 1.5 or 
                time_since_switch >= self.max_green_time):
                should_switch = True
                next_green = max_direction
        
        # Execute switch if needed
        if should_switch:
            self._switch_lights(next_green)
            
        return self.current_green
    
    def _switch_lights(self, new_green):
        """Handle the transition to a new green direction"""
        # First, set current green to yellow
        self.traffic_lights[self.current_green].set_yellow()
        time.sleep(self.yellow_time)
        
        # Then set all to red briefly
        for light in self.traffic_lights.values():
            light.set_red()
        time.sleep(1)
        
        # Set new direction to green
        self.traffic_lights[new_green].set_green()
        
        # Update state
        self.current_green = new_green
        self.last_switch_time = time.time()
        logger.info(f"Switched green light to {new_green.name} direction")
        
    def initialize_lights(self):
        """Set initial traffic light state"""
        # All red first
        for light in self.traffic_lights.values():
            light.set_red()
        time.sleep(1)
        
        # Set initial direction to green
        self.traffic_lights[self.current_green].set_green()
        logger.info(f"Initialized with {self.current_green.name} direction as green")
