"""
PyQt GUI for the Gesture Mapper MVP.
Provides a desktop interface to view the camera feed and manage gestures.
"""

import sys
import cv2
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QFormLayout, QLineEdit, QMessageBox, QGroupBox,
                             QSplitter, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap

from input_capture import HandCapture
from config_manager import ConfigManager
from gesture_detection import GestureDetector
from command_executor import CommandExecutor


class VideoThread(QThread):
    """Thread to capture video and detect gestures."""
    change_pixmap_signal = pyqtSignal(QImage)
    gesture_detected_signal = pyqtSignal(str)

    def __init__(self, hand_capture, gesture_detector):
        super().__init__()
        self._run_flag = True
        self.hand_capture = hand_capture
        self.gesture_detector = gesture_detector

    def run(self):
        """Capture video and emit frames and gestures."""
        while self._run_flag:
            success, frame = self.hand_capture.read_frame()
            if not success:
                continue

            # Gesture detection
            landmarks = self.hand_capture.get_landmarks(frame)
            gesture_name = None
            if landmarks:
                normalized_landmarks = self.gesture_detector.normalize_keypoints(landmarks)
                gesture_name = self.gesture_detector.detect_gesture(normalized_landmarks)

                # Draw landmarks for debugging
                for i, landmark in enumerate(landmarks):
                    x = int(landmark['x'] * frame.shape[1])
                    y = int(landmark['y'] * frame.shape[0])
                    cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
                    cv2.putText(frame, str(i), (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                                0.3, (0, 255, 0), 1)

            if gesture_name:
                self.gesture_detected_signal.emit(gesture_name)
                cv2.putText(frame, f"Gesture: {gesture_name}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                self.gesture_detected_signal.emit("")


            # Convert frame to QImage
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            p = convert_to_qt_format.scaled(640, 480, Qt.KeepAspectRatio)
            self.change_pixmap_signal.emit(p)

    def stop(self):
        """Sets run flag to False and waits for thread to finish."""
        self._run_flag = False
        self.wait()


class GestureMapperGUI(QMainWindow):
    """Main window for the Gesture Mapper application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture Mapper")
        self.setGeometry(100, 100, 1280, 720)
        self.set_stylesheet()

        # --- Initialize Backend Components ---
        try:
            self.config_manager = ConfigManager(config_path="config/gestures.json")
            self.hand_capture = HandCapture()
            self.gesture_detector = GestureDetector(self.config_manager.get_config())
            self.command_executor = CommandExecutor(self.config_manager.get_mappings())
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize components: {e}")
            sys.exit(1)


        # --- Main Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(splitter)

        # --- Left Panel (Video and Status) ---
        left_widget = QWidget()
        self.left_panel = QVBoxLayout(left_widget)
        
        video_group = QGroupBox("Live Feed")
        video_layout = QVBoxLayout()
        self.video_label = QLabel(self)
        self.video_label.setFixedSize(640, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.video_label)
        self.status_label = QLabel("Status: Initializing...", self)
        video_layout.addWidget(self.status_label)
        
        self.enable_commands_checkbox = QCheckBox("Enable Gesture Commands")
        self.enable_commands_checkbox.setChecked(True)
        video_layout.addWidget(self.enable_commands_checkbox)
        
        video_group.setLayout(video_layout)
        self.left_panel.addWidget(video_group)
        splitter.addWidget(left_widget)

        # --- Right Panel (Config and Management) ---
        right_widget = QWidget()
        self.right_panel = QVBoxLayout(right_widget)

        config_group = QGroupBox("Configuration (`config/gestures.json`)")
        config_layout = QVBoxLayout()
        self.config_display = QTextEdit()
        self.config_display.setReadOnly(True)
        self.reload_button = QPushButton("Reload Config")
        self.reload_button.clicked.connect(self.load_config)
        config_layout.addWidget(self.config_display)
        config_layout.addWidget(self.reload_button)
        config_group.setLayout(config_layout)

        management_group = QGroupBox("Management")
        management_layout = QVBoxLayout()
        self.management_forms = QFormLayout()

        # Add Gesture Form
        self.gesture_name_input = QLineEdit()
        self.gesture_conditions_input = QTextEdit()
        self.add_gesture_button = QPushButton("Add Gesture")
        self.add_gesture_button.clicked.connect(self.add_gesture)
        self.management_forms.addRow("Gesture Name:", self.gesture_name_input)
        self.management_forms.addRow("Conditions (JSON):", self.gesture_conditions_input)
        self.management_forms.addRow(self.add_gesture_button)

        # Add Mapping Form
        self.mapping_gesture_name_input = QLineEdit()
        self.mapping_details_input = QTextEdit()
        self.add_mapping_button = QPushButton("Add Mapping")
        self.add_mapping_button.clicked.connect(self.add_mapping)
        self.management_forms.addRow("Mapping Gesture Name:", self.mapping_gesture_name_input)
        self.management_forms.addRow("Mapping (JSON):", self.mapping_details_input)
        self.management_forms.addRow(self.add_mapping_button)
        
        management_group.setLayout(self.management_forms)
        
        self.right_panel.addWidget(config_group)
        self.right_panel.addWidget(management_group)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([680, 600])


        # --- Initialize Video Thread ---
        self.thread = VideoThread(self.hand_capture, self.gesture_detector)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.gesture_detected_signal.connect(self.on_gesture_detected)
        self.thread.start()

        # Load initial config
        self.load_config()

    def set_stylesheet(self):
        """Sets a modern stylesheet for the application."""
        style = """
            QMainWindow {
                background-color: #2E2E2E;
            }
            QGroupBox {
                background-color: #3C3C3C;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 12px;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: 1px solid #666666;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #6A6A6A;
            }
            QPushButton:pressed {
                background-color: #4A4A4A;
            }
            QTextEdit, QLineEdit {
                background-color: #252525;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
                font-family: Consolas, Courier New, monospace;
            }
            QCheckBox {
                color: #E0E0E0;
            }
            QSplitter::handle {
                background-color: #4A4A4A;
            }
            QSplitter::handle:horizontal {
                width: 5px;
            }
        """
        self.setStyleSheet(style)


    def load_config(self):
        """Loads and displays the configuration."""
        config = self.config_manager.get_config()
        self.config_display.setText(json.dumps(config, indent=2))
        
        # Update gesture detector and command executor
        self.gesture_detector = GestureDetector(config)
        self.command_executor.update_mappings(config.get('mappings', {}))
        self.thread.gesture_detector = self.gesture_detector
        self.status_label.setText("Status: Config reloaded")

    def add_gesture(self):
        """Adds a new gesture to the configuration."""
        name = self.gesture_name_input.text()
        conditions_str = self.gesture_conditions_input.toPlainText()
        if not name or not conditions_str:
            QMessageBox.warning(self, "Input Error", "Please fill in all gesture fields.")
            return
        
        try:
            conditions = json.loads(conditions_str)
            gesture = {"name": name, "conditions": conditions}
            if self.config_manager.add_gesture(gesture):
                QMessageBox.information(self, "Success", "Gesture added successfully.")
                self.load_config()
                self.gesture_name_input.clear()
                self.gesture_conditions_input.clear()
            else:
                QMessageBox.critical(self, "Error", "Failed to add gesture.")

        except json.JSONDecodeError:
            QMessageBox.warning(self, "Input Error", "Invalid JSON in conditions.")

    def add_mapping(self):
        """Adds a new mapping to the configuration."""
        gesture_name = self.mapping_gesture_name_input.text()
        mapping_str = self.mapping_details_input.toPlainText()
        if not gesture_name or not mapping_str:
            QMessageBox.warning(self, "Input Error", "Please fill in all mapping fields.")
            return
            
        try:
            mapping = json.loads(mapping_str)
            if self.config_manager.add_mapping(gesture_name, mapping):
                QMessageBox.information(self, "Success", "Mapping added successfully.")
                self.load_config()
                self.mapping_gesture_name_input.clear()
                self.mapping_details_input.clear()
            else:
                 QMessageBox.critical(self, "Error", "Failed to add mapping.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Input Error", "Invalid JSON in mapping.")


    def update_image(self, qt_img):
        """Updates the video_label with a new QPixmap."""
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def on_gesture_detected(self, gesture_name):
        """Handles the detected gesture."""
        if gesture_name:
            self.status_label.setText(f"Status: Detected '{gesture_name}'")
            # Execute command only if the checkbox is checked
            if self.enable_commands_checkbox.isChecked():
                self.command_executor.execute_command(gesture_name)
        else:
            self.status_label.setText("Status: No gesture detected")


    def closeEvent(self, event):
        """Shuts down the video thread when the window is closed."""
        self.thread.stop()
        self.hand_capture.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GestureMapperGUI()
    window.show()
    sys.exit(app.exec_())

