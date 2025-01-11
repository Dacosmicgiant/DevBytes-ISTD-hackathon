# FocusFlow: Your AI Study Companion 🎓

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Transform your study sessions with an AI companion that keeps you focused, maintains your well-being, and maximizes your learning potential.

## 🌟 Features

### 👁️ Intelligent Focus Monitoring

- **Smart Pause/Play**: Automatically pauses your study content when you look away and resumes when you return
- **Posture & Distance Detection**: Ensures you maintain a healthy distance from your screen
- **Gesture Control**: Optional hand gesture controls for a touch-free experience

### 😴 Drowsiness Detection

- **Real-time Alertness Monitoring**: Tracks your blink rate and eye movement patterns
- **Timely Break Reminders**: Suggests breaks when signs of fatigue are detected
- **Head Position Analysis**: Monitors head tilting that may indicate drowsiness

### 🎙️ AI Study Assistant

- **Voice-Activated Note Taking**: Capture important points without breaking your flow

### 🎯 Focus Enhancement

- **Strict Mode**: Extra accountability for intensive study sessions
- **Customizable Thresholds**: Adjust sensitivity to match your study style
- **Progress Tracking**: Monitor your focus metrics over time

## 🚀 Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
```

Required packages:

- OpenCV
- MediaPipe
- PyAutoGUI
- SpeechRecognition
- faster-whisper
- customtkinter
- CTkMessagebox

### Quick Start

1. Clone the repository:

```bash
git clone https://github.com/yourusername/focusflow.git
cd focusflow
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run FocusFlow:

```bash
python main.py
```

## 💡 Usage Tips

### Optimal Setup

- Ensure good lighting for accurate face detection
- Position your camera at eye level
- Maintain a comfortable sitting posture
- Test different threshold settings to find your sweet spot

### Control Modes

1. **Face Detection Mode**

   - Tracks your face position and eye movements
   - Automatically manages content playback

2. **Gesture Control Mode**
   - Use simple hand gestures to control playback
   - Perfect for hands-free operation

### AI Assistant Commands

- "Take note [your note]" - Captures a study note
- "Save notes" - Saves all accumulated notes
- "Start video [URL]" - Begins monitoring with video content

## ⚙️ Customization

### Adjustable Thresholds - Find your comfort.

- Look Threshold: Sensitivity to head movement
- Side Look Threshold: Tolerance for lateral head movement
- Close Threshold: Screen distance warning trigger

### Strict Mode Options

- Enhanced focus monitoring
- Stricter break enforcement
- Detailed attention analytics

## 🤝 Contributing

We welcome contributions! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- MediaPipe team for their amazing computer vision tools
- OpenCV community for image processing capabilities
- Whisper by OpenAI for speech recognition
- CustomTkinter for the modern UI components
- ProgrammingHero YT for introducing us to mediapipe

---

<p align="center">Built with ❤️ for students, by students</p>
