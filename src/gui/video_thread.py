"""
Contains the VideoThread class for handling camera input and processing
in a separate thread to keep the GUI responsive.
"""
import cv2
import time
from PyQt5.QtCore import QThread, pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QImage

# --- Drawing Constants ---
# Colors are in BGR format for OpenCV
SELECTED_COLOR = (50, 255, 255)  # Yellow
LANDMARK_COLOR = (50, 250, 50)  # Green
CLICK_VIZ_COLOR = (0, 0, 255)    # Red
TEXT_COLOR = (200, 100, 100) # Light Blue

# Gesture Editor Colors
DISTANCE_COLOR = (255, 0, 0)     # Blue for distance conditions
ANGLE_COLOR = (255, 0, 255)      # Magenta for angle conditions
BOTH_COLOR = (0, 255, 255)       # Cyan for landmarks used in both

LANDMARK_RADIUS = 5
CLICK_VIZ_RADIUS = 8
CLICK_VIZ_THICKNESS = 2
FONT = cv2.FONT_HERSHEY_COMPLEX
FONT_SCALE = 0.4
FONT_THICKNESS = 1


class VideoThread(QThread):
    """
    A separate worker thread to handle all camera and model processing.
    This prevents the main GUI from freezing by offloading heavy tasks.

    Signals:
        change_pixmap_signal: Emits the processed video frame as a QImage.
        gesture_detected_signal: Emits the name of any detected gesture.
        landmarks_signal: Emits both raw and normalized landmark data.
    """
    change_pixmap_signal = pyqtSignal(QImage)
    gesture_detected_signal = pyqtSignal(str)
    landmarks_signal = pyqtSignal(list, list)

    def __init__(self, hand_capture, gesture_detector, parent=None):
        super().__init__(parent)
        self._run_flag = True
        self.hand_capture = hand_capture
        self.gesture_detector = gesture_detector

        # State variables updated by the main thread
        self.selected_points = []
        self.click_viz_pos = None
        self.click_viz_end_time = 0
        
        # Gesture Editor state
        self.editing_conditions = []

    def run(self):
        """
        The main loop for the video thread. Continuously captures frames,
        processes them, and emits signals with the results.
        """
        while self._run_flag:
            success, frame = self.hand_capture.read_frame()
            if not success:
                self.msleep(10)  # Wait a bit if frame reading fails
                continue

            # --- Core Processing ---
            raw_landmarks = self.hand_capture.get_landmarks(frame)
            gesture_name = ""
            normalized_landmarks = []

            if raw_landmarks:
                # Normalize landmarks for gesture detection
                normalized_landmarks = self.gesture_detector.normalize_keypoints(raw_landmarks)
                # Check for a gesture using the normalized data
                gesture_name = self.gesture_detector.detect_gesture(normalized_landmarks) or ""
                # Draw visualizations on the frame using the raw data
                self.draw_landmarks(frame, raw_landmarks, self.selected_points)

            # --- Emit Signals to Main GUI Thread ---
            self.gesture_detected_signal.emit(gesture_name)
            self.landmarks_signal.emit(raw_landmarks or [], normalized_landmarks or [])

            # Convert the OpenCV frame (BGR) to a QImage (RGB) for display
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_format_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

            self.change_pixmap_signal.emit(qt_format_image)

    def draw_landmarks(self, frame, landmarks, selected_points):
        """Draws circles and numbers for each landmark on the frame."""
        # Determine landmark roles for color coding
        landmark_roles = self._get_landmark_roles()
        
        for i, landmark in enumerate(landmarks):
            x = int(landmark['x'] * frame.shape[1])
            y = int(landmark['y'] * frame.shape[0])

            # Determine color based on role and selection
            if i in selected_points:
                color = SELECTED_COLOR
            elif i in landmark_roles:
                role = landmark_roles[i]
                if 'distance' in role and 'angle' in role:
                    color = BOTH_COLOR
                elif 'distance' in role:
                    color = DISTANCE_COLOR
                elif 'angle' in role:
                    color = ANGLE_COLOR
                else:
                    color = LANDMARK_COLOR
            else:
                color = LANDMARK_COLOR

            cv2.circle(frame, (x, y), LANDMARK_RADIUS, color, -1)
            cv2.putText(frame, str(i), (x + 8, y + 8),
                        FONT, FONT_SCALE, TEXT_COLOR, FONT_THICKNESS)

    def _get_landmark_roles(self):
        """Determines the role of each landmark based on editing conditions."""
        landmark_roles = {}
        
        for condition in self.editing_conditions:
            condition_type = condition.get('type', '')
            points = condition.get('points', [])
            
            for point_idx in points:
                if point_idx not in landmark_roles:
                    landmark_roles[point_idx] = set()
                landmark_roles[point_idx].add(condition_type)
        
        return landmark_roles

    @pyqtSlot(list)
    def update_selected_points(self, points: list):
        """Receives the latest list of selected points from the main thread."""
        self.selected_points = points

    @pyqtSlot(tuple)
    def set_click_visualization(self, norm_pos: tuple):
        """Receives a normalized click position to visualize for a short duration."""
        self.click_viz_pos = norm_pos
        self.click_viz_end_time = time.time() + 0.5  # Visualize for 0.5 seconds

    @pyqtSlot(list)
    def update_editing_conditions(self, conditions: list):
        """Receives the list of conditions for the gesture being edited."""
        self.editing_conditions = conditions

    def stop(self):
        """Sets the flag to gracefully stop the thread's run loop."""
        self._run_flag = False
        self.wait()

