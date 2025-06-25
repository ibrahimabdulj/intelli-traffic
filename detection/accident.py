import logging
logger = logging.getLogger(__name__)

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