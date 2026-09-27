"""Apply the idempotent 2.5x quest-only creature drop override to this stack."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    sql = (ROOT / "scripts/sql/quest-drop-boost.sql").read_text(encoding="utf-8")
    subprocess.run(
        ["docker", "compose", "exec", "-T", "ac-database", "sh", "-c",
         'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --batch acore_world'],
        cwd=ROOT, input=sql, text=True, check=True,
    )
    print("Saved. Reload creature loot or restart the world to apply to new loot.")


if __name__ == "__main__":
    main()
