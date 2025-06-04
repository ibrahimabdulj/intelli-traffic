# Intelligent Traffic Management System
# Core modules for an AI-powered traffic control system with accident detection

import cv2
import numpy as np
import time
import requests
import threading
import queue
import logging
import base64
import json
import serial
import RPi.GPIO as GPIO
from enum import Enum
from collections import defaultdict
from datetime import datetime

import requests
import datetime

# This function will send traffic alerts to your web backend
def send_traffic_alert(alert_type, direction):
    url = "https://your-backend-domain.com/api/traffic"  # REPLACE with your actual backend endpoint

    data = {
        "alert_type": alert_type,       # e.g., "accident", "congestion", or "emergency"
        "direction": direction          # e.g., "north", "south", "east", "west"
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"[{datetime.datetime.now()}] Alert sent: {alert_type} in {direction}")
        else:
            print(f"[ERROR] Failed to send alert: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[EXCEPTION] Error sending alert: {e}")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

class TrafficLight:
    """Controls traffic light signals for a single direction"""
    def __init__(self, red_pin, yellow_pin, green_pin):
        self.red_pin = red_pin
        self.yellow_pin = yellow_pin
        self.green_pin = green_pin
        
    def setup(self):
        """Initialize GPIO pins"""
        GPIO.setup(self.red_pin, GPIO.OUT)
        GPIO.setup(self.yellow_pin, GPIO.OUT)
        GPIO.setup(self.green_pin, GPIO.OUT)
        
    def set_red(self):
        """Turn on red light, turn off others"""
        GPIO.output(self.red_pin, GPIO.HIGH)
        GPIO.output(self.yellow_pin, GPIO.LOW)
        GPIO.output(self.green_pin, GPIO.LOW)
        
    def set_yellow(self):
        """Turn on yellow light, turn off others"""
        GPIO.output(self.red_pin, GPIO.LOW)
        GPIO.output(self.yellow_pin, GPIO.HIGH)
        GPIO.output(self.green_pin, GPIO.LOW)
        
    def set_green(self):
        """Turn on green light, turn off others"""
        GPIO.output(self.red_pin, GPIO.LOW)
        GPIO.output(self.yellow_pin, GPIO.LOW)
        GPIO.output(self.green_pin, GPIO.HIGH)
        
    def turn_off(self):
        """Turn off all lights"""
        GPIO.output(self.red_pin, GPIO.LOW)
        GPIO.output(self.yellow_pin, GPIO.LOW)
        GPIO.output(self.green_pin, GPIO.LOW)

class EmergencyDetector:
    """Detects emergency vehicles using vision model"""
    def __init__(self, confidence_threshold=0.7):
        self.confidence_threshold = confidence_threshold
        
    def detect_emergency_vehicle(self, frame, vision_response):
        """
        Analyzes vision model response to detect emergency vehicles
        Returns True if emergency vehicle is detected with confidence above threshold
        """
        if not vision_response:
            return False
            
        # Check if the model mentions emergency vehicles or ambulances
        emergency_terms = ['ambulance', 'emergency vehicle', 'police car', 'fire truck']
        
        for term in emergency_terms:
            if term in vision_response.lower():
                # Extract confidence if available
                confidence_pattern = f"{term}.*?(\d+(?:\.\d+)?)%"
                import re
                confidence_match = re.search(confidence_pattern, vision_response.lower())
                
                if confidence_match:
                    confidence = float(confidence_match.group(1)) / 100.0
                    if confidence >= self.confidence_threshold:
                        logger.info(f"Emergency vehicle detected: {term} with {confidence:.2f} confidence")
                        return True
                elif term in vision_response.lower():
                    # If no specific confidence, but term is mentioned prominently
                    logger.info(f"Emergency vehicle detected: {term}")
                    return True
                    
        return False

class AccidentDetector:
    """Detects potential accidents using vision model"""
    def __init__(self, confidence_threshold=0.6):
        self.confidence_threshold = confidence_threshold
        self.accident_history = []
        self.history_length = 5  # Number of frames to keep in history
        
    def detect_accident(self, frame, vision_response):
        """
        Analyzes vision model response to detect potential accidents
        Returns True if accident indicators are detected
        """
        if not vision_response:
            return False
            
        # Check if the model mentions accident indicators
        accident_terms = ['collision', 'crash', 'accident', 'vehicles colliding', 
                         'damaged vehicle', 'overturned vehicle', 'debris on road']
        
        is_accident = False
        for term in accident_terms:
            if term in vision_response.lower():
                is_accident = True
                logger.warning(f"Potential accident detected: {term}")
                break
                
        # Add to history and check for consistent detection
        self.accident_history.append(is_accident)
        if len(self.accident_history) > self.history_length:
            self.accident_history.pop(0)
            
        # Only report accident if detected multiple times (reduces false positives)
        if sum(self.accident_history) >= 3:  # At least 3 detections in history
            logger.critical("ACCIDENT CONFIRMED - Alert triggered")
            return True
            
        return False

