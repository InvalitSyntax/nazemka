from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from pprint import pprint


@dataclass(frozen=True, slots=True)
class PositionCenterData:
    timestamp: int
    angle: float
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float


@dataclass(frozen=True, slots=True)
class PoseState:
    x_m: float
    y_m: float
    angle_deg: float
    vx_mps: float
    vy_mps: float
    t_us: int


_FMT = "<Qfffffff"
_SIZE = struct.calcsize(_FMT)


def iter_position_center_data_one_sender(
    bind_ip: str = "0.0.0.0",
    bind_port: int = 40555,
    recv_buf: int = 2048,
) -> Iterator[Tuple[PositionCenterData, Tuple[str, int]]]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((bind_ip, bind_port))

        chosen: Optional[Tuple[str, int]] = None

        while True:
            payload, peer = sock.recvfrom(recv_buf)

            if chosen is None:
                chosen = peer

            if peer != chosen:
                continue

            ts, angle, x, y, z, vx, vy, vz = struct.unpack(_FMT, payload[:_SIZE:])
            print(ts, angle, x, y, z, vx, vy, vz)
            yield PositionCenterData(ts, angle, x, y, z, vx, vy, vz), peer
    finally:
        sock.close()


# def to_pose_state(msg: PositionCenterData) -> PoseState:
#     return PoseState(
#         x_m=msg.x / 1000.0,
#         y_m=msg.y / 1000.0,
#         angle_deg=msg.angle,
#         vx_mps=msg.vx / 1000.0,
#         vy_mps=msg.vy / 1000.0,
#         t_us=msg.timestamp,
#     )

def to_pose_state(msg: PositionCenterData) -> PoseState:
    return PoseState(
        x_m=msg.x,
        y_m=msg.y,
        angle_deg=msg.angle,
        vx_mps=msg.vx,
        vy_mps=msg.vy,
        t_us=msg.timestamp,
    )


def main() -> None:
    for msg, peer in iter_position_center_data_one_sender():
        print(peer, msg)


if __name__ == "__main__":
    main()