from __future__ import annotations

import math
import random
import socket
import struct
import time


DST_IP = "127.0.0.1"
DST_PORT = 40555

MODE = "smooth"  # "random" | "smooth"

RANDOM_SLEEP_RANGE_S = (0.01, 0.35)

SMOOTH_HZ = 60.0

SMOOTH_AX_MM = 1800.0
SMOOTH_AY_MM = 1800.0
SMOOTH_W_RAD_S = 0.7
SMOOTH_DRIFT_MM_S = 120.0

Z_AMP_MM = 200.0
Z_W_RAD_S = 0.3


_FMT = "<Qfffffff"
_SIZE = struct.calcsize(_FMT)


def _send(
    sock: socket.socket,
    ip: str,
    port: int,
    t_us: int,
    angle_deg: float,
    x_mm: float,
    y_mm: float,
    z_mm: float,
    vx_mm_s: float,
    vy_mm_s: float,
    vz_mm_s: float,
) -> None:
    payload = struct.pack(
        _FMT,
        t_us,
        float(angle_deg),
        float(x_mm),
        float(y_mm),
        float(z_mm),
        float(vx_mm_s),
        float(vy_mm_s),
        float(vz_mm_s),
    )
    if len(payload) != _SIZE:
        raise RuntimeError("Bad packet size")
    sock.sendto(payload, (ip, port))


def run_random(sock: socket.socket) -> None:
    t0 = time.monotonic()
    while True:
        time.sleep(random.uniform(*RANDOM_SLEEP_RANGE_S))

        t_us = int((time.monotonic() - t0) * 1_000_000)

        angle = random.uniform(0.0, 360.0)

        x = random.uniform(-2500.0, 2500.0)
        y = random.uniform(-2500.0, 2500.0)
        z = random.uniform(-500.0, 500.0)

        v = random.uniform(0.0, 1500.0)
        phi = random.uniform(0.0, 2.0 * math.pi)
        vx = v * math.cos(phi)
        vy = v * math.sin(phi)
        vz = random.uniform(-200.0, 200.0)

        print(angle, x/10000, y/10000, z/10000)
        _send(sock, DST_IP, DST_PORT, t_us, angle, x/10000, y/10000, z/10000, vx, vy, vz)


def run_smooth(sock: socket.socket) -> None:
    dt = 1.0 / max(SMOOTH_HZ, 1e-9)
    t0 = time.monotonic()

    while True:
        t = time.monotonic() - t0
        t_us = int(t * 1_000_000)

        x = SMOOTH_AX_MM * math.cos(SMOOTH_W_RAD_S * t) + SMOOTH_DRIFT_MM_S * t
        y = SMOOTH_AY_MM * math.sin(SMOOTH_W_RAD_S * t)
        z = Z_AMP_MM * math.sin(Z_W_RAD_S * t)

        vx = -SMOOTH_AX_MM * SMOOTH_W_RAD_S * math.sin(SMOOTH_W_RAD_S * t) + SMOOTH_DRIFT_MM_S
        vy = SMOOTH_AY_MM * SMOOTH_W_RAD_S * math.cos(SMOOTH_W_RAD_S * t)
        vz = Z_AMP_MM * Z_W_RAD_S * math.cos(Z_W_RAD_S * t)

        angle = (math.degrees(math.atan2(vy, vx)) + 360.0) % 360.0

        print(angle, x/10000, y/10000, z/10000)
        _send(sock, DST_IP, DST_PORT, t_us, angle, x/10000, y/10000, z/100, vx, vy, vz)
        time.sleep(dt)


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        if MODE == "random":
            run_random(sock)
        elif MODE == "smooth":
            run_smooth(sock)
        else:
            raise ValueError("MODE must be 'random' or 'smooth'")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
