import socket
import pathlib
from pathlib import Path
import os
import hashlib


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


BUFFER_SIZE = 4096 # send 4096 bytes each time step

p = Path("store_items")
SEPARATOR = "123"


# the ip address or hostname of the server, the receiver
host = "192.168.178.29"
# the port, let's use 5001
port = 5001
# the name of file we want to send, make sure it exists

# get the file size
filesize = p.stat().st_size

s = socket.socket()

print(f"[+] Connecting to {host}:{port}")
s.connect((host, port))
print("[+] Connected.")

with open(p, "rb") as f:
    while True:
        # read the bytes from the file
        bytes_read = f.read(BUFFER_SIZE)
        if not bytes_read:
            # file transmitting is done
            break
        # we use sendall to assure transimission in
        # busy networks
        s.sendall(bytes_read)

# close the socket
s.close()
