import os
import json
import re
import time
import uuid
from pathlib import Path

import cv2
import httpx
import mss
import numpy as np
import psutil
import win32gui
import win32process
import easyocr
import warnings
from ctypes import windll

warnings.filterwarnings("ignore", category=UserWarning)

try:
    windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        windll.user32.SetProcessDPIAware()
    except Exception:
        pass

TEMPLATE_BASE_HEIGHT = 1440
MATCH_THRESHOLD = 0.80

X_LEFT_PCT = (0.100, 0.217)
X_RIGHT_PCT = (0.783, 0.900)
Y_NAME_PCT = (0.555, 0.600)

POLL_X_PCT = (0.30, 0.70)
POLL_Y_PCT = (0.60, 0.71)

print("Initializing OCR Engine...")
reader = easyocr.Reader(['en'], gpu=False)
print("OCR Engine Ready.")


def load_device_id():
    appdata = Path(os.environ.get("APPDATA", ".."))
    path = appdata / "echt" / "device_id"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text().strip()
    device_id = str(uuid.uuid4())
    path.write_text(device_id)
    return device_id


def get_game_client_area(hwnd):
    rect = win32gui.GetClientRect(hwnd)
    x, y = win32gui.ClientToScreen(hwnd, (0, 0))
    return x, y, rect[2], rect[3]


def find_efootball_window():
    matches = []

    def callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
            if "efootball" in win32gui.GetWindowText(hwnd).lower():
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid)
                    if proc.name().lower().startswith("efootball"):
                        matches.append(hwnd)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return True

    win32gui.EnumWindows(callback, None)
    return matches[0] if matches else None


def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (0, 0), fx=1.0, fy=1.0, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_usernames(frame, w, h):
    left_crop = frame[int(h * Y_NAME_PCT[0]):int(h * Y_NAME_PCT[1]), int(w * X_LEFT_PCT[0]):int(w * X_LEFT_PCT[1])]
    right_crop = frame[int(h * Y_NAME_PCT[0]):int(h * Y_NAME_PCT[1]), int(w * X_RIGHT_PCT[0]):int(w * X_RIGHT_PCT[1])]

    left_processed = preprocess_image(left_crop)
    right_processed = preprocess_image(right_crop)
    w_l = left_processed.shape[1]
    spacer = np.zeros((left_processed.shape[0], 100), dtype=np.uint8)
    combined = np.hstack((left_processed, spacer, right_processed))

    results = reader.readtext(combined, adjust_contrast=False)

    left_raw, right_raw = "", ""
    if results:
        sorted_results = sorted(results, key=lambda r: r[0][0][0])
        for res in sorted_results:
            bbox, text, conf = res
            center_x = bbox[0][0] + (bbox[1][0] - bbox[0][0]) / 2
            if center_x < w_l:
                left_raw = text
            else:
                right_raw = text

    return re.sub(r'[^a-zA-Z0-9_-]', '', left_raw), re.sub(r'[^a-zA-Z0-9_-]', '', right_raw)


def monitor_matchmaking(callback_function):
    hwnd = find_efootball_window()
    if not hwnd:
        print("Error: eFootball is not running (or is minimized)!")
        return

    template_dir = Path(__file__).resolve().parent
    template_left = cv2.imread(str(template_dir / 'collective_strength_left.png'), cv2.IMREAD_COLOR)
    template_right = cv2.imread(str(template_dir / 'collective_strength_right.png'), cv2.IMREAD_COLOR)
    if template_left is None or template_right is None:
        print("Error: Templates not found.")
        return

    print("\n[ACTIVE] Monitoring matchmaking. Press Ctrl+C to stop.")

    cached_h = 0
    left_t_gray, right_t_gray = None, None
    loop_count = 0
    match_reported = False
    x, y, w, h = 0, 0, 0, 0

    with mss.MSS() as sct:
        while True:
            if win32gui.IsIconic(hwnd):
                time.sleep(1.0)
                continue

            if loop_count % 5 == 0 or w == 0:
                try:
                    x, y, w, h = get_game_client_area(hwnd)
                    try:
                        sidecar = Path(os.environ.get("APPDATA", "..")) / "echt" / "game_rect.json"
                        sidecar.parent.mkdir(parents=True, exist_ok=True)
                        sidecar.write_text(json.dumps({"x": x, "y": y, "w": w, "h": h}))
                    except Exception:
                        pass
                except Exception:
                    print("Game window lost.")
                    break
            loop_count += 1

            if w <= 0 or h <= 0:
                time.sleep(1.0)
                continue

            crop_x = x + int(w * POLL_X_PCT[0])
            crop_y = y + int(h * POLL_Y_PCT[0])
            crop_w = int(w * (POLL_X_PCT[1] - POLL_X_PCT[0]))
            crop_h = int(h * (POLL_Y_PCT[1] - POLL_Y_PCT[0]))

            monitor = {"top": crop_y, "left": crop_x, "width": crop_w, "height": crop_h}
            frame_gray = cv2.cvtColor(np.array(sct.grab(monitor)), cv2.COLOR_BGRA2GRAY)

            if h != cached_h:
                sf = h / TEMPLATE_BASE_HEIGHT
                l_scaled = cv2.resize(template_left, (0, 0), fx=sf, fy=sf, interpolation=cv2.INTER_LINEAR)
                r_scaled = cv2.resize(template_right, (0, 0), fx=sf, fy=sf, interpolation=cv2.INTER_LINEAR)
                left_t_gray = cv2.cvtColor(l_scaled, cv2.COLOR_BGR2GRAY)
                right_t_gray = cv2.cvtColor(r_scaled, cv2.COLOR_BGR2GRAY)
                cached_h = h

            if left_t_gray.shape[0] <= frame_gray.shape[0] and left_t_gray.shape[1] <= frame_gray.shape[1]:
                max_l = cv2.minMaxLoc(cv2.matchTemplate(frame_gray, left_t_gray, cv2.TM_CCOEFF_NORMED))[1]
                max_r = cv2.minMaxLoc(cv2.matchTemplate(frame_gray, right_t_gray, cv2.TM_CCOEFF_NORMED))[1]
                max_val = max(max_l, max_r)

                print(f"Monitoring... (Best Match Score: {max_val:.2f})", end="\r")

                if max_val >= MATCH_THRESHOLD and not match_reported:
                    match_reported = True
                    x, y, w, h = get_game_client_area(hwnd)
                    start_time = time.time()

                    while time.time() - start_time < 5.0:
                        try:
                            full_monitor = {"top": y, "left": x, "width": w, "height": h}
                            full_frame = cv2.cvtColor(np.array(sct.grab(full_monitor)), cv2.COLOR_BGRA2BGR)
                            u_name, o_name = extract_usernames(full_frame, w, h)

                            if len(u_name) >= 4 and len(o_name) >= 4:
                                callback_function(u_name, o_name)
                                break
                        except Exception:
                            pass
                        time.sleep(0.05)

            if max_val < MATCH_THRESHOLD:
                match_reported = False

            time.sleep(0.2)


def on_match_found(user_name, opponent_name):
    device_id = load_device_id()

    print(f"\n\n[MATCH DETECTED]")
    print(f"Me       : {user_name}")
    print(f"Opponent : {opponent_name}")
    print("-------------------------------------------------")

    try:
        httpx.post("http://localhost:8000/bot/match", json={
            "device_id": device_id,
            "left": user_name,
            "right": opponent_name,
        })
    except Exception as e:
        print(f"Failed to report match: {e}")


if __name__ == "__main__":
    monitor_matchmaking(on_match_found)
