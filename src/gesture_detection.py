"""
Gesture Detection Module
Handles keypoint normalization and gesture matching for the gesture mapper MVP.
"""

import numpy as np
import math
from typing import List, Dict, Optional, Tuple


class GestureDetector:
    """Detects gestures based on normalized hand keypoints."""
    
    def __init__(self, config: Dict):
        """Initializes the detector with a given configuration."""
        self.config = {}
        self.transformations = {}
        self.gesture_defs = []
        self.update_config(config) # Use the update method for initialization
        
        # MediaPipe hand landmark indices
        self.WRIST = 0
        self.THUMB_TIP = 4
        self.INDEX_TIP = 8
        self.MIDDLE_FINGER_BASE = 9
        self.MIDDLE_FINGER_TIP = 12

    def update_config(self, new_config: Dict):
        """
        Updates the detector's configuration with a new set of gestures and transformations.
        This is crucial for reloading configurations at runtime.
        """
        self.config = new_config
        self.transformations = self.config.get('transformations', {})
        self.gesture_defs = self.config.get('gestures', [])
        print(f"GestureDetector updated with {len(self.gesture_defs)} gestures.")
    
    def normalize_keypoints(self, landmarks: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Apply transformations to make gestures invariant to displacement, scale, and rotation.
        
        Args:
            landmarks: List of 21 landmarks with x, y, z coordinates
            
        Returns:
            Normalized landmarks
        """
        if not landmarks or len(landmarks) < 21:
            return landmarks
        
        normalized = landmarks.copy()
        
        # Displacement invariance: Center on wrist (point 0)
        if self.transformations.get('displacement_invariant', False):
            wrist = landmarks[self.WRIST]
            normalized = [
                {
                    'x': p['x'] - wrist['x'],
                    'y': p['y'] - wrist['y'],
                    'z': p['z'] - wrist['z']
                }
                for p in landmarks
            ]
        
        # Scale invariance: Normalize by hand size
        if self.transformations.get('scale_invariant', False):
            # Use distance from wrist to middle finger base as scale reference
            if len(normalized) > self.MIDDLE_FINGER_BASE:
                scale_factor = self._euclidean_distance(
                    normalized[self.WRIST], 
                    normalized[self.MIDDLE_FINGER_BASE]
                )
                
                if scale_factor > 0:
                    normalized = [
                        {
                            'x': p['x'] / scale_factor,
                            'y': p['y'] / scale_factor,
                            'z': p['z'] / scale_factor
                        }
                        for p in normalized
                    ]
        
        # Rotation invariance: Rotate so wrist-to-index is vertical
        if self.transformations.get('rotation_invariant', False):
            if len(normalized) > self.INDEX_TIP:
                # Calculate angle between wrist and index finger
                angle = self._calculate_angle_2d(
                    normalized[self.WRIST],
                    normalized[self.INDEX_TIP]
                )
                
                # Apply rotation to all points
                normalized = self._rotate_points(normalized, -angle)
        
        return normalized
    
    def detect_gesture(self, normalized_landmarks: List[Dict[str, float]]) -> Optional[str]:
        """
        Check if the normalized landmarks match any defined gestures.
        
        Args:
            normalized_landmarks: Normalized hand landmarks
            
        Returns:
            Name of detected gesture, or None if no match
        """
        if not normalized_landmarks or len(normalized_landmarks) < 21:
            return None
        
        for gesture in self.gesture_defs:
            if self._check_gesture_conditions(normalized_landmarks, gesture):
                return gesture['name']
        
        return None
    
    def _check_gesture_conditions(self, landmarks: List[Dict[str, float]], gesture: Dict) -> bool:
        """Check if landmarks satisfy all conditions for a gesture."""
        conditions = gesture.get('conditions', [])
        
        for condition in conditions:
            if not self._evaluate_condition(landmarks, condition):
                return False
        
        return True
    
    def _evaluate_condition(self, landmarks: List[Dict[str, float]], condition: Dict) -> bool:
        """Evaluate a single condition against the landmarks."""
        condition_type = condition.get('type')
        
        if condition_type == 'distance':
            return self._check_distance_condition(landmarks, condition)
        elif condition_type == 'angle':
            return self._check_angle_condition(landmarks, condition)
        elif condition_type == 'position':
            return self._check_position_condition(landmarks, condition)
        
        return False
    
    def _check_distance_condition(self, landmarks: List[Dict[str, float]], condition: Dict) -> bool:
        """Check if distance between two points meets the condition."""
        points = condition.get('points', [])
        if len(points) != 2:
            return False
        
        point1_idx, point2_idx = points[0], points[1]
        if point1_idx >= len(landmarks) or point2_idx >= len(landmarks):
            return False
        
        distance = self._euclidean_distance(landmarks[point1_idx], landmarks[point2_idx])
        
        min_dist = condition.get('min', float('-inf'))
        max_dist = condition.get('max', float('inf'))
        
        return min_dist <= distance <= max_dist
    
    def _check_angle_condition(self, landmarks: List[Dict[str, float]], condition: Dict) -> bool:
        """Check if angle between three points meets the condition."""
        points = condition.get('points', [])
        if len(points) != 3:
            return False
        
        p1_idx, p2_idx, p3_idx = points[0], points[1], points[2]
        if any(idx >= len(landmarks) for idx in [p1_idx, p2_idx, p3_idx]):
            return False
        
        angle = self._calculate_angle_three_points(
            landmarks[p1_idx],
            landmarks[p2_idx], # Vertex
            landmarks[p3_idx]
        )
        
        min_angle = condition.get('min', float('-inf'))
        max_angle = condition.get('max', float('inf'))
        
        return min_angle <= angle <= max_angle
    
    def _check_position_condition(self, landmarks: List[Dict[str, float]], condition: Dict) -> bool:
        """Check if a point's position meets the condition."""
        point_idx = condition.get('point', 0)
        if point_idx >= len(landmarks):
            return False
        
        point = landmarks[point_idx]
        
        # Check x coordinate
        if 'x_min' in condition and point['x'] < condition['x_min']: return False
        if 'x_max' in condition and point['x'] > condition['x_max']: return False
        
        # Check y coordinate
        if 'y_min' in condition and point['y'] < condition['y_min']: return False
        if 'y_max' in condition and point['y'] > condition['y_max']: return False
        
        return True
    
    def _euclidean_distance(self, point1: Dict[str, float], point2: Dict[str, float]) -> float:
        """Calculate Euclidean distance between two 3D points."""
        dx = point1['x'] - point2['x']
        dy = point1['y'] - point2['y']
        dz = point1['z'] - point2['z']
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _calculate_angle_2d(self, point1: Dict[str, float], point2: Dict[str, float]) -> float:
        """Calculate 2D angle between two points relative to horizontal."""
        dx = point2['x'] - point1['x']
        dy = point2['y'] - point1['y']
        return math.atan2(dy, dx)
    
    def _calculate_angle_three_points(self, p1: Dict[str, float], 
                                    p2: Dict[str, float], 
                                    p3: Dict[str, float]) -> float:
        """Calculate angle at p2 between p1 and p3 (in degrees)."""
        # Create vectors from the vertex p2
        v1 = {'x': p1['x'] - p2['x'], 'y': p1['y'] - p2['y']}
        v2 = {'x': p3['x'] - p2['x'], 'y': p3['y'] - p2['y']}
        
        # Dot product
        dot_product = v1['x'] * v2['x'] + v1['y'] * v2['y']
        
        # Magnitude
        mag1 = math.sqrt(v1['x']**2 + v1['y']**2)
        mag2 = math.sqrt(v2['x']**2 + v2['y']**2)
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        # Cosine of the angle
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle)) # Clamp to avoid domain errors
        
        angle_rad = math.acos(cos_angle)
        return math.degrees(angle_rad)
    
    def _rotate_points(self, landmarks: List[Dict[str, float]], angle: float) -> List[Dict[str, float]]:
        """Rotate all points around the origin by the given angle."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        rotated = []
        for point in landmarks:
            x, y = point['x'], point['y']
            rotated_x = x * cos_a - y * sin_a
            rotated_y = x * sin_a + y * cos_a
            
            rotated.append({
                'x': rotated_x,
                'y': rotated_y,
                'z': point['z']
            })
        
        return rotated
    
    def get_analogue_value(self, landmarks: List[Dict[str, float]], 
                          gesture_name: str) -> Optional[float]:
        """
        Calculate analogue value for continuous gestures. (Future enhancement)
        
        Args:
            landmarks: Current hand landmarks
            gesture_name: Name of the detected gesture
            
        Returns:
            Analogue value, or None if not applicable
        """
        # Placeholder for future implementation where analogue control
        # could be defined in the JSON configuration.
        return None

