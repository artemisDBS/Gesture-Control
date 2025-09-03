"""
Configuration Management Module
Handles loading and saving gesture configurations for the gesture mapper MVP.
"""

import json
import os
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages gesture configuration loading, saving, and validation."""
    
    def __init__(self, config_path: str = "config/gestures.json"):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = {}
        # The default_config is now a clean slate.
        self.default_config = self._get_default_config()
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Load configuration
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration structure. 
        This is a blank slate, used for first-time setup or as a fallback.
        """
        return {
            "transformations": {
                "displacement_invariant": True,
                "scale_invariant": True,
                "rotation_invariant": False
            },
            "gestures": [],
            "mappings": {}
        }
    
    def load_config(self) -> bool:
        """
        Load configuration from file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                return True
            else:
                logger.warning(f"Configuration file not found at {self.config_path}")
                logger.info("Creating default (empty) configuration")
                self.config = self.default_config.copy()
                self.save_config()
                return True
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {str(e)}")
            logger.info("Loading default (empty) configuration as a fallback.")
            self.config = self.default_config.copy()
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            logger.info("Loading default (empty) configuration as a fallback.")
            self.config = self.default_config.copy()
            return False
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.config.copy()
    
    def get_transformations(self) -> Dict[str, bool]:
        """Get transformation settings."""
        return self.config.get('transformations', {}).copy()
    
    def get_gestures(self) -> list:
        """Get gesture definitions."""
        return self.config.get('gestures', []).copy()
    
    def get_mappings(self) -> Dict[str, Dict]:
        """Get gesture-to-command mappings."""
        return self.config.get('mappings', {}).copy()
    
    def update_transformations(self, transformations: Dict[str, bool]) -> bool:
        """
        Update transformation settings.
        
        Args:
            transformations: New transformation settings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.config['transformations'] = transformations.copy()
            return self.save_config()
        except Exception as e:
            logger.error(f"Error updating transformations: {str(e)}")
            return False
    
    def add_gesture(self, gesture: Dict[str, Any]) -> bool:
        """
        Add a new gesture definition.
        
        Args:
            gesture: Gesture definition dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate gesture
            if not self._validate_gesture(gesture):
                logger.error("Invalid gesture definition")
                return False
            
            # Check for duplicate names
            existing_names = [g['name'] for g in self.config.get('gestures', [])]
            if gesture['name'] in existing_names:
                logger.error(f"Gesture with name '{gesture['name']}' already exists")
                return False
            
            self.config.setdefault('gestures', []).append(gesture)
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Error adding gesture: {str(e)}")
            return False
    
    def update_gesture(self, gesture_name: str, new_gesture: Dict[str, Any]) -> bool:
        """
        Update an existing gesture definition.
        
        Args:
            gesture_name: Name of the gesture to update
            new_gesture: New gesture definition
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate gesture
            if not self._validate_gesture(new_gesture):
                logger.error("Invalid gesture definition")
                return False
            
            gestures = self.config.get('gestures', [])
            for i, gesture in enumerate(gestures):
                if gesture['name'] == gesture_name:
                    gestures[i] = new_gesture.copy()
                    return self.save_config()
            
            logger.error(f"Gesture '{gesture_name}' not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating gesture: {str(e)}")
            return False
    
    def remove_gesture(self, gesture_name: str) -> bool:
        """
        Remove a gesture definition.
        
        Args:
            gesture_name: Name of the gesture to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            gestures = self.config.get('gestures', [])
            self.config['gestures'] = [g for g in gestures if g['name'] != gesture_name]
            
            # Also remove the mapping if it exists
            if 'mappings' in self.config and gesture_name in self.config['mappings']:
                del self.config['mappings'][gesture_name]
            
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Error removing gesture: {str(e)}")
            return False
    
    def add_mapping(self, gesture_name: str, mapping: Dict[str, Any]) -> bool:
        """
        Add or update a gesture-to-command mapping.
        
        Args:
            gesture_name: Name of the gesture
            mapping: Command mapping definition
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate mapping
            if not self._validate_mapping(mapping):
                logger.error("Invalid mapping definition")
                return False
            
            self.config.setdefault('mappings', {})[gesture_name] = mapping.copy()
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Error adding mapping: {str(e)}")
            return False
    
    def remove_mapping(self, gesture_name: str) -> bool:
        """
        Remove a gesture-to-command mapping.
        
        Args:
            gesture_name: Name of the gesture
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'mappings' in self.config and gesture_name in self.config['mappings']:
                del self.config['mappings'][gesture_name]
                return self.save_config()
            return True
            
        except Exception as e:
            logger.error(f"Error removing mapping: {str(e)}")
            return False
    
    def _validate_gesture(self, gesture: Dict[str, Any]) -> bool:
        """Validate a gesture definition."""
        required_fields = ['name', 'conditions']
        
        for field in required_fields:
            if field not in gesture:
                logger.error(f"Missing required field: {field}")
                return False
        
        conditions = gesture.get('conditions', [])
        if not isinstance(conditions, list) or len(conditions) == 0:
            logger.error("Gesture must have at least one condition")
            return False
        
        for condition in conditions:
            if not self._validate_condition(condition):
                return False
        
        return True
    
    def _validate_condition(self, condition: Dict[str, Any]) -> bool:
        """Validate a condition definition."""
        required_fields = ['type']
        
        for field in required_fields:
            if field not in condition:
                logger.error(f"Missing required field in condition: {field}")
                return False
        
        condition_type = condition['type']
        
        if condition_type == 'distance':
            return self._validate_distance_condition(condition)
        elif condition_type == 'angle':
            return self._validate_angle_condition(condition)
        elif condition_type == 'position':
            return self._validate_position_condition(condition)
        else:
            logger.error(f"Unknown condition type: {condition_type}")
            return False
    
    def _validate_distance_condition(self, condition: Dict[str, Any]) -> bool:
        """Validate a distance condition."""
        if 'points' not in condition or not isinstance(condition['points'], list):
            logger.error("Distance condition must have 'points' list")
            return False
        
        if len(condition['points']) != 2:
            logger.error("Distance condition must have exactly 2 points")
            return False
        
        has_constraint = 'min' in condition or 'max' in condition
        if not has_constraint:
            logger.error("Distance condition must have 'min' or 'max' constraint")
            return False
        
        return True
    
    def _validate_angle_condition(self, condition: Dict[str, Any]) -> bool:
        """Validate an angle condition."""
        if 'points' not in condition or not isinstance(condition['points'], list):
            logger.error("Angle condition must have 'points' list")
            return False
        
        if len(condition['points']) != 3:
            logger.error("Angle condition must have exactly 3 points")
            return False
        
        has_constraint = 'min' in condition or 'max' in condition
        if not has_constraint:
            logger.error("Angle condition must have 'min' or 'max' constraint")
            return False
        
        return True
    
    def _validate_position_condition(self, condition: Dict[str, Any]) -> bool:
        """Validate a position condition."""
        if 'point' not in condition:
            logger.error("Position condition must have 'point' field")
            return False
        
        has_constraint = any(k in condition for k in ['x_min', 'x_max', 'y_min', 'y_max'])
        if not has_constraint:
            logger.error("Position condition must have at least one coordinate constraint")
            return False
        
        return True
    
    def _validate_mapping(self, mapping: Dict[str, Any]) -> bool:
        """Validate a mapping definition."""
        if 'type' not in mapping:
            logger.error("Mapping must have 'type' field")
            return False
        
        mapping_type = mapping['type']
        
        if mapping_type == 'key_press': return 'key' in mapping
        elif mapping_type == 'key_hold': return 'key' in mapping
        elif mapping_type == 'mouse_click': return True
        elif mapping_type == 'mouse_move': return 'sensitivity' in mapping
        elif mapping_type == 'scroll': return 'sensitivity' in mapping
        elif mapping_type == 'volume': return 'sensitivity' in mapping
        elif mapping_type == 'custom': return 'command' in mapping
        else:
            logger.error(f"Unknown mapping type: {mapping_type}")
            return False
