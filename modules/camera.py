from __future__ import annotations

import time
from collections.abc import Iterator
from threading import Condition, Event, Lock, Thread

import cv2
import numpy as np
import zxingcpp
from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from nicegui import app

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:  # pragma: no cover
    pyzbar_decode = None


CAMERA_INDEX = 0
_barcode_lock = Lock()
_latest_barcode: str | None = None


def clear_barcode() -> None:
    global _latest_barcode
    with _barcode_lock:
        _latest_barcode = None


def set_barcode(value: str) -> None:
    global _latest_barcode
    with _barcode_lock:
        _latest_barcode = value


def get_barcode() -> str | None:
    with _barcode_lock:
        return _latest_barcode


def _apply_camera_settings(capture) -> None:
    try:
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    except cv2.error:
        pass
    try:
        capture.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    except cv2.error:
        pass

    for property_id, value in (
        (getattr(cv2, 'CAP_PROP_ZOOM', -1), 150),
        (getattr(cv2, 'CAP_PROP_FOCUS', -1), 120),
        (getattr(cv2, 'CAP_PROP_AUTOFOCUS', -1), 0),
    ):
        if property_id < 0:
            continue
        try:
            capture.set(property_id, value)
        except cv2.error:
            continue


def _read_first_frame(capture, max_attempts: int = 5) -> np.ndarray | None:
    for attempt in range(max_attempts):
        try:
            success, frame = capture.read()
            if success and frame is not None:
                return frame
        except cv2.error:
            pass
        time.sleep(0.2)
    return None


def open_camera(index: int, backend: int | None = None):
    candidate_backends: list[int | None] = []
    if backend is not None:
        candidate_backends.append(backend)
    else:
        candidate_backends.extend([cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY, None])

    last_error = None
    for candidate in candidate_backends:
        try:
            if candidate is None:
                capture = cv2.VideoCapture(index)
            else:
                capture = cv2.VideoCapture(index, candidate)
            if capture is not None and capture.isOpened():
                _apply_camera_settings(capture)
                frame = _read_first_frame(capture)
                if frame is not None:
                    return capture
            if capture is not None:
                capture.release()
        except cv2.error as error:
            last_error = error
            continue
    if last_error:
        raise last_error
    return None


def find_camera_index() -> int | None:
    best_index = None
    best_area = 0
    candidate_indexes = [CAMERA_INDEX, *[index for index in range(1, 10) if index != CAMERA_INDEX]]
    for index in candidate_indexes:
        try:
            capture = open_camera(index)
        except cv2.error:
            continue
        if capture is None:
            continue
        try:
            success, frame = capture.read()
            if not success or frame is None:
                continue
            height, width = frame.shape[:2]
            if width * height > best_area:
                best_index = index
                best_area = width * height
                if index == CAMERA_INDEX:
                    return best_index
        finally:
            capture.release()
    return best_index


def _normalize_barcode(value: str) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    digits = ''.join(ch for ch in text if ch.isdigit())
    if 8 <= len(digits) <= 14:
        return digits
    if 8 <= len(text) <= 14:
        return text
    return None


