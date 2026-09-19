"""The fast decompressor (slice copies) against the old one (one byte at a
time), on every compressed section of every `.bze` on the disc: same bytes.

    .venv/Scripts/python tools/diagnostics/check_bze.py

Exits with 1 if a section differs.
"""
import os
import sys
import time

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import bze  # noqa: E402
import paths  # noqa: E402


def lz_decompress_slow(block):
    """The previous, slower version, unchanged."""
    cfg = block[0]
    item_count = (block[1] << 16) | (block[2] << 8) | block[3]
    table, mask, distance_shift = bze._length_table(cfg)
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
                code_word = (block[pos] << 8) | block[pos + 1]
                pos += 2
                distance = code_word >> distance_shift
                run_length = table[code_word & mask] + 1
                source = len(output) - distance
                if source < 0:
                    raise ValueError("distance")
                for i in range(run_length):
                    output.append(output[source + i])
            flag_bits >>= 1
            done += 1
    return bytes(output)


n_identical = n_mismatched = 0
n_overlapping = 0
t_slow = t_fast = 0.0
file = sorted(f for f in os.listdir(paths.DATA_BZE) if f.lower().endswith(".bze"))
for entry_name in file:
    sections, data = bze.open_bze(os.path.join(paths.DATA_BZE, entry_name))
    for s in sections:
        raw_section = bze.section_bytes(data, s, inflate=False)
        try:
            a = time.perf_counter()
            old = lz_decompress_slow(raw_section)
            b = time.perf_counter()
        except Exception:  # noqa: BLE001
            continue        # not compressed, or unreadable before too
        new = bze.lz_decompress(raw_section)
        c = time.perf_counter()
        t_slow += b - a
        t_fast += c - b
        if new == old:
            n_identical += 1
        else:
            n_mismatched += 1
            print(f"DIFFERENT: {entry_name} section {s}")
print(f"{len(file)} files: {n_identical} sections identical, {n_mismatched} different")
print(f"time: old {t_slow:.1f} s, new {t_fast:.1f} s")
sys.exit(1 if n_mismatched or not n_identical else 0)
