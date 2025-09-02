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
        self.config = config
        self.transformations = config.get('transformations', {})
        self.gesture_defs = config.get('gestures', [])
        
        # MediaPipe hand landmark indices
        self.WRIST = 0
        self.THUMB_TIP = 4
        self.INDEX_TIP = 8
        self.MIDDLE_FINGER_BASE = 9
        self.MIDDLE_FINGER_TIP = 12
    
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
                angle = self._calculate_angle(
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
        
        return min_dist < distance < max_dist
    
    def _check_angle_condition(self, landmarks: List[Dict[str, float]], condition: Dict) -> bool:
        """Check if angle between three points meets the condition."""
        points = condition.get('points', [])
        if len(points) != 3:
            return False
        
        point1_idx, point2_idx, point3_idx = points[0], points[1], points[2]
        if any(idx >= len(landmarks) for idx in [point1_idx, point2_idx, point3_idx]):
            return False
        
        angle = self._calculate_angle_three_points(
            landmarks[point1_idx],
            landmarks[point2_idx],
            landmarks[point3_idx]
        )
        
        min_angle = condition.get('min', float('-inf'))
        max_angle = condition.get('max', float('inf'))
        
        return min_angle < angle < max_angle
    
    def _check_position_condition(self, landmarks: List[Dict[str, float]], condition: Dict) -> bool:
        """Check if a point's position meets the condition."""
        point_idx = condition.get('point', 0)
        if point_idx >= len(landmarks):
            return False
        
        point = landmarks[point_idx]
        
        # Check x coordinate
        if 'x_min' in condition and point['x'] < condition['x_min']:
            return False
        if 'x_max' in condition and point['x'] > condition['x_max']:
            return False
        
        # Check y coordinate
        if 'y_min' in condition and point['y'] < condition['y_min']:
            return False
        if 'y_max' in condition and point['y'] > condition['y_max']:
            return False
        
        return True
    
    def _euclidean_distance(self, point1: Dict[str, float], point2: Dict[str, float]) -> float:
        """Calculate Euclidean distance between two 3D points."""
        dx = point1['x'] - point2['x']
        dy = point1['y'] - point2['y']
        dz = point1['z'] - point2['z']
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _calculate_angle(self, point1: Dict[str, float], point2: Dict[str, float]) -> float:
        """Calculate angle between two points relative to horizontal."""
        dx = point2['x'] - point1['x']
        dy = point2['y'] - point1['y']
        return math.atan2(dy, dx)
    
    def _calculate_angle_three_points(self, point1: Dict[str, float], 
                                    point2: Dict[str, float], 
                                    point3: Dict[str, float]) -> float:
        """Calculate angle at point2 between point1 and point3."""
        # Vector from point2 to point1
        v1x = point1['x'] - point2['x']
        v1y = point1['y'] - point2['y']
        
        # Vector from point2 to point3
        v2x = point3['x'] - point2['x']
        v2y = point3['y'] - point2['y']
        
        # Calculate angle using dot product
        dot_product = v1x * v2x + v1y * v2y
        mag1 = math.sqrt(v1x * v1x + v1y * v1y)
        mag2 = math.sqrt(v2x * v2x + v2y * v2y)
        
        if mag1 == 0 or mag2 == 0:
            return 0
        
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp to [-1, 1]
        
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
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
        Calculate analogue value for continuous gestures.
        
        Args:
            landmarks: Current hand landmarks
            gesture_name: Name of the detected gesture
            
        Returns:
            Analogue value (e.g., for volume control), or None if not applicable
        """
        # For MVP, implement simple analogue control based on finger position
        if gesture_name == "thumbs_up" and len(landmarks) > self.THUMB_TIP:
            # Use thumb tip Y position as analogue value
            # Lower Y = higher value (since Y increases downward in image coordinates)
            return 1.0 - landmarks[self.THUMB_TIP]['y']
        
        return None


def test_gesture_detection():
    """Test function to verify gesture detection logic."""
    # Sample config
    config = {
        "transformations": {
            "displacement_invariant": True,
            "scale_invariant": True,
            "rotation_invariant": False
        },
        "gestures": [
            {
                "name": "pinch",
                "conditions": [
                    {
                        "type": "distance",
                        "points": [4, 8],
                        "max": 0.05
                    }
                ]
            }
        ]
    }
    
    detector = GestureDetector(config)
    
    # Test with sample landmarks (pinch gesture)
    sample_landmarks = [
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Wrist
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Thumb base
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Thumb middle
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Thumb tip
        {'x': 0.48, 'y': 0.48, 'z': 0.0},  # Thumb tip (close to index)
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Index base
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Index middle
        {'x': 0.5, 'y': 0.5, 'z': 0.0},  # Index tip
        {'x': 0.49, 'y': 0.49, 'z': 0.0},  # Index tip (close to thumb)
        # ... add more points to make it 21 total
    ]
    
    # Pad to 21 points
    while len(sample_landmarks) < 21:
        sample_landmarks.append({'x': 0.5, 'y': 0.5, 'z': 0.0})
    
    # Test normalization
    normalized = detector.normalize_keypoints(sample_landmarks)
    print(f"Normalized landmarks: {len(normalized)} points")
    
    # Test gesture detection
    gesture = detector.detect_gesture(normalized)
    print(f"Detected gesture: {gesture}")
    
    # Test analogue value
    analogue_val = detector.get_analogue_value(normalized, "thumbs_up")
    print(f"Analogue value: {analogue_val}")


if __name__ == "__main__":
    test_gesture_detection()
