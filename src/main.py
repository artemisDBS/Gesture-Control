"""
Main Application Module
Integrates all components to provide real-time gesture mapping functionality for the MVP.
"""

import cv2
import time
import sys
import os
from typing import Optional, Dict, Any
import logging

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from input_capture import HandCapture
from gesture_detection import GestureDetector
from command_executor import CommandExecutor
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GestureMapper:
    """Main application class that integrates all gesture mapping components."""
    
    def __init__(self, config_path: str = "config/gestures.json"):
        """
        Initialize the gesture mapper application.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.running = False
        
        # Initialize components
        try:
            self.config_manager = ConfigManager(config_path)
            self.hand_capture = HandCapture()
            self.gesture_detector = GestureDetector(self.config_manager.get_config())
            self.command_executor = CommandExecutor(self.config_manager.get_mappings())
            
            logger.info("Gesture mapper initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize gesture mapper: {str(e)}")
            raise
    
    def run(self):
        """Main application loop."""
        logger.info("Starting gesture mapper...")
        logger.info("Press 'q' to quit, 'r' to reload config, 'h' to show help")
        
        self.running = True
        frame_count = 0
        start_time = time.time()
        
        try:
            while self.running:
                # Read frame from webcam
                success, frame = self.hand_capture.read_frame()
                if not success:
                    logger.warning("Failed to read frame from webcam")
                    continue
                
                # Get hand landmarks
                landmarks = self.hand_capture.get_landmarks(frame)
                
                if landmarks:
                    # Process landmarks
                    self._process_landmarks(landmarks, frame)
                else:
                    # No hand detected
                    self._draw_no_hand_message(frame)
                
                # Draw debug information
                self._draw_debug_info(frame, frame_count, start_time)
                
                # Display the frame
                cv2.imshow('Gesture Mapper MVP', frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.running = False
                elif key == ord('r'):
                    self._reload_config()
                elif key == ord('h'):
                    self._show_help()
                
                frame_count += 1
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
        finally:
            self.cleanup()
    
    def _process_landmarks(self, landmarks: list, frame):
        """Process detected hand landmarks and execute gestures."""
        try:
            # Normalize landmarks based on configuration
            normalized_landmarks = self.gesture_detector.normalize_keypoints(landmarks)
            
            # Detect gesture
            gesture_name = self.gesture_detector.detect_gesture(normalized_landmarks)
            
            if gesture_name:
                # Get analogue value if applicable
                analogue_value = self.gesture_detector.get_analogue_value(
                    normalized_landmarks, gesture_name
                )
                
                # Execute command
                success = self.command_executor.execute_command(gesture_name, analogue_value)
                
                # Draw gesture detection on frame
                self._draw_gesture_detection(frame, gesture_name, success, analogue_value)
                
                # Log detection
                if success:
                    logger.info(f"Gesture detected: {gesture_name} (analogue: {analogue_value})")
                else:
                    logger.warning(f"Failed to execute command for gesture: {gesture_name}")
            else:
                # Draw landmarks for debugging
                self._draw_landmarks(frame, landmarks)
        
        except Exception as e:
            logger.error(f"Error processing landmarks: {str(e)}")
    
    def _draw_landmarks(self, frame, landmarks):
        """Draw hand landmarks on the frame."""
        try:
            # Draw keypoint numbers and connections
            for i, landmark in enumerate(landmarks):
                x = int(landmark['x'] * frame.shape[1])
                y = int(landmark['y'] * frame.shape[0])
                
                # Draw keypoint number
                cv2.putText(frame, str(i), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.3, (0, 255, 0), 1)
                
                # Draw keypoint circle
                cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
            
            # Draw some key connections for debugging
            connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
                (0, 5), (5, 6), (6, 7), (7, 8),  # Index
                (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
                (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
                (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
            ]
            
            for start_idx, end_idx in connections:
                if start_idx < len(landmarks) and end_idx < len(landmarks):
                    start_point = landmarks[start_idx]
                    end_point = landmarks[end_idx]
                    
                    start_x = int(start_point['x'] * frame.shape[1])
                    start_y = int(start_point['y'] * frame.shape[0])
                    end_x = int(end_point['x'] * frame.shape[1])
                    end_y = int(end_point['y'] * frame.shape[0])
                    
                    cv2.line(frame, (start_x, start_y), (end_x, end_y), (255, 0, 0), 1)
        
        except Exception as e:
            logger.error(f"Error drawing landmarks: {str(e)}")
    
    def _draw_gesture_detection(self, frame, gesture_name: str, success: bool, analogue_value: Optional[float]):
        """Draw gesture detection information on the frame."""
        try:
            # Draw gesture name
            color = (0, 255, 0) if success else (0, 0, 255)
            cv2.putText(frame, f"Gesture: {gesture_name}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # Draw analogue value if available
            if analogue_value is not None:
                cv2.putText(frame, f"Value: {analogue_value:.2f}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Draw status
            status = "SUCCESS" if success else "FAILED"
            status_color = (0, 255, 0) if success else (0, 0, 255)
            cv2.putText(frame, f"Status: {status}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        except Exception as e:
            logger.error(f"Error drawing gesture detection: {str(e)}")
    
    def _draw_no_hand_message(self, frame):
        """Draw message when no hand is detected."""
        try:
            cv2.putText(frame, "No hand detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "Show your hand to the camera", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        except Exception as e:
            logger.error(f"Error drawing no hand message: {str(e)}")
    
    def _draw_debug_info(self, frame, frame_count: int, start_time: float):
        """Draw debug information on the frame."""
        try:
            # Calculate FPS
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            # Draw FPS
            cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 120, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Draw frame count
            cv2.putText(frame, f"Frame: {frame_count}", (frame.shape[1] - 120, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Draw controls
            cv2.putText(frame, "q: quit, r: reload, h: help", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        except Exception as e:
            logger.error(f"Error drawing debug info: {str(e)}")
    
    def _reload_config(self):
        """Reload configuration from file."""
        try:
            logger.info("Reloading configuration...")
            
            # Reload config
            self.config_manager.load_config()
            
            # Update components with new config
            new_config = self.config_manager.get_config()
            self.gesture_detector = GestureDetector(new_config)
            self.command_executor.update_mappings(new_config.get('mappings', {}))
            
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Error reloading configuration: {str(e)}")
    
    def _show_help(self):
        """Show help information."""
        help_text = """
