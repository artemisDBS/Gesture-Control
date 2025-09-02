"""
Command Execution Module
Handles mapping detected gestures to system commands and actions for the gesture mapper MVP.
"""

import pyautogui
import time
from typing import Dict, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes commands based on detected gestures."""
    
    def __init__(self, mappings: Dict[str, Dict], cooldown: float = 0.5):
        """
        Initialize the command executor.
        
        Args:
            mappings: Dictionary mapping gesture names to command definitions
            cooldown: Minimum time between executions of the same gesture (seconds)
        """
        self.mappings = mappings
        self.cooldown = cooldown
        self.last_execution = {}  # Track last execution time for each gesture
        
        # Configure pyautogui safety
        pyautogui.FAILSAFE = True  # Move mouse to corner to stop
        pyautogui.PAUSE = 0.1  # Small delay between actions
        
        logger.info(f"Command executor initialized with {len(mappings)} gesture mappings")
    
    def execute_command(self, gesture_name: str, analogue_value: Optional[float] = None) -> bool:
        """
        Execute the command associated with a detected gesture.
        
        Args:
            gesture_name: Name of the detected gesture
            analogue_value: Continuous value for analogue gestures (0.0 to 1.0)
            
        Returns:
            True if command was executed successfully, False otherwise
        """
        # Check if gesture is mapped
        if gesture_name not in self.mappings:
            logger.warning(f"No mapping found for gesture: {gesture_name}")
            return False
        
        # Check cooldown
        current_time = time.time()
        if gesture_name in self.last_execution:
            time_since_last = current_time - self.last_execution[gesture_name]
            if time_since_last < self.cooldown:
                logger.debug(f"Gesture {gesture_name} still in cooldown ({time_since_last:.2f}s)")
                return False
        
        # Get command definition
        command_def = self.mappings[gesture_name]
        command_type = command_def.get('type')
        
        try:
            success = False
            
            if command_type == 'key_press':
                success = self._execute_key_press(command_def)
            elif command_type == 'key_hold':
                success = self._execute_key_hold(command_def)
            elif command_type == 'mouse_click':
                success = self._execute_mouse_click(command_def)
            elif command_type == 'mouse_move':
                success = self._execute_mouse_move(command_def, analogue_value)
            elif command_type == 'scroll':
                success = self._execute_scroll(command_def, analogue_value)
            elif command_type == 'volume':
                success = self._execute_volume_control(command_def, analogue_value)
            elif command_type == 'custom':
                success = self._execute_custom_command(command_def, analogue_value)
            else:
                logger.warning(f"Unknown command type: {command_type}")
                return False
            
            if success:
                self.last_execution[gesture_name] = current_time
                logger.info(f"Executed {command_type} command for gesture: {gesture_name}")
                return True
            else:
                logger.error(f"Failed to execute {command_type} command for gesture: {gesture_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing command for gesture {gesture_name}: {str(e)}")
            return False
    
    def _execute_key_press(self, command_def: Dict[str, Any]) -> bool:
        """Execute a key press command."""
        key = command_def.get('key')
        if not key:
            logger.error("No key specified for key_press command")
            return False
        
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            logger.error(f"Failed to press key {key}: {str(e)}")
            return False
    
    def _execute_key_hold(self, command_def: Dict[str, Any]) -> bool:
        """Execute a key hold command."""
        key = command_def.get('key')
        duration = command_def.get('duration', 0.1)
        
        if not key:
            logger.error("No key specified for key_hold command")
            return False
        
        try:
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            logger.error(f"Failed to hold key {key}: {str(e)}")
            return False
    
    def _execute_mouse_click(self, command_def: Dict[str, Any]) -> bool:
        """Execute a mouse click command."""
        button = command_def.get('button', 'left')
        clicks = command_def.get('clicks', 1)
        
        try:
            pyautogui.click(button=button, clicks=clicks)
            return True
        except Exception as e:
            logger.error(f"Failed to click mouse {button}: {str(e)}")
            return False
    
    def _execute_mouse_move(self, command_def: Dict[str, Any], analogue_value: Optional[float]) -> bool:
        """Execute a mouse movement command."""
        if analogue_value is None:
            logger.warning("Mouse move command requires analogue value")
            return False
        
        # Get current mouse position
        current_x, current_y = pyautogui.position()
        
        # Calculate movement based on analogue value
        sensitivity = command_def.get('sensitivity', 100)
        movement_x = command_def.get('movement_x', 0)
        movement_y = command_def.get('movement_y', 0)
        
        # Apply analogue value to movement
        target_x = current_x + (movement_x * analogue_value * sensitivity)
        target_y = current_y + (movement_y * analogue_value * sensitivity)
        
        try:
            pyautogui.moveTo(target_x, target_y)
            return True
        except Exception as e:
            logger.error(f"Failed to move mouse: {str(e)}")
            return False
    
    def _execute_scroll(self, command_def: Dict[str, Any], analogue_value: Optional[float]) -> bool:
        """Execute a scroll command."""
        if analogue_value is None:
            logger.warning("Scroll command requires analogue value")
            return False
        
        sensitivity = command_def.get('sensitivity', 10)
        direction = command_def.get('direction', 'vertical')  # 'vertical' or 'horizontal'
        
        # Calculate scroll amount
        scroll_amount = int(analogue_value * sensitivity)
        
        try:
            if direction == 'horizontal':
                pyautogui.hscroll(scroll_amount)
            else:
                pyautogui.scroll(scroll_amount)
            return True
        except Exception as e:
            logger.error(f"Failed to scroll: {str(e)}")
            return False
    
    def _execute_volume_control(self, command_def: Dict[str, Any], analogue_value: Optional[float]) -> bool:
        """Execute volume control command."""
        if analogue_value is None:
            logger.warning("Volume control requires analogue value")
            return False
        
        # For MVP, simulate volume control via scroll
        # In a full implementation, you might use platform-specific volume APIs
        sensitivity = command_def.get('sensitivity', 5)
        scroll_amount = int(analogue_value * sensitivity)
        
        try:
            pyautogui.scroll(scroll_amount)
            return True
        except Exception as e:
            logger.error(f"Failed to control volume: {str(e)}")
            return False
    
    def _execute_custom_command(self, command_def: Dict[str, Any], analogue_value: Optional[float]) -> bool:
        """Execute a custom command (placeholder for future extensibility)."""
        command = command_def.get('command')
        if not command:
            logger.error("No command specified for custom command")
            return False
        
        try:
            # For MVP, just log the custom command
            # In future versions, this could execute shell commands, API calls, etc.
            logger.info(f"Custom command: {command} (analogue_value: {analogue_value})")
            return True
        except Exception as e:
            logger.error(f"Failed to execute custom command: {str(e)}")
            return False
    
    def get_available_gestures(self) -> list:
        """Get list of all available gesture names."""
        return list(self.mappings.keys())
    
    def get_command_info(self, gesture_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a gesture's command."""
        if gesture_name in self.mappings:
            return self.mappings[gesture_name].copy()
        return None
    
    def update_mappings(self, new_mappings: Dict[str, Dict]):
        """Update the gesture-to-command mappings."""
        self.mappings = new_mappings
        self.last_execution.clear()  # Reset execution history
        logger.info(f"Updated mappings with {len(new_mappings)} gesture mappings")


def test_command_executor():
    """Test function to verify command execution logic."""
    # Sample mappings
    test_mappings = {
        "pinch": {
            "type": "key_press",
            "key": "space"
        },
        "thumbs_up": {
            "type": "scroll",
            "direction": "vertical",
            "sensitivity": 10
        },
        "open_palm": {
            "type": "key_press",
            "key": "enter"
        }
    }
    
    executor = CommandExecutor(test_mappings)
    
    # Test available gestures
    gestures = executor.get_available_gestures()
    print(f"Available gestures: {gestures}")
    
    # Test command info
    for gesture in gestures:
        info = executor.get_command_info(gesture)
        print(f"Gesture '{gesture}': {info}")
    
    # Test execution (without actually executing)
    print("\nTesting command execution (dry run):")
    
    # Test key press
    success = executor.execute_command("pinch")
    print(f"Pinch gesture executed: {success}")
    
    # Test analogue command
    success = executor.execute_command("thumbs_up", analogue_value=0.5)
    print(f"Thumbs up gesture executed: {success}")
    
    # Test unknown gesture
    success = executor.execute_command("unknown_gesture")
    print(f"Unknown gesture executed: {success}")


if __name__ == "__main__":
    test_command_executor()
