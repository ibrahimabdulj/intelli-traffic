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
from collections import defaultdict
from datetime import datetime
from flask import Flask, Response
from detection.emergency import EmergencyDetector
from detection.accident import AccidentDetector
from detection.vehicle_counter import VehicleCounter
from vision.client import VisionModelClient
from logic.alert_system import AlertSystem
from logic.decision import DecisionModule
from logic.direction import Direction
from components.traffic_lights import TrafficLight

# Configuration
SUPABASE_URL = "https://fxvslxkvsqydgqtgzqlg.supabase.com"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ4dnNseGt2c3F5ZGdxdGd6cWxnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkwNDE2MzYsImV4cCI6MjA2NDYxNzYzNn0.YbwRTt9ADEzpKHOUL28s3mkKJM4GdaqAJ4P5DtyYqqg"
SUPABASE_TABLE_NAME = "traffic_alerts"

CONGESTION_THRESHOLD = 10  # Example threshold for congestion
JUNCTIONS = {
    Direction.NORTH: 0,
    Direction.EAST: 1,
    Direction.SOUTH: 2,
    Direction.WEST: 3
}

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Livefeed via Flask
app = Flask(__name__)
camera = cv2.VideoCapture(0)

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Alert sending
def send_traffic_alert(event_type, direction, confidence=None):
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    data = {
        "event_type": event_type,
        "direction": direction.name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if confidence is not None:
        data["confidence"] = confidence

    try:
        response = requests.post(f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE_NAME}", json=data, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            logger.info(f"Alert sent successfully: {data}")
            return True
        else:
            logger.warning(f"Failed to send alert: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception occurred while sending alert: {e}")
        return False

# Event logging

def log_event_to_supabase(event_type, direction, vehicle_count=None):
    try:
        data = {
            "event_type": event_type,
            "direction": direction.name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if vehicle_count is not None:
            data["vehicle_count"] = vehicle_count

        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json",
        }

        response = requests.post(f"{SUPABASE_URL}/rest/v1/traffic_events", headers=headers, json=data)

        if response.status_code not in [200, 201]:
            logger.warning(f"Failed to log event to Supabase: {response.text}")
    except Exception as e:
        logger.error(f"Exception logging event to Supabase: {e}")

# Camera rotation
SERVO_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def rotate_camera(angle):
    duty = angle / 18 + 2
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

# Main system initialization
class IntelligentTrafficSystem:
    def __init__(self, camera_ports, api_key, gsm_port=None):
        GPIO.setmode(GPIO.BCM)
        self.cameras = {}
        for direction, port in camera_ports.items():
            cap = cv2.VideoCapture(port)
            if cap.isOpened():
                self.cameras[direction] = cap
            else:
                logger.error(f"Failed to open camera for {direction.name}")

        self.traffic_lights = {
            Direction.NORTH: TrafficLight(2, 3, 4),
            Direction.EAST: TrafficLight(17, 27, 22),
            Direction.SOUTH: TrafficLight(10, 9, 11),
            Direction.WEST: TrafficLight(5, 6, 13)
        }

        for light in self.traffic_lights.values():
            light.setup()

        self.vision_client = VisionModelClient(api_key)
        self.vehicle_counter = VehicleCounter()
        self.emergency_detector = EmergencyDetector()
        self.accident_detector = AccidentDetector()
        self.decision_module = DecisionModule(self.traffic_lights)
        self.alert_system = AlertSystem(gsm_port)

        self.frame_queues = {direction: queue.Queue(maxsize=1) for direction in Direction}
        self.result_queues = {direction: queue.Queue(maxsize=1) for direction in Direction}
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()
        for cap in self.cameras.values():
            cap.release()
        for light in self.traffic_lights.values():
            light.turn_off()
        GPIO.cleanup()
        logger.info("System shut down cleanly")

# Sample traffic monitoring loop (customize as needed)
def monitor_traffic():
    traffic_system = IntelligentTrafficSystem(JUNCTIONS, SUPABASE_API_KEY, gsm_port="/dev/ttyUSB0")
    while True:
        for direction, camera_id in JUNCTIONS.items():
            cap = cv2.VideoCapture(camera_id)
            success, frame = cap.read()
            if not success:
                continue
            vision_response = traffic_system.vision_client.analyze_frame(frame, direction)
            if vision_response:
                if traffic_system.accident_detector.detect_accident(frame, vision_response):
                    send_traffic_alert("accident", direction)
                    log_event_to_supabase("accident", direction)
                if traffic_system.emergency_detector.detect_emergency_vehicle(frame, vision_response):
                    send_traffic_alert("emergency", direction)
                    log_event_to_supabase("emergency", direction)
                vehicle_count = traffic_system.vehicle_counter.count_vehicles(frame)
                if vehicle_count >= CONGESTION_THRESHOLD:
                    send_traffic_alert("congestion", direction)
                    log_event_to_supabase("congestion", direction, vehicle_count)
            cap.release()
        time.sleep(5)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Interrupted. Cleaning up...")
        GPIO.cleanup()
