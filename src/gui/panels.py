"""
Contains the QGroupBox panels for the Gesture Mapper GUI.
- InspectorPanel: For creating new gesture conditions interactively.
- ConfigPanel: For displaying the current configuration.
- ManagementPanel: For saving new gestures and mappings.
"""
import json
import math
from PyQt5.QtWidgets import (QGroupBox, QFormLayout, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QLineEdit,
                             QComboBox, QMessageBox)
from PyQt5.QtCore import pyqtSignal

class InspectorPanel(QGroupBox):
    """A panel for interactively inspecting landmarks and creating conditions."""
    condition_generated = pyqtSignal(str)
    selection_cleared = pyqtSignal()
    snapshot_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Landmark Inspector", parent)
        self.live_value = 0.0

        layout = QFormLayout()
        self.selected_points_label = QLabel("None")
        self.relationship_type_combo = QComboBox()
        self.relationship_type_combo.addItems(["Distance", "Angle"])
        self.relationship_type_combo.currentTextChanged.connect(self._update_constraint_combo)
        
        self.constraint_type_combo = QComboBox()
        self._update_constraint_combo(self.relationship_type_combo.currentText())

        self.live_value_label = QLabel("N/A")
        self.importance_combo = QComboBox()
        self.importance_combo.addItems(["Strict", "Loose"])
        
        layout.addRow("Selected Points:", self.selected_points_label)
        layout.addRow("Relationship:", self.relationship_type_combo)
        layout.addRow("Constraint:", self.constraint_type_combo)
        layout.addRow("Live Value:", self.live_value_label)
        layout.addRow("Importance:", self.importance_combo)

        button_layout = QHBoxLayout()
        snapshot_button = QPushButton("Snapshot Condition")
        snapshot_button.clicked.connect(self.snapshot_requested.emit)
        clear_selection_button = QPushButton("Clear Selection")
        clear_selection_button.clicked.connect(self.selection_cleared.emit)
        button_layout.addWidget(snapshot_button)
        button_layout.addWidget(clear_selection_button)
        layout.addRow(button_layout)
        
        self.generated_condition_display = QTextEdit()
        self.generated_condition_display.setReadOnly(True)
        add_condition_to_gesture_button = QPushButton("Add Condition to Gesture Form")
        add_condition_to_gesture_button.clicked.connect(self._emit_condition)
        layout.addRow("Generated Condition:", self.generated_condition_display)
        layout.addRow(add_condition_to_gesture_button)
        
        self.setLayout(layout)

    def _update_constraint_combo(self, text):
        """Update constraint options based on relationship type."""
        self.constraint_type_combo.clear()
        if text == "Distance":
            self.constraint_type_combo.addItems(["Less Than (Close)", "Greater Than (Far)"])
        elif text == "Angle":
            self.constraint_type_combo.addItems(["Between (Exact)", "Less Than (Acute)", "Greater Than (Obtuse)"])

    def _emit_condition(self):
        """Emits the generated condition text if it exists."""
        condition_str = self.generated_condition_display.toPlainText()
        if condition_str:
            self.condition_generated.emit(condition_str)
        else:
            QMessageBox.warning(self, "Error", "No condition has been generated yet.")

    def set_selected_points_text(self, points):
        self.selected_points_label.setText(str(points) if points else "None")

    def update_live_value(self, landmarks, selected_points, gesture_detector):
        """Calculates and displays the live value based on selected points."""
        if not landmarks or not selected_points:
            self.live_value_label.setText("N/A")
            return
            
        rel_type = self.relationship_type_combo.currentText()
        num_points = len(selected_points)
        value_text = "N/A"
        self.live_value = 0.0

        try:
            if rel_type == "Distance" and num_points == 2:
                p1 = landmarks[selected_points[0]]
                p2 = landmarks[selected_points[1]]
                dist = gesture_detector._euclidean_distance(p1, p2)
                self.live_value = dist
                value_text = f"{dist:.4f}"
            elif rel_type == "Angle" and num_points == 3:
                p1 = landmarks[selected_points[0]]
                p2 = landmarks[selected_points[1]] # Vertex
                p3 = landmarks[selected_points[2]]
                angle = gesture_detector._calculate_angle_three_points(p1, p2, p3)
                self.live_value = angle
                value_text = f"{angle:.2f}°"
        except IndexError:
            value_text = "Error: Invalid landmark index."

        self.live_value_label.setText(value_text)
    
    def snapshot_condition(self, selected_points):
        """Generates a JSON condition based on the current state."""
        rel_type = self.relationship_type_combo.currentText()
        constraint = self.constraint_type_combo.currentText()
        importance = self.importance_combo.currentText().lower()
        num_points = len(selected_points)
        
        if self.live_value <= 0:
            QMessageBox.warning(self, "Snapshot Error", "Cannot snapshot with a zero or invalid live value. Please hold the pose steady.")
            return

        condition = {
            "type": rel_type.lower(),
            "points": selected_points.copy(),
            "importance": importance
        }

        if rel_type == "Distance" and num_points == 2:
            percent = 0.05 if importance == "strict" else 0.15
            buffer = self.live_value * percent
            if "Less Than" in constraint:
                condition["max"] = round(self.live_value + buffer, 4)
            elif "Greater Than" in constraint:
                condition["min"] = round(self.live_value - buffer, 4)
        elif rel_type == "Angle" and num_points == 3:
            percent = 0.10 if importance == "strict" else 0.20
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

    def clear_selection(self):
        """Clears the UI elements in the inspector."""
        self.selected_points_label.setText("None")
        self.live_value_label.setText("N/A")
        self.generated_condition_display.clear()

