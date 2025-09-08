"""
Contains the QWidget panels for the Gesture Mapper GUI.
- CreateGesturePanel: For creating new gestures from scratch.
- EditGesturePanel: For viewing, modifying, and managing existing gestures.
- MappingPanel: For assigning actions to gestures.
- SettingsPanel: For managing global normalization settings.
- InspectorPanel: Shared landmark inspector component.
"""
import json
import math
from PyQt5.QtWidgets import (QWidget, QFormLayout, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QLineEdit,
                             QComboBox, QMessageBox, QSpinBox, QListWidget,
                             QGroupBox, QCheckBox, QSplitter)
from PyQt5.QtCore import pyqtSignal, Qt


class InspectorPanel(QGroupBox):
    """A shared landmark inspector component for creating and editing conditions."""
    condition_generated = pyqtSignal(str)
    condition_updated = pyqtSignal(int, str)  # condition_index, condition_json
    selection_cleared = pyqtSignal()
    snapshot_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Landmark Inspector", parent)
        self.live_value = 0.0

        layout = QFormLayout()
        
        # --- Gesture Status Display ---
        self.detected_gesture_label = QLabel("None")
        font = self.detected_gesture_label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.detected_gesture_label.setFont(font)
        self.detected_gesture_label.setStyleSheet("color: #33AFFF;") # Light blue color
        layout.addRow("Detected Gesture:", self.detected_gesture_label)
        layout.addRow("---", QLabel()) # Separator

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
        self.add_condition_button = QPushButton("Add Condition")
        self.add_condition_button.clicked.connect(self.snapshot_requested.emit)
        self.update_condition_button = QPushButton("Update Condition")
        self.update_condition_button.clicked.connect(self._update_condition)
        self.update_condition_button.setVisible(False)  # Hidden by default
        clear_selection_button = QPushButton("Clear Selection")
        clear_selection_button.clicked.connect(self.selection_cleared.emit)
        button_layout.addWidget(self.add_condition_button)
        button_layout.addWidget(self.update_condition_button)
        button_layout.addWidget(clear_selection_button)
        layout.addRow(button_layout)
        
        self.generated_condition_display = QTextEdit()
        self.generated_condition_display.setReadOnly(True)
        add_condition_to_gesture_button = QPushButton("Add Condition to Gesture Form")
        add_condition_to_gesture_button.clicked.connect(self._emit_condition)
        layout.addRow("Generated Condition:", self.generated_condition_display)
        layout.addRow(add_condition_to_gesture_button)
        
        self.setLayout(layout)

    def set_detected_gesture(self, gesture_name):
        """Updates the gesture status label."""
        if gesture_name:
            self.detected_gesture_label.setText(gesture_name)
            self.detected_gesture_label.setStyleSheet("color: #50FA7B;") # Green for detected
        else:
            self.detected_gesture_label.setText("None")
            self.detected_gesture_label.setStyleSheet("color: #33AFFF;")

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

    def _update_condition(self):
        """Updates the currently selected condition with new values."""
        condition_str = self.generated_condition_display.toPlainText()
        if not condition_str:
            QMessageBox.warning(self, "Error", "No condition has been generated yet.")
            return
        
        # Get the current condition index from the parent (main window)
        # This will be set by the main window when a condition is selected
        if hasattr(self, 'editing_condition_index'):
            self.condition_updated.emit(self.editing_condition_index, condition_str)
        else:
            QMessageBox.warning(self, "Error", "No condition selected for editing.")

    def set_editing_mode(self, enabled, condition_index=None):
        """Switches between add and edit modes."""
        self.add_condition_button.setVisible(not enabled)
        self.update_condition_button.setVisible(enabled)
        if enabled:
            self.editing_condition_index = condition_index
        else:
            self.editing_condition_index = None

    def load_condition_for_editing(self, condition):
        """Loads a condition's data into the form for editing."""
        # Set the relationship type
        condition_type = condition.get('type', 'distance')
        if condition_type == 'distance':
            self.relationship_type_combo.setCurrentText("Distance")
        elif condition_type == 'angle':
            self.relationship_type_combo.setCurrentText("Angle")
        
        # Update constraint based on condition values
        if 'min' in condition and 'max' in condition:
            self.constraint_type_combo.setCurrentText("Between (Exact)")
        elif 'max' in condition:
            self.constraint_type_combo.setCurrentText("Less Than (Close)" if condition_type == 'distance' else "Less Than (Acute)")
        elif 'min' in condition:
            self.constraint_type_combo.setCurrentText("Greater Than (Far)" if condition_type == 'distance' else "Greater Than (Obtuse)")
        
        # Set importance
        importance = condition.get('importance', 'loose')
        self.importance_combo.setCurrentText(importance.capitalize())
        
        # Set points (this will be handled by the main window)
        points = condition.get('points', [])
        self.selected_points_label.setText(str(points))
        
        # Display the condition in the text area
        self.generated_condition_display.setText(json.dumps(condition, indent=2))

    def clear_selection(self):
        """Clears the UI elements in the inspector."""
        self.selected_points_label.setText("None")
        self.live_value_label.setText("N/A")
        self.generated_condition_display.clear()


