"""Remove only this project's generated build directory."""

import pathlib, shutil

root = pathlib.Path(__file__).resolve().parents[1]
target = (root / "build").resolve()
if target.parent != root or target.name != "build":
    raise SystemExit("Unsafe build path")
if target.exists():
    shutil.rmtree(target)
