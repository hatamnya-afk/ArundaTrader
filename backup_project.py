"""
ARUNDA TRADER
PROJECT BACKUP UTILITY v0.1

Current checkpoint:
DEV-06 — STEP 13A
FEATURE ENGINE CONTRACT AUDIT — PASS

Purpose
-------
Create a complete, read-only backup of the ArundaTrader project.

Safety
------
- No database mutation
- No SQL
- No production writes
- Source files are only READ
- Database is copied as a binary file
- Existing project is never modified
- Backup is written outside the project folder
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import hashlib
import shutil
import zipfile
import os


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

BACKUP_ROOT = Path(
    r"C:\Users\ASUS\ArundaTrader_Backups"
)

DATABASE_NAME = "arunda.db"

# Files/directories that should NOT be backed up
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
}

EXCLUDED_FILES = {
    "backup_project.py",
}


# ============================================================================
# HELPERS
# ============================================================================

def sha256_file(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def should_skip(path: Path) -> bool:

    if any(
        part in EXCLUDED_DIRS
        for part in path.parts
    ):
        return True

    if path.name in EXCLUDED_FILES:
        return True

    return False


def collect_files() -> list[Path]:

    files = []

    for path in PROJECT_DIR.rglob("*"):

        if not path.is_file():
            continue

        if should_skip(path):
            continue

        files.append(path)

    return sorted(
        files,
        key=lambda p: str(p).lower(),
    )


def format_size(size: int) -> str:

    units = (
        "B",
        "KB",
        "MB",
        "GB",
    )

    value = float(size)

    for unit in units:

        if value < 1024:

            return (
                f"{value:.2f} {unit}"
            )

        value /= 1024

    return f"{value:.2f} TB"


# ============================================================================
# BACKUP
# ============================================================================

def create_backup() -> None:

    print("=" * 110)
    print(
        "ARUNDA TRADER — FULL PROJECT BACKUP"
    )
    print("=" * 110)

    # ------------------------------------------------------------------------
    # Validate project
    # ------------------------------------------------------------------------

    if not PROJECT_DIR.exists():

        raise FileNotFoundError(
            f"Project directory not found: "
            f"{PROJECT_DIR}"
        )

    # ------------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_dir = (
        BACKUP_ROOT
        / f"ARUNDA_TRADER_BACKUP_{timestamp}"
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    # ------------------------------------------------------------------------
    # Create source snapshot
    # ------------------------------------------------------------------------

    snapshot_dir = (
        backup_dir
        / "PROJECT_SNAPSHOT"
    )

    snapshot_dir.mkdir(
        parents=True
    )

    files = collect_files()

    print()
    print(
        f"PROJECT : {PROJECT_DIR}"
    )

    print(
        f"BACKUP  : {backup_dir}"
    )

    print()
    print(
        f"FILES FOUND : {len(files)}"
    )

    # ------------------------------------------------------------------------
    # Copy files
    # ------------------------------------------------------------------------

    manifest = []

    total_size = 0

    for source in files:

        relative = source.relative_to(
            PROJECT_DIR
        )

        destination = (
            snapshot_dir
            / relative
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        size = source.stat().st_size

        total_size += size

        digest = sha256_file(
            source
        )

        manifest.append(
            {
                "path": str(relative),
                "size": size,
                "sha256": digest,
            }
        )

    # ------------------------------------------------------------------------
    # Check database
    # ------------------------------------------------------------------------

    database_path = (
        PROJECT_DIR
        / DATABASE_NAME
    )

    database_status = (
        "PRESENT"
        if database_path.exists()
        else "NOT FOUND"
    )

    # ------------------------------------------------------------------------
    # Write manifest
    # ------------------------------------------------------------------------

    manifest_path = (
        backup_dir
        / "MANIFEST.txt"
    )

    with manifest_path.open(
        "w",
        encoding="utf-8",
    ) as handle:

        handle.write(
            "ARUNDA TRADER — BACKUP MANIFEST\n"
        )

        handle.write(
            "=" * 100
            + "\n\n"
        )

        handle.write(
            "CHECKPOINT\n"
        )

        handle.write(
            "DEV-06 — STEP 13A\n"
        )

        handle.write(
            "FEATURE ENGINE CONTRACT AUDIT — PASS\n\n"
        )

        handle.write(
            f"Backup time : "
            f"{datetime.now().isoformat()}\n"
        )

        handle.write(
            f"Project     : "
            f"{PROJECT_DIR}\n"
        )

        handle.write(
            f"Database    : "
            f"{database_status}\n"
        )

        handle.write(
            f"File count  : "
            f"{len(manifest)}\n"
        )

        handle.write(
            f"Total size  : "
            f"{format_size(total_size)}\n\n"
        )

        handle.write(
            "=" * 100
            + "\n"
        )

        handle.write(
            "FILES\n"
        )

        handle.write(
            "=" * 100
            + "\n\n"
        )

        for item in manifest:

            handle.write(
                f"{item['path']}\n"
            )

            handle.write(
                f"SIZE   : "
                f"{item['size']} bytes\n"
            )

            handle.write(
                f"SHA256 : "
                f"{item['sha256']}\n\n"
            )

    # ------------------------------------------------------------------------
    # Create ZIP
    # ------------------------------------------------------------------------

    zip_path = (
        BACKUP_ROOT
        / (
            f"ARUNDA_TRADER_BACKUP_"
            f"{timestamp}.zip"
        )
    )

    print()
    print(
        "CREATING ZIP..."
    )

    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:

        for path in backup_dir.rglob("*"):

            if not path.is_file():
                continue

            archive_name = path.relative_to(
                backup_dir
            )

            archive.write(
                path,
                archive_name,
            )

    # ------------------------------------------------------------------------
    # Backup summary
    # ------------------------------------------------------------------------

    zip_size = zip_path.stat().st_size

    print()
    print("=" * 110)
    print(
        "BACKUP RESULT"
    )
    print("=" * 110)

    print()
    print(
        f"STATUS              : PASS"
    )

    print(
        f"CHECKPOINT          : DEV-06 — STEP 13A"
    )

    print(
        f"CONTRACT AUDIT      : PASS"
    )

    print(
        f"FILES BACKED UP     : {len(manifest)}"
    )

    print(
        f"SOURCE SIZE         : "
        f"{format_size(total_size)}"
    )

    print(
        f"ZIP SIZE            : "
        f"{format_size(zip_size)}"
    )

    print(
        f"DATABASE            : "
        f"{database_status}"
    )

    print(
        f"DATABASE MUTATION  : NONE"
    )

    print(
        f"PRODUCTION WRITE    : NONE"
    )

    print(
        f"SQL                 : NONE"
    )

    print()
    print(
        f"BACKUP DIRECTORY:"
    )

    print(
        backup_dir
    )

    print()
    print(
        f"ZIP BACKUP:"
    )

    print(
        zip_path
    )

    print()
    print("=" * 110)
    print(
        "BACKUP COMPLETE"
    )
    print("=" * 110)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    try:

        create_backup()

    except Exception as exc:

        print()
        print(
            "=" * 110
        )

        print(
            "BACKUP RESULT : FAIL"
        )

        print(
            f"ERROR : "
            f"{type(exc).__name__}: {exc}"
        )

        print(
            "=" * 110
        )

        raise