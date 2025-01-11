import cv2
import mediapipe as mp
import pyautogui
import tkinter as tk
from tkinter import messagebox
import threading
import time

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)

# Default thresholds
LOOK_THRESHOLD = 0.125
SIDE_LOOK_THRESHOLD = 0.01

# Playback state
is_playing = True
monitoring = False
monitor_thread = None  # Thread for monitoring

# Strict Mode and Break Alert variables
strict_mode = False  # Default is off
away_time = 0  # Tracks time spent looking away
AWAY_ALERT_THRESHOLD = 10  # Time in seconds to trigger the break alert

# Additional thresholds for face distance monitoring
CLOSE_THRESHOLD = 0.0001  # Threshold for "too close" (normalized distance)
FAR_THRESHOLD = 0.0    # Set static "Far" threshold to 0
JUST_RIGHT_THRESHOLD = (CLOSE_THRESHOLD + FAR_THRESHOLD) / 2  # Optimal "Just Right" distance

# Camera initialization
def init_camera():
    global cap
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Unable to access webcam.")
        return False
    return True

def toggle_monitoring():
    global monitoring, monitor_thread, cap
    if monitoring:
        # Stop monitoring and release the camera
        monitoring = False
        status_label.config(text="Monitoring: OFF", fg="red")
        if cap.isOpened():
            cap.release()
    else:
        # Start monitoring
        monitoring = True
        status_label.config(text="Monitoring: ON", fg="green")
        # Initialize the camera if it's not already initialized
        if not cap.isOpened():
            if not init_camera():
                return
        # Start the monitoring thread
        monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitor_thread.start()

def toggle_strict_mode():
    global strict_mode
    strict_mode = not strict_mode
    strict_mode_label.config(text="Strict Mode: ON" if strict_mode else "Strict Mode: OFF", fg="green" if strict_mode else "red")

def update_thresholds():
    global LOOK_THRESHOLD, SIDE_LOOK_THRESHOLD, CLOSE_THRESHOLD, JUST_RIGHT_THRESHOLD
    try:
        LOOK_THRESHOLD = float(look_threshold_var.get())
        SIDE_LOOK_THRESHOLD = float(side_look_threshold_var.get())
        CLOSE_THRESHOLD = float(close_threshold_var.get())
        JUST_RIGHT_THRESHOLD = (CLOSE_THRESHOLD + FAR_THRESHOLD) / 2  # Recalculate the Just Right distance
        messagebox.showinfo("Success", "Thresholds updated successfully!")
    except ValueError:
        messagebox.showerror("Error", "Invalid input for thresholds. Please enter valid numbers.")