class CreateGesturePanel(QWidget):
    """Panel for creating new gestures from scratch.
    Note: Uses the shared Inspector placed under the video. This panel only
    displays and manages the list of conditions in a human-friendly way.
    """
    gesture_saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conditions = []  # stores parsed condition dicts
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Gesture name input
        name_layout = QFormLayout()
        self.gesture_name_input = QLineEdit()
        self.gesture_name_input.setPlaceholderText("Enter gesture name...")
        name_layout.addRow("Gesture Name:", self.gesture_name_input)
        layout.addLayout(name_layout)
        
        # Local inspector placed between name and conditions
        self.inspector_panel = InspectorPanel()
        layout.addWidget(self.inspector_panel)

        # Conditions list and normalization settings
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Conditions list
        conditions_group = QGroupBox("Gesture Conditions")
        conditions_layout = QVBoxLayout()
        
        self.conditions_list = QListWidget()
        self.conditions_list.setMaximumHeight(200)
        # Panel already titled, remove redundant 'Conditions:' label
        conditions_layout.addWidget(self.conditions_list)
        
        # Condition management buttons
        condition_buttons = QHBoxLayout()
        self.remove_condition_button = QPushButton("Remove Selected")
        self.remove_condition_button.clicked.connect(self._remove_selected_condition)
        self.clear_conditions_button = QPushButton("Clear All")
        self.clear_conditions_button.clicked.connect(self._clear_all_conditions)
        condition_buttons.addWidget(self.remove_condition_button)
        condition_buttons.addWidget(self.clear_conditions_button)
        conditions_layout.addLayout(condition_buttons)
        
        conditions_group.setLayout(conditions_layout)
        right_layout.addWidget(conditions_group)
        
        # Save button
        self.save_button = QPushButton("Save New Gesture")
        self.save_button.clicked.connect(self._save_gesture)
        right_layout.addWidget(self.save_button)
        
        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget)
        self.setLayout(layout)

    def add_condition_to_form(self, condition_str):
        """Adds a condition to the conditions list."""
        try:
            condition = json.loads(condition_str)
            self.conditions.append(condition)
            self.conditions_list.addItem(self._describe_condition(condition))
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid condition JSON.")

    def _remove_selected_condition(self):
        """Removes the selected condition from the list."""
        current_row = self.conditions_list.currentRow()
        if current_row >= 0:
            self.conditions.pop(current_row)
            self.conditions_list.takeItem(current_row)

    def _clear_all_conditions(self):
        """Clears all conditions from the list."""
        self.conditions.clear()
        self.conditions_list.clear()

    def _save_gesture(self):
        """Saves the new gesture."""
        name = self.gesture_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a gesture name.")
            return
        
        # Use collected parsed conditions
        if not self.conditions:
            QMessageBox.warning(self, "Error", "Please add at least one condition.")
            return
        
        # Create gesture data
        gesture_data = {
            "name": name,
            "conditions": self.conditions.copy()
        }
        
        # Note: Normalization overrides are now handled by the main window's left panel
        
        self.gesture_saved.emit(gesture_data)

    def _describe_condition(self, condition: dict) -> str:
        ctype = condition.get('type', 'unknown')
        importance = condition.get('importance', 'loose')
        if ctype == 'distance' and len(condition.get('points', [])) == 2:
            p = condition['points']
            base = f"Distance between points {p[0]} and {p[1]}"
            if 'min' in condition and 'max' in condition:
                base += f" (between {condition['min']:.3f} and {condition['max']:.3f})"
            elif 'max' in condition:
                base += f" (less than {condition['max']:.3f})"
            elif 'min' in condition:
                base += f" (greater than {condition['min']:.3f})"
            return base + f" [{importance}]"
        if ctype == 'angle' and len(condition.get('points', [])) == 3:
            p = condition['points']
            base = f"Angle at {p[1]} between {p[0]} and {p[2]}"
            if 'min' in condition and 'max' in condition:
                base += f" (between {condition['min']:.2f}° and {condition['max']:.2f}°)"
            elif 'max' in condition:
                base += f" (less than {condition['max']:.2f}°)"
            elif 'min' in condition:
                base += f" (greater than {condition['min']:.2f}°)"
            return base + f" [{importance}]"
        return ctype.title()

    def clear_form(self):
        """Clears the form for creating a new gesture."""
        self.gesture_name_input.clear()
        self.conditions.clear()
        self.conditions_list.clear()
        # nothing else to clear beyond list

    # Shared inspector handles live values and snapshots


