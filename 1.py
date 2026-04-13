import socket

# Слушаем всё
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 42555))
print("Waiting for any data on 42555...")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"Received {len(data)} bytes from {addr}: {data.hex().upper()}")