"""
PyQt GUI for the Gesture Mapper MVP.
Provides a desktop interface to view the camera feed and manage gestures,
including an interactive tool for creating new gesture definitions.
"""

import sys
import cv2
import json
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QFormLayout, QLineEdit, QMessageBox, QGroupBox,
                             QSplitter, QCheckBox, QComboBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QPoint, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

from input_capture import HandCapture
from config_manager import ConfigManager
from gesture_detection import GestureDetector
from command_executor import CommandExecutor

# --- Clickable Label for Interactive Video Feed ---
class ClickableLabel(QLabel):
    """A QLabel that emits a signal with the coordinates of a click."""
    clicked = pyqtSignal(QPoint)

    def mousePressEvent(self, event):
        self.clicked.emit(event.pos())
        super().mousePressEvent(event)

# --- Video Processing Thread ---
class VideoThread(QThread):
    """Thread to capture video, process landmarks, and detect gestures."""
    change_pixmap_signal = pyqtSignal(QImage)
    gesture_detected_signal = pyqtSignal(str)
    landmarks_signal = pyqtSignal(list) # Emits raw landmark data for the inspector

    def __init__(self, hand_capture, gesture_detector, gui_instance):
        super().__init__()
        self._run_flag = True
        self.hand_capture = hand_capture
        self.gesture_detector = gesture_detector
        self.gui = gui_instance

    def run(self):
        """Capture video and emit frames, gestures, and landmarks."""
        while self._run_flag:
            success, frame = self.hand_capture.read_frame()
            if not success:
                continue

            landmarks = self.hand_capture.get_landmarks(frame)
            gesture_name = ""

            if landmarks:
                self.landmarks_signal.emit(landmarks) # Emit for inspector
                normalized_landmarks = self.gesture_detector.normalize_keypoints(landmarks)
                gesture_name = self.gesture_detector.detect_gesture(normalized_landmarks)

                # Draw all landmarks
                for i, landmark in enumerate(landmarks):
                    x = int(landmark['x'] * frame.shape[1])
                    y = int(landmark['y'] * frame.shape[0])
                    # Highlight selected landmarks
                    if i in self.gui.selected_points:
                        cv2.circle(frame, (x, y), 6, (0, 255, 255), -1) # Yellow circle
                        cv2.circle(frame, (x, y), 3, (0, 0, 0), -1)      # Black dot
                    else:
                        cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

            if gesture_name:
                self.gesture_detected_signal.emit(gesture_name)
                cv2.putText(frame, f"Gesture: {gesture_name}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                self.gesture_detected_signal.emit("")

            # Convert frame to QImage and emit
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


# --- Main Application Window ---
class GestureMapperGUI(QMainWindow):
    """Main window for the Gesture Mapper application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture Mapper")
        self.setGeometry(100, 100, 1400, 800)
        self.set_stylesheet()

        # --- State Variables ---
        self.selected_points = []
        self.landmarks = []
        self.live_value = 0.0

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

        # --- Left Panel (Video and Inspector) ---
        left_widget = QWidget()
        self.left_panel = QVBoxLayout(left_widget)
        
        # Video Group
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

        # Inspector Group
        inspector_group = self._create_inspector_group()

        self.left_panel.addWidget(video_group)
        self.left_panel.addWidget(inspector_group)
        splitter.addWidget(left_widget)

        # --- Right Panel (Config and Management) ---
        right_widget = QWidget()
        self.right_panel = QVBoxLayout(right_widget)
        config_group = self._create_config_group()
        management_group = self._create_management_group()
        self.right_panel.addWidget(config_group)
        self.right_panel.addWidget(management_group)
        splitter.addWidget(right_widget)
        splitter.setSizes([700, 700])

        # --- Initialize Video Thread ---
        self.thread = VideoThread(self.hand_capture, self.gesture_detector, self)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.gesture_detected_signal.connect(self.on_gesture_detected)
        self.thread.landmarks_signal.connect(self.on_landmarks_received)
        self.thread.start()
        self.load_config()

    # --- UI Group Creation Methods ---
    def _create_inspector_group(self):
        inspector_group = QGroupBox("Landmark Inspector")
        inspector_layout = QFormLayout()
        self.selected_points_label = QLabel("None")
        self.relationship_type_combo = QComboBox()
        self.relationship_type_combo.addItems(["Distance", "Angle"])
        self.relationship_type_combo.currentTextChanged.connect(self._update_constraint_combo)
        
        self.constraint_type_combo = QComboBox()
        self._update_constraint_combo(self.relationship_type_combo.currentText())

        self.live_value_label = QLabel("N/A")
        self.importance_combo = QComboBox()
        self.importance_combo.addItems(["Strict", "Loose"])
        
        inspector_layout.addRow("Selected Points:", self.selected_points_label)
        inspector_layout.addRow("Relationship:", self.relationship_type_combo)
        inspector_layout.addRow("Constraint:", self.constraint_type_combo)
        inspector_layout.addRow("Live Value:", self.live_value_label)
        inspector_layout.addRow("Importance:", self.importance_combo)

        button_layout = QHBoxLayout()
        self.snapshot_button = QPushButton("Snapshot Condition")
        self.snapshot_button.clicked.connect(self.snapshot_condition)
        self.clear_selection_button = QPushButton("Clear Selection")
        self.clear_selection_button.clicked.connect(self.clear_point_selection)
        button_layout.addWidget(self.snapshot_button)
        button_layout.addWidget(self.clear_selection_button)
        inspector_layout.addRow(button_layout)
        
        self.generated_condition_display = QTextEdit()
        self.generated_condition_display.setReadOnly(True)
        self.add_condition_to_gesture_button = QPushButton("Add Condition to Gesture Form")
        self.add_condition_to_gesture_button.clicked.connect(self.add_condition_to_gesture)
        inspector_layout.addRow("Generated Condition:", self.generated_condition_display)
        inspector_layout.addRow(self.add_condition_to_gesture_button)
        
        inspector_group.setLayout(inspector_layout)
        return inspector_group

    def _update_constraint_combo(self, text):
        """Update constraint options based on relationship type."""
        self.constraint_type_combo.clear()
        if text == "Distance":
            self.constraint_type_combo.addItems(["Less Than (Close)", "Greater Than (Far)"])
        elif text == "Angle":
            self.constraint_type_combo.addItems(["Between (Exact)", "Less Than (Acute)", "Greater Than (Obtuse)"])

    def _create_config_group(self):
        config_group = QGroupBox("Configuration (`config/gestures.json`)")
        config_layout = QVBoxLayout()
        self.config_display = QTextEdit()
        self.config_display.setReadOnly(True)
        self.reload_button = QPushButton("Reload Config")
        self.reload_button.clicked.connect(self.load_config)
        config_layout.addWidget(self.config_display)
        config_layout.addWidget(self.reload_button)
        config_group.setLayout(config_layout)
        return config_group

    def _create_management_group(self):
        management_group = QGroupBox("Gesture & Mapping Management")
        self.management_forms = QFormLayout()
        self.gesture_name_input = QLineEdit()
        self.gesture_conditions_input = QTextEdit()
        self.add_gesture_button = QPushButton("Save New Gesture")
        self.add_gesture_button.clicked.connect(self.add_gesture)
        self.management_forms.addRow("Gesture Name:", self.gesture_name_input)
        self.management_forms.addRow("Conditions (JSON):", self.gesture_conditions_input)
        self.management_forms.addRow(self.add_gesture_button)
        self.mapping_gesture_name_input = QLineEdit()
        self.mapping_details_input = QTextEdit()
        self.add_mapping_button = QPushButton("Save New Mapping")
        self.add_mapping_button.clicked.connect(self.add_mapping)
        self.management_forms.addRow("---", QLabel()) # Separator
        self.management_forms.addRow("Mapping Gesture Name:", self.mapping_gesture_name_input)
        self.management_forms.addRow("Mapping (JSON):", self.mapping_details_input)
        self.management_forms.addRow(self.add_mapping_button)
        management_group.setLayout(self.management_forms)
        return management_group

    # --- Slots and Event Handlers ---
    def on_landmarks_received(self, landmarks):
        """Update landmarks and recalculate live values for the inspector."""
        self.landmarks = landmarks
        self.update_live_value()

    @pyqtSlot(QPoint)
    def on_video_label_clicked(self, pos):
        """Handle clicks on the video feed to select landmarks."""
        if not self.landmarks:
            return
        
        # Convert click position to frame coordinates
        label_size = self.video_label.size()
        frame_w, frame_h = self.hand_capture.cap.get(3), self.hand_capture.cap.get(4)
        
        scale_x = frame_w / label_size.width()
        scale_y = frame_h / label_size.height()
        
        click_x_frame = pos.x() * scale_x
        click_y_frame = pos.y() * scale_y
        
        # Find the closest landmark
        min_dist = float('inf')
        closest_landmark_idx = -1
        for i, landmark in enumerate(self.landmarks):
            landmark_x_px = landmark['x'] * frame_w
            landmark_y_px = landmark['y'] * frame_h
            dist = math.sqrt((landmark_x_px - click_x_frame)**2 + (landmark_y_px - click_y_frame)**2)
            if dist < min_dist:
                min_dist = dist
                closest_landmark_idx = i

        # Select landmark if click is close enough
        if min_dist < 20: # pixel threshold
            if closest_landmark_idx not in self.selected_points:
                self.selected_points.append(closest_landmark_idx)
                self.selected_points_label.setText(str(self.selected_points))
            else:
                self.selected_points.remove(closest_landmark_idx)
                self.selected_points_label.setText(str(self.selected_points))
    
    def update_live_value(self):
        """Calculate and display live distance or angle."""
        if not self.landmarks:
            self.live_value_label.setText("N/A")
            return
            
        rel_type = self.relationship_type_combo.currentText()
        num_points = len(self.selected_points)
        
        value_text = "N/A"
        self.live_value = 0.0

        try:
            if rel_type == "Distance" and num_points == 2:
                p1 = self.landmarks[self.selected_points[0]]
                p2 = self.landmarks[self.selected_points[1]]
                dist = self.gesture_detector._euclidean_distance(p1, p2)
                self.live_value = dist
                value_text = f"{dist:.4f}"
            elif rel_type == "Angle" and num_points == 3:
                p1 = self.landmarks[self.selected_points[0]]
                p2 = self.landmarks[self.selected_points[1]] # Vertex
                p3 = self.landmarks[self.selected_points[2]]
                angle = self.gesture_detector._calculate_angle_three_points(p1, p2, p3)
                self.live_value = angle
                value_text = f"{angle:.2f}°"
        except IndexError:
            value_text = "Error: Invalid landmark index."

        self.live_value_label.setText(value_text)

    def snapshot_condition(self):
        """Generate a JSON condition based on the current inspector state."""
        rel_type = self.relationship_type_combo.currentText()
        constraint = self.constraint_type_combo.currentText()
        importance = self.importance_combo.currentText().lower()
        num_points = len(self.selected_points)
        
        if self.live_value <= 0:
            QMessageBox.warning(self, "Snapshot Error", "Cannot snapshot with a zero or invalid live value. Please hold the pose steady.")
            return

        condition = {
            "type": rel_type.lower(),
            "points": self.selected_points.copy(),
            "importance": importance
        }

        if rel_type == "Distance" and num_points == 2:
            # Use a 5% buffer for strict, 15% for loose
            strict_percent = 0.05
            loose_percent = 0.15
            percent = strict_percent if importance == "strict" else loose_percent
            buffer = self.live_value * percent
            
            if "Less Than" in constraint:
                condition["max"] = round(self.live_value + buffer, 4)
            elif "Greater Than" in constraint:
                condition["min"] = round(self.live_value - buffer, 4)
        
        elif rel_type == "Angle" and num_points == 3:
            # Use a 10% buffer for strict, 20% for loose for angles
            strict_percent = 0.10
            loose_percent = 0.20
            percent = strict_percent if importance == "strict" else loose_percent
            buffer = self.live_value * percent

            if "Between" in constraint:
                condition["min"] = round(self.live_value - buffer, 2)
                condition["max"] = round(self.live_value + buffer, 2)
            elif "Less Than" in constraint:
                condition["max"] = round(self.live_value + buffer, 2)
            elif "Greater Than" in constraint:
                condition["min"] = round(self.live_value - buffer, 2)
        
        else:
            QMessageBox.warning(self, "Snapshot Error", "Please select the correct number of points for the chosen relationship (2 for Distance, 3 for Angle).")
            return

        self.generated_condition_display.setText(json.dumps(condition, indent=2))

    def add_condition_to_gesture(self):
        """Append the generated condition to the main gesture form."""
        new_condition_str = self.generated_condition_display.toPlainText()
        if not new_condition_str:
            QMessageBox.warning(self, "Error", "No condition has been generated yet.")
            return

        try:
            new_condition = json.loads(new_condition_str)
            current_conditions_str = self.gesture_conditions_input.toPlainText()
            
            if not current_conditions_str:
                current_conditions = []
            else:
                current_conditions = json.loads(current_conditions_str)
            
            current_conditions.append(new_condition)
            self.gesture_conditions_input.setText(json.dumps(current_conditions, indent=2))
            
        except json.JSONDecodeError:
            self.gesture_conditions_input.setText(f"[{new_condition_str}]")


    def clear_point_selection(self):
        """Clear the list of selected points."""
        self.selected_points = []
        self.selected_points_label.setText("None")
        self.live_value_label.setText("N/A")
        self.generated_condition_display.clear()

    # --- Other Methods (from previous version) ---
    def set_stylesheet(self):
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

    def load_config(self):
        config = self.config_manager.get_config()
        self.config_display.setText(json.dumps(config, indent=2))
        self.gesture_detector = GestureDetector(config)
        self.command_executor.update_mappings(config.get('mappings', {}))
        self.thread.gesture_detector = self.gesture_detector
        self.status_label.setText("Status: Config reloaded")

    def add_gesture(self):
        name = self.gesture_name_input.text()
        conditions_str = self.gesture_conditions_input.toPlainText()
        if not name or not conditions_str:
            QMessageBox.warning(self, "Input Error", "Please fill in all gesture fields.")
            return
        try:
            conditions = json.loads(conditions_str)
            gesture = {"name": name, "conditions": conditions}
            if self.config_manager.add_gesture(gesture):
                QMessageBox.information(self, "Success", "Gesture saved successfully.")
                self.load_config()
                self.gesture_name_input.clear()
                self.gesture_conditions_input.clear()
            else:
                QMessageBox.critical(self, "Error", "Failed to save gesture.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Input Error", "Invalid JSON in conditions.")

    def add_mapping(self):
        gesture_name = self.mapping_gesture_name_input.text()
        mapping_str = self.mapping_details_input.toPlainText()
        if not gesture_name or not mapping_str:
            QMessageBox.warning(self, "Input Error", "Please fill in all mapping fields.")
            return
        try:
            mapping = json.loads(mapping_str)
            if self.config_manager.add_mapping(gesture_name, mapping):
                QMessageBox.information(self, "Success", "Mapping saved successfully.")
                self.load_config()
                self.mapping_gesture_name_input.clear()
                self.mapping_details_input.clear()
            else:
                 QMessageBox.critical(self, "Error", "Failed to save mapping.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Input Error", "Invalid JSON in mapping.")

    def update_image(self, qt_img):
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def on_gesture_detected(self, gesture_name):
        if gesture_name:
            self.status_label.setText(f"Status: Detected '{gesture_name}'")
            if self.enable_commands_checkbox.isChecked():
                self.command_executor.execute_command(gesture_name)
        else:
            self.status_label.setText("Status: No gesture detected")

    def closeEvent(self, event):
        self.thread.stop()
        self.hand_capture.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GestureMapperGUI()
    window.show()
    sys.exit(app.exec_())