class EditGesturePanel(QWidget):
    """Panel for editing existing gestures."""
    gesture_updated = pyqtSignal(str, dict)  # gesture_name, gesture_data
    gesture_deleted = pyqtSignal(str)  # gesture_name
    gesture_load_requested = pyqtSignal(str)  # gesture_name
    condition_generated = pyqtSignal(str)
    condition_updated = pyqtSignal(int, str)
    condition_selected = pyqtSignal(int)
    selection_cleared = pyqtSignal()
    snapshot_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_gesture = None
        self.current_conditions = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Gesture selection with helper hint
        selection_layout = QHBoxLayout()
        self.gesture_selector = QComboBox()
        self.gesture_selector.setPlaceholderText("Select a gesture to edit...")
        self.gesture_selector.currentIndexChanged.connect(self._load_gesture)
        self.load_button = QPushButton("Load Gesture")
        self.load_button.clicked.connect(self._load_gesture)
        selection_layout.addWidget(QLabel("Gesture:"))
        selection_layout.addWidget(self.gesture_selector)
        selection_layout.addWidget(self.load_button)
        layout.addLayout(selection_layout)

        # Remove guidance text to save space
        
        # Local inspector placed above the conditions list
        self.inspector_panel = InspectorPanel()
        layout.addWidget(self.inspector_panel)

        # Conditions list and controls
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Gesture info
        info_group = QGroupBox("Gesture Information")
        info_layout = QFormLayout()
        self.gesture_name_label = QLabel("No gesture loaded")
        self.condition_count_label = QLabel("0 conditions")
        info_layout.addRow("Name:", self.gesture_name_label)
        info_layout.addRow("Conditions:", self.condition_count_label)
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        # Conditions list
        conditions_group = QGroupBox("Gesture Conditions")
        conditions_layout = QVBoxLayout()
        
        self.conditions_list = QListWidget()
        self.conditions_list.setMaximumHeight(200)
        self.conditions_list.itemClicked.connect(self._on_condition_selected)
        # Remove redundant 'Conditions:' label
        conditions_layout.addWidget(self.conditions_list)
        
        # Condition management buttons
        condition_buttons = QHBoxLayout()
        self.remove_condition_button = QPushButton("Remove Selected")
        self.remove_condition_button.clicked.connect(self._remove_selected_condition)
        self.clear_conditions_button = QPushButton("Clear All")
        self.clear_conditions_button.clicked.connect(self._clear_all_conditions)
        condition_buttons.addWidget(self.remove_condition_button)
        condition_buttons.addWidget(self.clear_conditions_button)
        conditions_layout.addLayout(condition_buttons)
        
        conditions_group.setLayout(conditions_layout)
        right_layout.addWidget(conditions_group)
        
        # Advanced Normalization Settings
        self.normalization_group = QGroupBox("Advanced Normalization")
        self.normalization_group.setCheckable(True)
        self.normalization_group.setChecked(False)
        normalization_layout = QFormLayout()
        
        self.displacement_checkbox = QCheckBox("Displacement Invariant")
        self.scale_checkbox = QCheckBox("Scale Invariant")
        self.rotation_checkbox = QCheckBox("Rotation Invariant")
        
        normalization_layout.addRow(self.displacement_checkbox)
        normalization_layout.addRow(self.scale_checkbox)
        normalization_layout.addRow(self.rotation_checkbox)
        
        self.normalization_group.setLayout(normalization_layout)
        right_layout.addWidget(self.normalization_group)
        
        # Action buttons
        action_buttons = QHBoxLayout()
        self.update_button = QPushButton("Update Gesture")
        self.update_button.clicked.connect(self._update_gesture)
        self.delete_button = QPushButton("Delete Gesture")
        self.delete_button.clicked.connect(self._delete_gesture)
        action_buttons.addWidget(self.update_button)
        action_buttons.addWidget(self.delete_button)
        right_layout.addLayout(action_buttons)
        
        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget)
        self.setLayout(layout)


    def update_gesture_list(self, gesture_names):
        """Updates the gesture selector dropdown."""
        self.gesture_selector.clear()
        self.gesture_selector.addItems(gesture_names)

    def load_gesture(self, gesture):
        """Loads a gesture for editing."""
        self.current_gesture = gesture
        self.current_conditions = gesture.get('conditions', []).copy()
        
        # Update UI
        self.gesture_name_label.setText(gesture['name'])
        self.condition_count_label.setText(f"{len(self.current_conditions)} conditions")
        
        # Populate conditions list
        self.populate_conditions(self.current_conditions)
        
        # Load normalization overrides if they exist
        overrides = gesture.get('normalization_overrides')
        if overrides:
            self.normalization_group.setChecked(True)
            self.displacement_checkbox.setChecked(overrides.get('displacement_invariant', False))
            self.scale_checkbox.setChecked(overrides.get('scale_invariant', False))
            self.rotation_checkbox.setChecked(overrides.get('rotation_invariant', False))
        else:
            self.normalization_group.setChecked(False)

    def populate_conditions(self, conditions):
        """Populates the conditions list widget."""
        self.conditions_list.clear()
        for i, condition in enumerate(conditions):
            condition_type = condition.get('type', 'unknown')
            points = condition.get('points', [])
            importance = condition.get('importance', 'loose')
            
            # Create a human-readable description
            if condition_type == 'distance' and len(points) == 2:
                desc = f"Distance between points {points[0]} and {points[1]}"
            elif condition_type == 'angle' and len(points) == 3:
                desc = f"Angle at point {points[1]} between {points[0]} and {points[2]}"
            else:
                desc = f"{condition_type.title()} condition"
            
            # Add constraints
            if 'min' in condition and 'max' in condition:
                desc += f" (between {condition['min']:.3f} and {condition['max']:.3f})"
            elif 'max' in condition:
                desc += f" (less than {condition['max']:.3f})"
            elif 'min' in condition:
                desc += f" (greater than {condition['min']:.3f})"
            
            desc += f" [{importance}]"
            
            self.conditions_list.addItem(desc)

    def _on_condition_selected(self, item):
        """Handles when a condition is selected from the list."""
        row = self.conditions_list.row(item)
        self.condition_selected.emit(row)

    def load_condition_for_editing(self, condition, condition_index):
        """Loads a condition into the inspector for editing."""
        self.inspector_panel.load_condition_for_editing(condition)
        self.inspector_panel.set_editing_mode(True, condition_index)

    def add_condition_to_form(self, condition_str):
        """Adds a condition to the conditions list."""
        try:
            condition = json.loads(condition_str)
            self.current_conditions.append(condition)
            self.populate_conditions(self.current_conditions)
            self.condition_count_label.setText(f"{len(self.current_conditions)} conditions")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid condition JSON.")

    def _remove_selected_condition(self):
        """Removes the selected condition from the list."""
        current_row = self.conditions_list.currentRow()
        if current_row >= 0:
            self.current_conditions.pop(current_row)
            self.populate_conditions(self.current_conditions)
            self.condition_count_label.setText(f"{len(self.current_conditions)} conditions")

    def _clear_all_conditions(self):
        """Clears all conditions from the list."""
        self.current_conditions.clear()
        self.populate_conditions(self.current_conditions)
        self.condition_count_label.setText("0 conditions")

    def _load_gesture(self):
        """Loads the selected gesture for editing."""
        gesture_name = self.gesture_selector.currentText()
        if gesture_name:
            self.gesture_load_requested.emit(gesture_name)

    def _update_gesture(self):
        """Updates the current gesture."""
        if not self.current_gesture:
            QMessageBox.warning(self, "Error", "No gesture loaded.")
            return
        
        if not self.current_conditions:
            QMessageBox.warning(self, "Error", "Please add at least one condition.")
            return
        
        # Create updated gesture data
        gesture_data = {
            "name": self.current_gesture['name'],
            "conditions": self.current_conditions.copy()
        }
        
        # Add normalization overrides if specified
        if self.normalization_group.isChecked():
            gesture_data["normalization_overrides"] = {
                "displacement_invariant": self.displacement_checkbox.isChecked(),
                "scale_invariant": self.scale_checkbox.isChecked(),
                "rotation_invariant": self.rotation_checkbox.isChecked()
            }
        
        self.gesture_updated.emit(self.current_gesture['name'], gesture_data)

    def _delete_gesture(self):
        """Deletes the current gesture."""
        if not self.current_gesture:
            QMessageBox.warning(self, "Error", "No gesture loaded.")
            return
        
        self.gesture_deleted.emit(self.current_gesture['name'])

    def set_detected_gesture(self, gesture_name):
        """Updates the detected gesture display."""
        self.inspector_panel.set_detected_gesture(gesture_name)

    def update_live_value(self, landmarks, selected_points, gesture_detector):
        """Updates the live value display."""
        self.inspector_panel.update_live_value(landmarks, selected_points, gesture_detector)

    def set_selected_points_text(self, points):
        """Sets the selected points text."""
        self.inspector_panel.set_selected_points_text(points)

    def clear_selection(self):
        """Clears the selection."""
        self.inspector_panel.clear_selection()

    def snapshot_condition(self, selected_points):
        """Takes a snapshot of the current condition."""
        self.inspector_panel.snapshot_condition(selected_points)


