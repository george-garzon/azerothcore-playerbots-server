"""Send a fixed command over Docker Desktop's local attach API (Windows pipe)."""
import ctypes
from ctypes import wintypes
import os
import re
import subprocess
import sys
import time
import msvcrt


def send(command):
    if command not in ("server info", "ollama reload", "reload creature_loot_template") and not re.fullmatch(
            r"announce Server shutdown in \d+ seconds\. Please finish safely\.", command):
        raise ValueError("Unsupported console command")
    endpoint = subprocess.check_output(["docker", "context", "inspect", "--format",
                                       "{{.Endpoints.docker.Host}}"], text=True).strip()
    if not endpoint.startswith("npipe:////./pipe/"):
        raise RuntimeError("The controller requires a local Docker Desktop named-pipe context.")
    pipe_path = "\\\\.\\pipe\\" + endpoint.rsplit("/", 1)[1]
    peek = ctypes.windll.kernel32.PeekNamedPipe
    peek.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                     wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    peek.restype = wintypes.BOOL
    with open(pipe_path, "r+b", buffering=0) as pipe:
        request = ("POST /containers/ac-worldserver/attach?stream=1&stdin=1&stdout=1&stderr=1 HTTP/1.1\r\n"
                   "Host: docker\r\nConnection: Upgrade\r\nUpgrade: tcp\r\nContent-Length: 0\r\n\r\n")
        pipe.write(request.encode())
        handle = msvcrt.get_osfhandle(pipe.fileno())
        buffer = b""
        deadline = time.monotonic() + 5
        while b"\r\n\r\n" not in buffer:
            available = wintypes.DWORD()
            if not peek(handle, None, 0, None, ctypes.byref(available), None):
                raise RuntimeError("Docker attach pipe closed")
            if available.value:
                buffer += pipe.read(available.value)
            elif time.monotonic() >= deadline:
                raise TimeoutError("Docker attach handshake timed out")
            else:
                time.sleep(0.02)
        header, output = buffer.split(b"\r\n\r\n", 1)
        if not header.startswith((b"HTTP/1.1 101", b"HTTP/1.1 200")):
            raise RuntimeError("Docker attach rejected the console connection")
        pipe.write((command + "\n").encode())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            available = wintypes.DWORD()
            if not peek(handle, None, 0, None, ctypes.byref(available), None):
                break
            if available.value:
                output += pipe.read(available.value)
            else:
                time.sleep(0.05)
        print(output.decode("utf-8", "replace"))


if __name__ == "__main__":
    send(sys.argv[1])