class VehicleCounter:
    """Counts vehicles in each direction using vision model"""
    def __init__(self):
        self.vehicle_counts = {direction: 0 for direction in Direction}
        self.count_history = {direction: [] for direction in Direction}
        self.history_length = 3  # Number of frames to keep for smoothing
        
    def extract_count(self, vision_response):
        """Extract vehicle count from vision model response"""
        if not vision_response:
            return 0
            
        # Look for patterns like "5 cars", "10 vehicles", etc.
        import re
        count_patterns = [
            r"(\d+)\s+(?:cars|vehicles|automobiles)",
            r"(?:count|total of|counted)\s+(\d+)",
            r"(\d+)\s+(?:cars|vehicles|automobiles)\s+(?:detected|identified|found|present)"
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, vision_response.lower())
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
                    
        # If no specific count is found, estimate from the text
        if "no cars" in vision_response.lower() or "empty" in vision_response.lower():
            return 0
        elif "few cars" in vision_response.lower() or "light traffic" in vision_response.lower():
            return 2
        elif "moderate" in vision_response.lower():
            return 5
        elif "heavy traffic" in vision_response.lower() or "congested" in vision_response.lower():
            return 10
            
        # Default fallback
        return 0
        
    def update_count(self, direction, vision_response):
        """Update the vehicle count for a given direction"""
        count = self.extract_count(vision_response)
        
        # Add to history
        self.count_history[direction].append(count)
        if len(self.count_history[direction]) > self.history_length:
            self.count_history[direction].pop(0)
            
        # Use average for smoother counts
        self.vehicle_counts[direction] = sum(self.count_history[direction]) / len(self.count_history[direction])
        return self.vehicle_counts[direction]
        
    def get_count(self, direction):
        """Get the current count for a direction"""
        return self.vehicle_counts[direction]

