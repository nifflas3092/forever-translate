"""Reads the coloured block strip that the Forever Translate addon draws
in the corner of the WoW window, and turns it back into chat messages.

The layout must match addon/ForeverTranslate/Encoder.lua.
"""

import threading
import time

import numpy as np

COLS = 64
ROWS = 8
BLOCKS = COLS * ROWS
HEADER_BLOCKS = 23

_cols = np.arange(BLOCKS) % COLS
_rows = np.arange(BLOCKS) // COLS


def _runs(mask_row):
    """Start and length of each run of True values in a 1-D bool array."""
    padded = np.concatenate(([False], mask_row, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[0::2], edges[1::2]
    return starts, ends - starts


def _masks(img):
    r = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    b = img[:, :, 2].astype(np.int16)
    magenta = (r > 190) & (g < 80) & (b > 190)
    green = (g > 190) & (r < 80) & (b < 80)
    return magenta, green


def _measure(img, magenta, green, x, y, size):
    """Use the green+magenta end marker in the bottom-right corner to get the
    exact block width and height (blocks can be e.g. 3.4 pixels wide)."""
    h, w = magenta.shape
    yc = int(y + (ROWS - 0.5) * size)
    if yc >= h:
        return None
    lo = int(x + (COLS - 2) * size * 0.85)
    hi = min(w, int(x + COLS * size * 1.15) + 2)
    starts, lengths = _runs(magenta[yc, lo:hi])
    for start, length in zip(starts, lengths):
        start += lo
        if start > 0 and green[yc, start - 1] and size * 0.5 - 1 <= length <= size * 1.5 + 1:
            end_x = start + length
            break
    else:
        return None
    sx = (end_x - x) / COLS
    xc = int(start + length / 2)
    end_y = yc
    while end_y < h and magenta[end_y, xc]:
        end_y += 1
    sy = (end_y - y) / ROWS
    return sx, sy


def find_grid(img):
    """Find the strip in a screenshot (H x W x 3 RGB array).

    Returns (x0, y0, block_width, block_height) or None.
    """
    magenta, green = _masks(img)
    rows = np.flatnonzero(magenta.any(axis=1))
    width = img.shape[1]
    for y in rows[:4000]:
        starts, lengths = _runs(magenta[y])
        for x, w in zip(starts, lengths):
            if w < 2 or w > 60:
                continue
            # expect: magenta(w) green magenta green, each about w wide
            pos = x + w
            ok = True
            for want_green in (True, False, True):
                row = green[y] if want_green else magenta[y]
                if pos >= width or not row[pos]:
                    ok = False
                    break
                end = pos
                while end < width and row[end]:
                    end += 1
                if not (w * 0.5 - 1 <= end - pos <= w * 1.5 + 1):
                    ok = False
                    break
                pos = end
            if not ok:
                continue
            size = (pos - x) / 4.0
            if size < 2:
                continue
            measured = _measure(img, magenta, green, x, y, size)
            if not measured:
                continue
            sx, sy = measured
            if not _calibration_ok(_sample(img, x, y, sx, sy)):
                continue
            return float(x), float(y), sx, sy
    return None


def _sample(img, x0, y0, sx, sy):
    xs = (x0 + (_cols + 0.5) * sx).astype(int)
    ys = (y0 + (_rows + 0.5) * sy).astype(int)
    if xs.max() >= img.shape[1] or ys.max() >= img.shape[0] or xs.min() < 0 or ys.min() < 0:
        return None
    return img[ys, xs, :3].astype(np.int16)


def _calibration_ok(values):
    if values is None:
        return False
    cal = values[4:20].mean(axis=1)
    return cal[15] - cal[0] > 100 and np.all(np.diff(cal) >= -6)


def decode_values(values):
    """Decode sampled block colours. Returns (seq, text) or None."""
    if values is None:
        return None
    finder = values[0:4]
    if not (finder[0, 0] > 190 and finder[0, 1] < 80 and finder[1, 1] > 190 and finder[1, 0] < 80
            and finder[2, 0] > 190 and finder[3, 1] > 190):
        return None
    if not _calibration_ok(values):
        return None
    cal = values[4:20]  # 16 levels x 3 channels
    # nearest calibration level, per channel
    diff = np.abs(values[:, :, None] - cal.T[None, :, :])  # BLOCKS x 3 x 16
    nib = diff.argmin(axis=2)

    def read12(i):
        return int(nib[i, 0]) * 256 + int(nib[i, 1]) * 16 + int(nib[i, 2])

    seq, length, checksum = read12(20), read12(21), read12(22)
    stream = nib[HEADER_BLOCKS:BLOCKS - 2].reshape(-1)
    if length * 2 > len(stream):
        return None
    pairs = stream[: length * 2].reshape(-1, 2)
    data = bytes((pairs[:, 0] * 16 + pairs[:, 1]).astype(np.uint8).tolist())
    total = 0
    for i, byte in enumerate(data):
        total = (total + byte * (i % 7 + 1)) % 4096
    if total != checksum:
        return None
    return seq, data.decode("utf-8", errors="replace")


def decode(img, x0, y0, sx, sy):
    return decode_values(_sample(img, x0, y0, sx, sy))


def parse_payload(text):
    """'Channel\\tSender\\tMessage' -> (channel, sender, message)."""
    parts = text.split("\t", 2)
    while len(parts) < 3:
        parts.insert(0, "")
    return parts[0], parts[1], parts[2]


class BridgeReader(threading.Thread):
    """Watches the screen and calls on_message(channel, sender, text) for
    every new message, and on_status(str) when the connection changes."""

    POLL_SECONDS = 1 / 40
    SEARCH_SECONDS = 1.0
    LOST_AFTER_SECONDS = 2.0

    def __init__(self, on_message, on_status):
        super().__init__(daemon=True)
        self.on_message = on_message
        self.on_status = on_status
        self.stop_flag = threading.Event()

    def stop(self):
        self.stop_flag.set()

    def run(self):
        import mss  # imported here so the decoder can be tested without it

        lock = None
        last_seq = None
        last_good = 0.0
        status = None

        def set_status(s):
            nonlocal status
            if s != status:
                status = s
                self.on_status(s)

        with mss.mss() as sct:
            while not self.stop_flag.is_set():
                if lock is None:
                    set_status("searching")
                    for mon in sct.monitors[1:]:
                        shot = np.asarray(sct.grab(mon))[:, :, [2, 1, 0]]  # BGRA -> RGB
                        found = find_grid(shot)
                        if found:
                            x, y, sx, sy = found
                            lock = (mon["left"] + x, mon["top"] + y, sx, sy)
                            last_good = time.time()
                            set_status("connected")
                            break
                    if lock is None:
                        self.stop_flag.wait(self.SEARCH_SECONDS)
                    continue

                ax, ay, sx, sy = lock
                margin = 2
                region = {
                    "left": int(ax) - margin,
                    "top": int(ay) - margin,
                    "width": int(COLS * sx) + 2 * margin + 2,
                    "height": int(ROWS * sy) + 2 * margin + 2,
                }
                try:
                    shot = np.asarray(sct.grab(region))[:, :, [2, 1, 0]]
                    result = decode(shot, ax - region["left"], ay - region["top"], sx, sy)
                except Exception:
                    result = None
                now = time.time()
                if result:
                    last_good = now
                    seq, payload = result
                    if seq != last_seq:
                        last_seq = seq
                        self.on_message(*parse_payload(payload))
                elif now - last_good > self.LOST_AFTER_SECONDS:
                    lock = None
                    continue
                self.stop_flag.wait(self.POLL_SECONDS)
