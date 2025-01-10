import cv2
import mediapipe as mp
import pyautogui

# Initialize MediaPipe Face Mesh and OpenCV
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
cap = cv2.VideoCapture(0)

# Thresholds for head tilt and horizontal displacement
LOOK_THRESHOLD = 0.125  # For vertical/horizontal tilt
SIDE_LOOK_THRESHOLD = 0.01  # For left/right displacement

# Playback state
is_playing = True

while True:
    ret, frame = cap.read()
    if not ret:
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

        # Calculate the midpoint of the eyes
        eyes_midpoint_x = (left_x + right_x) / 2
        eyes_midpoint_y = (left_y + right_y) / 2

        # Calculate the nose's horizontal displacement relative to eye midpoint
        nose_displacement = (nose_x - eyes_midpoint_x) / frame_w

        # Debug: Print tilt and displacement values
        print(f"Horizontal Tilt: {norm_horizontal_tilt}, Vertical Tilt: {norm_vertical_tilt}, Nose Displacement: {nose_displacement}")

        # Check if user is looking away (up/down tilt or left/right turn)
        if (
            abs(norm_horizontal_tilt) > LOOK_THRESHOLD
            or abs(norm_vertical_tilt) > LOOK_THRESHOLD
            or abs(nose_displacement) > SIDE_LOOK_THRESHOLD
        ):
            if is_playing:
                pyautogui.press('k')  # Pause the video
                print("Paused video")
                is_playing = False
        else:
            if not is_playing:
                pyautogui.press('k')  # Play the video
                print("Resumed video")
                is_playing = True

        # Visualize head pose estimation
        cv2.circle(frame, (nose_x, nose_y), 5, (0, 255, 0), -1)
        cv2.line(frame, (left_x, left_y), (right_x, right_y), (255, 0, 0), 2)

        # Visualize nose displacement relative to eyes
        color = (0, 0, 255) if abs(nose_displacement) > SIDE_LOOK_THRESHOLD else (0, 255, 0)
        cv2.line(frame, (nose_x, nose_y), (int(eyes_midpoint_x), int(eyes_midpoint_y)), color, 2)

    # Add visual indicator
    if is_playing:
        cv2.putText(frame, "Playing", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Paused", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Display the frame
    cv2.imshow("Head Pose Detection", frame)

    # Exit condition
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
