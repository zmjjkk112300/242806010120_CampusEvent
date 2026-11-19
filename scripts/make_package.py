"""打包仓库为 tar.gz，保留中文文件名（供云主机推送用）。"""

from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "CampusEvent_pkg.tar.gz"
SKIP = {".venv", "instance", "__pycache__", ".pytest_cache"}

with tarfile.open(OUT, "w:gz") as tf:
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(p in SKIP for p in rel.parts):
            continue
        tf.add(path, arcname=str(Path(ROOT.name) / rel).replace("\\", "/"))

print(OUT, OUT.stat().st_size)
