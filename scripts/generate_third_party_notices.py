"""Regenerate THIRD-PARTY-NOTICES.md from the declared dependencies.

The notice file carries an obligation, not a description: every dependency's
licence requires its copyright notice to travel with anything distributed. A
hand-maintained list goes stale the first time somebody adds a package and
forgets, and nothing reports it, so CI regenerates the file and compares.

Run with --check to compare only, which is what CI does.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICES = ROOT / "THIRD-PARTY-NOTICES.md"

_OBLIGATIONS = (
    ("MIT", "保留版權聲明與授權全文"),
    ("BSD-3-Clause", "保留版權聲明與授權全文，不得以原作者名義背書"),
    ("Apache-2.0", "保留 NOTICE，修改過的檔案要標示"),
    ("MPL-2.0", "檔案層級 copyleft，僅在修改該套件原始檔時觸發；本專案未修改"),
    ("PSF-2.0", "保留版權聲明"),
)


def declared_dependencies() -> list[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    names = {re.split(r"[=<>\[]", entry)[0].strip() for entry in project["dependencies"]}
    return sorted(names)


def describe(name: str) -> tuple[str, str]:
    """Return the licence and the home page recorded in the installed package."""
    try:
        meta = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return "未安裝，授權待確認", ""
    licence = meta.get("License-Expression") or ""
    if not licence:
        classifiers = [
            entry.rsplit("::", 1)[-1].strip()
            for entry in meta.get_all("Classifier") or []
            if "License ::" in entry
        ]
        licence = classifiers[0] if classifiers else (meta.get("License") or "未標示")
    if len(licence) >= 60:
        licence = "見套件內附授權"
    url = meta.get("Home-page") or ""
    if not url:
        for entry in meta.get_all("Project-URL") or []:
            if entry.lower().startswith(("homepage", "source", "repository")):
                url = entry.split(",", 1)[-1].strip()
                break
    return licence, url


def render() -> str:
    lines = [
        "# Third-Party Notices",
        "",
        "Agentic SDK 依賴以下套件，各自由其著作權人依所列授權條款釋出。"
        "散布本軟體時，這份清單連同各套件內附的授權全文一併散布。",
        "",
        "| 套件 | 授權 | 出處 |",
        "| --- | --- | --- |",
    ]
    for name in declared_dependencies():
        licence, url = describe(name)
        lines.append(f"| `{name}` | {licence} | {url} |")
    lines += ["", "## 各類授權帶來的義務", "", "| 授權 | 散布時要做什麼 |", "| --- | --- |"]
    lines += [f"| {licence} | {duty} |" for licence, duty in _OBLIGATIONS]
    lines += [
        "",
        "這份檔案由 `scripts/generate_third_party_notices.py` 產生，改動依賴後重新執行它。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="比對而不寫入，供 CI 使用")
    arguments = parser.parse_args()

    rendered = render()
    if not arguments.check:
        NOTICES.write_text(rendered, encoding="utf-8")
        return 0

    current = NOTICES.read_text(encoding="utf-8") if NOTICES.exists() else ""
    if current == rendered:
        return 0
    print(
        "THIRD-PARTY-NOTICES.md 與宣告的依賴不一致。"
        "執行 python scripts/generate_third_party_notices.py 後一併提交。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
