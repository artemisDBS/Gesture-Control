"""
This is the main entry point for the Gesture Mapper GUI.
This file assembles all the UI panels and orchestrates the application's components.
"""

import sys
import json
import math
import time

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                             QVBoxLayout, QMessageBox, QSplitter, QCheckBox, QSizePolicy, QTabWidget, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSlot, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage

# Backend Imports
from input_capture import HandCapture
from config_manager import ConfigManager
from gesture_detection import GestureDetector
from command_executor import CommandExecutor

# GUI Component Imports
from gui.video_thread import VideoThread
from gui.widgets import ClickableLabel
from gui.panels import (CreateGesturePanel, EditGesturePanel, MappingPanel, 
                       SettingsPanel, InspectorPanel)


class GestureMapperGUI(QMainWindow):
    """
    The main window for the Gesture Mapper application.
    Orchestrates the video feed, UI panels, and backend logic.
    """
    selection_changed_signal = pyqtSignal(list)
    click_visualization_signal = pyqtSignal(tuple)
    gesture_saved_signal = pyqtSignal()  # Signal to refresh other tabs when a gesture is saved

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture Mapper")
        self.setGeometry(100, 100, 1400, 800)

        # --- Backend Initialization ---
        self.config_manager = ConfigManager()
        self.hand_capture = HandCapture()
        self.gesture_detector = GestureDetector(self.config_manager.get_config())
        self.command_executor = CommandExecutor(self.config_manager.get_mappings())

        # Correctly initialize landmark storage
        self.raw_landmarks = []
        self.normalized_landmarks = []
        self.selected_points = []
        self.commands_enabled = False
        
        # Gesture Editor State Management
        self.editing_gesture_name = None
        self.editing_conditions = []
        self.selected_condition_index = -1

        # --- UI Initialization ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self._setup_ui_panels()
        self._setup_video_thread()
        self._connect_signals()
        self._apply_stylesheet()
        
        self._reload_config()

    def _setup_ui_panels(self):
        """Creates and arranges the UI panels with the new tab structure."""
        # Create the main tab widget
        self.tab_widget = QTabWidget()
        
        # Create the four main tabs
        self.create_gesture_panel = CreateGesturePanel()
        self.edit_gesture_panel = EditGesturePanel()
        self.mapping_panel = MappingPanel()
        self.settings_panel = SettingsPanel()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.create_gesture_panel, "Create Gesture")
        self.tab_widget.addTab(self.edit_gesture_panel, "Edit Gestures")
        self.tab_widget.addTab(self.mapping_panel, "Command Mappings")
        self.tab_widget.addTab(self.settings_panel, "Settings")

        # Create video panel (left column)
        self.video_label = ClickableLabel("Initializing Camera...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 1px solid #555; background-color: #111;")
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.video_label.setScaledContents(False)

        self.enable_commands_checkbox = QCheckBox("Enable Gesture Commands")
        self.enable_commands_checkbox.toggled.connect(self._toggle_commands)
        self.enable_commands_checkbox.setStyleSheet("font-size: 16px; font-weight: bold;")

        # Advanced Normalization panel for the left side
        self.normalization_group = QGroupBox("Advanced Normalization")
        self.normalization_group.setCheckable(True)
        self.normalization_group.setChecked(False)
        normalization_layout = QFormLayout()
        
        self.displacement_checkbox = QCheckBox("Displacement Invariant")
        self.displacement_checkbox.setToolTip("Center landmarks on the wrist so hand position doesn't matter.")
        self.scale_checkbox = QCheckBox("Scale Invariant")
        self.scale_checkbox.setToolTip("Normalize by hand size so distance-based rules are comparable.")
        self.rotation_checkbox = QCheckBox("Rotation Invariant")
        self.rotation_checkbox.setToolTip("Rotate landmarks so wrist→index is vertical; ignores wrist twist.")
        
        normalization_layout.addRow(self.displacement_checkbox)
        normalization_layout.addRow(self.scale_checkbox)
        normalization_layout.addRow(self.rotation_checkbox)
        
        self.normalization_group.setLayout(normalization_layout)

        video_layout = QVBoxLayout()
        video_layout.addWidget(self.video_label, 5)
        video_layout.addWidget(self.enable_commands_checkbox)
        video_layout.addWidget(self.normalization_group)
        video_widget = QWidget()
        video_widget.setLayout(video_layout)
        
        # Create the main splitter with video on left and tabs on right
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(video_widget)
        splitter.addWidget(self.tab_widget)
        # Make video column ~45% of width (approximate using stretch ratios)
        splitter.setStretchFactor(0, 9)
        splitter.setStretchFactor(1, 11)

        self.layout.addWidget(splitter)

    def _setup_video_thread(self):
        """Initializes and starts the background thread for video capture."""
        self.video_thread = VideoThread(
            self.hand_capture, self.gesture_detector, self
        )
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.landmarks_signal.connect(self.on_landmarks_received)
        self.video_thread.gesture_detected_signal.connect(self.on_gesture_detected)
        self.selection_changed_signal.connect(self.video_thread.update_selected_points)
        self.click_visualization_signal.connect(self.video_thread.set_click_visualization)
        self.video_thread.start()

    def _connect_signals(self):
        """Connects signals from UI panels to slots in this main window."""
        self.video_label.clicked.connect(self.on_video_label_clicked)
        
        # Panel-specific signals and inspectors
        # Create tab inspector
        self.create_gesture_panel.inspector_panel.snapshot_requested.connect(
            lambda: self.create_gesture_panel.inspector_panel.snapshot_condition(self.selected_points)
        )
        self.create_gesture_panel.inspector_panel.selection_cleared.connect(self.clear_point_selection)
        self.create_gesture_panel.inspector_panel.condition_generated.connect(self.create_gesture_panel.add_condition_to_form)
        self.create_gesture_panel.inspector_panel.condition_updated.connect(self._update_condition)
        self.create_gesture_panel.gesture_saved.connect(self._save_new_gesture)
        self.edit_gesture_panel.condition_selected.connect(self._on_condition_selected)
        self.edit_gesture_panel.gesture_updated.connect(self._update_gesture)
        self.edit_gesture_panel.gesture_deleted.connect(self._delete_gesture)
        self.edit_gesture_panel.gesture_load_requested.connect(self._load_gesture_for_editing)
        # Edit tab inspector
        self.edit_gesture_panel.inspector_panel.snapshot_requested.connect(
            lambda: self.edit_gesture_panel.inspector_panel.snapshot_condition(self.selected_points)
        )
        self.edit_gesture_panel.inspector_panel.selection_cleared.connect(self.clear_point_selection)
        self.edit_gesture_panel.inspector_panel.condition_generated.connect(self.edit_gesture_panel.add_condition_to_form)
        self.edit_gesture_panel.inspector_panel.condition_updated.connect(self._update_condition)
        
        # Connect signals from the Mapping panel
        self.mapping_panel.mapping_saved.connect(self._save_new_mapping)
        
        # Connect signals from the Settings panel
        self.settings_panel.settings_saved.connect(self._save_global_settings)
        
        # Connect normalization controls to save global settings
        self.displacement_checkbox.toggled.connect(self._save_global_settings_from_left_panel)
        self.scale_checkbox.toggled.connect(self._save_global_settings_from_left_panel)
        self.rotation_checkbox.toggled.connect(self._save_global_settings_from_left_panel)
        
        # Connect the gesture saved signal to refresh other tabs
        self.gesture_saved_signal.connect(self._refresh_all_tabs)
    
    def _reload_config(self):
        """Loads the latest config and updates all relevant components."""
        self.config_manager.load_config()
        new_config = self.config_manager.get_config()
        self.gesture_detector.update_config(new_config)
        self.command_executor.update_mappings(new_config.get('mappings', {}))
        
        # Update gesture lists in all panels
        gesture_names = [gesture['name'] for gesture in new_config.get('gestures', [])]
        self.edit_gesture_panel.update_gesture_list(gesture_names)
        self.mapping_panel.update_gesture_list(gesture_names)
        
        # Update settings panel with current global settings
        self.settings_panel.update_settings(new_config.get('transformations', {}))
        
        # Update main window normalization controls with global settings
        transformations = new_config.get('transformations', {})
        self.displacement_checkbox.setChecked(transformations.get('displacement_invariant', False))
        self.scale_checkbox.setChecked(transformations.get('scale_invariant', False))
        self.rotation_checkbox.setChecked(transformations.get('rotation_invariant', False))
        
        print("Configuration reloaded and applied to all components.")

    def _save_new_gesture(self, gesture_data):
        """Saves a new gesture and reloads the configuration."""
        # Add normalization overrides from the left panel if enabled
        if self.normalization_group.isChecked():
            gesture_data["normalization_overrides"] = {
                "displacement_invariant": self.displacement_checkbox.isChecked(),
                "scale_invariant": self.scale_checkbox.isChecked(),
                "rotation_invariant": self.rotation_checkbox.isChecked()
            }
        
        if self.config_manager.add_gesture(gesture_data):
            QMessageBox.information(self, "Success", "Gesture saved successfully.")
            self.create_gesture_panel.clear_form()
            self._reload_config()
            self.gesture_saved_signal.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to save gesture.")

    def _save_new_mapping(self, gesture_name, mapping_data):
        """Saves a new mapping and reloads the configuration."""
        if self.config_manager.add_mapping(gesture_name, mapping_data):
            QMessageBox.information(self, "Success", "Mapping saved successfully.")
            self.mapping_panel.clear_form()
            self._reload_config()
        else:
            QMessageBox.critical(self, "Error", "Failed to save mapping.")
    
    def _update_gesture(self, gesture_name, gesture_data):
        """Updates an existing gesture."""
        if self.config_manager.update_gesture(gesture_name, gesture_data):
            QMessageBox.information(self, "Success", "Gesture updated successfully.")
            self._reload_config()
            self.gesture_saved_signal.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to update gesture.")
    
    def _delete_gesture(self, gesture_name):
        """Deletes a gesture."""
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete gesture '{gesture_name}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.config_manager.remove_gesture(gesture_name):
                QMessageBox.information(self, "Success", "Gesture deleted successfully.")
                self._reload_config()
                self.gesture_saved_signal.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete gesture.")
    
    def _save_global_settings(self, settings):
        """Saves global normalization settings."""
        if self.config_manager.update_transformations(settings):
            QMessageBox.information(self, "Success", "Settings saved successfully.")
            self._reload_config()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
    
    def _refresh_all_tabs(self):
        """Refreshes all tabs when a gesture is saved."""
        self._reload_config()
    
    def _save_global_settings_from_left_panel(self):
        """Saves global settings when left panel normalization controls change."""
        settings = {
            'displacement_invariant': self.displacement_checkbox.isChecked(),
            'scale_invariant': self.scale_checkbox.isChecked(),
            'rotation_invariant': self.rotation_checkbox.isChecked()
        }
        self._save_global_settings(settings)

    def _toggle_commands(self, checked):
        """Enables or disables the execution of gesture commands."""
        self.commands_enabled = checked
        status = "ENABLED" if checked else "DISABLED"
        print(f"Gesture commands {status}.")

    @pyqtSlot(QImage)
    def update_image(self, qt_image):
        """Updates the video_label with a new QImage from the video thread."""
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)

    def on_landmarks_received(self, raw_landmarks, normalized_landmarks):
        """
        Receives both raw and normalized landmarks from the video thread.
        Stores them for use in click detection and the inspector panels.
        """
        self.raw_landmarks = raw_landmarks
        self.normalized_landmarks = normalized_landmarks
        
        # Update active tab inspector live values
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, 'inspector_panel'):
            current_tab.inspector_panel.update_live_value(
                self.normalized_landmarks, self.selected_points, self.gesture_detector
            )

    @pyqtSlot(str)
    def on_gesture_detected(self, gesture_name):
        """Handles a detected gesture, updating the UI and executing a command if enabled."""
        # Update detected gesture display on active inspector
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, 'inspector_panel'):
            current_tab.inspector_panel.set_detected_gesture(gesture_name)
        
        if self.commands_enabled and gesture_name:
            analogue_value = self.gesture_detector.get_analogue_value(self.normalized_landmarks, gesture_name)
            self.command_executor.execute_command(gesture_name, analogue_value)

    @pyqtSlot(QPoint)
    def on_video_label_clicked(self, pos):
        """Handles clicks on the video feed to select landmarks, using RAW landmarks."""
        if not self.raw_landmarks or self.video_label.pixmap() is None or self.video_label.pixmap().isNull():
            return

        label_size = self.video_label.size()
        pixmap = self.video_label.pixmap()
        scaled_size = pixmap.size()
        
        offset_x = (label_size.width() - scaled_size.width()) / 2
        offset_y = (label_size.height() - scaled_size.height()) / 2
        
        img_x = pos.x() - offset_x
        img_y = pos.y() - offset_y

        if not (0 <= img_x <= scaled_size.width() and 0 <= img_y <= scaled_size.height()):
            return

        norm_x = img_x / scaled_size.width()
        norm_y = img_y / scaled_size.height()
        
        self.click_visualization_signal.emit((norm_x, norm_y))

        min_dist_sq = float('inf')
        closest_landmark_idx = -1
        # Use RAW landmarks for click detection
        for i, landmark in enumerate(self.raw_landmarks):
            dist_sq = (landmark['x'] - norm_x)**2 + (landmark['y'] - norm_y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_landmark_idx = i
        
        TOLERANCE_SQ = 0.002
        if closest_landmark_idx != -1 and min_dist_sq < TOLERANCE_SQ:
            if closest_landmark_idx in self.selected_points:
                self.selected_points.remove(closest_landmark_idx)
            else:
                self.selected_points.append(closest_landmark_idx)
            
            # Get relationship type from active inspector
            current_tab = self.tab_widget.currentWidget()
            rel_type = None
            if hasattr(current_tab, 'inspector_panel'):
                rel_type = current_tab.inspector_panel.relationship_type_combo.currentText()
            if rel_type is None:
                rel_type = "Distance"
            max_points = 2 if rel_type == "Distance" else 3
            if len(self.selected_points) > max_points:
                self.selected_points.pop(0)

            # Update selected points display
            if hasattr(current_tab, 'inspector_panel'):
                current_tab.inspector_panel.set_selected_points_text(self.selected_points)
            self.selection_changed_signal.emit(self.selected_points)

    def clear_point_selection(self):
        """Clears the selected points list and updates the UI."""
        self.selected_points.clear()
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, 'inspector_panel'):
            current_tab.inspector_panel.clear_selection()
        self.selection_changed_signal.emit(self.selected_points)

    def _load_gesture_for_editing(self, gesture_name):
        """Loads a gesture for editing and populates the condition list."""
        config = self.config_manager.get_config()
        gestures = config.get('gestures', [])
        
        # Find the gesture
        gesture = None
        for g in gestures:
            if g['name'] == gesture_name:
                gesture = g
                break
        
        if not gesture:
            QMessageBox.warning(self, "Error", f"Gesture '{gesture_name}' not found.")
            return
        
        # Store editing state
        self.editing_gesture_name = gesture_name
        self.editing_conditions = gesture.get('conditions', []).copy()
        
        # Load gesture into the edit panel
        self.edit_gesture_panel.load_gesture(gesture)
        
        # Send conditions to video thread for color coding
        self.video_thread.update_editing_conditions(self.editing_conditions)
        
        print(f"Loaded gesture '{gesture_name}' with {len(self.editing_conditions)} conditions for editing.")

    def _on_condition_selected(self, condition_index):
        """Handles when a condition is selected from the list for editing."""
        if condition_index < 0 or condition_index >= len(self.editing_conditions):
            return
        
        self.selected_condition_index = condition_index
        condition = self.editing_conditions[condition_index]
        
        # Load condition into the edit tab inspector for editing
        self.edit_gesture_panel.inspector_panel.load_condition_for_editing(condition)
        self.edit_gesture_panel.inspector_panel.set_editing_mode(True, condition_index)
        
        # Set the points for visual feedback
        points = condition.get('points', [])
        self.selected_points = points.copy()
        self.edit_gesture_panel.inspector_panel.set_selected_points_text(points)
        self.selection_changed_signal.emit(points)
        
        print(f"Selected condition {condition_index} for editing: {condition}")

    def _update_condition(self, condition_index, condition_json):
        """Updates a condition in the editing list."""
        try:
            condition = json.loads(condition_json)
            if 0 <= condition_index < len(self.editing_conditions):
                self.editing_conditions[condition_index] = condition
                
                # Update the condition list display in the edit panel
                self.edit_gesture_panel.populate_conditions(self.editing_conditions)
                
                # Send updated conditions to video thread
                self.video_thread.update_editing_conditions(self.editing_conditions)
                
                print(f"Updated condition {condition_index}: {condition}")
            else:
                QMessageBox.warning(self, "Error", "Invalid condition index.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid JSON in condition.")
    
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
            QTabBar::tab {
                background: #3A3A3A;
                color: #F5F5F5;
                padding: 8px 16px;
                border: 1px solid #555;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #505050;
                color: #FFFFFF;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                top: -1px;
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
            QCheckBox {
                font-size: 15px;
            }
            /* Toggle-like effect for checkboxes (simple styling) */
            QCheckBox::indicator {
                width: 22px; height: 22px;
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