class MappingPanel(QWidget):
    """Panel for assigning actions to gestures."""
    mapping_saved = pyqtSignal(str, dict)  # gesture_name, mapping_data

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout()
        
        # Gesture selection
        self.gesture_selector = QComboBox()
        self.gesture_selector.setPlaceholderText("Select a gesture...")
        layout.addRow("Gesture:", self.gesture_selector)
        
        # Command type selection
        self.command_type_combo = QComboBox()
        self.command_type_combo.addItems(["key_press", "mouse_click", "scroll"])
        self.command_type_combo.currentTextChanged.connect(self._update_command_widgets)
        layout.addRow("Command Type:", self.command_type_combo)
        
        # Dynamic command options container
        self.command_options_widget = QWidget()
        self.command_options_layout = QFormLayout()
        self.command_options_widget.setLayout(self.command_options_layout)
        layout.addRow("Command Options:", self.command_options_widget)
        
        # Initialize with default widgets
        self._create_command_widgets("key_press")
        
        # Save button
        self.save_button = QPushButton("Save Mapping")
        self.save_button.clicked.connect(self._save_mapping)
        layout.addRow(self.save_button)
        
        self.setLayout(layout)

    def update_gesture_list(self, gesture_names):
        """Updates the gesture selector dropdown."""
        self.gesture_selector.clear()
        self.gesture_selector.addItems(gesture_names)

    def _create_command_widgets(self, command_type):
        """Create dynamic widgets based on the selected command type."""
        # Clear existing widgets
        for i in reversed(range(self.command_options_layout.count())):
            child = self.command_options_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Store widget references for later access
        self.command_widgets = {}
        
        if command_type == "key_press":
            self.command_widgets['key'] = QLineEdit()
            self.command_widgets['key'].setPlaceholderText("e.g., 'w', 'enter', 'space'")
            self.command_options_layout.addRow("Key:", self.command_widgets['key'])
            
        elif command_type == "mouse_click":
            self.command_widgets['button'] = QComboBox()
            self.command_widgets['button'].addItems(["left", "right", "middle"])
            self.command_widgets['clicks'] = QSpinBox()
            self.command_widgets['clicks'].setRange(1, 10)
            self.command_widgets['clicks'].setValue(1)
            self.command_options_layout.addRow("Button:", self.command_widgets['button'])
            self.command_options_layout.addRow("Number of Clicks:", self.command_widgets['clicks'])
            
        elif command_type == "scroll":
            self.command_widgets['direction'] = QComboBox()
            self.command_widgets['direction'].addItems(["up", "down", "left", "right"])
            self.command_widgets['sensitivity'] = QSpinBox()
            self.command_widgets['sensitivity'].setRange(1, 100)
            self.command_widgets['sensitivity'].setValue(10)
            self.command_options_layout.addRow("Direction:", self.command_widgets['direction'])
            self.command_options_layout.addRow("Sensitivity:", self.command_widgets['sensitivity'])

    def _update_command_widgets(self, command_type):
        """Update the command options when the type changes."""
        self._create_command_widgets(command_type)

    def _save_mapping(self):
        """Saves the mapping."""
        gesture_name = self.gesture_selector.currentText()
        if not gesture_name:
            QMessageBox.warning(self, "Error", "Please select a gesture.")
            return
        
        # Build mapping from current widget values
        command_type = self.command_type_combo.currentText()
        mapping = {"type": command_type}
        
        try:
            if command_type == "key_press":
                key = self.command_widgets['key'].text().strip()
                if not key:
                    QMessageBox.warning(self, "Error", "Please enter a key.")
                    return
                mapping["key"] = key
                
            elif command_type == "mouse_click":
                button = self.command_widgets['button'].currentText()
                clicks = self.command_widgets['clicks'].value()
                mapping["button"] = button
                mapping["clicks"] = clicks
                
            elif command_type == "scroll":
                direction = self.command_widgets['direction'].currentText()
                sensitivity = self.command_widgets['sensitivity'].value()
                mapping["direction"] = direction
                mapping["sensitivity"] = sensitivity
            
            self.mapping_saved.emit(gesture_name, mapping)
            
        except KeyError as e:
            QMessageBox.warning(self, "Error", f"Missing required field: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error creating mapping: {str(e)}")

    def clear_form(self):
        """Clears the form."""
        self.gesture_selector.setCurrentIndex(-1)
        self.command_type_combo.setCurrentText("key_press")
        self._create_command_widgets("key_press")


