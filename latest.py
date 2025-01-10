import cv2
import mediapipe as mp
import pyautogui
import tkinter as tk
from tkinter import messagebox
import threading

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
cap = cv2.VideoCapture(0)

# Default thresholds
LOOK_THRESHOLD = 0.125
SIDE_LOOK_THRESHOLD = 0.01

# Playback state
is_playing = True
monitoring = False
monitor_thread = None  # Thread for monitoring

def toggle_monitoring():
    global monitoring, monitor_thread
    monitoring = not monitoring
    status_label.config(text="Monitoring: ON" if monitoring else "Monitoring: OFF", fg="green" if monitoring else "red")

    if monitoring:
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitor_thread.start()

def update_thresholds():
    global LOOK_THRESHOLD, SIDE_LOOK_THRESHOLD
    try:
        LOOK_THRESHOLD = float(look_threshold_var.get())
        SIDE_LOOK_THRESHOLD = float(side_look_threshold_var.get())
        messagebox.showinfo("Success", "Thresholds updated successfully!")
    except ValueError:
        messagebox.showerror("Error", "Invalid input for thresholds. Please enter valid numbers.")

def start_monitoring():
    global is_playing, monitoring

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

            # Extract key points for head pose
            nose_tip = landmarks[1]
            left_eye_inner = landmarks[133]
            right_eye_inner = landmarks[362]

            # Map landmarks to pixel coordinates
            nose_x, nose_y = int(nose_tip.x * frame_w), int(nose_tip.y * frame_h)
            left_x, left_y = int(left_eye_inner.x * frame_w), int(left_eye_inner.y * frame_h)
            right_x, right_y = int(right_eye_inner.x * frame_w), int(right_eye_inner.y * frame_h)

            # Calculate horizontal and vertical tilt
            horizontal_tilt = (left_x + right_x) / 2 - nose_x
            vertical_tilt = (left_y + right_y) / 2 - nose_y

            # Normalize tilt values
            norm_horizontal_tilt = horizontal_tilt / frame_w
            norm_vertical_tilt = vertical_tilt / frame_h

            # Calculate nose's horizontal displacement
            eyes_midpoint_x = (left_x + right_x) / 2
            nose_displacement = (nose_x - eyes_midpoint_x) / frame_w

            # Check if user is looking away
            if (
                abs(norm_horizontal_tilt) > LOOK_THRESHOLD
                or abs(norm_vertical_tilt) > LOOK_THRESHOLD
                or abs(nose_displacement) > SIDE_LOOK_THRESHOLD
            ):
                if is_playing:
                    pyautogui.press('k')  # Pause the video
                    is_playing = False
            else:
                if not is_playing:
                    pyautogui.press('k')  # Resume the video
                    is_playing = True

        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# GUI setup
root = tk.Tk()
root.title("Study Helper")

look_threshold_var = tk.StringVar(value=str(LOOK_THRESHOLD))
side_look_threshold_var = tk.StringVar(value=str(SIDE_LOOK_THRESHOLD))

tk.Label(root, text="Look Threshold:").grid(row=0, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=look_threshold_var).grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Side Look Threshold:").grid(row=1, column=0, padx=10, pady=5)
tk.Entry(root, textvariable=side_look_threshold_var).grid(row=1, column=1, padx=10, pady=5)

tk.Button(root, text="Update Thresholds", command=update_thresholds).grid(row=2, column=0, columnspan=2, pady=10)
status_label = tk.Label(root, text="Monitoring: OFF", fg="red")
status_label.grid(row=3, column=0, columnspan=2, pady=10)

tk.Button(root, text="Start/Stop Monitoring", command=toggle_monitoring).grid(row=4, column=0, columnspan=2, pady=10)

root.protocol("WM_DELETE_WINDOW", lambda: (cap.release(), root.destroy()))
root.mainloop()
