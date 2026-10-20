#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source_db="$repo_dir/backend/payroll_tracker.db"
backup_dir="$repo_dir/backups"
if [[ ! -f "$source_db" ]]; then
  echo "Database missing: $source_db" >&2
  exit 1
fi
mkdir -p "$backup_dir"
stamp="$(date +%Y-%m-%d-%H%M%S)"
candidate="$backup_dir/task-tracker-$stamp.db"
counter=1
while [[ -e "$candidate" ]]; do
  candidate="$backup_dir/task-tracker-$stamp-$counter.db"
  counter=$((counter + 1))
done
cp --no-clobber -- "$source_db" "$candidate"
if [[ ! -s "$candidate" ]]; then
  echo "Backup failed: $candidate" >&2
  exit 1
fi
echo "$candidate"
