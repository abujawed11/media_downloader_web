#!/usr/bin/env python3
"""
Cleanup script to remove old downloaded files from VPS storage.
Run this as a cron job: 0 */6 * * * python cleanup_old_files.py
"""
import os
import shutil
import time
from datetime import datetime, timedelta

# Configuration
DOWNLOADS_DIR = "/app/downloads"  # Docker volume path
MAX_AGE_HOURS = 24  # Delete files older than 24 hours
DRY_RUN = False  # Set to True to see what would be deleted without actually deleting


def cleanup_old_files(downloads_dir: str, max_age_hours: int, dry_run: bool = False):
    """Delete temporary download directories older than max_age_hours."""

    if not os.path.isdir(downloads_dir):
        print(f"Downloads directory not found: {downloads_dir}")
        return

    cutoff_time = time.time() - (max_age_hours * 3600)
    total_size = 0
    deleted_count = 0

    print(f"Scanning {downloads_dir} for files older than {max_age_hours} hours...")
    print(f"Cutoff time: {datetime.fromtimestamp(cutoff_time)}")

    for item in os.listdir(downloads_dir):
        item_path = os.path.join(downloads_dir, item)

        # Only process directories (temp download folders)
        if not os.path.isdir(item_path):
            continue

        # Check if it's a temp download directory (starts with "md_" or "mdjob_")
        if not (item.startswith("md_") or item.startswith("mdjob_")):
            continue

        # Get modification time
        mtime = os.path.getmtime(item_path)

        if mtime < cutoff_time:
            # Calculate size
            size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(item_path)
                for filename in filenames
            )
            total_size += size

            age_hours = (time.time() - mtime) / 3600
            size_mb = size / (1024 * 1024)

            if dry_run:
                print(f"[DRY RUN] Would delete: {item} (Age: {age_hours:.1f}h, Size: {size_mb:.1f}MB)")
            else:
                try:
                    shutil.rmtree(item_path)
                    deleted_count += 1
                    print(f"✓ Deleted: {item} (Age: {age_hours:.1f}h, Size: {size_mb:.1f}MB)")
                except Exception as e:
                    print(f"✗ Failed to delete {item}: {e}")

    total_size_mb = total_size / (1024 * 1024)
    total_size_gb = total_size / (1024 * 1024 * 1024)

    if dry_run:
        print(f"\n[DRY RUN] Would delete {deleted_count} directories, freeing {total_size_gb:.2f}GB")
    else:
        print(f"\n✓ Cleanup complete! Deleted {deleted_count} directories, freed {total_size_gb:.2f}GB")


if __name__ == "__main__":
    import sys

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No files will be deleted")
        print("=" * 60)

    cleanup_old_files(DOWNLOADS_DIR, MAX_AGE_HOURS, dry_run)
