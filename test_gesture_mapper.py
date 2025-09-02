#!/usr/bin/env python3
"""
Test Script for Gesture Mapper MVP
Tests all components individually to ensure they're working correctly.
"""

import sys
import os
import json

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from input_capture import HandCapture
        print("✓ HandCapture imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import HandCapture: {e}")
        return False
    
    try:
        from gesture_detection import GestureDetector
        print("✓ GestureDetector imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import GestureDetector: {e}")
        return False
    
    try:
        from command_executor import CommandExecutor
        print("✓ CommandExecutor imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import CommandExecutor: {e}")
        return False
    
    try:
        from config_manager import ConfigManager
        print("✓ ConfigManager imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ConfigManager: {e}")
        return False
    
    return True

def test_config_manager():
    """Test configuration management functionality."""
    print("\nTesting ConfigManager...")
    
    try:
        # Create a temporary config file
        test_config_path = "test_config.json"
        
        config_mgr = ConfigManager(test_config_path)
        
        # Test basic functionality
        config = config_mgr.get_config()
        gestures = config_mgr.get_gestures()
        mappings = config_mgr.get_mappings()
        
        print(f"✓ Config loaded: {len(gestures)} gestures, {len(mappings)} mappings")
        
        # Test adding a gesture
        new_gesture = {
            "name": "test_gesture",
            "conditions": [
                {
                    "type": "distance",
                    "points": [4, 8],
                    "max": 0.1
                }
            ]
        }
        
        success = config_mgr.add_gesture(new_gesture)
        if success:
            print("✓ Added test gesture successfully")
        else:
            print("✗ Failed to add test gesture")
            return False
        
        # Test adding a mapping
        new_mapping = {
            "type": "key_press",
            "key": "t"
        }
        
        success = config_mgr.add_mapping("test_gesture", new_mapping)
        if success:
            print("✓ Added test mapping successfully")
        else:
            print("✗ Failed to add test mapping")
            return False
        
        # Clean up
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
        
        print("✓ ConfigManager tests passed")
        return True
        
    except Exception as e:
        print(f"✗ ConfigManager test failed: {e}")
        return False

def test_gesture_detector():
    """Test gesture detection functionality."""
    print("\nTesting GestureDetector...")
    
    try:
        # Create test config
        test_config = {
            "transformations": {
                "displacement_invariant": True,
                "scale_invariant": True,
                "rotation_invariant": False
            },
            "gestures": [
                {
                    "name": "test_pinch",
                    "conditions": [
                        {
                            "type": "distance",
                            "points": [4, 8],
                            "max": 0.05
                        }
                    ]
                }
            ]
        }
        
        detector = GestureDetector(test_config)
        
        # Test with sample landmarks (pinch gesture)
        sample_landmarks = []
        for i in range(21):
            if i == 4:  # Thumb tip
                sample_landmarks.append({'x': 0.48, 'y': 0.48, 'z': 0.0})
            elif i == 8:  # Index tip
                sample_landmarks.append({'x': 0.49, 'y': 0.49, 'z': 0.0})
            else:
                sample_landmarks.append({'x': 0.5, 'y': 0.5, 'z': 0.0})
        
        # Test normalization
        normalized = detector.normalize_keypoints(sample_landmarks)
        if len(normalized) == 21:
            print("✓ Keypoint normalization working")
        else:
            print("✗ Keypoint normalization failed")
            return False
        
        # Test gesture detection
        gesture = detector.detect_gesture(normalized)
        if gesture == "test_pinch":
            print("✓ Gesture detection working")
        else:
            print(f"✗ Gesture detection failed, got: {gesture}")
            return False
        
        print("✓ GestureDetector tests passed")
        return True
        
    except Exception as e:
        print(f"✗ GestureDetector test failed: {e}")
        return False

def test_command_executor():
    """Test command execution functionality."""
    print("\nTesting CommandExecutor...")
    
    try:
        # Create test mappings
        test_mappings = {
            "test_gesture": {
                "type": "key_press",
                "key": "t"
            }
        }
        
        executor = CommandExecutor(test_mappings)
        
        # Test available gestures
        gestures = executor.get_available_gestures()
        if "test_gesture" in gestures:
            print("✓ Command executor initialized correctly")
        else:
            print("✗ Command executor initialization failed")
            return False
        
        # Test command info
        info = executor.get_command_info("test_gesture")
        if info and info.get('type') == 'key_press':
            print("✓ Command info retrieval working")
        else:
            print("✗ Command info retrieval failed")
            return False
        
        print("✓ CommandExecutor tests passed")
        return True
        
    except Exception as e:
        print(f"✗ CommandExecutor test failed: {e}")
        return False

def test_config_file():
    """Test that the configuration file exists and is valid."""
    print("\nTesting configuration file...")
    
    config_path = "config/gestures.json"
    
    if not os.path.exists(config_path):
        print(f"✗ Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Check required sections
        required_sections = ['transformations', 'gestures', 'mappings']
        for section in required_sections:
            if section not in config:
                print(f"✗ Missing required section: {section}")
                return False
        
        print(f"✓ Configuration file valid: {len(config['gestures'])} gestures, {len(config['mappings'])} mappings")
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in configuration file: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading configuration file: {e}")
        return False

def main():
    """Run all tests."""
    print("Gesture Mapper MVP - Component Tests")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_config_file,
        test_config_manager,
        test_gesture_detector,
        test_command_executor
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"Test {test.__name__} failed!")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The gesture mapper is ready to run.")
        print("\nTo start the application, run:")
        print("python src/main.py")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
