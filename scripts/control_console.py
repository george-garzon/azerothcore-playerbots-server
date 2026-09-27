"""Send a fixed command over Docker Desktop's local attach API (Windows pipe)."""
import ctypes
from ctypes import wintypes
import os
import re
import subprocess
import sys
import time
import msvcrt


def extract_player_level(output):
    # pinfo also includes private account details: return only its character-level line.
    clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    levels = re.findall(r"\| Level: (\d+)\b", clean)
    if len(levels) != 1 or not 1 <= int(levels[0]) <= 80:
        raise RuntimeError("Could not read the character's live level.")
    return levels[0]


def send(command):
    player_info = re.fullmatch(r"pinfo [A-Za-z]{2,12}", command)
    if command not in ("server info", "ollama reload", "reload creature_loot_template",
                       "reload config", "playerbots rndbot reload") and not player_info and not re.fullmatch(
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
        decoded = output.decode("utf-8", "replace")
        print(extract_player_level(decoded) if player_info else decoded)


if __name__ == "__main__":
    send(sys.argv[1])
