import argparse
import os
import sqlite3
from typing import List, Tuple

import dotenv

DEFAULT_DATABASE_PATH = "./output/data.sqlite"
COUNTABLE_COLUMNS = {
	"airline": "Airline",
	"aircraft": "Aircraft"
}


def _load_database_path() -> str:
	env_path = dotenv.find_dotenv('.env', False)
	dotenv.load_dotenv(env_path)
	return os.getenv("DATABASE_FILE_PATH", DEFAULT_DATABASE_PATH)


def _validate_column(column: str) -> str:
	if column not in COUNTABLE_COLUMNS:
		raise ValueError(f"Unsupported column '{column}'. Valid options: {', '.join(COUNTABLE_COLUMNS)}")
	return column


def fetch_counts(conn: sqlite3.Connection, column: str, limit: int | None = None) -> List[Tuple[str, int]]:
	column = _validate_column(column)
	query = f"""
        SELECT
            COALESCE(NULLIF(TRIM({column}), ''), 'Unknown') AS label,
            COUNT(*) AS total
        FROM incidents
        GROUP BY label
        ORDER BY total DESC, label ASC
    """
	rows = conn.execute(query).fetchall()
	if limit is not None:
		return rows[:limit]
	return rows


def _print_counts(title: str, rows: List[Tuple[str, int]]):
	print(f"\n{title}")
	if not rows:
		print("  (no data)")
		return
	for label, total in rows:
		print(f"{label} {total}次")


def analyze_database(db_path: str, mode: str, limit: int | None = None):
	if not os.path.exists(db_path):
		raise FileNotFoundError(f"Database file not found: {db_path}")
	conn = sqlite3.connect(db_path)
	try:
		if mode in ("airline", "both"):
			rows = fetch_counts(conn, "airline", limit=limit)
			_print_counts("按航空公司统计", rows)
		if mode in ("aircraft", "both"):
			rows = fetch_counts(conn, "aircraft", limit=limit)
			_print_counts("按机型统计", rows)
	finally:
		conn.close()


def parse_args():
	parser = argparse.ArgumentParser(
		description="统计 SQLite 数据库中的航司与机型出现次数。"
	)
	parser.add_argument(
		"--mode",
		choices=["airline", "aircraft", "both"],
		default="both",
		help="选择统计类型（默认 both）。"
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="只显示前 N 条记录。"
	)
	parser.add_argument(
		"--database",
		type=str,
		default=None,
		help="手动指定数据库路径（默认读取 .env 中的 DATABASE_FILE_PATH）。"
	)
	return parser.parse_args()


def main():
	args = parse_args()
	db_path = args.database or _load_database_path()
	analyze_database(db_path, mode=args.mode, limit=args.limit)


if __name__ == "__main__":
	main()

