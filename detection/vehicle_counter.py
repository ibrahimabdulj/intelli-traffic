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

        
    def reset(self):
    self.vehicle_counts = {direction: 0 for direction in Direction}
    self.count_history = {direction: deque(maxlen=self.history_length) for direction in Direction}
