import cv2
import mediapipe as mp
import pyautogui
import threading
import time
import speech_recognition as sr
from faster_whisper import WhisperModel
import queue
import re
import os
from datetime import datetime
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

# Initialize MediaPipe Face Mesh and Hands
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Initialize speech recognition components
recognizer = sr.Recognizer()
whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
voice_command_queue = queue.Queue()

# Default thresholds
LOOK_THRESHOLD = 0.125
SIDE_LOOK_THRESHOLD = 0.01

# Added drowsiness detection thresholds
BLINK_THRESHOLD = 0.5
DROWSY_BLINK_DURATION = 0.5
HEAD_TILT_THRESHOLD = 0.3
DROWSY_ALERT_INTERVAL = 30

# Playback state
is_playing = True
monitoring = False
monitor_thread = None
close_popup_shown = False

# Control mode
use_gestures = False

# Strict Mode and Break Alert variables
strict_mode = False
away_time = 0
AWAY_ALERT_THRESHOLD = 10

# Additional thresholds for face distance monitoring
CLOSE_THRESHOLD = 0.0001
FAR_THRESHOLD = 0.0
JUST_RIGHT_THRESHOLD = (CLOSE_THRESHOLD + FAR_THRESHOLD) / 2

# Drowsiness monitoring variables
last_blink_start = 0
last_drowsy_alert = 0
eyes_closed = False
drowsiness_detected = False
blink_count = 0
blink_start_time = 0
BLINKS_THRESHOLD = 30
blink_times = []

# Set appearance mode and default color theme
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