# Improved function for real-time distance monitoring and updates
def start_monitoring():
    global is_playing, monitoring, away_time

    while monitoring:
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Error", "Unable to access webcam.")
            break

        # Flip frame for a mirror effect
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame with MediaPipe Face Mesh
        result = face_mesh.process(rgb_frame)
        frame_h, frame_w, _ = frame.shape

        if result.multi_face_landmarks:
            # Get landmarks for the first detected face
            landmarks = result.multi_face_landmarks[0].landmark

            # Extract key points for face distance monitoring
            left_eye = landmarks[133]  # Left eye inner corner
            right_eye = landmarks[362]  # Right eye inner corner

            # Calculate the distance between the eyes in pixels
            left_eye_x, left_eye_y = int(left_eye.x * frame_w), int(left_eye.y * frame_h)
            right_eye_x, right_eye_y = int(right_eye.x * frame_w), int(right_eye.y * frame_h)

            # Euclidean distance between the eyes (in pixels)
            eye_distance = ((right_eye_x - left_eye_x) ** 2 + (right_eye_y - left_eye_y) ** 2) ** 0.5

            # Calculate the bounding box around the face (distance between the leftmost and rightmost landmarks)
            min_x = min([landmark.x for landmark in landmarks])
            max_x = max([landmark.x for landmark in landmarks])
            min_y = min([landmark.y for landmark in landmarks])
            max_y = max([landmark.y for landmark in landmarks])

            # Calculate the size of the face (bounding box)
            face_size = ((max_x - min_x) * frame_w) * ((max_y - min_y) * frame_h)

            # Use the eye distance and face size to estimate the distance
            estimated_distance = (eye_distance ** 2) / face_size  # Simple proportional relation

            # Normalize the distance for UI display
            normalized_distance = estimated_distance / frame_w  # Normalize with respect to frame width

            # Determine the distance status
            if normalized_distance > CLOSE_THRESHOLD:
                distance_status_label.config(text="Distance Status: Too Close", fg="red")
                # Show popup if the user is too close
                if not close_popup_shown:
                    messagebox.showwarning("Too Close", "You are too close to the screen. Please move back!")
                    close_popup_shown = True
            elif normalized_distance < FAR_THRESHOLD:
                distance_status_label.config(text="Distance Status: Too Far", fg="orange")
            elif FAR_THRESHOLD <= normalized_distance <= CLOSE_THRESHOLD:
                distance_status_label.config(text="Distance Status: Just Right", fg="green")
                close_popup_shown = False  # Reset popup flag when in the "Just Right" range

            # Extract other facial landmarks for head pose
            nose_tip = landmarks[1]
            left_eye_inner = landmarks[133]
            right_eye_inner = landmarks[362]

            nose_x, nose_y = int(nose_tip.x * frame_w), int(nose_tip.y * frame_h)
            left_x, left_y = int(left_eye_inner.x * frame_w), int(left_eye_inner.y * frame_h)
            right_x, right_y = int(right_eye_inner.x * frame_w), int(right_eye_inner.y * frame_h)

            horizontal_tilt = (left_x + right_x) / 2 - nose_x
            vertical_tilt = (left_y + right_y) / 2 - nose_y

            norm_horizontal_tilt = horizontal_tilt / frame_w
            norm_vertical_tilt = vertical_tilt / frame_h

            eyes_midpoint_x = (left_x + right_x) / 2
            nose_displacement = (nose_x - eyes_midpoint_x) / frame_w

            if (
                abs(norm_horizontal_tilt) > LOOK_THRESHOLD
                or abs(norm_vertical_tilt) > LOOK_THRESHOLD
                or abs(nose_displacement) > SIDE_LOOK_THRESHOLD
            ):
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

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.5)  # Slight delay for smoother updates

    cap.release()
    cv2.destroyAllWindows()

# GUI setup
root = tk.Tk()
root.title("Study Helper")

look_threshold_var = tk.StringVar(value=str(LOOK_THRESHOLD))
side_look_threshold_var = tk.StringVar(value=str(SIDE_LOOK_THRESHOLD))
close_threshold_var = tk.StringVar(value=str(CLOSE_THRESHOLD))

# Flag for the "Too Close" popup
close_popup_shown = False

# Threshold UI Elements
tk.Label(root, text="Look Threshold:").grid(row=0, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=look_threshold_var).grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Side Look Threshold:").grid(row=1, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=side_look_threshold_var).grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Close Threshold:").grid(row=2, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=close_threshold_var).grid(row=2, column=1, padx=10, pady=5)

tk.Button(root, text="Update Thresholds", command=update_thresholds).grid(row=3, column=0, columnspan=2, pady=10)

status_label = tk.Label(root, text="Monitoring: OFF", fg="red")
status_label.grid(row=4, column=0, columnspan=2, pady=10)

tk.Button(root, text="Start/Stop Monitoring", command=toggle_monitoring).grid(row=5, column=0, columnspan=2, pady=10)

strict_mode_label = tk.Label(root, text="Strict Mode: OFF", fg="red")
strict_mode_label.grid(row=6, column=0, columnspan=2, pady=5)

tk.Button(root, text="Toggle Strict Mode", command=toggle_strict_mode).grid(row=7, column=0, columnspan=2, pady=10)

# Add a new label for the distance status
distance_status_label = tk.Label(root, text="Distance Status: Normal", fg="green")
distance_status_label.grid(row=8, column=0, columnspan=2, pady=5)

# Initialize the camera once on startup
init_camera()

root.protocol("WM_DELETE_WINDOW", lambda: (cap.release(), root.destroy()))
root.mainloop()
