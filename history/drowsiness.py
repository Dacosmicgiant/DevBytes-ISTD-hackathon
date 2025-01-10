import cv2
import mediapipe as mp
import pyautogui
import tkinter as tk
from tkinter import messagebox
import threading
import time

# Initialize MediaPipe Face Mesh and Hands
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Default thresholds
LOOK_THRESHOLD = 0.125
SIDE_LOOK_THRESHOLD = 0.01

# Added drowsiness detection thresholds
BLINK_THRESHOLD = 0.5  # Threshold for considering eyes closed
DROWSY_BLINK_DURATION = 0.5  # Seconds for a blink to be considered drowsy
HEAD_TILT_THRESHOLD = 0.3  # Threshold for head tilt detection
DROWSY_ALERT_INTERVAL = 30  # Minimum seconds between drowsiness alerts

# Playback state
is_playing = True
monitoring = False
monitor_thread = None
close_popup_shown = False  # Added global declaration


# Control mode
use_gestures = False  # Default to face detection

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
BLINKS_THRESHOLD = 30  # Blinks per minute threshold
blink_times = []

def init_camera():
    # [Previous init_camera code remains unchanged]
    global cap
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Unable to access webcam.")
            return False
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Camera initialization error: {str(e)}")
        return False


def toggle_control_mode():
    global use_gestures
    use_gestures = not use_gestures
    control_mode_label.config(
        text="Control Mode: Gesture" if use_gestures else "Control Mode: Face Detection",
        fg="blue"
    )

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
            
            if distance < 0.1:  # Threshold for pinch gesture
                if is_playing:
                    pyautogui.press('k')
                    is_playing = False
                    time.sleep(0.3)
            else:
                if not is_playing:
                    pyautogui.press('k')
                    is_playing = True
                    time.sleep(0.3)
                    

def toggle_strict_mode():
    global strict_mode
    strict_mode = not strict_mode
    strict_mode_label.config(text="Strict Mode: ON" if strict_mode else "Strict Mode: OFF", 
                           fg="green" if strict_mode else "red")

def update_thresholds():
    global LOOK_THRESHOLD, SIDE_LOOK_THRESHOLD, CLOSE_THRESHOLD
    try:
        LOOK_THRESHOLD = float(look_threshold_var.get())
        SIDE_LOOK_THRESHOLD = float(side_look_threshold_var.get())
        CLOSE_THRESHOLD = float(close_threshold_var.get())
        messagebox.showinfo("Success", "Thresholds updated successfully!")
    except ValueError:
        messagebox.showerror("Error", "Invalid input for thresholds. Please enter valid numbers.")
        

def toggle_monitoring():
    global monitoring, monitor_thread, cap
    if monitoring:
        monitoring = False
        status_label.config(text="Monitoring: OFF", fg="red")
        if cap is not None and cap.isOpened():
            cap.release()
    else:
        monitoring = True
        status_label.config(text="Monitoring: ON", fg="green")
        if not hasattr(cap, 'isOpened') or not cap.isOpened():
            if not init_camera():
                return
        monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitor_thread.start()

def check_drowsiness(landmarks, frame_w, frame_h, current_time):
    global last_blink_start, last_drowsy_alert, eyes_closed, drowsiness_detected
    global blink_count, blink_start_time, blink_times

    # Get eye landmarks
    left_eye_top = landmarks[159]  # Upper left eye landmark
    left_eye_bottom = landmarks[145]  # Lower left eye landmark
    right_eye_top = landmarks[386]  # Upper right eye landmark
    right_eye_bottom = landmarks[374]  # Lower right eye landmark
    
    # Calculate eye aspect ratio (EAR)
    left_eye_height = abs(left_eye_top.y - left_eye_bottom.y)
    right_eye_height = abs(right_eye_top.y - right_eye_bottom.y)
    ear = (left_eye_height + right_eye_height) / 2
    
    # Head tilt calculation
    nose_tip = landmarks[1]
    left_eye = landmarks[133]
    right_eye = landmarks[362]
    head_tilt = abs((left_eye.y - right_eye.y) / (right_eye.x - left_eye.x))

    # Blink detection
    if not eyes_closed and ear < BLINK_THRESHOLD:
        eyes_closed = True
        blink_start_time = current_time
        blink_times.append(current_time)
        
        # Remove blinks older than 60 seconds
        blink_times = [t for t in blink_times if current_time - t <= 60]
        blink_count = len(blink_times)
    
    elif eyes_closed and ear >= BLINK_THRESHOLD:
        eyes_closed = False
        blink_duration = current_time - blink_start_time
        
        # Check for drowsy blink
        if blink_duration > DROWSY_BLINK_DURATION:
            drowsiness_detected = True

    # Check head tilt
    if head_tilt > HEAD_TILT_THRESHOLD:
        drowsiness_detected = True

    # Alert if drowsy and enough time has passed since last alert
    if drowsiness_detected and (current_time - last_drowsy_alert) > DROWSY_ALERT_INTERVAL:
        messagebox.showwarning("Drowsiness Alert", 
                             "You appear to be drowsy! Consider taking a break.")
        last_drowsy_alert = current_time
        drowsiness_detected = False

    # Update drowsiness status label
    if blink_count > BLINKS_THRESHOLD:
        drowsiness_status_label.config(text="Drowsiness Status: High Blink Rate", fg="red")
    elif drowsiness_detected:
        drowsiness_status_label.config(text="Drowsiness Status: Drowsy", fg="red")
    else:
        drowsiness_status_label.config(text="Drowsiness Status: Alert", fg="green")

