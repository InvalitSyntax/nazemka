#!/usr/bin/env python3

import socket
import signal
import struct
from dataclasses import dataclass

HOST = "0.0.0.0"
PORT = 40555
BUF_SIZE = 16384

# C struct from posData.h:
# typedef struct {
#   uint64_t timestamp; // us
#   float angle;        // deg
#   float x, y, z;
#   float vx, vy, vz;
# } PositionCenterData_t;

PACKET_FMT = "<Q7f"  # little-endian: u64 + 7 floats
PACKET_SIZE = 8 + 7 * 4  # 36 bytes

@dataclass
class PositionCenterData:
    timestamp: int  # microseconds
    angle: float
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float

def decode_position_center(raw_bytes: bytes) -> PositionCenterData:
    if len(raw_bytes) != PACKET_SIZE:
        raise ValueError(f"Wrong size: expected {PACKET_SIZE}, got {len(raw_bytes)}")
    ts, angle, x, y, z, vx, vy, vz = struct.unpack(PACKETS_FMT if False else PACKET_FMT, raw_bytes)
    return PositionCenterData(ts, angle, x, y, z, vx, vy, vz)

stop = False
sock = None

def _signal_handler(sig, frame):
    global stop, sock
    stop = True
    try:
        if sock:
            sock.close()
    except Exception:
        pass
    
def main():
    global stop, sock
    signal.signal(signal.SIGINT, _signal_handler)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    print(f"Listening for UDP on {HOST}:{PORT}")
    counter = 0
    try:
        while not stop:
            try:
                data, addr = sock.recvfrom(BUF_SIZE)
                # print(f"Received {len(data)} bytes from {addr}")
            except OSError:
                break
            if not data:
                continue
            try:
                buffer = data
                while len(buffer) >= PACKET_SIZE:
                    packet = buffer[:PACKET_SIZE]
                    buffer = buffer[PACKET_SIZE:]
                    pos = decode_position_center(packet)
                    if pos.timestamp != 0:
                        counter += 1
                        print(
                            addr,
                            pos.timestamp / 1_000_000.0,
                            PACKET_SIZE,
                            counter,
                            pos.angle,
                            pos.x,
                        )
            except Exception as e:
                print("Decode error:", e)
    finally:
        try:
            sock.close()
        except Exception:
            pass
        sock = None
        print("UDP server stopped")

if __name__ == "__main__":
    main()
