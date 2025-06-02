#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import copy
import argparse
from collections import Counter
from collections import deque

import cv2 as cv
import mediapipe as mp

from utils import CvFpsCalc
from model import KeyPointClassifier
from model import PointHistoryClassifier

import methods

from flask import Flask, jsonify
import threading

app = Flask(__name__)
gesture_state = {"hand": None, "gesture": None}


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", help="cap width", type=int, default=960)
    parser.add_argument("--height", help="cap height", type=int, default=540)

    parser.add_argument("--use_static_image_mode", action="store_true")
    parser.add_argument(
        "--min_detection_confidence",
        help="min_detection_confidence",
        type=float,
        default=0.7,
    )
    parser.add_argument(
        "--min_tracking_confidence",
        help="min_tracking_confidence",
        type=int,
        default=0.5,
    )

    args = parser.parse_args()

    return args


def gesture_loop():
    # Argument parsing #################################################################
    args = get_args()

    cap_device = args.device
    cap_width = args.width
    cap_height = args.height

    use_static_image_mode = args.use_static_image_mode
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence

    swipe_cooldown = 0
    cooldown_max = 20  # number of frames to wait after swipe
    swipe_triggered = False

    use_brect = True

    # Camera preparation ###############################################################
    cap = cv.VideoCapture(cap_device)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    # Model load
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=2,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    keypoint_classifier = KeyPointClassifier()

    point_history_classifier = PointHistoryClassifier()

    # Read labels
    with open(
        "hand-gesture-recognition-mediapipe-main/model/keypoint_classifier/keypoint_classifier_label.csv",
        encoding="utf-8-sig",
    ) as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [row[0] for row in keypoint_classifier_labels]
    with open(
        "hand-gesture-recognition-mediapipe-main/model/point_history_classifier/point_history_classifier_label.csv",
        encoding="utf-8-sig",
    ) as f:
        point_history_classifier_labels = csv.reader(f)
        point_history_classifier_labels = [
            row[0] for row in point_history_classifier_labels
        ]

    # FPS Measurement
    cvFpsCalc = CvFpsCalc(buffer_len=10)

    # Coordinate history
    history_length = 16
    point_history = deque(maxlen=history_length)

    swipe_history = deque(maxlen=5)

    # Finger gesture history
    finger_gesture_history = deque(maxlen=history_length)

    mode = 0

    while True:
        fps = cvFpsCalc.get()

        # Process Key (ESC: end)
        key = cv.waitKey(10)
        if key == 27:  # ESC
            break
        # number, mode = select_mode(key, mode)

        # Camera capture
        ret, image = cap.read()
        if not ret:
            break
        image = cv.flip(image, 1)  # Mirror display
        debug_image = copy.deepcopy(image)

        # Detection implementation
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True

        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                # Bounding box calculation
                brect = methods.calc_bounding_rect(debug_image, hand_landmarks)
                # Landmark calculation
                landmark_list = methods.calc_landmark_list(debug_image, hand_landmarks)

                # Conversion to relative coordinates / normalized coordinates
                pre_processed_landmark_list = methods.pre_process_landmark(
                    landmark_list
                )
                pre_processed_point_history_list = methods.pre_process_point_history(
                    debug_image, point_history
                )

                # Hand sign classification
                hand_sign_id = keypoint_classifier(pre_processed_landmark_list)
                pointer_id = None
                if hand_sign_id == 2:  # Point gesture
                    point_history.append(landmark_list[8])
                    swipe_history.append(landmark_list[8])
                else:
                    point_history.append([0, 0])
                    swipe_history.append([0, 0])

                # Only evaluate if not cooling down
                if len(swipe_history) >= 3:
                    x_vals = [pt[0] for pt in swipe_history if pt != [0, 0]]

                    if len(x_vals) >= 2:
                        dx = x_vals[-1] - x_vals[0]

                        if abs(dx) > 50:  # adjust swipe sensitivity threshold
                            if dx > 0:
                                pointer_id = "Swipe Right"
                            else:
                                pointer_id = "Swipe Left"

                gesture_state["hand"] = handedness.classification[0].label[0:]
                gesture_state["gesture"] = (
                    pointer_id
                    if hand_sign_id == 2
                    else keypoint_classifier_labels[hand_sign_id]
                )

                # print(
                #     f"Hand: {handedness.classification[0].label[0:]}, Gesture: {keypoint_classifier_labels[hand_sign_id]} \r"
                # )

                # Finger gesture classification
                finger_gesture_id = 0
                point_history_len = len(pre_processed_point_history_list)
                if point_history_len == (history_length * 2):
                    finger_gesture_id = point_history_classifier(
                        pre_processed_point_history_list
                    )

                # Calculates the gesture IDs in the latest detection
                finger_gesture_history.append(finger_gesture_id)
                most_common_fg_id = Counter(finger_gesture_history).most_common()
                # print(f"Point classification {most_common_fg_id[0][0]}")

                # Drawing part
                debug_image = methods.draw_bounding_rect(use_brect, debug_image, brect)
                debug_image = methods.draw_landmarks(debug_image, landmark_list)
                debug_image = methods.draw_info_text(
                    debug_image,
                    brect,
                    handedness,
                    keypoint_classifier_labels[hand_sign_id],
                    point_history_classifier_labels[most_common_fg_id[0][0]],
                )
        else:
            point_history.append([0, 0])

        debug_image = methods.draw_point_history(debug_image, point_history)
        debug_image = methods.draw_info(debug_image, fps, mode, 0)

        # Screen reflection #############################################################
        # cv.imshow("Hand Gesture Recognition", debug_image)

    cap.release()
    cv.destroyAllWindows()


@app.route("/gesture", methods=["GET"])
def get_gesture():
    return jsonify(gesture_state)


if __name__ == "__main__":
    # Start gesture detection in a background thread
    threading.Thread(target=gesture_loop, daemon=True).start()

    # Start the Flask server
    app.run(host="0.0.0.0", port=5001)
