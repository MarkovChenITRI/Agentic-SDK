"""Check that every path declared in REUSE.toml still matches a file.

REUSE.toml declares which unit owns which feature, and a central path list
decays silently: a file gets moved, the glob matches nothing, and the
declaration keeps looking correct while covering nothing at all. Technology
transfer reads this file to scope what it is transferring, so a stale entry is
a gap in the record rather than an untidy config.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "REUSE.toml"


def declared_paths() -> list[str]:
    annotations = tomllib.loads(DECLARATION.read_text(encoding="utf-8"))["annotations"]
    paths: list[str] = []
    for annotation in annotations:
        entry = annotation["path"]
        paths.extend(entry if isinstance(entry, list) else [entry])
    return paths


def main() -> int:
    unmatched = [pattern for pattern in declared_paths() if not any(ROOT.glob(pattern))]
    if not unmatched:
        return 0
    print("REUSE.toml 宣告的路徑找不到對應檔案：", file=sys.stderr)
    for pattern in unmatched:
        print(f"  {pattern}", file=sys.stderr)
    print(
        "檔案搬移後宣告不會跟著走，請更新 REUSE.toml 的路徑，"
        "並確認 CONTRIBUTORS.md 的範疇表一致。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
