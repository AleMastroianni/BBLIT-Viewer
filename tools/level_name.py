"""The official name of a level from its file code, and the other way round.

    .venv/Scripts/python tools/level_name.py L05A1 L03A
    .venv/Scripts/python tools/level_name.py --all
    .venv/Scripts/python tools/level_name.py --find "Planet X"

The rule: a level's name is **always** read with
`levels.official_name`, never written from memory, not even in a chat message;
and in prose -- documents, docstrings, messages -- the first mention is
`Name (CODE)`, as this prints it: "The Planet X File! 1 (L05A1)". In the
viewer's own interface the name stays alone.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
from game import levels  # noqa: E402


def in_prose(code: str, in_english: bool = False) -> str:
    """"The Planet X File! 1 (L05A1)", or just the code if it has no name."""
    name = levels.official_name(code, in_english)
    return f"{name} ({code.upper()})" if name else code.upper()


def main(argv):
    codes = sorted({v[1] for v in levels.all_entries()})
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--all":
        for code in codes:
            print(f"{code:10s} {levels.official_name(code) or '—'}")
        return 0
    if argv[0] == "--find":
        needle = " ".join(argv[1:]).lower()
        for code in codes:
            name = levels.official_name(code) or ""
            if needle in name.lower():
                print(in_prose(code))
        return 0
    for code in argv:
        print(in_prose(code))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
