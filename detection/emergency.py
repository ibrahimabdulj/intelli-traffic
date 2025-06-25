import logging
logger = logging.getLogger(__name__)

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