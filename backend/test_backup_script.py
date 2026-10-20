import shutil
import subprocess
from pathlib import Path


def test_backup_script_creates_unique_copies(tmp_path):
    repo = tmp_path / "fixture"
    (repo / "backend").mkdir(parents=True)
    (repo / "scripts").mkdir()
    script = repo / "scripts" / "backup-db.sh"
    shutil.copy2(Path(__file__).resolve().parents[1] / "scripts" / "backup-db.sh", script)
    database = repo / "backend" / "payroll_tracker.db"

    missing = subprocess.run(["bash", str(script)], capture_output=True, text=True, check=False)
    assert missing.returncode != 0
    assert "Database missing" in missing.stderr

    database.write_bytes(b"SQLite fixture")
    first = subprocess.run(["bash", str(script)], capture_output=True, text=True, check=True)
    second = subprocess.run(["bash", str(script)], capture_output=True, text=True, check=True)
    first_path = Path(first.stdout.strip())
    second_path = Path(second.stdout.strip())
    assert first_path != second_path
    assert first_path.read_bytes() == second_path.read_bytes() == b"SQLite fixture"
