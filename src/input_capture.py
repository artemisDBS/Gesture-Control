"""
Input Capture Module
Handles webcam feed and MediaPipe hand detection for the gesture mapper MVP.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Optional, Tuple


class HandCapture:
    """Captures hand keypoints from webcam using MediaPipe."""
    
    def __init__(self, camera_index: int = 0, max_hands: int = 1):
        self.cap = cv2.VideoCapture(camera_index)
        self.mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Check if camera opened successfully
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")
    
    def get_landmarks(self, frame: np.ndarray) -> Optional[List[Dict[str, float]]]:
        """
        Extract hand landmarks from a frame.
        
        Returns:
            List of 21 landmarks with x, y, z coordinates, or None if no hand detected
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.mp_hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            # Get the first hand's landmarks
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # Convert to our format
            landmarks = []
            for landmark in hand_landmarks.landmark:
                landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z
                })
            
            return landmarks
        
        return None
    
    def draw_landmarks(self, frame: np.ndarray, landmarks: List[Dict[str, float]]) -> np.ndarray:
        """Draw hand landmarks and connections on the frame for debugging."""
        # Convert our format back to MediaPipe format for drawing
        mp_landmarks = mp.solutions.hands.HandLandmark
        hand_landmarks = mp.solutions.hands.HandLandmark
        
        # Create a temporary MediaPipe landmarks object for drawing
        temp_landmarks = mp.solutions.hands.HandLandmark()
        
        # Draw the landmarks
        self.mp_drawing.draw_landmarks(
            frame,
            temp_landmarks,
            mp.solutions.hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style()
        )
        
        # Draw keypoint numbers for debugging
        for i, landmark in enumerate(landmarks):
            x = int(landmark['x'] * frame.shape[1])
            y = int(landmark['y'] * frame.shape[0])
            cv2.putText(frame, str(i), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return frame
    
    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """Read a frame from the webcam."""
        return self.cap.read()
    
    def release(self):
        """Release the camera and MediaPipe resources."""
        self.cap.release()
        self.mp_hands.close()
        cv2.destroyAllWindows()


def test_capture():
    """Test function to verify hand detection is working."""
    capture = HandCapture()
    
    try:
        while True:
            success, frame = capture.read_frame()
            if not success:
                print("Failed to read frame")
                break
            
            # Get landmarks
            landmarks = capture.get_landmarks(frame)
            
            if landmarks:
                print(f"Hand detected! Landmarks: {len(landmarks)} points")
                # Draw landmarks on frame
                frame = capture.draw_landmarks(frame, landmarks)
            
            # Display the frame
            cv2.imshow('Hand Detection Test', frame)
            
            # Break on 'q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        capture.release()


if __name__ == "__main__":
    test_capture()
