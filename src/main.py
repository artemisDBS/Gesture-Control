"""
This is the main entry point for the Gesture Mapper GUI.
This file assembles all the UI panels and orchestrates the application's components.
"""

import sys
import json
import math

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                            QVBoxLayout, QMessageBox, QSplitter, QCheckBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSlot, QPoint
from PyQt5.QtGui import QPixmap, QImage

# Backend Imports
from input_capture import HandCapture
from config_manager import ConfigManager
from gesture_detection import GestureDetector
from command_executor import CommandExecutor

# GUI Component Imports
from gui.video_thread import VideoThread
from gui.widgets import ClickableLabel
from gui.panels import InspectorPanel, ConfigPanel, ManagementPanel


class GestureMapperGUI(QMainWindow):
    """
    The main window for the Gesture Mapper application.
    Orchestrates the video feed, UI panels, and backend logic.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture Mapper")
        self.setGeometry(100, 100, 1200, 700)

        # --- Backend Initialization ---
        self.config_manager = ConfigManager()
        self.hand_capture = HandCapture()
        self.gesture_detector = GestureDetector(self.config_manager.get_config())
        self.command_executor = CommandExecutor(self.config_manager.get_mappings())

        self.landmarks = []
        self.selected_points = []
        self.commands_enabled = False

        # --- UI Initialization ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)

        self._setup_ui_panels()
        self._setup_video_thread()
        self._connect_signals()
        self._apply_stylesheet()
        
        # Load initial config into UI
        self._reload_config()

    def _setup_ui_panels(self):
        """Creates and arranges the UI panels."""
        # Video Feed Panel
        self.video_label = ClickableLabel("Initializing Camera...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 1px solid #555; background-color: #111;")
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.video_label.setScaledContents(False)

        # Enable Commands Checkbox
        self.enable_commands_checkbox = QCheckBox("Enable Gesture Commands")
        self.enable_commands_checkbox.toggled.connect(self._toggle_commands)

        video_layout = QVBoxLayout()
        video_layout.addWidget(self.video_label)
        video_layout.addWidget(self.enable_commands_checkbox)
        video_widget = QWidget()
        video_widget.setLayout(video_layout)
        
        # Right-side panels
        self.inspector_panel = InspectorPanel()
        self.config_panel = ConfigPanel()
        self.management_panel = ManagementPanel()

        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(self.inspector_panel)
        right_panel_layout.addWidget(self.config_panel)
        right_panel_layout.addWidget(self.management_panel)
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel_layout)

        # Splitter to make panels resizable
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(video_widget)
        splitter.addWidget(right_panel_widget)
        splitter.setStretchFactor(0, 2) # Video panel takes more space initially
        splitter.setStretchFactor(1, 1)

        self.layout.addWidget(splitter, 0, 0)

    def _setup_video_thread(self):
        """Initializes and starts the background thread for video capture."""
        self.video_thread = VideoThread(
            self.hand_capture, self.gesture_detector, self
        )
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.landmarks_signal.connect(self.on_landmarks_received)
        self.video_thread.gesture_detected_signal.connect(self.on_gesture_detected)
        self.video_thread.start()

    def _connect_signals(self):
        """Connects signals from UI panels to slots in this main window."""
        self.video_label.clicked.connect(self.on_video_label_clicked)
        
        # Inspector Panel Signals
        self.inspector_panel.snapshot_requested.connect(
            lambda: self.inspector_panel.snapshot_condition(self.selected_points)
        )
        self.inspector_panel.selection_cleared.connect(self.clear_point_selection)
        self.inspector_panel.condition_generated.connect(self.management_panel.add_condition_to_form)

        # Config Panel Signals
        self.config_panel.reload_requested.connect(self._reload_config)
        
        # Management Panel Signals
        self.management_panel.new_gesture_to_save.connect(self._save_new_gesture)
        self.management_panel.new_mapping_to_save.connect(self._save_new_mapping)
    
    def _reload_config(self):
        """Loads the latest config and updates all relevant components."""
        self.config_manager.load_config()
        new_config = self.config_manager.get_config()
        
        # Update the backend components with the new configuration
        self.gesture_detector.update_config(new_config)
        self.command_executor.update_mappings(new_config.get('mappings', {}))

        # Update the UI display
        config_text = json.dumps(new_config, indent=2)
        self.config_panel.set_config_text(config_text)
        print("Configuration reloaded and applied to all components.")


    def _save_new_gesture(self, gesture_data):
        """Saves a new gesture and reloads the configuration."""
        if self.config_manager.add_gesture(gesture_data):
            QMessageBox.information(self, "Success", "Gesture saved successfully.")
            self.management_panel.clear_gesture_form()
            self._reload_config()
        else:
            QMessageBox.critical(self, "Error", "Failed to save gesture. Check for duplicate names or invalid conditions.")

    def _save_new_mapping(self, gesture_name, mapping_data):
        """Saves a new mapping and reloads the configuration."""
        if self.config_manager.add_mapping(gesture_name, mapping_data):
            QMessageBox.information(self, "Success", "Mapping saved successfully.")
            self.management_panel.clear_mapping_form()
            self._reload_config()
        else:
            QMessageBox.critical(self, "Error", "Failed to save mapping. Check for invalid JSON.")

    def _toggle_commands(self, checked):
        """Enables or disables the execution of gesture commands."""
        self.commands_enabled = checked
        status = "ENABLED" if checked else "DISABLED"
        print(f"Gesture commands {status}.")

    # --- PyQt Slots for handling signals ---

    @pyqtSlot(QImage)
    def update_image(self, qt_image):
        """Updates the video_label with a new QImage from the video thread."""
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)


    @pyqtSlot(list)
    def on_landmarks_received(self, landmarks):
        """Stores the latest landmarks and updates the inspector panel."""
        self.landmarks = landmarks
        self.inspector_panel.update_live_value(
            self.landmarks, self.selected_points, self.gesture_detector
        )

    @pyqtSlot(str)
    def on_gesture_detected(self, gesture_name):
        """Handles a detected gesture, updating the UI and executing a command if enabled."""
        # This is the crucial fix: Always update the UI panel.
        self.inspector_panel.set_detected_gesture(gesture_name)

        if self.commands_enabled and gesture_name:
            # The get_analogue_value is a placeholder for future enhancements
            analogue_value = self.gesture_detector.get_analogue_value(self.landmarks, gesture_name)
            self.command_executor.execute_command(gesture_name, analogue_value)

    @pyqtSlot(QPoint)
    def on_video_label_clicked(self, pos):
        """Handles clicks on the video feed to select landmarks, accounting for aspect ratio."""
        if not self.landmarks or self.video_label.pixmap() is None or self.video_label.pixmap().isNull():
            return

        # Get label and pixmap dimensions
        label_size = self.video_label.size()
        pixmap_size = self.video_label.pixmap().size()

        if not pixmap_size.isValid():
            return
            
        # Calculate the scaled pixmap's properties within the label
        scaled_pixmap = self.video_label.pixmap().scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_size = scaled_pixmap.size()

        # Calculate the position of the top-left corner of the image (the offset for black bars)
        offset_x = (label_size.width() - scaled_size.width()) / 2
        offset_y = (label_size.height() - scaled_size.height()) / 2

        # Adjust click position to be relative to the pixmap, not the label
        img_x = pos.x() - offset_x
        img_y = pos.y() - offset_y

        # Check if the click was inside the actual image area
        if not (0 <= img_x <= scaled_size.width() and 0 <= img_y <= scaled_size.height()):
            return # Click was on the black bars

        # Normalize the coordinates to the 0.0 - 1.0 range of the image
        norm_x = img_x / scaled_size.width()
        norm_y = img_y / scaled_size.height()

        # Find the closest landmark to the normalized click position
        min_dist_sq = float('inf')
        closest_landmark_idx = -1
        for i, landmark in enumerate(self.landmarks):
            dist_sq = (landmark['x'] - norm_x)**2 + (landmark['y'] - norm_y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_landmark_idx = i
        
        # Heuristic to decide if the click was close enough to a landmark
        if closest_landmark_idx != -1 and min_dist_sq < 0.002:
            if closest_landmark_idx in self.selected_points:
                self.selected_points.remove(closest_landmark_idx)
            else:
                self.selected_points.append(closest_landmark_idx)
            
            # Limit selection based on relationship type
            rel_type = self.inspector_panel.relationship_type_combo.currentText()
            max_points = 2 if rel_type == "Distance" else 3
            if len(self.selected_points) > max_points:
                self.selected_points.pop(0) # Remove the oldest point
            
            self.inspector_panel.set_selected_points_text(self.selected_points)


    def clear_point_selection(self):
        """Clears the selected points list and updates the UI."""
        self.selected_points.clear()
        self.inspector_panel.clear_selection()
    
    def closeEvent(self, event):
        """Cleanly stops the video thread and releases the camera on exit."""
        self.video_thread.stop()
        self.hand_capture.release()
        event.accept()

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #E0E0E0;
                font-family: Arial, sans-serif;
            }
            QMainWindow {
                background-color: #222222;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
                background-color: #2E2E2E;
            }
            QLabel, QCheckBox {
                font-size: 14px;
            }
            QPushButton {
                background-color: #555;
                border: 1px solid #777;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #666;
            }
            QPushButton:pressed {
                background-color: #444;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
            }
            QSplitter::handle {
                background-color: #555;
            }
            QSplitter::handle:horizontal {
                width: 1px;
            }
            QSplitter::handle:vertical {
                height: 1px;
            }
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GestureMapperGUI()
    window.show()
    sys.exit(app.exec_())

