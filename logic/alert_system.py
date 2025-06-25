import serial
import time
import logging
from datetime import datetime
from logic.direction import Direction
import requests
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class AlertSystem:
    """Handles traffic alerts for accident, emergency, congestion etc."""

    def __init__(self, gsm_port=None):
        self.gsm_port = gsm_port
        self.gsm_connected = False
        self.emergency_contacts = ["+2348107471505"]

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_api_key = os.getenv("SUPABASE_API_KEY")
        self.supabase_table = os.getenv("SUPABASE_TABLE_NAME", "traffic_alerts")

        if gsm_port:
            try:
                self.gsm = serial.Serial(gsm_port, 9600, timeout=1)
                self.gsm_connected = True
                logger.info("Connected to GSM module")
            except Exception as e:
                logger.error(f"Failed to connect to GSM module: {e}")

    def send_traffic_alert(self, event_type, direction, confidence=None):
        """
        Unified method to handle alerts.
        Logs all alerts to Supabase and sends SMS only for 'accident' or 'emergency'.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"ALERT: {event_type.upper()} detected at {direction.name} direction. Time: {timestamp}"
        if confidence is not None:
            message += f" (Confidence: {confidence:.2f})"

        # 1. Log to Supabase
        self._log_to_supabase(event_type, direction.name, timestamp, confidence)

        # 2. Send SMS only for accident or emergency
        if event_type in ["accident", "emergency"] and self.gsm_connected:
            try:
                for contact in self.emergency_contacts:
                    self._send_sms(contact, message)
                logger.info(f"{event_type.capitalize()} SMS alert sent to {len(self.emergency_contacts)} contacts")
            except Exception as e:
                logger.error(f"Failed to send {event_type} SMS: {e}")
        elif event_type in ["accident", "emergency"]:
            logger.warning(f"GSM not connected. Would have sent: {message}")
        else:
            logger.info(f"{event_type.capitalize()} alert logged to Supabase only.")

    def _send_sms(self, number, message):
        """Send SMS using GSM module."""
        self.gsm.write(b'AT+CMGF=1\r')
        time.sleep(0.5)
        self.gsm.write(f'AT+CMGS="{number}"\r'.encode())
        time.sleep(0.5)
        self.gsm.write(message.encode() + b'\x1A')  # Ctrl+Z to send
        time.sleep(2)

    def _log_to_supabase(self, event_type, direction, timestamp, confidence):
        """Send alert data to Supabase table."""
        url = f"{self.supabase_url}/rest/v1/{self.supabase_table}"
        headers = {
            "apikey": self.supabase_api_key,
            "Authorization": f"Bearer {self.supabase_api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        data = {
            "event_type": event_type,
            "direction": direction,
            "timestamp": timestamp,
            "confidence": confidence
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                logger.info("Alert logged to Supabase successfully.")
            else:
                logger.error(f"Failed to log alert to Supabase: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Exception logging to Supabase: {e}")
