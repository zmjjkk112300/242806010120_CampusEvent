"""打包提交物：排除 .venv、instance、缓存，保留 .git（含 baseline-v1 标签）。"""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "CampusEvent_242806010120_提交包.zip"
EXCLUDE_DIRS = {".venv", "instance", "__pycache__", ".pytest_cache", ".git-hooks"}

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.is_file():
            zf.write(path, Path(ROOT.name) / rel)

print(OUT, OUT.stat().st_size)
