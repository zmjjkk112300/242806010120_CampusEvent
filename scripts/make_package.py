"""打包仓库为 tar.gz，保留中文文件名（供云主机推送用）。

用法：
    python scripts/make_package.py            # 不含 .git，用于部署
    python scripts/make_package.py --with-git # 含 .git，用于推送完整提交历史
"""

import sys
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
WITH_GIT = "--with-git" in sys.argv
OUT = ROOT.parent / ("CampusEvent_pkg_git.tar.gz" if WITH_GIT else "CampusEvent_pkg.tar.gz")
SKIP = {".venv", "instance", "__pycache__", ".pytest_cache"}
if not WITH_GIT:
    SKIP.add(".git")

with tarfile.open(OUT, "w:gz") as tf:
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(p in SKIP for p in rel.parts):
            continue
        tf.add(path, arcname=str(Path(ROOT.name) / rel).replace("\\", "/"))

print(OUT, OUT.stat().st_size)
