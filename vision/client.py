import base64
import cv2
import requests
import logging

logger = logging.getLogger(__name__)



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