class VisionModelClient:
    """Client to interact with a Vision Language Model API"""
    def __init__(self, api_url=None, api_key=None, model="gpt-4o"):
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        self.api_key = api_key
        self.model = model
        
    def encode_image(self, image_path):
        """Encode image to base64 for API transmission"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
            
    def encode_frame(self, frame):
        """Encode CV2 frame to base64 for API transmission"""
        _, buffer = cv2.imencode(".jpg", frame)
        return base64.b64encode(buffer).decode('utf-8')
    
    def analyze_frame(self, frame, direction):
        """
        Send frame to vision model API and get analysis
        Returns the model's textual response
        """
        base64_image = self.encode_frame(frame)
        
        # Prepare prompt based on direction
        prompt = f"""
        Analyze this traffic camera image showing the {direction.name} direction.
        
        1. Count all vehicles visible in the image.
        2. Check for emergency vehicles (ambulances, police cars, fire trucks).
        3. Look for any signs of accidents or hazardous conditions.
        
        Provide a structured response with:
        - Total vehicle count
        - Presence of emergency vehicles (yes/no with confidence)
        - Traffic density assessment (light/moderate/heavy)
        - Any accident indicators
        """
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error querying vision model: {e}")
            return None

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

class AlertSystem:
    """Handles emergency alerts for accidents"""
    def __init__(self, gsm_port=None):
        self.gsm_port = gsm_port
        self.gsm_connected = False
        self.emergency_contacts = ["+2348107471505"]  # Default emergency contact
        
        # Try to connect to GSM module if port provided
        if gsm_port:
            try:
                self.gsm = serial.Serial(gsm_port, 9600, timeout=1)
                self.gsm_connected = True
                logger.info("Connected to GSM module")
            except Exception as e:
                logger.error(f"Failed to connect to GSM module: {e}")
                
    def send_emergency_alert(self, accident_location, image_path=None):
        """Send emergency alert via GSM module"""
        message = f"ALERT: Traffic accident detected at intersection, {accident_location.name} direction. Time: {datetime.now().strftime('%H:%M:%S')}"
        
        if self.gsm_connected:
            try:
                # Send SMS to emergency contacts
                for contact in self.emergency_contacts:
                    self._send_sms(contact, message)
                logger.info(f"Emergency alert sent to {len(self.emergency_contacts)} contacts")
                return True
            except Exception as e:
                logger.error(f"Failed to send emergency alert: {e}")
        else:
            # Fallback: just log the alert
            logger.critical(f"EMERGENCY ALERT: {message}")
            
        return False
        
    def _send_sms(self, number, message):
        """Send SMS using GSM module"""
        self.gsm.write(b'AT+CMGF=1\r')  # Set to text mode
        time.sleep(0.5)
        self.gsm.write(f'AT+CMGS="{number}"\r'.encode())
        time.sleep(0.5)
        self.gsm.write(message.encode() + b'\x1A')  # Message and Ctrl+Z to send
        time.sleep(2)  # Wait for sending

class IntelligentTrafficSystem:
    """Main system integrating all components"""
    def __init__(self, camera_ports, api_key, gsm_port=None):
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Camera setup
        self.cameras = {}
        for direction, port in camera_ports.items():
            try:
                cap = cv2.VideoCapture(port)
                if not cap.isOpened():
                    logger.error(f"Failed to open camera for {direction.name} direction")
                    continue
                self.cameras[direction] = cap
                logger.info(f"Camera initialized for {direction.name} direction")
            except Exception as e:
                logger.error(f"Error initializing camera for {direction.name}: {e}")
        
        # Traffic light setup
        self.traffic_lights = {
            Direction.NORTH: TrafficLight(red_pin=2, yellow_pin=3, green_pin=4),
            Direction.EAST: TrafficLight(red_pin=17, yellow_pin=27, green_pin=22),
            Direction.SOUTH: TrafficLight(red_pin=10, yellow_pin=9, green_pin=11),
            Direction.WEST: TrafficLight(red_pin=5, yellow_pin=6, green_pin=13)
        }
        
        for light in self.traffic_lights.values():
            light.setup()
        
        # Component initialization
        self.vision_client = VisionModelClient(api_key=api_key)
        self.vehicle_counter = VehicleCounter()
        self.emergency_detector = EmergencyDetector()
        self.accident_detector = AccidentDetector()
        self.decision_module = DecisionModule(self.traffic_lights)
        self.alert_system = AlertSystem(gsm_port)
        
        # Initialize processing queues and threads
        self.frame_queues = {direction: queue.Queue(maxsize=1) for direction in Direction}
        self.result_queues = {direction: queue.Queue(maxsize=1) for direction in Direction}
        self.stop_event = threading.Event()
        
        # Analysis results
        self.vehicle_counts = {direction: 0 for direction in Direction}
        self.emergency_detected = False
        self.emergency_direction = None
        self.accident_detected = False
        self.accident_location = None
        
        # Stats and monitoring
        self.frame_counts = {direction: 0 for direction in Direction}
        self.processing_times = {direction: [] for direction in Direction}
        self.system_start_time = time.time()
        
    def start(self):
        """Start the intelligent traffic system"""
        logger.info("Starting Intelligent Traffic System")
        
        # Initialize traffic lights
        self.decision_module.initialize_lights()
        
        # Start processing threads for each direction
        threads = []
        for direction in Direction:
            if direction in self.cameras:
                thread = threading.Thread(
                    target=self._process_direction, 
                    args=(direction,)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
                
        # Start decision thread
        decision_thread = threading.Thread(target=self._run_decision_loop)
        decision_thread.daemon = True
        decision_thread.start()
        threads.append(decision_thread)
        
        try:
            # Main capture loop
            while not self.stop_event.is_set():
                for direction, cap in self.cameras.items():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning(f"Failed to read from camera {direction.name}")
                        continue
                    
                    # Update the frame queue (non-blocking)
                    try:
                        # Clear the queue first to always use latest frame
                        while not self.frame_queues[direction].empty():
                            self.frame_queues[direction].get_nowait()
                        self.frame_queues[direction].put_nowait(frame)
                    except queue.Full:
                        pass  # Skip frame if queue is full
                        
                time.sleep(0.05)  # Small sleep to prevent CPU hogging
                
        except KeyboardInterrupt:
            logger.info("System shutdown initiated")
        finally:
            self.stop()
            for thread in threads:
                thread.join(timeout=1.0)
                
    def stop(self):
        """Safely shut down the system"""
        self.stop_event.set()
        
        # Release cameras
        for cap in self.cameras.values():
            cap.release()
            
        # Turn off all traffic lights
        for light in self.traffic_lights.values():
            light.turn_off()
            
        # Clean up GPIO
        GPIO.cleanup()
        
        logger.info("System successfully shut down")
        
    def _process_direction(self, direction):
        """Process frames for a specific direction"""
        logger.info(f"Started processing thread for {direction.name} direction")
        
        while not self.stop_event.is_set():
            try:
                # Get latest frame
                frame = self.frame_queues[direction].get(timeout=1.0)
                start_time = time.time()
                
                # Process with vision model
                vision_response = self.vision_client.analyze_frame(frame, direction)
                
                if vision_response:
                    # Update vehicle count
                    count = self.vehicle_counter.update_count(direction, vision_response)
                    
                    # Check for emergency vehicles
                    is_emergency = self.emergency_detector.detect_emergency_vehicle(frame, vision_response)
                    
                    # Check for accidents
                    is_accident = self.accident_detector.detect_accident(frame, vision_response)
                    
                    # Put results in queue
                    result = {
                        'count': count,
                        'emergency': is_emergency,
                        'accident': is_accident,
                        'timestamp': time.time()
                    }
                    
                    # Update result queue (non-blocking)
                    try:
                        while not self.result_queues[direction].empty():
                            self.result_queues[direction].get_nowait()
                        self.result_queues[direction].put_nowait(result)
                    except queue.Full:
                        pass
                    
                    # Update stats
                    self.frame_counts[direction] += 1
                    processing_time = time.time() - start_time
                    self.processing_times[direction].append(processing_time)
                    
                    # Log occasionally
                    if self.frame_counts[direction] % 50 == 0:
                        avg_time = sum(self.processing_times[direction][-20:]) / min(20, len(self.processing_times[direction]))
                        logger.info(f"{direction.name}: Processed {self.frame_counts[direction]} frames. " 
                                   f"Last count: {count:.1f}, Avg processing time: {avg_time:.2f}s")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in processing thread for {direction.name}: {e}")
                time.sleep(1)  # Prevent rapid error loops
                
    def _run_decision_loop(self):
        """Run the decision loop for traffic control"""
        logger.info("Started decision module thread")
        
        while not self.stop_event.is_set():
            try:
                # Get latest results from all directions
                updated_vehicle_counts = {}
                self.emergency_detected = False
                self.accident_detected = False
                
                for direction in Direction:
                    try:
                        if not self.result_queues[direction].empty():
                            result = self.result_queues[direction].get_nowait()
                            updated_vehicle_counts[direction] = result['count']
                            
                            # Check for emergency vehicles
                            if result['emergency']:
                                self.emergency_detected = True
                                self.emergency_direction = direction
                                
                            # Check for accidents
                            if result['accident']:
                                self.accident_detected = True
                                self.accident_location = direction
                                
                                # Send alert if accident detected
                                self.alert_system.send_emergency_alert(direction)
                    except queue.Empty:
                        # Use previous count if no new data
                        updated_vehicle_counts[direction] = self.vehicle_counts.get(direction, 0)
                
                # Update vehicle counts
                self.vehicle_counts = updated_vehicle_counts
                
                # Make decision
                current_green = self.decision_module.process_perception_data(
                    self.vehicle_counts,
                    self.emergency_detected,
                    self.emergency_direction,
                    self.accident_detected,
                    self.accident_location
                )
                
                # Log status occasionally
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    runtime = time.time() - self.system_start_time
                    hours, remainder = divmod(runtime, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    logger.info(f"System runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
                    logger.info(f"Current green: {current_green.name}, Vehicle counts: {self.vehicle_counts}")
                
                time.sleep(1)  # Check decision every second
                
            except Exception as e:
                logger.error(f"Error in decision loop: {e}")
                time.sleep(1)  # Prevent rapid error loops

if __name__ == "__main__":
    # Camera port configuration
    camera_ports = {
        Direction.NORTH: 0,  # First camera (built-in or USB)
        Direction.EAST: 2,   # Additional USB cameras
        Direction.SOUTH: 4,
        Direction.WEST: 6
    }
    
    # Replace with your actual API key
    api_key = "your_vision_model_api_key_here"
    
    # GSM module port (if available)
    gsm_port = "/dev/ttyUSB0"  # Typical port for USB GSM modem
    
    # Create and start the system
    system = IntelligentTrafficSystem(camera_ports, api_key, gsm_port)
    system.start()