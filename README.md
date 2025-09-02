# Gesture Mapper MVP

A real-time hand gesture recognition and command mapping system built with OpenCV, MediaPipe, and Python. This MVP focuses on the core essentials: capturing hand keypoints, defining basic gestures, mapping them to simple commands, and handling basic transformations.

## 🎯 MVP Features

### Core Functionality
- **Real-time hand detection** using MediaPipe Hands (21 keypoints)
- **User-defined gestures** based on relative positions of keypoints
- **Basic command mapping** (key presses, mouse actions, scrolling)
- **Transformation handling** (displacement, scale, and rotation invariance)
- **Analogue control** for continuous gestures (e.g., volume control)

### Gesture Types Supported
- **Distance-based**: Pinch gestures, finger spacing
- **Angle-based**: Thumbs up, hand orientation
- **Position-based**: Hand location relative to screen

### Command Types
- **Key Press**: Simulate keyboard input
- **Mouse Click**: Left/right clicks
- **Scroll**: Vertical/horizontal scrolling
- **Volume Control**: System volume adjustment
- **Custom**: Extensible for future commands

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Webcam
- Windows/macOS/Linux

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd gesture-mapper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   python test_gesture_mapper.py
   ```

4. **Run the application**
   ```bash
   python src/main.py
   ```

## 📁 Project Structure

```
gesture-mapper/
├── src/                    # Source code
│   ├── input_capture.py    # Webcam and MediaPipe integration
│   ├── gesture_detection.py # Gesture recognition and normalization
│   ├── command_executor.py # Command execution and mapping
│   ├── config_manager.py   # Configuration management
│   └── main.py            # Main application
├── config/
│   └── gestures.json      # Gesture definitions and mappings
├── requirements.txt        # Python dependencies
├── test_gesture_mapper.py # Component testing script
└── README.md              # This file
```

## ⚙️ Configuration

The system uses a JSON configuration file (`config/gestures.json`) to define gestures and their mappings.

### Example Configuration

```json
{
  "transformations": {
    "displacement_invariant": true,
    "scale_invariant": true,
    "rotation_invariant": false
  },
  "gestures": [
    {
      "name": "pinch",
      "conditions": [
        {
          "type": "distance",
          "points": [4, 8],
          "max": 0.05
        }
      ]
    }
  ],
  "mappings": {
    "pinch": {
      "type": "key_press",
      "key": "space"
    }
  }
}
```

### Configuration Options

#### Transformations
- **displacement_invariant**: Gestures work regardless of hand position on screen
- **scale_invariant**: Gestures work regardless of hand size/distance from camera
- **rotation_invariant**: Gestures work regardless of hand rotation

#### Gesture Conditions
- **distance**: Distance between two keypoints
- **angle**: Angle formed by three keypoints
- **position**: Absolute position of a keypoint

#### Command Types
- **key_press**: Single key press
- **key_hold**: Key held for specified duration
- **mouse_click**: Mouse click (left/right, single/double)
- **scroll**: Scroll wheel movement
- **volume**: System volume control
- **custom**: Custom commands (extensible)

## 🎮 Usage

### Running the Application

1. **Start the application**
   ```bash
   python src/main.py
   ```

2. **Show your hand to the camera**
   - The system will detect your hand and display 21 keypoints
   - Keypoints are numbered 0-20 (0 = wrist, 4 = thumb tip, 8 = index tip, etc.)

3. **Perform gestures**
   - **Pinch**: Bring thumb tip (4) close to index tip (8)
   - **Thumbs up**: Raise thumb with other fingers closed
   - **Open palm**: Spread fingers apart

### Controls
- **q**: Quit application
- **r**: Reload configuration file
- **h**: Show help information

### Debug Information
The application displays:
- Real-time hand landmarks and connections
- Detected gesture names
- Command execution status
- FPS and frame count
- Analogue values for continuous gestures

## 🔧 Customization

### Adding New Gestures

1. **Edit the configuration file** (`config/gestures.json`)
2. **Define gesture conditions** using the supported types
3. **Map to commands** using the available command types
4. **Reload configuration** by pressing 'r' in the application

### Example: Adding a Fist Gesture

```json
{
  "name": "fist",
  "conditions": [
    {
      "type": "distance",
      "points": [0, 8],
      "max": 0.1
    }
  ]
}
```

### Example: Adding a Custom Command

```json
{
  "type": "custom",
  "command": "open_notepad"
}
```

## 🧪 Testing

### Component Testing
Run the test script to verify all components are working:
```bash
python test_gesture_mapper.py
```

### Individual Module Testing
Each module can be tested independently:
```bash
python src/input_capture.py      # Test webcam and hand detection
python src/gesture_detection.py  # Test gesture recognition
python src/command_executor.py   # Test command execution
python src/config_manager.py     # Test configuration management
```

## 🚧 Limitations & Future Enhancements

### Current MVP Limitations
- Single hand detection only
- Basic gesture types (distance, angle, position)
- Simple command execution
- No visual programming interface
- Limited error handling

### Planned Enhancements (v2+)
- **Multi-hand support**
- **Dynamic gestures** (time-based, motion tracking)
- **Gesture combinations** and sequences
- **Visual programming interface** (Scratch-like)
- **Advanced ML recognition**
- **Web-based configuration UI**
- **Plugin system** for custom commands

## 🐛 Troubleshooting

### Common Issues

1. **"Could not open camera"**
   - Ensure webcam is connected and not in use by other applications
   - Check camera permissions
   - Try different camera index (modify `camera_index` in `HandCapture`)

2. **"No hand detected"**
   - Ensure good lighting
   - Keep hand clearly visible to camera
   - Check MediaPipe installation

3. **Gestures not triggering**
   - Verify gesture definitions in configuration
   - Check threshold values (may need adjustment)
   - Ensure transformations are configured correctly

4. **Commands not executing**
   - Check command mappings in configuration
   - Verify pyautogui permissions
   - Check system security settings

### Performance Issues
- **Low FPS**: Reduce camera resolution or processing complexity
- **High latency**: Adjust MediaPipe confidence thresholds
- **Memory usage**: Close other applications using camera

## 📚 Technical Details

### Architecture
The system follows a modular pipeline architecture:
```
Webcam → Frame → Hand Detection → Keypoint Extraction → 
Normalization → Gesture Matching → Command Execution
```

### Key Technologies
- **OpenCV**: Computer vision and image processing
- **MediaPipe**: Hand landmark detection and tracking
- **pyautogui**: System automation and command execution
- **NumPy**: Numerical computations and array operations

### Performance Targets
- **Latency**: <100ms per frame
- **Accuracy**: >80% on defined gestures
- **FPS**: 15-30 FPS depending on hardware

## 🤝 Contributing

This is an MVP designed for validation and iteration. Future contributions are welcome:

1. **Report bugs** and issues
2. **Suggest enhancements** and new features
3. **Submit pull requests** for improvements
4. **Share use cases** and feedback

## 📄 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

- **MediaPipe** team for hand tracking technology
- **OpenCV** community for computer vision tools
- **Python** ecosystem for rapid prototyping

---

**Note**: This MVP is designed to validate the core concept of gesture-based command mapping. It provides a solid foundation for future development while keeping the current scope focused and manageable.
#   G e s t u r e - C o n t r o l  
 