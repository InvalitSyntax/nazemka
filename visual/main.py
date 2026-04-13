from __future__ import annotations

import argparse
import math
import time
from collections import deque
from threading import Lock, Thread
from typing import Deque, Optional, Tuple

from udp import PoseState, iter_position_center_data_one_sender, to_pose_state
from window import LiveTrackView


class TrackStore:
    def __init__(self, maxlen: int = 50) -> None:
        self._lock = Lock()
        self._xs: Deque[float] = deque(maxlen=maxlen)
        self._ys: Deque[float] = deque(maxlen=maxlen)
        self._last: Optional[PoseState] = None

    def push(self, st: PoseState) -> None:
        with self._lock:
            self._xs.append(st.x_m)
            self._ys.append(st.y_m)
            self._last = st

    def snapshot(self) -> Tuple[list[float], list[float], Optional[PoseState]]:
        with self._lock:
            return list(self._xs), list(self._ys), self._last


def _udp_worker(store: TrackStore) -> None:
    for msg, _peer in iter_position_center_data_one_sender():
        store.push(to_pose_state(msg))


def _test_worker(store: TrackStore, hz: float = 50.0) -> None:
    dt = 1.0 / max(hz, 1e-9)
    t0 = time.time()
    k = 0

    while True:
        tt = time.time() - t0

        x_m = 0.6 * math.cos(0.7 * tt) + 0.01 * k
        y_m = 0.6 * math.sin(0.7 * tt)

        angle_deg = (tt * 70.0) % 360.0

        vx_mps = -0.6 * 0.7 * math.sin(0.7 * tt) + 0.01 / dt
        vy_mps = 0.6 * 0.7 * math.cos(0.7 * tt)

        store.push(PoseState(x_m, y_m, angle_deg, vx_mps, vy_mps, t_us=k))
        k += 1
        time.sleep(dt)


def _painter_worker(view: LiveTrackView, store: TrackStore, hz: float = 60.0) -> None:
    dt = 1.0 / max(hz, 1e-9)
    last_t_us: Optional[int] = None

    while True:
        xs, ys, last = store.snapshot()
        if last is not None and last.t_us != last_t_us:
            view.set_frame(xs, ys, last)
            last_t_us = last.t_us
        time.sleep(dt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    store = TrackStore(maxlen=100)
    view = LiveTrackView(circle_center=(0.0, 0.0), circle_radius_m=2.0, maximize=True, arrow_len_m=0.3, refresh_hz=120)

    feeder = Thread(target=_test_worker if args.test else _udp_worker, args=(store,), daemon=True)
    feeder.start()

    painter = Thread(target=_painter_worker, args=(view, store), daemon=True)
    painter.start()

    view.run()


if __name__ == "__main__":
    main()