def start_monitoring():
    global is_playing, monitoring, away_time, close_popup_shown

    while monitoring:
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Error", "Unable to access webcam.")
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
                
                # Add drowsiness detection
                check_drowsiness(landmarks, frame_w, frame_h, current_time)

                # [Rest of the existing face monitoring code remains unchanged]
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
                    distance_status_label.config(text="Distance Status: Too Close", fg="red")
                    if not close_popup_shown:
                        messagebox.showwarning("Too Close", "You are too close to the screen. Please move back!")
                        close_popup_shown = True
                elif normalized_distance < FAR_THRESHOLD:
                    distance_status_label.config(text="Distance Status: Too Far", fg="orange")
                elif FAR_THRESHOLD <= normalized_distance <= CLOSE_THRESHOLD:
                    distance_status_label.config(text="Distance Status: Just Right", fg="green")
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
                            pyautogui.alert("You've been looking away for too long. Time to refocus!")
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
                distance_status_label.config(text="Distance Status: No Face Detected", fg="gray")
                drowsiness_status_label.config(text="Drowsiness Status: No Face Detected", fg="gray")

        time.sleep(0.1)

    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()

# GUI setup
root = tk.Tk()
root.title("Study Helper")

# [Previous GUI elements remain unchanged]
control_mode_label = tk.Label(root, text="Control Mode: Face Detection", fg="blue")
control_mode_label.grid(row=0, column=0, columnspan=2, pady=5)

tk.Button(root, text="Toggle Control Mode", command=toggle_control_mode).grid(row=1, column=0, columnspan=2, pady=5)

look_threshold_var = tk.StringVar(value=str(LOOK_THRESHOLD))
side_look_threshold_var = tk.StringVar(value=str(SIDE_LOOK_THRESHOLD))
close_threshold_var = tk.StringVar(value=str(CLOSE_THRESHOLD))

tk.Label(root, text="Look Threshold:").grid(row=2, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=look_threshold_var).grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Side Look Threshold:").grid(row=3, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=side_look_threshold_var).grid(row=3, column=1, padx=10, pady=5)

tk.Label(root, text="Close Threshold:").grid(row=4, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=close_threshold_var).grid(row=4, column=1, padx=10, pady=5)

tk.Button(root, text="Update Thresholds", command=update_thresholds).grid(row=5, column=0, columnspan=2, pady=10)

status_label = tk.Label(root, text="Monitoring: OFF", fg="red")
status_label.grid(row=6, column=0, columnspan=2, pady=10)

tk.Button(root, text="Start/Stop Monitoring", command=toggle_monitoring).grid(row=7, column=0, columnspan=2, pady=10)

strict_mode_label = tk.Label(root, text="Strict Mode: OFF", fg="red")
strict_mode_label.grid(row=8, column=0, columnspan=2, pady=5)

tk.Button(root, text="Toggle Strict Mode", command=toggle_strict_mode).grid(row=9, column=0, columnspan=2, pady=10)

distance_status_label = tk.Label(root, text="Distance Status: Normal", fg="green")
distance_status_label.grid(row=10, column=0, columnspan=2, pady=5)

# Add drowsiness status label
drowsiness_status_label = tk.Label(root, text="Drowsiness Status: Alert", fg="green")
drowsiness_status_label.grid(row=11, column=0, columnspan=2, pady=5)

# Initialize camera
cap = None
init_camera()

# Set up window close handler
root.protocol("WM_DELETE_WINDOW", lambda: (cap.release() if cap is not None and cap.isOpened() else None, root.destroy()))
root.mainloop()