class ConfigPanel(QGroupBox):
    """A panel for displaying the contents of the configuration file."""
    reload_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Configuration (`config/gestures.json`)", parent)
        layout = QVBoxLayout()
        self.config_display = QTextEdit()
        self.config_display.setReadOnly(True)
        self.reload_button = QPushButton("Reload Config")
        self.reload_button.clicked.connect(self.reload_requested.emit)
        layout.addWidget(self.config_display)
        layout.addWidget(self.reload_button)
        self.setLayout(layout)

    def set_config_text(self, text):
        self.config_display.setText(text)

class ManagementPanel(QGroupBox):
    """A panel with forms for saving new gestures and mappings."""
    new_gesture_to_save = pyqtSignal(dict)
    new_mapping_to_save = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__("Gesture & Mapping Management", parent)
        layout = QFormLayout()
        
        # Gesture Form
        self.gesture_name_input = QLineEdit()
        self.gesture_conditions_input = QTextEdit()
        add_gesture_button = QPushButton("Save New Gesture")
        add_gesture_button.clicked.connect(self._emit_new_gesture)
        layout.addRow("Gesture Name:", self.gesture_name_input)
        layout.addRow("Conditions (JSON):", self.gesture_conditions_input)
        layout.addRow(add_gesture_button)
        
        layout.addRow("---", QLabel()) # Separator

        # Mapping Form
        self.mapping_gesture_name_input = QLineEdit()
        self.mapping_details_input = QTextEdit()
        add_mapping_button = QPushButton("Save New Mapping")
        add_mapping_button.clicked.connect(self._emit_new_mapping)
        layout.addRow("Mapping Gesture Name:", self.mapping_gesture_name_input)
        layout.addRow("Mapping (JSON):", self.mapping_details_input)
        layout.addRow(add_mapping_button)

        self.setLayout(layout)

    def add_condition_to_form(self, condition_str):
        """Appends a new condition string to the conditions text area."""
        try:
            new_condition = json.loads(condition_str)
            current_conditions_str = self.gesture_conditions_input.toPlainText()
            
            current_conditions = []
            if current_conditions_str:
                current_conditions = json.loads(current_conditions_str)
            
            current_conditions.append(new_condition)
            self.gesture_conditions_input.setText(json.dumps(current_conditions, indent=2))
        except json.JSONDecodeError:
            self.gesture_conditions_input.setText(f"[\n  {condition_str}\n]")

    def _emit_new_gesture(self):
        """Validates and emits gesture data to be saved."""
        name = self.gesture_name_input.text()
        conditions_str = self.gesture_conditions_input.toPlainText()
        if not name or not conditions_str:
            QMessageBox.warning(self, "Input Error", "Please provide a gesture name and at least one condition.")
            return
        try:
            conditions = json.loads(conditions_str)
            gesture = {"name": name, "conditions": conditions}
            self.new_gesture_to_save.emit(gesture)
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Input Error", "Invalid JSON in the conditions field.")

    def _emit_new_mapping(self):
        """Validates and emits mapping data to be saved."""
        gesture_name = self.mapping_gesture_name_input.text()
        mapping_str = self.mapping_details_input.toPlainText()
        if not gesture_name or not mapping_str:
            QMessageBox.warning(self, "Input Error", "Please provide a gesture name and mapping details.")
            return
        try:
            mapping = json.loads(mapping_str)
            self.new_mapping_to_save.emit(gesture_name, mapping)
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Input Error", "Invalid JSON in the mapping field.")
    
    def clear_gesture_form(self):
        self.gesture_name_input.clear()
        self.gesture_conditions_input.clear()

    def clear_mapping_form(self):
        self.mapping_gesture_name_input.clear()
        self.mapping_details_input.clear()
