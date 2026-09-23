"""The version of the viewer: the only place where the number is written.

Every build shows it (window title, Help -> About) and the release zip takes
its name from it. It is the number of the NEXT release: right after a release
is published, raise it here.
"""

from __future__ import annotations

VERSION = "0.3.0"


def window_title(name: str, build: str = "") -> str:
    """"BBLIT Viewer 0.3.0", plus the kind of copy when the folder names one."""
    return f"{name} {VERSION}" + (f" — {build}" if build else "")
