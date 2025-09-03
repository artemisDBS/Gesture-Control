"""
Main entry point for the Gesture Mapper PyQt GUI.
This file assembles the UI panels and orchestrates the application's components.
"""
import sys
import cv2
import json
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QMessageBox, QGroupBox, QSplitter,
                             QLabel, QCheckBox)
from PyQt5.QtCore import Qt, QPoint, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage

# Backend Imports
from input_capture import HandCapture
from config_manager import ConfigManager
from gesture_detection import GestureDetector
from command_executor import CommandExecutor

# GUI Component Imports (Corrected Paths)
from gui.video_thread import VideoThread
from gui.widgets import ClickableLabel
from gui.panels import InspectorPanel, ConfigPanel, ManagementPanel

class GestureMapperGUI(QMainWindow):
    """
    Main window for the Gesture Mapper application.
    Orchestrates the video feed, UI panels, and backend logic.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture Mapper")
        self.setGeometry(100, 100, 1400, 800)
        self.set_stylesheet()

        # --- State Variables ---
        self.selected_points = []
        self.landmarks = []

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

        # --- Assemble Left Panel (Video and Inspector) ---
        left_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_widget)
        video_group = self._create_video_group()
        self.inspector_panel = InspectorPanel()
        left_panel_layout.addWidget(video_group)
        left_panel_layout.addWidget(self.inspector_panel)
        splitter.addWidget(left_widget)

        # --- Assemble Right Panel (Config and Management) ---
        right_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_widget)
        self.config_panel = ConfigPanel()
        self.management_panel = ManagementPanel()
        right_panel_layout.addWidget(self.config_panel)
        right_panel_layout.addWidget(self.management_panel)
        splitter.addWidget(right_widget)
        splitter.setSizes([700, 700])

        # --- Initialize and Connect Video Thread ---
        self.video_thread = VideoThread(self.hand_capture, self.gesture_detector, self)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.gesture_detected_signal.connect(self.on_gesture_detected)
        self.video_thread.landmarks_signal.connect(self.on_landmarks_received)
        self.video_thread.start()

        # --- Connect Panel Signals to Slots ---
        self.config_panel.reload_requested.connect(self.load_config)
        self.inspector_panel.condition_generated.connect(self.management_panel.add_condition_to_form)
        self.inspector_panel.selection_cleared.connect(self.clear_point_selection)
        self.inspector_panel.snapshot_requested.connect(self.snapshot_condition)
        self.management_panel.new_gesture_to_save.connect(self.add_gesture)
        self.management_panel.new_mapping_to_save.connect(self.add_mapping)

        self.load_config()

    def _create_video_group(self):
        """Creates the QGroupBox for the live video feed."""
        video_group = QGroupBox("Live Feed")
        video_layout = QVBoxLayout()
        self.video_label = ClickableLabel(self)
        self.video_label.setFixedSize(640, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.clicked.connect(self.on_video_label_clicked)
        video_layout.addWidget(self.video_label)
        self.status_label = QLabel("Status: Initializing...", self)
        video_layout.addWidget(self.status_label)
        self.enable_commands_checkbox = QCheckBox("Enable Gesture Commands")
        self.enable_commands_checkbox.setChecked(True)
        video_layout.addWidget(self.enable_commands_checkbox)
        video_group.setLayout(video_layout)
        return video_group

    def set_stylesheet(self):
        """Sets the application's stylesheet for a dark theme."""
        self.setStyleSheet("""
            QMainWindow { background-color: #2E2E2E; }
            QGroupBox {
                background-color: #3C3C3C; color: #FFFFFF;
                border: 1px solid #555555; border-radius: 5px;
                margin-top: 1ex; font-size: 14px; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px;
            }
            QLabel { color: #E0E0E0; font-size: 12px; }
            QPushButton {
                background-color: #555555; color: #FFFFFF;
                border: 1px solid #666666; padding: 5px 10px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #6A6A6A; }
            QPushButton:pressed { background-color: #4A4A4A; }
            QTextEdit, QLineEdit {
                background-color: #252525; color: #E0E0E0;
                border: 1px solid #555555; border-radius: 3px; padding: 2px;
                font-family: Consolas, Courier New, monospace;
            }
            QComboBox {
                background-color: #252525; color: #E0E0E0;
                border: 1px solid #555555;
            }
            QCheckBox { color: #E0E0E0; }
            QSplitter::handle { background-color: #4A4A4A; }
            QSplitter::handle:horizontal { width: 5px; }
        """)

    # --- Major Slots (Application Logic) ---

    @pyqtSlot()
    def load_config(self):
        """Reloads the configuration and updates all relevant components."""
        config = self.config_manager.get_config()
        self.config_panel.set_config_text(json.dumps(config, indent=2))
        
        self.gesture_detector = GestureDetector(config)
        self.command_executor.update_mappings(config.get('mappings', {}))
        self.video_thread.gesture_detector = self.gesture_detector
        
        self.status_label.setText("Status: Config reloaded")

    @pyqtSlot(dict)
    def add_gesture(self, gesture):
        """Saves a new gesture and reloads the configuration."""
        if self.config_manager.add_gesture(gesture):
            QMessageBox.information(self, "Success", "Gesture saved successfully.")
            self.load_config()
            self.management_panel.clear_gesture_form()
        else:
            QMessageBox.critical(self, "Error", "Failed to save gesture. Check if the name is unique and conditions are valid.")

    @pyqtSlot(str, dict)
    def add_mapping(self, gesture_name, mapping):
        """Saves a new mapping and reloads the configuration."""
        if self.config_manager.add_mapping(gesture_name, mapping):
            QMessageBox.information(self, "Success", "Mapping saved successfully.")
            self.load_config()
            self.management_panel.clear_mapping_form()
        else:
            QMessageBox.critical(self, "Error", "Failed to save mapping.")

    @pyqtSlot(QImage)
    def update_image(self, qt_img):
        """Updates the video feed label with a new frame."""
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    @pyqtSlot(str)
    def on_gesture_detected(self, gesture_name):
        """Handles detected gestures and executes commands if enabled."""
        if gesture_name:
            self.status_label.setText(f"Status: Detected '{gesture_name}'")
            if self.enable_commands_checkbox.isChecked():
                self.command_executor.execute_command(gesture_name)
        else:
            self.status_label.setText("Status: No gesture detected")

    @pyqtSlot(list)
    def on_landmarks_received(self, landmarks):
        """Updates internal landmark state and tells the inspector panel to update."""
        self.landmarks = landmarks
        self.inspector_panel.update_live_value(landmarks, self.selected_points, self.gesture_detector)

    @pyqtSlot(QPoint)
    def on_video_label_clicked(self, pos):
        """Handles clicks on the video feed to select landmarks."""
        if not self.landmarks:
            return
        
        label_size = self.video_label.size()
        frame_w, frame_h = self.hand_capture.cap.get(3), self.hand_capture.cap.get(4)
        
        scale_x = frame_w / label_size.width()
        scale_y = frame_h / label_size.height()
        
        click_x_frame = pos.x() * scale_x
        click_y_frame = pos.y() * scale_y
        
        min_dist = float('inf')
        closest_landmark_idx = -1
        for i, landmark in enumerate(self.landmarks):
            landmark_x_px = landmark['x'] * frame_w
            landmark_y_px = landmark['y'] * frame_h
            dist = math.sqrt((landmark_x_px - click_x_frame)**2 + (landmark_y_px - click_y_frame)**2)
            if dist < min_dist:
                min_dist = dist
                closest_landmark_idx = i

        if min_dist < 20: # pixel threshold
            if closest_landmark_idx not in self.selected_points:
                self.selected_points.append(closest_landmark_idx)
            else:
                self.selected_points.remove(closest_landmark_idx)
            self.inspector_panel.set_selected_points_text(self.selected_points)

    @pyqtSlot()
    def snapshot_condition(self):
        self.inspector_panel.snapshot_condition(self.selected_points)

    @pyqtSlot()
    def clear_point_selection(self):
        """Clears the selected points list and updates the UI."""
        self.selected_points = []
        self.inspector_panel.clear_selection()

    def closeEvent(self, event):
        """Cleanly stops the video thread and releases the camera on exit."""
        self.video_thread.stop()
        self.hand_capture.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GestureMapperGUI()
    window.show()
    sys.exit(app.exec_())
