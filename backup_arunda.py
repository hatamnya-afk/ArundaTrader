from pathlib import Path
from datetime import datetime
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = PROJECT_ROOT / "_backups"

EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "_backups",
}

EXCLUDE_FILES = {
    ".pyc",
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_name = f"ArundaTrader_BACKUP_{timestamp}.zip"
backup_path = BACKUP_DIR / backup_name

BACKUP_DIR.mkdir(exist_ok=True)

files_added = 0
files_skipped = 0

print("=" * 70)
print("ARUNDA TRADER — BACKUP")
print("=" * 70)
print(f"Project : {PROJECT_ROOT}")
print(f"Backup  : {backup_path}")
print()

with zipfile.ZipFile(
    backup_path,
    "w",
    compression=zipfile.ZIP_DEFLATED
) as zf:

    for path in PROJECT_ROOT.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(PROJECT_ROOT)

        # Skip excluded directories
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            files_skipped += 1
            continue

        # Skip excluded extensions
        if path.suffix.lower() in EXCLUDE_FILES:
            files_skipped += 1
            continue

        zf.write(path, relative)
        files_added += 1

print("BACKUP COMPLETE")
print("-" * 70)
print(f"Files included : {files_added}")
print(f"Files skipped  : {files_skipped}")
print(f"Backup size    : {backup_path.stat().st_size / 1024:.2f} KB")
print()
print(f"ZIP FILE:")
print(backup_path)
print("=" * 70)