Gesture Mapper MVP - Help

Controls:
- q: Quit application
- r: Reload configuration
- h: Show this help

Available Gestures:
"""
        
        # Get current gestures
        gestures = self.config_manager.get_gestures()
        for gesture in gestures:
            help_text += f"- {gesture['name']}\n"
        
        help_text += "\nConfiguration file: " + self.config_path
        
        # Display help in a new window
        cv2.namedWindow('Help', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Help', 600, 400)
        
        # Create help image
        help_img = self._create_help_image(help_text)
        cv2.imshow('Help', help_img)
        
        logger.info("Help window displayed")
    
    def _create_help_image(self, help_text: str):
        """Create an image with help text."""
        # Create a white background
        img = np.ones((400, 600, 3), dtype=np.uint8) * 255
        
        # Split text into lines
        lines = help_text.strip().split('\n')
        
        # Draw each line
        y = 30
        for line in lines:
            if line.strip():
                cv2.putText(img, line.strip(), (20, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            y += 20
        
        return img
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        
        try:
            if hasattr(self, 'hand_capture'):
                self.hand_capture.release()
            
            cv2.destroyAllWindows()
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def main():
    """Main entry point."""
    try:
        # Create and run gesture mapper
        mapper = GestureMapper()
        mapper.run()
        
    except Exception as e:
        logger.error(f"Failed to start gesture mapper: {str(e)}")
        print(f"Error: {str(e)}")
        print("Please check that your webcam is connected and accessible.")
        return 1
    
    return 0


if __name__ == "__main__":
    # Import numpy here to avoid import issues
    import numpy as np
    
    exit_code = main()
    sys.exit(exit_code)