class SettingsPanel(QWidget):
    """Panel for managing global normalization settings."""
    settings_saved = pyqtSignal(dict)  # settings dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Settings group
        settings_group = QGroupBox("Global Normalization Settings")
        settings_layout = QFormLayout()
        
        self.displacement_checkbox = QCheckBox("Displacement Invariant")
        self.scale_checkbox = QCheckBox("Scale Invariant")
        self.rotation_checkbox = QCheckBox("Rotation Invariant")
        
        settings_layout.addRow(self.displacement_checkbox)
        settings_layout.addRow(self.scale_checkbox)
        settings_layout.addRow(self.rotation_checkbox)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Info text
        info_text = QLabel("""
        <b>Global Settings:</b><br>
        These settings will be used as defaults for all gestures that don't have their own specific overrides.<br><br>
        <b>Displacement Invariant:</b> Centers gestures on the wrist (point 0)<br>
        <b>Scale Invariant:</b> Normalizes gestures by hand size<br>
        <b>Rotation Invariant:</b> Rotates gestures so wrist-to-index is vertical
        """)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(info_text)
        
        # Save button
        self.save_button = QPushButton("Save Global Settings")
        self.save_button.clicked.connect(self._save_settings)
        layout.addWidget(self.save_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.setLayout(layout)

    def update_settings(self, settings):
        """Updates the settings checkboxes."""
        self.displacement_checkbox.setChecked(settings.get('displacement_invariant', False))
        self.scale_checkbox.setChecked(settings.get('scale_invariant', False))
        self.rotation_checkbox.setChecked(settings.get('rotation_invariant', False))

    def _save_settings(self):
        """Saves the global settings."""
        settings = {
            'displacement_invariant': self.displacement_checkbox.isChecked(),
            'scale_invariant': self.scale_checkbox.isChecked(),
            'rotation_invariant': self.rotation_checkbox.isChecked()
        }
        self.settings_saved.emit(settings)