def _candidate_rois(frame) -> list[np.ndarray]:
    height, width = frame.shape[:2]
    if height == 0 or width == 0:
        return [frame]

    candidates = [
        frame,
        frame[0:height, max(0, width // 8):min(width, width * 7 // 8)],
        frame[max(0, height // 6):min(height, height * 5 // 6), :],
        frame[max(0, height // 8):min(height, height * 7 // 8), max(0, width // 8):min(width, width * 7 // 8)],
        frame[max(0, height // 4):min(height, height * 3 // 4), max(0, width // 4):min(width, width * 3 // 4)],
    ]
    unique: list[np.ndarray] = []
    seen: set[int] = set()
    for candidate in candidates:
        key = id(candidate)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _decode_ean13_scanline(frame: np.ndarray) -> str | None:
    left_patterns = {
        '0001101': '0', '0011001': '1', '0010011': '2', '0111101': '3', '0100011': '4',
        '0110001': '5', '0101111': '6', '0111011': '7', '0110111': '8', '0001011': '9',
    }
    right_patterns = {
        '1110010': '0', '1100110': '1', '1101100': '2', '1000010': '3', '1011100': '4',
        '1001110': '5', '1010000': '6', '1000100': '7', '1001000': '8', '1110100': '9',
    }
    g_patterns = {
        '0100111': '0', '0110011': '1', '0011011': '2', '0100001': '3', '0011101': '4',
        '0111001': '5', '0000101': '6', '0010001': '7', '0001001': '8', '0010111': '9',
    }
    parity_patterns = {
        'LLLLLL': '0', 'LLGLGG': '1', 'LLGGLG': '2', 'LLGGGL': '3', 'LGLLGG': '4',
        'LGGLLG': '5', 'LGGGLL': '6', 'LGLLGL': '7', 'LGLGLG': '8', 'LGGLGL': '9',
    }
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    for row in thresholded[thresholded.shape[0] // 3:thresholded.shape[0] * 2 // 3:4]:
        dark = np.flatnonzero(row < 128)
        if dark.size < 95:
            continue
        cropped = row[dark[0]:dark[-1] + 1]
        sampled = cv2.resize(cropped.reshape(1, -1), (95, 1), interpolation=cv2.INTER_AREA)[0]
        bits = ''.join('1' if value < 128 else '0' for value in sampled)
        if not (bits.startswith('101') and bits[45:50] == '01010' and bits.endswith('101')):
            continue
        first = bits[3:45]
        last = bits[50:92]
        left_digits = []
        parity = []
        for offset in range(0, 42, 7):
            pattern = first[offset:offset + 7]
            if pattern in left_patterns:
                left_digits.append(left_patterns[pattern])
                parity.append('L')
            elif pattern in g_patterns:
                left_digits.append(g_patterns[pattern])
                parity.append('G')
            else:
                break
        if len(left_digits) != 6 or ''.join(parity) not in parity_patterns:
            continue
        right_digits = [right_patterns.get(last[offset:offset + 7]) for offset in range(0, 42, 7)]
        if any(digit is None for digit in right_digits):
            continue
        return parity_patterns[''.join(parity)] + ''.join(left_digits) + ''.join(right_digits)
    return None


def decode_frame(detector: cv2.barcode_BarcodeDetector, frame) -> str | None:
    def to_gray(image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def variants_for(image: np.ndarray) -> list[np.ndarray]:
        gray = to_gray(image)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        normalized = [
            image,
            gray,
            blurred,
            binary,
            cv2.bitwise_not(binary),
            cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC),
        ]
        for rotated in (
            cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
            cv2.rotate(image, cv2.ROTATE_180),
        ):
            normalized.extend([rotated, to_gray(rotated)])
        return normalized

    candidate_frames: list[np.ndarray] = []
    for roi in _candidate_rois(frame):
        candidate_frames.extend(variants_for(roi))
    candidate_frames.extend(variants_for(frame))

    seen_variants: set[int] = set()
    for variant in candidate_frames:
        variant_id = id(variant)
        if variant_id in seen_variants:
            continue
        seen_variants.add(variant_id)
        for rotation in (variant, cv2.rotate(variant, cv2.ROTATE_90_CLOCKWISE), cv2.rotate(variant, cv2.ROTATE_180), cv2.rotate(variant, cv2.ROTATE_90_COUNTERCLOCKWISE)):
            try:
                results = zxingcpp.read_barcodes(
                    rotation,
                    try_rotate=True,
                    try_downscale=True,
                    try_invert=True,
                )
                for result in results:
                    if result.text:
                        normalized = _normalize_barcode(result.text)
                        if normalized:
                            return normalized
            except (RuntimeError, ValueError, cv2.error):
                pass
            try:
                result = detector.detectAndDecode(rotation)
                value = result[0] if isinstance(result, tuple) else result
                if isinstance(value, str):
                    normalized = _normalize_barcode(value)
                    if normalized:
                        return normalized
                if isinstance(value, (list, tuple)):
                    for item in value:
                        if isinstance(item, str):
                            normalized = _normalize_barcode(item)
                            if normalized:
                                return normalized
            except cv2.error:
                continue
            if pyzbar_decode is not None:
                try:
                    for decoded in pyzbar_decode(rotation):
                        if decoded.data:
                            normalized = _normalize_barcode(decoded.data.decode('utf-8', 'ignore'))
                            if normalized:
                                return normalized
                except Exception:
                    pass
    return _decode_ean13_scanline(frame)


class CameraManager:
    def __init__(self) -> None:
        self.condition = Condition()
        self.latest_frame: bytes | None = None
        self.frame_number = 0
        self.clients = 0
        self.thread: Thread | None = None
        self.stop_event = None

    def subscribe(self) -> None:
        thread_to_join: Thread | None = None
        with self.condition:
            self.clients += 1
            if self.thread is not None and self.thread.is_alive() and self.stop_event and self.stop_event.is_set():
                thread_to_join = self.thread

        if thread_to_join is not None:
            thread_to_join.join(timeout=1.0)

        with self.condition:
            if self.thread is None or not self.thread.is_alive():
                self.latest_frame = None
                self.stop_event = Event()
                self.thread = Thread(target=self._capture_loop, daemon=True)
                self.thread.start()

    def unsubscribe(self) -> None:
        with self.condition:
            self.clients = max(0, self.clients - 1)
            if self.clients == 0 and self.stop_event:
                self.stop_event.set()
            self.condition.notify_all()

    def wait_for_frame(self, previous_number: int) -> tuple[int, bytes] | None:
        with self.condition:
            self.condition.wait_for(
                lambda: self.frame_number > previous_number or self.thread is None,
                timeout=2.0,
            )
            if self.latest_frame is None or self.frame_number <= previous_number:
                return None
            return self.frame_number, self.latest_frame

    def _capture_loop(self) -> None:
        index = find_camera_index()
        if index is None:
            return
        capture = open_camera(index)
        if capture is None:
            return
        _apply_camera_settings(capture)
        detector = cv2.barcode_BarcodeDetector()
        try:
            while self.stop_event and not self.stop_event.is_set():
                try:
                    success, frame = capture.read()
                    if not success or frame is None:
                        time.sleep(0.05)
                        continue
                except cv2.error:
                    time.sleep(0.05)
                    continue
                try:
                    decoded = decode_frame(detector, frame)
                    if decoded:
                        set_barcode(decoded)
                except cv2.error:
                    pass
                encoded, buffer = cv2.imencode('.jpg', frame)
                if not encoded:
                    continue
                payload = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
                with self.condition:
                    self.latest_frame = payload
                    self.frame_number += 1
                    self.condition.notify_all()
        finally:
            capture.release()
            with self.condition:
                self.thread = None
                self.condition.notify_all()

    def stream(self) -> Iterator[bytes]:
        self.subscribe()
        frame_number = -1
        saw_frame = False
        try:
            while True:
                result = self.wait_for_frame(frame_number)
                if result is None:
                    if self.thread is None:
                        if not saw_frame:
                            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b'\r\n'
                        return
                    continue
                frame_number, payload = result
                saw_frame = True
                yield payload
        finally:
            self.unsubscribe()


CAMERA = CameraManager()


@app.get('/camera/stream')
def camera_stream() -> Response:
    if find_camera_index() is None:
        return JSONResponse({'error': 'Camera unavailable'}, status_code=503)
    return StreamingResponse(
        CAMERA.stream(),
        media_type='multipart/x-mixed-replace; boundary=frame',
    )


@app.get('/camera/barcode')
def camera_barcode(clear: bool = False) -> JSONResponse:
    if clear:
        clear_barcode()
    return JSONResponse({'barcode': get_barcode()})


@app.post('/camera/decode')
async def camera_decode(request: Request) -> JSONResponse:
    payload = await request.body()
    frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({'barcode': None, 'error': 'Invalid camera frame'}, status_code=400)
    detector = cv2.barcode_BarcodeDetector()
    decoded = decode_frame(detector, frame)
    if decoded:
        set_barcode(decoded)
    return JSONResponse({'barcode': decoded})
