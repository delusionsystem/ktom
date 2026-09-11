import cv2
import numpy as np

from modules.camera import camera_stream, decode_frame, open_camera

LEFT = [
    '0001101', '0011001', '0010011', '0111101', '0100011',
    '0110001', '0101111', '0111011', '0110111', '0001011',
]
RIGHT = [
    '1110010', '1100110', '1101100', '1000010', '1011100',
    '1001110', '1010000', '1000100', '1001000', '1110100',
]
PARITY = {
    '0': ['L', 'L', 'L', 'L', 'L', 'L'],
    '1': ['L', 'L', 'G', 'L', 'G', 'G'],
    '2': ['L', 'L', 'G', 'G', 'L', 'G'],
    '3': ['L', 'L', 'G', 'G', 'G', 'L'],
    '4': ['L', 'G', 'L', 'L', 'G', 'G'],
    '5': ['L', 'G', 'G', 'L', 'L', 'G'],
    '6': ['L', 'G', 'G', 'G', 'L', 'L'],
    '7': ['L', 'G', 'L', 'L', 'G', 'L'],
    '8': ['L', 'G', 'L', 'G', 'L', 'G'],
    '9': ['L', 'G', 'G', 'L', 'G', 'L'],
}
G = [
    '0100111', '0110011', '0011011', '0100001', '0011101',
    '0111001', '0000101', '0010001', '0001001', '0010111',
]


def _build_ean13(code: str = '9781234567890') -> np.ndarray:
    assert len(code) == 13 and code.isdigit()
    pattern = ['101']
    for index, digit in enumerate(code[1:7]):
        mode = PARITY[code[0]][index]
        pattern.append(LEFT[int(digit)] if mode == 'L' else G[int(digit)])
    pattern.append('01010')
    for digit in code[7:]:
        pattern.append(RIGHT[int(digit)])
    pattern.append('101')
    flat = ''.join(pattern)

    width = len(flat) * 4 + 80
    height = 220
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    x = 30
    for bit in flat:
        color = 0 if bit == '1' else 255
        cv2.rectangle(image, (x, 30), (x + 3, height - 30), (color, color, color), -1)
        x += 4
    return image


def test_decode_frame_recovers_ean13_from_generated_barcode() -> None:
    image = _build_ean13(code='9781234567890')
    detector = cv2.barcode_BarcodeDetector()
    assert decode_frame(detector, image) == '9781234567890'


def test_open_camera_falls_back_to_default_backend(monkeypatch) -> None:
    backends = []

    class FakeCapture:
        def __init__(self, opened: bool) -> None:
            self._opened = opened

        def isOpened(self) -> bool:
            return self._opened

        def set(self, *args, **kwargs):
            return True

        def read(self):
            return True, np.zeros((480, 640, 3), dtype=np.uint8)

        def release(self) -> None:
            return None

    def fake_video_capture(index, backend=None):
        backends.append((index, backend))
        if backend == cv2.CAP_DSHOW:
            return FakeCapture(False)
        if backend == cv2.CAP_MSMF:
            return FakeCapture(False)
        return FakeCapture(True)

    monkeypatch.setattr(cv2, 'VideoCapture', fake_video_capture)

    capture = open_camera(0)
    assert capture is not None
    assert capture.isOpened() is True
    assert any(backend == cv2.CAP_DSHOW for _, backend in backends)
    assert any(backend in (cv2.CAP_MSMF, None) for _, backend in backends)


def test_camera_stream_returns_503_when_camera_missing(monkeypatch) -> None:
    monkeypatch.setattr('modules.camera.find_camera_index', lambda: None)

    response = camera_stream()
    assert response.status_code == 503
    assert response.body == b'{"error":"Camera unavailable"}'
