"""
core/screencast.py
------------------
Thread-safe ScreencastBroadcaster singleton.

Playwright verifiers push base64 PNG frames + action labels here.
The WebSocket server drains connected clients and streams each frame.
"""

import threading
import queue
import json
import base64
from collections import deque
from pathlib import Path

MAX_RING_BUFFER = 200   # how many frames to keep for replay scrubbing


class ScreencastBroadcaster:
    """
    Singleton that accepts Playwright screenshot frames and broadcasts
    them to all connected WebSocket clients in real-time.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Each connected WS client gets its own queue
        self._client_queues: list[queue.Queue] = []
        # Ring buffer for replay (stores dict with 'frame' and 'label')
        self._ring_buffer: deque = deque(maxlen=MAX_RING_BUFFER)
        self._current_label: str = "Idle"
        self._is_live: bool = False

    # ------------------------------------------------------------------
    # Called by Playwright verifier scripts
    # ------------------------------------------------------------------

    def push_frame(self, png_bytes: bytes, label: str = "") -> None:
        """
        Push a raw PNG screenshot (bytes) into the broadcast pipeline.
        All connected clients will receive this frame immediately.
        """
        b64 = base64.b64encode(png_bytes).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64}"
        msg = json.dumps({
            "type": "frame",
            "data": data_uri,
            "label": label or self._current_label,
            "frame_index": len(self._ring_buffer)
        })

        with self._lock:
            self._ring_buffer.append({"data": data_uri, "label": label or self._current_label})
            if label:
                self._current_label = label
            for q in self._client_queues:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass  # skip slow clients rather than blocking Playwright

    def push_frame_from_path(self, png_path: str, label: str = "") -> None:
        """Convenience: push from a screenshot file path."""
        path = Path(png_path)
        if path.exists():
            self.push_frame(path.read_bytes(), label)

    def set_label(self, label: str) -> None:
        """Update the current action label (broadcast as a standalone message)."""
        with self._lock:
            self._current_label = label
        msg = json.dumps({"type": "label", "label": label})
        with self._lock:
            for q in self._client_queues:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

    def set_live(self, is_live: bool) -> None:
        """Broadcast a live/idle status change to all clients."""
        self._is_live = is_live
        msg = json.dumps({"type": "status", "live": is_live})
        with self._lock:
            for q in self._client_queues:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

    def clear(self) -> None:
        """Reset ring buffer between verification runs."""
        with self._lock:
            self._ring_buffer.clear()
            self._current_label = "Idle"
            self._is_live = False

    # ------------------------------------------------------------------
    # Called by WebSocket server to register/unregister clients
    # ------------------------------------------------------------------

    def register_client(self) -> queue.Queue:
        """Register a new WebSocket client and return its frame queue."""
        q: queue.Queue = queue.Queue(maxsize=50)

        with self._lock:
            self._client_queues.append(q)
            # Send the last frame immediately so client doesn't see blank screen
            if self._ring_buffer:
                last = self._ring_buffer[-1]
                init_msg = json.dumps({
                    "type": "frame",
                    "data": last["data"],
                    "label": last["label"],
                    "frame_index": len(self._ring_buffer) - 1
                })
                q.put_nowait(init_msg)
            # Also send replay buffer size so frontend can set up scrubber
            meta_msg = json.dumps({
                "type": "meta",
                "total_frames": len(self._ring_buffer),
                "live": self._is_live,
                "label": self._current_label
            })
            q.put_nowait(meta_msg)

        return q

    def unregister_client(self, q: queue.Queue) -> None:
        """Remove a disconnected WebSocket client."""
        with self._lock:
            if q in self._client_queues:
                self._client_queues.remove(q)

    def get_replay_frame(self, index: int) -> dict | None:
        """Return a specific frame from the ring buffer for replay."""
        with self._lock:
            buf = list(self._ring_buffer)
            if 0 <= index < len(buf):
                return buf[index]
        return None

    def get_all_replay_frames(self) -> list[dict]:
        """Return all buffered frames for replay export."""
        with self._lock:
            return list(self._ring_buffer)


# Global singleton — imported by verifiers and server
screencast_broadcaster = ScreencastBroadcaster()
