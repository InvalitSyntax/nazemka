from __future__ import annotations

import argparse
import math
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Deque, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from udp import PoseState


@dataclass(frozen=True, slots=True)
class TrackFrame:
    xs: Tuple[float, ...]
    ys: Tuple[float, ...]
    last: Optional[PoseState]


class LiveTrackView:
    def __init__(
        self,
        circle_center: Tuple[float, float] = (0.0, 0.0),
        circle_radius_m: float = 2.0,
        arrow_len_m: float = 0.6,
        refresh_hz: float = 60.0,
        maximize: bool = True,
    ) -> None:
        self._lock = Lock()
        self._frame: Optional[TrackFrame] = None

        self._arrow_len_m = arrow_len_m
        self._dt = 1.0 / max(refresh_hz, 1e-9)

        plt.ion()
        self._fig = plt.figure(figsize=(16, 9), constrained_layout=True)
        gs = self._fig.add_gridspec(1, 2, width_ratios=(5, 1))

        self._ax = self._fig.add_subplot(gs[0, 0])
        self._ax_txt = self._fig.add_subplot(gs[0, 1])

        circle = Circle(
            circle_center,
            circle_radius_m,
            edgecolor="red",
            facecolor="red",
            alpha=0.15,
            linewidth=2.0,
            zorder=1,
        )
        self._ax.add_patch(circle)
        self._ax.set_aspect("equal", adjustable="box")
        self._ax.grid(True, alpha=0.25)
        self._ax.set_xlabel("x, m")
        self._ax.set_ylabel("y, m")

        (self._track_artist,) = self._ax.plot([], [], "-", linewidth=1.3, color="black", alpha=0.65, zorder=2)
        (self._pos_artist,) = self._ax.plot([], [], "o", markersize=7, color="black", zorder=3)

        self._dir_artist = self._ax.quiver(
            [0.0], [0.0], [0.0], [0.0],
            angles="xy",
            scale_units="xy",
            scale=1.0,
            width=0.0025,
            headwidth=3.0,
            headlength=4.0,
            headaxislength=3.5,
            color="black",
            zorder=4,
        )

        self._ax_txt.set_axis_off()
        self._speed_text = self._ax_txt.text(
            0.05,
            0.85,
            "v = — m/s",
            fontsize=22,
            family="monospace",
            va="top",
        )

        if maximize:
            manager = getattr(self._fig.canvas, "manager", None)
            win = getattr(manager, "window", None)
            if win is not None and hasattr(win, "showMaximized"):
                win.showMaximized()
        
        self._circle_center = circle_center
        self._circle_radius_m = circle_radius_m

        (self._target_artist,) = self._ax.plot([], [], "x", color="orange", markersize=10, mew=2.0, zorder=10)
        self._target_text = self._ax.text(
            0.0,
            0.0,
            "target",
            color="orange",
            fontsize=14,
            va="bottom",
            ha="left",
            visible=False,
            zorder=10,
        )

        self._fig.canvas.mpl_connect("button_press_event", self._on_click)
    
    def _on_click(self, event) -> None:
        if event.inaxes is not self._ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        x_m = float(event.xdata)
        y_m = float(event.ydata)

        cx, cy = self._circle_center
        r = self._circle_radius_m

        if (x_m - cx) ** 2 + (y_m - cy) ** 2 > r ** 2:
            return

        x_mm = int(round(x_m * 1000.0))
        y_mm = int(round(y_m * 1000.0))
        print(f"target_mm: x={x_mm} y={y_mm}")

        self._target_artist.set_data([x_m], [y_m])
        self._target_text.set_position((x_m, y_m))
        self._target_text.set_visible(True)

        self._fig.canvas.draw_idle()


    def set_frame(self, xs: List[float], ys: List[float], last: Optional[PoseState]) -> None:
        frame = TrackFrame(tuple(xs), tuple(ys), last)
        with self._lock:
            self._frame = frame

    def _snapshot(self) -> Optional[TrackFrame]:
        with self._lock:
            return self._frame

    def run(self) -> None:
        last_t_us: Optional[int] = None

        while plt.fignum_exists(self._fig.number):
            fr = self._snapshot()
            if fr is not None and fr.last is not None and fr.last.t_us != last_t_us:
                st = fr.last
                x, y = st.x_m, st.y_m

                theta = math.radians(st.angle_deg)
                u = math.cos(theta) * self._arrow_len_m
                w = math.sin(theta) * self._arrow_len_m

                speed = math.hypot(st.vx_mps, st.vy_mps)

                self._track_artist.set_data(fr.xs, fr.ys)
                self._pos_artist.set_data([x], [y])
                self._dir_artist.set_offsets([[x, y]])
                self._dir_artist.set_UVC([u], [w])

                self._ax.relim()
                self._ax.autoscale_view()

                self._speed_text.set_text(f"v = {speed:7.3f} m/s")

                self._fig.canvas.draw_idle()
                last_t_us = st.t_us

            self._fig.canvas.flush_events()
            time.sleep(self._dt)



def _demo_feeder(view: LiveTrackView, maxlen: int = 50, hz: float = 50.0) -> None:
    dt = 1.0 / max(hz, 1e-9)
    xs: Deque[float] = deque(maxlen=maxlen)
    ys: Deque[float] = deque(maxlen=maxlen)

    k = 0
    t0 = time.time()

    while True:
        tt = time.time() - t0

        x_m = 0.6 * math.cos(0.8 * tt) + 0.01 * k
        y_m = 0.6 * math.sin(0.8 * tt)

        angle_deg = (tt * 60.0) % 360.0

        vx_mps = -0.6 * 0.8 * math.sin(0.8 * tt) + 0.01 / dt
        vy_mps = 0.6 * 0.8 * math.cos(0.8 * tt)

        st = PoseState(x_m, y_m, angle_deg, vx_mps, vy_mps, t_us=k)

        xs.append(st.x_m)
        ys.append(st.y_m)

        view.set_frame(list(xs), list(ys), st)

        k += 1
        time.sleep(dt)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--no-test", action="store_true")
    args = ap.parse_args()

    view = LiveTrackView(circle_center=(0.0, 0.0), circle_radius_m=2.0, maximize=True)

    if not args.no_test:
        Thread(target=_demo_feeder, args=(view,), daemon=True).start()

    view.run()


if __name__ == "__main__":
    main()
