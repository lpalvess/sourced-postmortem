"""Gera .claude-plugin/icon.png (1024x1024) só com a biblioteca padrão."""
import struct
import zlib
from pathlib import Path

SIZE = 1024
BG = (0x11, 0x18, 0x27)
FG = (0xFF, 0xC8, 0x3D)

RING_C = (440, 440)
RING_R = 260
RING_T = 80
HANDLE = ((630, 630), (860, 860), 70)
CHECK = (((330, 450), (410, 530), 45), ((410, 530), (560, 360), 45))


def seg_dist(px, py, a, b):
    """Distância do ponto (px, py) ao segmento a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def inside(x, y):
    d = ((x - RING_C[0]) ** 2 + (y - RING_C[1]) ** 2) ** 0.5
    if abs(d - RING_R) <= RING_T / 2:
        return True
    a, b, t = HANDLE
    if seg_dist(x, y, a, b) <= t / 2:
        return True
    return any(seg_dist(x, y, a, b) <= t / 2 for a, b, t in CHECK)


def main():
    raw = bytearray()
    bg, fg = bytes(BG), bytes(FG)
    for y in range(SIZE):
        raw.append(0)
        for x in range(SIZE):
            raw += fg if inside(x + 0.5, y + 0.5) else bg

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    out = Path(__file__).resolve().parents[2] / ".claude-plugin" / "icon.png"
    out.write_bytes(png)
    print(f"gravado {out} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