class AIAssistant:
    def __init__(self):
        self.current_video_url = None
        self.notes = []
        self.is_listening = False
        self.listen_thread = None
    
    def start_listening(self):
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_for_commands, daemon=True)
        self.listen_thread.start()
    
    def stop_listening(self):
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join()
    
    def _listen_for_commands(self):
        with sr.Microphone() as source:
            print("Listening for commands...")
            while self.is_listening:
                try:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                    # Convert audio to WAV file
                    with open("temp_audio.wav", "wb") as f:
                        f.write(audio.get_wav_data())
                    
                    # Process with Whisper and correctly handle the output
                    segments, _ = whisper_model.transcribe("temp_audio.wav")
                    command = " ".join([segment.text for segment in segments]).lower().strip()
                    print(f"Recognized command: {command}")  # Debug output
                    
                    # Clean up temporary file
                    if os.path.exists("temp_audio.wav"):
                        os.remove("temp_audio.wav")
                    
                    if "take note" in command or "make note" in command:
                        self._process_note_command(command)
                    elif "save notes" in command:
                        self._save_notes()
                    elif "start video" in command:
                        self._extract_video_url(command)
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    print(f"Error processing command: {str(e)}")
                    
                # Additional cleanup
                if os.path.exists("temp_audio.wav"):
                    try:
                        os.remove("temp_audio.wav")
                    except:
                        pass
    
    def _process_note_command(self, command):
        note_content = re.sub(r'^(take note|make note)\s*', '', command, flags=re.IGNORECASE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self.current_video_url:
            video_time = "00:00"  # You'll need to implement getting actual video time
            note = f"[{video_time}] {note_content}"
        else:
            note = f"[{timestamp}] {note_content}"
            
        self.notes.append(note)
        print(f"Note added: {note}")
    
    def _save_notes(self):
        if not self.notes:
            print("No notes to save.")
            return
            
        filename = f"study_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            if self.current_video_url:
                f.write(f"Notes for video: {self.current_video_url}\n\n")
            f.write("\n".join(self.notes))
        
        print(f"Notes saved to {filename}")
        self.notes = []
    
    def _extract_video_url(self, command):
        url_match = re.search(r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+', command)
        if url_match:
            self.current_video_url = url_match.group()
            print(f"Current video set to: {self.current_video_url}")
    
    def get_current_notes(self):
        return self.notes

def init_camera():
    global cap
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            CTkMessagebox(title="Error", message="Unable to access webcam.", icon="cancel")
            return False
        return True
    except Exception as e:
        CTkMessagebox(title="Error", message=f"Camera initialization error: {str(e)}", icon="cancel")
        return False

def detect_gesture(frame):
    global is_playing
    
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            thumb_tip = hand_landmarks.landmark[4]
            index_tip = hand_landmarks.landmark[8]
            
            distance = ((thumb_tip.x - index_tip.x) ** 2 + 
                       (thumb_tip.y - index_tip.y) ** 2) ** 0.5
            
            if distance < 0.1:
                if is_playing:
                    pyautogui.press('k')
                    is_playing = False
                    time.sleep(0.3)
            else:
                if not is_playing:
                    pyautogui.press('k')
                    is_playing = True
                    time.sleep(0.3)

def check_drowsiness(landmarks, frame_w, frame_h, current_time):
    global last_blink_start, last_drowsy_alert, eyes_closed, drowsiness_detected
    global blink_count, blink_start_time, blink_times

    left_eye_top = landmarks[159]
    left_eye_bottom = landmarks[145]
    right_eye_top = landmarks[386]
    right_eye_bottom = landmarks[374]
    
    left_eye_height = abs(left_eye_top.y - left_eye_bottom.y)
    right_eye_height = abs(right_eye_top.y - right_eye_bottom.y)
    ear = (left_eye_height + right_eye_height) / 2
    
    nose_tip = landmarks[1]
    left_eye = landmarks[133]
    right_eye = landmarks[362]
    head_tilt = abs((left_eye.y - right_eye.y) / (right_eye.x - left_eye.x))

    if not eyes_closed and ear < BLINK_THRESHOLD:
        eyes_closed = True
        blink_start_time = current_time
        blink_times.append(current_time)
        
        blink_times = [t for t in blink_times if current_time - t <= 60]
        blink_count = len(blink_times)
    
    elif eyes_closed and ear >= BLINK_THRESHOLD:
        eyes_closed = False
        blink_duration = current_time - blink_start_time
        
        if blink_duration > DROWSY_BLINK_DURATION:
            drowsiness_detected = True

    if head_tilt > HEAD_TILT_THRESHOLD:
        drowsiness_detected = True

    if drowsiness_detected and (current_time - last_drowsy_alert) > DROWSY_ALERT_INTERVAL:
        CTkMessagebox(title="Drowsiness Alert", 
                     message="You appear to be drowsy! Consider taking a break.",
                     icon="warning")
        last_drowsy_alert = current_time
        drowsiness_detected = False

    if blink_count > BLINKS_THRESHOLD:
        app.drowsiness_status_label.configure(text="Drowsiness Status: High Blink Rate", text_color="red")
    elif drowsiness_detected:
        app.drowsiness_status_label.configure(text="Drowsiness Status: Drowsy", text_color="red")
    else:
        app.drowsiness_status_label.configure(text="Drowsiness Status: Alert", text_color="green")

def start_monitoring():
    global is_playing, monitoring, away_time, close_popup_shown

    while monitoring:
        ret, frame = cap.read()
        if not ret:
            CTkMessagebox(title="Error", message="Unable to access webcam.", icon="cancel")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        current_time = time.time()

        if use_gestures:
            detect_gesture(frame)
        else:
            result = face_mesh.process(rgb_frame)
            frame_h, frame_w, _ = frame.shape

            if result.multi_face_landmarks:
                landmarks = result.multi_face_landmarks[0].landmark
                
                check_drowsiness(landmarks, frame_w, frame_h, current_time)

                left_eye = landmarks[133]
                right_eye = landmarks[362]
                
                left_eye_x, left_eye_y = int(left_eye.x * frame_w), int(left_eye.y * frame_h)
                right_eye_x, right_eye_y = int(right_eye.x * frame_w), int(right_eye.y * frame_h)
                
                eye_distance = ((right_eye_x - left_eye_x) ** 2 + (right_eye_y - left_eye_y) ** 2) ** 0.5
                
                min_x = min([landmark.x for landmark in landmarks])
                max_x = max([landmark.x for landmark in landmarks])
                min_y = min([landmark.y for landmark in landmarks])
                max_y = max([landmark.y for landmark in landmarks])
                
                face_size = ((max_x - min_x) * frame_w) * ((max_y - min_y) * frame_h)
                estimated_distance = (eye_distance ** 2) / face_size
                normalized_distance = estimated_distance / frame_w

                if normalized_distance > CLOSE_THRESHOLD:
                    app.distance_status_label.configure(text="Distance Status: Too Close", text_color="red")
                    if not close_popup_shown:
                        CTkMessagebox(title="Too Close", message="You are too close to the screen. Please move back!", icon="warning")
                        close_popup_shown = True
                elif normalized_distance < FAR_THRESHOLD:
                    app.distance_status_label.configure(text="Distance Status: Too Far", text_color="orange")
                elif FAR_THRESHOLD <= normalized_distance <= CLOSE_THRESHOLD:
                    app.distance_status_label.configure(text="Distance Status: Just Right", text_color="green")
                    close_popup_shown = False

                nose_tip = landmarks[1]
                left_eye_inner = landmarks[133]
                right_eye_inner = landmarks[362]

                nose_x = int(nose_tip.x * frame_w)
                nose_y = int(nose_tip.y * frame_h)
                left_x = int(left_eye_inner.x * frame_w)
                left_y = int(left_eye_inner.y * frame_h)
                right_x = int(right_eye_inner.x * frame_w)
                right_y = int(right_eye_inner.y * frame_h)

                horizontal_tilt = (left_x + right_x) / 2 - nose_x
                vertical_tilt = (left_y + right_y) / 2 - nose_y
                norm_horizontal_tilt = horizontal_tilt / frame_w
                norm_vertical_tilt = vertical_tilt / frame_h
                eyes_midpoint_x = (left_x + right_x) / 2
                nose_displacement = (nose_x - eyes_midpoint_x) / frame_w

                if (abs(norm_horizontal_tilt) > LOOK_THRESHOLD or 
                    abs(norm_vertical_tilt) > LOOK_THRESHOLD or 
                    abs(nose_displacement) > SIDE_LOOK_THRESHOLD):
                    
                    if strict_mode:
                        away_time += 1
                        if away_time > AWAY_ALERT_THRESHOLD:
                            CTkMessagebox(title="Focus Alert", message="You've been looking away for too long. Time to refocus!", icon="info")
                            away_time = 0
                    
                    if is_playing:
                        pyautogui.press('k')
                        is_playing = False
                else:
                    away_time = 0
                    if not is_playing:
                        pyautogui.press('k')
                        is_playing = True
            else:
                app.distance_status_label.configure(text="Distance Status: No Face Detected", text_color="gray")
                app.drowsiness_status_label.configure(text="Drowsiness Status: No Face Detected", text_color="gray")

        time.sleep(0.1)

    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()

class StudyHelperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("FocusFlow")
        self.geometry("300x900")
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.create_frames()
        self.initialize_variables()
        
    def create_frames(self):
        # Control Mode Frame
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="nsew")
        
        self.control_mode_label = ctk.CTkLabel(
            self.control_frame, 
            text="Control Mode: Face Detection",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.control_mode_label.pack(pady=10)
        
        self.toggle_control_btn = ctk.CTkButton(
            self.control_frame,
            text="Toggle Control Mode",
            command=self.toggle_control_mode
        )
        self.toggle_control_btn.pack(pady=10)
        
        # Thresholds Frame
        self.threshold_frame = ctk.CTkFrame(self)
        self.threshold_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        
        ctk.CTkLabel(
            self.threshold_frame,
            text="Threshold Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Look Threshold
        self.look_threshold_var = ctk.StringVar(value=str(LOOK_THRESHOLD))
        self.create_threshold_entry("Look Threshold:", self.look_threshold_var)
        
        # Side Look Threshold
        self.side_look_threshold_var = ctk.StringVar(value=str(SIDE_LOOK_THRESHOLD))
        self.create_threshold_entry("Side Look Threshold:", self.side_look_threshold_var)
        
        # Close Threshold
        self.close_threshold_var = ctk.StringVar(value=str(CLOSE_THRESHOLD))
        self.create_threshold_entry("Close Threshold:", self.close_threshold_var)
        
        ctk.CTkButton(
            self.threshold_frame,
            text="Update Thresholds",
            command=self.update_thresholds
        ).pack(pady=15)
        
        # Status Frame
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Monitoring: OFF",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(pady=10)
        
        self.distance_status_label = ctk.CTkLabel(
            self.status_frame,
            text="Distance Status: Normal",
            font=ctk.CTkFont(size=14)
        )
        self.distance_status_label.pack(pady=5)
        
        self.drowsiness_status_label = ctk.CTkLabel(
            self.status_frame,
            text="Drowsiness Status: Alert",
            font=ctk.CTkFont(size=14)
        )
        self.drowsiness_status_label.pack(pady=5)
        
        # Control Buttons Frame
        self.control_buttons_frame = ctk.CTkFrame(self)
        self.control_buttons_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="nsew")
        
        self.monitoring_btn = ctk.CTkButton(
            self.control_buttons_frame,
            text="Start/Stop Monitoring",
            command=self.toggle_monitoring
        )
        self.monitoring_btn.pack(pady=10)
        
        self.strict_mode_label = ctk.CTkLabel(
            self.control_buttons_frame,
            text="Strict Mode: OFF",
            font=ctk.CTkFont(size=14)
        )
        self.strict_mode_label.pack(pady=5)
        
        self.strict_mode_btn = ctk.CTkButton(
            self.control_buttons_frame,
            text="Toggle Strict Mode",
            command=self.toggle_strict_mode
        )
        self.strict_mode_btn.pack(pady=10)
        
        self.ai_assistant_label = ctk.CTkLabel(
            self.control_buttons_frame,
            text="AI Assistant: OFF",
            font=ctk.CTkFont(size=14)
        )
        self.ai_assistant_label.pack(pady=5)
        
        self.ai_assistant_btn = ctk.CTkButton(
            self.control_buttons_frame,
            text="Toggle AI Assistant",
            command=self.toggle_ai_assistant
        )
        self.ai_assistant_btn.pack(pady=10)
    
    def create_threshold_entry(self, label_text, variable):
        frame = ctk.CTkFrame(self.threshold_frame)
        frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(frame, text=label_text).pack(side="left", padx=10)
        ctk.CTkEntry(frame, textvariable=variable, width=100).pack(side="right", padx=10)
    
    def initialize_variables(self):
        # global ai_assistant, cap
        self.use_gestures = False
        self.strict_mode = False
        self.monitoring = False
        self.monitor_thread = None
        self.ai_assistant = None
        self.cap = None
        
        # Initialize camera
        init_camera()
        
        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def toggle_control_mode(self):
        global use_gestures
        use_gestures = not use_gestures
        self.control_mode_label.configure(
            text="Control Mode: Gesture" if use_gestures else "Control Mode: Face Detection"
        )
    
    def update_thresholds(self):
        try:
            global LOOK_THRESHOLD, SIDE_LOOK_THRESHOLD, CLOSE_THRESHOLD
            LOOK_THRESHOLD = float(self.look_threshold_var.get())
            SIDE_LOOK_THRESHOLD = float(self.side_look_threshold_var.get())
            CLOSE_THRESHOLD = float(self.close_threshold_var.get())
            CTkMessagebox(title="Success", message="Thresholds updated successfully!", icon="check")
        except ValueError:
            CTkMessagebox(title="Error", message="Invalid input for thresholds. Please enter valid numbers.", icon="cancel")
    
    def toggle_monitoring(self):
        global monitoring, monitor_thread, cap
        if monitoring:
            monitoring = False
            self.status_label.configure(text="Monitoring: OFF", text_color="red")
            if cap is not None and cap.isOpened():
                cap.release()
        else:
            monitoring = True
            self.status_label.configure(text="Monitoring: ON", text_color="green")
            if not hasattr(cap, 'isOpened') or not cap.isOpened():
                if not init_camera():
                    return
            monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
            monitor_thread.start()
    
    def toggle_strict_mode(self):
        global strict_mode
        strict_mode = not strict_mode
        self.strict_mode_label.configure(
            text="Strict Mode: ON" if strict_mode else "Strict Mode: OFF",
            text_color="green" if strict_mode else "red"
        )
    
    def toggle_ai_assistant(self):
        # global ai_assistant
        if self.ai_assistant is None:  # Changed from ai_assistant to self.ai_assistant
            self.ai_assistant = AIAssistant()
            self.ai_assistant.start_listening()
            self.ai_assistant_label.configure(text="AI Assistant: ON", text_color="green")
        else:
            self.ai_assistant.stop_listening()
            self.ai_assistant = None
            self.ai_assistant_label.configure(text="AI Assistant: OFF", text_color="red")
    
    def on_closing(self):
        # global cap, ai_assistant
        
        if self.cap is not None and self.cap.isOpened():  # Changed from cap to self.cap
            self.cap.release()
        if self.ai_assistant is not None:  # Changed from ai_assistant to self.ai_assistant
            self.ai_assistant.stop_listening()
        self.quit()

if __name__ == "__main__":
    app = StudyHelperApp()
    app.mainloop() 