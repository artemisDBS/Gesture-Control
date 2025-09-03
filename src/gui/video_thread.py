"""
Contains the VideoThread class for handling camera input and processing
in a separate thread to keep the GUI responsive.
"""
import cv2
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage

class VideoThread(QThread):
    """Thread to capture video, process landmarks, and detect gestures."""
    change_pixmap_signal = pyqtSignal(QImage)
    gesture_detected_signal = pyqtSignal(str)
    landmarks_signal = pyqtSignal(list)

    def __init__(self, hand_capture, gesture_detector, gui_instance):
        super().__init__()
        self._run_flag = True
        self.hand_capture = hand_capture
        self.gesture_detector = gesture_detector
        self.gui = gui_instance # To access selected_points for drawing

    def run(self):
        """Capture video and emit frames, gestures, and landmarks."""
        while self._run_flag:
            success, frame = self.hand_capture.read_frame()
            if not success:
                self.msleep(10) # Wait a bit if frame reading fails
                continue

            landmarks = self.hand_capture.get_landmarks(frame)
            gesture_name = ""

            if landmarks:
                self.landmarks_signal.emit(landmarks)
                normalized_landmarks = self.gesture_detector.normalize_keypoints(landmarks)
                gesture_name = self.gesture_detector.detect_gesture(normalized_landmarks)

                # Draw landmarks on the frame
                for i, landmark in enumerate(landmarks):
                    x = int(landmark['x'] * frame.shape[1])
                    y = int(landmark['y'] * frame.shape[0])
                    # Highlight selected landmarks
                    if i in self.gui.selected_points:
                        cv2.circle(frame, (x, y), 6, (0, 255, 255), -1) # Yellow
                        cv2.circle(frame, (x, y), 3, (0, 0, 0), -1)      # Black dot
                    else:
                        cv2.circle(frame, (x, y), 3, (0, 255, 0), -1) # Green

            if gesture_name:
                self.gesture_detected_signal.emit(gesture_name)
                cv2.putText(frame, f"Gesture: {gesture_name}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                self.gesture_detected_signal.emit("")

            # Convert frame to QImage for display
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_format_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            scaled_image = qt_format_image.scaled(640, 480, Qt.KeepAspectRatio)
            self.change_pixmap_signal.emit(scaled_image)

    def stop(self):
        """Sets run flag to False and waits for thread to finish."""
        self._run_flag = False
        self.wait()
