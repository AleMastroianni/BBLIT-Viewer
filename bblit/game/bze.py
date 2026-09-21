"""Reader for the .bze container and LZ77 decompressor.

Container format (Ombelll's FORMATS.md §2):

    u32  version        always 1
    u32  section count
    per section (12 bytes):
        u32 id          1..10, not in order
        u32 size        actual size
        u32 reserved    size rounded up to 2048 (CD sector)
    data starts at 2048; each section is aligned to 2048

Compression (Ombelll's FORMATS.md §3, from FUN_00430ff0):

    byte 0      config (0x0B in all measured sections)
    byte 1..3   number of symbols, 24-bit BIG-endian
    byte 4..    the stream

The original file is never modified: it is only opened with "rb".
"""

from __future__ import annotations

import argparse
import os
import struct
from dataclasses import dataclass

SECTOR = 2048


@dataclass(frozen=True)
class BzeSection:
    id: int
    size: int
    reserved: int
    offset: int


def read_sections(data: bytes) -> list[BzeSection]:
    version, item_count = struct.unpack_from("<II", data, 0)
    if version != 1:
        raise ValueError(f"unexpected container version: {version}")
    sections, offset = [], SECTOR
    for i in range(item_count):
        sid, size, reserved = struct.unpack_from("<III", data, 8 + 12 * i)
        if reserved != -(-size // SECTOR) * SECTOR:
            raise ValueError(f"section {sid}: reserved {reserved} is not size {size} rounded up")
        sections.append(BzeSection(sid, size, reserved, offset))
        offset += reserved
    if offset != len(data):
        raise ValueError(f"computed size {offset} != file size {len(data)}")
    return sections


def _length_table(cfg: int) -> tuple[list[int], int, int]:
    mask = 0x7F >> (cfg & 7)
    distance_shift = 7 - (cfg & 7)
    extra_shift = (cfg >> 3) & 3
    threshold = 0x13 if mask >= 0x1F else mask >> 1
    table = []
    for i in range(mask + 1):
        val = i if i <= threshold else ((i - threshold) << extra_shift) + threshold
        table.append(val + 2)
    return table, mask, distance_shift


def lz_decompress(block: bytes) -> bytes:
    """Reconstruction of FUN_00430ff0."""
    cfg = block[0]
    item_count = (block[1] << 16) | (block[2] << 8) | block[3]
    table, mask, distance_shift = _length_table(cfg)

    output = bytearray()
    pos = 4
    done = 0
    while done < item_count:
        flag_bits = 0x100 | block[pos]
        pos += 1
        while flag_bits != 1 and done < item_count:
            if flag_bits & 1:
                output.append(block[pos])
                pos += 1
            else:
                code_word = (block[pos] << 8) | block[pos + 1]  # BIG-endian
                pos += 2
                distance = code_word >> distance_shift
                run_length = table[code_word & mask] + 1
                source = len(output) - distance
                if source < 0:
                    raise ValueError(f"distance {distance} past the start of the output")
                if distance >= run_length:
                    output += output[source:source + run_length]
                else:
                    # overlap (allowed): the run repeats every
                    # `distance` bytes, as if copied one byte at a time
                    run_bytes = output[source:]
                    output += (run_bytes * (run_length // distance + 1))[:run_length]
            flag_bits >>= 1
            done += 1
    return bytes(output)


def open_bze(file_path: str) -> tuple[list[BzeSection], bytes]:
    with open(file_path, "rb") as f:
        data = f.read()
    return read_sections(data), data


def section_bytes(data: bytes, s: BzeSection, *, inflate: bool = True) -> bytes:
    raw = data[s.offset : s.offset + s.size]
    return lz_decompress(raw) if inflate else raw


def main() -> None:
    p = argparse.ArgumentParser(description="reads and extracts a .bze file")
    p.add_argument("bze")
    p.add_argument("-o", "--output", help="folder to write the decompressed sections to")
    p.add_argument("--raw", action="store_true", help="do not decompress")
    args = p.parse_args()

    sections, data = open_bze(args.bze)
    stem = os.path.splitext(os.path.basename(args.bze))[0]
    print(f"{args.bze}: {len(sections)} sections, {len(data)} bytes")
    for s in sections:
        block = section_bytes(data, s, inflate=not args.raw)
        cfg = data[s.offset]
        print(
            f"  id {s.id:2d}  offset {s.offset:9d}  compressed {s.size:8d}"
            f"  -> {len(block):9d}  ({len(block) / s.size:4.2f}x, cfg 0x{cfg:02X})"
        )
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            name = os.path.join(args.output, f"{stem}_id{s.id:02d}.bin")
            with open(name, "wb") as f:
                f.write(block)


if __name__ == "__main__":
    main()
