import RPi.GPIO as GPIO
import time
import logging
from logic.direction import Direction  # Only if you're using direction.name

logger = logging.getLogger(__name__)


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
